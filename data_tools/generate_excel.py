from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict, Counter
import random, json
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data"
R = random.Random(92026)
D = Decimal
CENT = D("0.01")


def money(x):
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def total(rows, field):
    return sum((r[field] for r in rows), D(0))


merchants = [
    (f"M{i:03}", name)
    for i, name in enumerate(
        [
            "Cedar Market",
            "Harbor Books",
            "Maple Apparel",
            "Orbit Electronics",
            "Willow Home",
        ],
        1,
    )
]
fees = {
    "card": (D("0.029"), {"INR": D("2"), "USD": D(".30"), "EUR": D(".25")}),
    "bank_transfer": (D(".008"), {"INR": D("1"), "USD": D(".10"), "EUR": D(".10")}),
    "upi": (D(".003"), {"INR": D("0")}),
}
rows = []
start = date(2026, 9, 28)
# Balanced date coverage guarantees records on every boundary day.
for i in range(984):
    dt = start + timedelta(days=i % 38)
    merchant = merchants[R.randrange(5)][0]
    currency = R.choice(["INR", "USD", "EUR"])
    method = R.choice(
        ["card", "bank_transfer"] + (["upi"] if currency == "INR" else [])
    )
    factor = 80 if currency == "INR" else 1
    gross = (
        D(R.randint(500, 20000) if R.random() < 0.92 else R.randint(100000, 500000))
        * factor
        / 100
    )
    rate, fixed = fees[method]
    raw_fee = gross * rate + fixed[currency]
    fee = money(raw_fee)
    batch = f"BAT-{dt:%Y%m%d}-{merchant}-{currency}"
    rows.append(
        dict(
            transaction_id=f"TXN-{i+1:06}",
            transaction_date=dt,
            merchant_id=merchant,
            currency=currency,
            payment_method=method,
            event_type="payment",
            original_transaction_id="",
            gross_amount=gross,
            processing_fee=fee,
            net_amount=gross - fee,
            unrounded_fee=raw_fee,
            batch_reference=batch,
        )
    )
