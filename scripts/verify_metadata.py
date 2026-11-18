import asyncio

from sqlalchemy import text

from loanlens.config import get_settings
from loanlens.db.session import make_engine


async def main():
    settings = get_settings()

    if not settings.test_database_url:
        raise RuntimeError("TEST_DATABASE_URL is not configured")

    settings = settings.model_copy(update={"database_url": settings.test_database_url})

    engine = make_engine(settings)

    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text("""
                    SELECT
                        COUNT(*) AS total_documents,
                        COUNT(*) FILTER (
                            WHERE metadata::text LIKE '%null%'
                        ) AS documents_with_null_text,
                        COUNT(*) FILTER (
                            WHERE metadata ? 'lender'
                        ) AS records_with_lender,
                        COUNT(*) FILTER (
                            WHERE metadata ? 'scheme'
                        ) AS records_with_scheme
                    FROM documents
                """)
            )

            row = result.mappings().one()

            for key, value in row.items():
                print(f"{key}: {value}")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
