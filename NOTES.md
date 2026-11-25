# LoanLens – Technical Notes

## D03 – PostgreSQL Integration

### 1. PostgreSQL Integration

- Database: PostgreSQL hosted on Neon

- ORM: SQLAlchemy 2.x (async)

- Driver: asyncpg

- Migration tool: Alembic

- Metadata storage: PostgreSQL JSONB

### 2. Migration History and Verification

Three Alembic migrations were created and applied across the PostgreSQL and Docker build stages.

| Revision | Description | Build stage |

|---|---|---|

| `109f18291bfb` | Create documents and pages | D03 |

| `0899d658d997` | Add metadata GIN index | D03 |

| `07a82ad9cd94` | Add typed lender column and B-tree index | D04 |

Migration verification commands:

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

### 3. Data Loader Verification

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

### 4. PostgreSQL GIN Index and EXPLAIN Verification

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

### 5. D03 Verification Summary

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

---

# D04 – Docker Configuration and API Verification

### 6. Docker Configuration

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

### 7. Docker Image Verification

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

### 8. Docker Compose Health and Dependencies

Verified using:

```powershell

docker compose config

docker compose ps

```

Results:

- PostgreSQL health check: Passed

- Redis health check: Passed

- Migration service: Completed successfully

- API health check: Passed

- API waits for healthy PostgreSQL and Redis and successful migration completion.

### 9. Migration and Seed Verification

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

Seed loader – first execution:

```text

records=20 inserted=20 updated=0 unchanged=0

```

Repeated execution:

```text

records=20 inserted=0 updated=0 unchanged=20

```

The loader correctly handles repeated execution without duplicating records.

### 10. API Health and Readiness Verification

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

### 11. Unit and Integration Tests

Unit tests:

```powershell

uv run poe test

```

Historical D04 result:

```text

31 passed

```

Integration tests:

```powershell

uv run poe test-integration

```

Historical D04 result:

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

### 12. Coverage Report

Command:

```powershell

uv run poe cov

```

Historical result:

