# LoanLens — Source Registry

This document tracks the official sources used by LoanLens to provide education-loan information.

## Source Record Format

Each source must include:

- **Source name:** Official name of the institution or scheme.
- **Source URL:** Original official source URL.
- **Source type:** Bank website, government portal, official PDF, etc.
- **Format:** HTML, PDF, CSV, or API.
- **Terms on card:** Loan amount, interest rate, repayment period, eligibility, collateral requirements, and other relevant terms.
- **Last verified:** Date the source was last checked.

## Sources

### 1. State Bank of India — Global Ed-Vantage

- **Source name:** State Bank of India
- **Scheme:** Global Ed-Vantage
- **Source URL:** https://sbi.bank.in/web/personal-banking/loans/education-loans/global-ed-vantage-scheme
- **Additional source:** https://sbi.co.in/documents/16012/49183003/MITC-Global%2BEd-Vantage-%2BNov%272024.pdf/5df57fed-7229-40ca-b367-ccfd7d267264
- **Interest rate source:** https://sbi.bank.in/web/interest-rates/interest-rates/loan-schemes-interest-rates/education-loan-scheme
- **Source type:** Official bank website and bank PDF
- **Format:** HTML and PDF
- **Terms on card:**
  - Maximum loan amount: ₹3 crore
  - Collateral-free limit: Up to ₹50 lakh for select premier institutions
  - Margin: 10%
  - Moratorium: Course period + 6 months
  - Interest: Floating rate; simple interest during course and moratorium
  - Repayment: Up to 15 years
- **Last verified:** 2026-11-23

### 2. Government of India — PM-Vidyalaxmi

- **Source name:** Department of Higher Education, Ministry of Education
- **Scheme:** Pradhan Mantri Vidyalaxmi
- **Source URL:** https://www.dohe-education.gov.in/static/uploads/2026/02/c0a1cba1bd387f52bb3735542e679632.pdf
- **Additional source:** https://www.pmvidyalaxmi.co.in/
- **Reference:** https://www.pib.gov.in/PressReleasePage.aspx?PRID=2290079
- **Source type:** Government guidelines PDF, official portal and PIB release
- **Format:** PDF and HTML
- **Terms on card:**
  - Loan amount: No fixed upper cap under the scheme guidelines; based on eligible institutional fees and expenses
  - Security: Collateral-free and guarantor-free
  - Eligibility: Merit-based admission to designated Quality Higher Education Institutions (QHEIs) in India
  - Interest subvention: 3% on eligible loans up to ₹10 lakh for families with annual income up to ₹8 lakh
  - Moratorium: Course period + 1 year
  - Repayment: Up to 15 years, excluding moratorium
- **Related scheme:** PM-USP CSIS provides full interest subvention for eligible students with annual family income up to ₹4.5 lakh pursuing approved technical/professional courses. This is a separate benefit with separate eligibility conditions.
- **Last verified:** 2026-11-23

## Verification Notes

- Prefer official government and bank sources.
- Record the original source URL for every loan or scheme.
- Keep dynamic interest rates linked to the bank's latest official rate page.
- Distinguish scheme benefits from bank-specific loan terms.
- Do not publish unverified loan terms.
- Recheck source information before updating production records.
- Record the verification date whenever a source is checked.
