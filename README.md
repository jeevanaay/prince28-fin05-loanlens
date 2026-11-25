# LoanLens

An education-loan information assistant that helps students understand, explore, and compare education loans, government schemes, and interest subsidies.

LoanLens aims to simplify education financing for students planning higher studies in India and abroad by bringing scattered loan information into one structured platform.

- **System status:** LoanLens Status
- **Live API:** https://prince28-fin05-loanlens.onrender.com
- **API documentation:** https://prince28-fin05-loanlens.onrender.com/docs
- **Production health:** Health check · Database readiness

> **Deployment note:** The existing backend deployment and monitoring links are retained here. The Day 8 LLM gateway work described below has been implemented and verified locally. Deploy the updated revision and configure its production secrets before treating the new chat and usage endpoints as available on the live service.

---

## The Problem

Education-loan information is scattered across bank scheme documents, government websites, and policy PDFs.

Every lender has different conditions, including:

- Maximum loan limits
- Collateral requirements
- Margin percentages
- Moratorium periods
- Interest rates and rules
- Family-income limits for interest subsidies

Government schemes also have specific eligibility conditions. Understanding these rules, comparing loan options, and estimating repayment costs can be confusing for students.

LoanLens aims to make this information easier to understand and compare.

## Who It's For

Students planning higher education who need help understanding education-loan options, collateral requirements, repayment conditions, and government interest subsidies.

**Example use case:** A student planning an MS in Germany with an estimated education-loan requirement of ₹20 lakh who needs to understand collateral, moratorium, and repayment rules.

---

## Key Features

### Document Management and Search

- Store education-loan scheme information in PostgreSQL.
- Search documents using text queries.
- Filter records by lender and scheme.
- Retrieve individual documents by ID.

### API Filtering and Sorting

- Filter by lender and scheme.
- Search across document information.
- Sort by lender, scheme, maximum loan amount, publication date, or document ID.
- Support ascending and descending sorting.
- Paginate API responses.

### Database and Data Management

- PostgreSQL database integration.
- SQLAlchemy asynchronous database operations.
- Alembic database migrations.
- JSONB storage for flexible scheme metadata.
- Typed lender column with a B-tree index.
- GIN index for JSONB metadata queries.
- Idempotent data loading with versioned fingerprints.
- JSON metadata pruning to remove unnecessary null values.

### LLM Gateway and Chat

- OpenAI-compatible Chat Completions integration for the configured Gemini primary provider and Groq fallback provider.
- Configurable primary and fallback models and base URLs.
- Streaming and non-streaming chat responses.
- Retry handling for retryable provider failures.
- Circuit-breaker support for provider availability.
- Fallback to the secondary provider when the primary provider is unavailable.
- Per-attempt usage and error recording in PostgreSQL.
- Input/output token estimates and INR cost estimates.
- Versioned LoanLens system prompt loaded from `prompts/chat_system_v1.md`.
- Local command-line client at `scripts/ask.py` for testing chat responses.

> **Important:** The current system prompt provides general LoanLens guidance. Scheme documents are not connected to the assistant yet. Responses should not be treated as verified scheme-specific advice. Users should confirm eligibility, rates, and policy conditions with official sources.

### Monitoring and Health Checks

- `/health` — Application liveness.
- `/ready` — Database readiness.
- `/pool` — Database connection-pool statistics.

### Statistics and Usage

- `/v1/documents/stats` provides document statistics.
- `/v1/usage` provides daily LLM call counts, errors, fallback counts, token totals, and estimated INR cost.

---

## Tech Stack

| Category | Technologies |
|---|---|
| Language | Python 3.12 |
| API Framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Database Migrations | Alembic |
| Data Validation | Pydantic |
| Database Querying | SQL / JSONB |
| LLM Integration | Gemini, Groq, HTTPX |
| Testing | Pytest |
| Code Quality | Ruff |
| Server | Uvicorn |
| Dependency / Task Management | uv, Poe the Poet |
| Containerization | Docker, Docker Compose |
| Deployment / Monitoring | Render, Neon, UptimeRobot |

---

## Project Structure

