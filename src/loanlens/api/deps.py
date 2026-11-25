"""Dependencies: endpoints ask for these instead of building them."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from loanlens.config import Settings
from loanlens.db.llm_calls import UsageRepository
from loanlens.db.repository import DocumentRepository
from loanlens.llm.gateway import LLMGateway


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_db_session(request: Request):
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


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
RepositoryDep = Annotated[DocumentRepository, Depends(get_repository)]
GatewayDep = Annotated[LLMGateway, Depends(get_llm_gateway)]
UsageDep = Annotated[UsageRepository, Depends(get_usage_repository)]
