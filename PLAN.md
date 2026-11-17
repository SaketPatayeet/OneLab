# Payment Reconciliation Plan

Status: agreed product and analysis plan; implementation is a separate next step.

## Objective and audience

Explain where month-end payment reconciliation gaps occur, with traceable evidence and amounts. Serve both finance analysts investigating individual records and finance leadership reviewing the overall position.

Present an issue list first, followed by financial summaries. Deliver an interactive dashboard and a downloadable Excel reconciliation report.

## Inputs and scope

- Accept the generated dataset and other Excel workbooks using the same sheets and columns.
- Use Platform_Transactions and Bank_Settlements as the primary inputs. Merchant, fee-rule and dictionary sheets provide supporting context.
- Allow selection of the reconciliation month; use October 2026 for the sample.
- Preserve surrounding-month records for settlement tracing and refund-reference checks.
- Follow DATA_ASSUMPTIONS.md for the sample's currencies, fees, batching, refund treatment and one-to-two-calendar-day settlement policy.
- Analyze currencies separately; do not combine currency amounts without an explicit conversion policy.
- Use the answer-key workbook only for verification, never as an analysis input.

## User flow

1. Upload an Excel workbook.
2. Review validation results and select the reconciliation month.
3. View the issue list, with filters for issue type, merchant, currency and date.
4. Expand an issue to inspect its supporting rows and calculations.
5. Review per-currency financial summaries and the explanation of the gap.
6. Download an Excel reconciliation report.

## Input validation

- Check required sheets and columns, identifiers, dates, numeric amounts, currency codes and event types.
- Check amount signs and consistency of gross, processing fee and net fields under the stated input contract.
- Retain workbook sheet and row references for evidence.
- Distinguish invalid records from financial discrepancies.
- Show missing or invalid fields clearly. Never silently discard invalid rows and present the resulting totals as complete.
- Report data coverage and limitations relevant to the selected month.
- Duplicate IDs with identical contents are exact duplicates. Duplicate IDs with differing contents are conflicts and must not be resolved by arbitrarily choosing a row.

## Reconciliation approach

### Original and adjusted views

Preserve all uploaded rows and calculate original source totals. Create a separate comparison excluding extra copies of exact duplicates, retaining one copy per immutable ID. Show the original totals, duplicate adjustments and adjusted totals explicitly. Keep every duplicate copy inspectable. Conflicting records prevent definitive reconciliation of the affected scope and remain visible as unresolved issues.

### Matching

- Link platform events and bank settlements using their shared batch reference.
- Validate that merchant and currency agree across each match.
- Compare unique platform events with unique bank settlements.
- Trace individual transactions to their containing settlement batch and settlement date.
- Include refunds in signed batch totals and check their original payment references against all supplied payment history.
- Flag ambiguous batches or unsupported structures rather than forcing a match.

### Issue types and evidence

| Issue | Evidence | Conclusion supported by the data |
| --- | --- | --- |
| Settlement outside the selected month | Activity date, batch reference, bank settlement date and amount | Confirmed timing contribution to the month-end gap |
| Prior-month activity settled this month | Prior activity and current-month bank cash | Boundary inflow contributing to the comparison |
| Exact duplicate | Repeated ID and identical source rows | Additional imported copies distort original totals |
| Conflicting ID | Same ID with differing contents | Identity conflict requiring unresolved treatment |
| Orphan refund | Refund, original reference and search across supplied history | Original payment is absent from supplied records |
| Rounding difference | Sum of individually rounded nets versus rounded sum of unrounded nets | Amount difference consistent with the documented rounding policies |
| Missing settlement | Platform batch and absence of a matching bank record in supplied coverage | Settlement not found in supplied data |
| Unmatched bank record | Bank record and absence of corresponding platform records | Platform match not found in supplied data |
| Unexplained amount difference | Matched source records and residual calculation | Amount difference not explained by supported rules |

A known next-month settlement is different from a settlement merely absent from the upload. Do not infer future settlement without evidence. A duplicate's operational cause, such as an import retry, cannot be established from identical rows alone. A missing refund original does not prove that the refund was invalid.

## Issue list and evidence detail

Each issue should show:

- Issue type and record or batch reference.
- Merchant and currency.
- Relevant transaction and settlement dates.
- Affected amount.
- Signed contribution to the selected month's platform-minus-bank gap.
- Evidence references and a concise factual explanation.

Keep affected amount separate from gap contribution: an orphan refund may have a nonzero affected amount but no additional cash-gap impact when already settled. Do not sum affected amounts across overlapping issues as though they were independent losses.

Expanding an issue shows source rows, related transactions and settlements, and the relevant calculation. Show both duplicate copies and both rounding calculations where applicable. Include evidence and amounts only; suggested remediation actions are outside the agreed presentation scope.

## Financial summaries

For each currency, show:

1. Original platform net activity in the selected month.
2. Original bank cash received in the selected month.
3. Original gap: platform net minus bank cash.
4. Explicit duplicate adjustments and adjusted source totals.
5. A signed breakdown of timing, prior-month inflows, rounding and other differences.
6. Any remaining unexplained amount and completeness limitations.

Every monetary contribution must be counted once even when an issue has several labels. The original gap must equal the sum of the signed explanation contributions plus the unexplained remainder. A zero cash remainder does not imply there are no record-quality issues. Conflicts and invalid data must not be hidden behind a claim of complete reconciliation.

## Excel export

Include:

- Issue list with amounts and signed gap contributions.
- Supporting source evidence with sheet and row references.
- Per-currency financial summaries and gap breakdowns.
- Original-versus-adjusted totals and duplicate adjustments.
- Input-validation problems, selected month, source coverage and analysis assumptions.

Exported values must agree with the dashboard for the same analysis. Preserve source records and avoid modifying the uploaded workbook.

## Verification and acceptance criteria

- Detect all planted sample cases using only the data workbook.
- Compare findings and currency totals with the separate answer key afterward.
- Verify transaction-to-batch tracing and exact one-to-two-day sample settlement dates.
- Verify that extra exact copies affect original totals once per extra copy and do not inflate adjusted totals.
- Verify that settled orphan refunds remain visible with zero additional cash-gap impact.
- Verify the accumulated rounding examples using decimal-safe arithmetic and the documented rounding policy.
- Verify the signed October bridge independently for INR, USD and EUR, including September inflows and November settlements.
- Test clean data, missing columns, invalid fields, conflicting IDs, absent settlements, unmatched bank records, unexplained mismatches and incomplete date coverage.
- Verify that imported answer-key labels are not required by the analysis.
- Verify dashboard filtering, evidence expansion and exported report consistency.

## Implementation sequence

1. Finalize the import contract and validation behavior against the existing workbook.
2. Implement source preservation, duplicate handling, batch matching and evidence-based classification.
3. Implement per-currency totals and gap explanations; verify against the answer key.
4. Build the issues-first dashboard, filters and evidence detail.
5. Add the financial summaries and Excel export.
6. Run the agreed verification cases and review the completed experience.

Framework, hosting and deployment details remain implementation decisions. This plan does not initiate application implementation or deployment.
