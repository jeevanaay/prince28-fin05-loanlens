"""App factory: build a fully wired FastAPI app from settings."""

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from loanlens.api.errors import register_error_handlers
from loanlens.api.middleware import request_context
from loanlens.api.routes import documents, health
from loanlens.config import Settings, get_settings
from loanlens.db.session import make_engine, make_sessionmaker
from loanlens.logging_setup import setup_logging

logger = logging.getLogger("loanlens")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = make_engine(settings)
        app.state.engine = engine
        app.state.session_factory = make_sessionmaker(engine)

        logger.info("database session factory initialized")

        try:
            yield
        finally:
            await engine.dispose()
            logger.info("database engine disposed")

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.settings = settings

    app.middleware("http")(request_context)
    register_error_handlers(app)

    v1 = APIRouter(prefix="/v1")
    v1.include_router(documents.router)

    app.include_router(health.router)
    app.include_router(v1)

    return app
