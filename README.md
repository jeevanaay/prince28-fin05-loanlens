
# LoanLens

An education-loan information assistant that explains and compares education loans, central schemes and interest subsidies for students planning studies in India and abroad.

**Status:** Day 1 foundation (FastAPI skeleton, quality gates). Live URL planned from Day 5.

## Who it's for

A third-year CSE student at Prince college planning an MS in Germany who needs about Rs 20 lakh and does not understand collateral or moratorium rules.

## The problem

Education-loan information is scattered across different bank scheme documents and government websites. Each lender has different loan limits, collateral requirements, margin percentages, moratorium periods and interest rules. Central government schemes also provide interest subsidies with specific family-income limits. Comparing these options and calculating the actual repayment cost is confusing for students.

## Data sources

- PM-Vidyalaxmi scheme documents and FAQs
- IBA Model Education Loan Scheme
- Central Sector Interest Subsidy guidelines
- Education-loan scheme pages and PDFs from banks

Source websites:

- https://www.pmvidyalaxmi.co.in/
- https://www.education.gov.in/
- https://sbi.bank.in/

Terms: Public scheme documents. PM-Vidyalaxmi blocks bots: download documents manually and list each in DATASET.md.

## Hardest problem (my interview story)

Eligibility and money calculations: collateral thresholds, margin, moratorium and income-based interest subsidies must be applied as rules in code. EMI calculations must also include interest accumulated during the moratorium.

## Signature feature

Loan comparison table: enter course, country, loan amount and family income to compare each scheme's EMI, total interest and subsidy eligibility.

## Target metric

- EMI and total interest exact for 100% of 20 test cases.
- Eligibility correct for 90%+ of 40 questions.

## Run it locally

```bash
python -m uv sync
python -m uv run uvicorn loanlens.api.main:create_app --factory --reload
```

Then open http://localhost:8000/docs

## Checks

```bash
python -m uv run pytest
python -m uv run ruff check .
```
