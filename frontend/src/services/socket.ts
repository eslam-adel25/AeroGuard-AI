import { getStoredAuthToken } from "./api";

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
  critical_alerts?: number;
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

export type SocketHandle = {
  socket: WebSocket | null;
  close: () => void;
};

let activeSocket: WebSocket | null = null;
let activeToken: string | null = null;
const subscribers = new Set<(message: WSMessage) => void>();

const broadcastMessage = (message: WSMessage) => {
  subscribers.forEach((subscriber) => subscriber(message));
};

const disconnectSocket = () => {
  if (activeSocket && activeSocket.readyState !== WebSocket.CLOSED) {
    activeSocket.close();
  }

  activeSocket = null;
  activeToken = null;
};

const connectSocket = () => {
  const token = getStoredAuthToken();
  if (!token) {
    activeToken = null;
    return null;
  }

  if (
    activeSocket &&
    (activeSocket.readyState === WebSocket.OPEN ||
      activeSocket.readyState === WebSocket.CONNECTING) &&
    activeToken === token
  ) {
    return activeSocket;
  }

  if (activeSocket && activeSocket.readyState !== WebSocket.CLOSED) {
    activeSocket.close();
  }

  activeToken = token;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsBaseUrl =
    import.meta.env.VITE_WS_BASE_URL || `${protocol}//${window.location.host}`;
  const WS_URL = `${wsBaseUrl}/ws/dashboard?token=${encodeURIComponent(token)}`;
  const socket = new WebSocket(WS_URL);

  socket.onopen = () => {
    console.log("🚀 [AeroGuard] Secure Socket Link Established");
  };

  socket.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data) as WSMessage;
      broadcastMessage(parsed);
    } catch (error) {
      console.error("❌ Failed to parse system event:", error);
    }
  };

  socket.onclose = () => {
    if (activeSocket === socket) {
      activeSocket = null;
    }

    if (subscribers.size === 0) {
      activeToken = null;
      return;
    }

    const latestToken = getStoredAuthToken();
    if (!latestToken) {
      activeToken = null;
      return;
    }
  };

  activeSocket = socket;
  return socket;
};

export const createSocket = (
  onMessage: (message: WSMessage) => void,
): SocketHandle => {
  subscribers.add(onMessage);
  const socket = connectSocket();

  return {
    socket,
    close: () => {
      subscribers.delete(onMessage);
      if (subscribers.size === 0) {
        disconnectSocket();
      }
    },
  };
};

export const closeActiveSocket = () => {
  subscribers.clear();
  disconnectSocket();
};
