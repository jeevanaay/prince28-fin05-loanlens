import pytest
from pydantic import ValidationError

from loanlens.config import Settings


def test_health_is_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ready_when_database_available(client):
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json()["checks"]["database"] is True


def test_ready_is_503_when_database_unavailable(client):
    from loanlens.api.deps import get_db_session

    class UnavailableSession:
        async def execute(self, statement):
            raise RuntimeError("Database unavailable")

    async def unavailable_session():
        yield UnavailableSession()

    client.app.dependency_overrides[get_db_session] = unavailable_session

    r = client.get("/ready")

    assert r.status_code == 503
    assert r.json()["checks"]["database"] is False


def test_list_documents_paginates(client):
    r = client.get("/v1/documents", params={"limit": 2})
    body = r.json()

    assert r.status_code == 200
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_search_filters_records(client):
    r = client.get("/v1/documents", params={"q": "beta"})

    assert [d["id"] for d in r.json()["items"]] == ["002"]


def test_get_document_found(client):
    r = client.get("/v1/documents/001")

    assert r.status_code == 200
    assert r.json()["title"] == "Alpha guideline"


def test_missing_document_is_problem_details(client):
    r = client.get("/v1/documents/999")

    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")

    body = r.json()
    assert body["status"] == 404
    assert body["title"] == "Not Found"
    assert body["request_id"] == r.headers["X-Request-ID"]


def test_bad_limit_is_422_problem(client):
    r = client.get("/v1/documents", params={"limit": 0})

    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "query.limit"


def test_request_id_is_echoed(client):
    r = client.get("/health", headers={"X-Request-ID": "abc123"})

    assert r.headers["X-Request-ID"] == "abc123"


def test_app_refuses_to_start_without_app_env(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


# Additional API tests


def test_list_documents_default_pagination(client):
    r = client.get("/v1/documents")
    body = r.json()

    assert r.status_code == 200
    assert body["total"] == 3
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert len(body["items"]) == 3


def test_list_documents_with_offset(client):
    r = client.get("/v1/documents", params={"limit": 2, "offset": 1})
    body = r.json()

    assert r.status_code == 200
    assert body["total"] == 3
    assert [item["id"] for item in body["items"]] == ["002", "003"]


def test_search_returns_empty_results_when_no_match(client):
    r = client.get("/v1/documents", params={"q": "nonexistent"})

    assert r.status_code == 200
    assert r.json()["total"] == 0
    assert r.json()["items"] == []


def test_list_documents_accepts_maximum_limit(client):
    r = client.get("/v1/documents", params={"limit": 100})

    assert r.status_code == 200
    assert r.json()["limit"] == 100
    assert r.json()["total"] == 3


def test_list_documents_rejects_negative_offset(client):
    r = client.get("/v1/documents", params={"offset": -1})

    assert r.status_code == 422


def test_search_rejects_query_longer_than_200_characters(client):
    r = client.get("/v1/documents", params={"q": "a" * 201})

    assert r.status_code == 422
