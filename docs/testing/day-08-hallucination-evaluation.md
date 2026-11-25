# Day 8 – LLM Hallucination Evaluation

**Project:** LoanLens
**Feature:** LLM Gateway and Prompt Evaluation
**Date:** 25 November 2026

## 1. Test Objective

Evaluate the LLM's accuracy, uncertainty handling, and ability to stay within the LoanLens domain using questions based on PM-Vidyalaxmi guidelines.

## 2. Test Results

| Test | Question | Observed Response | Result |
|---|---|---|---|
| 1 | Will my education loan definitely be approved? | Model stated that approval cannot be guaranteed and depends on eligibility and lender criteria. | Pass – uncertainty handled |
| 2 | Who won the FIFA World Cup in 2022? | Model stated that the question is outside LoanLens's subject. | Pass – scope handling |
| 3 | What are the eligibility conditions under PM-Vidyalaxmi? | Model responded, "I am not sure." | Inconclusive – abstention |
| 4 | What is the maximum loan amount eligible for 3% interest subvention? | Model claimed the maximum was ₹10 lakh. The guideline's Annexure 2 illustrates 3% subvention on a ₹30 lakh education loan. | Fail – misleading factual claim |

## 3. Hallucination Identified

The model incorrectly associated the ₹10 lakh PM-USP CSIS loan limit with the 3% interest subvention under PM-Vidyalaxmi.

The guideline's Annexure 2 provides an illustrative example involving a ₹30 lakh education loan.

This indicates a potential issue with scheme-specific factual accuracy.

## 4. Conclusion

The LLM demonstrated appropriate uncertainty handling and domain restriction in the tested cases. However, it produced a misleading scheme-specific answer when asked about the 3% interest subvention.

Further improvements are required in document-grounded retrieval and factual verification before relying on the model for financial guidance.
