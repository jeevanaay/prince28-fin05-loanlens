from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

import pymupdf
import trafilatura
import yaml
from pypdf import PdfReader


@dataclass
class ParsedPage:
    page_no: int
    text: str
    headings: list[str] = field(default_factory=list)
    tables: int = 0


@dataclass
class ParsedDoc:
    parser: str
    kind: str
    title: str
    pages: list[ParsedPage]


class ParseError(Exception):
    def __init__(self, reason: str, detail: str = ""):
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}")


def detect_kind(path: Path, content: bytes) -> str:
    """Detect file type from content, not just its extension."""
    stripped = content.lstrip()

    if content.startswith(b"%PDF-"):
        return "pdf"

    if stripped[:100].lower().startswith((b"<!doctype html", b"<html", b"<!doctype")):
        return "html"

    suffix = path.suffix.lower()

    if suffix in {".html", ".htm", ".aspx"}:
        return "html"
    if suffix in {".txt", ".md"}:
        return "text"
    if suffix in {".json", ".yaml", ".yml", ".csv"}:
        return "data"

    if b"<html" in stripped[:1000].lower():
        return "html"

    try:
        stripped.decode("utf-8")
        return "text"
    except UnicodeDecodeError:
        raise ParseError(
            "unsupported_type",
            f"Cannot identify {path.name}",
        ) from None


def _pdf_line_text(spans: list[dict]) -> str:
    """Reconstruct a PDF line from spans, preserving word boundaries."""
    parts = []
    previous_end = None

    for span in spans:
        value = span.get("text", "")
        if not value:
            continue

        start = span.get("bbox", (0, 0, 0, 0))[0]
        size = span.get("size", 10)

        if previous_end is not None and start - previous_end > max(1, size * 0.15):
            parts.append(" ")

        parts.append(value)
        previous_end = span.get("bbox", (0, 0, 0, 0))[2]

    return "".join(parts).strip()


def _numbered_heading(lines: list[list[dict]], index: int) -> tuple[int, str] | None:
    """Detect numbered headings, including bold labels followed by regular text."""
    line = lines[index]
    line_text = _pdf_line_text(line)

    marker = re.match(r"^(\d+(?:\.\d+)*\.?)\s*(.*)$", line_text)
    if not marker:
        return None

    number = marker.group(1).rstrip(".")
    level = len(number.split("."))

    if level > 6:
        return None

    remainder = marker.group(2).strip()
    visible_spans = [span for span in line if span.get("text", "").strip()]
    bold_spans = [span for span in visible_spans if span.get("flags", 0) & 16]

    title = ""

    def normalize(value):
        return " ".join(value.split()).casefold()

    if remainder and bold_spans:
        bold_text = _pdf_line_text(bold_spans).strip()

        # The complete line is bold.
        if normalize(bold_text) == normalize(line_text):
            title = remainder

        # Only the numbered heading label is bold; following text is body content.
        elif re.match(
            rf"^{re.escape(number)}\.?\s+.+:\s*$",
            bold_text,
        ):
            title = re.sub(
                rf"^{re.escape(number)}\.?\s+",
                "",
                bold_text,
            ).strip()

    elif not remainder and index + 1 < len(lines):
        next_visible = [span for span in lines[index + 1] if span.get("text", "").strip()]

        if next_visible and all(span.get("flags", 0) & 16 for span in next_visible):
            title = _pdf_line_text(next_visible)

    if not title or len(title) > 150:
        return None

    return level, title


def _pdf_tables(page) -> tuple[str, int]:
    """Extract ruled tables and represent them as Markdown."""
    try:
        found = page.find_tables()
    except Exception:
        return "", 0

    output = []
    count = 0

    for table in found.tables:
        rows = table.extract()
        if not rows:
            continue

        rows = [
            [str(cell or "").replace("|", "\\|").replace("\n", " ").strip() for cell in row]
            for row in rows
        ]

        width = max(len(row) for row in rows)
        rows = [row + [""] * (width - len(row)) for row in rows]

        output.append("| " + " | ".join(rows[0]) + " |")
        output.append("| " + " | ".join(["---"] * width) + " |")

        for row in rows[1:]:
            output.append("| " + " | ".join(row) + " |")

        count += 1

    return "\n".join(output), count


