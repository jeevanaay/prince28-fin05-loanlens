from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def build_report(manifest_path: Path, raw_dir: Path) -> dict:
    records = []

    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    downloaded = [
        record
        for record in records
        if record.get("status") == "downloaded"
        and record.get("path")
        and Path(record["path"]).is_file()
    ]

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
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 2),
        "pdf_pages": pdf_pages,
        "sources": dict(source_counts),
        "raw_directory": str(raw_dir),
        "raw_directory_exists": raw_dir.exists(),
    }


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
    args = parser.parse_args()

    report = build_report(args.manifest, args.raw_dir)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
