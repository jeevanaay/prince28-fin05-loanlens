from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def load_manifest(manifest_path: Path) -> list[dict]:
    records = []

    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return records


def load_sources(sources_path: Path) -> list[dict]:
    if not sources_path.exists():
        return []

    lines = [
        line
        for line in sources_path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    return list(csv.DictReader(lines))


def build_report(manifest_path: Path, raw_dir: Path) -> dict:
    records = load_manifest(manifest_path)

    downloaded = [
        record
        for record in records
        if record.get("status") == "downloaded"
        and record.get("path")
        and Path(record["path"]).is_file()
    ]

    blocked = [record for record in records if record.get("status") == "blocked"]

    total_bytes = sum(record.get("bytes", 0) for record in downloaded)

    source_counts = Counter(record.get("source", "Unknown") for record in downloaded)

    pdf_pages = 0

    for record in downloaded:
        path = Path(record["path"])
        try:
            with path.open("rb") as file:
                is_pdf = file.read(5) == b"%PDF-"

            if is_pdf:
                from pypdf import PdfReader

                pdf_pages += len(PdfReader(path).pages)
        except Exception:
            continue

    return {
        "manifest_records": len(records),
        "downloaded_files": len(downloaded),
        "blocked_records": len(blocked),
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 2),
        "pdf_pages": pdf_pages,
        "sources": dict(source_counts),
        "raw_directory": str(raw_dir),
        "raw_directory_exists": raw_dir.exists(),
    }


def build_markdown(
    report: dict,
    sources: list[dict],
    records: list[dict],
) -> str:
    # Group manifest records by URL. Prefer a successfully collected file.
    records_by_url: dict[str, list[dict]] = {}

    for record in records:
        records_by_url.setdefault(record.get("url", ""), []).append(record)

    source_counts: Counter = Counter()

    # Count only valid downloaded files, using source names from sources.csv.
    source_names = {source["url"]: source["source"] for source in sources}

    for record in records:
        path = record.get("path")
        if record.get("status") == "downloaded" and path and Path(path).is_file():
            source_name = source_names.get(
                record.get("url", ""),
                record.get("source", "Unknown"),
            )
            source_counts[source_name] += 1

    lines = [
        "## 6. Initial Collection Report",
        "",
        "Generated using `scripts/dataset_report.py`.",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Manifest entries | {report['manifest_records']} |",
        f"| Successfully downloaded documents | {report['downloaded_files']} |",
        f"| Blocked collection attempts | {report['blocked_records']} |",
        f"| Total downloaded size | {report['total_mb']:.2f} MB |",
        f"| PDF pages detected | {report['pdf_pages']} |",
        f"| Source organisations | {len(source_counts)} |",
        "",
        "### Source breakdown",
        "",
        "| Source | Downloaded documents |",
        "|---|---:|",
    ]

    for source, count in sorted(source_counts.items()):
        lines.append(f"| {source} | {count} |")

    lines.extend(
        [
            "",
            "### Source register and collection status",
            "",
            "| Source | Document | URL | Licence / reuse status | Collection status | Method |",
            "|---|---|---|---|---|---|",
        ]
    )

    for source in sources:
        url = source["url"]
        matching = records_by_url.get(url, [])

        valid_downloads = [
            record
            for record in matching
            if record.get("status") == "downloaded"
            and record.get("path")
            and Path(record["path"]).is_file()
        ]

        if valid_downloads:
            selected = valid_downloads[-1]
            status = "Downloaded"
            method = selected.get("via", "Unknown")
        elif matching:
            selected = matching[-1]
            status = selected.get("status", "Unknown").capitalize()
            method = selected.get("via", "Unknown")
        else:
            status = "Not attempted"
            method = "—"

        lines.append(
            f"| {source['source']} "
            f"| {source['title']} "
            f"| [Official source]({url}) "
            f"| {source['licence']} "
            f"| {status} "
            f"| {method} |"
        )

    lines.extend(
        [
            "",
            "### Known gaps",
            "",
            "- The initial collection contains only "
            f"{report['pdf_pages']} detected PDF pages; "
            "the expanded target is 1,500+ pages.",
            "- Some source requests were blocked because robots.txt "
            "disallowed crawling or could not be checked. "
            "These restrictions must not be bypassed.",
            "- Some documents were collected manually. "
            "Manual collection does not establish permission for "
            "automated crawling or redistribution.",
            "- Licence and reuse terms are not yet verified for "
            "several sources. Verify permissions before redistribution.",
            "- The current storage estimate is based on only "
            f"{report['downloaded_files']} downloaded documents.",
            "- Additional bank documents, FAQs, circulars and "
            "policy documents remain to be collected and reviewed.",
            "",
            "Raw documents are stored locally in `data/raw/` and excluded "
            "from Git. The committed `data/manifest.jsonl` records "
            "collection metadata and document hashes.",
            "",
            "These figures describe the current collection only. "
            "They do not represent the final target corpus.",
            "",
        ]
    )

    return "\n".join(lines)


def update_dataset_markdown(
    dataset_path: Path,
    generated_section: str,
) -> None:
    existing = dataset_path.read_text(encoding="utf-8") if dataset_path.exists() else ""

    marker = "## 6. Initial Collection Report"

    if marker in existing:
        existing = existing.split(marker, maxsplit=1)[0].rstrip()
    else:
        existing = existing.rstrip()

    content = f"{existing}\n\n{generated_section}"
    dataset_path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="LoanLens dataset report")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/manifest.jsonl"),
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
    )
    parser.add_argument(
        "--sources",
        type=Path,
        default=Path("data/sources.csv"),
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("DATASET.md"),
    )
    args = parser.parse_args()

    records = load_manifest(args.manifest)
    sources = load_sources(args.sources)
    report = build_report(args.manifest, args.raw_dir)

    markdown = build_markdown(report, sources, records)
    update_dataset_markdown(args.dataset, markdown)

    print(json.dumps(report, indent=2))
    print(f"\nUpdated Markdown report: {args.dataset}")


if __name__ == "__main__":
    main()
