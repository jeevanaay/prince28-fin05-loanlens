import pytest
from pydantic import ValidationError

from loanlens.api.deps import get_repository
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


def test_filter_documents_by_lender(client):
    r = client.get(
        "/v1/documents",
        params={"lender": "State Bank of India"},
    )

    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert [d["id"] for d in r.json()["items"]] == ["001"]


def test_filter_documents_by_scheme(client):
    r = client.get(
        "/v1/documents",
        params={"scheme": "Vidya"},
    )

    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert [d["id"] for d in r.json()["items"]] == ["003"]


def test_filter_documents_by_lender_and_scheme(client):
    r = client.get(
        "/v1/documents",
        params={
            "lender": "Bank",
            "scheme": "Scholar",
        },
    )

    assert r.status_code == 200
    assert r.json()["total"] == 1
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


# Statistics endpoint tests


def test_document_stats_returns_correct_totals(client):
    r = client.get("/v1/documents/stats")

    assert r.status_code == 200

    body = r.json()
    assert body["total_documents"] == 3
    assert body["unique_lenders"] == 3
    assert body["unique_schemes"] == 3


def test_document_stats_groups_documents_by_lender(client):
    r = client.get("/v1/documents/stats")

    assert r.status_code == 200

    assert r.json()["documents_by_lender"] == [
        {"lender": "Bank of Baroda", "count": 1},
        {"lender": "Government of India", "count": 1},
        {"lender": "State Bank of India", "count": 1},
    ]


def test_document_stats_groups_documents_by_type(client):
    r = client.get("/v1/documents/stats")

    assert r.status_code == 200

    assert r.json()["documents_by_type"] == [
        {"doc_type": "government_scheme", "count": 1},
        {"doc_type": "loan_scheme", "count": 2},
    ]


def test_document_stats_handles_empty_database(client):
    class EmptyRepository:
        async def stats(self):
            return {
                "total_documents": 0,
                "unique_lenders": 0,
                "unique_schemes": 0,
                "documents_by_lender": [],
                "documents_by_type": [],
            }

    client.app.dependency_overrides[get_repository] = lambda: EmptyRepository()

    r = client.get("/v1/documents/stats")

    assert r.status_code == 200
    assert r.json() == {
        "total_documents": 0,
        "unique_lenders": 0,
        "unique_schemes": 0,
        "documents_by_lender": [],
        "documents_by_type": [],
    }


# Sorting endpoint tests


def test_sort_documents_by_lender_ascending(client):
    r = client.get(
        "/v1/documents",
        params={"sort_by": "lender", "sort_order": "asc"},
    )

    assert r.status_code == 200
    assert [item["id"] for item in r.json()["items"]] == [
        "002",
        "003",
        "001",
    ]


def test_sort_documents_by_lender_descending(client):
    r = client.get(
        "/v1/documents",
        params={"sort_by": "lender", "sort_order": "desc"},
    )

    assert r.status_code == 200
    assert [item["id"] for item in r.json()["items"]] == [
        "001",
        "003",
        "002",
    ]


def test_sort_documents_by_scheme_ascending(client):
    r = client.get(
        "/v1/documents",
        params={"sort_by": "scheme", "sort_order": "asc"},
    )

    assert r.status_code == 200
    assert [item["id"] for item in r.json()["items"]] == [
        "002",
        "001",
        "003",
    ]


def test_sort_documents_by_max_amount_descending(client):
    r = client.get(
        "/v1/documents",
        params={"sort_by": "max_amount", "sort_order": "desc"},
    )

    assert r.status_code == 200
    assert [item["id"] for item in r.json()["items"]] == [
        "001",
        "002",
        "003",
    ]


def test_sort_documents_by_published_date_descending(client):
    r = client.get(
        "/v1/documents",
        params={"sort_by": "published_on", "sort_order": "desc"},
    )

    assert r.status_code == 200
    assert [item["id"] for item in r.json()["items"]] == [
        "001",
        "002",
        "003",
    ]


def test_sort_documents_with_filter_and_pagination(client):
    r = client.get(
        "/v1/documents",
        params={
            "sort_by": "max_amount",
            "sort_order": "desc",
            "limit": 1,
            "offset": 1,
        },
    )

    body = r.json()

    assert r.status_code == 200
    assert body["total"] == 3
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == "002"


def test_invalid_sort_field_returns_422(client):
    r = client.get(
        "/v1/documents",
        params={"sort_by": "invalid_field"},
    )

    assert r.status_code == 422


def test_invalid_sort_order_returns_422(client):
    r = client.get(
        "/v1/documents",
        params={"sort_order": "random"},
    )

    assert r.status_code == 422
