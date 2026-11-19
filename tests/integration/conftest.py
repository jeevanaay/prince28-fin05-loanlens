"""Integration tests using a fresh PostgreSQL database for every test run."""

import asyncio
import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from loanlens.db.url import to_asyncpg_url

BASE_URL = os.getenv("TEST_DATABASE_URL")


def pytest_collection_modifyitems(config, items):
    """Skip integration tests when TEST_DATABASE_URL is unavailable."""
    if BASE_URL:
        return

    skip = pytest.mark.skip(reason="Set TEST_DATABASE_URL to run integration tests.")

    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(skip)


async def execute_admin_sql(base_url: str, sql: str) -> None:
    """Execute database administration SQL using an autocommit connection."""
    engine = create_async_engine(
        to_asyncpg_url(base_url),
        isolation_level="AUTOCOMMIT",
    )

    try:
        async with engine.connect() as connection:
            await connection.execute(text(sql))
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def database_url():
    """Create a unique database, migrate it, and drop it after the test run."""
    if not BASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured.")

    database_name = f"loanlens_test_{uuid.uuid4().hex[:8]}"

    # Connect to the existing local app_test database to create a new database.
    asyncio.run(
        execute_admin_sql(
            BASE_URL,
            f'CREATE DATABASE "{database_name}"',
        )
    )

    database_url = (
        make_url(to_asyncpg_url(BASE_URL))
        .set(database=database_name)
        .render_as_string(hide_password=False)
    )

    patch = pytest.MonkeyPatch()
    patch.setenv("APP_ENV", "ci")
    patch.setenv("DATABASE_URL", database_url)
    patch.delenv("LOANLENS_ALEMBIC_USE_TEST_DB", raising=False)

    try:
        from loanlens.config import get_settings

        get_settings.cache_clear()

        alembic_config = Config("alembic.ini")
        command.upgrade(alembic_config, "head")

        yield database_url

    finally:
        get_settings.cache_clear()
        patch.undo()

        asyncio.run(
            execute_admin_sql(
                BASE_URL,
                f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)',
            )
        )
