"""Extract and validate structured metadata from parsed documents."""

import asyncio
import json
import time
from dataclasses import dataclass, field

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from loanlens.db.models import Document, Page
from loanlens.llm.doc_meta import DocMeta
from loanlens.llm.gateway import LLMGateway, LLMResult, LLMUnavailable


def parse_json(reply: str) -> dict:
    """Parse a JSON object, tolerating surrounding prose or Markdown fences."""
    start = reply.find("{")

    if start == -1:
        raise ValueError("No JSON object found in model response")

    try:
        value, _ = json.JSONDecoder().raw_decode(reply[start:])
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc.msg}") from exc

    if not isinstance(value, dict):
        raise ValueError("Model response must contain a JSON object")

    return value


def explain(error: Exception) -> str:
    """Return a compact explanation of a parsing or validation error."""
    if isinstance(error, ValidationError):
        details = [
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        ]
        return "; ".join(details)[:1000]

    return str(error)[:1000]


@dataclass
class Extraction:
    """Result of one document extraction."""

    record: DocMeta | None
    attempts: int
    errors: list[str] = field(default_factory=list)
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_inr: float = 0.0

    @property
    def ok(self) -> bool:
        return self.record is not None

    @property
    def repaired(self) -> bool:
        return self.ok and self.attempts > 1


def build_messages(
    prompt: str,
    document_text: str,
) -> list[dict[str, str]]:
    """Keep document content separate from extraction instructions."""
    schema = json.dumps(DocMeta.model_json_schema(), indent=2)

    system_prompt = (
        f"{prompt.strip()}\n\n"
        "The required JSON schema is:\n"
        f"{schema}\n\n"
        "Return an object that validates against this schema."
    )

    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (f"<document>\n{document_text.strip()}\n</document>"),
        },
    ]


async def extract(
    gateway: LLMGateway,
    prompt: str,
    version: str,
    document_text: str,
    *,
    max_attempts: int = 3,
) -> Extraction:
    """Extract metadata, validate it, and retry with validation feedback."""
    messages = build_messages(prompt, document_text)

    errors: list[str] = []
    total_tokens_in = 0
    total_tokens_out = 0
    total_cost = 0.0
    model = ""

    for attempt in range(1, max_attempts + 1):
        result: LLMResult = await gateway.generate(
            messages,
            purpose="extract",
            prompt_version=version,
            temperature=0,
        )

        model = result.model
        total_tokens_in += result.tokens_in
        total_tokens_out += result.tokens_out
        total_cost += result.cost_inr

        try:
            data = parse_json(result.text)
            record = DocMeta.model_validate(data)

            return Extraction(
                record=record,
                attempts=attempt,
                errors=errors,
                model=model,
                tokens_in=total_tokens_in,
                tokens_out=total_tokens_out,
                cost_inr=round(total_cost, 6),
            )

        except (ValueError, ValidationError) as exc:
            reason = explain(exc)
            errors.append(reason)

            if attempt == max_attempts:
                break

            messages.extend(
                [
                    {"role": "assistant", "content": result.text},
                    {
                        "role": "user",
                        "content": (
                            "Your previous response could not be accepted.\n"
                            f"Problem: {reason}\n"
                            "Correct the response and return exactly one valid "
                            "JSON object matching the required schema. "
                            "Use only facts supported by the document."
                        ),
                    },
                ]
            )

    return Extraction(
        record=None,
        attempts=max_attempts,
        errors=errors,
        model=model,
        tokens_in=total_tokens_in,
        tokens_out=total_tokens_out,
        cost_inr=round(total_cost, 6),
    )


def document_text(pages: list[Page], max_chars: int = 12000) -> str:
    """Combine the first three pages, keeping the text within a safe limit."""
    selected = sorted(pages, key=lambda page: page.page_no)[:3]
    text = "\n\n".join(page.text for page in selected if page.text)
    return text[:max_chars]


