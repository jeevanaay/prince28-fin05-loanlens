# LoanLens — Day 3 Technical Notes

## 1. PostgreSQL Integration

- Database: PostgreSQL hosted on Neon
- ORM: SQLAlchemy 2.x (async)
- Driver: asyncpg
- Migration tool: Alembic
- Metadata storage: PostgreSQL JSONB

## 2. Migration History

Two Alembic migrations were created and applied successfully.

| Revision | Description |
|---|---|
| `109f18291bfb` | Create documents and pages |
| `0899d658d997` | Add metadata GIN index |

Verification:

```text
0899d658d997 (head)
```

Migration upgrade, downgrade and re-upgrade were tested successfully.

## 3. Data Loader Verification

The loader was tested for idempotency using 20 sample records.

First execution:

```text
records=20 inserted=20 updated=0 unchanged=0
```

Second execution:

```text
records=20 inserted=0 updated=0 unchanged=20
```

After modifying and restoring a test record:

```text
records=20 inserted=0 updated=1 unchanged=19
```

The loader correctly identifies new, modified and unchanged records.

## 4. PostgreSQL GIN Index Verification

Index:

```text
ix_documents_metadata_gin
```

Index type: GIN

Operator class: `jsonb_path_ops`

Diagnostic query:

```sql
EXPLAIN
SELECT external_id
FROM documents
WHERE metadata @> '{"lender": "State Bank of India"}';
```

Query plan:

```text
Bitmap Heap Scan on documents
  Recheck Cond: (metadata @> '{"lender": "State Bank of India"}'::jsonb)
  -> Bitmap Index Scan on ix_documents_metadata_gin
       Index Cond: (metadata @> '{"lender": "State Bank of India"}'::jsonb)
```

**Observation:** PostgreSQL successfully used `ix_documents_metadata_gin` for the JSONB containment query.

Note: Sequential scans were disabled for this diagnostic query to verify index usability.

## 5. Test Results

| Test category | Passed |
|---|---:|
| API tests | 16 |
| PostgreSQL integration tests | 3 |
| Total | 19 |

Command:

```powershell
python -m pytest -v
```

Result:

```text
19 passed
```

## 6. Code Quality

- Ruff lint: Passed
- Ruff formatting: Passed
- Pre-commit hooks: Passed
- Secret detection: Passed

## 7. GitHub Integration

- Feature branch: `feat/day-03-postgres`
- Pull request: #2
- Status: Merged and closed
- Main branch: Updated and synchronised
- Working tree: Clean

Commit:

```text
0893537
feat: integrate PostgreSQL database with SQLAlchemy and Alembic
```
