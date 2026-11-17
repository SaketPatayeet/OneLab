"""HTTP endpoints for session-only workbook analysis and report downloads."""

from pathlib import Path
from decimal import Decimal
from datetime import date
from io import BytesIO
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from .schema import parse_workbook, InputError, error, MAX_BYTES
from .reconcile import analyze
from .report import export_report

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title="LedgerLens")


def serialize_result(value):
    """Send Decimal amounts as strings so JSON does not lose precision."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: serialize_result(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize_result(item) for item in value]
    return value


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/reference")
def reference():
    return FileResponse(
        ROOT / "data/Onelab_Reconciliation_Data.xlsx",
        filename="LedgerLens_Reference.xlsx",
    )


async def process_upload(file, month):
    """Read a bounded upload and always release its request-owned file handle."""
    try:
        if not (file.filename or "").lower().endswith(".xlsx"):
            raise InputError([error("Upload an .xlsx workbook.")])
        content = await file.read(MAX_BYTES + 1)
        return analyze(parse_workbook(content), month)
    finally:
        await file.close()


@app.exception_handler(InputError)
async def invalid(request, exception):
    return JSONResponse(
        status_code=422, content={"message": str(exception), "errors": exception.errors}
    )


@app.exception_handler(ValueError)
async def invalid_value(request, exception):
    return JSONResponse(
        status_code=422, content={"message": str(exception), "errors": []}
    )


@app.post("/api/analyze")
async def analyze_workbook(file: UploadFile = File(...), month: str = Form(...)):
    result = await process_upload(file, month)
    # Evidence is already attached to findings; omit the full source from JSON.
    result.pop("source")
    return JSONResponse(serialize_result(result))


@app.post("/api/report")
async def download_report(file: UploadFile = File(...), month: str = Form(...)):
    result = await process_upload(file, month)
    return StreamingResponse(
        BytesIO(export_report(result)),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="LedgerLens-{month}.xlsx"'
        },
    )


# Mount the UI last so static routes cannot shadow /api endpoints.
if (ROOT / "web-build").exists():
    app.mount(
        "/", StaticFiles(directory=ROOT / "web-build", html=True), name="frontend"
    )
