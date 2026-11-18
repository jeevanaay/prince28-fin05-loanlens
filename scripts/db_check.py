"""Check database connectivity and verify loaded records."""

import asyncio

from sqlalchemy import text

from loanlens.config import get_settings
from loanlens.db.session import make_engine


async def main() -> None:
    engine = make_engine(get_settings())

    try:
        async with engine.connect() as conn:
            version = await conn.scalar(text("SELECT version()"))
            database = await conn.scalar(text("SELECT current_database()"))
            document_count = await conn.scalar(text("SELECT COUNT(*) FROM documents"))

        print(f"Connected to database '{database}'")
        print(version)
        print(f"Documents stored: {document_count}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
