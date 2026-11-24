from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

from loanlens.ingest.fetch import (
    Manifest,
    ManifestRecord,
    Robots,
    fetch_all,
    make_client,
    safe_filename,
    utc_now,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "data" / "raw"
DEFAULT_MANIFEST = ROOT / "data" / "manifest.jsonl"
DEFAULT_CSV = ROOT / "data" / "sources.csv"


def read_sources(path: Path) -> list[dict[str, str]]:
    """Read source rows, ignoring blank and comment lines."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        lines = (line for line in handle if line.strip() and not line.lstrip().startswith("#"))
        reader = csv.DictReader(lines)

        required = {
            "url",
            "source",
            "licence",
            "title",
            "collection_status",
            "collection_evidence",
        }
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"CSV must contain columns: {sorted(required)}")

        items = []
        for row in reader:
            item = {key: (row.get(key) or "").strip() for key in required}

            if not item["url"]:
                continue

            if item["collection_status"] not in {
                "approved",
                "pending",
                "blocked",
            }:
                raise ValueError(f"Invalid collection_status for {item['url']}")

            if not item["collection_evidence"]:
                raise ValueError(f"Missing collection_evidence for {item['url']}")

            items.append(item)

    return items


def require_collection_approval(args: argparse.Namespace) -> None:
    """Require explicit approval and supporting evidence before collection."""
    status = args.collection_status.strip().lower()
    evidence = args.collection_evidence.strip()

    if status != "approved":
        raise PermissionError("Collection blocked: collection_status must be 'approved'.")

    if not evidence:
        raise PermissionError("Collection blocked: collection_evidence must not be empty.")


async def collect_urls(args: argparse.Namespace) -> None:
    items = read_sources(args.csv)
    results = await fetch_all(
        items,
        raw_dir=args.raw_dir,
        manifest_path=args.manifest,
        concurrency=args.concurrency,
        per_host_delay=args.delay,
    )
    for result in results:
        print(f"{result.status:10} {result.title} — {result.url}")


async def sitemap_urls(url: str) -> list[str]:
    """Read a sitemap or sitemap index while respecting robots.txt."""
    async with make_client() as client:
        robots = Robots(client)
        allowed, _ = await robots.allowed(url)
        if not allowed:
            raise PermissionError(f"Sitemap is disallowed or robots.txt unavailable: {url}")

        response = await client.get(url)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        sitemap_locations = [
            node.text for node in root.findall(".//sm:sitemap/sm:loc", namespace) if node.text
        ]

        if sitemap_locations:
            collected = []
            for child_url in sitemap_locations:
                collected.extend(await sitemap_urls(child_url))
            return collected

        return [node.text for node in root.findall(".//sm:url/sm:loc", namespace) if node.text]


async def collect_sitemap(args: argparse.Namespace) -> None:
    require_collection_approval(args)

    urls = await sitemap_urls(args.url)
    extensions = {".pdf", ".doc", ".docx"}

    items = [
        {
            "url": url,
            "source": args.source,
            "licence": args.licence,
            "title": Path(urlsplit(url).path).name or url,
            "collection_status": args.collection_status,
            "collection_evidence": args.collection_evidence,
        }
        for url in urls
        if Path(urlsplit(url).path).suffix.lower() in extensions
    ]

    print(f"Found {len(items)} document URLs in sitemap.")
    if not items:
        return

    results = await fetch_all(
        items,
        raw_dir=args.raw_dir,
        manifest_path=args.manifest,
        concurrency=args.concurrency,
        per_host_delay=args.delay,
    )
    for result in results:
        print(f"{result.status:10} {result.title}")


def register_manual(args: argparse.Namespace) -> None:
    """Register a manually downloaded document after approval."""
    require_collection_approval(args)

    source_file = args.file.resolve()
    if not source_file.is_file():
        raise FileNotFoundError(source_file)

    args.raw_dir.mkdir(parents=True, exist_ok=True)
    destination = args.raw_dir / safe_filename(args.url)
    shutil.copy2(source_file, destination)

    content_hash = hashlib.sha256(destination.read_bytes()).hexdigest()

    record = ManifestRecord(
        url=args.url,
        source=args.source,
        licence=args.licence,
        title=args.title,
        status="downloaded",
        fetched_at=utc_now(),
        path=str(destination),
        sha256=content_hash,
        bytes=destination.stat().st_size,
        via="manual",
        collection_status=args.collection_status,
        collection_evidence=args.collection_evidence,
    )

    Manifest(args.manifest).add(record)
    print(f"Registered manual document: {destination}")


def collect_repo(args: argparse.Namespace) -> None:
    """Clone and register repository PDFs after explicit approval."""
    require_collection_approval(args)

    args.raw_dir.mkdir(parents=True, exist_ok=True)
    manifest = Manifest(args.manifest)

    with tempfile.TemporaryDirectory(prefix="loanlens-repo-") as temporary:
        checkout = Path(temporary) / "repository"

        subprocess.run(
            ["git", "clone", "--depth", "1", args.url, str(checkout)],
            check=True,
            capture_output=True,
            text=True,
            timeout=args.timeout,
        )

        documents = sorted(checkout.rglob("*.pdf"))
        print(f"Found {len(documents)} PDF files.")

        for source_file in documents:
            relative = source_file.relative_to(checkout)
            document_url = f"{args.url.rstrip('/')}/{relative.as_posix()}"
            destination = args.raw_dir / safe_filename(document_url)

            shutil.copy2(source_file, destination)

            content = destination.read_bytes()
            record = ManifestRecord(
                url=document_url,
                source=args.source,
                licence=args.licence,
                title=source_file.name,
                status="downloaded",
                fetched_at=utc_now(),
                path=str(destination),
                sha256=hashlib.sha256(content).hexdigest(),
                bytes=len(content),
                via="repo",
                collection_status=args.collection_status,
                collection_evidence=args.collection_evidence,
            )

            manifest.add(record)
            print(f"Registered: {relative}")


def add_collection_arguments(command: argparse.ArgumentParser) -> None:
    """Add explicit collection eligibility arguments to a command."""
    command.add_argument(
        "--collection-status",
        choices=["approved", "pending", "blocked"],
        default="pending",
        help="Collection eligibility; defaults to pending.",
    )
    command.add_argument(
        "--collection-evidence",
        required=True,
        help="Evidence supporting the collection eligibility decision.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LoanLens document collection")
    subparsers = parser.add_subparsers(dest="door", required=True)

    urls = subparsers.add_parser(
        "urls",
        help="Fetch URLs from sources.csv",
    )
    urls.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    urls.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    urls.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    urls.add_argument("--concurrency", type=int, default=4)
    urls.add_argument("--delay", type=float, default=0.5)
    urls.set_defaults(func=collect_urls)

    sitemap = subparsers.add_parser(
        "sitemap",
        help="Collect PDFs from a sitemap",
    )
    sitemap.add_argument("url")
    sitemap.add_argument("--source", default="Sitemap source")
    sitemap.add_argument(
        "--licence",
        default="Reuse terms to be verified",
    )
    sitemap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    sitemap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    sitemap.add_argument("--concurrency", type=int, default=4)
    sitemap.add_argument("--delay", type=float, default=0.5)
    add_collection_arguments(sitemap)
    sitemap.set_defaults(func=collect_sitemap)

    repo = subparsers.add_parser(
        "repo",
        help="Collect PDFs from a public Git repository",
    )
    repo.add_argument("url")
    repo.add_argument("--source", default="Git repository")
    repo.add_argument(
        "--licence",
        default="Repository licence to be verified",
    )
    repo.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    repo.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    repo.add_argument("--timeout", type=int, default=120)
    add_collection_arguments(repo)
    repo.set_defaults(func=collect_repo)

    manual = subparsers.add_parser(
        "manual",
        help="Register a manually downloaded document",
    )
    manual.add_argument("file", type=Path)
    manual.add_argument("--url", required=True)
    manual.add_argument("--source", required=True)
    manual.add_argument("--licence", required=True)
    manual.add_argument("--title", required=True)
    manual.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    manual.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    add_collection_arguments(manual)
    manual.set_defaults(func=register_manual)

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.door in {"urls", "sitemap"}:
        asyncio.run(args.func(args))
    else:
        args.func(args)


if __name__ == "__main__":
    main()