# Eight valid full refunds and eight refunds whose originals are absent.
for j in range(16):
    original = next(
        t
        for t in rows[:984]
        if t["transaction_date"] == date(2026, 10, 1 + j // 2)
        and t["event_type"] == "payment"
    )
    dt = date(2026, 10, 18 + j // 2)
    r = dict(original)
    r.update(
        transaction_id=f"TXN-{985+j:06}",
        transaction_date=dt,
        event_type="refund",
        original_transaction_id=(
            original["transaction_id"] if j < 8 else f"EXT-MISSING-{j-7:03}"
        ),
        gross_amount=-original["gross_amount"],
        processing_fee=D(0),
        net_amount=-original["gross_amount"],
        unrounded_fee=D(0),
        batch_reference=f"BAT-{dt:%Y%m%d}-{original['merchant_id']}-{original['currency']}",
    )
    rows.append(r)
groups = defaultdict(list)
for r in rows:
    groups[r["batch_reference"]].append(r)
bank = []
for n, (batch, items) in enumerate(sorted(groups.items()), 1):
    first = items[0]
    lag = 1 + sum(batch.encode()) % 2
    bank.append(
        dict(
            settlement_id=f"SET-{n:06}",
            batch_reference=batch,
            activity_date=first["transaction_date"],
            settlement_date=first["transaction_date"] + timedelta(days=lag),
            merchant_id=first["merchant_id"],
            currency=first["currency"],
            transaction_count=len(items),
            settlement_amount=total(items, "net_amount"),
        )
    )
issues = []


def issue(kind, ref, batch, currency, impact, explanation):
    issues.append(
        dict(
            case_id=f"CASE-{len(issues)+1:04}",
            gap_type=kind,
            record_reference=ref,
            batch_reference=batch,
            currency=currency,
            october_gap_impact=impact,
            explanation=explanation,
        )
    )


# Plant bank batch-rounding in eight batches where accumulated subcent fees differ.
planted = []
for b in bank:
    items = groups[b["batch_reference"]]
    raw = money(sum((t["gross_amount"] - t["unrounded_fee"] for t in items), D(0)))
    delta = b["settlement_amount"] - raw
    if (
        len(planted) < 8
        and b["activity_date"].month == 10
        and len(items) >= 3
        and delta
    ):
        b["settlement_amount"] = raw
        planted.append(b["batch_reference"])
        issue(
            "rounding",
            b["settlement_id"],
            b["batch_reference"],
            b["currency"],
            delta,
            "Bank rounds the sum of unrounded net amounts; platform sums individually rounded net amounts. Difference is visible only in the batch total.",
        )
for b in bank:
    if b["activity_date"].month == 10 and b["settlement_date"].month == 11:
        issue(
            "next_month_settlement",
            b["settlement_id"],
            b["batch_reference"],
            b["currency"],
            b["settlement_amount"],
            "October activity settles in November within the agreed 1-2 calendar days.",
        )
    if b["activity_date"].month == 9 and b["settlement_date"].month == 10:
        issue(
            "prior_month_inflow",
            b["settlement_id"],
            b["batch_reference"],
            b["currency"],
            -b["settlement_amount"],
            "September activity arrives in October; boundary context, not an additional planted error.",
        )
for r in rows:
    if r["original_transaction_id"].startswith("EXT-MISSING"):
        issue(
            "orphan_refund",
            r["transaction_id"],
            r["batch_reference"],
            r["currency"],
            D(0),
            "Original payment is absent from the entire supplied history. Refund is included in bank cash; this integrity exception has no additional cash-gap impact.",
        )
platform = list(rows)
for r in R.sample(
    [
        t
        for t in rows
        if t["event_type"] == "payment"
        and t["transaction_date"].month == 10
        and t["batch_reference"] not in planted
    ],
    6,
):
    platform.append(dict(r))
    issue(
        "duplicate_platform",
        r["transaction_id"],
        r["batch_reference"],
        r["currency"],
        r["net_amount"],
        "Exact repeated platform transaction ID and content; one extra imported row. Bank contains the economic event once.",
    )
statement = list(bank)
for b in R.sample(
    [
        b
        for b in bank
        if b["activity_date"].month == 10
        and b["settlement_date"].month == 10
        and b["batch_reference"] not in planted
    ],
    6,
):
    statement.append(dict(b))
    issue(
        "duplicate_bank",
        b["settlement_id"],
        b["batch_reference"],
        b["currency"],
        -b["settlement_amount"],
        "Exact repeated bank settlement ID and content; one extra statement row.",
    )
platform.sort(key=lambda r: (r["transaction_date"], r["transaction_id"]))
statement.sort(key=lambda r: (r["settlement_date"], r["settlement_id"]))
summary = []
for cur in ["INR", "USD", "EUR"]:
    p = total(
        [
            r
            for r in platform
            if r["currency"] == cur and r["transaction_date"].month == 10
        ],
        "net_amount",
    )
    b = total(
        [
            r
            for r in statement
            if r["currency"] == cur and r["settlement_date"].month == 10
        ],
        "settlement_amount",
    )
    explained = total([r for r in issues if r["currency"] == cur], "october_gap_impact")
    assert p - b == explained, (cur, p - b, explained)
    summary.append(
        dict(
            currency=cur,
            october_platform_net=p,
            october_bank_cash=b,
            raw_gap=p - b,
            explained_gap=explained,
            unexplained_gap=p - b - explained,
        )
    )


def sheet(wb, name, data):
    ws = wb.create_sheet(name)
    fields = list(data[0])
    ws.append(fields)
    for row in data:
        ws.append([float(row[k]) if isinstance(row[k], D) else row[k] for k in fields])
    ws.freeze_panes = "A2"
    tab = Table(displayName=name.replace("_", "") + "Table", ref=ws.dimensions)
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(tab)
    for cell in ws[1]:
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = PatternFill("solid", fgColor="17365D")
    for idx, key in enumerate(fields, 1):
        from openpyxl.utils import get_column_letter

        ws.column_dimensions[get_column_letter(idx)].width = min(
            64, max(18, len(key) + 3)
        )
        for cells in ws.iter_rows(min_row=2, min_col=idx, max_col=idx):
            cell = cells[0]
            if isinstance(cell.value, date):
                cell.number_format = "yyyy-mm-dd"
            elif isinstance(cell.value, float):
                cell.number_format = (
                    "0.0%"
                    if key == "percentage_rate"
                    else (
                        "0.000000"
                        if key == "unrounded_fee"
                        else "#,##0.00;[Red](#,##0.00)"
                    )
                )
    return ws


wb = Workbook()
wb.remove(wb.active)
sheet(wb, "Platform_Transactions", platform)
sheet(wb, "Bank_Settlements", statement)
sheet(wb, "Merchants", [dict(merchant_id=i, merchant_name=n) for i, n in merchants])
sheet(
    wb,
    "Fee_Rules",
    [
        dict(payment_method=m, currency=c, percentage_rate=rate, fixed_fee=f)
        for m, (rate, fs) in fees.items()
        for c, f in fs.items()
    ],
)
sheet(
    wb,
    "Data_Dictionary",
    [
        dict(field=k, meaning=v)
        for k, v in {
            "transaction_id": "Immutable event ID; payment and refund events have distinct IDs.",
            "transaction_date": "Platform accounting date; date-only calendar-day convention.",
            "gross_amount": "Signed amount in the stated currency; negative for refunds.",
            "processing_fee": "Positive fee rounded half-up to two decimals; refund fees are zero.",
            "net_amount": "gross_amount minus processing_fee, rounded at transaction level.",
            "unrounded_fee": "Synthetic exact fee before rounding, retained for audit of batch precision.",
            "batch_reference": "Shared reference: activity date + merchant + currency.",
            "settlement_amount": "Signed bank cash after fees in the original currency.",
            "transaction_count": "Number of underlying unique events; excludes duplicate imported rows.",
            "original_transaction_id": "Refund payment reference; blank for payments.",
            "settlement_date": "Bank cash date, one or two calendar days after activity_date.",
        }.items()
    ],
)
wb.save(OUT / "Onelab_Reconciliation_Data.xlsx")
key = Workbook()
key.remove(key.active)
sheet(key, "Gap_Bridge", summary)
sheet(key, "Answer_Key", issues)
sheet(
    key,
    "Batch_Truth",
    [
        dict(
            batch_reference=b["batch_reference"],
            currency=b["currency"],
            activity_date=b["activity_date"],
            settlement_date=b["settlement_date"],
            unique_event_count=b["transaction_count"],
            platform_net=total(groups[b["batch_reference"]], "net_amount"),
            bank_cash=b["settlement_amount"],
            rounding_difference=total(groups[b["batch_reference"]], "net_amount")
            - b["settlement_amount"],
        )
        for b in bank
    ],
)
sheet(
    key,
    "Case_Counts",
    [
        dict(gap_type=k, count=v)
        for k, v in Counter(r["gap_type"] for r in issues).items()
    ],
)
key.save(OUT / "Onelab_Answer_Key.xlsx")
assert len(rows) == 1000 and len(platform) == 1006 and len(planted) == 8
assert all((b["settlement_date"] - b["activity_date"]).days in (1, 2) for b in bank)
assert len({r["transaction_id"] for r in platform}) == 1000
assert all(
    len({r["currency"] for r in items}) == 1
    and len({r["merchant_id"] for r in items}) == 1
    for items in groups.values()
)
assert (
    sum(
        r["event_type"] == "refund" and r["original_transaction_id"].startswith("EXT")
        for r in rows
    )
    == 8
)
for filename, expected in [
    (
        "Onelab_Reconciliation_Data.xlsx",
        {"Platform_Transactions": 1006, "Bank_Settlements": len(statement)},
    ),
    ("Onelab_Answer_Key.xlsx", {"Answer_Key": len(issues)}),
]:
    loaded = load_workbook(OUT / filename, read_only=True, data_only=True)
    for name, count in expected.items():
        assert loaded[name].max_row - 1 == count
    loaded.close()
report = {
    "seed": 92026,
    "unique_platform_events": 1000,
    "platform_rows": len(platform),
    "unique_bank_batches": len(bank),
    "bank_rows": len(statement),
    "anomaly_counts": dict(Counter(r["gap_type"] for r in issues)),
    "currency_gap_bridge": summary,
    "validation": "PASSED: row counts, workbook reload, batch currency/merchant isolation, settlement lags, orphan count, planted rounding count, and exact Decimal gap bridges.",
}
(OUT / "validation_report.json").write_text(
    json.dumps(report, indent=2, default=str), encoding="utf-8"
)
print(json.dumps(report, indent=2, default=str))
