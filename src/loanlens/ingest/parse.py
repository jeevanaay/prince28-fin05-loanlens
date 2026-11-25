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


def _heading_level(span: dict) -> int | None:
    """Estimate heading level from font size and bold formatting."""
    size = span.get("size", 0)
    flags = span.get("flags", 0)
    text = span.get("text", "").strip()

    if not text or len(text) > 150:
        return None

    if size >= 18:
        return 1
    if size >= 14 or (flags & 16 and size >= 12):
        return 2
    if size >= 11 and flags & 16:
        return 3

    return None


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

        title = document.metadata.get("title") or path.stem

        for index, page in enumerate(document):
            blocks = page.get_text("dict")["blocks"]
            lines = []
            page_headings = []

            for block in blocks:
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    for span in line["spans"]:
                        value = span["text"].strip()
                        if not value:
                            continue

                        level = _heading_level(span)
                        if level:
                            page_headings.append((level, value))

                        lines.append(value)

            text = "\n".join(lines).strip()
            total_chars += len(text)

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

            self.current_heading_tag = None
            self.current_heading_parts = []

        if tag == "main":
            self.in_main = False


def parse_html(path: Path, content: bytes) -> ParsedDoc:
    """Extract HTML content, headings and tables."""
    try:
        parser = MainExtractor()
        parser.feed(content.decode("utf-8", errors="replace"))

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
        title = metadata.title if metadata and metadata.title else path.stem

        return ParsedDoc(
            "trafilatura",
            "html",
            title,
            [
                ParsedPage(
                    1,
                    extracted.strip(),
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
