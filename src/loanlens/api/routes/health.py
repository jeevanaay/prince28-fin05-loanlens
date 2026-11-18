from fastapi import APIRouter, Request, Response
from sqlalchemy import text

from loanlens.api.deps import SessionDep, SettingsDep
from loanlens.db.session import get_pool_status

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: SettingsDep) -> dict[str, str]:
    """Liveness: is the process alive?"""
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }


@router.get("/ready")
async def ready(
    session: SessionDep,
    response: Response,
) -> dict:
    """Readiness: can this instance connect to the database?"""
    try:
        await session.execute(text("SELECT 1"))
        checks = {"database": True}
    except Exception:
        checks = {"database": False}

    ok = all(checks.values())

    if not ok:
        response.status_code = 503

    return {
        "status": "ready" if ok else "not_ready",
        "checks": checks,
    }


@router.get("/pool")
def pool_status(request: Request) -> dict:
    """Return current database connection pool statistics."""
    engine = request.app.state.engine

    return {
        "status": "ok",
        "pool": get_pool_status(engine),
    }
