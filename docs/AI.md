# AI Engine & Modules (derived from code)

This document describes the AI pipeline and detection/tracking modules implemented in the repository under `awro-guard/backend/app/ai`.

Core components

- `awro-guard/backend/app/ai/processor.py` — `AIProcessor` is the central processing loop. It:
  - Loads a YOLO model via `ultralytics.YOLO(model_path)` (the project includes `models/yolov8n.pt`).
  - Reads frames from OpenCV `VideoCapture` (supports device `0`, RTSP/HTTP, or uploaded file paths).
  - Optionally respects `frame_skip` from runtime settings to reduce inference frequency.
  - Filters detected classes against a whitelist (person, bag/backpack/suitcase, car/truck/bus/vehicle, fire, smoke).
  - Performs tracking via `TrackerManager` (adapter that can support ByteTrack/DeepSORT adapters).
  - Runs heuristics (loitering, abandoned bag, wrong direction, restricted area) and triggers alerts by calling `AIService.register_event()` and broadcasting via `websocket.manager.broadcast()`.

- `awro-guard/backend/app/ai/tracker.py` and `bytetrack_adapter.py` / `deepsort_adapter.py` — tracker adapters provide a pluggable tracking layer. The repository includes adapter files, and the processor uses `TrackerManager().initialize()` and `update()` to maintain object tracks.

AIService

- `awro-guard/backend/app/services/ai_service.py` — Responsible for persisting AI events via `AIRepository`, saving screenshots under `uploads/ai_events`, and broadcasting events to WebSocket clients.

Decision Engine

- `awro-guard/backend/app/services/decision_engine.py` — Applies business rules to detection/track outputs. The `AIProcessor` consults the `DecisionEngine` to categorize detections and decide when to create events.

Model files

- `awro-guard/backend/app/models/yolov8n.pt` and `awro-guard/backend/models/yolov8n.pt` are present in the repository and used by the `AIProcessor` when initialized with `model_path="models/yolov8n.pt"`.

AI capabilities observed in code

- Person detection (YOLO classes mapped to `person`).
- Baggage detection (bag, backpack, suitcase) and abandoned-bag heuristics.
- Vehicle detection (car/truck/bus/vehicle).
- Fire and smoke detection triggers immediate high-priority alerts.
- Loitering detection based on movement thresholds and time tracked per `track_id`.
- Wrong-direction heuristics comparing vertical movement.
- Restricted zone detection by polygon point-in-polygon tests (OpenCV `pointPolygonTest`).
- Tracking via `TrackerManager` with configurable adapters.

Limitations & runtime notes

- GPU support is toggled by `gpu_enabled` in `SystemSettings`; `AIProcessor.update_config()` attempts to reload the YOLO model on `cuda` when enabled.
- The pipeline relies on `ultralytics` and `opencv-python` for detection and frame handling.
- The AI engine stores screenshots to disk when requested; the screenshot path is included in AI event records.

Concrete configuration knobs are present in `UserSettings` / `SystemSettings` and can be reviewed in the source models and settings API.
