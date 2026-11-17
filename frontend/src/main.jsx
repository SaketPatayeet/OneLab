import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Layers,
  ArrowDownToLine,
  UploadCloud,
  ChevronDown,
  ChevronUp,
  Search,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
} from "lucide-react";
import "./style.css";
import { label, amount } from "./format";
import { SummaryCard, EvidenceTable } from "./components";

function App() {
  const [file, setFile] = useState(null);
  const [month, setMonth] = useState("2026-10");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [filters, setFilters] = useState({
    type: "",
    currency: "",
    merchant: "",
    date: "",
    search: "",
  });
  const [open, setOpen] = useState({});
  // Reports reprocess the current file; no server-side session is stored.
  async function requestWorkbook(report = false) {
    setBusy(true);
    setError(null);
    if (!report) setResult(null);
    try {
      const body = new FormData();
      body.append("file", file);
      body.append("month", month);
      const res = await fetch(report ? "/api/report" : "/api/analyze", {
        method: "POST",
        body,
      });
      if (!res.ok) {
        const e = await res.json();
        throw e;
      }
      if (report) {
        const url = URL.createObjectURL(await res.blob());
        const a = document.createElement("a");
        a.href = url;
        a.download = `LedgerLens-${month}.xlsx`;
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 5000);
      } else {
        setResult(await res.json());
        setOpen({});
      }
    } catch (e) {
      setError(
        e.message
          ? e
          : {
              message: "Could not process the workbook. Please try again.",
              errors: [],
            },
      );
    } finally {
      setBusy(false);
    }
  }
  // Filtering changes the visible list, never the backend financial summaries.
  const issues =
    result?.issues.filter(
      (i) =>
        (!filters.type || i.type === filters.type) &&
        (!filters.currency || i.currency === filters.currency) &&
        (!filters.merchant || i.merchant === filters.merchant) &&
        (!filters.date || i.date === filters.date) &&
        (!filters.search ||
          `${i.reference} ${i.batch}`
            .toLowerCase()
            .includes(filters.search.toLowerCase())),
    ) || [];
  const select = (key, title) => (
    <select
      aria-label={title}
      value={filters[key]}
      onChange={(e) => setFilters({ ...filters, [key]: e.target.value })}
    >
      <option value="">{title}</option>
      {[...new Set(result.issues.map((i) => i[key]))].sort().map((v) => (
        <option key={v} value={v}>
          {label(v)}
        </option>
      ))}
    </select>
  );
  return (
    <>
      <header>
        <div className="brand">
          <Layers size={25} />
          <span>
            LedgerLens<span className="brand-dot">.</span>
          </span>
        </div>
        <span className="header-note">PAYMENT RECONCILIATION</span>
        <span className="session">
          <span /> Session only · No saved uploads
        </span>
      </header>
      <main>
        <div className="eyebrow">MONTH-END, MADE CLEAR</div>
        <div className="intro">
          <div>
            <h1>
              Follow the money.
              <br />
              <span>Find the difference.</span>
            </h1>
            <p>
              Trace payment gaps to the records behind them.
              <br />
              One workbook. Every difference in view.
            </p>
          </div>
          <div className="intro-note">
            <span className="step-number">01 — 03</span>
            <p>
              Upload your workbook
              <br />
              Inspect the evidence
              <br />
              Export your findings
            </p>
          </div>
        </div>
        <section className="upload-card">
          <div className="section-heading">
            <div>
              <h2>Start a reconciliation</h2>
              <p>
                Use the reference format and replace the example rows with your
                data.
              </p>
            </div>
            <a className="text-link" href="/api/reference">
              <ArrowDownToLine size={16} /> Reference Excel
            </a>
          </div>
          <div className="upload-controls">
            <label className="file-input">
              <UploadCloud size={25} />
              <div>
                <strong>
                  {file ? file.name : "Choose your Excel workbook"}
                </strong>
                <span>
                  .xlsx · Up to 8 MB · Platform_Transactions + Bank_Settlements
                </span>
              </div>
              <input
                aria-label="Upload Excel workbook"
                type="file"
                accept=".xlsx"
                onChange={(e) => {
                  setFile(e.target.files[0] || null);
                  setResult(null);
                  setError(null);
                }}
              />
            </label>
            <label className="month-label">
              Accounting month
              <input
                aria-label="Accounting month"
                type="month"
                value={month}
                onChange={(e) => {
                  setMonth(e.target.value);
                  setResult(null);
                }}
              />
            </label>
            <button
              disabled={!file || !month || busy}
              onClick={() => requestWorkbook()}
            >
              {busy ? "Processing…" : "Find the gaps"}
              <ArrowRight size={17} />
            </button>
          </div>
          <div className="upload-foot">
            <CheckCircle2 size={14} /> Original records preserved <span>•</span>{" "}
            Currencies analyzed separately <span>•</span> No account needed
          </div>
        </section>
        {error && (
          <section className="error" role="alert">
            <h3>
              <AlertCircle size={18} /> {error.message}
            </h3>
            <a href="/api/reference">Download the reference Excel</a>
            {error.errors?.length > 0 && (
              <ul>
                {error.errors.map((e, i) => (
                  <li key={i}>
                    {[e.sheet, e.row && `row ${e.row}`, e.column]
                      .filter(Boolean)
                      .join(" · ")}
                    : {e.message}
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}
        {result ? (
          <>
            <section className="results">
              <div className="section-heading">
                <div>
                  <div className="eyebrow">THE FINDINGS</div>
                  <h2>
                    Where the gaps are{" "}
                    <span className="count">{result.issues.length}</span>
                  </h2>
                  <p>
                    {result.counts.platform_rows.toLocaleString()} platform rows
                    · {result.counts.bank_rows.toLocaleString()} bank rows ·{" "}
                    {result.month}
                  </p>
                </div>
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() => requestWorkbook(true)}
                >
                  <ArrowDownToLine size={16} /> Export Excel report
                </button>
              </div>
              <div className="filters">
                <label className="search">
                  <Search size={16} />
                  <input
                    placeholder="Search reference or batch"
                    aria-label="Search issues"
                    value={filters.search}
                    onChange={(e) =>
                      setFilters({ ...filters, search: e.target.value })
                    }
                  />
                </label>
                {select("type", "All issue types")}
                {select("merchant", "All merchants")}
                {select("currency", "All currencies")}
                <input
                  type="date"
                  aria-label="Filter issue date"
                  value={filters.date}
                  onChange={(e) =>
                    setFilters({ ...filters, date: e.target.value })
                  }
                />
                <button
                  className="clear"
                  onClick={() =>
                    setFilters({
                      type: "",
                      merchant: "",
                      currency: "",
                      date: "",
                      search: "",
                    })
                  }
                >
                  Clear
                </button>
              </div>
              <div className="table-scroll">
                <table className="issues">
                  <thead>
                    <tr>
                      <th>Issue / reference</th>
                      <th>Merchant</th>
                      <th>Date</th>
                      <th>Affected amount</th>
                      <th>Gap contribution</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {issues.map((i) => (
                      <React.Fragment key={i.id}>
                        <tr className="issue-row">
                          <td>
                            <span className={"badge " + i.type}>
                              {label(i.type)}
                            </span>
                            <small>{i.reference}</small>
                          </td>
                          <td>
                            {i.merchant}
                            <small>{i.currency}</small>
                          </td>
                          <td>{i.date}</td>
                          <td>{amount(i.amount, i.currency)}</td>
                          <td
                            className={Number(i.impact) !== 0 ? "impact" : ""}
                          >
                            {Number(i.impact) > 0 ? "+" : ""}
                            {amount(i.impact, i.currency)}
                          </td>
                          <td>
                            <button
                              className="expand"
                              aria-label={`Evidence for ${i.reference}`}
                              aria-expanded={!!open[i.id]}
                              onClick={() =>
                                setOpen({ ...open, [i.id]: !open[i.id] })
                              }
                            >
                              {open[i.id] ? (
                                <ChevronUp size={18} />
                              ) : (
                                <ChevronDown size={18} />
                              )}
                            </button>
                          </td>
                        </tr>
                        {open[i.id] && (
                          <tr>
                            <td colSpan="6" className="evidence">
                              <strong>Evidence · {i.batch}</strong>
                              <p>{i.detail}</p>
                              <EvidenceTable records={i.evidence} />
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
                {!issues.length && (
                  <div className="empty">
                    <CheckCircle2 />
                    <h3>
                      {result.issues.length
                        ? "No issues match these filters"
                        : "No issues found in the supplied records"}
                    </h3>
                  </div>
                )}
              </div>
              <div className="table-note">
                {issues.length} findings shown · Expand a row to inspect source
                records. Affected amounts may overlap; use gap contributions for
                the financial bridge.
              </div>
            </section>
            <section className="summary-section">
              <div className="eyebrow">THE FINANCIAL PICTURE</div>
              <h2>Every currency, accounted for.</h2>
              <p>
                Gap = platform net activity − bank cash in the selected month.
              </p>
              <div className="summary-grid">
                {result.summaries.map((s) => (
                  <SummaryCard key={s.currency} summary={s} />
                ))}
              </div>
              <div className="coverage">
                <h3>Scope of this analysis</h3>
                {Object.entries(result.coverage).map(([k, v]) => (
                  <p key={k}>
                    <strong>{label(k)} coverage:</strong>{" "}
                    {v.start || "No records"} — {v.end || "No records"}
                  </p>
                ))}
                {result.limitations.map((v) => (
                  <p key={v}>{v}</p>
                ))}
              </div>
            </section>
          </>
        ) : (
          <section className="waiting">
            <FileSpreadsheet size={34} />
            <h3>Your records tell the story.</h3>
            <p>
              Upload a workbook to see timing gaps, duplicates,
              <br />
              rounding differences and unmatched refunds.
            </p>
            <div className="waiting-tags">
              <span>01 / Upload</span>
              <span>02 / Investigate</span>
              <span>03 / Export</span>
            </div>
          </section>
        )}
        <footer>
          <span>LedgerLens · Onelab assessment</span>
          <span>Evidence behind every difference.</span>
        </footer>
      </main>
    </>
  );
}
createRoot(document.getElementById("root")).render(<App />);
