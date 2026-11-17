"""Fixed workbook contract and strict, evidence-preserving import."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from zipfile import ZipFile, BadZipFile
import re
from openpyxl import load_workbook

CENT = Decimal("0.01")
MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 20000
SCHEMA = {
    "Platform_Transactions": {
        "transaction_id": "text",
        "transaction_date": "date",
        "merchant_id": "text",
        "currency": "currency",
        "payment_method": "method",
        "event_type": "event",
        "original_transaction_id": "optional",
        "gross_amount": "money",
        "processing_fee": "money",
        "net_amount": "money",
        "unrounded_fee": "precise",
        "batch_reference": "text",
    },
    "Bank_Settlements": {
        "settlement_id": "text",
        "batch_reference": "text",
        "activity_date": "date",
        "settlement_date": "date",
        "merchant_id": "text",
        "currency": "currency",
        "transaction_count": "count",
        "settlement_amount": "money",
    },
}


class InputError(Exception):
    def __init__(self, errors):
        self.errors = errors[:100]
        super().__init__(
            "Invalid data. Please use the format in the reference Excel workbook."
        )


def error(message, sheet="", row=None, column=""):
    return dict(sheet=sheet, row=row, column=column, message=message)


def rounded(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def convert(value, kind):
    """Convert a cell according to the contract, rejecting ambiguous representations."""
    if kind == "optional" and value is None:
        return ""
    if value is None:
        raise ValueError("Required value is missing.")
    if kind == "date":
        if isinstance(value, datetime):
            if value.time() != datetime.min.time():
                raise ValueError("Use a date without a time of day.")
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            try:
                return date.fromisoformat(value)
            except ValueError:
                pass
        raise ValueError("Expected an Excel date or a valid YYYY-MM-DD date.")
    if kind in ("money", "precise", "count"):
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise ValueError("Expected a numeric Excel cell, not text or a formula.")
        try:
            n = Decimal(str(value))
        except InvalidOperation:
            raise ValueError("Invalid number.")
        if not n.is_finite() or abs(n) > Decimal("1000000000000"):
            raise ValueError("Number is outside the supported range.")
        if kind == "count":
            if n < 1 or n != n.to_integral_value():
                raise ValueError("Expected a positive whole event count.")
            return int(n)
        if kind == "money" and n != rounded(n):
            raise ValueError("Amounts must have at most two decimal places.")
        if kind == "precise" and n != n.quantize(Decimal(".000001")):
            raise ValueError("Unrounded fees support up to six decimal places.")
        return n
    if not isinstance(value, str) or not value.strip() or len(value) > 180:
        raise ValueError("Expected nonempty text of at most 180 characters.")
    if kind == "currency" and value not in ("INR", "USD", "EUR"):
        raise ValueError("Supported currencies: INR, USD and EUR (no FX conversion).")
    if kind == "event" and value not in ("payment", "refund"):
        raise ValueError("Use payment or refund.")
    if kind == "method" and value not in ("card", "bank_transfer", "upi"):
        raise ValueError("Use card, bank_transfer or upi.")
    return value


def parse_workbook(content):
    """Validate both sheets and collect row-level errors before analysis begins.

    The returned records retain Excel row numbers for evidence. Record-quality
    findings such as duplicate IDs are deliberately left to reconciliation.
    """
    if not content or len(content) > MAX_BYTES:
        raise InputError(
            [error("Upload a nonempty .xlsx workbook no larger than 8 MB.")]
        )
    try:
        # XLSX files are ZIP archives; bound expanded size before loading cells.
        with ZipFile(BytesIO(content)) as z:
            if (
                len(z.infolist()) > 2000
                or sum(i.file_size for i in z.infolist()) > 64 * 1024 * 1024
            ):
                raise InputError(
                    [
                        error(
                            "Workbook expands beyond supported limits; use a smaller workbook."
                        )
                    ]
                )
        wb = load_workbook(
            BytesIO(content), read_only=True, data_only=False, keep_links=False
        )
    except InputError:
        raise
    except Exception:
        raise InputError(
            [error("Cannot read this .xlsx workbook. Use the reference Excel format.")]
        )
    errors = []
    output = {}
    seen_rows = 0
    try:
        for name, schema in SCHEMA.items():
            output[name] = []
            if name not in wb.sheetnames:
                errors.append(error("Required sheet is missing.", name))
                continue
            ws = wb[name]
            if ws.max_column > 100 or ws.max_row > MAX_ROWS + 1:
                errors.append(error("Sheet exceeds 20,000 rows or 100 columns.", name))
                continue
            iterator = ws.iter_rows()
            header = next(iterator, ())
            names = [c.value for c in header]
            missing = [n for n in schema if n not in names]
            if missing:
                errors.append(error("Missing columns: " + ", ".join(missing), name, 1))
                continue
            if any(names.count(n) > 1 for n in schema):
                errors.append(error("Required column headers must be unique.", name, 1))
                continue
            indices = {n: names.index(n) for n in schema}
            for rownum, cells in enumerate(iterator, 2):
                if all(c.value is None for c in cells):
                    continue
                seen_rows += 1
                if seen_rows > MAX_ROWS:
                    raise InputError(
                        [
                            error(
                                "Use at most 20,000 data rows across both input sheets."
                            )
                        ]
                    )
                record = {}
                before = len(errors)
                for field, kind in schema.items():
                    cell = cells[indices[field]]
                    try:
                        if cell.data_type == "f":
                            raise ValueError(
                                "Formulas are not accepted; paste numeric values."
                            )
                        record[field] = convert(cell.value, kind)
                    except ValueError as exc:
                        errors.append(error(str(exc), name, rownum, field))
                if len(errors) == before and name == "Platform_Transactions":
                    checks = [
                        (
                            record["net_amount"]
                            == record["gross_amount"] - record["processing_fee"],
                            "net_amount",
                            "Must equal gross_amount minus processing_fee.",
                        ),
                        (
                            record["processing_fee"] >= 0
                            and record["unrounded_fee"] >= 0,
                            "processing_fee",
                            "Fees cannot be negative.",
                        ),
                        (
                            rounded(record["unrounded_fee"])
                            == record["processing_fee"],
                            "unrounded_fee",
                            "Must round half-up to processing_fee.",
                        ),
                        (
                            (
                                record["gross_amount"] > 0
                                if record["event_type"] == "payment"
                                else record["gross_amount"] < 0
                            ),
                            "gross_amount",
                            "Payments must be positive; refunds must be negative.",
                        ),
                        (
                            record["payment_method"] != "upi"
                            or record["currency"] == "INR",
                            "payment_method",
                            "UPI is supported for INR only.",
                        ),
                    ]
                    for valid, col, msg in checks:
                        if not valid:
                            errors.append(error(msg, name, rownum, col))
                if len(errors) == before:
                    record["_sheet"] = name
                    record["_row"] = rownum
                    output[name].append(record)
                if len(errors) >= 100:
                    raise InputError(errors)
        if not errors and not any(output.values()):
            errors.append(error("Workbook has no transaction or settlement records."))
        if errors:
            raise InputError(errors)
        return {
            "transactions": output["Platform_Transactions"],
            "settlements": output["Bank_Settlements"],
        }
    finally:
        wb.close()
