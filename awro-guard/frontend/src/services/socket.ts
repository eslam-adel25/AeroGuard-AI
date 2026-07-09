/**
 * تعريف دقيق لأنواع الرسائل القادمة من الباكيند (صفحة 156)
 * هذا يمنع خطأ "Unexpected any"
 */
export type AlertWSData = {
  type: string;
  priority: string;
  camera_id: string;
  confidence?: number;
  event_id?: string;
  screenshot?: string | null;
};

export type DashboardStats = {
  fps: number;
  objects: number;
  persons: number;
  bags: number;
  cars: number;
  camera_id?: string;
};

export type AIEventWSData = {
  event_id: string;
  camera_id: string;
  detection_type: string;
  severity: string;
  confidence?: number;
  created_at?: string;
  screenshot?: string | null;
};

export type CameraStatusWSData = {
  camera_id: string;
  status: string;
};

export type WSMessage =
  | { event: "new_alert"; data: AlertWSData }
  | { event: "ai_status"; data: DashboardStats }
  | { event: "ai_event"; data: AIEventWSData }
  | { event: "camera_status"; data: CameraStatusWSData };
export const createSocket = (onMessage: (message: WSMessage) => void) => {
  const token = localStorage.getItem("ag_token");
  // استخدام المنفذ الافتراضي للباكيند
  const WS_URL = `ws://127.0.0.1:8000/ws/dashboard?token=${token}`;

  const socket = new WebSocket(WS_URL);

  socket.onopen = () =>
    console.log("🚀 [AeroGuard] Secure Socket Link Established");

  socket.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data) as WSMessage;
      onMessage(parsed);
    } catch (error) {
      console.error("❌ Failed to parse system event:", error);
    }
  };

  socket.onclose = () => {
    console.warn("⚠️ Connection lost. Retrying in 3s...");
    setTimeout(() => createSocket(onMessage), 3000);
  };

  return socket;
};
