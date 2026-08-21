from fpdf import FPDF
import pandas as pd
from datetime import datetime
import os


class ReportGenerator:
    @staticmethod
    def generate_pdf(data, filename):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="AeroGuard AI - Operational Report", ln=True, align='C')
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 10, txt=f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
        metadata = data.get('metadata') or {}
        filters = metadata.get('filters') or {}
        pdf.set_text_color(0, 0, 0)
        pdf.cell(200, 8, txt=f"Date range: {filters.get('start_date', '')} to {filters.get('end_date', '')}", ln=True)
        pdf.cell(200, 8, txt=f"Camera: {filters.get('camera_id') or 'All Cameras'}", ln=True)
        pdf.ln(4)

        pdf.set_font("Arial", 'B', 11)
        pdf.cell(200, 8, txt="Analytics Summary", ln=True)
        pdf.set_font("Arial", size=9)
        summary = data.get('summary') or {}
        summary_keys = [
            'total_detections', 'critical_alerts', 'high_alerts',
            'medium_alerts', 'low_alerts', 'average_confidence',
            'active_cameras',
        ]
        for key in summary_keys:
            if key in summary:
                pdf.cell(70, 7, str(key), 1)
                pdf.cell(50, 7, str(summary[key]), 1)
                pdf.ln(7)
        pdf.ln(5)

        # Table Header
        pdf.set_fill_color(239, 68, 68) # AeroGuard Red
        pdf.set_text_color(255, 255, 255)
        pdf.cell(60, 10, "Detection Type", 1, 0, 'C', True)
        pdf.cell(60, 10, "Count", 1, 0, 'C', True)
        pdf.cell(70, 10, "Status", 1, 1, 'C', True)

        # Table Data
        pdf.set_text_color(0, 0, 0)
        for item in data['details']:
            pdf.cell(60, 10, str(item['type']), 1)
            pdf.cell(60, 10, str(item['count']), 1)
            pdf.cell(70, 10, "Verified", 1, 1)
        
        dirpath = os.path.join("uploads", "reports")
        os.makedirs(dirpath, exist_ok=True)
        path = os.path.join(dirpath, filename)
        pdf.output(path)
        return path

    @staticmethod
    def generate_pdf_with_ai(data, filename):
        """Extended PDF generator that includes AI events if present.

        Keeps backwards compatibility while supporting an 'ai_events' list
        where each item contains event_id, camera_id, detection_type, severity, confidence, created_at.
        """
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="AeroGuard AI - Operational Report", ln=True, align='C')
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 10, txt=f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
        metadata = data.get('metadata') or {}
        filters = metadata.get('filters') or {}
        pdf.set_text_color(0, 0, 0)
        pdf.cell(200, 8, txt=f"Date range: {filters.get('start_date', '')} to {filters.get('end_date', '')}", ln=True)
        pdf.cell(200, 8, txt=f"Camera: {filters.get('camera_id') or 'All Cameras'}", ln=True)
        pdf.ln(4)

        pdf.set_font("Arial", 'B', 11)
        pdf.cell(200, 8, txt="Analytics Summary", ln=True)
        pdf.set_font("Arial", size=9)
        summary = data.get('summary') or {}
        summary_keys = [
            'total_detections', 'critical_alerts', 'high_alerts',
            'medium_alerts', 'low_alerts', 'average_confidence',
            'active_cameras',
        ]
        for key in summary_keys:
            if key in summary:
                pdf.cell(70, 7, str(key), 1)
                pdf.cell(50, 7, str(summary[key]), 1)
                pdf.ln(7)
        pdf.ln(5)

        # Detection table (same as before)
        pdf.set_fill_color(239, 68, 68)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(60, 10, "Detection Type", 1, 0, 'C', True)
        pdf.cell(60, 10, "Count", 1, 0, 'C', True)
        pdf.cell(70, 10, "Status", 1, 1, 'C', True)

        pdf.set_text_color(0, 0, 0)
        for item in data.get('details', []):
            pdf.cell(60, 10, str(item.get('type', '')), 1)
            pdf.cell(60, 10, str(item.get('count', '')), 1)
            pdf.cell(70, 10, "Verified", 1, 1)

        # AI Events section
        ai_events = data.get('ai_events') or []
        if ai_events:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, txt="AI Events", ln=True)
            pdf.ln(4)
            pdf.set_font("Arial", size=9)
            # header
            pdf.set_fill_color(40, 40, 40)
            pdf.set_text_color(255, 255, 255)
            headers = ["Event ID", "Camera", "Type", "Severity", "Confidence", "Time"]
            widths = [50, 30, 40, 25, 20, 40]
            for w, h in zip(widths, headers):
                pdf.cell(w, 8, h, 1, 0, 'C', True)
            pdf.ln(8)
            pdf.set_text_color(0, 0, 0)
            for ev in ai_events:
                pdf.cell(widths[0], 8, str(ev.get('event_id', ''))[:32], 1)
                pdf.cell(widths[1], 8, str(ev.get('camera_id', '') )[:16], 1)
                pdf.cell(widths[2], 8, str(ev.get('detection_type', ''))[:24], 1)
                pdf.cell(widths[3], 8, str(ev.get('severity', ''))[:12], 1)
                pdf.cell(widths[4], 8, str(ev.get('confidence', ''))[:8], 1)
                pdf.cell(widths[5], 8, str(ev.get('created_at', ''))[:24], 1)
                pdf.ln(8)

        dirpath = os.path.join("uploads", "reports")
        os.makedirs(dirpath, exist_ok=True)
        path = os.path.join(dirpath, filename)
        pdf.output(path)
        return path

    @staticmethod
    def generate_excel(data, filename):
        df = pd.DataFrame(data['details'])
        dirpath = os.path.join("uploads", "reports")
        os.makedirs(dirpath, exist_ok=True)
        path = os.path.join(dirpath, filename)
        df.to_excel(path, index=False)
        return path
    
from sqlalchemy.orm import Session
from datetime import date

from ..repositories.report_repository import ReportRepository


class ReportService:
    @staticmethod
    def get_report_stats(
        db: Session,
        start_date: date,
        end_date: date,
        camera_id: str | None = None,
        owner_id: str | None = None,
        is_admin: bool = False,
    ):
        repo = ReportRepository(db)

        return repo.get_dashboard_data(
            start_date=start_date,
            end_date=end_date,
            camera_id=camera_id,
            owner_id=owner_id,
            is_admin=is_admin,
        )