import json

import pytest
from fastapi.testclient import TestClient

from loanlens.api.deps import get_db_session, get_repository
from loanlens.api.main import create_app
from loanlens.config import Settings

SAMPLE = [
    {
        "id": "001",
        "lender": "State Bank of India",
        "scheme": "Global Ed-Vantage",
        "title": "Alpha guideline",
        "source_url": None,
        "licence": None,
        "published_on": "2025-01-15",
        "doc_type": "loan_scheme",
        "max_amount": 30000000,
        "collateral_threshold": "Collateral-free up to INR 5000000",
        "margin_pct": 10,
        "moratorium": "Course period + 6 months",
        "interest_rule": "Floating rate",
        "subsidy_income_limit": None,
    },
    {
        "id": "002",
        "lender": "Bank of Baroda",
        "scheme": "Baroda Scholar",
        "title": "Beta circular",
        "source_url": None,
        "licence": None,
        "published_on": "2024-06-10",
        "doc_type": "loan_scheme",
        "max_amount": 15000000,
        "collateral_threshold": "Collateral required above applicable limits",
        "margin_pct": None,
        "moratorium": "Course period + 1 year",
        "interest_rule": "Simple interest during moratorium",
        "subsidy_income_limit": None,
    },
    {
        "id": "003",
        "lender": "Government of India",
        "scheme": "PM-Vidyalaxmi",
        "title": "Gamma notice",
        "source_url": None,
        "licence": None,
        "published_on": None,
        "doc_type": "government_scheme",
        "max_amount": None,
        "collateral_threshold": "Collateral-free for eligible institutions",
        "margin_pct": None,
        "moratorium": "Course period + 1 year",
        "interest_rule": "Eligible interest subvention",
        "subsidy_income_limit": 800000,
    },
]


class FakeRepository:
    """In-memory repository for isolated API tests."""

    def __init__(self, records):
        self.records = records

    async def search(
        self,
        q=None,
        lender=None,
        scheme=None,
        sort_by="external_id",
        sort_order="asc",
    ):
        rows = self.records

        if q:
            needle = q.lower()
            rows = [
                row for row in rows if any(needle in str(value).lower() for value in row.values())
            ]

        if lender:
            needle = lender.lower()
            rows = [row for row in rows if needle in str(row.get("lender", "")).lower()]

        if scheme:
            needle = scheme.lower()
            rows = [row for row in rows if needle in str(row.get("scheme", "")).lower()]

        sort_keys = {
            "external_id": lambda row: row["id"],
            "lender": lambda row: row.get("lender"),
            "scheme": lambda row: row.get("scheme"),
            "max_amount": lambda row: row.get("max_amount"),
            "published_on": lambda row: row.get("published_on"),
        }

        if sort_by in sort_keys:
            sort_key = sort_keys[sort_by]

            non_null_rows = [row for row in rows if sort_key(row) is not None]
            null_rows = [row for row in rows if sort_key(row) is None]

            # Sort IDs first so equal primary values retain ascending ID order.
            non_null_rows.sort(key=lambda row: row["id"])

            non_null_rows.sort(
                key=lambda row: sort_key(row),
                reverse=sort_order == "desc",
            )

            rows = non_null_rows + sorted(
                null_rows,
                key=lambda row: row["id"],
            )

        return rows

    async def get(self, document_id):
        return next(
            (row for row in self.records if row["id"] == document_id),
            None,
        )

    async def stats(self):
        """Return statistics calculated from the in-memory records."""
        lenders = [row["lender"] for row in self.records if row.get("lender")]

        schemes = [row["scheme"] for row in self.records if row.get("scheme")]

        lender_counts = {}
        for lender in lenders:
            lender_counts[lender] = lender_counts.get(lender, 0) + 1

        type_counts = {}
        for row in self.records:
            doc_type = row.get("doc_type")
            if doc_type:
                type_counts[doc_type] = type_counts.get(doc_type, 0) + 1

        return {
            "total_documents": len(self.records),
            "unique_lenders": len(set(lenders)),
            "unique_schemes": len(set(schemes)),
            "documents_by_lender": [
                {"lender": lender, "count": count}
                for lender, count in sorted(lender_counts.items())
            ],
            "documents_by_type": [
                {"doc_type": doc_type, "count": count}
                for doc_type, count in sorted(type_counts.items())
            ],
        }


class FakeSession:
    """Fake database session for readiness tests."""

    async def execute(self, statement):
        return None


@pytest.fixture
def data_file(tmp_path):
    path = tmp_path / "records.json"
    path.write_text(json.dumps(SAMPLE), encoding="utf-8")
    return path


@pytest.fixture
def client(data_file):
    settings = Settings(
        app_env="ci",
        data_file=data_file,
    )

    app = create_app(settings)

    app.dependency_overrides[get_repository] = lambda: FakeRepository(SAMPLE)

    async def fake_db_session():
        yield FakeSession()

    app.dependency_overrides[get_db_session] = fake_db_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
