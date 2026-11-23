## D03 — LoanLens: PostgreSQL Integration (Day 3 Build Lab)

## 1. PostgreSQL Integration

- Database: PostgreSQL hosted on Neon
- ORM: SQLAlchemy 2.x (async)
- Driver: asyncpg
- Migration tool: Alembic
- Metadata storage: PostgreSQL JSONB

## 2. Migration History and Verification

Three Alembic migrations were created and applied across the PostgreSQL and Docker build stages.

| Revision | Description | Build stage |
|---|---|---|
| `109f18291bfb` | Create documents and pages | D03 |
| `0899d658d997` | Add metadata GIN index | D03 |
| `07a82ad9cd94` | Add typed lender column and B-tree index | D04 |

Migration verification command:

```powershell
uv run alembic current
uv run alembic history
```

Latest migration:

```text
07a82ad9cd94 (head)
```

Migration upgrade, downgrade and re-upgrade were tested successfully.

The migration history was also verified through Docker Compose during D04.

## 3. Data Loader Verification

The PostgreSQL data loader at `scripts/load_db.py` was tested using 20 sample records.

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

Repeated execution does not create duplicate records, confirming idempotent behaviour.

## 4. PostgreSQL GIN Index and EXPLAIN Verification

Index:

```text
ix_documents_metadata_gin
```

- Index type: GIN
- Operator class: `jsonb_path_ops`
- Indexed column: `documents.metadata`

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

Observation:

PostgreSQL successfully used the GIN index `ix_documents_metadata_gin` for the JSONB containment query.

Sequential scans were disabled for this diagnostic query to verify index usability.

## 5. D03 Verification Summary

| Requirement | Result |
|---|---|
| PostgreSQL integration | Completed |
| SQLAlchemy async integration | Verified |
| Alembic migrations | Verified |
| Migration upgrade and downgrade | Tested |
| Sample records loaded | 20 records |
| Loader idempotency | Verified |
| GIN index creation | Verified |
| JSONB EXPLAIN query | Verified |

**D03 Outcome:** PostgreSQL integration, database migrations, idempotent data loading and GIN index verification were successfully completed.

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
WHERE datname LIKE 'loanlens_test\_%';
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

---

## D05 — LoanLens: Deployment and CI/CD (Day 5 Build Lab)

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

Latest successful workflow recorded during the initial Day 5 verification:

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
- CI Docker publishing does not require a separately configured GitHub personal access token.
- The CD workflow references `DATABASE_URL` and `RENDER_DEPLOY_HOOK` as GitHub Actions secrets.
- Production database and deployment credentials are not hardcoded in workflow files.

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

### Latest Production Deployment

- Commit: `cf18d2a`
- Pull request: #20
- Description: `docs: add official education loan source registry`
- Deployment date: November 23, 2026
- Deployment started: 10:32 AM
- Deployment live: 10:33 AM
- Trigger: Render Deploy Hook
- Status: Live

Previous deployment:

- Commit: `0f540b6`
- Pull request: #19
- Description: `chore: complete Week 1 validation and deployment checks`
- Deployment date: November 23, 2026
- Deployment started: 10:13 AM
- Deployment live: 10:14 AM
- Trigger: Render Deploy Hook
- Status: Live

### Production Health Verification

- `/health`: Previously verified as HTTP 200 with status `ok`.
- `/ready`: Previously verified as `ready`, with the database connected.
- Production deployment history confirms successful deployments of the latest commits.

## 20. Uptime Monitoring

Monitoring service: UptimeRobot

- Monitor endpoint: `/health`
- Monitoring status: UP
- Monitoring interval: 5 minutes
- Public status page:

https://stats.uptimerobot.com/0ObUsW7ASp

The health endpoint supports both GET and HEAD requests.

## 21. Production Rollback and Recovery Drill

Rollback platform: Render

### Objective

Verify that the production service can be rolled back to a previous successful deployment and subsequently restored to a newer deployment.

