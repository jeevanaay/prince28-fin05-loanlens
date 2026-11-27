"""ingest_jobs and ingest_items: the state of every queued document lives in Postgres.

Redis only carries "please handle item 42". If Redis loses its memory, the truth is still
here, and the worker can queue the unfinished items again.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from loanlens.db.models import Document, IngestItem, IngestJob, ParseFailure

OPEN = ("queued", "running")  # not finished yet


class IngestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def known_ids(self) -> set[str]:
        """Content identifiers already ingested or permanently rejected."""
        documents = await self.session.scalars(
            select(Document.sha256).where(Document.doc_type != "record")
        )
        failures = await self.session.scalars(select(ParseFailure.sha256))

        hashes = {value for value in documents if value}
        hashes.update(value for value in failures if value)

        return {f"f-{sha[:20]}" for sha in hashes}

    async def create(self, records: list[dict]) -> tuple[str, list[int]]:
        """One job, one item per manifest record. Returns the job id and the item ids."""
        job = IngestJob(id=uuid.uuid4().hex, requested=len(records))
        job.items = [IngestItem(record=record) for record in records]
        self.session.add(job)
        await self.session.commit()
        return job.id, [item.id for item in job.items]

    async def progress(self, job_id: str) -> dict | None:
        job = await self.session.get(IngestJob, job_id)
        if job is None:
            return None
        rows = await self.session.execute(
            select(IngestItem.status, func.count(), func.sum(IngestItem.pages))
            .where(IngestItem.job_id == job_id)
            .group_by(IngestItem.status)
        )
        counts = {"queued": 0, "running": 0, "done": 0, "skipped": 0, "failed": 0}
        pages = 0
        for status, count, page_sum in rows:
            counts[status] = count
            pages += int(page_sum or 0)
        last = await self.session.scalar(
            select(func.max(IngestItem.updated_at)).where(IngestItem.job_id == job_id)
        )
        finished = counts["queued"] + counts["running"] == 0
        end = last if finished and last else datetime.now(UTC)
        return {
            "job_id": job.id,
            "status": "finished" if finished else "working",
            "requested": job.requested,
            "counts": counts,
            "pages": pages,
            "seconds": round((end - job.created_at).total_seconds(), 1),
            "created_at": job.created_at.isoformat(),
            "dead_letter": await self.dead_letter(job_id=job_id, limit=20),
        }

    async def dead_letter(self, *, job_id: str | None = None, limit: int = 50) -> list[dict]:
        """Items that failed for good, newest first: the list a person has to look at."""
        stmt = select(IngestItem).where(IngestItem.status == "failed")
        if job_id:
            stmt = stmt.where(IngestItem.job_id == job_id)
        rows = await self.session.scalars(stmt.order_by(IngestItem.updated_at.desc()).limit(limit))
        return [
            {
                "item": row.id,
                "job_id": row.job_id,
                "url": row.record.get("url", ""),
                "path": row.record.get("path", ""),
                "attempts": row.attempts,
                "error": row.error,
            }
            for row in rows
        ]

    async def failed_records(self) -> list[dict]:
        """Approved, downloaded records in the dead-letter list, each URL once."""
        stmt = select(IngestItem.record).where(IngestItem.status == "failed")
        rows = await self.session.scalars(stmt.order_by(IngestItem.updated_at.desc()))

        eligible = {}
        for record in rows:
            if not isinstance(record, dict):
                continue

            url = record.get("url")
            evidence = record.get("collection_evidence")

            if (
                record.get("status") == "downloaded"
                and record.get("collection_status") == "approved"
                and isinstance(url, str)
                and url.strip()
                and isinstance(evidence, str)
                and evidence.strip()
            ):
                eligible[url] = record

        return list(eligible.values())

    async def open_item_ids(self) -> list[int]:
        """Items that should be in the queue. Used to queue them again after Redis lost them."""
        stmt = select(IngestItem.id).where(IngestItem.status.in_(OPEN)).order_by(IngestItem.id)
        return list(await self.session.scalars(stmt))
