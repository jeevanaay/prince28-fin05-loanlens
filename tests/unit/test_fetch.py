from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import httpx
import pytest

from loanlens.ingest.fetch import (
    HostGate,
    Manifest,
    ManifestRecord,
    Robots,
    fetch_all,
    fetch_one,
    safe_filename,
)


def make_record(url: str = "https://example.com/file.pdf") -> ManifestRecord:
    return ManifestRecord(
        url=url,
        source="Example",
        licence="Test licence",
        title="Example PDF",
        status="downloaded",
        fetched_at="2026-11-23T00:00:00+00:00",
        path="data/raw/example.pdf",
        sha256="abc123",
        bytes=100,
    )


def make_item(url: str = "https://example.com/file.pdf") -> dict[str, str]:
    return {
        "url": url,
        "source": "Example",
        "licence": "Test licence",
        "title": "Example PDF",
        "collection_status": "approved",
        "collection_evidence": "Approved test fixture",
    }


def test_safe_filename_is_stable_and_unique() -> None:
    first = safe_filename("https://example.com/a.pdf")
    second = safe_filename("https://example.com/a.pdf")
    third = safe_filename("https://example.com/b.pdf")

    assert first == second
    assert first != third
    assert first.endswith("_a.pdf")


def test_manifest_appends_and_reads_records(tmp_path: Path) -> None:
    path = tmp_path / "manifest.jsonl"
    manifest = Manifest(path)
    record = make_record()
    manifest.add(record)

    loaded = Manifest(path)

    assert loaded.records[record.url]["status"] == "downloaded"
    assert loaded.records[record.url]["sha256"] == "abc123"


def test_manifest_ignores_invalid_json_lines(tmp_path: Path) -> None:
    path = tmp_path / "manifest.jsonl"
    path.write_text("{invalid json}\n", encoding="utf-8")

    manifest = Manifest(path)

    assert manifest.records == {}


def test_manifest_complete_requires_existing_file(tmp_path: Path) -> None:
    document = tmp_path / "document.pdf"
    document.write_bytes(b"pdf")
    path = tmp_path / "manifest.jsonl"

    manifest = Manifest(path)
    record = make_record()
    record.path = str(document)
    manifest.add(record)

    assert manifest.is_complete(record.url)

    document.unlink()

    assert not manifest.is_complete(record.url)


def test_manifest_record_has_expected_fields() -> None:
    record = make_record()
    data = record.__dict__

    assert data["url"].startswith("https://")
    assert data["status"] == "downloaded"
    assert data["bytes"] == 100


def test_robots_allows_when_policy_has_no_disallow() -> None:
    from protego import Protego

    policy = Protego.parse("User-agent: *\nDisallow:\n")

    assert policy.can_fetch("https://example.com/file.pdf", "examate-student-bot")


def test_robots_denies_disallowed_path() -> None:
    from protego import Protego

    policy = Protego.parse("User-agent: *\nDisallow: /private/\n")

    assert not policy.can_fetch(
        "https://example.com/private/file.pdf",
        "examate-student-bot",
    )


def test_retry_after_seconds() -> None:
    from loanlens.ingest.fetch import retry_after_seconds

    assert retry_after_seconds("5") == 5.0
    assert retry_after_seconds(None) is None
    assert retry_after_seconds("invalid") is None


@pytest.mark.asyncio
async def test_robots_caches_policy_per_host() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, text="User-agent: *\nDisallow:\n")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        robots = Robots(client)

        first = await robots.allowed("https://example.com/a.pdf")
        second = await robots.allowed("https://example.com/b.pdf")

    assert first[0] is True
    assert second[0] is True
    assert calls == 1


@pytest.mark.asyncio
async def test_robots_fails_closed_on_server_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        robots = Robots(client)
        allowed, delay = await robots.allowed("https://example.com/file.pdf")

    assert allowed is False
    assert delay == 0.0


@pytest.mark.asyncio
async def test_host_gate_enforces_delay() -> None:
    gate = HostGate(default_delay=0.05)

    await gate.wait("https://example.com/a.pdf")

    start = asyncio.get_running_loop().time()
    await gate.wait("https://example.com/b.pdf")
    elapsed = asyncio.get_running_loop().time() - start

    assert elapsed >= 0.045


