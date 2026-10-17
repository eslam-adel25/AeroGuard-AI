# AI Engine & Modules

This document summarizes the AI pipeline that is implemented in the current workspace under backend/app/ai.

Core components

- backend/app/ai/processor.py — the central AI loop. It loads a YOLO model with ultralytics, reads frames from OpenCV, supports device `0`, RTSP/HTTP streams, and uploaded video paths, then runs object detection, tracking, and heuristic checks.
- backend/app/ai/tracker.py — the tracker facade used by the processor. The repository also contains adapter modules for ByteTrack and DeepSORT, but the current runtime path uses the built-in tracker manager fallback.
- backend/app/services/decision_engine.py — business rules for loitering, abandoned-bag, wrong-direction, restricted-area, fire, and smoke detection.
- backend/app/services/ai_service.py — persists AI events, stores screenshots under backend/uploads/ai_events, and broadcasts events to connected WebSocket clients.

What the current implementation does

- Loads the general model from backend/models/yolov8n.pt via the runtime path models/yolov8n.pt and the fire/smoke specialist from backend/models/fire-smoke-yolov8n.pt.
- The specialist model is local-only. Provision backend/models/fire-smoke-yolov8n.pt before starting the application; a missing, empty, unreadable, or invalid file disables specialist detection while general detection remains active.
- Runs both models on each inference frame, maps the specialist's verified class names to canonical fire and smoke detections, and merges overlapping same-class detections before tracking.
- Filters detections for classes relevant to campus/security use cases such as person, bag/backpack/suitcase, car/truck/bus/vehicle, fire, and smoke.
- Maintains track state across frames and uses heuristics to create alerts when rules are triggered.
- Stores annotated frames in memory so the camera stream endpoint can serve MJPEG output.

Runtime configuration

- The processor reads settings from the database-backed settings models and updates the running engine through update_config().
- GPU support is optional and toggled by the gpu_enabled setting; the code attempts to reload the model on CUDA when enabled.
- Detection confidence, frame skip, tracker backend, and the AI rule toggles are all exposed through the settings API.

Implementation note

- The AI engine is started from the cameras API and runs as a background task per camera. It is not a fully distributed worker queue, so production deployments with many cameras should consider dedicated worker processes or external task orchestration.
