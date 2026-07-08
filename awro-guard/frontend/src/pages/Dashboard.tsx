import { useEffect, useState, useCallback, useRef } from "react";
import { cameraService } from "../services/api";

import { createSocket } from "../services/socket";
import type { WSMessage } from "../services/socket";
import {
  Bell,
  Maximize,
  Minimize,
  Pause,
  Play,
  Camera as SnapshotIcon,
  ShieldAlert,
  Box,
  Loader2,
  Radio,
  Scan,
  ChevronsRight,
} from "lucide-react";

interface AlertData {
  camera_id: string;
  type: string;
  priority: string;
  confidence: number;
}

interface CameraData {
  camera_id: string;
  camera_name: string;
  location: string;
}

const Dashboard = () => {
  // --- States ---
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [cameras, setCameras] = useState<CameraData[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [fps, setFps] = useState(0);
  const [detectionCount, setDetectionCount] = useState(0);

  const videoContainerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLImageElement>(null);

  // --- AI Operations ---
  const startCameraAI = useCallback(async (id: string) => {
    try {
      await cameraService.start(id);
    } catch {
      console.log("AI initializing...");
    }
  }, []);

  useEffect(() => {
    const socket = createSocket((message: WSMessage) => {
      if (message.event === "new_alert") {
        setAlerts((prev) => [message.data, ...prev].slice(0, 3));
        setDetectionCount((c) => c + 1);
        // إخفاء التنبيه تلقائياً بعد 5 ثوانٍ لضمان نظافة الشاشة
        setTimeout(
          () => setAlerts((prev) => prev.filter((a) => a !== message.data)),
          5000,
        );
      }
      if (message.event === "ai_status") {
        setFps(message.data.fps || 0);
        setDetectionCount(message.data.objects || 0);
      }
    });

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
      if (socket) socket.close();
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

  return (
    <div className="min-h-screen bg-ag-dark text-ag-primary p-3 md:p-4 font-sans overflow-hidden">
      {/* Compact Header */}
      <header className="h-16 md:h-18 flex items-center justify-between rounded-[1.4rem] bg-ag-card/50 backdrop-blur-xl border border-white/5 shadow-2xl px-4 md:px-6 mb-3">
        <div className="flex items-center gap-3 md:gap-4 min-w-0">
          <div className="bg-ag-danger/95 p-2.5 rounded-2xl shadow-lg shadow-red-900/30 shrink-0">
            <Scan size={22} className="text-white" />
          </div>
          <div className="min-w-0">
            <h1 className="text-lg md:text-2xl font-black tracking-tight text-white leading-none">
              LIVE MONITORING
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <span className="w-2 h-2 bg-ag-success rounded-full animate-pulse" />
              <p className="text-[10px] md:text-[11px] text-ag-success font-black uppercase tracking-[0.26em] truncate">
                Secure Node 01 // Active
              </p>
            </div>
          </div>
        </div>

        <button className="p-2.5 md:p-3 bg-white/5 hover:bg-white/10 rounded-full transition-all text-gray-300 hover:text-white border border-white/5">
          <Bell size={20} />
        </button>
      </header>

      {/* Camera-first Layout */}
      <div className="grid grid-rows-[minmax(0,1fr)_auto] gap-3 h-[calc(100vh-4.5rem)] min-h-0">
        <div
          ref={videoContainerRef}
          className="relative group rounded-[2.5rem] overflow-hidden border border-white/8 shadow-[0_30px_90px_rgba(0,0,0,0.45)] bg-black ring-1 ring-white/10 min-h-0"
        >
          {/* Compact Glass Overlays */}
          <div className="absolute left-4 right-4 top-4 z-40 pointer-events-none flex flex-col gap-3">
            <div className="flex items-start justify-between gap-3">
              <div className="max-w-[65%] rounded-2xl border border-white/10 bg-black/55 backdrop-blur-xl px-4 py-3 shadow-xl">
                <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.28em] text-white/70 mb-1">
                  <span className="w-2 h-2 rounded-full bg-ag-danger animate-pulse" />
                  Live Feed
                </div>
                <div className="text-sm md:text-base font-bold text-white truncate">
                  <Radio
                    size={14}
                    className="inline-block mr-2 text-ag-danger align-[-2px]"
                  />
                  {cameras.find((c) => c.camera_id === selectedCamera)
                    ?.camera_name || "PROVISIONING..."}
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-black/55 backdrop-blur-xl px-4 py-3 shadow-xl flex items-center gap-4 shrink-0">
                <div className="text-center min-w-[54px]">
                  <div className="text-[9px] uppercase tracking-widest text-gray-500 font-bold">
                    FPS
                  </div>
                  <div className="text-lg font-black text-ag-success font-mono leading-none mt-1">
                    {fps || 30}
                  </div>
                </div>
                <div className="w-px h-10 bg-white/10" />
                <div className="text-center min-w-[64px]">
                  <div className="text-[9px] uppercase tracking-widest text-gray-500 font-bold">
                    Objects
                  </div>
                  <div className="text-lg font-black text-ag-warning font-mono leading-none mt-1">
                    {detectionCount}
                  </div>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 justify-between items-center">
              <div className="inline-flex items-center gap-2 rounded-full border border-ag-danger/40 bg-ag-danger/85 px-4 py-2 text-[10px] md:text-[11px] font-black uppercase tracking-[0.24em] text-white shadow-lg shadow-red-900/20">
                <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
                Live Analytics Active
              </div>

              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/40 px-3 py-2 text-[10px] md:text-[11px] font-bold text-gray-200 backdrop-blur-xl">
                <ChevronsRight size={14} className="text-ag-success" />
                Monitoring secured and streaming
              </div>
            </div>
          </div>

          {/* Floating Violation Alerts */}
          <div className="absolute left-1/2 top-[18%] z-50 flex w-full -translate-x-1/2 flex-col items-center gap-2 pointer-events-none px-3 md:px-6">
            {alerts.map((alert, idx) => (
              <div
                key={idx}
                className="max-w-[92%] rounded-2xl border border-ag-danger/40 bg-ag-danger/15 backdrop-blur-2xl px-4 py-3 flex items-center gap-3 animate-in slide-in-from-top zoom-in duration-300 shadow-[0_0_30px_rgba(239,68,68,0.18)]"
              >
                <div className="bg-ag-danger/90 p-2.5 rounded-xl shadow-lg">
                  <ShieldAlert size={20} className="text-white" />
                </div>
                <div>
                  <p className="text-[9px] font-black text-ag-danger uppercase tracking-[0.3em]">
                    Critical Alert
                  </p>
                  <h4 className="text-base md:text-lg font-black text-white uppercase tracking-tighter">
                    {alert.type} DETECTED
                  </h4>
                </div>
              </div>
            ))}
          </div>

          {/* Video Stream Implementation */}
          {selectedCamera ? (
            <img
              ref={videoRef}
              src={
                isPaused
                  ? ""
                  : `http://127.0.0.1:8000/api/v1/cameras/${selectedCamera}/stream`
              }
              alt="AeroGuard Engine"
              className={`absolute inset-0 h-full w-full object-cover transition-all duration-700 ${isPaused ? "scale-[1.03] blur-sm opacity-25" : "scale-100 opacity-100"}`}
            />
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-ag-dark">
              <Loader2 className="animate-spin text-ag-danger mb-4" size={52} />
              <p className="text-gray-500 font-black uppercase tracking-[0.35em] text-[11px]">
                Awaiting Encrypted Link
              </p>
            </div>
          )}

          {/* Compact Control Bar */}
          <div className="absolute left-1/2 bottom-4 z-50 flex -translate-x-1/2 items-center gap-3 rounded-full border border-white/10 bg-black/55 px-4 py-3 shadow-2xl backdrop-blur-2xl opacity-95 transition-all duration-300 group-hover:scale-[1.01]">
            <button
              onClick={() => setIsPaused(!isPaused)}
              className="p-3.5 bg-white/5 hover:bg-ag-danger rounded-full text-white transition-all hover:scale-105"
            >
              {isPaused ? (
                <Play size={20} fill="white" />
              ) : (
                <Pause size={20} fill="white" />
              )}
            </button>
            <div className="w-px h-8 bg-white/10"></div>
            <button
              onClick={takeSnapshot}
              className="p-3.5 bg-white/5 hover:bg-ag-success rounded-full text-white transition-all hover:scale-105"
              title="Capture Incident"
            >
              <SnapshotIcon size={20} />
            </button>
            <button
              onClick={() => alert("Admin Drawing Mode")}
              className="p-3.5 bg-white/5 hover:bg-blue-600 rounded-full text-white transition-all hover:scale-105"
            >
              <Box size={20} />
            </button>
            <div className="w-px h-8 bg-white/10"></div>
            <button
              onClick={toggleFullscreen}
              className="p-3.5 bg-white/5 hover:bg-white/10 rounded-full text-white transition-all hover:scale-105"
            >
              {isFullscreen ? <Minimize size={20} /> : <Maximize size={20} />}
            </button>
          </div>

          {/* Recording Indicator */}
          <div className="absolute bottom-4 right-4 z-30 flex items-center gap-2 rounded-full border border-white/10 bg-black/50 px-3 py-2 backdrop-blur-xl">
            <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse shadow-[0_0_10px_red]"></div>
            <span className="text-[10px] font-black text-white tracking-widest uppercase">
              Recording
            </span>
          </div>
        </div>

        {/* Camera Strip */}
        <div className="rounded-[1.8rem] border border-white/5 bg-ag-card/35 px-3 py-3 backdrop-blur-sm shadow-xl">
          <div className="flex gap-3 overflow-x-auto pb-1 custom-scrollbar">
            {cameras.map((cam) => (
              <button
                key={cam.camera_id}
                onClick={() => {
                  setSelectedCamera(cam.camera_id);
                  setIsPaused(false);
                  startCameraAI(cam.camera_id);
                }}
                className={`px-5 py-3 rounded-2xl text-[11px] font-black transition-all border flex items-center gap-3 whitespace-nowrap tracking-widest
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
