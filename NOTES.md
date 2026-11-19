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

# LoanLens — Day 4 Technical Notes

## 8. Docker Configuration

- Docker multi-stage build with Python 3.12 slim
- Runtime image: `prince28-fin05-loanlens-api`
- PostgreSQL: `pgvector/pgvector:pg17`
- Redis: `redis:7-alpine`
- API: FastAPI running on port 8000
- PostgreSQL host port: 5433
- Redis port: 6379
- API port: 8000

Docker Compose services:

| Service | Purpose |
|---|---|
| `db` | PostgreSQL database |
| `redis` | Redis service |
| `migrate` | Runs Alembic migrations and seed loader |
| `api` | FastAPI application |

A named Docker volume, `pgdata17`, is used for PostgreSQL persistence.

## 9. Docker Image Verification

Image size:

```text
Disk usage: 301 MB
Content size: 70 MB
```

The image is below the 400 MB target.

Non-root container verification:

```text
uid=999(app) gid=999(app) groups=999(app)
```

The application runs as the non-root `app` user.

## 10. Docker Compose Health and Dependencies

Verified using:

```powershell
docker compose config
docker compose ps
```

- PostgreSQL health check: Passed
- Redis health check: Passed
- Migration service: Completed successfully
- API health check: Passed
- API waits for healthy PostgreSQL and Redis and successful migration completion.

## 11. Migration and Seed Verification

Latest migration:

```text
07a82ad9cd94
```

Migration history:

| Revision | Description |
|---|---|
| `109f18291bfb` | Create documents and pages |
| `0899d658d997` | Add metadata GIN index |
| `07a82ad9cd94` | Add typed lender column and B-tree index |

Migration command:

```powershell
docker compose logs migrate
```

Seed loader — first execution:

```text
records=20 inserted=20 updated=0 unchanged=0
```

Repeated execution:

```text
records=20 inserted=0 updated=0 unchanged=20
```

The loader correctly handles repeated execution without duplicating records.

## 12. API Health and Readiness Verification

Endpoints:

| Endpoint | Purpose |
|---|---|
| `/health` | Application health |
| `/ready` | Application and database readiness |
| `/docs` | Swagger API documentation |

Verified:

- `/health` returned `status: ok`.
- `/ready` returned `status: ready` with `database: True`.
- `/v1/documents` returned 20 documents.

Database outage test:

- Stopped PostgreSQL.
- `/health` continued returning HTTP 200.
- `/ready` reported `not_ready` with `database: false`.

Recovery test:

- Restarted PostgreSQL.
- `/ready` recovered to `ready` with `database: true`.

## 13. Unit and Integration Tests

Unit tests:

```powershell
uv run poe test
```

Result:

```text
31 passed
```

Integration tests:

```powershell
uv run poe test-integration
```

Result:

```text
9 passed
```

Integration test database cleanup was verified:

```sql
SELECT datname
FROM pg_database
WHERE datname LIKE 'loanlens_test_%';
```

Result:

```text
(0 rows)
```

Temporary test databases are successfully removed after the integration test run.

## 14. Coverage Report

Command:

```powershell
uv run poe cov
```

Result:

```text
TOTAL    338    84    32    3    72%

31 passed, 9 skipped
```

- Total statements: 338
- Missing statements: 84
- Statement coverage: 72%
- Branch partials: 3
- Integration tests were skipped in this coverage run because the coverage task did not configure `TEST_DATABASE_URL`. They were run separately and all 9 passed.

Modules with the largest coverage gaps:

| Module | Coverage |
|---|---:|
| `store.py` | 0% |
| `repository.py` | 24% |
| `session.py` | 44% |

## 15. Day 4 Verification Summary

| Requirement | Result |
|---|---|
| Docker image below 400 MB | Passed |
| Non-root runtime user | Passed |
| PostgreSQL health check | Passed |
| Redis health check | Passed |
| Migration and seed service | Passed |
| API health and readiness | Passed |
| Database outage and recovery | Verified |
| Unit tests | 31 passed |
| Integration tests | 9 passed |
| Temporary database cleanup | Verified |
| Coverage report | 72% |
