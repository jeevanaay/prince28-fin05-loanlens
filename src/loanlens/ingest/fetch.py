from __future__ import annotations

import asyncio
import hashlib
import json
import random
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx
from protego import Protego

CONTACT = "https://github.com/jeevannay/prince28-fin05-loanlens"
ROBOTS_TOKEN = "examate-student-bot"
USER_AGENT = f"{ROBOTS_TOKEN}/0.1 (student project; +{CONTACT})"

MAX_CONCURRENCY = 4
PER_HOST_DELAY = 0.5
MAX_RETRIES = 3
ATTEMPT_TIMEOUT = 45.0


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def safe_filename(url: str) -> str:
    """Create a stable filename from a URL."""
    parsed = urlsplit(url)
    name = Path(parsed.path).name or "document"
    name = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return f"{digest}_{name}"


def retry_after_seconds(value: str | None) -> float | None:
    """Parse either Retry-After seconds or an HTTP date."""
    if not value:
        return None

    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            return max(
                0.0,
                (retry_at - datetime.now(UTC)).total_seconds(),
            )
        except (TypeError, ValueError, OverflowError):
            return None


@dataclass
class ManifestRecord:
    url: str
    source: str
    licence: str
    title: str
    status: str
    fetched_at: str
    path: str | None = None
    sha256: str | None = None
    bytes: int = 0
    error: str | None = None
    via: str = "url"
    collection_status: str = "pending"
    collection_evidence: str = ""