async def pending(
    session: AsyncSession,
    *,
    version: str = "extract_v1",
    limit: int | None = None,
    retry_failed: bool = False,
) -> list[Document]:
    """Find parsed documents that need extraction or a retry."""
    if limit is not None and limit < 1:
        return []

    statement = select(Document).where(Document.doc_type != "record").order_by(Document.id)

    result = await session.scalars(statement)
    documents = []

    for document in result.all():
        metadata = document.metadata_ or {}
        extraction = metadata.get("extract", {})
        previous_prompt = extraction.get("prompt")
        failed = extraction.get("status") == "error"

        if retry_failed:
            if not failed:
                continue
        elif previous_prompt == version:
            continue

        documents.append(document)

        if limit is not None and len(documents) >= limit:
            break

    return documents


async def save(
    session: AsyncSession,
    document: Document,
    result: Extraction,
    *,
    version: str = "extract_v1",
) -> None:
    """Save extraction output without deleting ingestion metadata."""
    metadata = dict(document.metadata_ or {})

    if result.record is not None:
        metadata.update(result.record.model_dump())

        metadata["extract"] = {
            "prompt": version,
            "status": "ok",
            "attempts": result.attempts,
            "model": result.model,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "cost_inr": result.cost_inr,
        }
    else:
        metadata["extract"] = {
            "prompt": version,
            "status": "error",
            "error": result.errors[-1] if result.errors else "Extraction failed",
            "attempts": result.attempts,
            "model": result.model,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "cost_inr": result.cost_inr,
        }

    document.metadata_ = metadata
    await session.commit()


async def run(
    session_factory: async_sessionmaker,
    gateway: LLMGateway,
    prompt: str,
    *,
    version: str = "extract_v1",
    limit: int | None = None,
    retry_failed: bool = False,
    rpm: int = 12,
) -> dict:
    """Extract metadata from pending documents with request pacing."""
    async with session_factory() as session:
        documents = await pending(
            session,
            version=version,
            limit=limit,
            retry_failed=retry_failed,
        )

    stats = {
        "total": len(documents),
        "ok": 0,
        "repaired": 0,
        "failed": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_inr": 0.0,
    }

    delay = 60 / rpm if rpm > 0 else 0
    consecutive_unavailable = 0

    for index, document in enumerate(documents, start=1):
        started = time.monotonic()
        stop_after_save = False
        if stop_after_save:
            print("Stopping after two consecutive LLM failures. Run again later to resume.")
            break
        async with session_factory() as session:
            current = await session.get(Document, document.id)

            if current is None:
                continue

            pages_result = await session.scalars(
                select(Page).where(Page.document_id == current.id).order_by(Page.page_no).limit(3)
            )
            text = document_text(list(pages_result.all()))

            if not text.strip():
                extraction = Extraction(
                    record=None,
                    attempts=0,
                    errors=["Document has no extractable page text"],
                )
            else:
                try:
                    extraction = await extract(
                        gateway,
                        prompt,
                        version,
                        text,
                    )
                    consecutive_unavailable = 0
                except LLMUnavailable as exc:
                    consecutive_unavailable += 1
                    extraction = Extraction(
                        record=None,
                        attempts=0,
                        errors=[str(exc)],
                    )
                    stop_after_save = consecutive_unavailable >= 2

            await save(
                session,
                current,
                extraction,
                version=version,
            )

        stats["ok"] += int(extraction.ok)
        stats["repaired"] += int(extraction.repaired)
        stats["failed"] += int(not extraction.ok)
        stats["tokens_in"] += extraction.tokens_in
        stats["tokens_out"] += extraction.tokens_out
        stats["cost_inr"] += extraction.cost_inr

        if index % 10 == 0 or index == len(documents):
            print(
                f"[{index}/{len(documents)}] "
                f"ok={stats['ok']} "
                f"repaired={stats['repaired']} "
                f"failed={stats['failed']}"
            )

        remaining = delay - (time.monotonic() - started)
        if remaining > 0 and index < len(documents):
            await asyncio.sleep(remaining)

    stats["cost_inr"] = round(stats["cost_inr"], 6)
    return stats
