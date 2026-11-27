"""Integration tests for PostgreSQL-backed ingestion queue recovery."""

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from loanlens.db.ingest_jobs import IngestRepository
from loanlens.db.models import IngestItem, IngestJob


@pytest_asyncio.fixture
async def recovery_session(database_url):
    engine = create_async_engine(database_url, pool_pre_ping=True)
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with factory() as session:
            yield session
    finally:
        async with factory() as session:
            await session.execute(delete(IngestItem))
            await session.execute(delete(IngestJob))
            await session.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_open_item_ids_returns_queued_and_running_items(recovery_session):
    repository = IngestRepository(recovery_session)

    _, item_ids = await repository.create(
        [
            {"url": "https://example.com/queued.pdf"},
            {"url": "https://example.com/running.pdf"},
            {"url": "https://example.com/done.pdf"},
        ]
    )

    queued_id, running_id, done_id = item_ids

    running_item = await recovery_session.get(IngestItem, running_id)
    done_item = await recovery_session.get(IngestItem, done_id)

    running_item.status = "running"
    done_item.status = "done"
    await recovery_session.commit()

    recovered_ids = await repository.open_item_ids()

    assert queued_id in recovered_ids
    assert running_id in recovered_ids
    assert done_id not in recovered_ids
    assert recovered_ids == sorted(recovered_ids)
