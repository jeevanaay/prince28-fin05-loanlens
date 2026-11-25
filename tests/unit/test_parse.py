from pathlib import Path

import pymupdf

from loanlens.ingest.parse import parse_pdf


def test_pdf_heading_hierarchy_and_continuation(tmp_path: Path):
    path = tmp_path / "heading-test.pdf"

    document = pymupdf.open()

    first = document.new_page()
    first.insert_text((72, 72), "1.", fontname="helv")
    first.insert_text((72, 90), "Introduction", fontname="hebo")
    first.insert_text((72, 120), "1.1.", fontname="helv")
    first.insert_text((72, 138), "Eligibility", fontname="hebo")
    first.insert_text(
        (72, 170),
        "1.1.1. Applicants must meet the eligibility criteria.",
        fontname="helv",
    )

    second = document.new_page()
    second.insert_text(
        (72, 72),
        "Applicants must submit the required documents.",
        fontname="helv",
    )

    document.save(path)
    document.close()

    parsed = parse_pdf(path)

    assert len(parsed.pages) == 2
    assert parsed.pages[0].headings == ["Introduction", "Eligibility"]
    assert parsed.pages[1].headings == ["Introduction", "Eligibility"]
    assert "Applicants must meet the eligibility criteria." in parsed.pages[0].text
    assert "1.1.1. Applicants" not in parsed.pages[0].headings


def test_pdf_same_line_numbered_bold_heading(tmp_path: Path):
    path = tmp_path / "same-line-heading.pdf"

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "2. Loan terms", fontname="hebo")
    page.insert_text((72, 100), "This document contains enough text for parsing.", fontname="helv")
    document.save(path)
    document.close()

    parsed = parse_pdf(path)

    assert parsed.pages[0].headings == ["Loan terms"]
