from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from ...database.session import get_db
from ...services.report_service import ReportService # استدعاء الخدمة
from ...core.auth_middleware import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/summary")
async def get_report_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    camera_id: str = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """رابط جلب ملخص التقارير (Section 4)"""
    return ReportService.get_report_stats(db, start_date, end_date, camera_id)

@router.get("/export/pdf")
async def export_pdf(start_date: date, end_date: date, db: Session = Depends(get_db)):
    # سيتم إضافة منطق ReportGenerator هنا لاحقاً
    return {"message": "PDF Export Logic Implementation"}


# ==========================================
# Dashboard Analytics API
# ==========================================

@router.get("/dashboard")
async def get_dashboard(
    start_date: date = Query(...),
    end_date: date = Query(...),
    camera_id: str | None = Query(None),
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
    )