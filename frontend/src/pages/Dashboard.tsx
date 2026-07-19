import {
  useEffect,
  useState,
  useCallback,
  useRef,
  useLayoutEffect,
  type MouseEvent,
} from "react";
import {
  cameraService,
  getStoredAuthToken,
  type ZoneCreateData,
  type ZoneData,
} from "../services/api";
import { createSocket } from "../services/socket";
import type { WSMessage } from "../services/socket";
import { useTranslation } from "react-i18next";
import {
  Maximize,
  Minimize,
  Pause,
  Play,
  Camera as SnapshotIcon,
  ShieldAlert,
  Box,
  Loader2,
  ChevronRight,
  ChevronLeft,
} from "lucide-react";
import { motion } from "framer-motion";

function formatLocalDateTime(date: Date) {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const year = date.getFullYear();
  let hours = date.getHours();
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");
  const ampm = hours >= 12 ? "PM" : "AM";
  hours = hours % 12 || 12;
  const hourString = String(hours).padStart(2, "0");
  return `${month}/${day}/${year} ${hourString}:${minutes}:${seconds} ${ampm}`;
}

interface AlertData {
  camera_id: string;
  type: string;
  priority: string;
  confidence?: number;
  event_id?: string;
  screenshot?: string | null;
}

interface CameraData {
  camera_id: string;
  camera_name: string;
  location: string;
}

