import json
from pathlib import Path

from scripts.dataset_report import (
    build_markdown,
    build_report,
    update_dataset_markdown,
)


def test_build_report_counts_downloaded_and_blocked(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    document = raw_dir / "sample.pdf"
    document.write_bytes(b"%PDF-invalid-test-content")

    manifest = tmp_path / "manifest.jsonl"
    records = [
        {
            "url": "https://example.com/sample.pdf",
            "source": "Example Bank",
            "title": "Sample Document",
            "status": "downloaded",
            "path": str(document),
            "bytes": document.stat().st_size,
        },
        {
            "url": "https://blocked.example.com/sample.pdf",
            "source": "Blocked Source",
            "title": "Blocked Document",
            "status": "blocked",
            "path": None,
            "bytes": 0,
        },
    ]

    manifest.write_text(
        "\n".join(json.dumps(record) for record in records),
        encoding="utf-8",
    )

    report = build_report(manifest, raw_dir)

    assert report["manifest_records"] == 2
    assert report["downloaded_files"] == 1
    assert report["blocked_records"] == 1
    assert report["total_bytes"] == document.stat().st_size
    assert report["sources"] == {"Example Bank": 1}


def test_build_markdown_includes_licence_status_and_known_gaps(
    tmp_path: Path,
):
    document = tmp_path / "sample.pdf"
    document.write_bytes(b"%PDF-invalid-test-content")

    sources = [
        {
            "url": "https://example.com/sample.pdf",
            "source": "Example Bank",
            "title": "Sample Document",
            "licence": "Reuse terms to be verified",
        }
    ]

    records = [
        {
            "url": "https://example.com/sample.pdf",
            "source": "Example Bank",
            "title": "Sample Document",
            "status": "downloaded",
            "path": str(document),
            "via": "manual",
        }
    ]

    report = {
        "manifest_records": 1,
        "downloaded_files": 1,
        "blocked_records": 0,
        "total_mb": 0.01,
        "pdf_pages": 0,
        "sources": {"Example Bank": 1},
    }

    markdown = build_markdown(report, sources, records)

    assert "Licence / reuse status" in markdown
    assert "Reuse terms to be verified" in markdown
    assert "Downloaded" in markdown
    assert "manual" in markdown
    assert "### Known gaps" in markdown
    assert "robots.txt" in markdown


def test_update_dataset_markdown_preserves_research_sections(
    tmp_path: Path,
):
    dataset = tmp_path / "DATASET.md"
    dataset.write_text(
        "# LoanLens Dataset\n\nResearch notes.\n\n## 6. Initial Collection Report\n\nOld report.\n",
        encoding="utf-8",
    )

    update_dataset_markdown(dataset, "## 6. Initial Collection Report\n\nNew report.")

    content = dataset.read_text(encoding="utf-8")

    assert "# LoanLens Dataset" in content
    assert "Research notes." in content
    assert "New report." in content
    assert "Old report." not in content
