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
        pdf.ln(10)

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