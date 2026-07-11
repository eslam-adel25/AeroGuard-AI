import {
  useEffect,
  useState,
  useCallback,
  useRef,
  useLayoutEffect,
  type MouseEvent,
} from "react";
import { cameraService, getStoredAuthToken } from "../services/api";

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
} from "lucide-react";

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
  const [detectionCount, setDetectionCount] = useState(0);
  const [peopleCount, setPeopleCount] = useState(0);
  const [carCount, setCarCount] = useState(0);
  const [bagCount, setBagCount] = useState(0);

  const videoContainerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLImageElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const streamToken = getStoredAuthToken();
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawingPoints, setDrawingPoints] = useState<Array<[number, number]>>(
    [],
  );
  const [drawingMode, setDrawingMode] = useState<
    "restricted" | "direction" | "tripwire"
  >("restricted");
  const [drawingInstructions, setDrawingInstructions] = useState<string>("");
  const [hoverPoint, setHoverPoint] = useState<[number, number] | null>(null);

  // --- AI Operations ---
  const startCameraAI = useCallback(async (id: string) => {
    try {
      await cameraService.start(id);
    } catch {
      console.log("AI initializing...");
    }
  }, []);

  useEffect(() => {
    const token = getStoredAuthToken();
    if (!token) {
      return;
    }

    const handleMessage = (message: WSMessage) => {
      if (message.event === "new_alert") {
        setAlerts((prev) => [message.data, ...prev].slice(0, 3));
        setDetectionCount((c) => c + 1);
        setTimeout(
          () => setAlerts((prev) => prev.filter((a) => a !== message.data)),
          5000,
        );
      }
      if (message.event === "ai_status") {
        setFps(message.data.fps || 0);
        setDetectionCount(message.data.objects || 0);
        setPeopleCount(message.data.persons || 0);
        setBagCount(message.data.bags || 0);
        setCarCount(message.data.cars || 0);
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
          setSelectedCamera(data[0].camera_id);
          startCameraAI(data[0].camera_id);
        }
      } catch {
        console.error("Link failed");
      }
    };

    init();
    return () => {
      socket.close();
    };
  }, [startCameraAI]);

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

  const getCanvasCoords = (event: MouseEvent<HTMLCanvasElement>) => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    return [event.clientX - rect.left, event.clientY - rect.top] as [
      number,
      number,
    ];
  };

  const updateOverlayCanvas = useCallback(() => {
    const canvas = overlayCanvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video || !videoContainerRef.current) return;

    const rect = video.getBoundingClientRect();
    const containerRect = videoContainerRef.current.getBoundingClientRect();

    canvas.width = rect.width;
    canvas.height = rect.height;
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
    canvas.style.left = `${rect.left - containerRect.left}px`;
    canvas.style.top = `${rect.top - containerRect.top}px`;
  }, []);

  const drawOverlay = useCallback(() => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (drawingPoints.length === 0) return;

    const path = new Path2D();
    drawingPoints.forEach(([x, y], index) => {
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
      if (drawingPoints.length >= 2) {
        const last = drawingPoints[drawingPoints.length - 1];
        const before = drawingPoints[drawingPoints.length - 2];
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

    drawingPoints.forEach(([x, y]) => {
      ctx.beginPath();
      const radius =
        hoverPoint && hoverPoint[0] === x && hoverPoint[1] === y ? 8 : 5;
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fillStyle = "#ffffff";
      ctx.strokeStyle = "rgba(0,0,0,0.35)";
      ctx.lineWidth = 2;
      ctx.fill();
      ctx.stroke();
    });
  }, [drawingPoints, drawingMode, hoverPoint]);

  useLayoutEffect(() => {
    updateOverlayCanvas();
    drawOverlay();
  }, [updateOverlayCanvas, drawOverlay]);

  useEffect(() => {
    const handleResize = () => {
      updateOverlayCanvas();
      drawOverlay();
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [updateOverlayCanvas, drawOverlay]);

  useEffect(() => {
    const updateForCamera = () => {
      updateOverlayCanvas();
      drawOverlay();
    };
    updateForCamera();
  }, [selectedCamera, updateOverlayCanvas, drawOverlay]);

  const enterDrawingMode = useCallback(() => {
    setDrawingPoints([]);
    setDrawingMode("restricted");
    setIsDrawing(true);
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

  const saveDrawing = useCallback(() => {
    setIsDrawing(false);
    setDrawingInstructions(t("dashboard.drawingInstructions.saved"));
    setHoverPoint(null);
    setTimeout(() => setDrawingInstructions(""), 2200);
  }, [t]);

  const onCanvasClick = (event: MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    const coords = getCanvasCoords(event);
    if (!coords) return;
    setDrawingPoints((prev) => [...prev, coords]);
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
    const coords = getCanvasCoords(event);
    if (!coords) return;

    const closest = drawingPoints.reduce<null | [number, number]>(
      (best, point) => {
        const dx = point[0] - coords[0];
        const dy = point[1] - coords[1];
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
      {/* Compact Header (reduced height for camera-first UX) */}
      <header className="h-12 md:h-14 flex items-center justify-between rounded-lg bg-ag-card/45 backdrop-blur-xl border border-white/5 shadow-lg px-3 md:px-4 mb-2">
        <div className="flex items-center gap-3 md:gap-4 min-w-0">
          <div className="min-w-0 flex items-center gap-3">
            <h1 className="text-sm md:text-base font-bold tracking-tight text-white leading-none">
              {t("dashboard.monitoringTitle")}
            </h1>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-ag-success rounded-full animate-pulse" />
              <p className="text-[10px] text-ag-success font-semibold uppercase truncate">
                {t("dashboard.secureNodeActive")}
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Camera-first Layout */}
      <div className="grid grid-rows-[minmax(0,1fr)_auto] gap-2 h-[calc(100vh-3.2rem)] min-h-0">
        <div
          ref={videoContainerRef}
          className="relative group rounded-lg overflow-hidden border border-white/8 shadow-[0_18px_60px_rgba(0,0,0,0.45)] bg-black ring-1 ring-white/8 min-h-0"
        >
          {/* Compact Glass Overlays */}
          <div className="absolute left-4 top-4 z-40 pointer-events-none flex flex-col gap-3 max-w-[min(42%,360px)]">
            <div className="rounded-2xl border border-white/10 bg-black/50 backdrop-blur-xl px-3 py-3 shadow-xl shadow-black/20">
              <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.32em] text-white/75 mb-2">
                <span className="w-2 h-2 rounded-full bg-ag-success animate-pulse" />
                {t("dashboard.liveMonitoring")}
              </div>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.22em] text-gray-300">
                    {t("dashboard.camera")}
                  </p>
                  <p className="text-sm font-bold text-white truncate">
                    {cameras.find((c) => c.camera_id === selectedCamera)
                      ?.camera_name || t("dashboard.provisioning")}
                  </p>
                </div>
                <div className="rounded-full bg-white/10 px-2 py-1 text-[11px] uppercase tracking-[0.22em] text-ag-success font-black">
                  {t("common.active")}
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/50 backdrop-blur-xl px-3 py-3 shadow-xl shadow-black/20">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-[52px]">
                  <p className="text-[9px] uppercase tracking-[0.2em] text-gray-400">
                    {t("common.fps")}
                  </p>
                  <p className="text-lg font-black text-ag-success font-mono">
                    {fps || 30}
                  </p>
                </div>
                <div className="min-w-[66px]">
                  <p className="text-[9px] uppercase tracking-[0.2em] text-gray-400">
                    {t("common.objects")}
                  </p>
                  <p className="text-lg font-black text-white font-mono">
                    {detectionCount}
                  </p>
                </div>
                <div className="min-w-[66px]">
                  <p className="text-[9px] uppercase tracking-[0.2em] text-gray-400">
                    People
                  </p>
                  <p className="text-lg font-black text-white font-mono">
                    {peopleCount}
                  </p>
                </div>
                <div className="min-w-[66px]">
                  <p className="text-[9px] uppercase tracking-[0.2em] text-gray-400">
                    Bags
                  </p>
                  <p className="text-lg font-black text-white font-mono">
                    {bagCount}
                  </p>
                </div>
                <div className="min-w-[66px]">
                  <p className="text-[9px] uppercase tracking-[0.2em] text-gray-400">
                    Cars
                  </p>
                  <p className="text-lg font-black text-white font-mono">
                    {carCount}
                  </p>
                </div>
                <div className="flex items-center gap-2 rounded-full bg-black/30 px-3 py-2">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse shadow-[0_0_12px_rgba(239,68,68,0.4)]" />
                  <span className="text-[10px] uppercase tracking-[0.24em] text-white font-semibold">
                    {t("common.recording")}
                  </span>
                </div>
              </div>
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
                      className="rounded-full bg-white/6 px-3 py-2 text-xs text-white"
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
                      className="rounded-full bg-white/6 px-3 py-2 text-xs text-white"
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
                className={`absolute left-0 top-0 z-30 ${isDrawing ? "pointer-events-auto" : "pointer-events-none"}`}
              />
            </>
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-ag-dark">
              <Loader2 className="animate-spin text-ag-danger mb-4" size={52} />
              <p className="text-gray-500 font-black uppercase tracking-[0.35em] text-[11px]">
                {t("dashboard.controls.awaitingLink")}
              </p>
            </div>
          )}

          {/* Compact Control Bar */}
          <div className="absolute left-1/2 bottom-3 z-50 flex -translate-x-1/2 items-center gap-2 rounded-full border border-white/10 bg-black/50 px-3 py-2 shadow-md backdrop-blur-lg opacity-95 transition-all duration-250 group-hover:scale-[1.02]">
            <button
              onClick={() => setIsPaused(!isPaused)}
              className="p-2.5 bg-white/6 hover:bg-ag-danger rounded-full text-white transition-transform hover:scale-105"
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
              className="p-2.5 bg-white/6 hover:bg-ag-success rounded-full text-white transition-transform hover:scale-105"
              title={t("dashboard.captureIncident")}
            >
              <SnapshotIcon size={18} />
            </button>
            <button
              onClick={enterDrawingMode}
              className="p-2.5 bg-white/6 hover:bg-blue-600 rounded-full text-white transition-transform hover:scale-105"
              title={t("dashboard.controls.enterDrawing")}
            >
              <Box size={18} />
            </button>
            <div className="w-px h-6 bg-white/10" />
            <button
              onClick={toggleFullscreen}
              className="p-2.5 bg-white/6 hover:bg-white/10 rounded-full text-white transition-transform hover:scale-105"
            >
              {isFullscreen ? <Minimize size={18} /> : <Maximize size={18} />}
            </button>
          </div>

          {isDrawing && (
            <div className="absolute right-4 bottom-24 z-50 w-[min(320px,calc(100%-2rem))] rounded-3xl border border-white/10 bg-black/70 backdrop-blur-xl p-4 shadow-2xl shadow-black/40 text-white">
              <div className="flex items-center justify-between gap-3 mb-3">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.32em] text-gray-400">
                    {t("dashboard.drawingMode")}
                  </p>
                  <h3 className="text-sm font-bold uppercase tracking-[0.14em]">
                    {t("dashboard.inCameraAnnotation")}
                  </h3>
                </div>
                <button
                  onClick={exitDrawingMode}
                  className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[11px] text-gray-200 hover:bg-white/10"
                >
                  {t("common.cancel")}
                </button>
              </div>
              <p className="text-[12px] leading-5 text-gray-300 mb-3">
                {drawingInstructions}
              </p>
              <div className="flex flex-wrap gap-2 mb-3">
                {(["restricted", "direction", "tripwire"] as const).map(
                  (mode) => (
                    <button
                      key={mode}
                      onClick={() => {
                        setDrawingMode(mode);
                        setDrawingInstructions(
                          mode === "restricted"
                            ? t("dashboard.drawingInstructions.restricted")
                            : mode === "direction"
                              ? t("dashboard.drawingInstructions.direction")
                              : t("dashboard.drawingInstructions.tripwire"),
                        );
                      }}
                      className={`rounded-full px-3 py-1 text-[11px] font-semibold transition ${
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
              <div className="flex flex-wrap gap-2 items-center justify-between">
                <div className="text-[11px] text-gray-400">
                  {t("common.points")}:{" "}
                  <span className="text-white">{drawingPoints.length}</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={undoLastPoint}
                    className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[11px] text-gray-200 hover:bg-white/10"
                  >
                    {t("common.undo")}
                  </button>
                  <button
                    onClick={clearDrawing}
                    className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[11px] text-gray-200 hover:bg-white/10"
                  >
                    {t("common.clear")}
                  </button>
                  <button
                    onClick={saveDrawing}
                    className="rounded-full bg-ag-success px-3 py-1 text-[11px] font-semibold text-black hover:bg-lime-400"
                  >
                    {t("common.save")}
                  </button>
                </div>
              </div>
              <p className="mt-3 text-[10px] uppercase tracking-[0.28em] text-gray-500">
                {t("dashboard.controls.doubleClickHint")}
              </p>
            </div>
          )}

          {/* Recording Indicator */}
          <div className="absolute top-4 right-4 z-30 flex items-center gap-2 rounded-full border border-white/10 bg-black/50 px-3 py-2 backdrop-blur-xl">
            <div className="w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse shadow-[0_0_10px_rgba(239,68,68,0.3)]"></div>
            <span className="text-[10px] font-semibold text-white uppercase tracking-[0.22em]">
              {t("common.recording")}
            </span>
          </div>
        </div>

        {/* Camera Strip */}
        <div className="rounded-xl border border-white/6 bg-ag-card/30 px-3 py-2 backdrop-blur-sm shadow-md">
          <div className="flex gap-3 overflow-x-auto pb-1 custom-scrollbar">
            {cameras.map((cam) => (
              <button
                key={cam.camera_id}
                onClick={() => {
                  setSelectedCamera(cam.camera_id);
                  setIsPaused(false);
                  startCameraAI(cam.camera_id);
                }}
                className={`px-4 py-2 rounded-2xl text-[11px] font-black transition-all border flex items-center gap-3 whitespace-nowrap tracking-widest
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
