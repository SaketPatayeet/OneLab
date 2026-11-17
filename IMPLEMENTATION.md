# Implementation Decisions

Status: implementation discussion recorded; application coding has not started under this plan.

Read alongside PLAN.md (behavior and acceptance criteria) and DATA_ASSUMPTIONS.md (sample data and financial conventions).

## Agreed decisions

| Area | Decision |
| --- | --- |
| Interface | React |
| Processing | Python, with decimal arithmetic for financial calculations |
| Retention | Current session only; no reconciliation history or database |
| Access | Public deployed link; no sign-in |
| Input | One Excel workbook following our reference workbook format |
| Invalid data | Block financial analysis, explain validation errors, and direct users to the downloadable reference Excel |
| Evidence | Expandable rows within the issues table |
| Demo behavior | Examiners upload their own data; no sample-loading shortcut required |
| Hosting | No provider preference; choose a simple deployment suitable for the timed assessment |
| Outputs | Interactive dashboard and downloadable Excel report |

## Upload contract and reference file

The simplest approach for the time limit is a fixed workbook schema. Avoid automatic column mapping or guessing the meaning of unfamiliar sheets. No upload mechanism can guarantee error-free inputs; predictable validation makes errors easy to correct.

- Accept .xlsx files with the existing Platform_Transactions and Bank_Settlements sheets and their documented column names.
- Provide a prominent Download reference Excel link before upload and beside validation errors. Use the existing data workbook, clearly labelled as synthetic example data; never distribute the answer key as the reference upload template.
- Explain that users should retain the headers and replace the example rows with their own records.
- Match columns by header name, so column order does not affect interpretation.
- Use supporting merchant, fee-rule and dictionary sheets for reference; core matching must use uploaded transaction and settlement records, not hardcoded sample IDs or totals.
- Define required columns, optional supporting sheets and allowed values explicitly in one schema module and in the reference instructions.
- Require numeric amount cells and actual dates or documented ISO date strings. Reject formulas in required input fields to avoid relying on missing or stale cached results.
- Preserve workbook sheet names and Excel row numbers as evidence references.

## Validation experience

On a failed upload, show: Invalid data. Please use the format in the reference Excel workbook.

Also list actionable errors with sheet, row, column and reason where available, for example: Platform_Transactions, row 12, net_amount: expected a numeric amount.

- Block reconciliation and financial export until structural and field validation succeeds.
- Collect useful errors together rather than forcing users through one error per upload.
- Validate required fields, supported dates, monetary precision, identifiers, currency and event types.
- Treat exact duplicates, orphan refunds, rounding differences and unmatched records as findings to analyze, not reasons to reject an otherwise valid workbook.
- Conflicting immutable IDs remain visible as unresolved reconciliation findings. Do not choose a conflicting copy automatically or claim definitive totals for an affected scope.
- Keep technical stack traces out of the user interface.

## Proposed internal structure

These are implementation recommendations within the agreed React/Python stack.

### Frontend

- React application with an upload area, reference download and reconciliation month selector.
- Validation-error view.
- Issues table with type, merchant, currency and date filters.
- Expandable evidence rows containing original source records and calculations.
- Per-currency summaries with original totals, duplicate adjustments, adjusted totals and the signed gap explanation.
- Download report action.
- Loading, empty-results and request-failure states.
- Render uploaded values as text; do not interpret spreadsheet contents as HTML.

### Python service

- Use FastAPI for upload and report endpoints and openpyxl for reading/writing Excel files.
- Keep workbook parsing, validation, reconciliation and report generation as separate modules.
- Perform financial calculations in Decimal with explicit rounding rules. Serialize monetary values as decimal strings; the frontend formats these values without recomputing financial totals.
- Implement reconciliation as a deterministic function over validated records plus the selected month. It must have no dependency on UI state, the answer key or the existing draft JavaScript engine.
- Produce one analysis result structure used by both dashboard and export to prevent inconsistent calculations.
- Escape or safely write user-supplied text in exported workbooks so it cannot become an Excel formula.

### Session handling

- Hold the selected workbook in browser memory for the current page session.
- Process uploads in server memory for each request; avoid persistent storage and a database.
- Let the analysis request return validated findings, evidence and summaries.
- For report download, send the same file and selected month again, run the same deterministic analysis, and stream the workbook response. This avoids shared server session state and report persistence.
- Changing the selected month triggers a new analysis of the same file.
- Refreshing or closing the page clears frontend state. Release server request buffers after processing; do not log uploaded financial rows.
- Set explicit upload and row-count limits appropriate to hosting capacity and explain limit errors clearly.

## Financial implementation sequence

1. Parse validated input while retaining source row references.
2. Identify exact duplicate groups and conflicting IDs.
3. Preserve original totals and build canonical records excluding only extra exact copies.
4. Match batches by reference; verify merchant and currency consistency.
5. Check refund originals against all supplied payment history.
6. Classify timing, missing matches, rounding and residual differences using source evidence.
7. Calculate original and adjusted monthly totals separately by currency.
8. Allocate each monetary contribution once; distinguish affected amount from signed gap impact.
9. Return evidence-backed findings and expose any unexplained remainder or completeness limitation.

Do not label a discrepancy as rounding merely because it is small: the alternate documented rounding calculation must explain it. Do not infer next-month settlement when the corresponding bank record is absent. A settled orphan refund can contribute zero additional cash difference while remaining an issue.

## Deployment recommendation

Use one service capable of running Python and serving the built React assets from the same origin. This reduces deployment configuration and avoids separate frontend/backend origins for the assessment. Package it as a container if required by the selected host.

A provider remains to be selected and its availability, pricing and public access verified before deployment. The earlier private Sites registration is not a public deployment of this planned Python application. Public access is agreed, but publication is a later implementation step.

## Build and verification order

1. Freeze and document the workbook contract; expose the reference download.
2. Implement parser and blocking validation, with useful errors.
3. Implement the deterministic reconciliation modules and verify against the answer key.
4. Implement the upload flow, issues table and expandable evidence.
5. Add per-currency summaries and Excel export from the shared result structure.
6. Verify another workbook with the same schema, using changed IDs and amounts to catch sample-specific assumptions.
7. Test clean data, duplicates, conflicting IDs, orphan refunds, rounding, missing settlements, boundary dates, incomplete coverage and invalid uploads.
8. Verify dashboard/export agreement and public deployment behavior.

Completion means the examiner can download the reference, upload a conforming workbook, select a month, inspect issues and evidence, and download matching results. The existing PLAN.md acceptance criteria also apply.