```text
prince28-fin05-loanlens/
├── data/
│   └── sample_records.json
├── docs/
│   ├── QUESTIONS.md
│   └── REQUIREMENTS.md
├── migrations/
│   └── versions/
├── prompts/
│   └── chat_system_v1.md
├── scripts/
│   ├── ask.py
│   ├── dataset_report.py
│   ├── db_check.py
│   ├── explain_gin.py
│   ├── fetch.py
│   ├── load_db.py
│   ├── parse_corpus.py
│   └── verify_metadata.py
├── src/
│   └── loanlens/
│       ├── api/
│       │   ├── routes/
│       │   │   ├── chat.py
│       │   │   ├── documents.py
│       │   │   └── health.py
│       │   ├── deps.py
│       │   ├── errors.py
│       │   ├── main.py
│       │   ├── middleware.py
│       │   └── schemas.py
│       ├── db/
│       │   ├── llm_calls.py
│       │   ├── models.py
│       │   ├── repository.py
│       │   ├── session.py
│       │   └── url.py
│       ├── ingest/
│       │   ├── fetch.py
│       │   ├── parse.py
│       │   └── store.py
│       ├── llm/
│       │   ├── gateway.py
│       │   └── gemini.py
│       ├── config.py
│       ├── logging_setup.py
│       └── store.py
├── tests/
│   ├── conftest.py
│   └── unit/
│       ├── conftest.py
│       ├── test_chat_api.py
│       └── test_gateway.py
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── README.md
└── pyproject.toml
```

The tree highlights the main application files and may omit additional tests, migrations, configuration files, or supporting modules.

---

## Database Design

LoanLens uses PostgreSQL to store structured document records and flexible scheme-specific metadata.

### Documents

The document model includes:

- Document ID
- Title
- Lender
- Source URL
- Licence
- Document type
- Publication date
- JSONB metadata

### LLM Call Records

The `llm_calls` table records provider-call information for usage monitoring, including:

- Provider and model
- Request status and error information
- Input and output token counts
- Estimated cost
- Request timing and fallback/attempt details

### Indexing

- B-tree index on the typed lender column.
- GIN index on JSONB metadata.
- Indexes supporting LLM usage aggregation and lookup.

### Data Loading

The data loader supports:

- Initial insertion of records.
- Updating changed records.
- Skipping unchanged records.
- Versioned content fingerprints.
- Removing unnecessary null-valued metadata.

The loader is designed to be idempotent, so repeated runs do not unnecessarily duplicate records.

---

## API Documentation

Once the application is running, interactive API documentation is available at:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Available Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Application health |
| GET | `/ready` | Database readiness |
| GET | `/pool` | Connection-pool statistics |
| GET | `/v1/documents` | List and search documents |
| GET | `/v1/documents/{doc_id}` | Retrieve a document |
| GET | `/v1/documents/stats` | Document statistics |
| POST | `/v1/chat` | Chat with the LoanLens LLM gateway |
| GET | `/v1/usage` | Daily LLM usage and estimated costs |

### Example Document API Requests

**List documents**

```http
GET /v1/documents
```

**Search documents**

```http
GET /v1/documents?q=education
```

**Filter by lender**

```http
GET /v1/documents?lender=SBI
```

**Filter by scheme**

```http
GET /v1/documents?scheme=PM-Vidyalaxmi
```

**Sort by maximum loan amount**

```http
GET /v1/documents?sort_by=max_amount&sort_order=desc
```

**Retrieve a specific document**

```http
GET /v1/documents/001
```

### Chat API

The chat endpoint supports both streaming and non-streaming responses. The request body contains a user message and a streaming preference.

**Example request:**

```http
POST /v1/chat
Content-Type: application/json
```

```json
{
  "message": "What is PM-Vidyalaxmi?",
  "stream": false
}
```

For streaming, set `"stream": true`. The API returns the response as server-sent events (SSE).

### Usage API

Retrieve usage totals for a selected number of days:

```http
GET /v1/usage?days=7
```

The response includes daily calls, errors, fallbacks, input/output token totals, and estimated INR cost.

---

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL database
- Git

For the Docker Compose setup:

- Docker Desktop
- Docker Compose

### 1. Clone the Repository

