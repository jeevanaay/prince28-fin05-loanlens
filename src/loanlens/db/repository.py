"""Database operations for LoanLens documents."""

from typing import Any, Literal

from sqlalchemy import BigInteger, Text, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from loanlens.db.models import Document

SortField = Literal[
    "external_id",
    "lender",
    "scheme",
    "max_amount",
    "published_on",
]

SortOrder = Literal["asc", "desc"]


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _serialize(document: Document) -> dict[str, Any]:
        """Convert a database document into the existing API record format."""
        return {
            "id": document.external_id,
            **document.metadata_,
            "lender": document.lender,
            "title": document.title,
            "source_url": document.source_url,
            "licence": document.licence,
            "doc_type": document.doc_type,
            "published_on": (document.published_on.isoformat() if document.published_on else None),
        }

    async def search(
        self,
        q: str | None = None,
        lender: str | None = None,
        scheme: str | None = None,
        sort_by: SortField = "external_id",
        sort_order: SortOrder = "asc",
    ) -> list[dict[str, Any]]:
        """Search documents with filtering and database-level sorting."""

        statement = select(Document)

        if q:
            pattern = f"%{q}%"
            statement = statement.where(
                func.concat(
                    Document.title,
                    " ",
                    cast(Document.metadata_, Text),
                ).ilike(pattern)
            )

        if lender:
            statement = statement.where(Document.lender.ilike(f"%{lender}%"))

        if scheme:
            statement = statement.where(Document.metadata_["scheme"].astext.ilike(f"%{scheme}%"))

        sort_columns = {
            "external_id": Document.external_id,
            "lender": Document.lender,
            "scheme": Document.metadata_["scheme"].astext,
            "max_amount": cast(
                Document.metadata_["max_amount"].astext,
                BigInteger,
            ),
            "published_on": Document.published_on,
        }

        sort_column = sort_columns[sort_by]

        if sort_order == "desc":
            statement = statement.order_by(
                sort_column.desc().nullslast(),
                Document.external_id.asc(),
            )
        else:
            statement = statement.order_by(
                sort_column.asc().nullslast(),
                Document.external_id.asc(),
            )

        result = await self.session.scalars(statement)
        return [self._serialize(document) for document in result.all()]

    async def get(self, document_id: str) -> dict[str, Any] | None:
        statement = select(Document).where(Document.external_id == document_id)
        document = await self.session.scalar(statement)

        if document is None:
            return None

        return self._serialize(document)

    async def stats(self) -> dict[str, Any]:
        """Return aggregate statistics about stored documents."""

        total_documents = await self.session.scalar(select(func.count(Document.id)))

        unique_lenders = await self.session.scalar(
            select(func.count(func.distinct(Document.lender))).where(
                Document.lender.is_not(None),
                Document.lender != "",
            )
        )

        unique_schemes = await self.session.scalar(
            select(func.count(func.distinct(Document.metadata_["scheme"].astext))).where(
                Document.metadata_["scheme"].astext.is_not(None),
                Document.metadata_["scheme"].astext != "",
            )
        )

        lender_statement = (
            select(
                Document.lender.label("lender"),
                func.count(Document.id).label("count"),
            )
            .where(
                Document.lender.is_not(None),
                Document.lender != "",
            )
            .group_by(Document.lender)
            .order_by(Document.lender)
        )

        lender_result = await self.session.execute(lender_statement)

        documents_by_lender = [{"lender": row.lender, "count": row.count} for row in lender_result]

        type_statement = (
            select(
                Document.doc_type,
                func.count(Document.id).label("count"),
            )
            .group_by(Document.doc_type)
            .order_by(Document.doc_type)
        )

        type_result = await self.session.execute(type_statement)

        documents_by_type = [{"doc_type": row.doc_type, "count": row.count} for row in type_result]

        return {
            "total_documents": total_documents or 0,
            "unique_lenders": unique_lenders or 0,
            "unique_schemes": unique_schemes or 0,
            "documents_by_lender": documents_by_lender,
            "documents_by_type": documents_by_type,
        }

    async def ready(self) -> bool:
        """Check whether the database can execute a query."""
        result = await self.session.execute(select(func.count()).select_from(Document))
        return result.scalar_one() >= 0
