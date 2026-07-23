import { useEffect, useState, useRef } from "react";
import { useTranslation } from "react-i18next";
import { X, Download } from "lucide-react";
import { aiService, getFilenameFromContentDisposition } from "../services/api";

interface Props {
  eventId: string;
  onClose: () => void;
}

export default function ScreenshotModal({ eventId, onClose }: Props) {
  const { t } = useTranslation();
  const [url, setUrl] = useState<string | null>(null);
  const objectUrlRef = useRef<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      try {
        const resp = await aiService.downloadScreenshot(eventId);
        const blob = resp.data as Blob;
        const objectUrl = URL.createObjectURL(blob);
        objectUrlRef.current = objectUrl;
        if (mounted) setUrl(objectUrl);
      } catch (err) {
        console.error("Failed to load screenshot", err);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
    };
  }, [eventId]);

  const handleDownload = async () => {
    try {
      const resp = await aiService.downloadScreenshot(eventId);
      const blob = resp.data as Blob;
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      const responseFilename = getFilenameFromContentDisposition(
        resp.headers["content-disposition"],
      );
      a.download = responseFilename || `ai_event_${eventId}.jpg`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      console.error("Download failed", err);
    }
  };

  return (
    <div className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/60 p-4">
      <div className="relative max-w-[95vw] max-h-[95vh] w-full overflow-hidden rounded-2xl bg-[#071018] p-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm font-semibold text-white">
            {t("app.screenshotModal.title")}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownload}
              className="rounded-md bg-white/5 px-3 py-1 text-sm text-white"
            >
              <Download size={14} className="inline-block mr-2" />
              {t("common.download")}
            </button>
            <button
              onClick={onClose}
              className="rounded-md bg-white/5 px-3 py-1 text-sm text-white"
            >
              <X size={14} />
            </button>
          </div>
        </div>

        <div className="flex h-[70vh] items-center justify-center overflow-auto">
          {loading ? (
            <div className="text-gray-400">
              {t("app.screenshotModal.loading")}
            </div>
          ) : url ? (
            <img src={url} alt="AI event" className="max-h-[70vh] w-auto" />
          ) : (
            <div className="text-gray-400">
              {t("app.screenshotModal.empty")}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
