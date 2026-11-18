"""Database operations for LoanLens documents."""

from typing import Any

from sqlalchemy import Text, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from loanlens.db.models import Document


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _serialize(document: Document) -> dict[str, Any]:
        """Convert a database document into the existing API record format."""
        return {
            "id": document.external_id,
            **document.metadata_,
            "title": document.title,
            "source_url": document.source_url,
            "licence": document.licence,
            "doc_type": document.doc_type,
            "published_on": (document.published_on.isoformat() if document.published_on else None),
        }

    async def search(
        self,
        q: str | None = None,
    ) -> list[dict[str, Any]]:
        statement = select(Document).order_by(Document.external_id)

        if q:
            pattern = f"%{q}%"
            statement = statement.where(
                func.concat(
                    Document.title,
                    " ",
                    cast(Document.metadata_, Text),
                ).ilike(pattern)
            )

        result = await self.session.scalars(statement)
        return [self._serialize(document) for document in result.all()]

    async def get(self, document_id: str) -> dict[str, Any] | None:
        statement = select(Document).where(Document.external_id == document_id)
        document = await self.session.scalar(statement)

        if document is None:
            return None

        return self._serialize(document)

    async def ready(self) -> bool:
        """Check whether the database can execute a query."""
        result = await self.session.execute(select(func.count()).select_from(Document))
        return result.scalar_one() >= 0
