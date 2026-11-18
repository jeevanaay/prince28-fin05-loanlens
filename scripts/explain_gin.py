"""Inspect the PostgreSQL query plan for the JSONB GIN index."""

import asyncio

from sqlalchemy import text

from loanlens.config import get_settings
from loanlens.db.session import make_engine


async def main():
    engine = make_engine(get_settings())

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SET enable_seqscan = off"))

            result = await conn.execute(
                text("""
                    EXPLAIN
                    SELECT external_id
                    FROM documents
                    WHERE metadata @> '{"lender": "State Bank of India"}'
                """)
            )

            print("GIN index query plan:")

            for row in result:
                print(row[0])

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
