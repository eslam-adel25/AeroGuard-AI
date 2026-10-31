from fastapi import APIRouter, Depends, Query, HTTPException, Body
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import date, datetime
import io, csv

from ...database.session import get_db
from ...services.report_service import ReportService # استدعاء الخدمة
from ...core.auth_middleware import (
    get_resource_user,
    require_tenant_isolation,
)
from ...core.customer_features import require_customer_feature
from ...core.tenant import PLATFORM_TENANT_SCOPE, tenant_owner_filter
from ...repositories.report_repository import ReportRepository
from ...repositories.ai_repository import AIRepository
from ...models.models import Camera
from ...ai.processor import ai_engine
from ...services.camera_status import apply_camera_runtime_statuses
import json
from ...utils.report_generator import ReportGenerator

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
    dependencies=[
        Depends(require_customer_feature("analytics")),
        Depends(require_tenant_isolation),
    ],
)

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
    current_user: dict = Depends(get_resource_user),
):
    """رابط جلب ملخص التقارير (Section 4)"""
    owner_id = current_user.get("user_id")
    return ReportService.get_report_stats(
        db,
        start_date,
        end_date,
        camera_id=camera_id,
        owner_id=owner_id,
        customer_profile_id=current_user.get("customer_profile_id"),
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
    current_user: dict = Depends(get_resource_user),
):
    """
    يرجع جميع بيانات صفحة Analytics في Request واحد.
    """

    response = ReportService.get_report_stats(
        db=db,
        start_date=start_date,
        end_date=end_date,
        camera_id=camera_id,
        owner_id=current_user.get("user_id"),
        customer_profile_id=current_user.get("customer_profile_id"),
        detection_type=detection_type,
        severity=severity,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
    )
    cameras = response.get("cameras", [])
    top_cameras = response.get("charts", {}).get("top_cameras", [])
    apply_camera_runtime_statuses(cameras + top_cameras, ai_engine)
    response.get("summary", {})["active_cameras"] = sum(
        1
        for camera in cameras
        if (camera.get("status") or "").strip().lower()
        in {"processing", "streaming", "running", "connected"}
    )
    return response


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
    current_user: dict = Depends(get_resource_user),
):
    owner_id = current_user.get("user_id")
    report = ReportService.generate_report(
        db=db,
        start_date=start_date,
        end_date=end_date,
        camera_id=camera_id,
        owner_id=owner_id,
        generated_by=owner_id,
        title=title,
        report_type=report_type,
        customer_profile_id=current_user.get("customer_profile_id"),
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
    current_user: dict = Depends(get_resource_user),
):
    owner_id = current_user.get("user_id")
    repo = ReportRepository(db)
    result = repo.list_reports(
        owner_id=owner_id,
        customer_profile_id=current_user.get("customer_profile_id"),
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
async def get_report(report_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user)):
    owner_id = current_user.get("user_id")
    repo = ReportRepository(db)
    report = repo.get_report(
        report_id,
        owner_id=owner_id,
        customer_profile_id=current_user.get("customer_profile_id"),
    )
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
async def export_report_csv(report_id: str = Query(...), db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user)):
    owner_id = current_user.get("user_id")
    repo = ReportRepository(db)
    report = repo.get_report(
        report_id,
        owner_id=owner_id,
        customer_profile_id=current_user.get("customer_profile_id"),
    )
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

    # AI Events section: include only events owned by the report customer.
    ai_repo = AIRepository(db)
    f = report.filters or {}
    try:
        sd = (
            datetime.fromisoformat(str(f["start_date"])).date()
            if f.get("start_date")
            else None
        )
        ed = (
            datetime.fromisoformat(str(f["end_date"])).date()
            if f.get("end_date")
            else None
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid report date filter") from exc

    _, ai_items = ai_repo.query_events_for_report(
        camera_id=f.get("camera_id"),
        customer_profile_id=current_user.get("customer_profile_id"),
        detection_type=f.get("detection_type"),
        severity=f.get("severity"),
        start_date=sd,
        end_date=ed,
        limit=10000,
        offset=0,
    )
    writer.writerow([""])
    writer.writerow(["AI Events"])
    writer.writerow(
        [
            "event_id",
            "camera_id",
            "detection_type",
            "severity",
            "confidence",
            "created_at",
            "screenshot_path",
            "metadata",
        ]
    )
    for ai in ai_items:
        writer.writerow([
            ai.get("event_id", ""),
            ai.get("camera_id", ""),
            ai.get("detection_type", ""),
            ai.get("severity", ""),
            ai.get("confidence", ""),
            ai.get("created_at", ""),
            ai.get("screenshot_path", ""),
            json.dumps(ai.get("metadata", {}), default=str),
        ])

    buf.seek(0)
    headers = {
        "Content-Disposition": f"attachment; filename=report-{report.report_id}.csv"
    }
    # record export
    repo.append_export_history(report,{"type":"csv","timestamp": datetime.utcnow().isoformat()})

    return StreamingResponse(buf, media_type="text/csv", headers=headers)


@router.get("/export/excel")
async def export_report_excel(report_id: str = Query(...), db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user)):
    # For now, fallback to CSV if Excel libraries unavailable
    try:
        import openpyxl
    except Exception:
        raise HTTPException(status_code=501, detail="Excel export not supported on server (missing openpyxl)")

    owner_id = current_user.get("user_id")
    repo = ReportRepository(db)
    report = repo.get_report(
        report_id,
        owner_id=owner_id,
        customer_profile_id=current_user.get("customer_profile_id"),
    )
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

    # AI Events sheet
    try:
        ai_repo = AIRepository(db)
        f = report.filters or {}
        sd = None
        ed = None
        try:
            if f.get("start_date"):
                sd = datetime.fromisoformat(str(f.get("start_date"))).date()
            if f.get("end_date"):
                ed = datetime.fromisoformat(str(f.get("end_date"))).date()
        except Exception:
            sd = None
            ed = None

        _, ai_items = ai_repo.query_events_for_report(
            camera_id=f.get("camera_id"),
            customer_profile_id=current_user.get("customer_profile_id"),
            detection_type=f.get("detection_type"),
            severity=f.get("severity"),
            start_date=sd,
            end_date=ed,
            limit=10000,
            offset=0,
        )

        if isinstance(ai_items, list) and len(ai_items) > 0:
            ws3 = wb.create_sheet("AI Events")
            headers = ["event_id", "camera_id", "detection_type", "severity", "confidence", "created_at", "screenshot_path", "metadata"]
            for c, h in enumerate(headers, start=1):
                ws3.cell(row=1, column=c, value=h)
            for r_idx, rowdata in enumerate(ai_items, start=2):
                ws3.cell(row=r_idx, column=1, value=rowdata.get("event_id"))
                ws3.cell(row=r_idx, column=2, value=rowdata.get("camera_id"))
                ws3.cell(row=r_idx, column=3, value=rowdata.get("detection_type"))
                ws3.cell(row=r_idx, column=4, value=rowdata.get("severity"))
                ws3.cell(row=r_idx, column=5, value=rowdata.get("confidence"))
                ws3.cell(row=r_idx, column=6, value=rowdata.get("created_at"))
                ws3.cell(row=r_idx, column=7, value=rowdata.get("screenshot_path"))
                ws3.cell(row=r_idx, column=8, value=str(rowdata.get("metadata", {})))
    except Exception:
        # allow exports to continue even if AI retrieval fails
        pass

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    headers = {"Content-Disposition": f"attachment; filename=report-{report.report_id}.xlsx"}
    repo.append_export_history(report,{"type":"excel","timestamp": datetime.utcnow().isoformat()})
    return StreamingResponse(out, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)


