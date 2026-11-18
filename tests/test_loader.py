from scripts.load_db import fingerprint, to_row


def test_to_row_removes_null_metadata():
    record = {
        "id": "test-001",
        "lender": "State Bank of India",
        "scheme": "Student Loan Scheme",
        "max_amount": 750000,
        "margin_pct": None,
        "moratorium": None,
        "interest_rule": None,
        "subsidy_income_limit": None,
        "source_url": None,
        "licence": None,
        "published_on": None,
    }

    row = to_row(record)

    assert row["lender"] == "State Bank of India"
    assert row["metadata_"] == {
        "scheme": "Student Loan Scheme",
        "max_amount": 750000,
    }


def test_to_row_preserves_zero_values():
    record = {
        "id": "test-002",
        "lender": "Canara Bank",
        "scheme": "Canara Vidya Turant",
        "margin_pct": 0,
        "max_amount": 0,
        "moratorium": None,
    }

    row = to_row(record)

    assert row["metadata_"]["margin_pct"] == 0
    assert row["metadata_"]["max_amount"] == 0
    assert "moratorium" not in row["metadata_"]
    assert "lender" not in row["metadata_"]


def test_to_row_preserves_non_null_metadata():
    record = {
        "id": "test-003",
        "lender": "Bank of Baroda",
        "scheme": "Baroda Scholar",
        "collateral_threshold": "Collateral required above applicable limits",
        "margin_pct": 10,
        "moratorium": "Course period + 1 year",
    }

    row = to_row(record)

    assert row["lender"] == "Bank of Baroda"
    assert row["metadata_"] == {
        "scheme": "Baroda Scholar",
        "collateral_threshold": "Collateral required above applicable limits",
        "margin_pct": 10,
        "moratorium": "Course period + 1 year",
    }


def test_fingerprint_is_deterministic():
    record = {
        "id": "test-004",
        "lender": "State Bank of India",
        "scheme": "Global Ed-Vantage",
    }

    assert fingerprint(record) == fingerprint(record)


def test_fingerprint_changes_when_record_changes():
    original = {
        "id": "test-005",
        "lender": "State Bank of India",
        "max_amount": 1000000,
    }

    modified = {
        "id": "test-005",
        "lender": "State Bank of India",
        "max_amount": 2000000,
    }

    assert fingerprint(original) != fingerprint(modified)


def test_to_row_uses_lender_as_title():
    record = {
        "id": "test-006",
        "lender": "Indian Overseas Bank",
        "scheme": "Vidya Jyothi",
    }

    row = to_row(record)

    assert row["title"] == "Indian Overseas Bank"
    assert row["lender"] == "Indian Overseas Bank"


def test_to_row_handles_missing_lender():
    record = {
        "id": "test-007",
        "scheme": "Example Scheme",
    }

    row = to_row(record)

    assert row["lender"] is None
    assert "lender" not in row["metadata_"]
