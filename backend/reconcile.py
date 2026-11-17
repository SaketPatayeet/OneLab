"""Explain monthly cash gaps while retaining source evidence and decimal precision."""

from collections import defaultdict
from decimal import Decimal
import re
from .schema import rounded

ZERO = Decimal(0)


def analyze(data, month):
    """Return findings, currency bridges and coverage for a validated workbook.

    Positive impacts increase platform net minus bank cash. Integrity findings
    can have a nonzero affected amount while contributing zero to that gap.
    """
    if not re.fullmatch("\\d{4}-(0[1-9]|1[0-2])", month):
        raise ValueError("Choose a YYYY-MM month.")
    issues = []
    provisional_currencies = set()

    def in_selected_month(record_date):
        return record_date.isoformat().startswith(month)

    def add_issue(issue_type, reference, rows, impact=ZERO, detail="", amount=None):
        """Keep affected amounts distinct from signed contributions to the cash gap."""
        record = rows[0]
        issues.append(
            dict(
                id=f"I-{len(issues) + 1:04}",
                type=issue_type,
                reference=reference,
                batch=record.get("batch_reference", ""),
                merchant=record["merchant_id"],
                currency=record["currency"],
                date=record.get(
                    "transaction_date", record.get("settlement_date")
                ).isoformat(),
                impact=impact,
                amount=abs(impact) if amount is None else amount,
                detail=detail,
                evidence=rows,
            )
        )

    def deduplicate(rows, id_field, amount_field, date_field, gap_sign):
        """Exclude exact extra copies; preserve conflicting IDs as provisional.

        Source sheet/row metadata is excluded from content comparison. Platform
        duplicates increase the raw gap; bank duplicates decrease it.
        """
        groups = defaultdict(list)
        for record in rows:
            groups[record[id_field]].append(record)
        result = []
        for reference, records in groups.items():
            signature = lambda record: tuple(
                ((k, v) for k, v in record.items() if not k.startswith("_"))
            )
            if len(set((signature(record) for record in records))) > 1:
                provisional_currencies.update(
                    (record["currency"] for record in records)
                )
                add_issue(
                    "conflicting_id",
                    reference,
                    records,
                    detail="Same immutable ID has differing contents. Affected currency totals are provisional.",
                )
                result.extend(records)
                continue
            result.append(records[0])
            if len(records) > 1:
                add_issue(
                    "duplicate_platform" if gap_sign == 1 else "duplicate_bank",
                    reference,
                    records,
                    sum(
                        (
                            gap_sign * record[amount_field]
                            for record in records[1:]
                            if in_selected_month(record[date_field])
                        ),
                        ZERO,
                    ),
                    "Exact repeated rows; extra copies excluded from adjusted totals.",
                    abs(records[0][amount_field]) * (len(records) - 1),
                )
        return result

    transactions = deduplicate(
        data["transactions"], "transaction_id", "net_amount", "transaction_date", 1
    )
    settlements = deduplicate(
        data["settlements"], "settlement_id", "settlement_amount", "settlement_date", -1
    )
    # Search the entire upload, not only this month, for refund originals.
    payments = {
        record["transaction_id"]
        for record in transactions
        if record["event_type"] == "payment"
    }
    for transaction in transactions:
        if (
            in_selected_month(transaction["transaction_date"])
            and transaction["event_type"] == "refund"
            and (transaction["original_transaction_id"] not in payments)
        ):
            add_issue(
                "orphan_refund",
                transaction["transaction_id"],
                [transaction],
                detail="Original "
                + (transaction["original_transaction_id"] or "(blank)")
                + " is absent from all supplied payment history.",
                amount=abs(transaction["net_amount"]),
            )
    # Shared batch references link events to cash without matching on amounts.
    transactions_by_batch = defaultdict(list)
    settlements_by_batch = defaultdict(list)
    for transaction in transactions:
        transactions_by_batch[transaction["batch_reference"]].append(transaction)
    for settlement in settlements:
        settlements_by_batch[settlement["batch_reference"]].append(settlement)
    for batch in sorted(set(transactions_by_batch) | set(settlements_by_batch)):
        batch_transactions = transactions_by_batch[batch]
        batch_settlements = settlements_by_batch[batch]
        rows = batch_transactions + batch_settlements
        expected = sum(
            (
                transaction["net_amount"]
                for transaction in batch_transactions
                if in_selected_month(transaction["transaction_date"])
            ),
            ZERO,
        )
        actual = sum(
            (
                settlement["settlement_amount"]
                for settlement in batch_settlements
                if in_selected_month(settlement["settlement_date"])
            ),
            ZERO,
        )
        gap = expected - actual
        if len({(record["merchant_id"], record["currency"]) for record in rows}) > 1:
            provisional_currencies.update((record["currency"] for record in rows))
            add_issue(
                "ambiguous_batch",
                batch,
                rows,
                detail="Batch spans merchants or currencies; totals are provisional.",
            )
            continue
        if not batch_transactions:
            if any(
                (
                    in_selected_month(settlement["settlement_date"])
                    for settlement in batch_settlements
                )
            ):
                add_issue(
                    "unmatched_bank",
                    batch,
                    rows,
                    -actual,
                    "No platform batch in supplied history.",
                )
            continue
        if not batch_settlements:
            if any(
                (
                    in_selected_month(transaction["transaction_date"])
                    for transaction in batch_transactions
                )
            ):
                add_issue(
                    "missing_settlement",
                    batch,
                    rows,
                    expected,
                    "No bank settlement found in supplied coverage.",
                )
            continue
        dates = {transaction["transaction_date"] for transaction in batch_transactions}
        if len(dates) != 1:
            add_issue(
                "ambiguous_batch",
                batch,
                rows,
                gap,
                "Platform batch spans activity dates; cannot safely allocate.",
            )
            continue
        activity_date = batch_transactions[0]["transaction_date"]
        platform_batch_total = sum(
            (transaction["net_amount"] for transaction in batch_transactions), ZERO
        )
        bank_batch_total = sum(
            (settlement["settlement_amount"] for settlement in batch_settlements), ZERO
        )
        # Separate timing from amount differences to avoid counting money twice.
        if in_selected_month(activity_date):
            outside_month_settlements = [
                settlement
                for settlement in batch_settlements
                if not in_selected_month(settlement["settlement_date"])
            ]
            if outside_month_settlements:
                add_issue(
                    (
                        "next_month_settlement"
                        if all(
                            (
                                settlement["settlement_date"] > activity_date
                                for settlement in outside_month_settlements
                            )
                        )
                        else "outside_month_settlement"
                    ),
                    batch,
                    rows,
                    sum(
                        (
                            settlement["settlement_amount"]
                            for settlement in outside_month_settlements
                        ),
                        ZERO,
                    ),
                    "Confirmed bank settlement outside the selected accounting month.",
                )
            amount_difference = platform_batch_total - bank_batch_total
            if amount_difference:
                # A small residual alone is insufficient evidence of rounding.
                rounded_batch_net = rounded(
                    sum(
                        (
                            transaction["gross_amount"] - transaction["unrounded_fee"]
                            for transaction in batch_transactions
                        ),
                        ZERO,
                    )
                )
                add_issue(
                    (
                        "rounding"
                        if rounded_batch_net == bank_batch_total
                        else "amount_mismatch"
                    ),
                    batch,
                    rows,
                    amount_difference,
                    f"Platform sum: {platform_batch_total}; bank sum: {bank_batch_total}; rounded sum of unrounded nets: {rounded_batch_net}.",
                )
        elif any(
            (
                in_selected_month(settlement["settlement_date"])
                for settlement in batch_settlements
            )
        ):
            add_issue(
                "prior_month_inflow",
                batch,
                rows,
                -actual,
                "Activity outside the selected month arrives in current-month bank cash.",
            )
        for settlement in batch_settlements:
            lag = (settlement["settlement_date"] - activity_date).days
            if in_selected_month(activity_date) and lag not in (1, 2):
                add_issue(
                    "settlement_delay",
                    settlement["settlement_id"],
                    rows,
                    detail=f"Settlement lag is {lag} calendar days; expected 1 or 2.",
                    amount=abs(settlement["settlement_amount"]),
                )
            if settlement["transaction_count"] != len(
                batch_transactions
            ) and in_selected_month(activity_date):
                add_issue(
                    "count_mismatch",
                    settlement["settlement_id"],
                    rows,
                    detail=f"Bank event count {settlement['transaction_count']}; supplied unique batch events {len(batch_transactions)}.",
                )
    # Bridge original imported totals, including the exact duplicate adjustments.
    summaries = []
    for currency in sorted(
        {record["currency"] for record in data["transactions"] + data["settlements"]}
    ):

        def sums(records, field, date_field):
            return sum(
                (
                    record[field]
                    for record in records
                    if record["currency"] == currency
                    and in_selected_month(record[date_field])
                ),
                ZERO,
            )

        platform_total = sums(data["transactions"], "net_amount", "transaction_date")
        bank_total = sums(data["settlements"], "settlement_amount", "settlement_date")
        adjusted_platform_total = sums(transactions, "net_amount", "transaction_date")
        adjusted_bank_total = sums(settlements, "settlement_amount", "settlement_date")
        explained = sum(
            (issue["impact"] for issue in issues if issue["currency"] == currency), ZERO
        )
        bridge = defaultdict(lambda: ZERO)
        for issue in issues:
            if issue["currency"] == currency:
                bridge[issue["type"]] += issue["impact"]
        summaries.append(
            dict(
                currency=currency,
                platform=platform_total,
                bank=bank_total,
                gap=platform_total - bank_total,
                platform_duplicate_adjustment=adjusted_platform_total - platform_total,
                bank_duplicate_adjustment=adjusted_bank_total - bank_total,
                adjusted_platform=adjusted_platform_total,
                adjusted_bank=adjusted_bank_total,
                adjusted_gap=adjusted_platform_total - adjusted_bank_total,
                explained=explained,
                unexplained=platform_total - bank_total - explained,
                provisional=currency in provisional_currencies,
                bridge=dict(bridge),
            )
        )
    coverage = {
        key: dict(
            start=min((record[date_field] for record in records), default=None),
            end=max((record[date_field] for record in records), default=None),
        )
        for key, records, date_field in [
            ("platform", transactions, "transaction_date"),
            ("bank", settlements, "settlement_date"),
        ]
    }
    return dict(
        month=month,
        issues=issues,
        summaries=summaries,
        coverage=coverage,
        counts=dict(
            platform_rows=len(data["transactions"]),
            bank_rows=len(data["settlements"]),
            issues=len(issues),
        ),
        limitations=[
            "Findings describe supplied records only. Missing originals or settlements may exist outside this upload.",
            "Currencies are not combined. Amounts follow the documented fee and rounding conventions.",
        ],
        source=data,
    )
