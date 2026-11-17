# LedgerLens

React + FastAPI month-end payment reconciliation. Session-only processing; no database or login. Uploaded records stay in request/browser memory. Exact financial calculations use Python Decimal.

## Run the completed production build locally

From this directory:

```powershell
python -m pip install -r requirements.txt
npm.cmd ci
npm.cmd run build
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Upload data/Onelab_Reconciliation_Data.xlsx and select October 2026. The reference workbook is also downloadable in the app. Examiners can replace example rows while preserving the column contract. Nothing uses the answer key at runtime.

## Development

Run the Python server above, then `npm.cmd run dev` in another terminal. Vite proxies /api to port 8000. For changes to production UI, rerun the build and restart the Python service.

## Verify

```powershell
python -m unittest discover -s tests -v
npm.cmd run build
```

Tests cover answer-key totals and categories, changed IDs, conflicts, malformed workbooks, formulas, missing columns, missing settlements, invalid months, orphan-refund impacts and the API/report pipeline. Financial exports include source rows and issue evidence. Conflicting currencies are marked provisional.

## Workbook contract

Required sheet names and fields live in backend/schema.py. Column order is flexible; column names are exact. Optional reference sheets are not required. Supported currencies are INR, USD and EUR; methods are card, bank_transfer and INR-only upi. Amounts must be numeric, dates Excel dates or YYYY-MM-DD, and formulas must be replaced with values. Limits: 8 MB upload, 20,000 total data rows, 64 MB expanded workbook. No foreign exchange conversion. Refund originals are searched across all supplied history. Fee and rounding conventions follow DATA_ASSUMPTIONS.md.

## Architecture

- backend/schema.py: workbook parsing and field validation.
- backend/reconcile.py: deterministic reconciliation and evidence.
- backend/report.py: Excel generation, safely writing user text as strings.
- backend/app.py: upload, analysis, reference and export endpoints; serves built React assets.
- frontend/src: issues-first UI, filters, expandable evidence and currency summaries.
- tests: backend and API checks.

The older dist/engine.mjs and scripts/generate.mjs files are unused early drafts. The active application uses backend/ and frontend/. Existing .openai/hosting.json belongs to an earlier private, unpublished registration and is not a deployment configuration for this Python service.

## Deployment

The Dockerfile builds React and serves it with FastAPI from one origin. Use a Python/container-capable host and expose its configured PORT. No secrets or database are needed by the application itself. Provisioning public hosting requires an authenticated hosting service; this workspace currently has no configured provider. Docker execution could not be verified because the local Docker daemon is unavailable. Public deployment and browser interaction QA remain pending.

## Known limits

Missing records can only be described relative to the uploaded date coverage; a missing refund original is not proof of an invalid refund. An unknown rounding policy or incomplete batch allocation can remain unexplained. This assessment app does not model FX, holidays, reserves, chargebacks, split settlement or production workload controls.

## Code readability and formatting

Use four-space Python indentation and the repository's Black configuration. React, CSS and configuration files use Prettier with two-space indentation.

```powershell
python -m pip install -r requirements-dev.txt
python -m black backend tests data_tools
npm.cmd run format
```

Check formatting with `python -m black --check backend tests data_tools` and `npm.cmd run format:check`.

Start reading with backend/app.py (request flow), backend/schema.py (Excel contract), then backend/reconcile.py (classification and the signed cash bridge). backend/report.py exports that same result. In the UI, main.jsx owns session state and requests, components.jsx holds the evidence table and currency card, and format.js handles display formatting only. Comments explain financial conventions and non-obvious decisions; function and variable names describe the steps.
