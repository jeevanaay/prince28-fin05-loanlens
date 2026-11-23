"""LoanLens production smoke tests.

Usage:
    uv run python scripts/smoke.py
    uv run python scripts/smoke.py https://example.onrender.com
"""

import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = (
    sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "https://prince28-fin05-loanlens.onrender.com"
)

TIMEOUT = 45
passed = 0
failed = 0


def check(name: str, path: str, validate) -> None:
    global passed, failed

    url = f"{BASE_URL}{path}"
    try:
        request = Request(url, headers={"Accept": "application/json"})

        with urlopen(request, timeout=TIMEOUT) as response:
            if response.status != 200:
                raise AssertionError(f"HTTP {response.status}")

            data = json.loads(response.read().decode("utf-8"))

        validate(data)
        passed += 1
        print(f"  PASS  {name}")

    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        ValueError,
        AssertionError,
        KeyError,
        TypeError,
    ) as error:
        failed += 1
        print(f"  FAIL  {name}: {error}")


def validate_health(data: dict) -> None:
    assert data["status"] == "ok", data
    assert data["app"] == "loanlens", data
    assert data["commit"], "Missing deployed commit"


def validate_readiness(data: dict) -> None:
    assert data["status"] == "ready", data
    assert data["checks"]["database"] is True, data


def validate_documents(data: dict) -> None:
    assert isinstance(data["total"], int), data
    assert data["total"] >= 1, data
    assert isinstance(data["items"], list), data
    assert len(data["items"]) >= 1, data

    first = data["items"][0]
    for field in ("id", "lender", "scheme", "title"):
        assert field in first, f"Missing document field: {field}"


def main() -> int:
    print("\nLoanLens Smoke Tests")
    print(f"Target: {BASE_URL}\n")

    check("API health", "/health", validate_health)
    check("Database readiness", "/ready", validate_readiness)
    check(
        "Document listing",
        "/v1/documents?limit=2",
        validate_documents,
    )

    print(f"\nResults: {passed} passed, {failed} failed.")

    if failed:
        print("Smoke tests FAILED.")
        return 1

    print("All smoke tests PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