```bash
git clone https://github.com/jeevanaay/prince28-fin05-loanlens.git
cd prince28-fin05-loanlens
```

### 2. Set Up the Environment

Using Python:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies using uv:

```bash
uv sync
```

### 3. Configure Environment Variables

Create a `.env` file in the project root. Start from `.env.example` and configure the values required for your environment.

At minimum, configure the database connection:

```env
DATABASE_URL=your_postgresql_connection_string
TEST_DATABASE_URL=your_test_database_connection_string
```

For LLM chat functionality, configure provider credentials and model settings in `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key

GEMINI_MODEL=gemini-3.5-flash-lite
LLM_PRIMARY_MODEL=gemini-3.5-flash-lite
LLM_FALLBACK_MODEL=openai/gpt-oss-20b

LLM_PRIMARY_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_FALLBACK_BASE_URL=https://api.groq.com/openai/v1
LLM_TIMEOUT_SECONDS=30
```

Use the exact variable names and defaults in the current `.env.example` and application settings.

> **Security:** Provider keys are secrets. Never commit `.env`, paste API keys into issues, or expose them in logs or screenshots. If a provider key is empty, that provider is not configured.

### 4. Run Database Migrations

```bash
uv run alembic upgrade head
```

**Important:** The default Alembic configuration targets `DATABASE_URL`. Use the explicit test-database override when applying migrations to the integration database.

Windows PowerShell:

```powershell
$env:LOANLENS_ALEMBIC_USE_TEST_DB = "1"
uv run alembic upgrade head
Remove-Item Env:LOANLENS_ALEMBIC_USE_TEST_DB
```

### 5. Load Sample Data

For the configured default database:

```bash
uv run python scripts/load_db.py
```

For the test database:

```bash
uv run python scripts/load_db.py --test-db
```

### 6. Start the Application

```bash
uv run poe dev
```

Open:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health
- Readiness check: http://localhost:8000/ready

### 7. Try the LLM Command-Line Client

With the API credentials configured, run:

```bash
uv run python scripts/ask.py "What is PM-Vidyalaxmi and who is eligible?"
```

To request a non-streaming JSON response:

```bash
uv run python scripts/ask.py "What is PM-Vidyalaxmi and who is eligible?" --json
```

The script displays the response and available request metrics, including provider/model, elapsed time, token counts, estimated INR cost, attempts, and whether fallback was used.

---

## Docker Compose Setup

From the project root, build and start the services:

```bash
docker compose up --build -d
```

This starts the services defined in the Compose configuration, including the database, migrations, and API.

**Verify running services:**

```bash
docker compose ps
```

**View API logs:**

```bash
docker compose logs -f api
```

**View migration logs:**

```bash
docker compose logs migrate
```

**Stop the application:**

```bash
docker compose down
```

This stops and removes containers while preserving named database volumes.

To reset the database completely:

```bash
docker compose down -v
```

> **Warning:** This removes Compose-managed named volumes and permanently deletes the database data stored in them.

---

## Additional Week 1 Development Work

The following milestones record the work completed across Days 3–8. Day 6 covers document collection and resumability; Day 7 covers parsing and page storage; Day 8 adds the LLM gateway.

### Day 3 — Database and Data-Loading Validation

- Applied and tracked the database migration workflow; the Week 1 validation snapshot contained 3 migrations.
- Loaded and checked 20 sample records in the development database.
- Reviewed query plans with PostgreSQL EXPLAIN as part of the indexing and database-query work.
- Confirmed the Week 1 project checker recognized the D03 documentation section.

### Day 5 — CI/CD, Deployment and Recovery

