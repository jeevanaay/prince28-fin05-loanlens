from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from loanlens.config import get_settings
from loanlens.db.session import make_engine, make_sessionmaker
from loanlens.ingest.fetch import Manifest
from loanlens.ingest.parse import parse_file
from loanlens.ingest.store import (
    store_parse_failure,
    store_parsed_document,
)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Parse and store LoanLens documents")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--parser", choices=["pymupdf", "pypdf"], default="pymupdf")
    args = parser.parse_args()

    manifest = Manifest(Path("data/manifest.jsonl"))

    records = [
        record
        for record in manifest.records.values()
        if record.get("status") == "downloaded"
        and record.get("path")
        and Path(record["path"]).is_file()
    ]

    if args.limit > 0:
        records = records[: args.limit]

    print(f"Found {len(records)} downloaded files.")

    settings = get_settings()
    engine = make_engine(settings)
    session_factory = make_sessionmaker(engine)

    succeeded = 0
    failed = 0

    try:
        async with session_factory() as session:
            for record in records:
                path = Path(record["path"])
                print(f"\nProcessing: {record.get('title', path.name)}")

                try:
                    parsed = parse_file(path, parser=args.parser)

                    async with session.begin():
                        await store_parsed_document(
                            session,
                            path=path,
                            manifest_record=record,
                            parsed_doc=parsed,
                        )

                    succeeded += 1
                    print(f"  Stored {len(parsed.pages)} pages using {parsed.parser}.")

                except Exception as exc:
                    reason = getattr(exc, "reason", type(exc).__name__)
                    detail = getattr(exc, "detail", str(exc))

                    async with session.begin():
                        await store_parse_failure(
                            session,
                            path=path,
                            manifest_record=record,
                            reason=str(reason),
                            detail=str(detail),
                        )

                    failed += 1
                    print(f"  FAILED: {reason} - {detail}")

    finally:
        await engine.dispose()

    print("\n--- Ingestion summary ---")
    print(f"Successful: {succeeded}")
    print(f"Failed:     {failed}")
    print(f"Total:      {succeeded + failed}")


if __name__ == "__main__":
    asyncio.run(main())
