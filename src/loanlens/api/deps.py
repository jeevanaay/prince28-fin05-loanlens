"""Dependencies: endpoints ask for these instead of building them."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from loanlens.config import Settings
from loanlens.db.repository import DocumentRepository


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_db_session(request: Request):
    """Provide one database session per request."""
    async with request.app.state.session_factory() as session:
        yield session


def get_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentRepository:
    return DocumentRepository(session)


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
RepositoryDep = Annotated[DocumentRepository, Depends(get_repository)]
