# LoanLens

**An education-loan information assistant that helps students understand, explore and compare education loans, government schemes and interest subsidies.**

LoanLens aims to simplify education financing for students planning higher studies in India and abroad by bringing scattered loan information into one structured platform.

**Project Status:** Core API and database foundation completed. Eight backend enhancements implemented and merged into `main`. Docker deployment and documentation improvements are in progress.

---

## The Problem

Education-loan information is scattered across bank scheme documents, government websites and policy PDFs.

Every lender has different conditions, including:

- Maximum loan limits
- Collateral requirements
- Margin percentages
- Moratorium periods
- Interest rates and rules
- Family-income limits for interest subsidies

Government schemes also have specific eligibility conditions. Understanding these rules, comparing loan options and estimating repayment costs can be confusing for students.

LoanLens aims to make this information easier to understand and compare.

## Who It's For

Students planning higher education who need help understanding education-loan options, collateral requirements, repayment conditions and government interest subsidies.

**Example use case:** A student planning an MS in Germany with an estimated education-loan requirement of ₹20 lakh who needs to understand collateral, moratorium and repayment rules.

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
- Sort by lender, scheme, maximum loan amount, publication date or document ID.
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

### Monitoring and Health Checks
- `/health` — application liveness.
- `/ready` — database readiness.
- `/pool` — database connection-pool statistics.

### Statistics
- `/v1/documents/stats` provides document statistics.

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
| Testing | Pytest |
| Code Quality | Ruff |
| Server | Uvicorn |

---

## Project Structure

```text
prince28-fin05-loanlens/
│
├── data/
│   └── sample_records.json
│
├── docs/
│   ├── QUESTIONS.md
│   └── REQUIREMENTS.md
│
├── migrations/
│   └── versions/
│
├── scripts/
│   ├── db_check.py
│   ├── explain_gin.py
│   ├── load_db.py
│   └── verify_metadata.py
│
├── src/
│   └── loanlens/
│       ├── api/
│       │   ├── routes/
│       │   │   ├── documents.py
│       │   │   └── health.py
│       │   ├── deps.py
│       │   ├── errors.py
│       │   ├── main.py
│       │   ├── middleware.py
│       │   └── schemas.py
│       │
│       ├── db/
│       │   ├── models.py
│       │   ├── repository.py
│       │   ├── session.py
│       │   └── url.py
│       │
│       ├── config.py
│       ├── logging_setup.py
│       └── store.py
│
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_db_integration.py
│   └── test_loader.py
│
├── README.md
└── ...
```

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

### Indexing

- B-tree index on the typed lender column.
- GIN index on JSONB metadata.

These indexes support efficient lender filtering and metadata queries.

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

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Available Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Application health |
| GET | `/ready` | Database readiness |
| GET | `/pool` | Connection-pool statistics |
| GET | `/v1/documents` | List and search documents |
| GET | `/v1/documents/{doc_id}` | Retrieve a document |
| GET | `/v1/documents/stats` | Document statistics |

### Example API Requests

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

---

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL database
- Git

### 1. Clone the repository

```bash
git clone https://github.com/jeevanaay/prince28-fin05-loanlens.git
cd prince28-fin05-loanlens
```

### 2. Set up the virtual environment

Using Python:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the project dependencies using the project's configured dependency manager.

If using uv:

```bash
uv sync
```

### 3. Configure environment variables

Create a `.env` file in the project root.

Configure the database connection settings required by the application:

```env
DATABASE_URL=your_postgresql_connection_string
TEST_DATABASE_URL=your_test_database_connection_string
```

Never commit `.env` files or expose database credentials in source control.

### 4. Run database migrations

```bash
alembic upgrade head
```

**Important:** The default Alembic configuration targets `DATABASE_URL`. Use the explicit test-database override when applying migrations to the integration database.

Windows PowerShell:

```powershell
$env:LOANLENS_ALEMBIC_USE_TEST_DB = "1"
alembic upgrade head
Remove-Item Env:LOANLENS_ALEMBIC_USE_TEST_DB
```

### 5. Load sample data

For the configured default database:

```bash
python scripts/load_db.py
```

For the test database:

```bash
python scripts/load_db.py --test-db
```

### 6. Start the application

```bash
uvicorn loanlens.api.main:create_app --factory --reload
```

Open:

```text
http://localhost:8000/docs
```

---

## Testing and Code Quality

Run the complete test suite:

```bash
python -m pytest
```

Run linting:

```bash
ruff check .
```

Check formatting:

```bash
ruff format --check .
```

Compile the Python source files:

```bash
python -m compileall -q src scripts tests migrations
```

### Current Test Status

- 47 tests passing.
- API and filtering tests.
- Sorting and pagination tests.
- Database integration tests.
- Data-loader tests.

Integration tests use the dedicated test database configuration.

---

## Data Sources

LoanLens uses public education-loan scheme documents and government guidelines.

Primary sources:

- [PM-Vidyalaxmi](https://www.pmvidyalaxmi.co.in/)
- [Ministry of Education](https://www.education.gov.in/)
- [State Bank of India](https://sbi.bank.in/)

Additional reference material:

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

---

## Target Metrics

- 100% accuracy for EMI and total-interest calculations across 20 test cases.
- 90%+ eligibility accuracy across 40 test questions.

These are project targets, not yet claimed production results.

---

## Development Roadmap

- [x] Day 1–3: FastAPI foundation, database integration and core API.
- [x] Enhancement 1: Pydantic response schemas.
- [x] Enhancement 2: Field-based filtering.
- [x] Enhancement 3: Document statistics.
- [x] Enhancement 4: Database readiness checks.
- [x] Enhancement 5: JSON metadata pruning.
- [x] Enhancement 6: Typed lender column and B-tree index.
- [x] Enhancement 7: API sorting.
- [x] Enhancement 8: Connection-pool monitoring.
- [ ] Day 4: Docker, Docker Compose, coverage and one-command setup.
- [ ] Day 5: Deployment and live API.
- [ ] Future: Loan eligibility engine, EMI calculator and loan comparison interface.

---

## Project Status

LoanLens currently has a working FastAPI backend, PostgreSQL integration, database migrations, document search and filtering, sorting, statistics and monitoring endpoints.

The next development phase focuses on containerization, deployment readiness and expanding the loan eligibility and repayment calculation capabilities.

---

**Built as an education-loan information assistant project.**
