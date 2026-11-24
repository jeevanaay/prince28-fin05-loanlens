# LoanLens â€” Dataset Source Register

## 1. Official Source Portals

| Source | URL | Status |
|---|---|---|
| PM-Vidyalaxmi | https://www.pmvidyalaxmi.co.in/ | Reviewed |
| Ministry of Education | https://www.education.gov.in/ | Reviewed |
| State Bank of India | https://sbi.bank.in/ | Reviewed |
| Indian Banks' Association | https://www.iba.org.in/ | Source identified |

## 2. Documents Reviewed

### 2.1 SBI â€” Global Ed-Vantage Scheme

- **Source:** State Bank of India
- **URL:** https://sbi.bank.in/web/personal-banking/loans/education-loans/global-ed-vantage-scheme
- **Document:** Global Ed-Vantage scheme page and November 2024 MITC
- **Reviewed:** 17 November 2026
- **Applicability:** Eligible full-time overseas education programmes

**Key findings:**
- Maximum loan amount: â‚¹3 crore.
- Collateral-free loan facility: Up to â‚¹50 lakh for select premier institutions, subject to scheme conditions.
- Margin: 10% as stated in the November 2024 MITC; verify against the latest applicable terms.
- Moratorium: Course period + 6 months.
- Simple interest is charged during the course and moratorium period.
- Unpaid accrued interest is added to the principal for EMI calculation.
- Repayment tenure: Up to 15 years.

### 2.2 PM-Vidyalaxmi Scheme Guidelines

- **Source:** Ministry of Education, Government of India
- **Document:** PM-Vidyalaxmi Scheme Guidelines
- **URL:** https://static.investindia.gov.in/s3fs-public/2025-03/pm_vidyalaxmi_scheme_guidelines.pdf
- **Reviewed:** 17 November 2026
- **Applicability:** Eligible Quality Higher Educational Institutions (QHEIs) in India.

**Key findings:**
- Students admitted to eligible QHEIs in India may qualify, subject to scheme conditions.
- Students with annual family income up to â‚¹8 lakh may qualify for 3% interest subvention.
- Interest subvention is available on eligible education loans up to â‚¹10 lakh.
- The benefit applies during the moratorium period.
- Moratorium: Course period + 1 year.
- The scheme is not applicable to overseas MS programmes.

### 2.3 IBA â€” Model Educational Loan Scheme (MELS), 2022

- **Source:** Indian Banks' Association
- **Document:** IBA Model Educational Loan Scheme, 2022
- **URL:** https://d2w7l1p59qkl0r.cloudfront.net/upload/iba-model-education-loan-scheme.pdf
- **Version:** 2022; amendments approved in 2023
- **Reviewed:** 17 November 2026
- **Applicability:** Eligible higher education programmes in India and abroad.

**Key findings:**
- Finance is based on the student's need and the bank's assessment; there is no single universal maximum loan amount.
- Margin under the model scheme:
  - Up to â‚¹4 lakh: No margin.
  - Above â‚¹4 lakh up to â‚¹7.5 lakh: 5% for studies in India and 15% for studies abroad.
  - Above â‚¹7.5 lakh: Subject to the lending bank's policy.
- Collateral requirements generally apply above â‚¹7.5 lakh, subject to applicable credit-guarantee coverage and bank policy.
- Moratorium: Course period + 1 year.
- Repayment: Up to 15 years, excluding the moratorium period.
- Simple interest is charged during the study and moratorium period.
- Unpaid accrued interest may be added to the principal when repayment begins.
- Actual terms may differ between banks because individual lenders can apply their own approved policies.

### 2.4 PM-USP â€” Central Sector Interest Subsidy Scheme (CSIS)

- **Source:** Ministry of Education, Government of India
- **Document:** PM-USP Central Sector Interest Subsidy Scheme Guidelines
- **URL:** https://www.canarabank.bank.in/documents/d/guest/csis-guideline-01-04-2022
- **Guideline date:** 1 April 2022
- **Reviewed:** 17 November 2026
- **Applicability:** Eligible professional and technical courses in India, subject to scheme conditions.

**Key findings:**
- Annual family income limit: â‚¹4.5 lakh.
- Provides 100% interest subsidy during the course period + 1 year.
- Subsidy applies to eligible education loans up to â‚¹10 lakh.
- Not applicable to overseas MS programmes.
- Collateral-free loans up to â‚¹7.5 lakh are subject to applicable CGFSEL coverage and eligibility conditions.
- Margin requirements must be checked against the applicable IBA model scheme and bank policy.

### 2.5 Bank of Baroda â€” Baroda Scholar

- **Source:** Bank of Baroda
- **URL:** https://bankofbaroda.bank.in/loans/education-loan/baroda-scholar
- **Reviewed:** 17 November 2026
- **Applicability:** Eligible higher education programmes abroad, subject to scheme conditions.

