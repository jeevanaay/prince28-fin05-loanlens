"""Pydantic response schemas for LoanLens API."""

from pydantic import BaseModel, ConfigDict


class Record(BaseModel):
    """Education loan scheme record."""

    model_config = ConfigDict(extra="forbid")

    id: str
    lender: str
    scheme: str
    title: str
    source_url: str | None = None
    licence: str | None = None
    published_on: str | None = None
    doc_type: str
    max_amount: int | None = None
    collateral_threshold: str | None = None
    margin_pct: float | None = None
    moratorium: str | None = None
    interest_rule: str | None = None
    subsidy_income_limit: int | None = None


class DocumentListResponse(BaseModel):
    """Paginated response containing education loan records."""

    total: int
    limit: int
    offset: int
    items: list[Record]


class ParsedDocument(BaseModel):
    """Successfully extracted source document metadata."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    source_url: str | None = None
    licence: str | None = None
    doc_type: str
    doc_kind: str
    year: int | None = None
    language: str
    summary: str
    topics: list[str]
    scheme: str | None = None
    max_amount: str | None = None
    collateral_threshold: str | None = None
    subsidy_income_limit: str | None = None


class ParsedDocumentListResponse(BaseModel):
    """Paginated extracted source documents."""

    total: int
    limit: int
    offset: int
    items: list[ParsedDocument]
