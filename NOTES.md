## D03 ? LoanLens: PostgreSQL Integration (Day 3 Build Lab)

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

# LoanLens Ã¢â‚¬â€ Day 4 Technical Notes

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

Seed loader Ã¢â‚¬â€ first execution:

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

## D05 Ã¢â‚¬â€ LoanLens: Deployment and CI/CD (Day 5 Build Lab)

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

- PR #13 Ã¢â‚¬â€ Security: Scope package write permission to Docker job.
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

### Rollback and Recovery Execution Ã¢â‚¬â€ November 21, 2026

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

---

# D06 Ã¢â‚¬â€ LoanLens: Document Collection and Dataset Capacity

## 24. Document Collection Pipeline

Implemented document collection under `src/loanlens/ingest/fetch.py`.

Collection methods exposed through `scripts/fetch.py`:

| Method | Purpose |
|---|---|
| `urls` | Collect URLs from `data/sources.csv` |
| `sitemap` | Discover documents from sitemaps |
| `repo` | Collect documents from public Git repositories |
| `manual` | Register manually downloaded documents |

### Collection safeguards

- HTTP client: httpx
- Robots policy: Protego
- PDF parsing: pypdf
- Maximum concurrency: 4
- Default per-host delay: 0.5 seconds
- Maximum retries: 3
- Request timeout: 45 seconds
- Failed robots retrieval: fail closed
- Completed documents: skipped when already present
- Partial downloads: temporary `.part` files with atomic replacement
### Source eligibility enforcement

Collection eligibility is enforced across all four collection methods.

| Method | Eligibility control |
|---|---|
| `urls` | Reads status and evidence from `data/sources.csv` |
| `sitemap` | Requires explicit approval and evidence before sitemap access |
| `repo` | Requires explicit approval and evidence before cloning |
| `manual` | Requires explicit approval and evidence before copying |

Supported statuses: `approved`, `pending`, `blocked`.

Unapproved sources are rejected before collection operations. Collection evidence is retained in manifest records.

Eligibility metadata does not itself establish legal permission. Source-specific collection and reuse rights must be independently verified.

## 25. Source Register and Collection

Source register: `data/sources.csv`

The register contains 15 source entries covering government schemes and education-loan information from SBI, Bank of Baroda, Canara Bank and Indian Bank.

Current collection eligibility:
- Total entries: 15
- Pending: 9
- Blocked: 6
- Approved: 0

No sources are currently approved for automated collection.

PM-Vidyalaxmi documents requiring manual collection are registered through the manual collection command rather than automatically crawled.

## 26. Dataset Manifest and Storage

Manifest: `data/manifest.jsonl`

Raw documents: `data/raw/`

- Manifest records contain source metadata, retrieval status, file path and SHA-256 hash.
- Raw documents are excluded from Git.
- The manifest and source register are retained for reproducibility.
- Existing reference documents are stored separately in `data/source_docs/`.

## 27. Initial Dataset Measurement

Measurement date: November 23, 2026

Generated using:

```powershell
uv run python scripts/dataset_report.py
```

Measured results:

| Metric | Result |
|---|---:|
| Manifest entries | 11 |
| Successfully downloaded documents | 8 |
| Total downloaded size | 3,510,332 bytes |
| Total size | 3.35 MB |
| PDF pages detected | 28 |
| Source organisations | 6 |

Source distribution:

| Source | Documents |
|---|---:|
| Ministry of Education | 1 |
| SBI | 3 |
| Canara Bank | 1 |
| Bank of Baroda | 1 |
| Indian Bank | 1 |
| Press Information Bureau | 1 |

PDF detection uses the `%PDF-` file signature rather than relying on file extensions.

## 28. Dataset Capacity Planning

Documentation: `docs/CAPACITY.md`

- Initial source register target: 10 URLs.
- Expanded corpus target: 1,500+ pages.
- Storage projections are estimates based on the measured initial collection.
- Additional bank circulars, FAQs and scheme documents remain to be collected.

## 29. Automated Tests

Test file: `tests/unit/test_fetch.py`

New downloader tests: 19

Verification:

```powershell
uv run pytest tests/unit/test_fetch.py -q
```

Result:

```text
19 passed
```

Full project test suite:

```powershell
uv run poe test
```

Result:

```text
58 passed
```

## 30. Quality Gate Verification

Command:

