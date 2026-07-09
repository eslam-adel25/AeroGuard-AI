from fastapi import APIRouter, Depends, Query, HTTPException, Body
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import date, datetime
import io, csv

from ...database.session import get_db
from ...services.report_service import ReportService # استدعاء الخدمة
from ...core.auth_middleware import get_current_user
from ...repositories.report_repository import ReportRepository
from ...utils.report_generator import ReportGenerator

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/summary")
async def get_report_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    camera_id: str | None = Query(None),
    detection_type: str | None = Query(None),
    severity: str | None = Query(None),
    confidence_min: float | None = Query(None),
    confidence_max: float | None = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """رابط جلب ملخص التقارير (Section 4)"""
    owner_id = current_user.get("user_id")
    is_admin = current_user.get("role") == "Administrator"
    return ReportService.get_report_stats(
        db,
        start_date,
        end_date,
        camera_id=camera_id,
        owner_id=owner_id,
        is_admin=is_admin,
        detection_type=detection_type,
        severity=severity,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
    )

# ==========================================
# Dashboard Analytics API
# ==========================================

@router.get("/dashboard")
async def get_dashboard(
    start_date: date = Query(...),
    end_date: date = Query(...),
    camera_id: str | None = Query(None),
    detection_type: str | None = Query(None),
    severity: str | None = Query(None),
    confidence_min: float | None = Query(None),
    confidence_max: float | None = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    يرجع جميع بيانات صفحة Analytics في Request واحد.
    """

    return ReportService.get_report_stats(
        db=db,
        start_date=start_date,
        end_date=end_date,
        camera_id=camera_id,
        owner_id=current_user.get("user_id"),
        is_admin=(current_user.get("role") == "Administrator"),
        detection_type=detection_type,
        severity=severity,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
    )


@router.post("/generate")
async def generate_report(
    start_date: date = Body(...),
    end_date: date = Body(...),
    camera_id: str | None = Body(None),
    title: str | None = Body(None),
    report_type: str = Body("custom"),
    detection_type: str | None = Body(None),
    severity: str | None = Body(None),
    confidence_min: float | None = Body(None),
    confidence_max: float | None = Body(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    owner_id = current_user.get("user_id")
    is_admin = (current_user.get("role") == "Administrator")
    report = ReportService.generate_report(
        db=db,
        start_date=start_date,
        end_date=end_date,
        camera_id=camera_id,
        owner_id=owner_id,
        generated_by=owner_id,
        title=title,
        report_type=report_type,
        detection_type=detection_type,
        severity=severity,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
    )
    return {
        "report_id": str(report.report_id),
        "generated_at": report.generated_at,
        "title": report.title,
        "report_type": report.report_type,
    }


@router.get("/")
async def list_reports(
    limit: int = Query(50),
    offset: int = Query(0),
    query: str | None = Query(None),
    camera_id: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    owner_id = current_user.get("user_id")
    is_admin = (current_user.get("role") == "Administrator")
    repo = ReportRepository(db)
    result = repo.list_reports(
        owner_id=owner_id,
        is_admin=is_admin,
        limit=limit,
        offset=offset,
        query=query,
        camera_id=camera_id,
        start_date=start_date,
        end_date=end_date,
    )
    # serialize UUIDs/datetimes to strings
    items = []
    for r in result["items"]:
        items.append({
            "report_id": str(r.report_id),
            "title": r.title,
            "generated_at": r.generated_at,
            "generated_by": str(r.generated_by),
            "report_type": r.report_type,
            "filters": r.filters,
            "export_history": r.export_history or [],
        })
    return {"total": result["total"], "items": items}


@router.get("/{report_id}")
async def get_report(report_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    owner_id = current_user.get("user_id")
    is_admin = (current_user.get("role") == "Administrator")
    repo = ReportRepository(db)
    report = repo.get_report(report_id, owner_id=owner_id, is_admin=is_admin)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "report_id": str(report.report_id),
        "title": report.title,
        "generated_at": report.generated_at,
        "filters": report.filters,
        "summary": report.summary,
        "charts": report.charts,
        "details": report.details,
        "export_history": report.export_history or [],
    }


@router.get("/export/csv")
async def export_report_csv(report_id: str = Query(...), db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    owner_id = current_user.get("user_id")
    is_admin = (current_user.get("role") == "Administrator")
    repo = ReportRepository(db)
    report = repo.get_report(report_id, owner_id=owner_id, is_admin=is_admin)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or access denied")

    # Build CSV in-memory
    buf = io.StringIO()
    writer = csv.writer(buf)

    # Header / metadata
    writer.writerow(["Report ID", str(report.report_id)])
    writer.writerow(["Title", report.title or ""])
    writer.writerow(["Generated By", str(report.generated_by)])
    writer.writerow(["Generated At", str(report.generated_at)])
    writer.writerow([""])

    # Summary
    writer.writerow(["Summary"])
    summary = report.summary or {}
    for k, v in (summary.items() if isinstance(summary, dict) else []):
        writer.writerow([k, v])

    writer.writerow([""])

    # Details: if details is list of items, write header row
    details = report.details or []
    if isinstance(details, list) and len(details) > 0:
        # write header
        keys = sorted({key for row in details for key in (row.keys() if isinstance(row, dict) else [])})
        writer.writerow(keys)
        for row in details:
            writer.writerow([row.get(k, "") for k in keys])

    buf.seek(0)
    headers = {
        "Content-Disposition": f"attachment; filename=report-{report.report_id}.csv"
    }
    # record export
    repo.append_export_history(report,{"type":"csv","timestamp": datetime.utcnow().isoformat()})

    return StreamingResponse(buf, media_type="text/csv", headers=headers)


@router.get("/export/excel")
async def export_report_excel(report_id: str = Query(...), db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # For now, fallback to CSV if Excel libraries unavailable
    try:
        import openpyxl
    except Exception:
        raise HTTPException(status_code=501, detail="Excel export not supported on server (missing openpyxl)")

    owner_id = current_user.get("user_id")
    is_admin = (current_user.get("role") == "Administrator")
    repo = ReportRepository(db)
    report = repo.get_report(report_id, owner_id=owner_id, is_admin=is_admin)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or access denied")

    # Build a simple workbook
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    summary = report.summary or {}
    row = 1
    for k, v in (summary.items() if isinstance(summary, dict) else []):
        ws.cell(row=row, column=1, value=k)
        ws.cell(row=row, column=2, value=str(v))
        row += 1

    # Details sheet
    details = report.details or []
    if isinstance(details, list) and len(details) > 0:
        ws2 = wb.create_sheet("Details")
        keys = sorted({key for row in details for key in (row.keys() if isinstance(row, dict) else [])})
        for c, k in enumerate(keys, start=1):
            ws2.cell(row=1, column=c, value=k)
        for r_idx, rowdata in enumerate(details, start=2):
            for c_idx, k in enumerate(keys, start=1):
                ws2.cell(row=r_idx, column=c_idx, value=rowdata.get(k, ""))

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    headers = {"Content-Disposition": f"attachment; filename=report-{report.report_id}.xlsx"}
    repo.append_export_history(report,{"type":"excel","timestamp": datetime.utcnow().isoformat()})
    return StreamingResponse(out, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)


@router.get("/export/pdf")
async def export_report_pdf(report_id: str = Query(...), db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    owner_id = current_user.get("user_id")
    is_admin = (current_user.get("role") == "Administrator")
    repo = ReportRepository(db)
    report = repo.get_report(report_id, owner_id=owner_id, is_admin=is_admin)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or access denied")

    filename = f"report-{report.report_id}.pdf"
    path = ReportGenerator.generate_pdf({
        "metadata": {
            "report_id": str(report.report_id),
            "title": report.title,
            "generated_by": str(report.generated_by),
            "generated_at": str(report.generated_at),
            "filters": report.filters,
        },
        "summary": report.summary or {},
        "details": report.details or [],
    }, filename)

    with open(path, "rb") as f:
        data = f.read()

    repo.append_export_history(report,{"type":"pdf","timestamp": datetime.utcnow().isoformat()})

    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf", headers=headers)


@router.delete("/{report_id}")
async def delete_report(report_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    owner_id = current_user.get("user_id")
    is_admin = (current_user.get("role") == "Administrator")
    repo = ReportRepository(db)
    ok = repo.delete_report(report_id, owner_id=owner_id, is_admin=is_admin)
    if not ok:
        raise HTTPException(status_code=404, detail="Report not found or access denied")
    return JSONResponse({"ok": True})