```text

TOTAL    338    84    32    3    72%

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

### 13. D04 Verification Summary

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

# D05 – Deployment and CI/CD

### 14. GitHub Actions CI/CD

Workflow: `.github/workflows/ci.yml`

Pipeline stages:

| Job | Responsibility |

|---|---|

| Lint and test | Ruff checks and pytest unit tests |

| Build and publish Docker image | Build Docker image and publish to GHCR |

Historical verification:

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

### 15. GitHub Actions Security

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

- PR #13 – Security: Scope package write permission to Docker job.

- Status: Merged.

- Commit: `9e8a362`.

### 16. Main Branch Protection

GitHub ruleset:

- Ruleset name: `main`

- Enforcement: Active

- Target: Default branch (`main`)

- Pull requests required before merging.

- Required status check: `Lint and test`.

- Branches must be up to date before merging.

- Force pushes blocked.

- Required approval count: 0.

### 17. Production Deployment

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

#### Latest Production Deployment

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

#### Production Health Verification

- `/health`: Previously verified as HTTP 200 with status `ok`.

- `/ready`: Previously verified as `ready`, with the database connected.

- Production deployment history confirms successful deployments of the latest commits.

### 18. Uptime Monitoring

Monitoring service: UptimeRobot

- Monitor endpoint: `/health`

- Monitoring status: UP

- Monitoring interval: 5 minutes

- Public status page:

https://stats.uptimerobot.com/0ObUsW7ASp

The health endpoint supports both GET and HEAD requests.

### 19. Production Rollback and Recovery Drill

Rollback platform: Render

#### Objective

Verify that the production service can be rolled back to a previous successful deployment and subsequently restored to a newer deployment.

#### Rollback and Recovery Execution – November 21, 2026

Two rollback operations were recorded in the Render deployment history.

| Time | Operation | Deployment / Commit | Result |

|---|---|---|---|

| 1:19 AM | Rollback initiated | Previous deployment `dep-dc04iirrjlhs7388uug0` | Initiated |

| 1:20 AM | Rollback deployment live | `9323df8` | Successful |

| 1:22 AM | Rollback initiated | Previous deployment `dep-dc08vimtlv9c739h201g` | Initiated |

| 1:22 AM | Recovery deployment live | `6cbf87c` | Successful |

#### Rollback Deployment

- Commit: `9323df8`

- Pull request: #14

- Description: `Docs: Add Day 5 deployment, CI/CD and rollback documentation`

- Rollback duration: 25.8 seconds

- Status: Deploy live

#### Recovery Deployment

- Commit: `6cbf87c`

- Pull request: #17

- Description: `feat: trigger Render deployment from GitHub CD`

- Recovery duration: 20.2 seconds

- Status: Deploy live

#### Verification

- Render deployment history recorded both rollback operations.

- Both rollback and recovery deployments were reported as successful and live.

- Production `/health` endpoint returned HTTP 200.

- The previous deployment was restored successfully.

- The newer deployment was subsequently restored successfully.

- Database readiness was checked as part of the production verification.

#### Rollback Outcome

The production rollback and recovery drill was successfully completed on November 21, 2026.

The drill demonstrated that a previous successful deployment could be restored through the Render dashboard and that a subsequent deployment could bring the application forward again.

#### Important Database Consideration

- Render rollback changes the deployed application version; it does not automatically reverse database migrations.

- Database schema compatibility must be checked before rolling back application code.

- Database migrations should remain backward-compatible with the previous application version wherever possible.

### 20. Deployment Lead Time Verification

Deployment platform: Render

Deployment trigger: GitHub Actions CD workflow using Render Deploy Hook.

#### Latest Recorded Deployment

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

#### Previous Deployment

| Metric | Value |

|---|---|

| Commit | `0f540b6` |

| Pull request | #19 |

| Deployment started | 10:13 AM |

| Deployment became live | 10:14 AM |

| Deployment lead time | Approximately 1 minute |

| Result | Successful |

#### CI Pipeline Duration

The latest recorded successful GitHub Actions CI workflow was:

- Workflow: LoanLens CI

- Run: #12

- Commit: `9e8a362`

- Branch: `main`

- Duration: 45 seconds

- Status: Success

#### Lead Time Observation

The recorded production deployments took approximately one minute from deployment initiation to becoming live.

The CI workflow completed in 45 seconds in the recorded run. CI execution time and production deployment lead time are separate measurements.

These results demonstrate that the automated CI/CD and production deployment pipeline can deliver application changes to production quickly.

**D05 Outcome:** CI/CD automation, production deployment, rollback and recovery verification were successfully completed.

### 21. Week 1 Git Milestone

Git tag:

`week-1`

Description:

`LoanLens Week 1: Backend, Docker, CI/CD and production deployment`

Tag was created, pushed and verified on GitHub.

Repository:

https://github.com/jeevanaay/prince28-fin05-loanlens

### 22. Day 5 Verification Summary

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

# D06 – Document Collection and Dataset Capacity

### 23. Document Collection Pipeline

Implemented document collection under `src/loanlens/ingest/fetch.py`.

Collection methods exposed through `scripts/fetch.py`:

| Method | Purpose |

|---|---|

| `urls` | Collect URLs from `data/sources.csv` |

| `sitemap` | Discover documents from sitemaps |

| `repo` | Collect documents from public Git repositories |

| `manual` | Register manually downloaded documents |

#### Collection Safeguards

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

#### Source Eligibility Enforcement

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

### 24. Source Register and Collection

Source register: `data/sources.csv`

The register contains 15 source entries covering government schemes and education-loan information from SBI, Bank of Baroda, Canara Bank and Indian Bank.

Current collection eligibility:

- Total entries: 15

- Pending: 9

- Blocked: 6

- Approved: 0

No sources are currently approved for automated collection.

PM-Vidyalaxmi documents requiring manual collection are registered through the manual collection command rather than automatically crawled.

### 25. Dataset Manifest and Storage

Manifest: `data/manifest.jsonl`

Raw documents: `data/raw/`

- Manifest records contain source metadata, retrieval status, file path and SHA-256 hash.

- Raw documents are excluded from Git.

- The manifest and source register are retained for reproducibility.

- Existing reference documents are stored separately in `data/source_docs/`.

### 26. Initial Dataset Measurement

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

### 27. Dataset Capacity Planning

Documentation: `docs/CAPACITY.md`

- Initial source register target: 10 URLs.

- Expanded corpus target: 1,500+ pages.

- Storage projections are estimates based on the measured initial collection.

- Additional bank circulars, FAQs and scheme documents remain to be collected.

### 28. Automated Tests

Test file: `tests/unit/test_fetch.py`

New downloader tests: 19

Verification:

```powershell

