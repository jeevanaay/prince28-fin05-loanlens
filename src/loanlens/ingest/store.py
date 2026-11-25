from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from loanlens.db.models import Document, Page, ParseFailure


async def store_parsed_document(
    session: AsyncSession,
    *,
    path: Path,
    manifest_record: dict,
    parsed_doc,
) -> Document:
    """Store document metadata and its parsed pages."""

    source_url = manifest_record.get("url", "")
    external_id = hashlib.sha256(source_url.encode()).hexdigest()

    document = await session.scalar(select(Document).where(Document.external_id == external_id))

    metadata = {
        "parser": parsed_doc.parser,
        "source": manifest_record.get("source"),
        "path": str(path),
        "page_count": len(parsed_doc.pages),
        "table_count": sum(page.tables for page in parsed_doc.pages),
    }

    if document is None:
        document = Document(
            external_id=external_id,
            title=manifest_record.get("title") or parsed_doc.title or path.stem,
            lender=manifest_record.get("source"),
            source_url=source_url,
            licence=manifest_record.get("licence"),
            doc_type=parsed_doc.kind,
            sha256=manifest_record.get("sha256"),
            metadata_=metadata,
        )
        session.add(document)
        await session.flush()
    else:
        document.title = manifest_record.get("title") or parsed_doc.title or path.stem
        document.lender = manifest_record.get("source")
        document.source_url = source_url
        document.licence = manifest_record.get("licence")
        document.doc_type = parsed_doc.kind
        document.sha256 = manifest_record.get("sha256")
        document.metadata_ = metadata

    await session.execute(delete(Page).where(Page.document_id == document.id))

    session.add_all(
        [
            Page(
                document_id=document.id,
                page_no=page.page_no,
                text=page.text,
                headings=page.headings,
            )
            for page in parsed_doc.pages
        ]
    )

    await session.execute(delete(ParseFailure).where(ParseFailure.path == str(path)))

    await session.flush()
    return document


async def store_parse_failure(
    session: AsyncSession,
    *,
    path: Path,
    manifest_record: dict,
    reason: str,
    detail: str,
) -> None:
    """Insert or update a failed document in the dead-letter table."""

    failure = await session.scalar(select(ParseFailure).where(ParseFailure.path == str(path)))

    if failure is None:
        session.add(
            ParseFailure(
                path=str(path),
                sha256=manifest_record.get("sha256"),
                source_url=manifest_record.get("url"),
                reason=reason[:40],
                detail=detail,
                attempts=1,
            )
        )
    else:
        failure.sha256 = manifest_record.get("sha256")
        failure.source_url = manifest_record.get("url")
        failure.reason = reason[:40]
        failure.detail = detail
        failure.attempts += 1

    await session.flush()
