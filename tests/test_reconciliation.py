import unittest
from pathlib import Path
from io import BytesIO
from decimal import Decimal
from collections import Counter
from openpyxl import load_workbook
from fastapi.testclient import TestClient
from backend.schema import parse_workbook, InputError
from backend.reconcile import analyze
from backend.app import app
from backend.report import export_report

ROOT = Path(__file__).resolve().parents[1]
CONTENT = (ROOT / "data/Onelab_Reconciliation_Data.xlsx").read_bytes()


def modified(fn):
    w = load_workbook(BytesIO(CONTENT))
    fn(w)
    b = BytesIO()
    w.save(b)
    return b.getvalue()


class ReconciliationTests(unittest.TestCase):
    def test_answer_key(self):
        r = analyze(parse_workbook(CONTENT), "2026-10")
        k = load_workbook(ROOT / "data/Onelab_Answer_Key.xlsx", data_only=True)
        expected = {
            row[0]: Decimal(str(row[3])) for row in list(k["Gap_Bridge"].values)[1:]
        }
        self.assertEqual({s["currency"]: s["gap"] for s in r["summaries"]}, expected)
        self.assertTrue(all(s["unexplained"] == 0 for s in r["summaries"]))
        self.assertEqual(
            Counter(i["type"] for i in r["issues"]),
            dict(
                rounding=8,
                next_month_settlement=19,
                prior_month_inflow=17,
                orphan_refund=8,
                duplicate_platform=6,
                duplicate_bank=6,
            ),
        )

    def test_formula_rejected(self):
        with self.assertRaises(InputError):
            parse_workbook(
                modified(
                    lambda w: setattr(w["Platform_Transactions"]["H2"], "value", "=1+1")
                )
            )

    def test_missing_column(self):
        with self.assertRaises(InputError):
            parse_workbook(
                modified(
                    lambda w: setattr(
                        w["Platform_Transactions"]["A1"], "value", "wrong"
                    )
                )
            )

    def test_conflict(self):
        d = parse_workbook(CONTENT)
        x = dict(d["transactions"][0])
        x["net_amount"] += 1
        d["transactions"].append(x)
        r = analyze(d, "2026-10")
        self.assertTrue(any(i["type"] == "conflicting_id" for i in r["issues"]))
        self.assertTrue(any(s["provisional"] for s in r["summaries"]))

    def test_missing_settlement(self):
        d = parse_workbook(CONTENT)
        batch = next(
            t["batch_reference"]
            for t in d["transactions"]
            if t["transaction_date"].isoformat().startswith("2026-10")
        )
        d["settlements"] = [
            b for b in d["settlements"] if b["batch_reference"] != batch
        ]
        self.assertTrue(
            any(
                i["type"] == "missing_settlement"
                for i in analyze(d, "2026-10")["issues"]
            )
        )

    def test_changed_ids_not_hardcoded(self):
        d = parse_workbook(CONTENT)
        for t in d["transactions"]:
            t["transaction_id"] = "NEW-" + t["transaction_id"]
            t["original_transaction_id"] = (
                "NEW-" + t["original_transaction_id"]
                if t["original_transaction_id"]
                else ""
            )
        r = analyze(d, "2026-10")
        self.assertEqual(sum(i["type"] == "orphan_refund" for i in r["issues"]), 8)

    def test_report_and_api(self):
        c = TestClient(app)
        res = c.post(
            "/api/analyze",
            files={"file": ("input.xlsx", CONTENT)},
            data={"month": "2026-10"},
        )
        self.assertEqual(res.status_code, 200)
        result = res.json()
        self.assertEqual(result["counts"]["issues"], 64)
        out = c.post(
            "/api/report",
            files={"file": ("input.xlsx", CONTENT)},
            data={"month": "2026-10"},
        )
        self.assertEqual(out.status_code, 200)
        w = load_workbook(BytesIO(out.content), data_only=True)
        self.assertEqual(w["Issues"].max_row - 1, 64)
        self.assertEqual(
            c.post(
                "/api/analyze",
                files={"file": ("bad.xlsx", b"bad")},
                data={"month": "2026-10"},
            ).status_code,
            422,
        )

    def test_clean_and_unexplained(self):
        d = parse_workbook(CONTENT)
        t = next(
            t
            for t in d["transactions"]
            if t["transaction_date"].isoformat().startswith("2026-10")
        )
        b = dict(
            next(
                b
                for b in d["settlements"]
                if b["batch_reference"] == t["batch_reference"]
            )
        )
        b["settlement_amount"] = t["net_amount"]
        b["transaction_count"] = 1
        clean = {"transactions": [t], "settlements": [b]}
        r = analyze(clean, "2026-10")
        self.assertEqual(r["issues"], [])
        b["settlement_amount"] -= Decimal("1.23")
        r = analyze(clean, "2026-10")
        self.assertTrue(any(i["type"] == "amount_mismatch" for i in r["issues"]))
        self.assertFalse(any(i["type"] == "rounding" for i in r["issues"]))

    def test_export_text_is_not_formula(self):
        r = analyze(parse_workbook(CONTENT), "2026-10")
        r["issues"][0]["detail"] = '=HYPERLINK("https://example.com")'
        w = load_workbook(BytesIO(export_report(r)), data_only=False)
        header = [c.value for c in w["Issues"][1]]
        cell = w["Issues"].cell(2, header.index("detail") + 1)
        self.assertEqual(cell.data_type, "s")

    def test_invalid_month(self):
        with self.assertRaises(ValueError):
            analyze(parse_workbook(CONTENT), "2026-13")

    def test_orphan_cash_not_double_counted(self):
        r = analyze(parse_workbook(CONTENT), "2026-10")
        self.assertTrue(
            all(
                i["impact"] == 0 and i["amount"] > 0
                for i in r["issues"]
                if i["type"] == "orphan_refund"
            )
        )


if __name__ == "__main__":
    unittest.main()
