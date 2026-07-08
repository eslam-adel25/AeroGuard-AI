from typing import List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # قائمة بكل المتصفحات المفتوحة حالياً (Active Dashboards)
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # إرسال الرسالة لكل الموظفين المتصلين في نفس اللحظة
        for connection in self.active_connections:
            await connection.send_json(message)

# إنشاء نسخة واحدة ثابتة (Singleton) ليستخدمها كل السيستم
manager = ConnectionManager()