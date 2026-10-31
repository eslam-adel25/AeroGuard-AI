from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from ...ai.processor import ai_engine
from ...database.session import SessionLocal
from ...repositories.camera_repository import CameraRepository
from ...models.models import Camera
from ...websocket.manager import manager
from ...core.auth_middleware import (
    ensure_platform_owner_active,
    ensure_user_can_access_platform,
    is_user_currently_authorized,
    load_user_from_token,
)
from ...core.tenant import PLATFORM_TENANT_SCOPE, customer_profile_for_user
from ...core.customer_features import has_customer_feature
from ...core.security import verify_token

router = APIRouter()


def _build_alarm_state_snapshot(user_id, customer_profile_id, is_owner=False):
    if ai_engine is None:
        return {}
    if not customer_profile_id:
        return {}

    db = SessionLocal()
    try:
        cameras = (
            db.query(Camera).all()
            if is_owner
            else CameraRepository(db).get_all_cameras(
                owner_id=user_id,
                customer_profile_id=customer_profile_id,
            )
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


def _build_tripwire_alarm_snapshot(user_id, customer_profile_id, is_owner=False):
    if ai_engine is None:
        return {}
    if not customer_profile_id:
        return {}

    db = SessionLocal()
    try:
        cameras = (
            db.query(Camera).all()
            if is_owner
            else CameraRepository(db).get_all_cameras(
                owner_id=user_id,
                customer_profile_id=customer_profile_id,
            )
        )
        return {
            str(camera.camera_id): {
                str(zone_id): {
                    "active": bool(state.get("active")),
                    "event_id": state.get("event_id"),
                }
                for zone_id, state in ai_engine._active_tripwire_alarm_states.get(
                    str(camera.camera_id),
                    {},
                ).items()
                if state.get("active") and state.get("event_id")
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

    if not verify_token(token):
        await websocket.close(code=1008)
        return

    db = SessionLocal()
    try:
        try:
            user = load_user_from_token(token, db)
            role = user.role.role_name if user.role else None
            if role == "Owner":
                ensure_platform_owner_active(user)
            else:
                ensure_user_can_access_platform(user)
        except HTTPException:
            await websocket.close(code=1008)
            return
        if not role:
            await websocket.close(code=1008)
            return
        is_owner = role == "Owner"
        tenant = None if is_owner else customer_profile_for_user(user)
        if not is_owner and tenant is None:
            await websocket.close(code=1008)
            return
        tenant_id = (
            PLATFORM_TENANT_SCOPE
            if is_owner
            else str(tenant.customer_profile_id)
        )
        user_id = str(user.user_id)
        enabled_socket_feature = is_owner or any(
            has_customer_feature(db, user_id, role, feature)
            for feature in ("dashboard", "cameras", "alerts")
        )
        if not enabled_socket_feature:
            await websocket.close(code=1008)
            return
        can_receive_alerts = is_owner or has_customer_feature(
            db, user_id, role, "alerts"
        )
    finally:
        db.close()

    await manager.connect(
        websocket,
        user_id=user_id,
        role=role,
        customer_profile_id=tenant_id,
        authorization_check=lambda: is_user_currently_authorized(user_id),
        feature_authorization_check=lambda feature: (
            is_owner or is_user_currently_authorized(user_id, feature)
        ),
    )
    try:
        if can_receive_alerts:
            await websocket.send_json({
                "event": "alarm_state_snapshot",
                "data": {
                    "states": _build_alarm_state_snapshot(
                        user_id, tenant_id, is_owner
                    ),
                },
            })
            await websocket.send_json({
                "event": "tripwire_alarm_snapshot",
                "data": {
                    "states": _build_tripwire_alarm_snapshot(
                        user_id, tenant_id, is_owner
                    ),
                },
            })
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)