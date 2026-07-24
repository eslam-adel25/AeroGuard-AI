# Camera Pipeline and AI Processing

This document summarizes the camera processing pipeline implemented in backend/app/ai/processor.py and the related API controls.

Overview

- Cameras can be created through POST /api/v1/cameras/ as LIVE, USB, or UPLOAD sources.
- Uploaded video files are stored under backend/uploads/videos/.
- Starting processing calls the AI processor in the background; stopping processing sets a stop flag and marks the camera offline.

AI loop

1. Source resolution: the processor accepts device `0`, RTSP/HTTP streams, or an uploaded file path.
2. Restricted zones: zone polygons are loaded from the database and used when evaluating detections.
3. Model inference: YOLOv8 runs through ultralytics with configurable confidence and frame-skip settings.
4. Detection filtering: only relevant classes are processed by the heuristics engine.
5. Tracking: the processor maintains tracks across frames and uses the tracker manager facade.
6. Heuristics: loitering, abandoned-bag, wrong-direction, restricted-area, fire, and smoke rules can create detections and AI events.
7. Persistence and notifications: detections are stored in the database and AI events are pushed to WebSocket clients.
8. Annotated frames: the last processed frame is cached for the MJPEG stream endpoint.

Runtime controls

- The settings APIs update the in-memory AI processor configuration.
- Detection confidence, frame skip, tracker backend, and rule toggles are all read from the settings model.

Performance note

- The current implementation uses a background task per camera and runs inference in a worker-friendly path. It is adequate for small deployments but should be scaled out for larger numbers of cameras.

Files of interest

- backend/app/ai/processor.py
- backend/app/ai/tracker.py
- backend/app/ai/bytetrack_adapter.py
- backend/app/ai/deepsort_adapter.py
- backend/app/services/ai_service.py
