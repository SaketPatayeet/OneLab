"""Build an Excel report from the same result structure used by the dashboard."""

from io import BytesIO
from decimal import Decimal
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter


def export_report(result):
    """Return workbook bytes without persisting source records or generated reports."""
    workbook = Workbook()
    workbook.remove(workbook.active)

    def add_sheet(name, rows):
        worksheet = workbook.create_sheet(name)
        if not rows:
            worksheet.append(["No records"])
            return
        fields = list(dict.fromkeys((field for record in rows for field in record)))
        worksheet.append(fields)
        for record in rows:
            values = []
            for field in fields:
                value = record.get(field)
                if isinstance(value, Decimal):
                    value = float(value)
                if isinstance(value, (dict, list)):
                    value = str(value)
                values.append(value)
            worksheet.append(values)
            for cell in worksheet[worksheet.max_row]:
                # Force user text to a string cell, even if it begins with '='.
                if isinstance(cell.value, str):
                    cell.data_type = "s"
                elif isinstance(cell.value, float):
                    cell.number_format = "#,##0.00"
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        for cell in worksheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="173D32")
        for column_index, field in enumerate(fields, 1):
            worksheet.column_dimensions[get_column_letter(column_index)].width = min(
                65, max(19, len(field) + 3)
            )

    add_sheet(
        "Summary",
        [
            {field: value for field, value in summary.items() if field != "bridge"}
            for summary in result["summaries"]
        ],
    )
    add_sheet(
        "Issues",
        [
            {field: value for field, value in issue.items() if field != "evidence"}
            for issue in result["issues"]
        ],
    )
    add_sheet(
        "Evidence",
        [
            dict(issue_id=issue["id"], **record)
            for issue in result["issues"]
            for record in issue["evidence"]
        ],
    )
    add_sheet(
        "Gap_Bridge",
        [
            dict(currency=summary["currency"], category=field, impact=value)
            for summary in result["summaries"]
            for field, value in summary["bridge"].items()
        ],
    )
    add_sheet("Platform_Source", result["source"]["transactions"])
    add_sheet("Bank_Source", result["source"]["settlements"])
    add_sheet(
        "Analysis_Context",
        [
            dict(item="Selected month", value=result["month"]),
            *[dict(item="Limitation", value=value) for value in result["limitations"]],
            *[
                dict(item=field + " coverage", value=str(value))
                for field, value in result["coverage"].items()
            ],
        ],
    )
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
