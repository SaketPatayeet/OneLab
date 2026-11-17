"""Check every individual finding against the independent 100-event answer key."""

from collections import Counter
from decimal import Decimal
from io import BytesIO
import json
from pathlib import Path
import unittest

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from backend.app import app, serialize_result
from backend.reconcile import analyze
from backend.report import export_report
from backend.schema import parse_workbook

DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "test_100"


def read_records(sheet):
    rows = list(sheet.values)
    return [dict(zip(rows[0], row)) for row in rows[1:]]


def issue_signature(issue):
    """Compare category, identity, batch, currency and both monetary fields."""
    return (
        issue["type"],
        issue["reference"],
        issue["batch"],
        issue["currency"],
        Decimal(str(issue["impact"])),
        Decimal(str(issue["amount"])),
    )


class HundredEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = (DIRECTORY / "Reconciliation_100.xlsx").read_bytes()
        cls.data = parse_workbook(cls.content)
        cls.result = analyze(cls.data, "2026-10")
        workbook = load_workbook(DIRECTORY / "Answer_Key_100.xlsx", data_only=True)
        cls.expected_issues = read_records(workbook["Expected_Issues"])
        cls.expected_summary = read_records(workbook["Expected_Summary"])
        workbook.close()

    def test_exact_case_references_and_amounts(self):
        self.assertEqual(
            Counter(map(issue_signature, self.result["issues"])),
            Counter(map(issue_signature, self.expected_issues)),
        )

    def test_all_currency_totals(self):
        actual = {row["currency"]: row for row in self.result["summaries"]}
        for expected in self.expected_summary:
            for field in ("platform", "bank", "gap", "explained", "unexplained"):
                with self.subTest(currency=expected["currency"], field=field):
                    self.assertEqual(
                        actual[expected["currency"]][field],
                        Decimal(str(expected[field])),
                    )

    def test_size_and_required_categories(self):
        self.assertEqual(len(self.data["transactions"]), 102)
        self.assertEqual(
            len({row["transaction_id"] for row in self.data["transactions"]}), 100
        )
        self.assertEqual(len(self.data["settlements"]), 22)
        self.assertEqual(
            Counter(row["type"] for row in self.result["issues"]),
            {
                "rounding": 2,
                "orphan_refund": 2,
                "next_month_settlement": 2,
                "prior_month_inflow": 2,
                "duplicate_platform": 2,
                "duplicate_bank": 2,
            },
        )

    def test_http_analysis_and_export(self):
        client = TestClient(app)
        response = client.post(
            "/api/analyze",
            files={"file": ("test.xlsx", self.content)},
            data={"month": "2026-10"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Counter(map(issue_signature, response.json()["issues"])),
            Counter(map(issue_signature, self.expected_issues)),
        )
        response = client.post(
            "/api/report",
            files={"file": ("test.xlsx", self.content)},
            data={"month": "2026-10"},
        )
        self.assertEqual(response.status_code, 200)
        workbook = load_workbook(BytesIO(response.content), data_only=True)
        self.assertEqual(
            Counter(map(issue_signature, read_records(workbook["Issues"]))),
            Counter(map(issue_signature, self.expected_issues)),
        )
        workbook.close()
        (DIRECTORY / "Actual_Report_100.xlsx").write_bytes(response.content)

    def test_settlement_dates_and_refund_references(self):
        payments = {
            row["transaction_id"]: row
            for row in self.data["transactions"]
            if row["event_type"] == "payment"
        }
        refunds = [
            row for row in self.data["transactions"] if row["event_type"] == "refund"
        ]
        self.assertEqual(
            sum(row["original_transaction_id"] not in payments for row in refunds), 2
        )
        for settlement in self.data["settlements"]:
            self.assertIn(
                (settlement["settlement_date"] - settlement["activity_date"]).days,
                (1, 2),
            )

    @classmethod
    def tearDownClass(cls):
        # Save actual output separately from the independently generated answer key.
        actual = {key: value for key, value in cls.result.items() if key != "source"}
        (DIRECTORY / "actual_analysis_100.json").write_text(
            json.dumps(serialize_result(actual), indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    unittest.main()