**Key findings:**
- Maximum loan amount: â‚¹150 lakh, as stated in the bank's scheme information.
- Interest rate: Starting from BRLLR + 1.75; verify the current applicable rate separately.
- Collateral requirements: Pending verification.
- Margin requirements: Pending verification.
- Moratorium: Pending verification.
- Interest treatment during moratorium: Pending verification.
- Subsidy income limit: Not specified as a benefit under this bank scheme; check separate government subsidy eligibility.

## 3. Documents Pending Collection

- [ ] Latest SBI Global Ed-Vantage MITC and interest-rate details.
- [ ] Latest PM-Vidyalaxmi FAQs and scheme updates.
- [ ] Latest IBA Model Educational Loan Scheme amendments, if any.
- [ ] Latest PM-USP CSIS guidelines and updates.
- [ ] Latest Bank of Baroda Baroda Scholar detailed terms.
- [ ] Education-loan scheme documents from seven additional banks.
- [ ] Verify collateral, margin, moratorium and interest rules for every bank.

## 4. Data Integrity Rules

1. Use official government documents, bank publications and official scheme guidelines.
2. Record the source document, publication/version date and review date for every scheme.
3. Do not invent missing values or assume that one bank follows another bank's terms.
4. Use `null` when a value is unavailable or cannot be verified.
5. Distinguish between the document's effective date and the date it was reviewed.
6. Verify collateral, margin, moratorium, interest and subsidy conditions before adding records.
7. Record bank-specific variations separately from IBA model guidelines.
8. Recheck floating interest rates before using them in calculations.
9. Do not treat PM-Vidyalaxmi or CSIS benefits as applicable to overseas education unless the relevant official guidelines explicitly permit it.
10. Keep source references traceable so every dataset value can be checked against its original document.

## 5. Dataset Schema

Every LoanLens record must contain the following fields:

| Field | Description |
|---|---|
| `id` | Unique record identifier |
| `lender` | Bank or scheme provider |
| `scheme` | Education-loan scheme name |
| `max_amount` | Maximum loan amount, in INR |
| `collateral_threshold` | Loan amount or conditions at which collateral is required |
| `margin_pct` | Margin percentage required |
| `moratorium` | Repayment holiday period |
| `interest_rule` | Interest calculation and repayment treatment |
| `subsidy_income_limit` | Annual family-income eligibility limit for subsidy |

**Dataset rules:**
- Use unique IDs starting from `001`.
- Store numeric values as numbers, not quoted strings.
- Store descriptive rules as strings.
- Use `null` for unavailable values.
- Do not add unsupported values merely to complete a record.

## 6. Initial Collection Report

Generated using `scripts/dataset_report.py`.

| Metric | Result |
|---|---:|
| Manifest entries | 11 |
| Successfully downloaded documents | 8 |
| Blocked collection attempts | 3 |
| Total downloaded size | 3.35 MB |
| PDF pages detected | 28 |
| Source organisations | 6 |

### Source breakdown

| Source | Downloaded documents |
|---|---:|
| Bank of Baroda | 1 |
| Canara Bank | 1 |
| Indian Bank | 1 |
| Ministry of Education | 1 |
| Press Information Bureau | 1 |
| SBI | 3 |

### Initial source collection records (historical)

