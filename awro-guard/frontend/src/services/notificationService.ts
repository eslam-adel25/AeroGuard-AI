import api from "./api";
import { createSocket, type AlertWSData } from "./socket";
import { aiService } from "./api";

export type NotificationSeverity =
  | "Critical"
  | "High"
  | "Medium"
  | "Low"
  | "Normal";

export interface NotificationItem {
  id: string; // event_id when available
  eventId?: string | null;
  detectionType: string;
  cameraName: string;
  severity: NotificationSeverity;
  time: string;
  status: "Read" | "Unread";
  screenshot?: string | null;
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
      // Prefer AI events as the notifications history
      const resp = await aiService.listEvents({ limit: 50 });
      const payload = (
        resp.data && Array.isArray(resp.data.items)
          ? resp.data.items
          : resp.data
      ) as Array<Record<string, unknown>>;
      return payload.map((item) => ({
        id: String(
          item.event_id ??
            item.id ??
            `${item.camera_id ?? "unknown"}-${item.type ?? "alert"}`,
        ),
        eventId: item.event_id
          ? String(item.event_id)
          : item.id
            ? String(item.id)
            : null,
        detectionType: String(
          item.detection_type ?? item.type ?? "Unknown Detection",
        ),
        cameraName: String(
          item.camera_name ?? item.camera_id ?? "Unknown Camera",
        ),
        severity:
          (item.severity as NotificationSeverity) ??
          (item.priority as NotificationSeverity) ??
          "Normal",
        time: String(item.created_at ?? item.time ?? new Date().toISOString()),
        status: item.status === "Read" ? "Read" : "Unread",
        screenshot:
          (item.screenshot_path as string) ??
          (item.screenshot as string) ??
          null,
      }));
    } catch (err) {
      console.error("fetchNotifications failed", err);
      try {
        // fallback to legacy notifications endpoint
        const response = await api.get("/notifications/");
        const payload = response.data as Array<Record<string, unknown>>;
        return payload.map((item) => ({
          id: String(
            item.id ?? `${item.camera_id ?? "unknown"}-${item.type ?? "alert"}`,
          ),
          eventId: item.id ? String(item.id) : null,
          detectionType: String(item.type ?? "Unknown Detection"),
          cameraName: String(
            item.camera_name ?? item.camera_id ?? "Unknown Camera",
          ),
          severity: (item.priority as NotificationSeverity) ?? "Normal",
          time: String(item.time ?? new Date().toISOString()),
          status: item.status === "Read" ? "Read" : "Unread",
          screenshot: null,
        }));
      } catch {
        return [];
      }
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
