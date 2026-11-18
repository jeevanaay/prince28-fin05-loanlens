"""One engine (a pool of connections) per app; one session per request."""

from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from loanlens.config import Settings


def make_engine(settings: Settings) -> AsyncEngine:
    """Create the application's async database engine."""
    return create_async_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=300,
    )


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker:
    """Create a session factory for the application."""
    return async_sessionmaker(engine, expire_on_commit=False)


def get_pool_status(engine: AsyncEngine) -> dict[str, Any]:
    """Return connection pool statistics."""
    pool = engine.pool

    pool_size = pool.size()
    checked_out = pool.checkedout()
    checked_in = pool.checkedin()
    overflow = pool.overflow()
    max_overflow = pool._max_overflow

    max_connections = pool_size + max_overflow
    available_connections = max_connections - checked_out

    utilization = round((checked_out / max_connections) * 100, 2) if max_connections > 0 else 0.0

    return {
        "pool_size": pool_size,
        "checked_out": checked_out,
        "checked_in": checked_in,
        "overflow": overflow,
        "max_overflow": max_overflow,
        "max_connections": max_connections,
        "available_connections": available_connections,
        "utilization_percent": utilization,
    }
