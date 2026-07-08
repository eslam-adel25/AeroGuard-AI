from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ...websocket.manager import manager

router = APIRouter()


@router.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    # استقبال التوكن والتأكد منه
    await manager.connect(websocket)
    try:
        while True:
            # انتظار رسائل بسيطة أو مجرد الحفاظ على الاتصال
            data = await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket)