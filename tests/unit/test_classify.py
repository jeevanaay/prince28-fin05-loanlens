import pytest

from loanlens.llm.classify import (
    accuracy,
    build_messages,
    classify,
    find_leaks,
    parse_label,
)
from loanlens.llm.gateway import FakeLLM, LLMGateway


def test_build_messages_wraps_question_in_tags():
    messages = build_messages("Classify the question.", "  What is PM-Vidyalaxmi?  ")

    assert messages == [
        {"role": "system", "content": "Classify the question."},
        {
            "role": "user",
            "content": "<question>\nWhat is PM-Vidyalaxmi?\n</question>",
        },
    ]


def test_parse_label_accepts_valid_labels():
    assert parse_label("docs") == "docs"
    assert parse_label("PERSONAL.") == "personal"
    assert parse_label("off-topic") == "off_topic"


def test_parse_label_rejects_invalid_or_ambiguous_replies():
    assert parse_label("maybe") == "invalid"
    assert parse_label("docs personal") == "invalid"
    assert parse_label("") == "invalid"


@pytest.mark.asyncio
async def test_classify_returns_label_and_result():
    provider = FakeLLM(name="gemini", script=["docs"])
    gateway = LLMGateway([provider])

    label, result = await classify(
        gateway,
        "Classify the question.",
        "v3",
        "What is PM-Vidyalaxmi?",
    )

    assert label == "docs"
    assert result.text == "docs"
    assert result.provider == "gemini"
    assert provider.calls == 1


def test_accuracy_calculates_correct_fraction():
    rows = [
        {"label": "docs", "got": "docs"},
        {"label": "personal", "got": "docs"},
        {"label": "off_topic", "got": "off_topic"},
    ]

    assert accuracy(rows) == pytest.approx(2 / 3)
    assert accuracy([]) == 0.0


def test_find_leaks_detects_questions_in_prompt():
    prompt = "Example: What is PM-Vidyalaxmi and who is eligible?"

    assert find_leaks(
        prompt,
        [
            "What is PM-Vidyalaxmi and who is eligible?",
            "What is the SBI moratorium period?",
        ],
    ) == ["What is PM-Vidyalaxmi and who is eligible?"]


def test_find_leaks_returns_empty_when_no_questions_leak():
    prompt = "Classify education loan questions."

    assert (
        find_leaks(
            prompt,
            [
                "What is PM-Vidyalaxmi?",
                "What is the SBI moratorium period?",
            ],
        )
        == []
    )
