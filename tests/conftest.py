import json

import pytest
from fastapi.testclient import TestClient

from loanlens.api.deps import get_db_session, get_repository
from loanlens.api.main import create_app
from loanlens.config import Settings

SAMPLE = [
    {"id": "001", "title": "Alpha guideline", "year": 2023},
    {"id": "002", "title": "Beta circular", "year": 2024},
    {"id": "003", "title": "Gamma notice", "year": 2025},
]


class FakeRepository:
    """In-memory repository for isolated API tests."""

    def __init__(self, records):
        self.records = records

    async def search(self, q=None):
        rows = self.records

        if q:
            needle = q.lower()
            rows = [
                row for row in rows if any(needle in str(value).lower() for value in row.values())
            ]

        return rows

    async def get(self, document_id):
        return next(
            (row for row in self.records if row["id"] == document_id),
            None,
        )


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