```powershell
uv run pre-commit run --all-files
```

Results:

- Trailing whitespace: Passed
- End-of-file checks: Passed
- YAML validation: Passed
- TOML validation: Passed
- Large-file checks: Passed
- Private-key detection: Passed
- Ruff lint: Passed
- Ruff formatting: Passed
- Secret detection: Passed

## 31. D06 Verification Summary

| Requirement | Result |
|---|---|
| Document collection module | Implemented |
| URL, sitemap, repository and manual collection interfaces | Implemented |
| Robots.txt compliance | Implemented |
| Retry and host-delay controls | Implemented |
| Manifest and SHA-256 tracking | Implemented |
| Dataset reporting | Implemented |
| Initial source register | Created |
| Initial documents collected | 8 |
| PDF pages detected | 28 |
| New unit tests | 19 passed |
| Full project tests | 58 passed |
| Pre-commit hooks | All passed |

**D06 Status:** Initial document collection pipeline, dataset reporting, capacity documentation and automated tests are implemented. The expanded 1,500+ page corpus and remaining source collection are still pending.


## 32. Forced Interruption and Resume Verification

A controlled local HTTP-server test verified recovery after forcibly
interrupting the document collection process with Ctrl+C.

| Metric | Result |
|---|---:|
| Documents downloaded before interruption | 1 |
| Completed documents skipped after restart | 1 |
| New documents downloaded after restart | 2 |
| Total documents available after resume | 3 |

Verification:
- Document 1 remained downloaded with its original SHA-256 hash.
- Document 2 was interrupted before completion.
- The restarted fetch skipped Document 1.
- Documents 2 and 3 downloaded successfully.
- No duplicate download of Document 1 occurred.

**Result:** Forced interruption and restart/resume test passed using
an isolated local test server and temporary test data.


\# D07 Ã¢â‚¬â€ LoanLens: Document Parsing and PostgreSQL Page Storage



\## 33. Objective



Built a document parsing pipeline to extract clean content from collected PDF and HTML files and store the results in PostgreSQL.



The pipeline captures:

\- Page numbers

\- Extracted text

\- Heading paths

\- Markdown tables

\- Parsing failures and failure reasons



\## 34. Dependencies and Database Migration



Installed:

\- PyMuPDF

\- Trafilatura

\- pypdf



Used SQLAlchemy 2.x with async PostgreSQL integration.



Created and applied migration:



`3880cb25b992\_add\_page\_headings\_and\_parse\_failures.py`



Database changes:

\- Added `headings` JSONB column to `pages`.

\- Created `parse\_failures` table.

\- Added failure tracking fields: path, SHA-256, source URL, reason, detail, attempts and timestamps.



\## 35. Parser Implementation



Created `src/loanlens/ingest/parse.py`.



Implemented:

\- PDF parsing using PyMuPDF.

\- Alternative PDF parsing using pypdf.

\- HTML parsing using Trafilatura.

\- Text parsing.

\- JSON, YAML and CSV parsing.

\- File-type detection.

\- Heading extraction.

\- Markdown table extraction.

\- Parse error handling.



Created `src/loanlens/ingest/store.py` to store parsed documents and pages and track parsing failures.



\## 36. Corpus Ingestion



Created `scripts/parse\_corpus.py` to parse downloaded files from the manifest and store the extracted results in PostgreSQL.



Results:



| Metric | Result |

|---|---:|

| Downloaded files processed | 8 |

| Documents stored | 8 |

| Pages stored | 33 |

| Parsing failures | 0 |



Three additional sources were blocked during collection and were not treated as parser failures.



\## 37. Extraction Quality Improvement



Improved the Baroda Scholar HTML extraction.



The initial extraction included unrelated promotional content, including personal loan and home loan sections.



Refined the extraction to focus on the main article content.



Final result:

\- Extracted characters: 11,919

\- Headings: 8

\- Personal loan promotional content: excluded

\- Home loan promotional content: excluded



Re-ingested the corrected document into PostgreSQL.



\## 38. Parser Comparison

Compared PyMuPDF and pypdf extraction for all 4 available PDF files. HTML extraction was reviewed separately using the current HTML parser.

### PDF Comparison

