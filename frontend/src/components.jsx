import React from "react";
import { label, amount } from "./format";

/** One currency only: preserves the backend's original and adjusted totals. */
export function SummaryCard({ summary }) {
  return (
    <article className="summary-card">
      <div className="currency-heading">
        <h3>{summary.currency}</h3>
        <span className={summary.provisional ? "status warning" : "status"}>
          {summary.provisional
            ? "Provisional"
            : Number(summary.unexplained) === 0
              ? "Gap explained"
              : "Unexplained remainder"}
        </span>
      </div>
      <div className="big-number">{amount(summary.gap, summary.currency)}</div>
      <small>Original month-end gap</small>
      <dl>
        {[
          ["Platform net", summary.platform],
          ["Bank cash", summary.bank],
          [
            "Platform duplicate adjustment",
            summary.platform_duplicate_adjustment,
          ],
          ["Bank duplicate adjustment", summary.bank_duplicate_adjustment],
          ["Adjusted platform", summary.adjusted_platform],
          ["Adjusted bank", summary.adjusted_bank],
          ["Adjusted gap", summary.adjusted_gap],
        ].map(([k, v]) => (
          <div key={k}>
            <dt>{k}</dt>
            <dd>{amount(v, summary.currency)}</dd>
          </div>
        ))}
      </dl>
      <h4>Explanation of original gap</h4>
      <dl>
        {Object.entries(summary.bridge)
          .filter(([k, v]) => Number(v) !== 0)
          .map(([k, v]) => (
            <div key={k}>
              <dt>{label(k)}</dt>
              <dd>{amount(v, summary.currency)}</dd>
            </div>
          ))}
        <div className="remainder">
          <dt>Unexplained</dt>
          <dd>{amount(summary.unexplained, summary.currency)}</dd>
        </div>
      </dl>
    </article>
  );
}

/** Show uploaded values as text and retain source sheet/row metadata. */
export function EvidenceTable({ records }) {
  return (
    <div className="evidence-scroll">
      <table>
        <thead>
          <tr>
            {Object.keys(records[0]).map((k) => (
              <th key={k}>{k}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {records.map((r, n) => (
            <tr key={n}>
              {Object.keys(records[0]).map((k) => (
                <td key={k}>{String(r[k] ?? "—")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
