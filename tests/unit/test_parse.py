from pathlib import Path

import pymupdf

from loanlens.ingest.parse import parse_html, parse_pdf


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


def test_pdf_same_line_numbered_bold_heading(tmp_path: Path):
    path = tmp_path / "same-line-heading.pdf"

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "2. Loan terms", fontname="hebo")
    page.insert_text(
        (72, 100),
        "This document contains enough text for parsing.",
        fontname="helv",
    )
    document.save(path)
    document.close()

    parsed = parse_pdf(path)

    assert parsed.pages[0].headings == ["Loan terms"]


def test_pdf_bold_heading_label_with_regular_value(tmp_path: Path):
    path = tmp_path / "bold-label.pdf"

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "6. Margin:", fontname="hebo")
    page.insert_text((120, 72), "10%", fontname="helv")
    page.insert_text(
        (72, 100),
        "Scholarship and assistantship are included in margin.",
        fontname="helv",
    )
    document.save(path)
    document.close()

    parsed = parse_pdf(path)

    assert parsed.pages[0].headings == ["Margin:"]


def test_pdf_extracts_prominent_first_page_title(tmp_path: Path):
    path = tmp_path / "title-test.pdf"

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text(
        (150, 45),
        "SBI GLOBAL ED-VANTAGE SCHEME",
        fontname="hebo",
        fontsize=16,
    )
    page.insert_text(
        (140, 65),
        "MOST IMPORTANT TERMS AND CONDITIONS",
        fontname="hebo",
        fontsize=16,
    )
    page.insert_text(
        (72, 100),
        "1. Purpose for which the loan can be availed:",
        fontname="hebo",
        fontsize=8,
    )
    page.insert_text(
        (72, 120),
        "Loans will be granted to deserving students.",
        fontname="helv",
        fontsize=8,
    )
    document.save(path)
    document.close()

    parsed = parse_pdf(path)

    assert parsed.title == "SBI GLOBAL ED-VANTAGE SCHEME"


def test_html_uses_main_heading_as_document_title(tmp_path: Path):
    path = tmp_path / "global-ed-vantage.html"

    content = b"""
    <html>
        <head>
            <title>Apply Online in India | SBI - Personal Banking</title>
        </head>
        <body>
            <main>
                <h1>Global Ed-Vantage Education Loan</h1>
                <h2>Eligibility</h2>
                <p>
                    Global Ed-Vantage provides education loans for students
                    pursuing higher education abroad. Applicants can review
                    eligibility criteria and loan terms before applying.
                </p>
            </main>
        </body>
    </html>
    """

    parsed = parse_html(path, content)

    assert parsed.title == "Global Ed-Vantage Education Loan"
    assert "Eligibility" in parsed.pages[0].headings
    assert "higher education abroad" in parsed.pages[0].text