class Manifest:
    """Append-only JSONL manifest with completed-download lookup."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.records: dict[str, dict] = {}

        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        self.records[record["url"]] = record
                    except (json.JSONDecodeError, KeyError):
                        continue

    def is_complete(self, url: str) -> bool:
        record = self.records.get(url, {})
        if record.get("status") != "downloaded" or not record.get("path"):
            return False
        return Path(record["path"]).is_file()

    def add(self, record: ManifestRecord) -> None:
        data = asdict(record)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(data, ensure_ascii=False) + "\n")
        self.records[record.url] = data


class Robots:
    """Fetch and cache robots.txt policies for each host."""

    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.cache: dict[str, Protego | None] = {}

    async def policy_for(self, url: str) -> Protego | None:
        parsed = urlsplit(url)
        origin = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
        if origin in self.cache:
            return self.cache[origin]

        robots_url = f"{origin}/robots.txt"

        try:
            response = await self.client.get(robots_url)
            if response.status_code in (404, 410):
                policy = Protego.parse("")
            elif 200 <= response.status_code < 300:
                policy = Protego.parse(response.text)
            else:
                # Fail closed when the policy cannot be retrieved safely.
                policy = None
        except httpx.HTTPError:
            policy = None

        self.cache[origin] = policy
        return policy

    async def allowed(self, url: str) -> tuple[bool, float]:
        policy = await self.policy_for(url)
        if policy is None:
            return False, 0.0

        permitted = policy.can_fetch(url, ROBOTS_TOKEN)
        delay = policy.crawl_delay(ROBOTS_TOKEN) or 0.0
        return permitted, float(delay)


class HostGate:
    """Enforce a minimum delay between requests to the same host."""

    def __init__(self, default_delay: float = PER_HOST_DELAY):
        self.default_delay = default_delay
        self._next_request: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def wait(self, url: str, crawl_delay: float = 0.0) -> None:
        host = urlsplit(url).netloc
        lock = self._locks.setdefault(host, asyncio.Lock())

        async with lock:
            delay = max(self.default_delay, crawl_delay)
            now = time.monotonic()
            wait_for = max(0.0, self._next_request.get(host, now) - now)

            if wait_for:
                await asyncio.sleep(wait_for)

            self._next_request[host] = time.monotonic() + delay


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(ATTEMPT_TIMEOUT),
        follow_redirects=True,
    )


async def fetch_one(
    item: dict[str, str],
    *,
    client: httpx.AsyncClient,
    robots: Robots,
    gate: HostGate,
    semaphore: asyncio.Semaphore,
    manifest: Manifest,
    raw_dir: Path,
    max_retries: int = MAX_RETRIES,
) -> ManifestRecord:
    url = item["url"]
    source = item.get("source", "")
    licence = item.get("licence", "")
    title = item.get("title", "")
    collection_status = item.get("collection_status", "pending").strip().lower()
    collection_evidence = item.get("collection_evidence", "").strip()

    if collection_status != "approved" or not collection_evidence:
        record = ManifestRecord(
            url=url,
            source=source,
            licence=licence,
            title=title,
            status="blocked",
            fetched_at=utc_now(),
            error=(
                "Automated collection is not approved: "
                f"collection_status={collection_status}; "
                f"evidence={collection_evidence}"
            ),
            collection_status=collection_status,
            collection_evidence=collection_evidence,
        )
        manifest.add(record)
        return record

    if manifest.is_complete(url):
        previous = manifest.records[url]
        return ManifestRecord(
            **{
                **previous,
                "status": "skipped",
                "fetched_at": utc_now(),
            }
        )

    permitted, crawl_delay = await robots.allowed(url)
    if not permitted:
        record = ManifestRecord(
            url=url,
            source=source,
            licence=licence,
            title=title,
            status="blocked",
            fetched_at=utc_now(),
            error="robots.txt disallows crawling or could not be checked",
            collection_status=collection_status,
            collection_evidence=collection_evidence,
        )
        manifest.add(record)
        return record

    raw_dir.mkdir(parents=True, exist_ok=True)
    destination = raw_dir / safe_filename(url)
    partial = destination.with_suffix(destination.suffix + ".part")

    async with semaphore:
        for attempt in range(max_retries + 1):
            await gate.wait(url, crawl_delay)

            try:
                async with asyncio.timeout(ATTEMPT_TIMEOUT):
                    response = await client.get(url)

                if (
                    response.status_code == 429 or response.status_code >= 500
                ) and attempt < max_retries:
                    server_delay = retry_after_seconds(response.headers.get("Retry-After"))
                    delay = (
                        server_delay
                        if server_delay is not None
                        else (min(30.0, 2**attempt) + random.uniform(0.1, 0.8))
                    )
                    await asyncio.sleep(delay)
                    continue

                response.raise_for_status()

                content = response.content
                if not content:
                    raise ValueError("Downloaded response was empty")

                partial.write_bytes(content)
                partial.replace(destination)

                record = ManifestRecord(
                    url=url,
                    source=source,
                    licence=licence,
                    title=title,
                    status="downloaded",
                    fetched_at=utc_now(),
                    path=str(destination),
                    sha256=hashlib.sha256(content).hexdigest(),
                    bytes=len(content),
                    collection_status=collection_status,
                    collection_evidence=collection_evidence,
                )
                manifest.add(record)
                return record

            except (
                httpx.HTTPError,
                TimeoutError,
                OSError,
                ValueError,
            ) as exc:
                if attempt >= max_retries:
                    error = f"{type(exc).__name__}: {exc}"
                    break

                await asyncio.sleep(min(30.0, 2**attempt) + random.uniform(0.1, 0.8))

        partial.unlink(missing_ok=True)

        record = ManifestRecord(
            url=url,
            source=source,
            licence=licence,
            title=title,
            status="failed",
            fetched_at=utc_now(),
            error=error,
            collection_status=collection_status,
            collection_evidence=collection_evidence,
        )
        manifest.add(record)
        return record


async def fetch_all(
    items: list[dict[str, str]],
    *,
    raw_dir: Path = Path("data/raw"),
    manifest_path: Path = Path("data/manifest.jsonl"),
    concurrency: int = MAX_CONCURRENCY,
    per_host_delay: float = PER_HOST_DELAY,
) -> list[ManifestRecord]:
    """Download a collection of URLs politely and record each result."""
    if not 1 <= concurrency <= MAX_CONCURRENCY:
        raise ValueError(f"Concurrency must be between 1 and {MAX_CONCURRENCY}")

    manifest = Manifest(manifest_path)
    semaphore = asyncio.Semaphore(concurrency)
    gate = HostGate(per_host_delay)

    async with make_client() as client:
        robots = Robots(client)
        tasks = [
            fetch_one(
                item,
                client=client,
                robots=robots,
                gate=gate,
                semaphore=semaphore,
                manifest=manifest,
                raw_dir=raw_dir,
            )
            for item in items
        ]
        return await asyncio.gather(*tasks)
