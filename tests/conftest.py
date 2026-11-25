"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from loanlens.api.deps import get_usage_repository
from loanlens.api.main import create_app
from loanlens.config import get_settings
from loanlens.llm.gateway import FakeLLM, LLMGateway


class FakeUsageRepository:
    """Return empty usage data without connecting to the database."""

    async def by_day(self, days: int = 7) -> list[dict]:
        return []


@pytest.fixture
def llm():
    """Provide a fake LLM for API tests."""
    return FakeLLM()


@pytest.fixture
def client(llm, monkeypatch):
    """Create a test client with fake LLM and usage dependencies."""
    from loanlens.api import main

    monkeypatch.setattr(
        main,
        "build_gateway",
        lambda settings, recorder=None: LLMGateway(providers=[llm]),
    )

    app = create_app(get_settings())
    app.dependency_overrides[get_usage_repository] = lambda: FakeUsageRepository()
    app.state.system_prompt = "You are a test assistant."

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
