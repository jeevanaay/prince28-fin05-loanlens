"""Load data/sample_records.json into Postgres.

New records are inserted, changed records updated, and unchanged
records skipped using versioned SHA-256 fingerprints.

Use --test-db to explicitly target TEST_DATABASE_URL.
"""

import argparse
import asyncio
import hashlib
import json
from datetime import date
from typing import Any

from sqlalchemy import select, update

from loanlens.config import get_settings
from loanlens.db.models import Document
from loanlens.db.session import make_engine, make_sessionmaker

TITLE_FIELD = "lender"
FINGERPRINT_VERSION = 3

KNOWN = {
    "id",
    "title",
    "lender",
    "source_url",
    "licence",
    "doc_type",
    "published_on",
}


def fingerprint(record: dict[str, Any]) -> str:
    """Generate a stable, versioned SHA-256 fingerprint."""
    canonical = json.dumps(
        {
            "loader_version": FINGERPRINT_VERSION,
            "record": record,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def to_row(record: dict[str, Any]) -> dict[str, Any]:
    """Convert a JSON record into a database row with pruned metadata."""
    published = record.get("published_on")

    metadata = {
        key: value for key, value in record.items() if key not in KNOWN and value is not None
    }

    lender = record.get("lender")

    return {
        "external_id": str(record["id"]),
        "title": str(record.get("title") or lender or record["id"]),
        "lender": str(lender) if lender is not None else None,
        "source_url": record.get("source_url"),
        "licence": record.get("licence"),
        "doc_type": record.get("doc_type") or "record",
        "published_on": date.fromisoformat(published) if published else None,
        "sha256": fingerprint(record),
        "metadata_": metadata,
    }


async def main(use_test_db: bool = False) -> None:
    settings = get_settings()

    if use_test_db:
        if not settings.test_database_url:
            raise RuntimeError(
                "TEST_DATABASE_URL is not configured. Refusing to use the production database."
            )

        settings = settings.model_copy(update={"database_url": settings.test_database_url})

        print("Database target: TEST DATABASE")

    else:
        print("Database target: DATABASE_URL")

    records = json.loads(settings.data_file.read_text(encoding="utf-8"))

    engine = make_engine(settings)
    session_factory = make_sessionmaker(engine)

    inserted = updated = unchanged = 0

    try:
        async with session_factory() as session, session.begin():
            rows = await session.execute(select(Document.external_id, Document.sha256))
            existing = dict(rows.all())

            for record in records:
                row = to_row(record)
                old_hash = existing.get(row["external_id"])

                if old_hash is None:
                    session.add(Document(**row))
                    inserted += 1

                elif old_hash != row["sha256"]:
                    await session.execute(
                        update(Document)
                        .where(Document.external_id == row["external_id"])
                        .values(**row)
                    )
                    updated += 1

                else:
                    unchanged += 1

    finally:
        await engine.dispose()

    print(f"records={len(records)} inserted={inserted} updated={updated} unchanged={unchanged}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load LoanLens records.")
    parser.add_argument(
        "--test-db",
        action="store_true",
        help="Use TEST_DATABASE_URL instead of DATABASE_URL.",
    )
    args = parser.parse_args()

    asyncio.run(main(use_test_db=args.test_db))
