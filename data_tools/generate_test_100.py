"""Generate a second, independently specified 100-event reconciliation fixture.

The answer key is assembled from planted cases before running the application.
Nothing in this generator imports the reconciliation engine.
"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import random

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

OUTPUT = Path(__file__).resolve().parents[1] / "data" / "test_100"
ZERO = Decimal("0")
CENT = Decimal("0.01")


def round_money(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def save_workbook(path, sheets):
    """Write actual Excel dates and numeric amounts with readable headers."""
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, records in sheets.items():
        sheet = workbook.create_sheet(name)
        headers = list(records[0])
        sheet.append(headers)
        for record in records:
            sheet.append(
                [
                    (
                        float(record[field])
                        if isinstance(record[field], Decimal)
                        else record[field]
                    )
                    for field in headers
                ]
            )
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for column_index, header in enumerate(headers, 1):
            sheet.column_dimensions[get_column_letter(column_index)].width = max(
                19, len(header) + 3
            )
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="173D32")
        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                if isinstance(cell.value, date):
                    cell.number_format = "yyyy-mm-dd"
                elif isinstance(cell.value, float):
                    cell.number_format = (
                        "0.000000"
                        if headers[cell.column - 1] == "unrounded_fee"
                        else "#,##0.00"
                    )
    workbook.save(path)


def generate():
    """Create 100 unique events, adding duplicate import copies separately."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    random_source = random.Random(1002026)
    transactions, settlements, expected = [], [], []

    def add_case(kind, reference, batch, currency, impact, amount):
        expected.append(
            dict(
                type=kind,
                reference=reference,
                batch=batch,
                currency=currency,
                impact=impact,
                amount=amount,
            )
        )

    # Twenty independent daily merchant/currency batches, five events in each.
    for batch_index in range(20):
        activity = date(2026, 10, 2) + timedelta(days=batch_index)
        if batch_index == 0:
            activity = date(2026, 9, 30)
        elif batch_index == 1:
            activity = date(2026, 9, 29)
        elif batch_index == 18:
            activity = date(2026, 10, 30)
        elif batch_index == 19:
            activity = date(2026, 10, 31)
        currency = ["INR", "USD", "EUR"][batch_index % 3]
        merchant = f"CHECK-M{batch_index % 5 + 1:02}"
        batch = f"CHECK-{activity:%Y%m%d}-{merchant}-{currency}"
        batch_events = []
        rounding_case = batch_index in (3, 4)
        for position in range(5):
            gross = Decimal(random_source.randint(1000, 20000)) / 100
            exact_fee = Decimal(".004") if rounding_case else Decimal(".30")
            event = dict(
                transaction_id=f"CHECK-T{len(transactions) + 1:04}",
                transaction_date=activity,
                merchant_id=merchant,
                currency=currency,
                payment_method="card" if position % 2 == 0 else "bank_transfer",
                event_type="payment",
                original_transaction_id="",
                gross_amount=gross,
                processing_fee=round_money(exact_fee),
                net_amount=gross - round_money(exact_fee),
                unrounded_fee=exact_fee,
                batch_reference=batch,
            )
            # Two genuine refunds and two orphan refunds, all settled normally.
            if batch_index in (15, 16) and position in (0, 1):
                original = next(
                    record
                    for record in transactions
                    if record["currency"] == currency
                    and record["merchant_id"] == merchant
                    and record["event_type"] == "payment"
                )
                event.update(
                    event_type="refund",
                    original_transaction_id=(
                        original["transaction_id"]
                        if position == 0
                        else f"ABSENT-{batch_index}"
                    ),
                    gross_amount=-original["gross_amount"],
                    processing_fee=ZERO,
                    net_amount=-original["gross_amount"],
                    unrounded_fee=ZERO,
                )
                if position == 1:
                    add_case(
                        "orphan_refund",
                        event["transaction_id"],
                        batch,
                        currency,
                        ZERO,
                        abs(event["net_amount"]),
                    )
            transactions.append(event)
            batch_events.append(event)
        platform_net = sum((event["net_amount"] for event in batch_events), ZERO)
        bank_cash = (
            round_money(
                sum(
                    (
                        event["gross_amount"] - event["unrounded_fee"]
                        for event in batch_events
                    ),
                    ZERO,
                )
            )
            if rounding_case
            else platform_net
        )
        # Boundary batches deliberately settle across month end within 1-2 days.
        lag = 2 if batch_index in (0, 1, 18, 19) else 1 + batch_index % 2
        settlement_date = activity + timedelta(days=lag)
        settlement = dict(
            settlement_id=f"CHECK-S{batch_index + 1:03}",
            batch_reference=batch,
            activity_date=activity,
            settlement_date=settlement_date,
            merchant_id=merchant,
            currency=currency,
            transaction_count=5,
            settlement_amount=bank_cash,
        )
        settlements.append(settlement)
        if rounding_case:
            difference = platform_net - bank_cash
            assert difference == Decimal(".02")
            add_case("rounding", batch, batch, currency, difference, abs(difference))
        if activity.month == 10 and settlement_date.month == 11:
            add_case(
                "next_month_settlement",
                batch,
                batch,
                currency,
                bank_cash,
                abs(bank_cash),
            )
        if activity.month == 9 and settlement_date.month == 10:
            add_case(
                "prior_month_inflow", batch, batch, currency, -bank_cash, abs(bank_cash)
            )

    # Duplicate complete rows without changing economic events or settlement counts.
    for index in (30, 35):
        event = transactions[index]
        transactions.append(dict(event))
        add_case(
            "duplicate_platform",
            event["transaction_id"],
            event["batch_reference"],
            event["currency"],
            event["net_amount"],
            abs(event["net_amount"]),
        )
    for index in (8, 9):
        settlement = settlements[index]
        settlements.append(dict(settlement))
        add_case(
            "duplicate_bank",
            settlement["settlement_id"],
            settlement["batch_reference"],
            settlement["currency"],
            -settlement["settlement_amount"],
            abs(settlement["settlement_amount"]),
        )

    summaries = []
    for currency in ("INR", "USD", "EUR"):
        platform = sum(
            (
                event["net_amount"]
                for event in transactions
                if event["currency"] == currency
                and event["transaction_date"].month == 10
            ),
            ZERO,
        )
        bank = sum(
            (
                row["settlement_amount"]
                for row in settlements
                if row["currency"] == currency and row["settlement_date"].month == 10
            ),
            ZERO,
        )
        explained = sum(
            (case["impact"] for case in expected if case["currency"] == currency), ZERO
        )
        assert platform - bank == explained
        summaries.append(
            dict(
                currency=currency,
                platform=platform,
                bank=bank,
                gap=platform - bank,
                explained=explained,
                unexplained=ZERO,
            )
        )
    assert len({event["transaction_id"] for event in transactions}) == 100
    save_workbook(
        OUTPUT / "Reconciliation_100.xlsx",
        {
            "Platform_Transactions": transactions,
            "Bank_Settlements": settlements,
        },
    )
    save_workbook(
        OUTPUT / "Answer_Key_100.xlsx",
        {"Expected_Issues": expected, "Expected_Summary": summaries},
    )
    print(
        f"Created {len(transactions)} platform rows (100 unique events), {len(settlements)} bank rows (20 unique batches), {len(expected)} expected findings."
    )


if __name__ == "__main__":
    generate()
