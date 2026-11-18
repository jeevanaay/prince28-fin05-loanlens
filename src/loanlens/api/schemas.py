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
