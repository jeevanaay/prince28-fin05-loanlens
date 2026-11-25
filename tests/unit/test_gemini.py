import json

import httpx
import pytest

from loanlens.llm.gemini import (
    GEMINI_URL,
    GeminiAPIError,
    GeminiProvider,
)


@pytest.mark.asyncio
async def test_stream_yields_text_and_usage():
    sse = (
        'data: {"event_type":"interaction.created",'
        '"interaction":{"id":"test-interaction-123"}}\n\n'
        'data: {"event_type":"step.delta",'
        '"delta":{"type":"text","text":"Hello "}}\n\n'
        'data: {"event_type":"step.delta",'
        '"delta":{"type":"text","text":"from LoanLens."}}\n\n'
        'data: {"event_type":"interaction.completed",'
        '"interaction":{"id":"test-interaction-123",'
        '"usage":{"total_input_tokens":10,'
        '"total_output_tokens":5,"total_tokens":15}}}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == GEMINI_URL
        assert request.headers["x-goog-api-key"] == "unit-test-placeholder"

        payload = json.loads(request.content)
        assert payload["model"] == "gemini-3.5-flash-lite"
        assert payload["input"] == "What is a loan?"
        assert payload["stream"] is True
        assert payload["system_instruction"] == "You are LoanLens."

        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text=sse,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GeminiProvider(
            api_key="unit-test-placeholder",  # pragma: allowlist secret
            model="gemini-3.5-flash-lite",
            client=client,
        )
        events = [
            event
            async for event in provider.stream(
                "What is a loan?",
                system_instruction="You are LoanLens.",
            )
        ]

    text = "".join(event.text or "" for event in events)
    assert text == "Hello from LoanLens."

    assert events[0].interaction_id == "test-interaction-123"
    assert events[-1].event_type == "interaction.completed"
    assert events[-1].usage == {
        "total_input_tokens": 10,
        "total_output_tokens": 5,
        "total_tokens": 15,
    }


@pytest.mark.asyncio
async def test_stream_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"error": {"message": "Rate limit exceeded"}},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GeminiProvider("test-key", "test-model", client)

        with pytest.raises(GeminiAPIError, match="Gemini HTTP 429"):
            async for _ in provider.stream("Hello"):
                pass


def test_provider_requires_api_key():
    async def unused_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(unused_handler))

    with pytest.raises(ValueError, match="Gemini API key is required"):
        GeminiProvider("", "test-model", client)