@pytest.mark.asyncio
async def test_fetch_downloads_and_hashes_file(tmp_path: Path) -> None:
    content = b"%PDF-1.4 sample document"

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:\n")
        return httpx.Response(200, content=content)

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        manifest = Manifest(tmp_path / "manifest.jsonl")
        result = await fetch_one(
            make_item(),
            client=client,
            robots=Robots(client),
            gate=HostGate(0),
            semaphore=asyncio.Semaphore(4),
            manifest=manifest,
            raw_dir=tmp_path / "raw",
        )

    assert result.status == "downloaded"
    assert result.sha256 == hashlib.sha256(content).hexdigest()
    assert Path(result.path).read_bytes() == content


@pytest.mark.asyncio
async def test_fetch_blocks_robots_disallowed_url(tmp_path: Path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="User-agent: *\nDisallow: /")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_one(
            make_item(),
            client=client,
            robots=Robots(client),
            gate=HostGate(0),
            semaphore=asyncio.Semaphore(4),
            manifest=Manifest(tmp_path / "manifest.jsonl"),
            raw_dir=tmp_path / "raw",
        )

    assert result.status == "blocked"
    assert not (tmp_path / "raw").exists()


@pytest.mark.asyncio
async def test_fetch_blocks_pending_collection_without_network(
    tmp_path: Path,
) -> None:
    item = make_item()
    item["collection_status"] = "pending"

    async def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("Network must not be called for pending sources")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        manifest = Manifest(tmp_path / "manifest.jsonl")
        result = await fetch_one(
            item,
            client=client,
            robots=Robots(client),
            gate=HostGate(0),
            semaphore=asyncio.Semaphore(4),
            manifest=manifest,
            raw_dir=tmp_path / "raw",
        )

    assert result.status == "blocked"
    assert "collection_status=pending" in result.error
    assert not (tmp_path / "raw").exists()
    assert item["url"] in manifest.records


@pytest.mark.asyncio
async def test_fetch_retries_temporary_server_error(tmp_path: Path) -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:\n")

        attempts += 1
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(200, content=b"document")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_one(
            make_item(),
            client=client,
            robots=Robots(client),
            gate=HostGate(0),
            semaphore=asyncio.Semaphore(4),
            manifest=Manifest(tmp_path / "manifest.jsonl"),
            raw_dir=tmp_path / "raw",
        )

    assert result.status == "downloaded"
    assert attempts == 2


@pytest.mark.asyncio
async def test_fetch_skips_completed_download(tmp_path: Path) -> None:
    document = tmp_path / "existing.pdf"
    document.write_bytes(b"existing")

    manifest = Manifest(tmp_path / "manifest.jsonl")
    record = make_record()
    record.path = str(document)
    manifest.add(record)

    async def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("Network should not be called for a completed download")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_one(
            make_item(),
            client=client,
            robots=Robots(client),
            gate=HostGate(0),
            semaphore=asyncio.Semaphore(4),
            manifest=manifest,
            raw_dir=tmp_path / "raw",
        )

    assert result.status == "skipped"


@pytest.mark.asyncio
async def test_fetch_all_rejects_excessive_concurrency(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Concurrency"):
        await fetch_all(
            [],
            raw_dir=tmp_path / "raw",
            manifest_path=tmp_path / "manifest.jsonl",
            concurrency=5,
        )


@pytest.mark.asyncio
async def test_fetch_all_empty_input(tmp_path: Path) -> None:
    results = await fetch_all(
        [],
        raw_dir=tmp_path / "raw",
        manifest_path=tmp_path / "manifest.jsonl",
    )

    assert results == []


def test_manifest_is_valid_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "manifest.jsonl"
    manifest = Manifest(path)
    manifest.add(make_record())

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    assert len(rows) == 1
    assert rows[0]["title"] == "Example PDF"


def test_manifest_records_manual_origin(tmp_path: Path) -> None:
    record = make_record()
    record.via = "manual"

    manifest = Manifest(tmp_path / "manifest.jsonl")
    manifest.add(record)

    stored = json.loads((tmp_path / "manifest.jsonl").read_text(encoding="utf-8").strip())

    assert stored["via"] == "manual"


@pytest.mark.asyncio
async def test_fetch_blocks_approved_source_without_evidence(
    tmp_path: Path,
) -> None:
    item = make_item()
    item["collection_status"] = "approved"
    item["collection_evidence"] = ""

    async def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("Network should not be called without collection evidence")

    manifest = Manifest(tmp_path / "manifest.jsonl")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_one(
            item,
            client=client,
            robots=Robots(client),
            gate=HostGate(0),
            semaphore=asyncio.Semaphore(4),
            manifest=manifest,
            raw_dir=tmp_path / "raw",
        )

    assert result.status == "blocked"
    assert "evidence" in (result.error or "").lower()
    assert not (tmp_path / "raw").exists()
