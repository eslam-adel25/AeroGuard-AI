# Reports System

The repository includes a reporting subsystem that aggregates detections and AI events for dashboards and exportable reports.

Key components

- backend/app/services/report_service.py — gathers report statistics and constructs report payloads.
- backend/app/repositories/report_repository.py — persists report records and exposes list/get/delete operations.
- backend/app/utils/report_generator.py — creates exportable report output for CSV, Excel, and PDF-style generation.

API endpoints

- GET /api/v1/reports/summary — returns aggregate stats for a supplied date range and optional filters.
- GET /api/v1/reports/dashboard — returns the analytics payload used by the dashboard UI.
- POST /api/v1/reports/generate — creates and stores a report record.
- GET /api/v1/reports/ — lists existing reports.
- GET /api/v1/reports/{report_id} — returns the report details.
- GET /api/v1/reports/export/csv — exports a report as CSV.
- GET /api/v1/reports/export/excel — exports a report as Excel when openpyxl is available.
- GET /api/v1/reports/export/pdf — exports a report as PDF.

Notes

- Export endpoints append metadata to the report’s export_history field.
- The report routes filter results by ownership unless the caller is an Administrator.
- The current implementation depends on the installed reporting libraries in backend/requirements.txt.
