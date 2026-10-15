import { getStoredAuthToken } from "./api";

/**
 * تعريف دقيق لأنواع الرسائل القادمة من الباكيند (صفحة 156)
 * هذا يمنع خطأ "Unexpected any"
 */
export type AlertWSData = {
  type: string;
  priority: string;
  camera_id: string;
  camera_name?: string;
  confidence?: number;
  event_id?: string;
  screenshot?: string | null;
  created_at?: string;
  event_time?: string;
  detection_time?: string;
  timestamp?: string;
  screenshot_timestamp?: string;
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

export type AlarmStateWSData = {
  camera_id: string;
  active: boolean;
  sources: string[];
};

export type AlarmStateSnapshotWSData = {
  states: Record<string, Omit<AlarmStateWSData, "camera_id">>;
};

export type CameraStatusWSData = {
  camera_id: string;
  status: string;
};

export type WSMessage =
  | { event: "new_alert"; data: AlertWSData }
  | { event: "ai_status"; data: DashboardStats }
  | { event: "ai_event"; data: AIEventWSData }
  | { event: "alarm_state"; data: AlarmStateWSData }
  | { event: "alarm_state_snapshot"; data: AlarmStateSnapshotWSData }
  | { event: "camera_status"; data: CameraStatusWSData }
  | { event: "socket_disconnected"; data: Record<string, never> };

export type SocketHandle = {
  socket: WebSocket | null;
  close: () => void;
};

let activeSocket: WebSocket | null = null;
let activeToken: string | null = null;
const subscribers = new Map<(message: WSMessage) => void, number>();
let reconnectTimer: number | null = null;
let reconnectAttempts = 0;
let alarmStates: AlarmStateSnapshotWSData["states"] = {};
let liveAlarmOverrides: AlarmStateSnapshotWSData["states"] = {};
let hasAlarmSnapshot = false;

const broadcastMessage = (message: WSMessage) => {
  subscribers.forEach((_count, subscriber) => subscriber(message));
};

const alarmSnapshotMessage = (): WSMessage => ({
  event: "alarm_state_snapshot",
  data: { states: { ...alarmStates } },
});

const clearAlarmStates = () => {
  alarmStates = {};
  liveAlarmOverrides = {};
  hasAlarmSnapshot = false;
};

const cancelReconnect = () => {
  if (reconnectTimer !== null) {
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
};

const disconnectSocket = () => {
  cancelReconnect();
  const socket = activeSocket;
  activeSocket = null;
  activeToken = null;
  reconnectAttempts = 0;
  clearAlarmStates();
  if (
    socket &&
    socket.readyState !== WebSocket.CLOSED &&
    socket.readyState !== WebSocket.CLOSING
  ) {
    socket.close();
  }
};

const scheduleReconnect = () => {
  if (reconnectTimer !== null || subscribers.size === 0) {
    return;
  }
  if (!getStoredAuthToken()) {
    return;
  }

  const delay = Math.min(1000 * 2 ** reconnectAttempts, 30000);
  reconnectAttempts += 1;
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null;
    connectSocket();
  }, delay);
};

const connectSocket = () => {
  const token = getStoredAuthToken();
  if (!token) {
    activeToken = null;
    return null;
  }
  cancelReconnect();

  if (
    activeSocket &&
    (activeSocket.readyState === WebSocket.OPEN ||
      activeSocket.readyState === WebSocket.CONNECTING) &&
    activeToken === token
  ) {
    return activeSocket;
  }

  if (activeSocket && activeSocket.readyState !== WebSocket.CLOSED) {
    const previousSocket = activeSocket;
    activeSocket = null;
    previousSocket.close();
  }

  activeToken = token;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsBaseUrl =
    import.meta.env.VITE_WS_BASE_URL || `${protocol}//${window.location.host}`;
  const WS_URL = `${wsBaseUrl}/ws/dashboard?token=${encodeURIComponent(token)}`;
  let socket: WebSocket;
  try {
    socket = new WebSocket(WS_URL);
  } catch (error) {
    activeToken = null;
    console.error("Failed to create dashboard WebSocket:", error);
    scheduleReconnect();
    return null;
  }

  socket.onopen = () => {
    if (activeSocket !== socket) {
      socket.close();
      return;
    }
    liveAlarmOverrides = {};
    hasAlarmSnapshot = false;
    console.log("🚀 [AeroGuard] Secure Socket Link Established");
  };

  socket.onmessage = (event) => {
    if (activeSocket !== socket) {
      return;
    }
    try {
      const parsed = JSON.parse(event.data) as WSMessage;
      if (parsed.event === "alarm_state") {
        const state = {
          active: parsed.data.active,
          sources: parsed.data.sources ?? [],
        };
        alarmStates[parsed.data.camera_id] = state;
        liveAlarmOverrides[parsed.data.camera_id] = state;
        broadcastMessage(parsed);
      } else if (parsed.event === "camera_status") {
        if (parsed.data.status === "Offline") {
          const inactiveState = { active: false, sources: [] };
          alarmStates[parsed.data.camera_id] = inactiveState;
          liveAlarmOverrides[parsed.data.camera_id] = inactiveState;
        }
        broadcastMessage(parsed);
      } else if (parsed.event === "alarm_state_snapshot") {
        alarmStates = { ...parsed.data.states };
        Object.entries(liveAlarmOverrides).forEach(([cameraId, state]) => {
          if (cameraId in alarmStates) {
            alarmStates[cameraId] = state;
          }
        });
        hasAlarmSnapshot = true;
        reconnectAttempts = 0;
        broadcastMessage(alarmSnapshotMessage());
      } else {
        broadcastMessage(parsed);
      }
    } catch (error) {
      console.error("❌ Failed to parse system event:", error);
    }
  };

  socket.onclose = () => {
    if (activeSocket !== socket) {
      return;
    }
    activeSocket = null;
    activeToken = null;

    if (subscribers.size === 0) {
      return;
    }

    clearAlarmStates();
    broadcastMessage({ event: "socket_disconnected", data: {} });
    scheduleReconnect();
  };

  socket.onerror = () => {
    if (activeSocket === socket) {
      socket.close();
    }
  };

  activeSocket = socket;
  return socket;
};

export const createSocket = (
  onMessage: (message: WSMessage) => void,
): SocketHandle => {
  const isNewSubscriber = !subscribers.has(onMessage);
  subscribers.set(onMessage, (subscribers.get(onMessage) ?? 0) + 1);
  const socket = connectSocket();
  if (
    isNewSubscriber &&
    hasAlarmSnapshot &&
    socket?.readyState === WebSocket.OPEN
  ) {
    onMessage(alarmSnapshotMessage());
  }
  let closed = false;

  return {
    socket,
    close: () => {
      if (closed) {
        return;
      }
      closed = true;
      const subscriberCount = subscribers.get(onMessage);
      if (subscriberCount !== undefined && subscriberCount > 1) {
        subscribers.set(onMessage, subscriberCount - 1);
      } else {
        subscribers.delete(onMessage);
      }
      if (subscribers.size === 0) {
        disconnectSocket();
      }
    },
  };
};

export const closeActiveSocket = () => {
  broadcastMessage({ event: "socket_disconnected", data: {} });
  subscribers.clear();
  disconnectSocket();
};
