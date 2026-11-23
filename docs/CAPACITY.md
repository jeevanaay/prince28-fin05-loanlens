
# LoanLens — Dataset Capacity Plan

## 1. Current Collection Snapshot

As of 23 November 2026:

| Metric | Current value |
|---|---:|
| Manifest entries | 11 |
| Successfully downloaded documents | 8 |
| Total storage | 3.35 MB |
| PDF pages detected | 28 |
| Source organisations | 6 |

These figures are measured using `scripts/dataset_report.py`.

## 2. Initial Corpus Target

The initial collection target is 10 official source URLs covering:

- Central government education-loan schemes.
- SBI Global Ed-Vantage.
- Bank of Baroda Baroda Scholar.
- Canara Bank education loans.
- Indian Bank education loans.

The expanded collection target is 1,500+ pages, including:

- Official scheme guidelines.
- Bank-specific loan documents.
- FAQs and circulars.
- Interest-rate and policy documents.

## 3. Storage Estimate

The current average document size is approximately 0.42 MB per downloaded document.

At the current average size:

| Collection size | Estimated storage |
|---|---:|
| 10 documents | 4.2 MB |
| 25 documents | 10.5 MB |
| 50 documents | 21 MB |
| 100 documents | 42 MB |

These are rough estimates. Actual document sizes may vary considerably.

## 4. Collection and Processing Limits

- Maximum concurrent downloads: 4.
- Default per-host delay: 0.5 seconds.
- Maximum retry attempts: 3.
- Individual request timeout: 45 seconds.
- Respect each website's `robots.txt` rules.
- Fail closed when robots policy cannot be retrieved reliably.
- Skip completed downloads when the manifest confirms the file exists.
- Use temporary `.part` files and atomic replacement for downloads.

## 5. Storage Architecture

| Location | Purpose | Git tracking |
|---|---|---|
| `data/sources.csv` | Source URL register | Tracked |
| `data/manifest.jsonl` | Collection metadata and hashes | Tracked |
| `data/raw/` | Downloaded source documents | Ignored |
| `data/source_docs/` | Existing reference documents | Check before committing |
| `scripts/dataset_report.py` | Dataset statistics | Tracked |

Raw source documents remain outside Git to avoid repository bloat and unnecessary redistribution.

## 6. Scaling Considerations

1. Keep source collection separate from document parsing.
2. Preserve SHA-256 hashes for document integrity checks.
3. Avoid downloading duplicate documents.
4. Respect host-specific crawl delays and access restrictions.
5. Record source, title, retrieval time and reuse terms.
6. Recalculate corpus statistics after each collection batch.
7. Inspect document quality before including it in the searchable corpus.
8. Verify reuse permissions before redistributing or publishing source documents.

## 7. Current Limitations

- The current collection has only 28 detected PDF pages.
- The 1,500+ page target has not yet been achieved.
- Some sources require manual document collection.
- Reuse terms remain unverified for several sources.
- Storage projections are estimates, not measured future requirements.
## 8. Capacity Assessment — Four Key Answers

### 1. How much data can the current pipeline handle?

The current measured baseline is 8 successfully downloaded documents, occupying 3.35 MB and containing 28 detected PDF pages. The pipeline supports up to 4 concurrent downloads. The 1,500+ page target remains outstanding, so larger-scale capacity still needs validation.

### 2. How much storage is required for the expanded corpus?

The current average document size is approximately 0.42 MB. Based on this average, 100 documents would require approximately 42 MB. This is a rough projection; the actual storage requirement for 1,500+ pages must be measured after collecting a representative corpus.

### 3. What limits collection throughput?

Collection throughput is controlled by a maximum concurrency of 4, a default per-host delay of 0.5 seconds, a 45-second request timeout and up to 3 retry attempts. Robots.txt restrictions and manual-only sources can further limit collection speed.

### 4. How can the corpus scale while preserving reliability and compliance?

Scale collection in batches, retain SHA-256 hashes and manifest records, skip completed downloads, and use temporary files with atomic replacement. Respect robots.txt and access restrictions, verify reuse permissions, and keep raw documents outside Git unless redistribution is permitted.

---
## 9. Capacity Reporting

Generate the latest collection report with:

```powershell
uv run python scripts/dataset_report.py
```