const Dashboard = () => {
  const { t } = useTranslation();
  // --- States ---
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [cameras, setCameras] = useState<CameraData[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [fps, setFps] = useState(0);
  const [bagCount, setBagCount] = useState(0);
  const [unknownObjectCount, setUnknownObjectCount] = useState(0);
  const [peopleCount, setPeopleCount] = useState(0);
  const [carCount, setCarCount] = useState(0);
  const [criticalAlertCount, setCriticalAlertCount] = useState(0);
  const [localDateTime, setLocalDateTime] = useState(() =>
    formatLocalDateTime(new Date()),
  );
  const [cameraStatus, setCameraStatus] = useState<
    "Running" | "Offline" | "Processing"
  >("Offline");
  const selectedCameraName =
    cameras.find((c) => c.camera_id === selectedCamera)?.camera_name || "";

  const videoContainerRef = useRef<HTMLDivElement>(null);
  const videoWrapperRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLImageElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const selectedCameraRef = useRef<string | null>(null);
  const streamToken = getStoredAuthToken();
  const [isDrawing, setIsDrawing] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [drawingPoints, setDrawingPoints] = useState<Array<[number, number]>>(
    [],
  );
  const [savedZones, setSavedZones] = useState<ZoneData[]>([]);
  const [drawingMode, setDrawingMode] = useState<
    "restricted" | "direction" | "tripwire"
  >("restricted");
  const [drawingInstructions, setDrawingInstructions] = useState<string>("");
  const [hoverPoint, setHoverPoint] = useState<[number, number] | null>(null);

  // --- AI Operations ---
  const stopCameraSession = useCallback(async (id: string | null) => {
    if (!id) return;
    try {
      await cameraService.stop(id);
    } catch {
      console.log("AI stopping...");
    }
  }, []);

  const startCameraAI = useCallback(async (id: string) => {
    setCameraStatus("Processing");
    try {
      await cameraService.start(id);
    } catch {
      console.log("AI initializing...");
    }
  }, []);

  const handleCameraSelection = useCallback(
    async (id: string, shouldStart: boolean = true) => {
      const previousCamera = selectedCameraRef.current;
      setSelectedCamera(id);
      selectedCameraRef.current = id;

      if (previousCamera && previousCamera !== id) {
        await stopCameraSession(previousCamera);
      }

      if (shouldStart) {
        await startCameraAI(id);
      } else {
        setCameraStatus("Offline");
      }
    },
    [startCameraAI, stopCameraSession],
  );

  useEffect(() => {
    selectedCameraRef.current = selectedCamera;
  }, [selectedCamera]);

  const fetchZones = useCallback(async (cameraId: string) => {
    try {
      const response = await cameraService.getZones(cameraId);
      setSavedZones(response.data as ZoneData[]);
    } catch (error) {
      console.error("Failed to load zones:", error);
      setSavedZones([]);
    }
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setLocalDateTime(formatLocalDateTime(new Date()));
    }, 1000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    const token = getStoredAuthToken();
    if (!token) {
      return;
    }

    const handleMessage = (message: WSMessage) => {
      if (message.event === "new_alert") {
        setAlerts((prev) => [message.data, ...prev].slice(0, 3));
        setTimeout(
          () => setAlerts((prev) => prev.filter((a) => a !== message.data)),
          5000,
        );
      }
      if (message.event === "ai_status") {
        if (
          message.data.camera_id &&
          selectedCameraRef.current &&
          message.data.camera_id !== selectedCameraRef.current
        ) {
          return;
        }
        setFps(message.data.fps ?? 0);
        setBagCount(message.data.bags ?? 0);
        setPeopleCount(message.data.persons ?? 0);
        setCarCount(message.data.cars ?? 0);
        setUnknownObjectCount(
          Math.max(
            0,
            (message.data.objects ?? 0) -
              (message.data.persons ?? 0) -
              (message.data.bags ?? 0) -
              (message.data.cars ?? 0),
          ),
        );
        if (message.data.critical_alerts !== undefined) {
          setCriticalAlertCount(message.data.critical_alerts);
        }
        setCameraStatus("Running");
      }

      if (message.event === "camera_status") {
        if (
          message.data.camera_id &&
          selectedCameraRef.current &&
          message.data.camera_id !== selectedCameraRef.current
        ) {
          return;
        }
        setCameraStatus(
          (message.data.status as "Running" | "Offline" | "Processing") ||
            "Offline",
        );
      }

      if (message.event === "ai_event") {
        const ev = message.data;
        setAlerts((prev) =>
          [
            {
              camera_id: ev.camera_id,
              type: ev.detection_type,
              priority: ev.severity,
              confidence: ev.confidence ?? 0,
              event_id: ev.event_id,
              screenshot: ev.screenshot ?? null,
            },
            ...prev,
          ].slice(0, 3),
        );
      }
    };

    const socket = createSocket(handleMessage);

    const init = async () => {
      try {
        const res = await cameraService.getAll();
        const data = res.data as CameraData[];
        setCameras(data);
        if (data.length > 0) {
          await handleCameraSelection(data[0].camera_id, true);
        }
      } catch {
        console.error("Link failed");
      }
    };

    init();
    return () => {
      socket.close();
    };
  }, [handleCameraSelection]);

  // --- Control Functions ---
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      videoContainerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const takeSnapshot = () => {
    if (videoRef.current) {
      const canvas = document.createElement("canvas");
      canvas.width = videoRef.current.naturalWidth;
      canvas.height = videoRef.current.naturalHeight;
      canvas.getContext("2d")?.drawImage(videoRef.current, 0, 0);
      const link = document.createElement("a");
      link.download = `AG_SNAPSHOT_${new Date().getTime()}.jpg`;
      link.href = canvas.toDataURL("image/jpeg");
      link.click();
    }
  };

  const getVideoRenderDetails = useCallback(() => {
    const video = videoRef.current;
    if (!video) return null;

    const rect = video.getBoundingClientRect();
    const naturalW = (video as HTMLImageElement).naturalWidth || rect.width;
    const naturalH = (video as HTMLImageElement).naturalHeight || rect.height;
    if (naturalW === 0 || naturalH === 0) return null;

    const scaleX = rect.width / naturalW;
    const scaleY = rect.height / naturalH;
    const scale = Math.max(scaleX, scaleY);
    const renderedW = naturalW * scale;
    const renderedH = naturalH * scale;
    const offsetX = Math.max(0, (renderedW - rect.width) / 2);
    const offsetY = Math.max(0, (renderedH - rect.height) / 2);

    return {
      rect,
      naturalW,
      naturalH,
      scale,
      offsetX,
      offsetY,
    };
  }, []);

  const getNormalizedVideoCoords = useCallback(
    (event: MouseEvent<HTMLCanvasElement>) => {
      const details = getVideoRenderDetails();
      if (!details) return null;

      const { rect, scale, offsetX, offsetY, naturalW, naturalH } = details;
      const xInElement = event.clientX - rect.left;
      const yInElement = event.clientY - rect.top;
      const videoX = (xInElement + offsetX) / scale;
      const videoY = (yInElement + offsetY) / scale;
      if (videoX < 0 || videoX > naturalW || videoY < 0 || videoY > naturalH) {
        return null;
      }
      return [videoX / naturalW, videoY / naturalH] as [number, number];
    },
    [getVideoRenderDetails],
  );

  const mapNormalizedToCanvasCoords = useCallback(
    (normalized: [number, number]) => {
      const details = getVideoRenderDetails();
      if (!details) return null;

      const { scale, offsetX, offsetY, naturalW, naturalH } = details;
      return [
        normalized[0] * naturalW * scale - offsetX,
        normalized[1] * naturalH * scale - offsetY,
      ] as [number, number];
    },
    [getVideoRenderDetails],
  );

  const getSavedZoneCanvasCoords = useCallback(
    (coords: [number, number][], zone?: ZoneData) => {
      const details = getVideoRenderDetails();
      if (!details) return [];

      const normalizePoint = (point: [number, number]) => {
        const [x, y] = point;
        if (x <= 1 && y <= 1) {
          return point;
        }
        const zoneW = zone?.video_width || details.naturalW;
        const zoneH = zone?.video_height || details.naturalH;
        if (zoneW === 0 || zoneH === 0) {
          return null;
        }
        return [x / zoneW, y / zoneH] as [number, number];
      };

      return coords
        .map(normalizePoint)
        .filter((value): value is [number, number] => value !== null)
        .map(mapNormalizedToCanvasCoords)
        .filter((value): value is [number, number] => value !== null);
    },
    [getVideoRenderDetails, mapNormalizedToCanvasCoords],
  );

  const updateOverlayCanvas = useCallback(() => {
    const canvas = overlayCanvasRef.current;
    const video = videoRef.current;
    const wrapper = videoWrapperRef.current;
    if (!canvas || !video || !wrapper) return;

    const rect = video.getBoundingClientRect();
    const containerRect = wrapper.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;

    canvas.width = Math.round(rect.width * ratio);
    canvas.height = Math.round(rect.height * ratio);
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
    canvas.style.left = `${rect.left - containerRect.left}px`;
    canvas.style.top = `${rect.top - containerRect.top}px`;

    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    }
  }, []);

  const drawOverlay = useCallback(() => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const ratio = window.devicePixelRatio || 1;
    ctx.clearRect(0, 0, canvas.width / ratio, canvas.height / ratio);

    const drawZone = (
      zone: ZoneData,
      fill = false,
      strokeStyle = "rgba(255, 255, 255, 0.9)",
      lineWidth = 2,
    ) => {
      const canvasCoords = getSavedZoneCanvasCoords(zone.polygon_coords, zone);
      if (canvasCoords.length === 0) return;
      const path = new Path2D();
      canvasCoords.forEach(([x, y], index) => {
        if (index === 0) {
          path.moveTo(x, y);
        } else {
          path.lineTo(x, y);
        }
      });
      if (zone.zone_type.toLowerCase().includes("direction")) {
        ctx.strokeStyle = "rgba(56, 161, 255, 0.95)";
        ctx.lineWidth = 3;
        ctx.stroke(path);
        if (canvasCoords.length >= 2) {
          const last = canvasCoords[canvasCoords.length - 1];
          const before = canvasCoords[canvasCoords.length - 2];
          const dx = last[0] - before[0];
          const dy = last[1] - before[1];
          const arrowX = last[0] - dx * 0.2;
          const arrowY = last[1] - dy * 0.2;
          ctx.beginPath();
          ctx.moveTo(last[0], last[1]);
          ctx.lineTo(arrowX - dy * 0.1, arrowY + dx * 0.1);
          ctx.lineTo(arrowX + dy * 0.1, arrowY - dx * 0.1);
          ctx.closePath();
          ctx.fillStyle = "rgba(56, 161, 255, 0.95)";
          ctx.fill();
        }
        return;
      }
      if (zone.zone_type.toLowerCase().includes("tripwire")) {
        ctx.strokeStyle = "rgba(250, 204, 21, 0.95)";
        ctx.lineWidth = 3;
        ctx.stroke(path);
        return;
      }
      if (fill) {
        ctx.fillStyle = "rgba(255, 0, 0, 0.18)";
        ctx.fill(path);
      }
      ctx.strokeStyle = strokeStyle;
      ctx.lineWidth = lineWidth;
      ctx.stroke(path);
    };

    savedZones.forEach((zone) =>
      drawZone(zone, zone.zone_type.toLowerCase().includes("restricted")),
    );

    if (drawingPoints.length === 0) return;

    const path = new Path2D();
    const canvasPoints = drawingPoints
      .map(mapNormalizedToCanvasCoords)
      .filter((p): p is [number, number] => p !== null);

    canvasPoints.forEach(([x, y], index) => {
      if (index === 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    });

    if (drawingMode === "restricted") {
      ctx.fillStyle = "rgba(255, 0, 0, 0.18)";
      ctx.strokeStyle = "rgba(255, 0, 0, 0.95)";
      ctx.lineWidth = 3;
      ctx.fill(path);
      ctx.stroke(path);
    } else if (drawingMode === "direction") {
      ctx.strokeStyle = "rgba(56, 161, 255, 0.95)";
      ctx.lineWidth = 3;
      ctx.stroke(path);
      if (canvasPoints.length >= 2) {
        const last = canvasPoints[canvasPoints.length - 1];
        const before = canvasPoints[canvasPoints.length - 2];
        const dx = last[0] - before[0];
        const dy = last[1] - before[1];
        const arrowX = last[0] - dx * 0.2;
        const arrowY = last[1] - dy * 0.2;
        ctx.beginPath();
        ctx.moveTo(last[0], last[1]);
        ctx.lineTo(arrowX - dy * 0.1, arrowY + dx * 0.1);
        ctx.lineTo(arrowX + dy * 0.1, arrowY - dx * 0.1);
        ctx.closePath();
        ctx.fillStyle = "rgba(56, 161, 255, 0.95)";
        ctx.fill();
      }
    } else {
      ctx.strokeStyle = "rgba(250, 204, 21, 0.95)";
      ctx.lineWidth = 3;
      ctx.stroke(path);
    }

    canvasPoints.forEach(([x, y], index) => {
      ctx.beginPath();
      const radius =
        hoverPoint &&
        hoverPoint[0] === drawingPoints[index][0] &&
        hoverPoint[1] === drawingPoints[index][1]
          ? 8
          : 5;
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fillStyle = "#ffffff";
      ctx.strokeStyle = "rgba(0,0,0,0.35)";
      ctx.lineWidth = 2;
      ctx.fill();
      ctx.stroke();
    });
  }, [
    drawingPoints,
    drawingMode,
    hoverPoint,
    savedZones,
    getSavedZoneCanvasCoords,
    mapNormalizedToCanvasCoords,
  ]);

  useLayoutEffect(() => {
    updateOverlayCanvas();
    drawOverlay();
  }, [updateOverlayCanvas, drawOverlay]);

  useEffect(() => {
    const handleLayoutChange = () => {
      updateOverlayCanvas();
      drawOverlay();
    };

    const wrapper = videoWrapperRef.current;
    if (wrapper) {
      const resizeObserver = new ResizeObserver(() => handleLayoutChange());
      resizeObserver.observe(wrapper);
      window.addEventListener("resize", handleLayoutChange);
      document.addEventListener("fullscreenchange", handleLayoutChange);
      return () => {
        resizeObserver.disconnect();
        window.removeEventListener("resize", handleLayoutChange);
        document.removeEventListener("fullscreenchange", handleLayoutChange);
      };
    }

    window.addEventListener("resize", handleLayoutChange);
    document.addEventListener("fullscreenchange", handleLayoutChange);
    return () => {
      window.removeEventListener("resize", handleLayoutChange);
      document.removeEventListener("fullscreenchange", handleLayoutChange);
    };
  }, [updateOverlayCanvas, drawOverlay]);

  useEffect(() => {
    const updateForCamera = () => {
      updateOverlayCanvas();
      drawOverlay();
    };
    updateForCamera();
  }, [selectedCamera, isSidebarOpen, updateOverlayCanvas, drawOverlay]);

  useEffect(() => {
    if (selectedCamera) {
      void fetchZones(selectedCamera);
    } else {
      setSavedZones([]);
    }
  }, [selectedCamera, fetchZones]);

  const enterDrawingMode = useCallback(() => {
    setDrawingPoints([]);
    setDrawingMode("restricted");
    setIsDrawing(true);
    setIsSidebarOpen(true);
    setDrawingInstructions(t("dashboard.drawingInstructions.initial"));
  }, [t]);

  const exitDrawingMode = useCallback(() => {
    setIsDrawing(false);
    setDrawingInstructions("");
    setHoverPoint(null);
  }, []);

  const undoLastPoint = useCallback(() => {
    setDrawingPoints((prev) => prev.slice(0, -1));
    setDrawingInstructions(t("dashboard.drawingInstructions.removed"));
    setTimeout(
      () => setDrawingInstructions(t("dashboard.drawingInstructions.initial")),
      1800,
    );
  }, [t]);

  const clearDrawing = useCallback(() => {
    setDrawingPoints([]);
    setDrawingInstructions(t("dashboard.drawingInstructions.cleared"));
    setTimeout(() => setDrawingInstructions(""), 1800);
  }, [t]);

  const deleteZone = useCallback(
    async (zoneId: string) => {
      if (!selectedCamera) return;
      try {
        await cameraService.deleteZone(selectedCamera, zoneId);
        await fetchZones(selectedCamera);
      } catch (err) {
        console.error("Failed to delete zone:", err);
      }
    },
    [fetchZones, selectedCamera],
  );

  const saveDrawing = useCallback(async () => {
    try {
      setIsDrawing(false);
      setDrawingInstructions(
        t("dashboard.drawingInstructions.saving") ||
          t("dashboard.drawingInstructions.saved"),
      );
      const vid = videoRef.current;
      if (!selectedCamera) throw new Error("No camera selected");
      if (!vid) throw new Error("No video available");

      const nativeW = (vid as HTMLImageElement).naturalWidth;
      const nativeH = (vid as HTMLImageElement).naturalHeight;
      const zoneType =
        drawingMode === "restricted"
          ? "Restricted Area"
          : drawingMode === "direction"
            ? "Direction"
            : "Tripwire";
      const zoneName = `${t("dashboard.inCameraAnnotation")} - ${zoneType}`;

      const payload: ZoneCreateData = {
        zone_name: zoneName,
        zone_type: zoneType,
        polygon_coords: drawingPoints,
        video_width: nativeW || undefined,
        video_height: nativeH || undefined,
      };

      try {
        await cameraService.addZone(selectedCamera, payload);
        setDrawingInstructions(t("dashboard.drawingInstructions.saved"));
        await fetchZones(selectedCamera);
      } catch (err) {
        console.error("Failed to save zone:", err);
        setDrawingInstructions(
          t("dashboard.drawingInstructions.saveFailed") ||
            "Failed to save zone",
        );
      }
    } finally {
      setHoverPoint(null);
      setIsSidebarOpen(false);
      setTimeout(() => setDrawingInstructions(""), 2200);
    }
  }, [t, drawingPoints, drawingMode, selectedCamera, fetchZones]);

  const onCanvasClick = (event: MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    const normalized = getNormalizedVideoCoords(event);
    if (!normalized) return;
    setDrawingPoints((prev) => [...prev, normalized]);
  };

  const onCanvasDoubleClick = (event: MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    event.preventDefault();
    saveDrawing();
  };

  const onCanvasContextMenu = (event: MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    event.preventDefault();
    undoLastPoint();
  };

  const onCanvasMouseMove = (event: MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    const normalized = getNormalizedVideoCoords(event);
    if (!normalized) return;

    const canvasPoint = mapNormalizedToCanvasCoords(normalized);
    if (!canvasPoint) return;

    const closest = drawingPoints.reduce<null | [number, number]>(
      (best, point) => {
        const pointCanvas = mapNormalizedToCanvasCoords(point);
        if (!pointCanvas) return best;
        const dx = pointCanvas[0] - canvasPoint[0];
        const dy = pointCanvas[1] - canvasPoint[1];
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 12) return point;
        return best;
      },
      null,
    );

    setHoverPoint(closest);
  };

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!isDrawing) return;
      if (event.key === "Escape") {
        exitDrawingMode();
      }
      if (event.key === "Enter") {
        saveDrawing();
      }
      if (event.key === "Backspace") {
        event.preventDefault();
        undoLastPoint();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isDrawing, saveDrawing, exitDrawingMode, undoLastPoint]);

  return (
    <div className="min-h-screen bg-ag-dark text-ag-primary p-2 md:p-3 font-sans overflow-hidden">
      {/* Camera-first Layout */}
      <div className="grid grid-rows-[minmax(0,1fr)_auto] gap-2 h-[calc(100vh-1.5rem)] min-h-0">
        <div
          ref={videoContainerRef}
          className="relative group rounded-lg overflow-hidden border border-white/8 shadow-[0_18px_60px_rgba(0,0,0,0.45)] bg-black ring-1 ring-white/8 min-h-0 flex flex-row items-stretch w-full h-full"
        >
          {/* Main Video Area */}
          <div
            ref={videoWrapperRef}
            className="relative flex-1 min-w-0 h-full overflow-hidden"
          >
            {/* Compact Top-Center Status Bar */}
            <div className="absolute top-4 left-1/2 z-40 -translate-x-1/2 pointer-events-none inline-flex items-center gap-4">
              <div className="inline-flex items-center gap-3 rounded-[18px] border border-white/15 bg-black/25 px-3 py-1.5 shadow-[0_10px_30px_rgba(0,0,0,0.18)] backdrop-blur-md text-[14px] font-semibold text-white whitespace-nowrap">
                <span className="flex items-center gap-2">
                  <span className="text-[14px]">📹</span>
                  <span className="max-w-[140px] overflow-hidden text-ellipsis text-white/90">
                    {selectedCameraName}
                  </span>
                </span>

                <span className="text-white/50">|</span>
                <span className="flex items-center gap-2 text-[14px] text-white">
                  <span className="h-2 w-2 rounded-full bg-ag-success" />
                  {cameraStatus}
                </span>

                <span className="text-white/50">|</span>
                <span className="flex items-center gap-1 text-white/90">
                  FPS: <span className="font-black text-ag-success">{fps}</span>
                </span>

                <span className="text-white/50">|</span>
                <span className="flex items-center gap-1 text-white/90">
                  <span>🧳</span>
                  <span className="font-black">{bagCount}</span>
                </span>

                <span className="text-white/50">|</span>
                <span className="flex items-center gap-1 text-white/90">
                  <span>❓</span>
                  <span className="font-black">{unknownObjectCount}</span>
                </span>

                <span className="text-white/50">|</span>
                <span className="flex items-center gap-1 text-white/90">
                  <span>👤</span>
                  <span className="font-black">{peopleCount}</span>
                </span>

                <span className="text-white/50">|</span>
                <span className="flex items-center gap-1 text-white/90">
                  <span>🚨</span>
                  <span className="font-black">{criticalAlertCount}</span>
                </span>

                <span className="text-white/50">|</span>
                <span className="flex items-center gap-1 text-white/90">
                  <span>🚗</span>
                  <span className="font-black">{carCount}</span>
                </span>
              </div>
              <div className="inline-flex items-center gap-3 rounded-[18px] border border-white/15 bg-black/25 px-3 py-1.5 shadow-[0_10px_30px_rgba(0,0,0,0.18)] backdrop-blur-md text-[14px] font-semibold text-white whitespace-nowrap">
                {localDateTime}
              </div>
            </div>

            {/* Floating Violation Alerts */}
            <div className="absolute left-1/2 top-[12%] z-50 flex w-full -translate-x-1/2 flex-col items-center gap-2 pointer-events-none px-3 md:px-6">
              {alerts.map((alert, idx) => (
                <div
                  key={idx}
                  className="max-w-[92%] rounded-xl border border-ag-danger/40 bg-ag-danger/12 backdrop-blur-lg px-4 py-3 flex items-center gap-3 animate-in slide-in-from-top zoom-in duration-300 shadow-[0_6px_30px_rgba(239,68,68,0.12)]"
                >
                  <div className="bg-ag-danger/90 p-2.5 rounded-xl shadow-lg">
                    <ShieldAlert size={20} className="text-white" />
                  </div>
                  <div>
                    <p className="text-[9px] font-black text-ag-danger uppercase tracking-[0.3em]">
                      {t("dashboard.criticalAlert")}
                    </p>
                    <h4 className="text-base md:text-lg font-black text-white uppercase tracking-tighter">
                      {alert.type} {t("dashboard.detectLabel")}
                    </h4>
                  </div>
                  {alert.event_id ? (
                    <div className="ml-auto flex items-center gap-2 pointer-events-auto">
                      <button
                        onClick={async () => {
                          try {
                            const res = await (
                              await import("../services/api")
                            ).aiService.downloadScreenshot(
                              alert.event_id as string,
                            );
                            const blob = res.data as Blob;
                            const url = window.URL.createObjectURL(blob);
                            window.open(url, "_blank");
                          } catch (err) {
                            console.error(err);
                          }
                        }}
                        className="rounded-full bg-white/6 px-3 py-2 text-xs text-white cursor-pointer"
                      >
                        View
                      </button>
                      <button
                        onClick={async () => {
                          try {
                            const res = await (
                              await import("../services/api")
                            ).aiService.downloadScreenshot(
                              alert.event_id as string,
                            );
                            const blob = res.data as Blob;
                            const url = window.URL.createObjectURL(blob);
                            const a = document.createElement("a");
                            a.href = url;
                            a.download = `ai_event_${alert.event_id}.jpg`;
                            a.click();
                            window.URL.revokeObjectURL(url);
                          } catch (err) {
                            console.error(err);
                          }
                        }}
                        className="rounded-full bg-white/6 px-3 py-2 text-xs text-white cursor-pointer"
                      >
                        Download
                      </button>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>

            {/* Video Stream Implementation */}
            {selectedCamera ? (
              <>
                <img
                  ref={videoRef}
                  src={
                    isPaused || !selectedCamera
                      ? ""
                      : streamToken
                        ? `/api/v1/cameras/${selectedCamera}/stream?token=${encodeURIComponent(streamToken)}`
                        : `/api/v1/cameras/${selectedCamera}/stream`
                  }
                  alt="AeroGuard Engine"
                  onLoad={() => {
                    updateOverlayCanvas();
                    drawOverlay();
                  }}
                  className={`absolute inset-0 h-full w-full object-cover transition-transform duration-700 ${isPaused ? "scale-[1.02] blur-sm opacity-30" : "scale-100 opacity-100"}`}
                />
                <canvas
                  ref={overlayCanvasRef}
                  onClick={onCanvasClick}
                  onDoubleClick={onCanvasDoubleClick}
                  onContextMenu={onCanvasContextMenu}
                  onMouseMove={onCanvasMouseMove}
                  className={`absolute left-0 top-0 z-30 ${isDrawing ? "pointer-events-auto cursor-crosshair" : "pointer-events-none"}`}
                />
              </>
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-ag-dark">
                <Loader2
                  className="animate-spin text-ag-danger mb-4"
                  size={52}
                />
                <p className="text-gray-500 font-black uppercase tracking-[0.35em] text-[11px]">
                  {t("dashboard.controls.awaitingLink")}
                </p>
              </div>
            )}

            {/* Compact Control Bar */}
            <div className="absolute left-1/2 bottom-3 z-50 flex -translate-x-1/2 items-center gap-2 rounded-full border border-white/10 bg-black/50 px-3 py-2 shadow-md backdrop-blur-lg opacity-95 transition-all duration-250 group-hover:scale-[1.02]">
              <button
                onClick={async () => {
                  if (isPaused) {
                    setIsPaused(false);
                    if (selectedCamera) {
                      await startCameraAI(selectedCamera);
                    }
                  } else {
                    setIsPaused(true);
                    if (selectedCamera) {
                      await stopCameraSession(selectedCamera);
                    }
                  }
                }}
                className="p-2.5 bg-white/6 hover:bg-ag-danger rounded-full text-white transition-transform hover:scale-105 cursor-pointer"
              >
                {isPaused ? (
                  <Play size={20} fill="white" />
                ) : (
                  <Pause size={20} fill="white" />
                )}
              </button>
              <div className="w-px h-6 bg-white/10" />
              <button
                onClick={takeSnapshot}
                className="p-2.5 bg-white/6 hover:bg-ag-success rounded-full text-white transition-transform hover:scale-105 cursor-pointer"
                title={t("dashboard.captureIncident")}
              >
                <SnapshotIcon size={18} />
              </button>
              <button
                onClick={enterDrawingMode}
                className={`p-2.5 rounded-full text-white transition-transform hover:scale-105 cursor-pointer ${isDrawing ? "bg-ag-success" : "bg-white/6 hover:bg-blue-600"}`}
                title={t("dashboard.controls.enterDrawing")}
              >
                <Box size={18} />
              </button>
              <div className="w-px h-6 bg-white/10" />
              <button
                onClick={toggleFullscreen}
                className="p-2.5 bg-white/6 hover:bg-white/10 rounded-full text-white transition-transform hover:scale-105 cursor-pointer"
              >
                {isFullscreen ? <Minimize size={18} /> : <Maximize size={18} />}
              </button>
            </div>
          </div>

          {/* Right Collapsible Sidebar Panel */}
          {isDrawing && (
            <div className="relative shrink-0 flex items-stretch">
              {/* Arrow Control Button */}
              <button
                onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                className="absolute top-1/2 -translate-y-1/2 -left-3.5 z-50 w-7 h-11 bg-[#0c1322] border border-white/10 border-r-0 rounded-l-md flex items-center justify-center cursor-pointer text-gray-400 hover:text-white hover:bg-white/5 transition-colors shadow-lg"
                style={{
                  transform: isSidebarOpen
                    ? "translateY(-50%)"
                    : "translateY(-50%) translateX(14px)",
                }}
              >
                {isSidebarOpen ? (
                  <ChevronRight size={14} />
                ) : (
                  <ChevronLeft size={14} />
                )}
              </button>

              {/* Sidebar Panel Container */}
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: isSidebarOpen ? 320 : 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                className="h-full border-l border-white/10 bg-[#0c1322] flex flex-col text-white overflow-hidden"
              >
                <div className="w-[320px] flex-1 p-6 flex flex-col justify-between h-full">
                  <div className="space-y-6">
                    {/* Header */}
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-[10px] uppercase tracking-[0.32em] text-gray-400">
                          {t("dashboard.drawingMode")}
                        </p>
                        <h3 className="text-sm font-bold uppercase tracking-[0.14em] text-white">
                          {t("dashboard.inCameraAnnotation")}
                        </h3>
                      </div>
                      <button
                        onClick={exitDrawingMode}
                        className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[11px] text-gray-200 hover:bg-white/10 transition cursor-pointer"
                      >
                        {t("common.cancel")}
                      </button>
                    </div>

                    {/* Mode Selector */}
                    <div className="flex flex-wrap gap-2">
                      {(["restricted", "direction", "tripwire"] as const).map(
                        (mode) => (
                          <button
                            key={mode}
                            onClick={() => {
                              setDrawingMode(mode);
                              setDrawingInstructions(
                                mode === "restricted"
                                  ? t(
                                      "dashboard.drawingInstructions.restricted",
                                    )
                                  : mode === "direction"
                                    ? t(
                                        "dashboard.drawingInstructions.direction",
                                      )
                                    : t(
                                        "dashboard.drawingInstructions.tripwire",
                                      ),
                              );
                            }}
                            className={`rounded-full px-3 py-1 text-[11px] font-semibold transition cursor-pointer ${
                              drawingMode === mode
                                ? "bg-ag-success text-black"
                                : "bg-white/10 text-gray-300 hover:bg-white/15"
                            }`}
                          >
                            {mode.toUpperCase()}
                          </button>
                        ),
                      )}
                    </div>

                    {/* Instructions */}
                    <p className="text-[12px] leading-5 text-gray-300">
                      {drawingInstructions}
                    </p>

                    {/* Points Counter */}
                    <div className="text-[11px] text-gray-400">
                      {t("common.points")}:{" "}
                      <span className="text-white font-bold">
                        {drawingPoints.length}
                      </span>
                    </div>

                    {savedZones.length > 0 ? (
                      <div className="space-y-2 rounded-2xl border border-white/10 bg-white/5 p-3 text-white">
                        <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.24em] text-gray-400">
                          <span>{t("dashboard.savedZones")}</span>
                          <span className="text-white/70">
                            {savedZones.length}
                          </span>
                        </div>
                        <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                          {savedZones.map((zone) => (
                            <div
                              key={zone.zone_id}
                              className="flex items-center justify-between gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2"
                            >
                              <div className="min-w-0 text-[11px] text-white/90 overflow-hidden text-ellipsis whitespace-nowrap">
                                {zone.zone_name}
                              </div>
                              <button
                                onClick={() => deleteZone(zone.zone_id)}
                                className="rounded-full bg-white/5 px-2 py-1 text-[10px] text-gray-200 hover:bg-white/10 transition"
                              >
                                {t("common.delete")}
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {/* Action Buttons */}
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={undoLastPoint}
                        className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[11px] text-gray-200 hover:bg-white/10 transition cursor-pointer"
                      >
                        {t("common.undo")}
                      </button>
                      <button
                        onClick={clearDrawing}
                        className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[11px] text-gray-200 hover:bg-white/10 transition cursor-pointer"
                      >
                        {t("common.clear")}
                      </button>
                      <button
                        onClick={saveDrawing}
                        className="rounded-full bg-ag-success px-4 py-1.5 text-[11px] font-semibold text-black hover:bg-lime-400 transition cursor-pointer ml-auto"
                      >
                        {t("common.save")}
                      </button>
                    </div>
                  </div>

                  {/* Bottom Hint */}
                  <div className="pt-6 border-t border-white/5">
                    <p className="text-[10px] uppercase tracking-[0.28em] text-gray-500 leading-relaxed">
                      {t("dashboard.controls.doubleClickHint")}
                    </p>
                  </div>
                </div>
              </motion.div>
            </div>
          )}
        </div>

        {/* Camera Strip */}
        <div className="rounded-xl border border-white/6 bg-ag-card/30 px-3 py-2 backdrop-blur-sm shadow-md">
          <div className="flex gap-3 overflow-x-auto pb-1 custom-scrollbar">
            {cameras.map((cam) => (
              <button
                key={cam.camera_id}
                onClick={async () => {
                  if (cam.camera_id === selectedCamera) {
                    return;
                  }

                  const shouldStart = !isPaused;
                  setIsPaused(false);
                  await handleCameraSelection(cam.camera_id, shouldStart);

                  if (!shouldStart) {
                    setIsPaused(true);
                  }
                }}
                className={`px-4 py-2 rounded-2xl text-[11px] font-black transition-all border flex items-center gap-3 whitespace-nowrap tracking-widest cursor-pointer
                    ${
                      selectedCamera === cam.camera_id
                        ? "bg-ag-danger border-ag-danger text-white shadow-lg shadow-red-900/25 scale-[0.98]"
                        : "bg-black/20 border-white/5 text-gray-500 hover:text-white hover:border-white/10"
                    }`}
              >
                <div
                  className={`w-2 h-2 rounded-full ${selectedCamera === cam.camera_id ? "bg-white" : "bg-gray-700"}`}
                ></div>
                {cam.camera_name.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
