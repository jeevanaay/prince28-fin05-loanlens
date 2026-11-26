from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Short = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=80),
]

Values = Annotated[list[Short], Field(max_length=8)]

Kind = Literal[
    "guideline",
    "rule",
    "notice",
    "list",
    "report",
    "faq",
    "form",
    "tutorial",
    "reference",
    "other",
]


class DocMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_kind: Kind
    year: int | None = None
    language: Literal["en", "ta", "hi", "other"]
    summary: Annotated[str, StringConstraints(min_length=20, max_length=300)]
    topics: Annotated[Values, Field(min_length=1, max_length=6)]

    # LoanLens-specific fields
    lender: Short | None = None
    scheme: Short | None = None
    max_amount: Short | None = None
    collateral_threshold: Short | None = None
    subsidy_income_limit: Short | None = None

    @field_validator("topics")
    @classmethod
    def normalize_topics(cls, topics: list[str]) -> list[str]:
        normalized = [topic.lower() for topic in topics]

        if len(normalized) != len(set(normalized)):
            raise ValueError("topics must be unique")

        return normalized
