"""Persist LLM call records and summarize daily usage."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select

from loanlens.db.models import LlmCall


class DatabaseRecorder:
    """Save each gateway call using the application's session factory."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __call__(self, row: dict) -> None:
        async with self.session_factory() as session:
            session.add(LlmCall(**row))
            await session.commit()


class UsageRepository:
    """Read daily LLM usage and estimated costs."""

    def __init__(self, session):
        self.session = session

    async def by_day(self, days: int = 7) -> list[dict]:
        since = datetime.now(UTC) - timedelta(days=days)

        day = func.date(LlmCall.created_at)

        statement = (
            select(
                day.label("day"),
                func.count(LlmCall.id).label("calls"),
                func.sum(case((LlmCall.status == "error", 1), else_=0)).label("errors"),
                func.sum(case((LlmCall.fallback_used.is_(True), 1), else_=0)).label("fallbacks"),
                func.coalesce(func.sum(LlmCall.tokens_in), 0).label("tokens_in"),
                func.coalesce(func.sum(LlmCall.tokens_out), 0).label("tokens_out"),
                func.coalesce(func.sum(LlmCall.cost_inr), 0).label("cost_inr"),
            )
            .where(LlmCall.created_at >= since)
            .group_by(day)
            .order_by(day)
        )

        result = await self.session.execute(statement)

        return [
            {
                "date": row.day.isoformat(),
                "calls": row.calls,
                "errors": row.errors,
                "fallbacks": row.fallbacks,
                "tokens_in": row.tokens_in,
                "tokens_out": row.tokens_out,
                "cost_inr": float(row.cost_inr),
            }
            for row in result
        ]