uv run pytest tests/unit/test_fetch.py -q

```

Historical result:

```text

19 passed

```

Full project test suite:

```powershell

uv run poe test

```

Historical D06 result:

```text

58 passed

```

### 29. Quality Gate Verification

Command:

```powershell

uv run pre-commit run --all-files

```

Historical results:

- Trailing whitespace: Passed

- End-of-file checks: Passed

- YAML validation: Passed

- TOML validation: Passed

- Large-file checks: Passed

- Private-key detection: Passed

- Ruff lint: Passed

- Ruff formatting: Passed

- Secret detection: Passed

### 30. D06 Verification Summary

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

### 31. Forced Interruption and Resume Verification

A controlled local HTTP-server test verified recovery after forcibly interrupting the document collection process with Ctrl+C.

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

**Result:** Forced interruption and restart/resume test passed using an isolated local test server and temporary test data.

---

# D07 – Document Parsing and PostgreSQL Page Storage

### 32. Objective

Built a document parsing pipeline to extract clean content from collected PDF and HTML files and store the results in PostgreSQL.

The pipeline captures:

- Page numbers

- Extracted text

- Heading paths

- Markdown tables

- Parsing failures and failure reasons

### 33. Dependencies and Database Migration

Installed:

- PyMuPDF

- Trafilatura

- pypdf

Used SQLAlchemy 2.x with async PostgreSQL integration.

Created and applied migration:

`3880cb25b992_add_page_headings_and_parse_failures.py`

Database changes:

- Added `headings` JSONB column to `pages`.

- Created `parse_failures` table.

- Added failure tracking fields: path, SHA-256, source URL, reason, detail, attempts and timestamps.

### 34. Parser Implementation

Created `src/loanlens/ingest/parse.py`.

Implemented:

- PDF parsing using PyMuPDF.

- Alternative PDF parsing using pypdf.

- HTML parsing using Trafilatura.

- Text parsing.

- JSON, YAML and CSV parsing.

- File-type detection.

- Heading extraction.

- Markdown table extraction.

- Parse error handling.

Created `src/loanlens/ingest/store.py` to store parsed documents and pages and track parsing failures.

### 35. Corpus Ingestion

Created `scripts/parse_corpus.py` to parse downloaded files from the manifest and store the extracted results in PostgreSQL.

#### Initial D07 Results

| Metric | Result |

|---|---:|

| Downloaded files processed | 8 |

| Documents stored | 8 |

| Pages stored | 33 |

| Parsing failures | 0 |

Three additional sources were blocked during collection and were not treated as parser failures.

### 36. Extraction Quality Improvement

Improved the Baroda Scholar HTML extraction.

The initial extraction included unrelated promotional content, including personal loan and home loan sections.

Refined the extraction to focus on the main article content.

Final result from the recorded extraction:

- Extracted characters: 11,919

- Headings: 8

- Personal loan promotional content: excluded

- Home loan promotional content: excluded

Re-ingested the corrected document into PostgreSQL.

### 37. Parser Comparison

Compared PyMuPDF and pypdf extraction for all 4 available PDF files. HTML extraction was reviewed separately using the current HTML parser.

#### PDF Comparison – Initial and Updated Results

| File | Initial similarity | Latest similarity | Latest verdict |

|---|---:|---:|---|

| PM-Vidyalaxmi Guidelines | 96.54% | 96.54% | Minor extraction differences |

| Global Ed-Vantage MITC November 2024 | 62.48% | 99.23% | Near-identical extraction after reading-order correction |

| PM-Vidyalaxmi Press Release | 97.57% | 97.57% | Minor extraction differences |

| PM-Vidyalaxmi Implementation Memorandum | 93.19% | 93.19% | Minor extraction differences; manual review recommended |

The percentages are script-reported text similarity measurements, not measures of extraction accuracy.

The initial Global Ed-Vantage MITC comparison recorded 62.48% similarity and required manual review. Following the two-column reading-order correction, a subsequent comparison achieved 99.23% similarity. The later result supersedes the initial measurement.

#### HTML Extraction Quality

| File | Characters | Headings | Pages | Extracted title | Verdict |

|---|---:|---:|---:|---|---|

| Global Ed-Vantage Scheme | 5,639 | 5 | 1 | SBI Global Ed-Vantage Scheme | Title and targeted cleanup verified |

| Masters Degree Education Loan India and Abroad | 5,378 | 9 | 1 | Education Loan for Masters Degree Abroad | Title and headings extracted |

| Baroda Scholar Education Loan | 11,920 | 8 | 1 | Baroda Scholar | Targeted extraction cleanup applied |

| Education Loan Interest Rates | 3,540 | 6 | 1 | Education Loan Scheme | Title and headings extracted |

| IB Education Loan IBA | 18,260 | 17 | 1 | Education Loan India - Study Without Limits | Title and headings extracted |

| PM-Vidyalaxmi Official Portal | 10,309 | 27 | 1 | Welcome to PM-Vidyalaxmi Portal for applying Education Loan | Heading extraction improved; manual review pending |

HTML character counts and heading counts describe extraction output; they are not similarity scores.

HTML results were not compared against an independent second parser.

#### HTML Heading Extraction Update

An earlier PM-Vidyalaxmi Official Portal extraction returned zero headings.

The latest Day 7 extraction detects 27 headings. This supersedes the earlier result. Manual content review is still pending.

#### Summary

- 4 PDF files compared using PyMuPDF and pypdf.

- 6 HTML files reviewed using the current HTML extraction pipeline.

- All 10 downloaded files were included.

- SBI Global Ed-Vantage Scheme title extraction and cleanup improved.

- SBI Global Ed-Vantage MITC PDF title extraction was verified against the actual PDF.

- Global Ed-Vantage MITC reading order was corrected and the latest similarity result reached 99.23%.

- PM-Vidyalaxmi Official Portal heading detection improved from zero to 27 detected headings.

- Baroda Scholar extraction cleanup was applied.

**Limitation:** HTML extraction quality was inspected, but no independent parser comparison or HTML similarity score was established.

### 38. PostgreSQL Verification

Re-ingested the complete 10-file corpus after the latest parser and storage changes.

| Database item | Verified result |

|---|---:|

| Total documents | 30 |

| Total pages | 40 |

| Parse failures | 0 |

The total document count includes metadata-only documents in addition to the 10 successfully parsed corpus documents.

Verified the parser-extracted titles in PostgreSQL:

- `SBI GLOBAL ED-VANTAGE SCHEME` — PDF, 2 pages.

- `SBI Global Ed-Vantage Scheme` — HTML, 1 page.

Verified page numbers and heading metadata using a real-document SQL query:

- PDF page 1: `Timeline for Disposal of Loan Application`

- PDF page 2: `Customer Service:`

- HTML page 1: 5 headings stored.

Page numbers and heading arrays are correctly persisted in PostgreSQL.

The documents inspected contain top-level headings; nested heading paths are covered by synthetic unit tests but still need verification against a real document containing nested sections.

The first re-ingestion completed successfully: 10 successful, 0 failed. A subsequent redundant run was interrupted during Neon connection establishment and did not complete.

### 39. D07 Summary

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

- Verified the PM-Vidyalaxmi Guidelines heading continuation and Annexure 1–5 detection.

**Remaining work:**

- Verify nested heading paths against a real document containing nested sections.

- Perform manual content review of the six HTML extraction results.

- Review the PM-Vidyalaxmi Official Portal's 27 extracted headings.

- Manually review the PM-Vidyalaxmi Implementation Memorandum extraction differences.

Global Ed-Vantage MITC two-column PDF reading order has been corrected and verified.

---

# Day 7 – Parser Comparison and Quality Review

### 40. Parser Comparison

| # | Document | Parser | Quality Result | Verdict |

|---|---|---|---|---|

| 1 | PM-Vidyalaxmi Guidelines | PyMuPDF vs pypdf | 96.54% similarity | Minor extraction differences |

| 2 | Global Ed-Vantage MITC November 2024 | PyMuPDF vs pypdf | 99.23% similarity | Near-identical extraction |

| 3 | PM-Vidyalaxmi Press Release | PyMuPDF vs pypdf | 97.57% similarity | Minor extraction differences |

| 4 | PM-Vidyalaxmi Implementation Memorandum | PyMuPDF vs pypdf | 93.19% similarity | Minor extraction differences; manual review recommended |

| 5 | Global Ed-Vantage Scheme | Trafilatura | 5,639 characters; 5 headings | Extraction completed; manual content review pending |

| 6 | Masters Degree Education Loan India and Abroad | Trafilatura | 5,378 characters; 9 headings | Extraction completed; manual content review pending |

| 7 | Baroda Scholar Education Loan | Trafilatura | 11,920 characters; 8 headings | Extraction completed; manual content review pending |

| 8 | Education Loan Interest Rates | Trafilatura | 3,540 characters; 6 headings | Extraction completed; manual content review pending |

| 9 | IB Education Loan IBA | Trafilatura | 18,260 characters; 17 headings | Extraction completed; manual content review pending |

| 10 | PM-Vidyalaxmi Official Portal | Trafilatura | 10,309 characters; 27 headings | Extraction completed; manual content review pending |

### 41. Quality Issues Identified

1. **PM-Vidyalaxmi Guidelines heading verification**

   Verified pages 14–15. `Contact us:` is the valid Section 26 heading, introduced by a standalone `26.` marker on page 14 and continued on page 15. No parser correction required.

2. **PDF title cleanup**

   Earlier PDF metadata and filename-derived titles were not descriptive.

   The title-cleanup logic was implemented and verified for:

   - `PM-Vidyalaxmi Guidelines (19 November 2024)`

   - `PM-Vidyalaxmi Implementation Memorandum`

3. **Global Ed-Vantage MITC extraction**

   The initial comparison showed 62.48% similarity. The two-column reading-order correction improved the later comparison to 99.23%.

4. **PM-Vidyalaxmi Official Portal heading extraction**

   The earlier extraction returned zero headings. The latest extraction detects 27 headings. Manual content review remains pending.

5. **HTML extraction review**

   The six HTML documents have been inspected for extraction output, but an independent parser comparison has not been performed.

6. **PM-Vidyalaxmi Implementation Memorandum**

   The latest similarity result is 93.19%. Manual review is recommended to assess the remaining extraction differences.

### 42. Ingestion Summary

- Downloaded files processed: 10

- Successfully parsed: 10

- Failed: 0

- Pages stored: 40

- Empty pages: 0

- Recorded parse failures: 0

### 43. Latest Unit Test Verification

Command:

```powershell