| Source | Document | URL | Licence / reuse status | Collection status | Method |
|---|---|---|---|---|---|
| Ministry of Education | PM-Vidyalaxmi Guidelines | [Official source](https://www.dohe-education.gov.in/static/uploads/2026/02/c0a1cba1bd387f52bb3735542e679632.pdf) | Government document - reuse terms to be verified | Downloaded | manual |
| Ministry of Education | PM-USP CSIS Public Notice | [Official source](https://www.education.gov.in/sites/upload_files/mhrd/files/document-reports/pncftis.pdf) | Government document - reuse terms to be verified | Blocked | url |
| SBI | Global Ed-Vantage Scheme | [Official source](https://sbi.bank.in/web/personal-banking/loans/education-loans/global-ed-vantage-scheme) | Official website - reuse terms to be verified | Downloaded | url |
| SBI | Global Ed-Vantage MITC November 2024 | [Official source](https://sbi.co.in/documents/16012/49183003/MITC-Global%2BEd-Vantage-%2BNov%272024.pdf/5df57fed-7229-40ca-b367-ccfd7d267264) | Official bank PDF - reuse terms to be verified | Downloaded | manual |
| SBI | Education Loan Interest Rates | [Official source](https://sbi.bank.in/web/interest-rates/interest-rates/loan-schemes-interest-rates/education-loan-scheme) | Official website - reuse terms to be verified | Downloaded | url |
| Bank of Baroda | Baroda Scholar Education Loan | [Official source](https://bankofbaroda.bank.in/loans/education-loan/baroda-scholar) | Official website - reuse terms to be verified | Downloaded | url |
| Canara Bank | Masters Degree Education Loan India and Abroad | [Official source](https://www.canarabank.bank.in/Education-Loan-Scheme-for-pursuing-Masters-Degree) | Official website - reuse terms to be verified | Downloaded | url |
| Indian Bank | IB Education Loan IBA | [Official source](https://indianbank.bank.in/en/ib-education-loan-iba) | Official website - reuse terms to be verified | Downloaded | url |
| PM-Vidyalaxmi Portal | PM-Vidyalaxmi Official Portal | [Official source](https://www.pmvidyalaxmi.co.in/) | Manual access only - bot restrictions | Blocked | url |
| Press Information Bureau | PM-Vidyalaxmi Press Release | [Official source](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2290079) | Government release - reuse terms to be verified | Downloaded | manual |

### Known gaps

- The initial collection contains only 28 detected PDF pages; the expanded target is 1,500+ pages.
- Some source requests were blocked because robots.txt disallowed crawling or could not be checked. These restrictions must not be bypassed.
- Some documents were collected manually. Manual collection does not establish permission for automated crawling or redistribution.
- Licence and reuse terms are not yet verified for several sources. Verify permissions before redistribution.
- The current storage estimate is based on only 8 downloaded documents.
- Additional bank documents, FAQs, circulars and policy documents remain to be collected and reviewed.

Raw documents are stored locally in `data/raw/` and excluded from Git. The committed `data/manifest.jsonl` records collection metadata and document hashes.

These figures describe the current collection only. They do not represent the final target corpus.

## Source compliance and verification

Checked on: 2026-11-23

### Robots.txt verification

| Domain | Result | Collection status |
|---|---|---|
| dohe-education.gov.in | `Allow: /` verified | Robots policy permits crawling |
| education.gov.in | `Allow: /` verified | Robots policy permits crawling |
| sbi.bank.in | No general disallow rule verified | Robots policy permits crawling |
| sbi.co.in | Redirects to sbi.bank.in robots.txt | Same policy as sbi.bank.in |
| bankofbaroda.bank.in | General PDF paths disallowed; source HTML path is not covered by that rule | Do not fetch disallowed PDF paths |
| canarabank.bank.in | robots.txt could not be verified | Automated collection not cleared |
| indianbank.bank.in | robots.txt could not be verified | Automated collection not cleared |
| pmvidyalaxmi.co.in | robots.txt could not be verified | Automated collection not cleared |
| pib.gov.in | robots.txt could not be verified | Automated collection not cleared |

An inaccessible robots.txt file is not proof that crawling is prohibited. It means permission to automate collection has not been established.

### Reuse and licensing status

- DoHE: reproduction permitted with attribution, subject to accuracy and third-party content exclusions.
- Ministry of Education (education.gov.in): applicable reuse terms remain unverified.
- SBI: applicable reuse terms remain unverified.
- Bank of Baroda: personal, informational and non-commercial use only; wider reproduction or redistribution requires prior written permission.
- Canara Bank: reproduction requires prior permission; third-party material is excluded.
- Indian Bank: prior written approval required for display or printing; other reuse rights remain unestablished.
- PM-Vidyalaxmi portal: protected content; copying, downloading, storing or redistribution requires express written authorization, except as necessary to use the service.
- PIB: reproduction permitted with prominent attribution and accurate, non-misleading use; third-party material is excluded.

### Outstanding compliance gaps

1. Confirm robots.txt access and applicable collection rules for Canara Bank, Indian Bank, PM-Vidyalaxmi and PIB before automated collection.
2. Obtain or verify applicable reuse terms for Ministry of Education and SBI materials before redistribution.
3. Obtain written permission where required by Canara Bank, Indian Bank, Bank of Baroda or PM-Vidyalaxmi terms.
4. Check individual documents for third-party copyright notices before reusing their contents.
5. Historical downloads cannot be certified as compliant solely from the current robots.txt checks. Their original access conditions have not all been independently established.

Until these gaps are resolved, do not treat the affected sources as cleared for automated collection or redistribution.

### Collection eligibility controls

The collection pipeline now enforces an explicit source-eligibility gate.

- `data/sources.csv` requires `collection_status` and `collection_evidence`.
- Supported statuses are `approved`, `pending` and `blocked`.
- URL collection rejects sources that are not approved.
- Sitemap, repository and manual collection require explicit eligibility arguments.
- These controls apply before network access, repository cloning or local file copying.
- Every collection decision is recorded in the manifest.

**Important:** Setting a source to `approved` is an administrative decision, not proof that legal permission exists. Approval must be supported by documented collection and reuse rights.

Current source register: 15 entries — 9 pending, 6 blocked, 0 approved.

Historical downloads are not automatically considered approved by the new controls. Their original collection conditions and reuse rights remain subject to verification.
