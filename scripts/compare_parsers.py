import json
from difflib import SequenceMatcher
from pathlib import Path

from loanlens.ingest.parse import parse_file

manifest = Path("data/manifest.jsonl")
records = [
    json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()
]

seen = set()
print("\nPDF COMPARISON")
print("-" * 85)

for record in records:
    if record.get("status") != "downloaded":
        continue

    path = Path(record["path"])
    if not path.exists() or path in seen:
        continue
    seen.add(path)

    if path.read_bytes().startswith(b"%PDF-"):
        try:
            pymupdf_doc = parse_file(path, "pymupdf")
            pypdf_doc = parse_file(path, "pypdf")

            text_a = " ".join(page.text for page in pymupdf_doc.pages).casefold().split()

            text_b = " ".join(page.text for page in pypdf_doc.pages).casefold().split()

            similarity = SequenceMatcher(None, text_a, text_b).ratio() * 100

            if similarity >= 98:
                verdict = "Near-identical extraction"
            elif similarity >= 90:
                verdict = "Minor extraction differences"
            else:
                verdict = "Review extraction differences"

            print(
                f"{record['title']}: {similarity:.2f}% | {len(pymupdf_doc.pages)} pages | {verdict}"
            )

        except Exception as exc:
            print(f"{record['title']}: COMPARISON ERROR | {exc}")

print("\nHTML EXTRACTION QUALITY")
print("-" * 85)

seen.clear()

for record in records:
    if record.get("status") != "downloaded":
        continue

    path = Path(record["path"])
    if not path.exists() or path in seen:
        continue
    seen.add(path)

    if path.read_bytes().startswith(b"%PDF-"):
        continue

    try:
        doc = parse_file(path)
        text = "\n".join(page.text for page in doc.pages)
        headings = [heading for page in doc.pages for heading in page.headings]

        print(
            f"{record['title']}: "
            f"{len(text)} characters | "
            f"{len(headings)} headings | "
            f"{len(doc.pages)} pages | "
            f"Title: {doc.title}"
        )

    except Exception as exc:
        print(f"{record['title']}: EXTRACTION ERROR | {exc}")