@router.get("/export/pdf")
async def export_report_pdf(report_id: str = Query(...), db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user)):
    owner_id = current_user.get("user_id")
    repo = ReportRepository(db)
    report = repo.get_report(
        report_id,
        owner_id=owner_id,
        customer_profile_id=current_user.get("customer_profile_id"),
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or access denied")

    report_time = report.generated_at or datetime.utcnow()
    filename_timestamp = report_time.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"AeroGuard_AI_Report_{filename_timestamp}.pdf"
    camera_scope = None
    report_filters = report.filters or {}
    if report_filters.get("camera_id"):
        camera_query = db.query(Camera).filter(
            Camera.camera_id == report_filters["camera_id"]
        )
        if current_user.get("customer_profile_id") != PLATFORM_TENANT_SCOPE:
            camera_query = camera_query.filter(
                tenant_owner_filter(
                    Camera,
                    db,
                    current_user.get("customer_profile_id"),
                    Camera.owner_id,
                )
            )
        camera = camera_query.first()
        if camera:
            camera_scope = {
                "camera_id": str(camera.camera_id),
                "camera_name": camera.camera_name,
                "location": camera.location,
            }
    path = ReportGenerator.generate_pdf({
        "metadata": {
            "report_id": str(report.report_id),
            "title": report.title,
            "generated_by": str(report.generated_by),
            "generated_at": str(report.generated_at),
            "filters": report.filters,
            "camera": camera_scope,
        },
        "summary": report.summary or {},
        "details": report.details or [],
    }, filename)

    # Attempt to attach AI events into PDF (non-fatal)
    try:
        f = report.filters or {}
        sd = None
        ed = None
        try:
            if f.get("start_date"):
                sd = datetime.fromisoformat(str(f.get("start_date"))).date()
            if f.get("end_date"):
                ed = datetime.fromisoformat(str(f.get("end_date"))).date()
        except Exception:
            sd = None
            ed = None

        ai_repo = AIRepository(db)
        _, ai_items = ai_repo.query_events_for_report(
            camera_id=f.get("camera_id"),
            customer_profile_id=current_user.get("customer_profile_id"),
            detection_type=f.get("detection_type"),
            severity=f.get("severity"),
            start_date=sd,
            end_date=ed,
            limit=1000,
            offset=0,
        )
        # regenerate PDF with AI events included
        path = ReportGenerator.generate_pdf_with_ai({
            "metadata": {
                "report_id": str(report.report_id),
                "title": report.title,
                "generated_by": str(report.generated_by),
                "generated_at": str(report.generated_at),
                "filters": report.filters,
                "camera": camera_scope,
            },
            "summary": report.summary or {},
            "details": report.details or [],
            "ai_events": ai_items,
        }, filename)
    except Exception:
        # keep original generated PDF if enrichment fails
        pass

    with open(path, "rb") as f:
        data = f.read()

    repo.append_export_history(report,{"type":"pdf","timestamp": datetime.utcnow().isoformat()})

    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf", headers=headers)


@router.delete("/{report_id}")
async def delete_report(report_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_resource_user)):
    owner_id = current_user.get("user_id")
    repo = ReportRepository(db)
    ok = repo.delete_report(
        report_id,
        owner_id=owner_id,
        customer_profile_id=current_user.get("customer_profile_id"),
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Report not found or access denied")
    return JSONResponse({"ok": True})