- Added the GitHub Actions workflow at `.github/workflows/ci.yml`.
- Recorded a successful CI run (#12) for commit `9e8a362`; the documented pipeline included 35 unit tests.
- Set up the deployment workflow using Render and GitHub Container Registry (GHCR), alongside the existing Neon PostgreSQL database and UptimeRobot monitoring.
- Practised rollback and recovery: rollback commit `9323df8` and recovery commit `6cbf87c`.
- Recorded an approximately one-minute deployment lead time.
- Verified the live `/health` endpoint returned HTTP 200 during the Week 1 check. The checked deployment was not confirmed to match the then-current main commit `33218a7`, so this check should not be read as proof that every later revision was deployed.

### Day 6 — Document Collection and Resumable Fetching

- Implemented the document fetcher in `src/loanlens/ingest/fetch.py`, with collection commands exposed through `scripts/fetch.py`.
- Added collection methods for registered URLs, sitemaps, public repositories, and manually registered documents.
- Added collection safeguards, including robots.txt checks, retry handling, per-host request delays, bounded concurrency, and safe handling of partial downloads.
- Added source eligibility checks using `data/sources.csv`, plus a manifest at `data/manifest.jsonl` with retrieval details and SHA-256 hashes.
- Added dataset reporting and capacity documentation through `scripts/dataset_report.py`, `DATASET.md`, and `CAPACITY.md`.
- The recorded collection snapshot contained 8 downloaded documents from 6 organisations. The broader corpus target of 1,500+ pages remained future work.

**D06 star — Forced-interruption resume test:** A controlled test forcibly stopped the fetcher with Ctrl+C and restarted it. The completed file was skipped on restart, while the two remaining files were downloaded successfully. The test confirmed that the finished file was not downloaded again and its SHA-256 hash remained unchanged. The test details were recorded in `NOTES.md`.

### Day 7 — Document Parsing and Page Storage

- Implemented document parsing and structured page storage.
- Added the ingestion components, including `src/loanlens/ingest/parse.py`, `src/loanlens/ingest/store.py`, and `scripts/parse_corpus.py`.
- Added database model and migration support for storing parsed document/page data.
- Committed the initial parsing and page-storage implementation as `89bf38d` (feat: add document parsing and page storage).
- Added parser-comparison documentation in `NOTES.md`; the documentation change was merged to main as `bddb806`.
- Ran the parser-related validation suite; the recorded parser milestone reached 68 passing tests, and all 9 pre-commit hooks passed. The broader Day 7 technical verification later recorded 71 passing tests.

**Parser comparison limitation:** The comparison exercise had 8 source files available against a planned set of 10, leaving a shortfall of 2 files. This limitation was documented rather than presenting the comparison as complete.

### Dataset Collection Snapshot

At the recorded Week 1 baseline:

- 11 manifest entries were recorded.
- 8 documents had been downloaded.
- The downloaded corpus occupied approximately 3.35 MB and contained 28 PDF pages.
- The records covered 6 organisations.
- The longer-term target of 1,500+ pages had not yet been reached.

These figures describe that development snapshot and should be refreshed before being presented as current dataset totals.

---

## Testing and Code Quality

Run the complete test suite:

```bash
uv run poe test
```

Run linting:

```bash
uv run poe lint
```

Run formatting checks:

```bash
uv run ruff format --check .
```

Compile the Python source files:

```bash
uv run python -m compileall -q src scripts tests migrations
```

---

## Current Verification Status

The Day 8 LLM gateway implementation has been tested locally.

| Check | Result |
|---|---|
| Unit and API tests | 100 passed |
| Ruff lint | Passed |
| Ruff formatting | Passed |
| Gemini primary provider | Verified |
| Groq fallback provider | Verified |
| Streaming chat | Verified |
| Non-streaming JSON chat | Verified |
| Prompt scope and uncertainty checks | Passed |
| Circuit-breaker threshold and bypass | Verified |
| Cooldown behaviour | Observed |
| Database call recording | Verified |
| Daily usage endpoint | Verified |

### Live Usage Test — November 25, 2026

| Metric | Result |
|---|---:|
| Calls | 32 |
| Errors | 12 |
| Fallback calls | 12 |
| Input tokens | 4,348 |
| Output tokens | 4,239 |
| Estimated cost | ₹0.359714 |

The usage snapshot includes deliberate provider-failure and fallback tests. These figures represent local development testing, not production usage.

### Provider Failover Verification

- Gemini was temporarily configured with an invalid model to simulate primary-provider failure.
- Gemini returned HTTP 404.
- Groq successfully handled fallback requests using `openai/gpt-oss-20b`.
- After three rapid primary-provider failures, the circuit breaker bypassed Gemini on the fourth request.
- The configured cooldown was observed during spaced requests.
- The original Gemini model was restored and successfully tested again.

> **Deployment note:** The gateway has been verified locally. Production deployment and production endpoint verification remain pending.

---

## Data Sources

LoanLens uses public education-loan scheme documents and government guidelines.

### Primary Sources

- PM-Vidyalaxmi
- Ministry of Education
- State Bank of India

### Additional Reference Material

- IBA Model Education Loan Scheme.
- Central Sector Interest Subsidy guidelines.
- Education-loan scheme documents and PDFs published by banks.

**Data collection note:** Some source websites restrict automated access. Relevant documents may need to be downloaded manually and documented in the dataset reference records.

---

## Signature Feature — Loan Comparison

The long-term goal of LoanLens is to provide a loan comparison experience.

Students will be able to enter:

- Course and destination country.
- Required loan amount.
- Family income.

LoanLens will compare eligible schemes based on:

- Maximum loan amount.
- Collateral requirements.
- Margin percentage.
- Moratorium period.
- Interest rules.
- Subsidy eligibility.
- Estimated EMI.
- Total interest payable.

The calculation engine must account for interest accumulated during the moratorium period when estimating repayment costs.

### Target Metrics

- 100% accuracy for EMI and total-interest calculations across 20 test cases.
- 90%+ eligibility accuracy across 40 test questions.

These are project targets, not yet claimed production results.

---

## Development Roadmap

- [x] Days 1–3: FastAPI foundation, database integration, and core API.
- [x] Enhancement 1: Pydantic response schemas.
- [x] Enhancement 2: Field-based filtering.
- [x] Enhancement 3: Document statistics.
- [x] Enhancement 4: Database readiness checks.
- [x] Enhancement 5: JSON metadata pruning.
- [x] Enhancement 6: Typed lender column and B-tree index.
- [x] Enhancement 7: API sorting.
- [x] Enhancement 8: Connection-pool monitoring.
- [x] Day 4: Docker, Docker Compose, automated migrations, unit and integration testing, coverage, and one-command setup.
- [x] Day 5: GitHub Actions CI workflow, container-based deployment workflow, deployment monitoring, and rollback/recovery exercise.
- [x] Deployment foundation: Render API deployment, Neon PostgreSQL connection, CI pipeline, and uptime monitoring.
- [x] Day 6: Document collection pipeline, source register, manifest and SHA-256 tracking, dataset/capacity reporting, and forced-interruption resume verification.
- [x] Day 7: Document parsing, structured page storage, ingestion script, parse-failure tracking, parser comparison, and extraction-quality improvements.
- [x] Day 8: LLM gateway with Gemini primary and Groq fallback configuration.
- [x] Day 8: Streaming and JSON chat API.
- [x] Day 8: Retry handling, circuit-breaker implementation, and provider fallback logic.
- [x] Day 8: PostgreSQL LLM call recording and daily usage endpoint.
- [x] Day 8: Versioned system prompt and CLI testing client.
- [x] Day 8: Live Groq fallback and circuit-breaker verification using a controlled primary-provider failure.
- [ ] Next: Deploy the updated LLM gateway and configure production secrets.
- [ ] Future: Connect verified scheme documents to retrieval.
- [ ] Future: Loan eligibility engine, EMI calculator, and loan comparison interface.

---

## Project Status

LoanLens has a FastAPI backend with PostgreSQL integration, database migrations, document search and filtering, sorting, statistics, and monitoring endpoints. The project also includes a document collection and resumable-fetch pipeline, document parsing with PostgreSQL page storage, and a configurable LLM gateway with chat API, usage recording, and a local CLI client.

The Day 8 gateway implementation has passed the local test suite (100 tests) and lint/format checks. Gemini primary chat, Groq fallback, and circuit-breaker behavior were verified locally using controlled provider-failure tests. The original Gemini primary model was restored and tested successfully.

The new chat and usage functionality still needs to be deployed and configured in the production environment before being advertised as live.

The next development phase focuses on deploying the updated gateway, configuring production secrets, connecting authoritative scheme documents, and expanding the loan eligibility and repayment calculation capabilities.

---

Built as an education-loan information assistant project.
