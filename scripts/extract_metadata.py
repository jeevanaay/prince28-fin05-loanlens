"""Extract structured metadata from parsed LoanLens documents.

Examples:
  uv run python scripts/extract_metadata.py --limit 5
  uv run python scripts/extract_metadata.py
  uv run python scripts/extract_metadata.py --retry-failed
  uv run python scripts/extract_metadata.py --version extract_v1 --limit 5
"""

import argparse
import asyncio
import sys

from loanlens.config import get_settings
from loanlens.db.llm_calls import DatabaseRecorder
from loanlens.db.session import make_engine, make_sessionmaker
from loanlens.llm.extract import run
from loanlens.llm.gateway import build_gateway
from loanlens.llm.prompts import list_versions, load_prompt


def positive_int(value: str) -> int:
    """Validate positive integer arguments."""
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def non_negative_float(value: str) -> float:
    """Validate a non-negative RPM value."""
    number = float(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return number


async def main(args: argparse.Namespace) -> int:
    settings = get_settings()

    available = {path.stem for path in list_versions("extract")}

    if args.version not in available:
        print(
            f"Prompt {args.version!r} not found. "
            f"Available versions: {', '.join(sorted(available)) or 'none'}"
        )
        return 1

    version_number = int(args.version.rsplit("_v", 1)[1])
    prompt = load_prompt("extract", version_number)

    engine = make_engine(settings)
    session_factory = make_sessionmaker(engine)
    recorder = DatabaseRecorder(session_factory)
    gateway = build_gateway(settings, recorder=recorder)

    try:
        print(f"Prompt: {args.version}")
        print(f"Document limit: {args.limit or 'all pending documents'}")
        print(f"Retry failed only: {args.retry_failed}")
        print(f"Rate limit: {args.rpm:g} requests/minute")
        print("Starting metadata extraction...\n")

        stats = await run(
            session_factory,
            gateway,
            prompt,
            version=args.version,
            limit=args.limit,
            retry_failed=args.retry_failed,
            rpm=args.rpm,
        )

        print("\nExtraction summary")
        print("------------------")
        print(f"Documents selected: {stats['total']}")
        print(f"Successful:         {stats['ok']}")
        print(f"Repaired:           {stats['repaired']}")
        print(f"Failed:             {stats['failed']}")
        print(f"Input tokens:       {stats['tokens_in']}")
        print(f"Output tokens:      {stats['tokens_out']}")
        print(f"Estimated cost:     Rs {stats['cost_inr']:.6f}")

        return 0

    finally:
        await engine.dispose()


def main_cli() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        default="extract_v1",
        help="extraction prompt version (default: extract_v1)",
    )
    parser.add_argument(
        "--limit",
        type=positive_int,
        default=None,
        help="maximum number of documents to process",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="process failed extractions only",
    )
    parser.add_argument(
        "--rpm",
        type=non_negative_float,
        default=12,
        help="model requests per minute; use 0 to disable pacing",
    )

    args = parser.parse_args()
    return asyncio.run(main(args))


if __name__ == "__main__":
    raise SystemExit(main_cli())
