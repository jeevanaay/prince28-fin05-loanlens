import pytest
from pydantic import ValidationError

from loanlens.db.models import Document
from loanlens.llm.doc_meta import DocMeta
from loanlens.llm.extract import (
    build_messages,
    extract,
    parse_json,
    pending,
)
from loanlens.llm.gateway import FakeLLM, LLMGateway

VALID_META = {
    "doc_kind": "guideline",
    "year": 2025,
    "language": "en",
    "summary": "This guideline explains education loan eligibility and application requirements.",
    "topics": ["education loans", "eligibility"],
    "lender": "SBI",
    "scheme": "Global Ed-Vantage",
    "max_amount": None,
    "collateral_threshold": None,
    "subsidy_income_limit": None,
}


def test_parse_json():
    result = parse_json('{"doc_kind": "guideline"}')
    assert result == {"doc_kind": "guideline"}


def test_parse_json_with_markdown():
    reply = '```json\n{"doc_kind": "guideline"}\n```'
    assert parse_json(reply) == {"doc_kind": "guideline"}


def test_parse_json_invalid():
    with pytest.raises(ValueError):
        parse_json("No JSON here")


def test_doc_meta_valid():
    record = DocMeta.model_validate(VALID_META)
    assert record.doc_kind == "guideline"
    assert record.language == "en"
    assert record.topics == ["education loans", "eligibility"]


def test_doc_meta_rejects_unknown_fields():
    invalid = {**VALID_META, "unexpected": "value"}

    with pytest.raises(ValidationError):
        DocMeta.model_validate(invalid)


def test_build_messages():
    messages = build_messages("Extract metadata.", "SBI education loan guideline")

    assert messages[0]["role"] == "system"
    assert "required JSON schema" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "<document>" in messages[1]["content"]


@pytest.mark.asyncio
async def test_extract_success():
    import json

    llm = FakeLLM(script=[json.dumps(VALID_META)])
    gateway = LLMGateway(providers=[llm])

    result = await extract(
        gateway,
        "Extract metadata.",
        "extract_v1",
        "SBI education loan guideline",
    )

    assert result.ok
    assert result.attempts == 1
    assert result.record.doc_kind == "guideline"


@pytest.mark.asyncio
async def test_extract_repairs_invalid_response():
    import json

    llm = FakeLLM(
        script=[
            '{"doc_kind": "invalid"}',
            json.dumps(VALID_META),
        ]
    )
    gateway = LLMGateway(providers=[llm])

    result = await extract(
        gateway,
        "Extract metadata.",
        "extract_v1",
        "SBI education loan guideline",
    )

    assert result.ok
    assert result.repaired
    assert result.attempts == 2
    assert len(result.errors) == 1


class FakePendingSession:
    def __init__(self, documents):
        self.documents = documents

    async def scalars(self, statement):
        class Result:
            def __init__(self, documents):
                self.documents = documents

            def all(self):
                return self.documents

        return Result(self.documents)


def make_document(doc_id, extraction=None):
    return Document(
        id=doc_id,
        external_id=f"doc-{doc_id}",
        title=f"Document {doc_id}",
        doc_type="guideline",
        metadata_=extraction or {},
    )


@pytest.mark.asyncio
async def test_pending_skips_documents_already_processed_by_same_prompt():
    documents = [
        make_document(1),
        make_document(
            2,
            {
                "extract": {
                    "prompt": "extract_v1",
                    "status": "ok",
                }
            },
        ),
        make_document(
            3,
            {
                "extract": {
                    "prompt": "extract_v0",
                    "status": "ok",
                }
            },
        ),
    ]

    session = FakePendingSession(documents)

    result = await pending(session, version="extract_v1")

    assert [document.id for document in result] == [1, 3]


@pytest.mark.asyncio
async def test_pending_retry_failed_selects_only_failed_documents():
    documents = [
        make_document(1),
        make_document(
            2,
            {
                "extract": {
                    "prompt": "extract_v1",
                    "status": "ok",
                }
            },
        ),
        make_document(
            3,
            {
                "extract": {
                    "prompt": "extract_v1",
                    "status": "error",
                    "error": "Invalid JSON",
                }
            },
        ),
        make_document(
            4,
            {
                "extract": {
                    "prompt": "extract_v0",
                    "status": "error",
                    "error": "Validation failed",
                }
            },
        ),
    ]

    session = FakePendingSession(documents)

    result = await pending(
        session,
        version="extract_v1",
        retry_failed=True,
    )

    assert [document.id for document in result] == [3, 4]
