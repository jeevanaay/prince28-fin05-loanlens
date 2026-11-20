# LoanLens â€” Day 3 Technical Notes

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

# LoanLens â€” Day 4 Technical Notes

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

Seed loader â€” first execution:

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
### Stretch Task: Docker Layer Analysis

The largest application layer is the copied Python virtual environment (`/app/.venv`) at 96.2 MB because it contains the installed application dependencies.

### Stretch Task: API Restart on Database Restart

Added `restart: true` under the API service's database dependency.

Tested using `docker compose restart db`. PostgreSQL restarted successfully, and Docker Compose automatically restarted the dependent API container. The API returned to a healthy state after startup.

# LoanLens — Day 5 Deployment and CI/CD Notes

## 16. GitHub Actions CI/CD

Workflow: `.github/workflows/ci.yml`

Pipeline stages:

| Job | Responsibility |
|---|---|
| Lint and test | Ruff checks and pytest unit tests |
| Build and publish Docker image | Build Docker image and publish to GHCR |

Verification:
- Ruff lint: Passed
- Ruff formatting: Passed
- Unit tests: 35 passed
- Docker build: Passed
- GHCR image publishing: Verified

Latest successful workflow:
- Workflow: LoanLens CI
- Run: #12
- Commit: `9e8a362`
- Branch: `main`
- Duration: 45 seconds
- Status: Success

## 17. GitHub Actions Security

Implemented least-privilege permissions.

| Scope | Permission |
|---|---|
| Workflow | `contents: read` |
| Test job | `contents: read` |
| Docker job | `contents: read`, `packages: write` |

- Docker publishing permission is restricted to the Docker job.
- GHCR authentication uses the automatically provided `GITHUB_TOKEN`.
- Repository secrets: None.
- Environment secrets: None.
- Render and Neon credentials remain configured in Render.

Security improvement:
- PR #13 — Security: Scope package write permission to Docker job.
- Status: Merged.
- Commit: `9e8a362`.

## 18. Main Branch Protection

GitHub ruleset:
- Ruleset name: `main`
- Enforcement: Active
- Target: Default branch (`main`)
- Pull requests required before merging.
- Required status check: `Lint and test`.
- Branches must be up to date before merging.
- Force pushes blocked.
- Required approval count: 0.

## 19. Production Deployment

Hosting: Render Web Service

Service: `prince28-fin05-loanlens`

Production URL:
https://prince28-fin05-loanlens.onrender.com

Database: Neon PostgreSQL

Production endpoints:

| Endpoint | Purpose |
|---|---|
| `/health` | Application health |
| `/ready` | Database readiness |
| `/docs` | Swagger API documentation |

Latest production deployment:
- Commit: `9e8a362`
- Status: Live
- Deployment duration: 46.6 seconds

Health verification:
- `/health`: HTTP 200, status `ok`.
- `/ready`: Previously verified as `ready`, database connected.

## 20. Uptime Monitoring

Monitoring service: UptimeRobot

- Monitor endpoint: `/health`
- Monitoring status: UP
- Monitoring interval: 5 minutes
- Public status page:
  https://stats.uptimerobot.com/0ObUsW7ASp

The health endpoint supports both GET and HEAD requests.

## 21. Rollback Readiness

Rollback platform: Render

Current production deployment:
- Commit: `9e8a362`
- Status: Live

Previous successful deployment:
- Commit: `c5a0556`
- Deployment duration: 51.1 seconds
- Status: Deploy succeeded
- Deployment date: November 20, 2026

Rollback readiness verification:
- Previous successful deployment visible in Render deployment history.
- Render rollback action available for the previous deployment.
- Production health endpoint verified after the latest deployment.

Rollback procedure:
1. Open the Render service deployment history.
2. Identify the last known-good deployment.
3. Open its deployment details.
4. Use the Rollback action if recovery is required.
5. Verify `/health` and `/ready` after rollback.
6. Check application logs and confirm database connectivity.

Important:
- No production rollback was executed during this verification.
- The rollback action and previous successful deployment were inspected.
- Render rollback changes the deployed application version; it does not automatically reverse database migrations.
- Database schema compatibility must be checked before rolling back application code.

Result: Rollback readiness inspected; actual rollback drill not performed.

## 22. Week 1 Git Milestone

Git tag:
`week-1`

Description:
`LoanLens Week 1: Backend, Docker, CI/CD and production deployment`

Tag was created, pushed and verified on GitHub.

Repository:
https://github.com/jeevanaay/prince28-fin05-loanlens

## 23. Day 5 Verification Summary

| Requirement | Result |
|---|---|
| GitHub Actions CI | Passed |
| Docker image publishing | Verified |
| Render deployment | Live |
| Neon database connectivity | Verified |
| GitHub branch protection | Configured |
| Least-privilege permissions | Implemented |
| Secrets audit | Completed |
| UptimeRobot monitoring | UP |
| README production links and badges | Updated |
| Week 1 Git tag | Pushed |
| Rollback readiness | Inspected |
| Actual rollback execution | Not performed |
