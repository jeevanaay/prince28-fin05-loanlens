from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.fetch import (
    collect_repo,
    collect_sitemap,
    register_manual,
    require_collection_approval,
)


@pytest.mark.parametrize("status", ["pending", "blocked"])
def test_collection_approval_rejects_unapproved_status(status: str) -> None:
    args = SimpleNamespace(
        collection_status=status,
        collection_evidence="Test evidence",
    )

    with pytest.raises(PermissionError, match="collection_status"):
        require_collection_approval(args)


def test_collection_approval_rejects_empty_evidence() -> None:
    args = SimpleNamespace(
        collection_status="approved",
        collection_evidence="  ",
    )

    with pytest.raises(PermissionError, match="collection_evidence"):
        require_collection_approval(args)


@pytest.mark.asyncio
async def test_sitemap_rejects_pending_before_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_if_called(url: str) -> list[str]:
        pytest.fail("Sitemap must not be accessed for pending sources")

    monkeypatch.setattr("scripts.fetch.sitemap_urls", fail_if_called)

    args = SimpleNamespace(
        collection_status="pending",
        collection_evidence="Not approved",
        url="https://example.com/sitemap.xml",
    )

    with pytest.raises(PermissionError):
        await collect_sitemap(args)


def test_manual_rejects_pending_before_copy(tmp_path: Path) -> None:
    source_file = tmp_path / "source.pdf"
    source_file.write_bytes(b"test document")

    raw_dir = tmp_path / "raw"

    args = SimpleNamespace(
        collection_status="pending",
        collection_evidence="Not approved",
        file=source_file,
        raw_dir=raw_dir,
    )

    with pytest.raises(PermissionError):
        register_manual(args)

    assert not raw_dir.exists()


def test_repo_rejects_pending_before_clone(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail_if_called(*args: object, **kwargs: object) -> None:
        pytest.fail("Git clone must not run for pending sources")

    monkeypatch.setattr("scripts.fetch.subprocess.run", fail_if_called)

    args = SimpleNamespace(
        collection_status="pending",
        collection_evidence="Not approved",
        raw_dir=tmp_path / "raw",
    )

    with pytest.raises(PermissionError):
        collect_repo(args)

    assert not args.raw_dir.exists()
