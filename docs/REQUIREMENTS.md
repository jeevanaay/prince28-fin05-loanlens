
# Requirements: LoanLens

## Functional (what it does)

1. A user can ask a question in plain English and get an answer drawn from my education-loan and government-scheme sources.
2. Every answer cites the source document and the relevant page or section.
3. If the available documents do not contain the answer, the product says "I don't know" instead of guessing.
4. Signature feature: A loan comparison table where users enter their course, country, loan amount and family income to compare schemes by EMI, total interest, collateral requirements and subsidy eligibility.
5. A user can browse and search the underlying records through GET /v1/documents.

## Non-functional (how well, with numbers)

| # | Quality | Target | How I will measure it |
|---|---|---|---|
| 1 | Speed: record lookups | p95 under 500 ms for GET /v1/documents | Load test (Week 6) |
| 2 | Speed: answers | p95 under 6 seconds for a full answer; first token under 2 seconds | Traces (Week 5) |
| 3 | Accuracy | EMI and total interest exact for 100% of 20 test cases; eligibility correct for 90%+ of 40 questions | Golden question set (Weeks 4 and 5) |
| 4 | Cost | Under Rs 0.50 per answered question | LLM usage tracking (Week 2) |
| 5 | Availability | 99% monthly uptime of the live URL | Uptime monitor from Day 5 |
