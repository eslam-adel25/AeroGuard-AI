import re
from datetime import date, datetime
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
SEVERITY_COLORS = {
    "critical": (166, 36, 36),
    "high": (174, 91, 22),
    "medium": (139, 105, 17),
    "low": (49, 96, 74),
}
EVENT_PRESENTATION = {
    "ABANDONED BAG": (
        "ABANDONED BAG",
        "Abandoned bag",
        "An unattended bag was detected by the AI surveillance system.",
    ),
    "LOITERING": (
        "LOITERING",
        "Loitering",
        "Person detected remaining in the monitored area under a loitering condition.",
    ),
    "RESTRICTED AREA": (
        "RESTRICTED AREA",
        "Restricted area",
        "Activity was detected within a restricted area.",
    ),
}


class OperationalPDF(FPDF):
    def __init__(self, metadata):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.metadata = metadata or {}
        self.set_margins(16, BODY_TOP, 16)
        self.set_auto_page_break(False)
        self.set_title("AeroGuard AI Security Incident Report")
        self.set_author("AeroGuard AI")
        self.alias_nb_pages()

    @staticmethod
    def text(value):
        if value is None or value == "":
            return "Not available"
        return str(value).encode("latin-1", "replace").decode("latin-1")

    @staticmethod
    def format_timestamp(value):
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, date):
            return value.strftime("%d %b %Y")
        elif isinstance(value, str):
            raw_value = value.strip()
            try:
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_value):
                    return date.fromisoformat(raw_value).strftime("%d %b %Y")
                parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
            except ValueError:
                return "Not available"
        else:
            return "Not available"
        return parsed.strftime("%d %b %Y | %I:%M %p")

    @staticmethod
    def format_date(value):
        if isinstance(value, datetime):
            return value.strftime("%d %b %Y")
        if isinstance(value, date):
            return value.strftime("%d %b %Y")
        if isinstance(value, str):
            try:
                return date.fromisoformat(value[:10]).strftime("%d %b %Y")
            except ValueError:
                return "Not available"
        return "Not available"

    def wrapped_lines(self, value, width, font="Arial", style="", size=8):
        self.set_font(font, style, size)
        paragraphs = self.text(value).splitlines() or [""]
        lines = []
        for paragraph in paragraphs:
            words = paragraph.split()
            if not words:
                lines.append("")
                continue
            current_line = ""
            for word in words:
                if self.get_string_width(word) > width:
                    if current_line:
                        lines.append(current_line)
                        current_line = ""
                    part = ""
                    for character in word:
                        if part and self.get_string_width(part + character) > width:
                            lines.append(part)
                            part = character
                        else:
                            part += character
                    current_line = part
                    continue
                candidate = f"{current_line} {word}".strip()
                if current_line and self.get_string_width(candidate) > width:
                    lines.append(current_line)
                    current_line = word
                else:
                    current_line = candidate
            if current_line:
                lines.append(current_line)
        return lines or [""]

    def draw_lines(
        self,
        lines,
        x,
        y,
        width,
        line_height,
        font="Arial",
        style="",
        size=8,
        color=(7, 19, 33),
    ):
        self.set_font(font, style, size)
        self.set_text_color(*color)
        for index, line in enumerate(lines):
            self.set_xy(x, y + index * line_height)
            self.cell(width, line_height, line)
        return y + len(lines) * line_height

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
        self.set_font("Arial", "B", 9)
        self.set_text_color(181, 197, 211)
        self.cell(100, 5, "Security Incident Report")
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
        self.cell(95, 5, "AeroGuard AI  |  Security Incident Report")
        self.cell(83, 5, f"Page {self.page_no()} of {{nb}}", align="R")

    def ensure_body_space(self, required_height):
        if self.get_y() + required_height <= BODY_BOTTOM:
            return False
        self.add_page()
        self.set_y(BODY_TOP)
        return True

    def section_title(self, title):
        self.set_text_color(7, 19, 33)
        self.set_font("Arial", "B", 12)
        self.cell(0, 8, self.text(title), ln=True)
        self.ln(2)

    def metadata_block(self, metadata):
        filters = metadata.get("filters") or {}
        camera = metadata.get("camera") or {}
        start_y = self.get_y()
        start_date = self.format_date(filters.get("start_date"))
        end_date = self.format_date(filters.get("end_date"))
        camera_scope = (
            (camera.get("camera_name") or "Not available")
            if filters.get("camera_id")
            else "All Cameras"
        )
        entries = [
            ("REPORT PERIOD", f"{start_date} to {end_date}"),
            ("GENERATED AT", self.format_timestamp(metadata.get("generated_at"))),
            ("CAMERA SCOPE", camera_scope),
            ("REPORT ID", metadata.get("report_id")),
        ]
        self.section_title("Report Information")
        start_y = self.get_y()
        x_positions = [20, 106]
        widths = [82, 82]
        prepared_entries = []
        for index, (label, value) in enumerate(entries):
            value_font = "Courier" if label == "REPORT ID" else "Arial"
            value_size = 6 if label == "REPORT ID" else 7.5
            lines = self.wrapped_lines(value, widths[index % 2], font=value_font, size=value_size)
            prepared_entries.append((label, lines, value_font, value_size))
        row_heights = [
            max(12, max(len(prepared_entries[index][1]), len(prepared_entries[index + 1][1])) * 3.2 + 7)
            for index in range(0, len(prepared_entries), 2)
        ]
        box_height = 3 + sum(row_heights) + 3
        self.set_fill_color(239, 244, 247)
        self.set_draw_color(213, 224, 231)
        self.rect(16, start_y, 178, box_height, "DF")
        row_y = start_y + 3
        for row_index, row_height in enumerate(row_heights):
            for column_index in range(2):
                index = row_index * 2 + column_index
                label, lines, value_font, value_size = prepared_entries[index]
                x = x_positions[column_index]
                width = widths[column_index]
                self.set_xy(x, row_y)
                self.set_font("Arial", "B", 6.5)
                self.set_text_color(99, 116, 132)
                self.cell(width, 3, label)
                self.draw_lines(
                    lines,
                    x,
                    row_y + 4,
                    width,
                    3.2,
                    font=value_font,
                    size=value_size,
                )
            row_y += row_height
        self.set_y(start_y + box_height + 3)

    def security_overview(self, summary):
        definitions = [
            ("Total Detections", ("total_detections", "total")),
            ("Critical Alerts", ("critical_alerts",), "critical"),
            ("High Alerts", ("high_alerts",), "high"),
            ("Medium Alerts", ("medium_alerts",), "medium"),
            ("Low Alerts", ("low_alerts",), "low"),
            ("Suspicious Objects", ("suspicious_objects",)),
            ("Fire / Smoke", ("fire",)),
            ("Persons", ("persons", "person_detections")),
            ("Vehicles", ("vehicles", "vehicle_detections")),
            ("Average AI Confidence", ("average_confidence",), "percent"),
            ("Active Cameras", ("active_cameras",)),
        ]
        metrics = []
        for definition in definitions:
            label, keys = definition[:2]
            style = definition[2] if len(definition) == 3 else None
            key = next(
                (candidate for candidate in keys if candidate in summary and summary[candidate] is not None),
                None,
            )
            if key is None:
                continue
            value = summary[key]
            if style == "percent":
                value = f"{float(value):.1f}%"
            elif isinstance(value, int):
                value = f"{value:,}"
            value_color = SEVERITY_COLORS.get(style, (7, 19, 33))
            metrics.append((label, value, value_color))

        self.section_title("Security Overview")
        if not metrics:
            self.set_font("Arial", "", 8)
            self.set_text_color(99, 116, 132)
            self.cell(178, 6, "No report statistics are available.", ln=True)
            return

        columns = 4
        gap_x = 2
        tile_width = (178 - gap_x * (columns - 1)) / columns
        gap_y = 2
        for row_start in range(0, len(metrics), columns):
            row_metrics = metrics[row_start:row_start + columns]
            prepared = []
            for label, value, value_color in row_metrics:
                label_lines = self.wrapped_lines(label.upper(), tile_width - 4, style="B", size=5.6)
                value_lines = self.wrapped_lines(value, tile_width - 4, style="B", size=9)
                prepared.append((label_lines, value_lines, value_color))
            row_height = max(
                15,
                max(len(labels) for labels, _, _ in prepared) * 2.6
                + max(len(values) for _, values, _ in prepared) * 4.2
                + 6,
            )
            if self.get_y() + row_height > BODY_BOTTOM:
                self.add_page()
                self.set_y(BODY_TOP)
                self.section_title("Security Overview (continued)")
            row_y = self.get_y()
            for column_index, (label_lines, value_lines, value_color) in enumerate(prepared):
                x = 16 + column_index * (tile_width + gap_x)
                self.set_fill_color(239, 244, 247)
                self.set_draw_color(213, 224, 231)
                self.rect(x, row_y, tile_width, row_height, "DF")
                label_y = row_y + 2
                self.draw_lines(
                    label_lines,
                    x + 2,
                    label_y,
                    tile_width - 4,
                    2.6,
                    style="B",
                    size=5.6,
                    color=(99, 116, 132),
                )
                value_y = label_y + max(len(labels) for labels, _, _ in prepared) * 2.6 + 1
                self.draw_lines(
                    value_lines,
                    x + 2,
                    value_y,
                    tile_width - 4,
                    4.2,
                    style="B",
                    size=9,
                    color=value_color,
                )
            self.set_y(row_y + row_height + gap_y)

    def _event_layout(self, event):
        raw_type = str(event.get("detection_type") or "").strip()
        normalized_type = re.sub(r"\s+", " ", re.sub(r"[_-]+", " ", raw_type).upper())
        presentation = EVENT_PRESENTATION.get(normalized_type)
        if presentation:
            title, reason, description = presentation
        else:
            title = normalized_type or "Not available"
            reason = title.title() if title != "Not available" else title
            description = f"Alert type: {reason}." if reason != "Not available" else "Alert type not available."

        severity = self.text(event.get("severity"))
        confidence = event.get("confidence")
        try:
            confidence_label = f"{float(confidence) * 100:.1f}%" if confidence is not None else "Not available"
        except (TypeError, ValueError):
            confidence_label = "Not available"

        camera_name = event.get("camera_name") or event.get("camera_id")
        location = event.get("location")
        self.set_font("Arial", "B", 7)
        severity_width = min(max(self.get_string_width(severity) + 7, 23), 45)
        severity_lines = self.wrapped_lines(severity, severity_width - 5, style="B", size=6.5)
        title_lines = self.wrapped_lines(title, 170 - severity_width - 6, style="B", size=10.5)
        header_height = max(len(severity_lines) * 3.2 + 2, len(title_lines) * 4.8)
        time_lines = self.wrapped_lines(
            f"Alert Time: {self.format_timestamp(event.get('created_at'))}", 170, size=7.5
        )
        camera_lines = self.wrapped_lines(f"Camera: {camera_name}", 82, size=7.5)
        location_lines = self.wrapped_lines(f"Location: {location}", 82, size=7.5)
        reason_lines = self.wrapped_lines(f"Reason: {reason}", 170, size=7.5)
        description_lines = self.wrapped_lines(description, 170, size=7.2)
        confidence_lines = self.wrapped_lines(f"AI Confidence: {confidence_label}", 170, size=7.5)
        event_id_lines = self.wrapped_lines(event.get("event_id"), 82, font="Courier", size=6)
        camera_id_lines = self.wrapped_lines(event.get("camera_id"), 82, font="Courier", size=6)

        line_height = 3.6
        camera_row_height = max(len(camera_lines), len(location_lines)) * line_height
        reference_row_height = 2.7 + max(len(event_id_lines), len(camera_id_lines)) * 3.1
        content_height = (
            2.5 + header_height + 1.2
            + len(time_lines) * line_height + 1
            + camera_row_height + 1
            + len(reason_lines) * line_height + 1
            + len(description_lines) * 3.5 + 1
            + len(confidence_lines) * line_height + 2
            + reference_row_height + 2.5
        )
        return {
            "severity": severity,
            "severity_width": severity_width,
            "severity_lines": severity_lines,
            "header_height": header_height,
            "title_lines": title_lines,
            "time_lines": time_lines,
            "camera_lines": camera_lines,
            "location_lines": location_lines,
            "reason_lines": reason_lines,
            "description_lines": description_lines,
            "confidence_lines": confidence_lines,
            "event_id_lines": event_id_lines,
            "camera_id_lines": camera_id_lines,
            "height": content_height,
        }

    def _draw_event(self, layout):
        card_x = 16
        card_width = 178
        card_y = self.get_y()
        card_height = layout["height"]
        severity_color = SEVERITY_COLORS.get(layout["severity"].strip().lower(), (75, 96, 112))
        self.set_fill_color(248, 250, 251)
        self.set_draw_color(213, 224, 231)
        self.rect(card_x, card_y, card_width, card_height, "F")
        self.set_fill_color(*severity_color)
        self.rect(card_x, card_y, 1.2, card_height, "F")
        self.set_fill_color(*severity_color)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 6.5)
        self.set_xy(card_x + 3, card_y + 1.5)
        self.multi_cell(
            layout["severity_width"] - 4,
            3.2,
            "\n".join(layout["severity_lines"]),
            align="C",
            fill=True,
        )

        title_x = card_x + 3 + layout["severity_width"] + 3
        self.draw_lines(
            layout["title_lines"],
            title_x,
            card_y + 2,
            card_width - (title_x - card_x) - 3,
            4.8,
            style="B",
            size=10.5,
        )

        content_x = card_x + 4
        y = card_y + 2.5 + layout["header_height"] + 1.2
        self.draw_lines(layout["time_lines"], content_x, y, 170, 3.6, size=7.5)
        y += len(layout["time_lines"]) * 3.6 + 1
        self.draw_lines(layout["camera_lines"], content_x, y, 82, 3.6, size=7.5)
        self.draw_lines(layout["location_lines"], content_x + 88, y, 82, 3.6, size=7.5)
        y += max(len(layout["camera_lines"]), len(layout["location_lines"])) * 3.6 + 1
        self.draw_lines(layout["reason_lines"], content_x, y, 170, 3.6, size=7.5)
        y += len(layout["reason_lines"]) * 3.6 + 1
        self.draw_lines(
            layout["description_lines"],
            content_x,
            y,
            170,
            3.5,
            size=7.2,
            color=(75, 96, 112),
        )
        y += len(layout["description_lines"]) * 3.5 + 1
        self.draw_lines(layout["confidence_lines"], content_x, y, 170, 3.6, size=7.5)
        y += len(layout["confidence_lines"]) * 3.6 + 2

        self.set_draw_color(213, 224, 231)
        self.line(content_x, y, card_x + card_width - 4, y)
        reference_y = y + 1.5
        self.set_font("Arial", "B", 5.8)
        self.set_text_color(99, 116, 132)
        self.set_xy(content_x, reference_y)
        self.cell(82, 2.5, "AI EVENT ID")
        self.set_xy(content_x + 88, reference_y)
        self.cell(82, 2.5, "CAMERA ID")
        reference_y += 2.7
        self.draw_lines(
            layout["event_id_lines"], content_x, reference_y, 82, 3.1,
            font="Courier", size=6, color=(75, 96, 112),
        )
        self.draw_lines(
            layout["camera_id_lines"], content_x + 88, reference_y, 82, 3.1,
            font="Courier", size=6, color=(75, 96, 112),
        )
        self.set_draw_color(213, 224, 231)
        self.rect(card_x, card_y, card_width, card_height)
        self.set_y(card_y + card_height + 2)

    def ai_event_overview(self, events):
        first_layout = self._event_layout(events[0]) if events else None
        if first_layout and self.get_y() + 11 + first_layout["height"] > BODY_BOTTOM:
            self.add_page()
            self.set_y(BODY_TOP)
        self.section_title("Security Events")
        if not events:
            self.set_font("Arial", "", 9)
            self.set_text_color(99, 116, 132)
            self.cell(178, 7, "No AI security events are available for this report.", ln=True)
            return

        for index, event in enumerate(events):
            layout = first_layout if index == 0 else self._event_layout(event)
            if self.get_y() + layout["height"] + 2 > BODY_BOTTOM:
                self.add_page()
                self.set_y(BODY_TOP)
                self.section_title("Security Events (continued)")
            self._draw_event(layout)


class ReportGenerator:
    @staticmethod
    def _build_pdf(data, filename):
        metadata = data.get("metadata") or {}
        pdf = OperationalPDF(metadata)
        pdf.add_page()
        pdf.set_y(BODY_TOP + 4)
        pdf.metadata_block(metadata)
        pdf.security_overview(data.get("summary") or {})
        pdf.add_page()
        pdf.set_y(BODY_TOP)
        pdf.ai_event_overview(data.get("ai_events") or [])
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