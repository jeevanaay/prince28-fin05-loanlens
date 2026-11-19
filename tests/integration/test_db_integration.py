"""Integration tests against a fresh, temporary PostgreSQL database."""

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from loanlens.db.models import Document
from loanlens.db.repository import DocumentRepository


@pytest_asyncio.fixture
async def db_session(database_url):
    """Create test records in the temporary database for each test."""
    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
    )

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            session.add_all(
                [
                    Document(
                        external_id="integration-001",
                        title="Integration Unique SBI Loan",
                        lender="Integration Test Lender SBI",
                        published_on=date(2025, 1, 15),
                        sha256="a" * 64,
                        metadata_={
                            "scheme": "Integration Unique Scheme SBI",
                            "max_amount": 2000000,
                        },
                    ),
                    Document(
                        external_id="integration-002",
                        title="Integration Unique BOB Loan",
                        lender="Integration Test Lender BOB",
                        published_on=date(2024, 6, 10),
                        sha256="b" * 64,
                        metadata_={
                            "scheme": "Integration Unique Scheme BOB",
                            "max_amount": 3000000,
                        },
                    ),
                    Document(
                        external_id="integration-003",
                        title="Integration Unique GOI Loan",
                        lender="Integration Test Lender GOI",
                        published_on=None,
                        sha256="c" * 64,
                        metadata_={
                            "scheme": "Integration Unique Scheme GOI",
                        },
                    ),
                ]
            )

            await session.commit()
            yield session

    finally:
        async with session_factory() as cleanup_session:
            await cleanup_session.execute(
                delete(Document).where(
                    Document.external_id.in_(
                        [
                            "integration-001",
                            "integration-002",
                            "integration-003",
                        ]
                    )
                )
            )
            await cleanup_session.commit()

        await engine.dispose()


@pytest.mark.asyncio
async def test_database_connection(db_session):
    result = await db_session.execute(text("SELECT 1"))

    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_document_retrieval(db_session):
    repository = DocumentRepository(db_session)

    document = await repository.get("integration-001")

    assert document is not None
    assert document["id"] == "integration-001"
    assert document["title"] == "Integration Unique SBI Loan"
    assert document["lender"] == "Integration Test Lender SBI"


@pytest.mark.asyncio
async def test_document_search(db_session):
    repository = DocumentRepository(db_session)

    results = await repository.search("Integration Unique Scheme BOB")

    assert len(results) == 1
    assert results[0]["id"] == "integration-002"
    assert results[0]["scheme"] == "Integration Unique Scheme BOB"


@pytest.mark.asyncio
async def test_lender_filter(db_session):
    repository = DocumentRepository(db_session)

    results = await repository.search(lender="Integration Test Lender SBI")

    assert len(results) == 1
    assert results[0]["id"] == "integration-001"
    assert results[0]["lender"] == "Integration Test Lender SBI"


@pytest.mark.asyncio
async def test_sort_by_lender_ascending(db_session):
    repository = DocumentRepository(db_session)

    results = await repository.search(
        q="Integration Unique",
        sort_by="lender",
        sort_order="asc",
    )

    assert [row["id"] for row in results] == [
        "integration-002",
        "integration-003",
        "integration-001",
    ]


@pytest.mark.asyncio
async def test_sort_by_max_amount_descending(db_session):
    repository = DocumentRepository(db_session)

    results = await repository.search(
        q="Integration Unique",
        sort_by="max_amount",
        sort_order="desc",
    )

    assert [row["id"] for row in results] == [
        "integration-002",
        "integration-001",
        "integration-003",
    ]


@pytest.mark.asyncio
async def test_sort_by_scheme_ascending(db_session):
    repository = DocumentRepository(db_session)

    results = await repository.search(
        q="Integration Unique",
        sort_by="scheme",
        sort_order="asc",
    )

    assert [row["id"] for row in results] == [
        "integration-002",
        "integration-003",
        "integration-001",
    ]


@pytest.mark.asyncio
async def test_sort_by_published_date_descending(db_session):
    repository = DocumentRepository(db_session)

    results = await repository.search(
        q="Integration Unique",
        sort_by="published_on",
        sort_order="desc",
    )

    assert [row["id"] for row in results] == [
        "integration-001",
        "integration-002",
        "integration-003",
    ]


@pytest.mark.asyncio
async def test_sort_keeps_null_values_last(db_session):
    repository = DocumentRepository(db_session)

    results = await repository.search(
        q="Integration Unique",
        sort_by="max_amount",
        sort_order="desc",
    )

    assert results[-1]["id"] == "integration-003"
    assert results[-1].get("max_amount") is None
