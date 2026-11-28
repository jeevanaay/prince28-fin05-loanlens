# LoanLens — Ingestion and Worker Verification Report

**Milestone:** D10 — Ingestion Worker Reliability and Production Verification
**Verification date:** 28 November 2026
**Project:** LoanLens

---

## 1. Overview

This report documents the D10 implementation and verification of the LoanLens asynchronous document ingestion pipeline.

The verification covered:

- Asynchronous ingestion job submission.
- Job status and progress tracking.
- Worker restart and recovery behaviour.
- Duplicate prevention and data integrity.
- Production ingestion of five OGD CSV datasets.
- Production API authentication.
- Dead-letter queue verification.
- CSV parser correction and deployment.

**Final result:** D10 verification completed. The local 20-item kill test passed its final integrity checks, and five CSV documents were successfully ingested into the production database.

## 2. Ingestion Architecture

The ingestion workflow uses an asynchronous worker architecture.

1. A client submits documents through `POST /v1/ingest`.
2. The API validates the request and authentication token.
3. An ingestion job is created and queued.
4. The worker processes the queued documents.
5. Job status and progress can be checked through `GET /v1/ingest/{job_id}`.
6. Failed items can be inspected through the dead-letter endpoint.

The worker is included in the Docker Compose configuration and uses the queue infrastructure for asynchronous processing.

## 3. Local Worker Kill Test

### 3.1 Objective

The purpose of the kill test was to verify that the ingestion worker could recover unfinished work after being stopped and restarted.

The test used 20 synthetic documents.

### 3.2 Final job status

| Status | Count |
|---|---:|
| Queued | 0 |
| Running | 0 |
| Done | 20 |
| Skipped | 0 |
| Failed | 0 |
| **Total** | **20** |

### 3.3 Data integrity verification

**Nothing lost**

No items remained queued or running after the test. All 20 items reached a terminal state.

`done + skipped + failed = 20`

**Nothing doubled**

- 20 distinct input hashes were recorded.
- 20 distinct document IDs were recorded.
- No duplicate documents were identified in the final test results.

### 3.4 Worker restart and recovery

The worker was stopped during processing and subsequently restarted.

Four unfinished items were automatically restored and processed after the restart.

Manual re-enqueue operations also occurred during debugging. Therefore, the final integrity result passed, but this test should not be described as a completely hands-off automatic recovery test.

### 3.5 Kill test conclusion

The final test results demonstrated:

- Zero lost items.
- Zero duplicated items.
- All 20 items accounted for.
- No remaining queued or running items.

**Result: PASSED**

The detailed test numbers and evidence are also recorded in `NOTES.md`.

## 4. Production OGD CSV Ingestion

### 4.1 Dataset ingestion

Five CSV datasets were placed in:

`data/ogd_sources/`

The datasets cover scholarship/funding information and loan account/disbursement information.

The ingestion manifest contains five entries with OGD source metadata and collection evidence.

### 4.2 Initial production ingestion

**Job ID:**

`f1bb3af0641f4cc9bd97a5649f33b09f`

Initial result:

| Metric | Count |
|---|---:|
| Requested | 5 |
| Done | 4 |
| Failed | 1 |
| Pages processed | 4 |

One CSV failed during parsing:

`RS_Session_260_AU_768_B.csv`

The recorded error was:

`parse: corrupt`

### 4.3 CSV parser correction

The issue was traced to CSV input handling in:

`src/loanlens/ingest/parse.py`

The parser was updated to use:

`csv.reader(io.StringIO(raw, newline=""))`

instead of:

`csv.reader(io.StringIO(raw))`

This corrected the newline handling issue affecting the CSV ingestion.

The fix was merged through PR #42.

**Commit:** `d48b738`

The updated deployment was confirmed on Render.

### 4.4 Retry result

The failed CSV was submitted again after the parser correction.

**Retry job ID:**

`9e831610a10f45dcaa32b9d0c9254990`

| Metric | Result |
|---|---:|
| Done | 1 |
| Skipped | 0 |
| Failed | 0 |
| Pages processed | 1 |
| Dead-letter items | 0 |

**Result: PASSED**

### 4.5 Production database verification

The production database was checked after ingestion.

Five unique documents were created with document IDs:

`31, 32, 33, 34, 35`

The records had distinct source URLs and were stored with:

`doc_type = data`

The initial ingestion and successful retry together resulted in five successfully ingested documents and five pages.

The earlier failed attempt remains in the historical ingestion job record; the retry succeeded.

## 5. Production API Verification

Production API:

