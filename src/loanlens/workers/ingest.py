"""One job = one document: get the file, parse it, extract its record, store everything.

A job can run twice (the worker died, or a retry). That is safe, because every step first
checks what is already in the database: a document is identified by its content hash.
"""

import asyncio
import hashlib
import logging
import re
import tempfile
import time
from pathlib import Path

import httpx
from arq import Retry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from loanlens.db.models import Document, IngestItem, Page
from loanlens.ingest.fetch import HostGate, Manifest, Robots, fetch_one
from loanlens.ingest.parse import ParseError, parse_file
from loanlens.ingest.store import store_parse_failure, store_parsed_document
from loanlens.llm.extract import document_text, extract, save

logger = logging.getLogger("loanlens.worker")
GITHUB_BLOB = re.compile(r"^https://github\.com/([^/]+/[^/]+)/blob/[^/]+/(.+)$")


class Permanent(Exception):
    """This document will never work, however often we try: no retry, straight to the list."""


def plan(
    records: list[dict], done_ids: set[str], *, source: str = "", limit: int = 0
) -> list[dict]:
    """Select downloaded records whose content identifiers are not already known."""
    todo, seen = [], set(done_ids)

    for record in records:
        if record.get("status") != "downloaded":
            continue
        if source and record.get("source") != source:
            continue

        content_id = f"f-{record['sha256'][:20]}"
        if content_id in seen:
            continue

        seen.add(content_id)
        todo.append(record)

    return todo[:limit] if limit else todo


def raw_url(record: dict) -> str:
    """Where a worker without your laptop's files can download this document."""
    match = GITHUB_BLOB.match(record["url"])
    if record.get("via") == "git" and match and record.get("commit"):
        return f"https://raw.githubusercontent.com/{match[1]}/{record['commit']}/{match[2]}"
    return record["url"]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class Pace:
    """At most `per_minute` passes a minute, shared by all jobs of this worker (backpressure)."""

    def __init__(self, per_minute: float, clock=time.monotonic, sleep=asyncio.sleep) -> None:
        self._gap, self._clock, self._sleep = 60 / per_minute, clock, sleep
        self._next = 0.0

    async def wait(self) -> None:
        now = self._clock()
        delay = max(0.0, self._next - now)
        self._next = max(now, self._next) + self._gap
        if delay:
            await self._sleep(delay)


async def get_file(
    record: dict, folder: Path, client: httpx.AsyncClient, sleep=asyncio.sleep
) -> Path:
    """Use a local file if present; otherwise use the project's polite fetcher."""

    # Approval is required whether the file is local or downloaded.
    evidence = record.get("collection_evidence")
    if (
        record.get("collection_status") != "approved"
        or not isinstance(evidence, str)
        or not evidence.strip()
    ):
        raise Permanent("collection blocked: approval status or supporting evidence is missing")

    path = Path(record["path"])

    if path.is_file():
        return path

    if record.get("via") == "manual":
        raise Permanent("downloaded by hand: this file exists only on the laptop that has it")

    item = {
        "url": raw_url(record),
        "source": record["source"],
        "licence": record.get("licence") or "unknown",
        "title": record.get("title") or "",
        "collection_status": record.get("collection_status", "pending"),
        "collection_evidence": record.get("collection_evidence", ""),
    }

    manifest = Manifest(folder / "manifest.jsonl")
    robots = Robots(client)
    gate = HostGate()
    semaphore = asyncio.Semaphore(1)

    try:
        fetched = await fetch_one(
            item,
            client=client,
            robots=robots,
            gate=gate,
            semaphore=semaphore,
            manifest=manifest,
            raw_dir=folder,
        )

        if fetched.status != "downloaded" or not fetched.path:
            message = fetched.error or f"Download ended with status: {fetched.status}"

            if fetched.status == "blocked" or "404" in message:
                raise Permanent(message)

            raise RuntimeError(message)

        return Path(fetched.path)
    except Exception as exc:
        message = str(exc)
        if "blocked" in message.lower() or "approval" in message.lower():
            raise Permanent(message) from exc
        raise


async def process(ctx: dict, session: AsyncSession, item: IngestItem) -> tuple[str, int]:
    """Do the work for one item. Returns (status, pages). Raises to ask for a retry."""
    record = dict(item.record)

    with tempfile.TemporaryDirectory() as folder:
        path = await get_file(record, Path(folder), ctx["http"])
        record["sha256"] = await asyncio.to_thread(sha256_of, path)

        # Content hash prevents storing identical files from different URLs twice.
        document = await session.scalar(select(Document).where(Document.sha256 == record["sha256"]))

        status = "skipped"
        if document is None:
            try:
                parsed = await asyncio.to_thread(parse_file, path)
            except ParseError as error:
                await store_parse_failure(
                    session,
                    path=path,
                    manifest_record=record,
                    reason=error.reason,
                    detail=error.detail,
                )
                # Preserve the failure record before Permanent triggers a rollback.
                await session.commit()
                raise Permanent(f"parse: {error.reason}") from error

            document = await store_parsed_document(
                session,
                path=path,
                manifest_record=record,
                parsed_doc=parsed,
            )
            status = "done"

    pages = int(document.metadata_.get("page_count", 0))
    task = ctx.get("extract")
    note = document.metadata_.get("extract") or {}

    if task and (note.get("prompt") != task["version"] or note.get("status") == "error"):
        await ctx["pace"].wait()
        pages_result = await session.scalars(
            select(Page).where(Page.document_id == document.id).order_by(Page.page_no)
        )
        text = document_text(list(pages_result.all()), task["chars"])

        result = await extract(
            ctx["gateway"],
            task["prompt"],
            task["version"],
            text,
        )

        await save(
            session,
            document,
            result,
            version=task["version"],
        )

        if result.record is None:
            detail = result.errors[-1][:200] if result.errors else "no record returned"
            raise Permanent(f"extract: {detail}")

        status = "done"
    return status, pages


async def ingest_document(ctx: dict, item_id: int) -> str:
    """The function the worker runs for every queued item. It never loses an item silently."""
    max_tries = ctx["settings"].ingest_max_tries
    async with ctx["sessionmaker"]() as session:
        item = await session.get(IngestItem, item_id)
        if item is None or item.status not in ("queued", "running"):
            return "ignored"  # unknown, already finished, or deliberately stopped
        if item.attempts >= max_tries:  # started that often and never finished: the worker died
            item.status = "failed"
            item.error = f"gave up: started {item.attempts} times and never finished"
            await session.commit()
            return "failed"
        item.status, item.attempts = "running", item.attempts + 1
        attempt = item.attempts  # counted in Postgres, so it survives a dead worker
        await session.commit()
        try:
            item.status, item.pages = await process(ctx, session, item)
            item.error = ""
        except Permanent as error:  # a poison message: retrying would only waste the queue
            await session.rollback()
            item.status, item.error = "failed", str(error)[:500]
        except Exception as error:
            await session.rollback()
            reason = f"{type(error).__name__}: {error}"[:500]
            if attempt >= max_tries:
                item.status, item.error = "failed", f"gave up after {attempt} tries: {reason}"
            else:
                item.status, item.error = "queued", f"try {attempt} failed: {reason}"
                await session.commit()
                logger.warning("item %s will be retried: %s", item_id, reason)
                raise Retry(defer=attempt * 30) from error  # in 30 s, then 60 s, then give up
        await session.commit()
        logger.info("item %s %s", item_id, item.status)
        return item.status