| File | Similarity | Verdict |
|---|---:|---|
| PM-Vidyalaxmi Guidelines | 96.54% | Minor extraction differences |
| Global Ed-Vantage MITC November 2024 | 62.48% | Review extraction differences |
| PM-Vidyalaxmi Press Release | 97.57% | Minor extraction differences |
| PM-Vidyalaxmi Implementation Memorandum | 93.19% | Minor extraction differences |

The percentages are script-reported text similarity measurements, not measures of extraction accuracy. The Global Ed-Vantage MITC result requires manual review. Its document title is now correctly extracted as "SBI GLOBAL ED-VANTAGE SCHEME".

### HTML Extraction Quality

| File | Characters | Headings | Pages | Extracted title | Verdict |
|---|---:|---:|---:|---|---|
| Global Ed-Vantage Scheme | 5,639 | 5 | 1 | SBI Global Ed-Vantage Scheme | Title and targeted cleanup verified |
| Masters Degree Education Loan India and Abroad | 5,378 | 9 | 1 | Education Loan for Masters Degree Abroad | Title and headings extracted |
| Baroda Scholar Education Loan | 11,920 | 8 | 1 | Baroda Scholar | Targeted extraction cleanup applied |
| Education Loan Interest Rates | 3,540 | 6 | 1 | Education Loan Scheme | Title and headings extracted |
| IB Education Loan IBA | 18,260 | 17 | 1 | Education Loan India - Study Without Limits | Title and headings extracted |
| PM-Vidyalaxmi Official Portal | 10,309 | 0 | 1 | Welcome to PM-Vidyalaxmi Portal for applying Education Loan | Review heading extraction |

HTML character counts and heading counts describe extraction output; they are not similarity scores. HTML results were not compared against an independent second parser.

### Summary

- 4 PDF files compared using PyMuPDF and pypdf.
- 6 HTML files reviewed using the current HTML extraction pipeline.
- All 10 downloaded files were included.
- SBI Global Ed-Vantage Scheme title extraction and cleanup improved.
- SBI Global Ed-Vantage MITC PDF title extraction was verified against the actual PDF.
- Global Ed-Vantage MITC still requires manual extraction review because of its 62.48% similarity result.
- PM-Vidyalaxmi Official Portal still has no detected headings.
- Baroda Scholar extraction cleanup was applied.

**Limitation:** HTML extraction quality was inspected, but no independent parser comparison or HTML similarity score was established.


## 39. PostgreSQL Verification

Re-ingested the complete 10-file corpus after the latest parser and storage changes.

| Database item | Verified result |
|---|---:|
| Total documents | 30 |
| Total pages | 40 |
| Parse failures | 0 |

Verified the parser-extracted titles in PostgreSQL:

- `SBI GLOBAL ED-VANTAGE SCHEME` — PDF, 2 pages.
- `SBI Global Ed-Vantage Scheme` — HTML, 1 page.

Verified page numbers and heading metadata using a real-document SQL query:

- PDF page 1: `Timeline for Disposal of Loan Application`
- PDF page 2: `Customer Service:`
- HTML page 1: 5 headings stored.

Page numbers and heading arrays are correctly persisted in PostgreSQL. The documents inspected contain top-level headings; nested heading paths are covered by synthetic unit tests but still need verification against a real document containing nested sections.

The first re-ingestion completed successfully: 10 successful, 0 failed. A subsequent redundant run was interrupted during Neon connection establishment and did not complete.

## 40. D07 Summary

Completed the document parsing and PostgreSQL page-storage pipeline, with further parser-quality improvements made during validation.

Successfully:

- Parsed all 10 available PDF and HTML files.
- Stored 10 parsed documents and 40 pages in the successful ingestion.
- Added heading metadata and parse-failure tracking.
- Improved PDF heading detection and added regression tests.
- Added prominent first-page PDF title extraction when metadata is missing.
- Improved SBI Global Ed-Vantage Scheme title extraction and HTML cleanup.
- Improved Baroda Scholar HTML extraction.
- Compared PyMuPDF and pypdf on 4 PDFs.
- Reviewed extraction quality for 6 HTML files.
- Verified document, page, heading, title, and failure data in PostgreSQL.
- Confirmed the complete unit test suite passes: 71 tests.
- Fixed and verified two-column reading order for the SBI Global Ed-Vantage MITC PDF.

**Remaining work:** PM-Vidyalaxmi Portal heading detection and real-document nested heading-path verification. Global Ed-Vantage MITC two-column PDF reading order has been corrected and verified.
