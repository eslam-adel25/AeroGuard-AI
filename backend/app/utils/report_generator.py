from datetime import datetime
from pathlib import Path

import pandas as pd
from fpdf import FPDF


REPORT_ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = REPORT_ROOT / "backend" / "uploads" / "reports"
LOGO_PATH = REPORT_ROOT / "frontend" / "public" / "favicon-96x96.png"
PAGE_HEIGHT = 297
HEADER_HEIGHT = 27
BODY_TOP = 34
FOOTER_RESERVED_HEIGHT = 20
BODY_BOTTOM = PAGE_HEIGHT - FOOTER_RESERVED_HEIGHT
EVENT_BLOCK_HEIGHT = 30


class OperationalPDF(FPDF):
    def __init__(self, metadata):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.metadata = metadata or {}
        self.set_margins(16, BODY_TOP, 16)
        self.set_auto_page_break(False)
        self.set_title(str(self.metadata.get("title") or "AeroGuard AI Operational Report"))
        self.set_author("AeroGuard AI")
        self.alias_nb_pages()

    @staticmethod
    def text(value):
        if value is None or value == "":
            return "Not available"
        return str(value).encode("latin-1", "replace").decode("latin-1")

    @staticmethod
    def compact(value, length):
        value = OperationalPDF.text(value)
        if len(value) <= length:
            return value
        return f"{value[: max(1, length - 3)]}..."

    def header(self):
        self.set_fill_color(7, 19, 33)
        self.rect(0, 0, 210, HEADER_HEIGHT, "F")
        if LOGO_PATH.exists():
            self.image(str(LOGO_PATH), x=16, y=4, w=14, h=14)
        self.set_xy(34, 4)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 12)
        self.cell(80, 6, "AeroGuard AI")
        self.set_xy(34, 11)
        self.set_font("Arial", "", 8)
        self.set_text_color(181, 197, 211)
        self.cell(100, 5, "Operational Intelligence / Surveillance Report")
        self.set_xy(140, 6)
        self.set_font("Arial", "B", 8)
        self.set_text_color(255, 255, 255)
        self.cell(54, 5, "CONFIDENTIAL OPERATIONS", align="R")
        self.set_draw_color(49, 76, 101)
        self.line(16, HEADER_HEIGHT, 194, HEADER_HEIGHT)

    def footer(self):
        self.set_y(PAGE_HEIGHT - FOOTER_RESERVED_HEIGHT + 5)
        self.set_draw_color(210, 220, 228)
        self.line(16, self.get_y() - 2, 194, self.get_y() - 2)
        self.set_font("Arial", "", 7)
        self.set_text_color(99, 116, 132)
        report_id = self.text(self.metadata.get("report_id"))
        generated_at = self.text(self.metadata.get("generated_at"))
        self.cell(95, 5, f"AeroGuard AI  |  Report {report_id}")
        self.cell(83, 5, f"Generated {generated_at}  |  Page {self.page_no()}/{{nb}}", align="R")

    def ensure_body_space(self, required_height):
        if self.get_y() + required_height <= BODY_BOTTOM:
            return
        self.add_page()
        self.set_y(BODY_TOP)

    def start_event_page(self, continued=False):
        self.add_page()
        self.set_y(BODY_TOP)
        self.section_title("AI Event Records", "Continued" if continued else "Traceable operational events from the authoritative AIEvent dataset")
        self.table_header(self.event_columns)

    def section_title(self, title, subtitle=None):
        self.set_text_color(7, 19, 33)
        self.set_font("Arial", "B", 13)
        self.cell(0, 8, self.text(title), ln=True)
        if subtitle:
            self.set_font("Arial", "", 8)
            self.set_text_color(99, 116, 132)
            self.cell(0, 5, self.text(subtitle), ln=True)
        self.ln(3)

    def metadata_block(self, metadata):
        filters = metadata.get("filters") or {}
        camera = metadata.get("camera") or {}
        self.set_fill_color(239, 244, 247)
        self.set_draw_color(213, 224, 231)
        self.rect(16, self.get_y(), 178, 29, "DF")
        entries = [
            ("Report ID", metadata.get("report_id")),
            ("Generated At", metadata.get("generated_at")),
            ("Date Range", f"{filters.get('start_date', 'Not available')} to {filters.get('end_date', 'Not available')}"),
            (
                "Camera Scope",
                (
                    f"{camera.get('camera_name')} / {camera.get('location')}"
                    if camera.get("camera_name") and camera.get("location")
                    else camera.get("camera_name")
                    or filters.get("camera_id")
                    or "All Cameras"
                ),
            ),
        ]
        x_positions = [21, 108]
        start_y = self.get_y()
        for index, (label, value) in enumerate(entries):
            x = x_positions[index % 2]
            y = start_y + 5 + (index // 2) * 12
            self.set_xy(x, y)
            self.set_font("Arial", "B", 7)
            self.set_text_color(75, 96, 112)
            self.cell(37, 4, self.text(label).upper())
            self.set_xy(x, y + 4)
            self.set_font("Arial", "", 8)
            self.set_text_color(7, 19, 33)
            self.cell(77, 5, self.text(value))
        self.set_y(start_y + 34)

    def summary_cards(self, summary):
        labels = [
            ("Total Detections", "total_detections"),
            ("Critical Alerts", "critical_alerts"),
            ("High Alerts", "high_alerts"),
            ("Medium Alerts", "medium_alerts"),
            ("Low Alerts", "low_alerts"),
            ("Average Confidence", "average_confidence"),
            ("Active Cameras", "active_cameras"),
        ]
        available = [(label, key) for label, key in labels if key in summary]
        start_y = self.get_y()
        for index, (label, key) in enumerate(available):
            if index and index % 4 == 0:
                start_y += 21
            x = 16 + (index % 4) * 45
            self.set_fill_color(7, 19, 33)
            self.set_draw_color(7, 19, 33)
            self.rect(x, start_y, 42, 18, "DF")
            self.set_xy(x + 3, start_y + 3)
            self.set_font("Arial", "", 6)
            self.set_text_color(181, 197, 211)
            self.cell(36, 4, self.text(label).upper())
            value = summary[key]
            if key == "average_confidence":
                value = f"{value}%"
            self.set_xy(x + 3, start_y + 8)
            self.set_font("Arial", "B", 11)
            self.set_text_color(255, 255, 255)
            self.cell(36, 6, self.text(value))
        self.set_y(start_y + 22 if available else self.get_y())

    def table_header(self, columns):
        self.set_fill_color(22, 57, 82)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 7)
        for label, width in columns:
            self.cell(width, 8, self.text(label).upper(), 1, 0, "L", True)
        self.ln(8)

    def detection_summary(self, details):
        self.section_title("Detection Summary", "Aggregated records from the authoritative Detection dataset")
        columns = [("Detection Type", 105), ("Records", 35), ("Source", 38)]
        self.table_header(columns)
        self.set_font("Arial", "", 8)
        for item in details:
            self.set_text_color(7, 19, 33)
            self.cell(105, 7, self.text(item.get("type")), 1)
            self.cell(35, 7, self.text(item.get("count")), 1)
            self.cell(38, 7, "Detection records", 1)
            self.ln(7)
        if not details:
            self.set_text_color(99, 116, 132)
            self.cell(178, 8, "No detection records in the selected scope", 1)
            self.ln(8)

    def ai_event_table(self, events):
        if not events:
            return
        self.event_columns = [("Event ID", 39), ("Camera", 31), ("Type", 29), ("Severity", 20), ("Confidence", 20), ("Occurred At", 39)]
        self.start_event_page()
        self.set_font("Arial", "", 6.5)
        for event in events:
            self.ensure_body_space(EVENT_BLOCK_HEIGHT)
            if self.get_y() == BODY_TOP:
                self.section_title("AI Event Records", "Continued")
                self.table_header(self.event_columns)
                self.set_font("Arial", "", 6.5)
            severity = self.text(event.get("severity"))
            severity_color = {"Critical": (166, 36, 36), "High": (174, 91, 22), "Medium": (139, 105, 17), "Low": (49, 96, 74)}.get(severity, (75, 96, 112))
            self.set_fill_color(248, 250, 251)
            self.set_text_color(7, 19, 33)
            self.cell(39, 8, self.compact(event.get("event_id"), 22), "B", 0, "L", True)
            self.cell(31, 8, self.compact(event.get("camera_name") or event.get("camera_id"), 17), "B", 0, "L", True)
            self.cell(29, 8, self.compact(event.get("detection_type"), 15), "B", 0, "L", True)
            self.set_text_color(*severity_color)
            self.cell(20, 8, self.compact(severity, 11), "B", 0, "L", True)
            self.set_text_color(7, 19, 33)
            confidence = event.get("confidence")
            confidence = f"{confidence * 100:.1f}%" if confidence is not None else "Not available"
            self.cell(20, 8, self.compact(confidence, 11), "B", 0, "L", True)
            self.cell(39, 8, self.compact(event.get("created_at"), 23), "B", 0, "L", True)
            self.ln(8)
            self.set_font("Courier", "", 6.5)
            self.set_text_color(99, 116, 132)
            self.set_font("Courier", "", 6.5)
            self.multi_cell(178, 4, f"Event ID: {self.text(event.get('event_id'))}", "B")
            self.multi_cell(178, 4, f"Camera ID: {self.text(event.get('camera_id'))}", "B")
            self.multi_cell(178, 4, f"Location: {self.text(event.get('location'))}", "B")
            self.set_draw_color(218, 226, 232)
            self.line(16, self.get_y(), 194, self.get_y())
            self.ln(2)


class ReportGenerator:
    @staticmethod
    def _build_pdf(data, filename):
        pdf = OperationalPDF(data.get("metadata") or {})
        pdf.add_page()
        pdf.set_text_color(7, 19, 33)
        pdf.set_font("Arial", "B", 24)
        pdf.cell(0, 13, "Operational Intelligence Report", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(75, 96, 112)
        pdf.ln(7)
        pdf.metadata_block(data.get("metadata") or {})
        pdf.section_title("Executive Summary", "Metrics are reproduced directly from the persisted report payload")
        pdf.summary_cards(data.get("summary") or {})
        pdf.ln(4)
        pdf.detection_summary(data.get("details") or [])
        pdf.ai_event_table(data.get("ai_events") or [])
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = REPORT_DIR / filename
        pdf.output(str(path))
        return str(path)

    @staticmethod
    def generate_pdf(data, filename):
        return ReportGenerator._build_pdf(data, filename)

    @staticmethod
    def generate_pdf_with_ai(data, filename):
        return ReportGenerator._build_pdf(data, filename)

    @staticmethod
    def generate_excel(data, filename):
        df = pd.DataFrame(data["details"])
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = REPORT_DIR / filename
        df.to_excel(path, index=False)
        return str(path)
    
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