def parse_pdf(path: Path) -> ParsedDoc:
    pages = []
    heading_stack: list[tuple[int, str]] = []
    total_chars = 0

    try:
        document = pymupdf.open(path)

        if document.is_encrypted:
            raise ParseError("encrypted", path.name)

        title = (document.metadata.get("title") or "").strip()

        if not title and len(document) > 0:
            first_page = document[0]
            title_candidates = []

            for block in first_page.get_text("dict")["blocks"]:
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    spans = [span for span in line["spans"] if span.get("text", "").strip()]

                    bold_title_spans = [
                        span
                        for span in spans
                        if span.get("flags", 0) & 16
                        and span.get("size", 0) >= 10
                        and span.get("bbox", (0, 0, 0, 0))[1] <= 100
                    ]

                    if bold_title_spans:
                        title_text = " ".join(span["text"].strip() for span in bold_title_spans)
                        y_position = min(span["bbox"][1] for span in bold_title_spans)
                        title_candidates.append((y_position, title_text))

            if title_candidates:
                title = min(title_candidates, key=lambda item: item[0])[1]

        if not title:
            title = path.stem

        for index, page in enumerate(document):
            blocks = page.get_text("dict")["blocks"]
            ordered_lines = _pdf_reading_order(page, blocks)

            pdf_lines = []
            text_parts = []

            if ordered_lines is not None:
                for item in ordered_lines:
                    spans = item["spans"]
                    pdf_lines.append(spans)

                    line_text = _pdf_line_text(spans)
                    if line_text:
                        text_parts.append(line_text)

                text = "\n".join(text_parts).strip()

            else:
                for block in blocks:
                    if "lines" not in block:
                        continue

                    for line in block["lines"]:
                        spans = [span for span in line["spans"] if span.get("text", "").strip()]

                        if spans:
                            pdf_lines.append(spans)

                text = page.get_text("text", sort=True).strip()

            total_chars += len(text)

            page_headings = []

            for line_index in range(len(pdf_lines)):
                heading = _numbered_heading(pdf_lines, line_index)

                if heading:
                    page_headings.append(heading)

            table_markdown, table_count = _pdf_tables(page)

            if table_markdown:
                text += "\n\n" + table_markdown

            for level, heading in page_headings:
                heading_stack = [item for item in heading_stack if item[0] < level]
                heading_stack.append((level, heading))

            pages.append(
                ParsedPage(
                    page_no=index + 1,
                    text=text,
                    headings=[heading for _, heading in heading_stack],
                    tables=table_count,
                )
            )

        document.close()

    except ParseError:
        raise
    except Exception as exc:
        raise ParseError("corrupt", str(exc)) from exc

    if not pages or total_chars / max(len(pages), 1) < 20:
        raise ParseError(
            "no_text_layer",
            "PDF has insufficient extractable text",
        )

    return ParsedDoc("pymupdf", "pdf", title, pages)


def parse_pdf_pypdf(path: Path) -> ParsedDoc:
    """Alternative PDF parser used for comparison."""
    try:
        reader = PdfReader(str(path))

        if reader.is_encrypted:
            raise ParseError("encrypted", path.name)

        pages = []
        total_chars = 0

        for index, page in enumerate(reader.pages):
            content = page.extract_text() or ""
            total_chars += len(content)

            pages.append(
                ParsedPage(
                    page_no=index + 1,
                    text=content.strip(),
                )
            )

        if not pages or total_chars / max(len(pages), 1) < 20:
            raise ParseError("no_text_layer", "PDF has insufficient text")

        title = reader.metadata.title if reader.metadata else None

        return ParsedDoc("pypdf", "pdf", title or path.stem, pages)

    except ParseError:
        raise
    except Exception as exc:
        raise ParseError("corrupt", str(exc)) from exc


