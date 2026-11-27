# Ingestion report

<!-- generated:start -->
_Generated 27 Nov 2026 11:13 from the database._

| What | Count |
|---|---|
| Documents in the database | 10 |
| Pages | 40 |
| Tokens of text (characters Ã· 4) | 39,024 |
| Files the parser gave up on | 0 |
| Documents with an extracted record | 10 |
| Documents whose extraction failed | 0 |

| Queue | Count |
|---|---|
| Ingest jobs started | 0 |
| Items finished (done or skipped) | 0 |
| Items that needed more than one try | 0 |
| Items in the dead-letter list | 0 |

Model calls for extraction: 33 Â· tokens in 119,374 Â· tokens out 6,539 Â· cost at list price Rs 4.96
<!-- generated:end -->

## What I learnt

1. The corpus increased from 28 pages on Monday to 40 pages today, a growth of 42.9%.
2. All 10 documents were successfully extracted, with zero parser failures and zero extraction failures.
3. The report estimates 39,024 text tokens across 40 pages, giving us a measured baseline for future capacity planning.

## Worker restart recovery test – 27 November 2026

1. Created a synthetic ingestion item in PostgreSQL with status `running` and attempt count `1`.
2. Restarted the local Docker worker without restarting PostgreSQL or Redis.
3. Confirmed that the worker detected and re-enqueued the unfinished item: `1 unfinished item(s) put back in the queue`.
4. Verified that the recovered job executed and its attempt count increased to `2`.
5. The synthetic item was correctly marked `failed` because collection approval evidence was intentionally absent.
6. Deleted the synthetic test job and verified that no test records remained.

**Result:** Local worker restart recovery successfully verified. PostgreSQL retained the unfinished job and the worker restored it to Redis.

## Redis queue reconstruction test - 27 November 2026

### Objective
Verify that the worker can reconstruct missing Redis queue entries using unfinished ingestion records stored in PostgreSQL.

### Test procedure
1. Checked the local Redis database and confirmed there were no existing ingestion jobs.
2. Created a synthetic ingestion job in PostgreSQL with its item status set to `running` and attempts set to 1.
3. Restarted the worker while the Redis queue had no corresponding ingestion job.
4. Observed the worker startup recovery process.
5. Verified that the worker detected one unfinished item and re-enqueued it.
6. Confirmed that the worker executed the reconstructed job and incremented its attempt count to 2.
7. The synthetic item failed as expected because collection approval evidence was intentionally omitted.
8. Deleted the synthetic job and verified that no test job remained.

### Result
Successful. The worker reconstructed a missing Redis queue entry from PostgreSQL and executed the corresponding ingestion item.

### Scope and limitation
This test verifies missing queue-entry reconstruction from PostgreSQL. It does not verify an actual Redis server crash, RDB/AOF restoration, or concurrent duplicate-execution prevention.
