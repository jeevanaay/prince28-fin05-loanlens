"""Integration tests against the dedicated PostgreSQL test database."""

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from loanlens.config import get_settings
from loanlens.db.models import Document
from loanlens.db.repository import DocumentRepository

TEST_IDS = ["integration-001", "integration-002"]


@pytest_asyncio.fixture
async def db_session():
    """Create isolated test records and clean them up afterward."""
    settings = get_settings()

    if not settings.test_database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    engine = create_async_engine(
        settings.test_database_url,
        pool_pre_ping=True,
    )

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        session_factory = async_sessionmaker(
            engine,
            expire_on_commit=False,
        )

        async with session_factory() as session:
            try:
                existing = await session.scalars(
                    select(Document).where(Document.external_id.in_(TEST_IDS))
                )

                for document in existing.all():
                    await session.delete(document)

                await session.flush()

                session.add_all(
                    [
                        Document(
                            external_id="integration-001",
                            title="Integration Test SBI Education Loan",
                            sha256="a" * 64,
                            metadata_={
                                "lender": "State Bank of India",
                                "scheme": "Student Loan Scheme",
                                "max_amount": 2000000,
                            },
                        ),
                        Document(
                            external_id="integration-002",
                            title="Integration Test Bank of Baroda Loan",
                            sha256="b" * 64,
                            metadata_={
                                "lender": "Bank of Baroda",
                                "scheme": "Baroda Scholar",
                                "max_amount": 3000000,
                            },
                        ),
                    ]
                )

                await session.commit()

                yield session

            finally:
                existing = await session.scalars(
                    select(Document).where(Document.external_id.in_(TEST_IDS))
                )

                for document in existing.all():
                    await session.delete(document)

                await session.commit()

    finally:
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
    assert document["title"] == "Integration Test SBI Education Loan"
    assert document["lender"] == "State Bank of India"


@pytest.mark.asyncio
async def test_document_search(db_session):
    repository = DocumentRepository(db_session)

    results = await repository.search("Baroda Scholar")

    assert len(results) == 1
    assert results[0]["id"] == "integration-002"
    assert results[0]["scheme"] == "Baroda Scholar"