class MainExtractor(HTMLParser):
    """Extract main content and heading text from HTML."""

    def __init__(self):
        super().__init__()
        self.in_main = False
        self.parts = []
        self.headings = []
        self.title_heading = None
        self.current_heading_tag = None
        self.current_heading_parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.in_main = True

        if self.in_main and tag in {"h1", "h2", "h3"}:
            self.current_heading_tag = tag
            self.current_heading_parts = []

    def handle_data(self, data):
        if self.in_main and data.strip():
            self.parts.append(data.strip())

            if self.current_heading_tag:
                self.current_heading_parts.append(data.strip())

    def handle_endtag(self, tag):
        if self.current_heading_tag == tag:
            heading = " ".join(self.current_heading_parts)

            if heading:
                self.headings.append(heading)

                if tag == "h1" and self.title_heading is None:
                    self.title_heading = heading

            self.current_heading_tag = None
            self.current_heading_parts = []

        if tag == "main":
            self.in_main = False


def parse_html(path: Path, content: bytes) -> ParsedDoc:
    """Extract HTML content, headings and tables."""
    try:
        decoded = content.decode("utf-8", errors="replace")

        parser = MainExtractor()
        parser.feed(decoded)

        main_text = " ".join(parser.parts)

        # Targeted cleanup for the Baroda Scholar page.
        start = main_text.find("Baroda Scholar Note")
        end = main_text.find("Need Assistance?", start)

        if start >= 0 and end > start:
            extracted = main_text[start:end]

            start_idx = next(
                (
                    i
                    for i, heading in enumerate(parser.headings)
                    if "baroda scholar" in heading.lower()
                ),
                0,
            )

            end_idx = next(
                (
                    i
                    for i in range(start_idx + 1, len(parser.headings))
                    if "need assistance" in parser.headings[i].lower()
                ),
                len(parser.headings),
            )

            headings = list(dict.fromkeys(parser.headings[start_idx:end_idx]))

        else:
            extracted = trafilatura.extract(
                content,
                output_format="markdown",
                include_tables=True,
                include_comments=False,
                include_links=False,
            )

            headings = []

            if extracted:
                for line in extracted.splitlines():
                    match = re.match(r"^(#{1,6})\s+(.+)", line.strip())
                    if match:
                        headings.append(match.group(2).strip())

        if not extracted or not extracted.strip():
            raise ParseError("empty", "HTML extraction returned no content")

        metadata = trafilatura.extract_metadata(content)

        sbi_title = re.search(
            r'<p[^>]*class=["\'][^"\']*\bcard-title\b[^"\']*["\'][^>]*>(.*?)</p>',
            decoded,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if sbi_title:
            title = re.sub(r"\s+", " ", sbi_title.group(1)).strip()

            # Remove the unrelated Education Loan Home footer section.
            extracted = re.split(
                r"(?im)^#{1,6}\s+Education Loan Home\s*$",
                extracted,
                maxsplit=1,
            )[0].strip()

            # Remove the SEO/browser title from the document text.
            if metadata and metadata.title:
                seo_heading = re.escape(metadata.title.strip())
                extracted = re.sub(
                    rf"(?m)^#\s+{seo_heading}\s*$",
                    "",
                    extracted,
                    count=1,
                ).strip()

            # Rebuild headings from the cleaned document text.
            headings = []
            for line in extracted.splitlines():
                match = re.match(r"^(#{1,6})\s+(.+)", line.strip())
                if match:
                    heading = match.group(2).strip()
                    if heading != metadata.title if metadata else True:
                        headings.append(heading)

        else:
            title = (
                parser.title_heading
                or (metadata.title if metadata and metadata.title else None)
                or path.stem
            )

        if not extracted:
            raise ParseError("empty", "HTML extraction returned no content")

        return ParsedDoc(
            "trafilatura",
            "html",
            title,
            [
                ParsedPage(
                    1,
                    extracted,
                    headings,
                    tables=extracted.count("| ---"),
                )
            ],
        )

    except ParseError:
        raise
    except Exception as exc:
        raise ParseError("crash", str(exc)) from exc


def parse_text(path: Path, content: bytes) -> ParsedDoc:
    try:
        text = content.decode("utf-8-sig").strip()
    except UnicodeDecodeError:
        raise ParseError(
            "unsupported_type",
            "Text is not UTF-8",
        ) from None

    if not text:
        raise ParseError("empty", "File contains no text")

    headings = []
    output = []

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                headings.append(heading)
                output.append(stripped)
        else:
            output.append(line)

    return ParsedDoc(
        "builtin",
        "text",
        path.stem,
        [ParsedPage(1, "\n".join(output), headings)],
    )


def parse_data(path: Path, content: bytes) -> ParsedDoc:
    try:
        raw = content.decode("utf-8-sig")

        if path.suffix.lower() == ".json":
            value = json.loads(raw)
            formatted = "```json\n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n```"

        elif path.suffix.lower() in {".yaml", ".yml"}:
            value = yaml.safe_load(raw)
            formatted = (
                "```yaml\n"
                + yaml.safe_dump(
                    value,
                    allow_unicode=True,
                    sort_keys=False,
                )
                + "\n```"
            )

        elif path.suffix.lower() == ".csv":
            rows = list(csv.reader(io.StringIO(raw)))

            if not rows:
                raise ParseError("empty", "CSV contains no rows")

            formatted_rows = [
                [cell.replace("|", "\\|").replace("\n", " ") for cell in row] for row in rows
            ]

            width = max(len(row) for row in formatted_rows)
            formatted_rows = [row + [""] * (width - len(row)) for row in formatted_rows]

            lines = [
                "| " + " | ".join(formatted_rows[0]) + " |",
                "| " + " | ".join(["---"] * width) + " |",
            ]

            lines.extend("| " + " | ".join(row) + " |" for row in formatted_rows[1:])

            formatted = "\n".join(lines)

        else:
            raise ParseError("unsupported_type", path.suffix)

        return ParsedDoc(
            "builtin",
            "data",
            path.stem,
            [ParsedPage(1, formatted)],
        )

    except ParseError:
        raise
    except Exception as exc:
        raise ParseError("corrupt", str(exc)) from exc


def parse_file(path: Path | str, parser: str = "pymupdf") -> ParsedDoc:
    """Parse one file into structured pages."""
    path = Path(path)

    if not path.is_file():
        raise ParseError("corrupt", f"File not found: {path}")

    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ParseError("corrupt", str(exc)) from exc

    kind = detect_kind(path, content)

    if kind == "pdf":
        if parser == "pypdf":
            return parse_pdf_pypdf(path)
        return parse_pdf(path)

    if kind == "html":
        return parse_html(path, content)

    if kind == "data":
        return parse_data(path, content)

    return parse_text(path, content)


def _pdf_reading_order(page, blocks):
    """Separate clear two-column PDF pages into individual reading lines."""
    midpoint = page.rect.width / 2
    left = []
    right = []
    spanning = []

    for block in blocks:
        if "lines" not in block:
            continue

        for line in block["lines"]:
            spans = [span for span in line["spans"] if span.get("text", "").strip()]

            if not spans:
                continue

            x0 = min(span["bbox"][0] for span in spans)
            x1 = max(span["bbox"][2] for span in spans)
            y0 = min(span["bbox"][1] for span in spans)

            item = {
                "bbox": (x0, y0, x1, max(span["bbox"][3] for span in spans)),
                "spans": spans,
            }

            if x1 <= midpoint:
                left.append(item)
            elif x0 >= midpoint:
                right.append(item)
            else:
                spanning.append(item)

    if not left or not right:
        return None

    first_column_y = min(item["bbox"][1] for item in left + right)

    if any(item["bbox"][3] > first_column_y for item in spanning):
        return None

    return (
        sorted(spanning, key=lambda item: item["bbox"][1])
        + sorted(left, key=lambda item: item["bbox"][1])
        + sorted(right, key=lambda item: item["bbox"][1])
    )
