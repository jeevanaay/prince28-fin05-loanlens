"""Dependencies: endpoints ask for these instead of building them."""

import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from loanlens.config import Settings
from loanlens.db.ingest_jobs import IngestRepository
from loanlens.db.llm_calls import UsageRepository
from loanlens.db.repository import DocumentRepository
from loanlens.llm.gateway import LLMGateway
from loanlens.workers.queue import Queue


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


def get_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentRepository:
    return DocumentRepository(session)


def get_llm_gateway(request: Request) -> LLMGateway:
    return request.app.state.llm_gateway


def get_usage_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UsageRepository:
    return UsageRepository(session)


async def get_ingest_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IngestRepository:
    return IngestRepository(session)


async def get_queue(request: Request) -> Queue:
    """Connect to Redis on first use, not during API startup."""
    state = request.app.state
    if getattr(state, "queue", None) is None:
        try:
            state.queue = await Queue.connect(state.settings.redis_url)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="The job queue (Redis) cannot be reached.",
            ) from exc
    return state.queue


def get_manifest(request: Request) -> list[dict]:
    """Read the newest manifest entry for each URL."""
    path = request.app.state.settings.manifest_file
    if not path.is_file():
        return []

    latest: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        if not isinstance(record, dict):
            continue

        url = record.get("url")
        if not isinstance(url, str) or not url.strip():
            continue

        latest[url] = record

    return list(latest.values())


def require_admin(
    request: Request,
    x_admin_token: Annotated[str, Header()] = "",
) -> None:
    """Require the configured token before starting ingestion."""
    expected = request.app.state.settings.admin_token

    if not expected and request.app.state.settings.app_env == "local":
        return

    if not expected or x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing admin token.")


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
RepositoryDep = Annotated[DocumentRepository, Depends(get_repository)]
GatewayDep = Annotated[LLMGateway, Depends(get_llm_gateway)]
UsageDep = Annotated[UsageRepository, Depends(get_usage_repository)]
IngestRepoDep = Annotated[IngestRepository, Depends(get_ingest_repo)]
QueueDep = Annotated[Queue, Depends(get_queue)]
ManifestDep = Annotated[list[dict], Depends(get_manifest)]
