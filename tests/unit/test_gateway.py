import pytest

from loanlens.llm.gateway import (
    PRICES_USD,
    CircuitBreaker,
    FakeLLM,
    LLMError,
    LLMGateway,
    LLMUnavailable,
    Reply,
    cost_inr,
    estimate_tokens,
)

MESSAGES = [{"role": "user", "content": "Explain education loans."}]


async def no_sleep(seconds: float) -> None:
    pass


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


# 1–5: Circuit breaker


def test_circuit_starts_closed():
    breaker = CircuitBreaker()
    assert breaker.state == "closed"
    assert breaker.allow()


def test_circuit_opens_after_threshold_failures():
    breaker = CircuitBreaker(threshold=3)
    for _ in range(3):
        breaker.failure()
    assert breaker.state == "open"
    assert not breaker.allow()


def test_circuit_becomes_half_open_after_cooldown():
    clock = FakeClock()
    breaker = CircuitBreaker(threshold=1, cooldown=30, clock=clock)
    breaker.failure()
    clock.advance(30)
    assert breaker.state == "half-open"
    assert breaker.allow()


def test_circuit_success_closes_it():
    breaker = CircuitBreaker(threshold=1)
    breaker.failure()
    breaker.success()
    assert breaker.state == "closed"
    assert breaker.failures == 0


def test_circuit_failure_reopens_after_half_open():
    clock = FakeClock()
    breaker = CircuitBreaker(threshold=1, cooldown=10, clock=clock)
    breaker.failure()
    clock.advance(10)
    assert breaker.state == "half-open"
    breaker.failure()
    assert breaker.state == "open"


# 6–8: Pricing and token estimation


def test_pricing_table_contains_configured_models():
    assert "gemini-3.5-flash-lite" in PRICES_USD
    assert "openai/gpt-oss-20b" in PRICES_USD


def test_cost_calculation_returns_nonnegative_value():
    result = cost_inr(
        "gemini-3.5-flash-lite",
        1000,
        500,
        95.0,
    )
    assert result >= 0


def test_token_estimation_returns_integer():
    result = estimate_tokens("Explain education loans in India.")
    assert isinstance(result, int)
    assert result >= 0


# 9–10: Fake provider


@pytest.mark.asyncio
async def test_fake_llm_generates_answer():
    provider = FakeLLM(script=["LoanLens test answer"])
    reply = await provider.generate(MESSAGES)
    assert reply.text == "LoanLens test answer"
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_fake_llm_streams_answer():
    provider = FakeLLM(script=["Hello world"])
    usage = Reply()
    pieces = [piece async for piece in provider.stream(MESSAGES, usage)]
    assert "".join(pieces).strip() == "Hello world"
    assert usage.tokens_out > 0


# 11–15: Gateway generation


@pytest.mark.asyncio
async def test_gateway_generates_successfully():
    provider = FakeLLM(name="gemini", model="gemini-3.5-flash-lite")
    gateway = LLMGateway([provider], sleep=no_sleep)

    result = await gateway.generate(MESSAGES)

    assert result.text == "A fake answer."
    assert result.provider == "gemini"
    assert result.fallback_used is False


@pytest.mark.asyncio
async def test_gateway_retries_retryable_error():
    provider = FakeLLM(
        name="gemini",
        script=[
            LLMError("Temporary error", retryable=True),
            "Recovered answer",
        ],
    )
    gateway = LLMGateway([provider], sleep=no_sleep)

    result = await gateway.generate(MESSAGES)

    assert result.text == "Recovered answer"
    assert provider.calls == 2
    assert result.attempts == 2


@pytest.mark.asyncio
async def test_gateway_does_not_retry_nonretryable_error():
    provider = FakeLLM(
        name="gemini",
        script=[LLMError("Invalid request", retryable=False)],
    )
    gateway = LLMGateway([provider], sleep=no_sleep)

    with pytest.raises(LLMUnavailable):
        await gateway.generate(MESSAGES)

    assert provider.calls == 1


@pytest.mark.asyncio
async def test_gateway_falls_back_to_second_provider():
    primary = FakeLLM(
        name="gemini",
        script=[LLMError("Primary unavailable", retryable=False)],
    )
    fallback = FakeLLM(name="groq", script=["Fallback answer"])

    gateway = LLMGateway([primary, fallback], sleep=no_sleep)
    result = await gateway.generate(MESSAGES)

    assert result.text == "Fallback answer"
    assert result.provider == "groq"
    assert result.fallback_used is True


@pytest.mark.asyncio
async def test_gateway_without_providers_raises_unavailable():
    gateway = LLMGateway([])

    with pytest.raises(LLMUnavailable):
        await gateway.generate(MESSAGES)


# 16–19: Streaming and recording


@pytest.mark.asyncio
async def test_gateway_streams_answer_and_result():
    provider = FakeLLM(name="gemini", script=["Hello from LoanLens"])
    gateway = LLMGateway([provider], sleep=no_sleep)

    items = [item async for item in gateway.stream(MESSAGES)]

    assert any(isinstance(item, str) for item in items)
    assert any(not isinstance(item, str) for item in items)


@pytest.mark.asyncio
async def test_gateway_stream_falls_back_before_first_piece():
    primary = FakeLLM(
        name="gemini",
        script=[LLMError("Unavailable", retryable=False)],
    )
    fallback = FakeLLM(name="groq", script=["Fallback stream"])

    gateway = LLMGateway([primary, fallback], sleep=no_sleep)
    items = [item async for item in gateway.stream(MESSAGES)]

    text = "".join(item for item in items if isinstance(item, str))
    result = next(item for item in items if not isinstance(item, str))

    assert "Fallback stream" in text
    assert result.provider == "groq"
    assert result.fallback_used is True


@pytest.mark.asyncio
async def test_gateway_does_not_fallback_after_partial_stream():
    primary = FakeLLM(
        name="gemini",
        script=[
            (
                "partial",
                LLMError("Stream interrupted", retryable=True),
            )
        ],
    )
    fallback = FakeLLM(name="groq", script=["Should not be used"])

    gateway = LLMGateway([primary, fallback], sleep=no_sleep)
    stream = gateway.stream(MESSAGES)

    with pytest.raises(LLMUnavailable):
        async for _ in stream:
            pass

    assert fallback.calls == 0


@pytest.mark.asyncio
async def test_gateway_records_success():
    records = []

    async def recorder(row):
        records.append(row)

    provider = FakeLLM(name="gemini")
    gateway = LLMGateway([provider], recorder=recorder, sleep=no_sleep)

    await gateway.generate(MESSAGES, purpose="chat", prompt_version="v1")

    assert len(records) == 1
    assert records[0]["provider"] == "gemini"
    assert records[0]["status"] == "ok"
    assert records[0]["purpose"] == "chat"
    assert records[0]["prompt_version"] == "v1"
