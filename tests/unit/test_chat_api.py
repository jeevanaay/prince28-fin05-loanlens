"""Tests for the chat and usage API."""


def test_chat_non_streaming(client):
    response = client.post(
        "/v1/chat",
        json={"message": "Hello", "stream": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "A fake answer."
    assert data["provider"] == "fake"


def test_chat_streaming(client):
    response = client.post(
        "/v1/chat",
        json={"message": "Hello", "stream": True},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'data: {"delta": "A "' in response.text
    assert "event: done" in response.text


def test_chat_rejects_empty_message(client):
    response = client.post(
        "/v1/chat",
        json={"message": "", "stream": False},
    )

    assert response.status_code == 422


def test_chat_rejects_message_over_4000_characters(client):
    response = client.post(
        "/v1/chat",
        json={"message": "a" * 4001, "stream": False},
    )

    assert response.status_code == 422


def test_usage_endpoint(client):
    response = client.get("/v1/usage")

    assert response.status_code == 200
    data = response.json()
    assert "days" in data
    assert "total_cost_inr" in data
    assert "calls" in data


def test_usage_rejects_invalid_days(client):
    response = client.get("/v1/usage?days=0")

    assert response.status_code == 422


def test_usage_rejects_days_over_90(client):
    response = client.get("/v1/usage?days=91")

    assert response.status_code == 422
