from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from ...ai.processor import ai_engine
from ...database.session import SessionLocal
from ...repositories.camera_repository import CameraRepository
from ...websocket.manager import manager
from ...core.security import verify_token

router = APIRouter()


def _build_alarm_state_snapshot(user_id, role):
    if ai_engine is None:
        return {}
    is_admin = role == "Administrator"
    if not is_admin and not user_id:
        return {}

    db = SessionLocal()
    try:
        cameras = CameraRepository(db).get_all_cameras(
            owner_id=user_id,
            is_admin=is_admin,
        )
        return {
            str(camera.camera_id): {
                "active": bool(
                    ai_engine._active_alarm_state.get(str(camera.camera_id), False)
                ),
                "sources": list(
                    ai_engine._active_alarm_sources.get(str(camera.camera_id), [])
                ),
            }
            for camera in cameras
        }
    finally:
        db.close()


@router.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    payload = verify_token(token)
    if not payload:
        await websocket.close(code=1008)
        return

    user_id = str(payload.get("user_id")) if payload.get("user_id") else None
    role = payload.get("role")
    await manager.connect(
        websocket,
        user_id=user_id,
        role=role,
    )
    try:
        await websocket.send_json({
            "event": "alarm_state_snapshot",
            "data": {
                "states": _build_alarm_state_snapshot(user_id, role),
            },
        })
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)