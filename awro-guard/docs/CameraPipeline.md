# Camera Pipeline and AI Processing

This document summarizes the camera processing pipeline implemented in `awro-guard/backend/app/ai/processor.py` and the related API controls.

Overview

- Cameras can be added via `POST /api/v1/cameras/` as `LIVE`, `USB`, or `UPLOAD` (video file). Uploaded videos are stored under `awro-guard/backend/uploads/videos/`.
- Starting processing: `POST /api/v1/cameras/{camera_id}/start` adds a background task that calls `AIProcessor.process_camera(camera_id, stream_url)`.
- Stopping processing: `AIProcessor.stop_camera(camera_id)` sets a stop flag; the `cameras` router also calls `ai_engine.stop_camera()` during deletion.

AI loop (in `AIProcessor.process_camera`)

1. Source resolution: supports `0` for local device, RTSP/HTTP streams, or absolute/relative uploaded file paths.
2. Load zones: restricted zones for the camera are loaded from DB and drawn on frames for detection.
3. Model inference: YOLOv8 is used (`ultralytics.YOLO`), with configurable `detection_confidence` and `frame_skip` via `SystemSettings`.
4. Detection filtering: only classes relevant to the application (`person`, `bag`, `backpack`, `suitcase`, `car`, `truck`, `bus`, `vehicle`, `fire`, `smoke`) are processed.
5. Tracking: `TrackerManager` maintains object tracks; default implementation is IoUTracker fallback; adapters for ByteTrack/DeepSORT exist as shims.
6. Heuristics: loitering, abandoned bag, wrong direction, restricted area detection trigger `Detection` records and AI events.
7. Persistence and notifications: detections saved via `DetectionRepository`, AI events persisted via `AIService.register_event()` and pushed over WebSocket.
8. Annotated frames: the processor keeps the last annotated frame in memory (`last_frames`) to support MJPEG streaming endpoint.

Runtime controls

- Settings that influence the pipeline are exposed in `SystemSettings` and `UserSettings`: detection confidence, frame skip, tracker backend, toggles for loitering/abandoned bag/wrong direction/restricted area detection.
- `AIProcessor.update_config(settings_model)` reloads the YOLO model (attempts to use GPU when `gpu_enabled` is set).

Performance

- The processor runs inference in a thread via `asyncio.to_thread` to keep the event loop responsive.
- For production with many cameras, move AI work to dedicated workers (separate processes or GPU-backed workers) and coordinate via a task queue.

Files of interest

- `awro-guard/backend/app/ai/processor.py`
- `awro-guard/backend/app/ai/tracker.py`
- `awro-guard/backend/app/ai/bytetrack_adapter.py`
- `awro-guard/backend/app/ai/deepsort_adapter.py`
- `awro-guard/backend/app/services/ai_service.py`