uv run poe test

```

Latest result:

```text

71 passed, 1 warning

```

The warning relates to the optional PySocks dependency used by urllib3. It did not cause test failures.

### 44. Heading Detection Verification

The numbered-heading hierarchy regression tests initially exposed missing numbered-heading detection. The detection logic was restored while retaining Annexure heading support.

Latest unit test result:

```text

71 passed

```

Real-document diagnostic:

- Page 14: `Contact us:`

- Page 15: `Contact us:`

- Page 16: `Annexure-1`

- Page 17: `Annexure-2`

- Page 18: `Annexure-3`

- Page 19: `Annexure-4: List of quality Higher Education Institutions (QHEIs) for the year 2024-25`

- Pages 20–21: `Annexure-5: State-wise distribution of 1,00,000 slots for 3% interest subvention under`

The `Contact us:` heading was checked against the PDF's original text and formatting:

- Page 14 contains a standalone `26.` marker.

- The next line, `Contact us:`, is bold.

- Page 14 then continues with subsection `26.1`.

- Page 15 continues with subsections `26.2` and `26.3`.

Therefore, `Contact us:` is a valid Section 26 heading and not an extraction error.

The Annexure headings are also detected correctly.

### 45. Day 7 Verification Summary

| Requirement | Latest result |

|---|---|

| PDF parser comparison | 4 PDFs compared |

| HTML extraction review | 6 HTML files reviewed |

| Corpus processed | 10 files |

| Successful parsing | 10 |

| Parsing failures | 0 |

| Pages stored | 40 |

| Empty pages | 0 |

| MITC reading-order correction | Verified |

| MITC latest similarity | 99.23% |

| PDF title cleanup | Verified |

| Numbered-heading regression tests | Passed |

| Annexure 1–5 detection | Verified |

| PM-Vidyalaxmi Guidelines Section 26 | Verified |

| Full unit test suite | 71 passed |

| PostgreSQL page storage | Verified |

**D07 / Day 7 Outcome:** The document parsing pipeline, PostgreSQL page storage, parser comparison, PDF title cleanup, numbered-heading detection and Annexure extraction have been implemented and verified against the recorded test results.

**Remaining work:** Real-document nested heading-path verification, manual HTML content review, and manual review of the remaining PDF extraction differences.

---

# Overall Project Progress – Week 1 and Day 7

LoanLens has completed the initial backend infrastructure, database integration, Docker configuration, CI/CD pipeline, production deployment, document collection pipeline and initial document parsing pipeline.

Major milestones:

- PostgreSQL integration using Neon.

- SQLAlchemy async database access.

- Alembic migration management.

- JSONB metadata and GIN index verification.

- Idempotent data loading.

- Docker multi-stage build and non-root runtime.

- Docker Compose health checks and service dependencies.

- FastAPI health and readiness endpoints.

- GitHub Actions CI/CD.

- GHCR Docker image publishing.

- GitHub branch protection and least-privilege permissions.

- Render production deployment.

- Production rollback and recovery drill.

- UptimeRobot monitoring.

- Document collection with robots.txt safeguards.

- Manifest tracking and SHA-256 verification.

- Forced interruption and resume testing.

- PDF, HTML, text, JSON, YAML and CSV parsing support.

- Page-level text and heading metadata.

- PostgreSQL page storage.

- Parsing failure tracking.

- PDF parser comparison and reading-order correction.

- HTML extraction cleanup.

- Unit test coverage expanded to 71 passing tests.

## Outstanding Technical Work

1. Verify nested heading paths against a real PDF or HTML document.

2. Manually review extracted content from all six HTML documents.

3. Review the PM-Vidyalaxmi Official Portal's 27 extracted headings.

4. Review the remaining extraction differences in the PM-Vidyalaxmi Implementation Memorandum.

5. Continue expanding the document corpus towards the 1,500+ page capacity target.

6. Approve additional collection sources only after independently verifying source-specific collection and reuse rights.

**Overall Status:** The initial LoanLens backend, deployment, document collection and parsing milestones have been implemented. The initial 10-document parsing run completed successfully with 40 pages stored and zero recorded parsing failures. Further extraction-quality review and corpus expansion remain ongoing.
D08 – LLM Gateway, Streaming and Usage Tracking
46. Objective
Implemented an LLM gateway for LoanLens with a primary Gemini provider, a Groq fallback provider, streaming and non-streaming chat responses, prompt management, call recording and daily usage reporting.
47. Gateway Configuration
Configuration is loaded through the application Settings.
Setting	Configured value
Primary provider	Gemini
Primary model	gemini-3.5-flash-lite
Fallback provider	Groq
Fallback model	openai/gpt-oss-20b
Primary API format	OpenAI-compatible Chat Completions
Fallback API format	OpenAI-compatible Chat Completions
Primary base URL	https://generativelanguage.googleapis.com/v1beta/openai
Fallback base URL	https://api.groq.com/openai/v1
Request timeout	30 seconds
Maximum attempts	2
Circuit-breaker threshold	3 failures
Circuit-breaker cooldown	30 seconds


API keys are stored in the local environment and are not committed to the repository. .env.example contains configuration placeholders only.

The existing Gemini Interactions API implementation in src/loanlens/llm/gemini.py was preserved. The new OpenAI-compatible gateway is implemented separately in src/loanlens/llm/gateway.py.
48. Gateway Features
Implemented in src/loanlens/llm/gateway.py:
- OpenAI-compatible provider abstraction for Gemini and Groq.
- Primary-provider and fallback-provider configuration.
- Streaming and non-streaming generation.
- Retry handling for retryable failures.
- Jittered exponential retry delay.
- Fallback to the secondary provider when the primary provider is unavailable.
- Circuit breaker with closed, open and half-open states.
- Per-attempt call recording.
- Token estimation and INR cost estimation.
- FakeLLM provider for deterministic tests.
- build_gateway(settings, recorder) factory.
Streaming fallback is attempted only before any response text has been yielded. This avoids silently switching providers after a partial answer has already reached the client.
49. System Prompt
Prompt file:

prompts/chat_system_v1.md

Prompt version:

chat_system_v1

The system prompt defines LoanLens as an assistant for explaining and comparing education loans, PM-Vidyalaxmi, interest subsidies, EMIs and total loan costs.

The prompt also instructs the model to:
- Answer from general knowledge in at most 120 words while documents are not connected.
- Use plain language.
- Say "I am not sure" instead of guessing.
- Never invent section numbers, page numbers, prices, doses or dates.
- Decline questions outside the product's subject in one sentence.
- Direct users to official sources or professionals for decisions.
The prompt is loaded by the API application and included as the system message for chat requests.
50. LLM Call Database Recording
Added the llm_calls table through Alembic migration:

33a6d0192c43_add_llm_calls.py

Revision:

33a6d0192c43

Parent revision:

3880cb25b992

The migration was applied successfully using:
uv run alembic upgrade head
The database model records call information including:
- Timestamp
- Request ID
- Provider and model
- Status and error details
- Input and output token counts
- Latency
- Estimated INR cost
- Whether fallback was used
Added src/loanlens/db/llm_calls.py with:
- DatabaseRecorder to persist gateway call records.
- UsageRepository to aggregate daily calls, errors, fallbacks, tokens and costs.
51. API Integration
Updated the FastAPI application factory in src/loanlens/api/main.py to initialize the database session factory, database recorder and LLM gateway during application lifespan.

Updated src/loanlens/api/deps.py with dependencies for the LLM gateway and usage repository.

Added chat and usage endpoints in src/loanlens/api/routes/chat.py.
Endpoint	Method	Purpose
/v1/chat	POST	Generate a chat response
/v1/usage	GET	Retrieve daily usage and estimated costs


The chat endpoint supports:
- Server-Sent Events (SSE) when stream: true.
- JSON responses when stream: false.
- Prompt version metadata.
- Provider, model, token, latency, cost and fallback metadata.
The usage endpoint accepts a days query parameter from 1 to 90, defaulting to 7.
52. Streaming Client
Created:

scripts/ask.py

The command-line client supports:
- Streaming chat requests.
- Non-streaming JSON requests using --json.
- First-word timing for streaming requests.
- Total response timing.
- Provider and model information.
- Token counts and estimated INR cost.
- Attempt count and fallback status.
Example commands:
uv run python scripts/ask.py "What is PM-Vidyalaxmi and who is eligible?"
uv run python scripts/ask.py "What is PM-Vidyalaxmi and who is eligible?" --json
Ruff validation for the script passed.

Timing note: In JSON mode, the script records the time after the complete response is received. This is total response time, not true first-token latency.
53. Prompt and Response Behaviour Tests
The live Gemini primary provider was tested using the local FastAPI server.

#### Education-loan question – streaming

Question:

"What is PM-Vidyalaxmi and who is eligible?"
Metric	Result
Provider	Gemini
Model	gemini-3.5-flash-lite
First words	3.65 seconds
Total response time	7.28 seconds
Input tokens	185
Output tokens	105
Estimated cost	Rs 0.030210
Attempts	1
Fallback used	No


The model returned an explanation of PM-Vidyalaxmi and its eligibility in India.

#### Same question – JSON response
Metric	Result
Provider	Gemini
Model	gemini-3.5-flash-lite
Total response time	4.76 seconds
Input tokens	185
Output tokens	168
Estimated cost	Rs 0.045173
Attempts	1
Fallback used	No


The JSON response completed successfully. The 4.76-second measurement is total response time and should not be compared directly with streaming first-word time.
54. English and Tamil Token Comparison
Tested three messages using the same system prompt.
Message	Total input tokens
"Hi" – baseline, mostly system prompt	172
English sentence	185
Same meaning in Tamil	190


The message token counts after subtracting the baseline were:
- English: 185 − 172 = 13 tokens.
- Tamil: 190 − 172 = 18 tokens.
- Tamil-to-English ratio: 18 ÷ 13 = approximately 1.38.
Tamil used approximately 1.38 times the input tokens of the English sentence in this test.

The first Tamil streaming attempt ended early with a provider stream error. The same request succeeded on retry.

Successful Tamil retry:
Metric	Result
First words	3.72 seconds
Total response time	4.80 seconds
Input tokens	190
Output tokens	151
Estimated cost	Rs 0.041278
Attempts	1
Fallback used	No


This is a single-message comparison and should not be treated as a universal English-versus-Tamil token ratio.
55. Model Reliability and Scope Tests
#### Loan approval uncertainty

Question:

"Will my education loan definitely be approved?"

Observed response began:

"I am not sure."

The model did not guarantee loan approval. It explained that lenders evaluate factors such as academic record, admission to a recognized institution, co-applicant income and collateral requirements. It recommended checking with the specific bank or official government portals.

Result: The model acknowledged uncertainty and did not claim to know the outcome of an individual loan application.

#### Off-topic question

Question:

"Who won the FIFA World Cup in 2022?"

Observed response:

"That question is outside LoanLens's subject."

Result: The model declined the unrelated question in one sentence, as instructed by the system prompt.
56. Unit Tests and Code Quality
Gateway and API tests were added.

Verification commands:
uv run pytest tests/unit/ -q
uv run poe test
uv run poe lint
Latest recorded results:
100 passed
Lint and formatting:
All checks passed!
67 files already formatted
The test run displayed one harmless warning related to the optional PySocks dependency used by urllib3.

The unit-test client was configured to use a fake gateway and fake usage repository so that automated tests do not make real provider API calls.
57. Docker Prompt Packaging
Updated the Dockerfile to include the prompt directory in the runtime image:
COPY --chown=app:app data ./data
COPY --chown=app:app prompts ./prompts
COPY --chown=app:app migrations ./migrations
Verified that the Dockerfile contains the prompt copy instruction.
58. Usage Tracking Verification
Opened:

http://localhost:8000/v1/usage

Observed daily usage:
Metric	Result
Date	November 25, 2026
Calls	8
Errors	1
Fallbacks	0
Input tokens	1,280
Output tokens	713
Estimated cost	Rs 0.205819
Rounded total cost	Rs 0.2058


The usage endpoint returned the daily aggregate and total cost successfully.

The one recorded error is consistent with the first Tamil streaming attempt that ended early. The subsequent Tamil retry succeeded.

Result: Database call recording and daily usage aggregation were verified against live local API requests.
59. D08 Verification Summary
Requirement	Latest result
Gemini primary provider	Live request successful
Groq fallback configuration	Configured; live fallback test pending
OpenAI-compatible provider abstraction	Implemented
Streaming chat	Verified
Non-streaming JSON chat	Verified
Versioned system prompt	Implemented and loaded
Retry handling	Implemented
Circuit breaker	Implemented; live behaviour test pending
Database call recorder	Verified
Daily usage endpoint	Verified
English and Tamil token comparison	Completed
Loan approval uncertainty test	Passed
Off-topic refusal test	Passed
Docker prompt packaging	Verified
Unit tests	100 passed
Ruff lint and formatting	Passed


D08 Status: The LLM gateway, Gemini live integration, streaming and JSON chat APIs, prompt loading, database call recording and usage reporting have been implemented and verified. Live Groq fallback and circuit-breaker behaviour remain to be tested.
60. Remaining D08 Work
1. Test Groq fallback by temporarily making the Gemini primary model unavailable.
2. Verify circuit-breaker behaviour after repeated primary-provider failures.
3. Verify half-open recovery after the configured cooldown.
4. Restore the valid Gemini primary model after testing.
5. Verify usage records for fallback calls and provider errors.
6. Test the deployed production endpoint after the local fallback behaviour is verified.
D08 Outcome: The primary Gemini integration and core gateway functionality are working locally. Fallback and circuit-breaker live verification are still pending.
### D08 – Live Fallback and Circuit-Breaker Verification Update
Date: November 25, 2026

Live provider-failure testing was completed using the local FastAPI server.

**Groq fallback verification**
- Temporarily configured an invalid Gemini primary model.
- Gemini returned HTTP 404.
- Groq successfully handled the requests using `openai/gpt-oss-20b`.
- Fallback responses were received successfully.

**Circuit-breaker verification**
- The configured failure threshold is 3.
- The first 3 rapid requests attempted Gemini and then used Groq.
- The 4th rapid request bypassed Gemini and used Groq directly.
- The 30-second cooldown was also observed during spaced requests, allowing Gemini to be attempted again.

**Primary-provider recovery**
- Restored `LLM_PRIMARY_MODEL=gemini-3.5-flash-lite`.
- Restarted the API server.
- Confirmed a successful Gemini primary response.

**Final local usage snapshot**
| Metric | Result |
|---|---:|
| Date | November 25, 2026 |
| Total calls | 32 |
| Errors | 12 |
| Fallback calls | 12 |
| Input tokens | 4,348 |
| Output tokens | 4,239 |
| Estimated cost | ₹0.359714 |

The errors and fallback calls include deliberate provider-failure tests. These are local development results, not production usage figures.

**Updated D08 status**
- Gemini primary integration: Verified
- Groq fallback: Verified
- Circuit-breaker threshold and bypass: Verified
- Cooldown behaviour: Observed
- Gemini primary restoration: Verified
- Usage persistence and aggregation: Verified
- Production deployment of the gateway: Pending
