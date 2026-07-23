import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { aiService } from "../services/api";
import ScreenshotModal from "../components/ScreenshotModal";

interface AIEvent {
  event_id: string;
  detection_type: string;
  camera_name?: string;
  created_at?: string;
}

export default function AlertHistory() {
  const { t } = useTranslation();
  const [events, setEvents] = useState<AIEvent[]>([]);
  const [page] = useState(0);
  const [selectedEvent, setSelectedEvent] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const resp = await aiService.listEvents({
          limit: 50,
          offset: page * 50,
        });
        const data = resp.data;
        type ResponseItem = Record<string, unknown>;
        const maybe = data as unknown;
        let items: ResponseItem[] = [];
        if (
          typeof maybe === "object" &&
          maybe !== null &&
          "items" in (maybe as Record<string, unknown>)
        ) {
          const m = maybe as Record<string, unknown>;
          if (Array.isArray(m.items)) items = m.items as ResponseItem[];
        } else if (Array.isArray(maybe)) {
          items = maybe as ResponseItem[];
        }
        setEvents(
          items.map((it: ResponseItem) => ({
            event_id: String(it.event_id ?? it.id ?? ""),
            detection_type: String(it.detection_type ?? it.type ?? "Unknown"),
            camera_name:
              (it.camera_name as string) ?? (it.camera_id as string) ?? "",
            created_at: (it.created_at as string) ?? (it.time as string) ?? "",
          })),
        );
      } catch (err) {
        console.error("Failed to load AI events", err);
      }
    };
    load();
  }, [page]);

  return (
    <div className="p-6">
      <h2 className="mb-4 text-2xl font-bold text-white">
        {t("alertHistory.title")}
      </h2>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {events.map((ev) => (
          <div key={ev.event_id} className="rounded-lg bg-ag-card p-3">
            <div className="mb-2 text-sm font-semibold text-white">
              {ev.detection_type}
            </div>
            <div className="mb-2 text-xs text-gray-400">{ev.camera_name}</div>
            <div className="mb-2 text-xs text-gray-400">{ev.created_at}</div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setSelectedEvent(ev.event_id)}
                className="rounded-full bg-white/5 px-3 py-1 text-sm text-white"
              >
                {t("common.view")}
              </button>
            </div>
          </div>
        ))}
      </div>

      {selectedEvent && (
        <ScreenshotModal
          eventId={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}
    </div>
  );
}
