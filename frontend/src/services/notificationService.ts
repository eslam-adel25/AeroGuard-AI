import api, { aiService, getStoredAuthToken } from "./api";
import { createSocket, type AIEventWSData } from "./socket";

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
  cameraId?: string;
  cameraName: string;
  severity: NotificationSeverity;
  time: string;
  status: "Read" | "Unread";
  screenshot?: string | null;
}

export interface NotificationHistory {
  items: NotificationItem[];
  unreadCount: number;
}

const normalizeAIEvent = (data: AIEventWSData): NotificationItem => ({
  id: data.event_id,
  eventId: data.event_id,
  detectionType: data.detection_type || "Unknown Detection",
  cameraId: data.camera_id,
  cameraName: data.camera_id || "Unknown Camera",
  severity: (data.severity as NotificationSeverity) ?? "Normal",
  time: data.created_at ?? new Date().toISOString(),
  status: "Unread",
  screenshot: data.screenshot ?? null,
});

export const notificationService = {
  fetchNotifications: async (): Promise<NotificationHistory> => {
    try {
      // Prefer AI events as the notifications history
      const resp = await aiService.listEvents({ limit: 50 });
      const payload = (
        resp.data && Array.isArray(resp.data.items)
          ? resp.data.items
          : resp.data
      ) as Array<Record<string, unknown>>;
      const items = payload.map(
        (item): NotificationItem => ({
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
          cameraId: item.camera_id ? String(item.camera_id) : undefined,
          cameraName: String(
            item.camera_name ?? item.camera_id ?? "Unknown Camera",
          ),
          severity:
            (item.severity as NotificationSeverity) ??
            (item.priority as NotificationSeverity) ??
            "Normal",
          time: String(
            item.created_at ??
              item.time ??
              item.timestamp ??
              new Date().toISOString(),
          ),
          status: item.status === "Read" ? "Read" : "Unread",
          screenshot:
            (item.screenshot_path as string) ??
            (item.screenshot as string) ??
            null,
        }),
      );
      return {
        items,
        unreadCount: Number(
          resp.data?.unread_count ??
            items.filter((item) => item.status === "Unread").length,
        ),
      };
    } catch (err) {
      console.error("fetchNotifications failed", err);
      try {
        // fallback to legacy notifications endpoint
        const response = await api.get("/notifications/");
        const payload = response.data as Array<Record<string, unknown>>;
        const items = payload.map(
          (item): NotificationItem => ({
            id: String(
              item.id ??
                `${item.camera_id ?? "unknown"}-${item.type ?? "alert"}`,
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
          }),
        );
        return {
          items,
          unreadCount: items.filter((item) => item.status === "Unread").length,
        };
      } catch {
        return { items: [], unreadCount: 0 };
      }
    }
  },

  subscribeToLiveAlerts: (
    callback: (notification: NotificationItem) => void,
  ) => {
    try {
      const token = getStoredAuthToken();
      if (!token) {
        return null;
      }

      return createSocket((message) => {
        if (message.event === "ai_event") {
          const notification = normalizeAIEvent(message.data);
          callback(notification);
        }
      });
    } catch (error) {
      console.error("Notification stream unavailable", error);
      return null;
    }
  },
};
