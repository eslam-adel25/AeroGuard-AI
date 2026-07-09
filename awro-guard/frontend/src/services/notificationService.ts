import api from "./api";
import { createSocket, type AlertWSData } from "./socket";

export type NotificationSeverity =
  | "Critical"
  | "High"
  | "Medium"
  | "Low"
  | "Normal";

export interface NotificationItem {
  id: string;
  detectionType: string;
  cameraName: string;
  severity: NotificationSeverity;
  time: string;
  status: "Read" | "Unread";
}

const normalizeNotification = (
  data: AlertWSData,
  cameraName?: string,
): NotificationItem => ({
  id: `${data.camera_id}-${data.type}-${data.priority}-${Date.now()}`,
  detectionType: data.type || "Unknown Detection",
  cameraName: cameraName || data.camera_id || "Unknown Camera",
  severity: (data.priority as NotificationSeverity) ?? "Normal",
  time: new Date().toISOString(),
  status: "Unread",
});

export const notificationService = {
  fetchNotifications: async (): Promise<NotificationItem[]> => {
    try {
      const response = await api.get("/notifications/");
      const payload = response.data as Array<Record<string, unknown>>;
      return payload.map((item) => ({
        id: String(
          item.id ?? `${item.camera_id ?? "unknown"}-${item.type ?? "alert"}`,
        ),
        detectionType: String(item.type ?? "Unknown Detection"),
        cameraName: String(
          item.camera_name ?? item.camera_id ?? "Unknown Camera",
        ),
        severity: (item.priority as NotificationSeverity) ?? "Normal",
        time: String(item.time ?? new Date().toISOString()),
        status: item.status === "Read" ? "Read" : "Unread",
      }));
    } catch {
      return [];
    }
  },

  subscribeToLiveAlerts: (
    callback: (notification: NotificationItem) => void,
  ): WebSocket | null => {
    try {
      return createSocket((message) => {
        if (message.event === "new_alert") {
          const notification = normalizeNotification(message.data);
          callback(notification);
        }
      });
    } catch (error) {
      console.error("Notification stream unavailable", error);
      return null;
    }
  },
};
