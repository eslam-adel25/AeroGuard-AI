# Reports System

The codebase provides a reporting subsystem used by the frontend to generate operational reports and exports.

Key components

- `ReportService` (`backend/app/services/report_service.py`) — aggregates detections and AI events to construct dashboard data and report payloads.
- `ReportRepository` (`backend/app/repositories/report_repository.py`) — persists `Report` records and exposes list/get/delete API.
- `ReportGenerator` (`backend/app/utils/report_generator.py`) — creates PDF/Excel files under `uploads/reports/`.

API endpoints (see `backend/app/api/v1/reports.py`)

- `GET /api/v1/reports/summary` — aggregate stats for a date range and optional filters.
- `GET /api/v1/reports/dashboard` — full analytics payload used by the frontend dashboard.
- `POST /api/v1/reports/generate` — generates and persists a report record, returning `report_id`.
- `GET /api/v1/reports/` — list persisted reports (owner-limited unless admin).
- `GET /api/v1/reports/{report_id}` — get report details including `summary`, `charts`, and `details`.
- Export endpoints: `/export/csv`, `/export/excel`, `/export/pdf` — produce downloadable files and append to report export history.

Notes

- Excel export requires `openpyxl` to be installed; otherwise the endpoint returns `501`.
- PDF generation uses `fpdf` and `ReportGenerator.generate_pdf_with_ai` attempts to include AI events.
- Export endpoints attempt to include AI events relevant to the report filters by querying `AIRepository.query_events_for_report`.