`https://prince28-fin05-loanlens.onrender.com`

API documentation:

`https://prince28-fin05-loanlens.onrender.com/docs`

### 5.1 Ingestion submission endpoint

**Endpoint:**

`POST /v1/ingest`

Verification:

| Test | Expected response | Result |
|---|---|---|
| Request with valid authentication token | HTTP 202 Accepted | PASSED |
| Request without authentication token | HTTP 401 Unauthorized | PASSED |

The endpoint correctly enforces authentication and accepts authorized ingestion requests.

### 5.2 Job progress endpoint

**Endpoint:**

`GET /v1/ingest/{job_id}`

The endpoint was verified to return ingestion job progress and status.

**Result: PASSED**

### 5.3 Dead-letter endpoint

**Endpoint:**

`GET /v1/ingest/dead-letter`

Authenticated production verification returned:

- HTTP 200.
- Dead-letter count: 0.
- Empty dead-letter list.

**Result: PASSED**

### 5.4 Production verification summary

| Verification | Result |
|---|---|
| Authenticated ingestion submission | PASSED |
| Unauthenticated request rejection | PASSED |
| Job progress retrieval | PASSED |
| Dead-letter inspection | PASSED |
| Five CSV documents ingested | PASSED |

## 6. Corpus Snapshot

The following figures distinguish the local baseline from the production state.

| Environment / milestone | Documents | Pages | Notes |
|---|---:|---:|---|
| Initial corpus | 10 | 40 | Original document collection |
| Local database baseline — 27 Nov 2026 | 20 | — | Historical local baseline |
| Additional OGD CSV ingestion | 5 | 5 | Five production CSV documents |
| Production database — 28 Nov 2026 | 35 | — | Includes the five newly ingested documents |

The 1,500+ page corpus remains a longer-term collection target and is not claimed as completed by D10.

## 7. Evidence and Related Files

The following files and implementation components support the D10 work:

- `workers/` — ingestion worker implementation.
- `src/loanlens/ingest/parse.py` — CSV parser implementation and correction.
- `data/ogd_sources/` — OGD CSV source files.
- `data/manifest.jsonl` — source and collection metadata.
- `INGEST_REPORT.md` — this verification report.
- `NOTES.md` — detailed development notes and kill-test results.
- Docker Compose worker configuration — worker service definition.

Relevant identifiers:

| Item | Identifier |
|---|---|
| Synthetic kill-test job | `e4bab11f18744fef87c1ca6e46d8f910` |
| Initial production ingestion job | `f1bb3af0641f4cc9bd97a5649f33b09f` |
| Production retry job | `9e831610a10f45dcaa32b9d0c9254990` |
| CSV parser fix commit | `d48b738` |
| Pull request | #42 |
| Git tag | `week-2` |

## 8. Data Collection and Licensing Note

The five source files are recorded in the ingestion manifest with OGD source information and GODL-India collection evidence.

Dataset-specific licensing and usage conditions were not independently confirmed for every dataset. The presence of collection evidence in the manifest should not be interpreted as blanket legal approval for every future use or redistribution.

Additional datasets should be reviewed for their applicable source terms before ingestion or redistribution.

## 9. Final D10 Verification Checklist

| Task | Status |
|---|---|
| Asynchronous ingestion job submission | Complete |
| Job progress endpoint | Complete |
| Worker implementation and Compose integration | Complete |
| Worker restart and recovery test | Complete |
| 20-item kill test | Complete |
| Final queue accounting | Complete |
| Distinct input hash verification | Complete |
| Distinct document ID verification | Complete |
| No-loss and no-duplicate verification | Complete |
| Production ingestion of five CSV datasets | Complete |
| CSV parser correction | Complete |
| Successful retry of failed CSV | Complete |
| Production API authentication verification | Complete |
| Job progress endpoint verification | Complete |
| Production dead-letter queue verification | Complete |
| Documentation of results | Complete |

## 10. Conclusion

The D10 ingestion and worker reliability verification for LoanLens is complete.

The local 20-item worker kill test finished with all items accounted for, zero lost items, and zero duplicated documents. Four unfinished items were automatically restored after the worker restart, with manual re-enqueue operations also used during debugging.

Production ingestion successfully processed five unique CSV documents. The CSV parser issue was corrected, merged through PR #42, and deployed. The failed document was successfully retried.

Production API authentication, job progress retrieval, and dead-letter queue status were also verified.

**Final milestone status: D10 — COMPLETE**

Future work includes continued production monitoring, expansion of the document corpus toward the 1,500+ page target, and further dataset-specific collection and licensing reviews.