### Rollback and Recovery Execution — November 21, 2026

Two rollback operations were recorded in the Render deployment history.

| Time | Operation | Deployment / Commit | Result |
|---|---|---|---|
| 1:19 AM | Rollback initiated | Previous deployment `dep-dc04iirrjlhs7388uug0` | Initiated |
| 1:20 AM | Rollback deployment live | `9323df8` | Successful |
| 1:22 AM | Rollback initiated | Previous deployment `dep-dc08vimtlv9c739h201g` | Initiated |
| 1:22 AM | Recovery deployment live | `6cbf87c` | Successful |

### Deployment Details

**Rollback deployment**

- Commit: `9323df8`
- Pull request: #14
- Description: `Docs: Add Day 5 deployment, CI/CD and rollback documentation`
- Rollback duration: 25.8 seconds
- Status: Deploy live

**Recovery deployment**

- Commit: `6cbf87c`
- Pull request: #17
- Description: `feat: trigger Render deployment from GitHub CD`
- Recovery duration: 20.2 seconds
- Status: Deploy live

### Verification

- Render deployment history recorded both rollback operations.
- Both rollback and recovery deployments were reported as successful and live.
- Production `/health` endpoint returned HTTP 200.
- The previous deployment was restored successfully.
- The newer deployment was subsequently restored successfully.
- Database readiness was checked as part of the production verification.

### Rollback Outcome

The production rollback and recovery drill was successfully completed on November 21, 2026.

The drill demonstrated that a previous successful deployment could be restored through the Render dashboard and that a subsequent deployment could bring the application forward again.

### Important Database Consideration

- Render rollback changes the deployed application version; it does not automatically reverse database migrations.
- Database schema compatibility must be checked before rolling back application code.
- Database migrations should remain backward-compatible with the previous application version wherever possible.
## 21A. Deployment Lead Time Verification

Deployment platform: Render

Deployment trigger: GitHub Actions CD workflow using Render Deploy Hook.

### Latest Recorded Deployment

| Metric | Value |
|---|---|
| Commit | `cf18d2a` |
| Pull request | #20 |
| Deployment date | November 23, 2026 |
| Deployment started | 10:32 AM |
| Deployment became live | 10:33 AM |
| Deployment lead time | Approximately 1 minute |
| Trigger | Render Deploy Hook |
| Result | Successful |

### Previous Deployment

| Metric | Value |
|---|---|
| Commit | `0f540b6` |
| Pull request | #19 |
| Deployment started | 10:13 AM |
| Deployment became live | 10:14 AM |
| Deployment lead time | Approximately 1 minute |
| Result | Successful |

### CI Pipeline Duration

The latest recorded successful GitHub Actions CI workflow was:

- Workflow: LoanLens CI
- Run: #12
- Commit: `9e8a362`
- Branch: `main`
- Duration: 45 seconds
- Status: Success

### Lead Time Observation

The recorded production deployments took approximately one minute from deployment initiation to becoming live.

The CI workflow completed in 45 seconds in the recorded run. CI execution time and production deployment lead time are separate measurements.

These results demonstrate that the automated CI/CD and production deployment pipeline can deliver application changes to production quickly.

**D05 Outcome:** CI/CD automation, production deployment, rollback and recovery verification were successfully completed.
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
| Previous deployment availability | Verified |
| Actual production rollback | Successfully executed |
| Recovery deployment | Successfully executed |
| Production health verification | Verified |
| Rollback and recovery drill | Completed |

---

# Overall Week 1 Verification

LoanLens successfully completed the PostgreSQL integration, Docker containerisation, automated testing, CI/CD implementation and production deployment milestones.

The production rollback and recovery drill was also executed on November 21, 2026, using Render's deployment history.

The application was subsequently deployed successfully through Render Deploy Hooks, with the latest recorded production deployment being commit `cf18d2a` on November 23, 2026.
