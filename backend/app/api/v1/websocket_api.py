from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from ...websocket.manager import manager
from ...core.security import verify_token

router = APIRouter()


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

    await manager.connect(
        websocket,
        user_id=str(payload.get("user_id")) if payload.get("user_id") else None,
        role=payload.get("role"),
    )
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)