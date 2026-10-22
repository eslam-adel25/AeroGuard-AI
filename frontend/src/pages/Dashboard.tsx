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
  type ZoneData,
} from "../services/api";
import { createSocket } from "../services/socket";
import type { WSMessage } from "../services/socket";
import directionLeftImage from "../assets/images/tripwire/direction-left.png";
import directionRightImage from "../assets/images/tripwire/direction-right.png";
import { useAlertAudio } from "../components/useAlertAudio";
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
  Volume2,
  VolumeX,
  X,
} from "lucide-react";
import { motion } from "framer-motion";

function formatLocalDateTime(date: Date, language: string) {
  return new Intl.DateTimeFormat(language, {
    month: "2-digit",
    day: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  }).format(date);
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
  status?: string;
}

const EMPTY_ALARM_SOURCES: string[] = [];

type DrawingMode = "restricted" | "direction" | "tripwire";
type DrawingPointsByType = Record<DrawingMode, Array<[number, number]>>;
type TripwireDirection = "left" | "right";
type TripwireState = {
  current_occupancy: number;
  remaining_group_count: number;
  over_limit_count: number;
  occupancy_confirmation_required: boolean;
};

type AnnotationAction =
  | { type: "point-added"; mode: DrawingMode }
  | { type: "zone-added"; zone: ZoneData }
  | { type: "zone-deleted"; zone: ZoneData; index: number; persisted: boolean };

const cloneZones = (zones: ZoneData[]) =>
  zones.map((zone) => ({
    ...zone,
    polygon_coords: zone.polygon_coords.map(
      ([x, y]) => [x, y] as [number, number],
    ),
  }));

const toZoneCreatePayload = (zone: ZoneData) => ({
  zone_name: zone.zone_name,
  zone_type: zone.zone_type,
  polygon_coords: zone.polygon_coords,
  video_width: zone.video_width,
  video_height: zone.video_height,
  tripwire_allowed_group_size: zone.tripwire_allowed_group_size,
  tripwire_initial_occupancy: zone.tripwire_initial_occupancy,
  tripwire_entry_direction: zone.tripwire_entry_direction,
});

const zoneTypeForDrawingMode = (mode: DrawingMode) =>
  mode === "restricted"
    ? "Restricted Area"
    : mode === "direction"
      ? "Direction"
      : "Tripwire";

const emptyDrawingPoints = (): DrawingPointsByType => ({
  restricted: [],
  direction: [],
  tripwire: [],
});

const alertBadgeLabel = (alert: AlertData, t: (key: string) => string) => {
  const typeLabel = alert.type?.trim();
  if (!typeLabel) return t("dashboard.alertBadgeDefault");
  if (/restricted/i.test(typeLabel)) return t("dashboard.alertBadgeRestricted");
  return typeLabel;
};

const hasCriticalAlerts = (alerts: AlertData[]) =>
  alerts.some((alert) => /critical/i.test(alert.priority || ""));

const isCameraRunning = (status?: string) =>
  status === "Processing" || status === "Running";

interface DashboardProps {
  onAlertBadgeClick?: () => void;
}

const Dashboard = ({ onAlertBadgeClick }: DashboardProps) => {
  const { t, i18n } = useTranslation();
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
  const {
    alarmStateByCamera,
    mutedCameraIds,
    toggleCameraMute,
  } = useAlertAudio();
  const [localDateTime, setLocalDateTime] = useState(() =>
    formatLocalDateTime(new Date(), i18n.language),
  );
  const [cameraStatus, setCameraStatus] = useState<
    "Running" | "Offline" | "Processing"
  >("Offline");
  const selectedCameraName =
    cameras.find((c) => c.camera_id === selectedCamera)?.camera_name || "";
  const selectedAlarmState = selectedCamera
    ? alarmStateByCamera[selectedCamera]
    : undefined;
  const alarmActive = selectedAlarmState?.active ?? false;
  const alarmSources = selectedAlarmState?.sources ?? EMPTY_ALARM_SOURCES;

  const videoContainerRef = useRef<HTMLDivElement>(null);
  const videoWrapperRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLImageElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const selectedCameraRef = useRef<string | null>(null);
  const streamToken = getStoredAuthToken();
  const [isDrawing, setIsDrawing] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [drawingPointsByType, setDrawingPointsByType] =
    useState<DrawingPointsByType>(emptyDrawingPoints);
  const [savedZones, setSavedZones] = useState<ZoneData[]>([]);
  const [editingZones, setEditingZones] = useState<ZoneData[]>([]);
  const [drawingMode, setDrawingMode] = useState<DrawingMode>("restricted");
  const [drawingInstructions, setDrawingInstructions] = useState<string>("");
  const [hoverPoint, setHoverPoint] = useState<[number, number] | null>(null);
  const [annotationHistory, setAnnotationHistory] = useState<
    AnnotationAction[]
  >([]);
  const [isSavingAnnotations, setIsSavingAnnotations] = useState(false);
  const [tripwireStates, setTripwireStates] = useState<
    Record<string, TripwireState>
  >({});
  const [tripwireDraftPoints, setTripwireDraftPoints] = useState<
    [number, number][] | null
  >(null);
  const [tripwireModalOpen, setTripwireModalOpen] = useState(false);
  const [tripwireForm, setTripwireForm] = useState({
    name: "",
    allowedGroupSize: "",
    currentOccupancy: "",
    direction: "" as TripwireDirection | "",
  });
  const [confirmationZone, setConfirmationZone] = useState<ZoneData | null>(
    null,
  );
  const zoneRequestVersionRef = useRef(0);
  const editorCameraRef = useRef<string | null>(null);
  const editorActive = isDrawing;
  const canvasZones = editorActive ? editingZones : savedZones;
  const drawingPoints = drawingPointsByType[drawingMode];
  const filteredSavedZones = editingZones.filter(
    (zone) => zone.zone_type === zoneTypeForDrawingMode(drawingMode),
  );

  // --- AI Operations ---
  const stopCameraSession = useCallback(async (id: string | null) => {
    if (!id) return;
    try {
      await cameraService.stop(id);
      if (selectedCameraRef.current === id) {
        setCameraStatus("Offline");
      }
      setCameras((current) =>
        current.map((camera) =>
          camera.camera_id === id ? { ...camera, status: "Offline" } : camera,
        ),
      );
    } catch {
      console.log("AI stopping...");
    }
  }, []);

  const startCameraAI = useCallback(async (id: string) => {
    setCameraStatus("Processing");
    setCameras((current) =>
      current.map((camera) =>
        camera.camera_id === id
          ? { ...camera, status: "Processing" }
          : camera,
      ),
    );
    try {
      await cameraService.start(id);
    } catch {
      console.log("AI initializing...");
      try {
        const response = await cameraService.getAll();
        const updatedCameras = response.data as CameraData[];
        const statuses = new Map(
          updatedCameras.map((camera) => [camera.camera_id, camera.status]),
        );
        setCameras((current) =>
          current.map((camera) =>
            camera.camera_id === id
              ? {
                  ...camera,
                  status: isCameraRunning(statuses.get(id))
                    ? statuses.get(id)
                    : "Offline",
                }
              : statuses.has(camera.camera_id)
                ? { ...camera, status: statuses.get(camera.camera_id) }
                : camera,
          ),
        );
        if (selectedCameraRef.current === id) {
          const status = statuses.get(id);
          const running = isCameraRunning(status);
          setCameraStatus(
            running ? (status as "Running" | "Processing") : "Offline",
          );
          setIsPaused(!running);
        }
      } catch {
        setCameras((current) =>
          current.map((camera) =>
            camera.camera_id === id ? { ...camera, status: "Offline" } : camera,
          ),
        );
        if (selectedCameraRef.current === id) {
          setCameraStatus("Offline");
          setIsPaused(true);
        }
      }
    }
  }, []);

  const handleCameraSelection = useCallback(
    (id: string, status?: string) => {
      setSelectedCamera(id);
      selectedCameraRef.current = id;
      localStorage.setItem("ag_selected_camera", id);
      const running = isCameraRunning(status);
      setCameraStatus(running ? (status as "Running" | "Processing") : "Offline");
      setIsPaused(!running);
    },
    [],
  );

  useEffect(() => {
    selectedCameraRef.current = selectedCamera;
  }, [selectedCamera]);

  const fetchZones = useCallback(async (cameraId: string, syncDraft = true) => {
    const requestVersion = ++zoneRequestVersionRef.current;
    try {
      const response = await cameraService.getZones(cameraId);
      if (
        requestVersion !== zoneRequestVersionRef.current ||
        selectedCameraRef.current !== cameraId
      ) {
        return null;
      }
      const zones = response.data as ZoneData[];
      setSavedZones(zones);
      setTripwireStates((current) => {
        const next = { ...current };
        zones
          .filter((zone) => zone.zone_type.toLowerCase().includes("tripwire"))
          .forEach((zone) => {
            const occupancy = zone.tripwire_current_occupancy ?? 0;
            const allowed = zone.tripwire_allowed_group_size ?? 0;
            next[zone.zone_id] = {
              current_occupancy: occupancy,
              remaining_group_count: Math.max(0, allowed - occupancy),
              over_limit_count: Math.max(0, occupancy - allowed),
              occupancy_confirmation_required:
                zone.tripwire_requires_confirmation ?? false,
            };
          });
        return next;
      });
      const needsConfirmation = zones.find(
        (zone) =>
          zone.zone_type.toLowerCase().includes("tripwire") &&
          zone.tripwire_requires_confirmation,
      );
      if (needsConfirmation) {
        setConfirmationZone(needsConfirmation);
        setTripwireForm({
          name: needsConfirmation.zone_name || "Tripwire",
          allowedGroupSize: String(
            needsConfirmation.tripwire_allowed_group_size ?? "",
          ),
          currentOccupancy: "",
          direction: needsConfirmation.tripwire_entry_direction ?? "",
        });
      }
      if (syncDraft) {
        setEditingZones(cloneZones(zones));
      }
      return zones;
    } catch (error) {
      if (
        requestVersion !== zoneRequestVersionRef.current ||
        selectedCameraRef.current !== cameraId
      ) {
        return null;
      }
      console.error("Failed to load zones:", error);
      setSavedZones([]);
      setEditingZones([]);
      return null;
    }
  }, []);

  useEffect(() => {
    setLocalDateTime(formatLocalDateTime(new Date(), i18n.language));
    const interval = window.setInterval(() => {
      setLocalDateTime(formatLocalDateTime(new Date(), i18n.language));
    }, 1000);
    return () => window.clearInterval(interval);
  }, [i18n.language]);

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
        if (message.data.camera_id) {
          setCameras((current) =>
            current.map((camera) =>
              camera.camera_id === message.data.camera_id
                ? { ...camera, status: "Running" }
                : camera,
            ),
          );
          if (message.data.camera_id === selectedCameraRef.current) {
            setIsPaused(false);
          }
        }
      }

      if (message.event === "camera_status") {
        const cameraId = message.data.camera_id;
        const status =
          (message.data.status as "Running" | "Offline" | "Processing") ||
          "Offline";
        if (cameraId) {
          setCameras((current) =>
            current.map((camera) =>
              camera.camera_id === cameraId
                ? { ...camera, status }
                : camera,
            ),
          );
        }
        if (cameraId === selectedCameraRef.current) {
          setCameraStatus(status);
          setIsPaused(!isCameraRunning(status));
        }
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

      if (message.event === "tripwire_state") {
        if (message.data.camera_id !== selectedCameraRef.current) return;
        setTripwireStates((current) => ({
          ...current,
          [message.data.zone_id]: {
            current_occupancy: message.data.current_occupancy,
            remaining_group_count: message.data.remaining_group_count,
            over_limit_count: message.data.over_limit_count,
            occupancy_confirmation_required:
              message.data.occupancy_confirmation_required,
          },
        }));
      }

    };

    const socket = createSocket(handleMessage);

    const init = async () => {
      try {
        const res = await cameraService.getAll();
        const data = res.data as CameraData[];
        setCameras(data);
        if (data.length > 0) {
          const storedCameraId = localStorage.getItem("ag_selected_camera");
          const selectedCamera =
            data.find((camera) => camera.camera_id === storedCameraId) ??
            data.find((camera) => isCameraRunning(camera.status)) ??
            data[0];
          handleCameraSelection(
            selectedCamera.camera_id,
            selectedCamera.status,
          );
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
        if (canvasCoords.length >= 2) {
          const [first, second] = canvasCoords;
          const midpointX = (first[0] + second[0]) / 2;
          const midpointY = (first[1] + second[1]) / 2;
          const state = tripwireStates[zone.zone_id];
          if (state?.occupancy_confirmation_required) {
            const pendingLabel = t("dashboard.tripwire.confirmationPending");
            ctx.font = "600 12px sans-serif";
            const pendingWidth = ctx.measureText(pendingLabel).width;
            const pendingX = Math.max(
              4,
              Math.min(
                midpointX - pendingWidth / 2,
                canvas.width / ratio - pendingWidth - 4,
              ),
            );
            const pendingY = Math.max(18, midpointY - 10);
            ctx.fillStyle = "rgba(5, 12, 24, 0.86)";
            ctx.fillRect(pendingX - 5, pendingY - 14, pendingWidth + 10, 20);
            ctx.fillStyle = "#fcd34d";
            ctx.fillText(pendingLabel, pendingX, pendingY);
            return;
          }

          const occupancy =
            state?.current_occupancy ?? zone.tripwire_current_occupancy ?? 0;
          const allowed = zone.tripwire_allowed_group_size ?? 0;
          const counters = [
            {
              value:
                state?.over_limit_count ?? Math.max(0, occupancy - allowed),
              color: "#f87171",
            },
            {
              value: occupancy,
              color: "#4ade80",
            },
            {
              value:
                state?.remaining_group_count ??
                Math.max(0, allowed - occupancy),
              color: "#60a5fa",
            },
          ];
          ctx.font = "700 16px sans-serif";
          const leftToRight =
            Math.abs(second[0] - first[0]) >= Math.abs(second[1] - first[1])
              ? [first, second].sort((a, b) => a[0] - b[0])
              : [first, second].sort((a, b) => a[1] - b[1]);
          const anchors: [[number, number], [number, number], [number, number]] =
            [
              leftToRight[0],
              [midpointX, midpointY],
              leftToRight[1],
            ];
          const canvasWidth = canvas.width / ratio;
          const canvasHeight = canvas.height / ratio;
          counters.forEach((counter, index) => {
            const text = String(counter.value);
            const textWidth = ctx.measureText(text).width;
            const [anchorX, anchorY] = anchors[index];
            const counterX = Math.max(
              textWidth / 2 + 2,
              Math.min(anchorX, canvasWidth - textWidth / 2 - 2),
            );
            const labelY = Math.max(
              18,
              Math.min(anchorY - 10, canvasHeight - 4),
            );
            ctx.fillStyle = counter.color;
            ctx.shadowColor = "rgba(0, 0, 0, 0.75)";
            ctx.shadowBlur = 3;
            ctx.textAlign = "center";
            ctx.fillText(text, counterX, labelY);
          });
          ctx.textAlign = "start";
          ctx.shadowColor = "transparent";
          ctx.shadowBlur = 0;
        }
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

    canvasZones.forEach((zone) =>
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
    canvasZones,
    getSavedZoneCanvasCoords,
    mapNormalizedToCanvasCoords,
    t,
    tripwireStates,
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
      editorCameraRef.current = selectedCamera;
      setIsDrawing(false);
      setIsSidebarOpen(true);
      setDrawingPointsByType(emptyDrawingPoints());
      setAnnotationHistory([]);
      setEditingZones([]);
      setConfirmationZone(null);
      setTripwireModalOpen(false);
      void fetchZones(selectedCamera);
    } else {
      editorCameraRef.current = null;
      setSavedZones([]);
      setEditingZones([]);
      setDrawingPointsByType(emptyDrawingPoints());
      setAnnotationHistory([]);
      setConfirmationZone(null);
      setTripwireModalOpen(false);
    }
  }, [selectedCamera, fetchZones]);

  const enterDrawingMode = useCallback(() => {
    const cameraId = selectedCameraRef.current;
    if (!cameraId) return;
    editorCameraRef.current = cameraId;
    setEditingZones(cloneZones(savedZones));
    setDrawingPointsByType(emptyDrawingPoints());
    setAnnotationHistory([]);
    setDrawingMode("restricted");
    setIsDrawing(true);
    setIsSidebarOpen(true);
    setDrawingInstructions(t("dashboard.drawingInstructions.initial"));
  }, [savedZones, t]);

  const startNewRegion = useCallback(() => {
    if (!selectedCameraRef.current) return;
    setDrawingPointsByType((prev) => ({
      ...prev,
      [drawingMode]: [],
    }));
    setAnnotationHistory((prev) =>
      prev.filter(
        (action) =>
          action.type !== "point-added" || action.mode !== drawingMode,
      ),
    );
    setIsDrawing(true);
    setIsSidebarOpen(true);
    setHoverPoint(null);
    setDrawingInstructions(t("dashboard.drawingInstructions.initial"));
  }, [drawingMode, t]);

  const exitDrawingMode = useCallback(() => {
    setIsDrawing(false);
    setIsSidebarOpen(true);
    setEditingZones(cloneZones(savedZones));
    setDrawingPointsByType(emptyDrawingPoints());
    setAnnotationHistory([]);
    setDrawingInstructions("");
    setHoverPoint(null);
  }, [savedZones]);

  const undoLastAction = useCallback(async () => {
    const lastAction = annotationHistory[annotationHistory.length - 1];
    if (!lastAction) return;

    if (lastAction.type === "point-added") {
      setDrawingPointsByType((prev) => ({
        ...prev,
        [lastAction.mode]: prev[lastAction.mode].slice(0, -1),
      }));
    } else if (lastAction.type === "zone-added") {
      setEditingZones((prev) =>
        prev.filter((zone) => zone.zone_id !== lastAction.zone.zone_id),
      );
    } else {
      let restoredZone = cloneZones([lastAction.zone])[0];
      if (lastAction.persisted && selectedCamera) {
        try {
          const response = await cameraService.addZone(
            selectedCamera,
            toZoneCreatePayload(restoredZone),
          );
          restoredZone = response.data;
          await fetchZones(selectedCamera, false);
        } catch (error) {
          console.error("Failed to restore zone:", error);
          return;
        }
      }
      setEditingZones((prev) => {
        const next = [...prev];
        next.splice(lastAction.index, 0, restoredZone);
        return next;
      });
    }
    setAnnotationHistory((prev) => prev.slice(0, -1));
    setDrawingInstructions(t("dashboard.drawingInstructions.removed"));
    setTimeout(
      () => setDrawingInstructions(t("dashboard.drawingInstructions.initial")),
      1800,
    );
  }, [annotationHistory, fetchZones, selectedCamera, t]);

  const deleteZone = useCallback(
    async (zoneId: string) => {
      const index = editingZones.findIndex((zone) => zone.zone_id === zoneId);
      if (index < 0) return;
      const zone = editingZones[index];
      const persisted = !zone.zone_id.startsWith("draft-");
      if (persisted && selectedCamera) {
        try {
          await cameraService.deleteZone(selectedCamera, zoneId);
          await fetchZones(selectedCamera, false);
        } catch (error) {
          console.error("Failed to delete zone:", error);
          return;
        }
      }
      setEditingZones((prev) => prev.filter((item) => item.zone_id !== zoneId));
      if (persisted) {
        setSavedZones((prev) => prev.filter((item) => item.zone_id !== zoneId));
      }
      setAnnotationHistory((history) => [
        ...history,
        {
          type: "zone-deleted",
          zone: cloneZones([zone])[0],
          index,
          persisted,
        },
      ]);
    },
    [editingZones, fetchZones, selectedCamera],
  );

  const saveAnnotations = useCallback(async () => {
    if (!selectedCamera || isSavingAnnotations) return;
    setIsSavingAnnotations(true);
    try {
      setDrawingInstructions(
        t("dashboard.drawingInstructions.saving") ||
          t("dashboard.drawingInstructions.saved"),
      );
      const selectedZoneType = zoneTypeForDrawingMode(drawingMode);
      const savedForMode = savedZones.filter(
        (zone) => zone.zone_type === selectedZoneType,
      );
      const editingForMode = editingZones.filter(
        (zone) => zone.zone_type === selectedZoneType,
      );
      const savedIds = new Set(savedForMode.map((zone) => zone.zone_id));
      const editingIds = new Set(editingForMode.map((zone) => zone.zone_id));
      const zonesToDelete = savedForMode.filter(
        (zone) => !editingIds.has(zone.zone_id),
      );
      const zonesToCreate = editingForMode.filter(
        (zone) => !savedIds.has(zone.zone_id),
      );

      for (const zone of zonesToDelete) {
        await cameraService.deleteZone(selectedCamera, zone.zone_id);
      }
      for (const zone of zonesToCreate) {
        const response = await cameraService.addZone(
          selectedCamera,
          toZoneCreatePayload(zone),
        );
        setEditingZones((prev) =>
          prev.map((item) =>
            item.zone_id === zone.zone_id ? response.data : item,
          ),
        );
      }
      const freshZones = await fetchZones(selectedCamera, false);
      if (!freshZones) {
        throw new Error("Unable to refresh saved annotations");
      }
      const freshForMode = freshZones.filter(
        (zone) => zone.zone_type === selectedZoneType,
      );
      setEditingZones((prev) => [
        ...prev.filter((zone) => zone.zone_type !== selectedZoneType),
        ...cloneZones(freshForMode),
      ]);
      setDrawingPointsByType((prev) => ({
        ...prev,
        [drawingMode]: [],
      }));
      setAnnotationHistory((prev) =>
        prev.filter(
          (action) =>
            action.type !== "point-added" || action.mode !== drawingMode,
        ),
      );
      setDrawingInstructions(t("dashboard.drawingInstructions.saved"));
    } catch (err) {
      console.error("Failed to save annotations:", err);
      setDrawingInstructions(
        t("dashboard.drawingInstructions.saveFailed") ||
          "Failed to save annotations",
      );
    } finally {
      setIsSavingAnnotations(false);
      setHoverPoint(null);
      setTimeout(() => setDrawingInstructions(""), 2200);
    }
  }, [
    drawingMode,
    editingZones,
    fetchZones,
    isSavingAnnotations,
    savedZones,
    selectedCamera,
    t,
  ]);

  const finishDrawing = useCallback(
    (points = drawingPoints) => {
      if (points.length === 0 || !selectedCamera) return;
      const vid = videoRef.current;
      if (!vid) return;
      const zoneType = zoneTypeForDrawingMode(drawingMode);
      const pointRequirement = drawingMode === "restricted" ? 3 : 2;
      if (
        drawingMode === "restricted"
          ? points.length < pointRequirement
          : points.length !== pointRequirement
      ) {
        setDrawingInstructions(
          drawingMode === "restricted"
            ? t("dashboard.drawingInstructions.restrictedMinPoints")
            : `${zoneType} requires exactly 2 points.`,
        );

        return;
      }
      if (drawingMode === "tripwire" && !tripwireModalOpen) {
        setTripwireDraftPoints(points);
        setTripwireForm({
          name: "",
          allowedGroupSize: "",
          currentOccupancy: "",
          direction: "",
        });
        setTripwireModalOpen(true);
        return;
      }
      const zone = {
        zone_id: `draft-${crypto.randomUUID()}`,
        zone_name:
          drawingMode === "tripwire" && tripwireForm.name.trim()
            ? tripwireForm.name.trim()
            : `${t("dashboard.inCameraAnnotation")} - ${zoneType}`,
        zone_type: zoneType,
        polygon_coords: cloneZones([
          {
            zone_id: "draft",
            zone_name: "draft",
            zone_type: zoneType,
            polygon_coords: points,
          },
        ])[0].polygon_coords,
        video_width: vid.naturalWidth || undefined,
        video_height: vid.naturalHeight || undefined,
        ...(drawingMode === "tripwire"
          ? {
              tripwire_allowed_group_size: Number(
                tripwireForm.allowedGroupSize,
              ),
              tripwire_initial_occupancy: Number(
                tripwireForm.currentOccupancy,
              ),
              tripwire_entry_direction: tripwireForm.direction as TripwireDirection,
            }
          : {}),
      } satisfies ZoneData;
      setEditingZones((prev) => [...prev, zone]);
      setAnnotationHistory((prev) => [
        ...prev.filter(
          (action) =>
            action.type !== "point-added" || action.mode !== drawingMode,
        ),
        { type: "zone-added", zone: cloneZones([zone])[0] },
      ]);
      setDrawingPointsByType((prev) => ({
        ...prev,
        [drawingMode]: [],
      }));
      setHoverPoint(null);
      setDrawingInstructions(t("dashboard.drawingInstructions.saved"));
    },
    [
      drawingMode,
      drawingPoints,
      selectedCamera,
      t,
      tripwireForm,
      tripwireModalOpen,
    ],
  );

  const confirmTripwireConfiguration = useCallback(() => {
    const name = tripwireForm.name.trim();
    const allowed = Number(tripwireForm.allowedGroupSize);
    const occupancy = Number(tripwireForm.currentOccupancy);
    if (
      !name ||
      name.length > 100 ||
      !Number.isInteger(allowed) ||
      allowed <= 0 ||
      !Number.isInteger(occupancy) ||
      occupancy < 0 ||
      !tripwireForm.direction
    ) {
      setDrawingInstructions(t("dashboard.tripwire.invalidConfiguration"));
      return;
    }
    if (confirmationZone && selectedCamera) {
      void cameraService
        .confirmTripwireOccupancy(
          selectedCamera,
          confirmationZone.zone_id,
          occupancy,
          allowed,
          name,
        )
        .then((response) => {
          const confirmed = response.data;
          setConfirmationZone(null);
          setTripwireModalOpen(false);
          setTripwireForm({
            name: "",
            allowedGroupSize: "",
            currentOccupancy: "",
            direction: "",
          });
          setSavedZones((current) =>
            current.map((zone) =>
              zone.zone_id === confirmed.zone_id ? confirmed : zone,
            ),
          );
          setEditingZones((current) =>
            current.map((zone) =>
              zone.zone_id === confirmed.zone_id ? confirmed : zone,
            ),
          );
          setTripwireStates((current) => ({
            ...current,
            [confirmed.zone_id]: {
              current_occupancy: occupancy,
              remaining_group_count: Math.max(
                0,
                (confirmed.tripwire_allowed_group_size ?? allowed) - occupancy,
              ),
              over_limit_count: Math.max(
                0,
                occupancy - (confirmed.tripwire_allowed_group_size ?? allowed),
              ),
              occupancy_confirmation_required: false,
            },
          }));
        })
        .catch((error) => {
          console.error("Failed to confirm tripwire occupancy:", error);
          setDrawingInstructions(t("dashboard.tripwire.confirmationFailed"));
        });
      return;
    }
    if (tripwireDraftPoints) {
      setTripwireModalOpen(false);
      finishDrawing(tripwireDraftPoints);
      setTripwireDraftPoints(null);
      setTripwireForm({
        name: "",
        allowedGroupSize: "",
        currentOccupancy: "",
        direction: "",
      });
    }
  }, [
    confirmationZone,
    finishDrawing,
    selectedCamera,
    t,
    tripwireDraftPoints,
    tripwireForm,
  ]);

  const onCanvasClick = (event: MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    const normalized = getNormalizedVideoCoords(event);
    if (!normalized) return;
    setDrawingPointsByType((prev) => ({
      ...prev,
      [drawingMode]: [...prev[drawingMode], normalized],
    }));
    setAnnotationHistory((prev) => [
      ...prev,
      { type: "point-added", mode: drawingMode },
    ]);
  };

  const onCanvasDoubleClick = (event: MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    event.preventDefault();
    finishDrawing(drawingPoints.slice(0, -1));
  };

  const onCanvasContextMenu = (event: MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    event.preventDefault();
    undoLastAction();
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
        finishDrawing();
      }
      if (event.key === "Backspace") {
        event.preventDefault();
        undoLastAction();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isDrawing, finishDrawing, exitDrawingMode, undoLastAction]);

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
                  {t(`dashboard.status.${cameraStatus.toLowerCase()}`)}
                </span>

                <span className="text-white/50">|</span>
                <span className="flex items-center gap-1 text-white/90">
                  {t("common.fps")}:{" "}
                  <span className="font-black text-ag-success">{fps}</span>
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

              {alerts.length > 0 ? (
                <button
                  type="button"
                  onClick={onAlertBadgeClick}
                  className="inline-flex items-center gap-2 rounded-[18px] border border-white/15 bg-black/25 px-3 py-1.5 shadow-[0_10px_30px_rgba(0,0,0,0.18)] backdrop-blur-md text-[13px] font-semibold text-white whitespace-nowrap pointer-events-auto transition hover:bg-white/5"
                >
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-ag-danger/90 text-white">
                    <ShieldAlert size={14} />
                  </div>
                  <span>
                    {alerts.length === 1
                      ? alertBadgeLabel(alerts[0], t)
                      : `${alerts.length} ${t(
                          hasCriticalAlerts(alerts)
                            ? "dashboard.alerts.critical"
                            : "dashboard.alerts.generic",
                        )}`}
                  </span>
                </button>
              ) : null}

              {alarmActive ? (
                alarmSources.length > 0 ? (
                  <span className="text-[12px] text-red-200/80">
                    {`${t("dashboard.alerts.sources")}: ${alarmSources.join(", ")}`}
                  </span>
                ) : null
              ) : null}

              <div className="inline-flex items-center gap-3 rounded-[18px] border border-white/15 bg-black/25 px-3 py-1.5 shadow-[0_10px_30px_rgba(0,0,0,0.18)] backdrop-blur-md text-[14px] font-semibold text-white whitespace-nowrap">
                {localDateTime}
              </div>
            </div>

              {tripwireModalOpen ? (
                <div className="pointer-events-none fixed inset-0 z-[100] flex items-center justify-center p-4">
                  <form
                    onSubmit={(event) => {
                      event.preventDefault();
                      confirmTripwireConfiguration();
                    }}
                    className="pointer-events-auto relative max-h-[calc(100vh-2rem)] w-full max-w-md space-y-5 overflow-y-auto rounded-2xl border border-white/15 bg-[#0c1322] p-6 text-white shadow-2xl"
                  >
                    <button
                      type="button"
                      aria-label="Close TRIPWIRE configuration"
                      onClick={() => {
                        setTripwireModalOpen(false);
                        if (!confirmationZone) {
                          setTripwireDraftPoints(null);
                          setDrawingPointsByType((current) => ({
                            ...current,
                            tripwire: [],
                          }));
                          setAnnotationHistory((history) =>
                            history.filter(
                              (action) =>
                                action.type !== "point-added" ||
                                action.mode !== "tripwire",
                            ),
                          );
                        }
                      }}
                      className="absolute right-4 top-4 rounded-full p-1 text-gray-400 transition hover:bg-white/10 hover:text-white"
                    >
                      <X size={18} />
                    </button>
                    <div>
                      <p className="text-[10px] uppercase tracking-[0.3em] text-gray-400">
                        TRIPWIRE
                      </p>
                      <h2 className="mt-1 text-lg font-bold">
                        {confirmationZone
                          ? t("dashboard.tripwire.confirmTitle")
                          : t("dashboard.tripwire.configureTitle")}
                      </h2>
                      {confirmationZone ? (
                        <p className="mt-2 text-xs text-amber-200">
                          {t("dashboard.tripwire.confirmDescription")}
                        </p>
                      ) : null}
                    </div>
                    <label className="block text-xs text-gray-300">
                      {t("dashboard.tripwire.name")}
                      <input
                        type="text"
                        maxLength={100}
                        required
                        value={tripwireForm.name}
                        onChange={(event) =>
                          setTripwireForm((current) => ({
                            ...current,
                            name: event.target.value,
                          }))
                        }
                        placeholder={t("dashboard.tripwire.namePlaceholder")}
                        className="mt-2 w-full rounded-lg border border-white/15 bg-black/30 px-3 py-2 text-white"
                      />
                    </label>
                    <label className="block text-xs text-gray-300">
                      {t("dashboard.tripwire.allowedGroupSize")}
                      <input
                        type="number"
                        min="1"
                        step="1"
                        required
                        value={tripwireForm.allowedGroupSize}
                        onChange={(event) =>
                          setTripwireForm((current) => ({
                            ...current,
                            allowedGroupSize: event.target.value,
                          }))
                        }
                        className="mt-2 w-full rounded-lg border border-white/15 bg-black/30 px-3 py-2 text-white"
                      />
                    </label>
                    <label className="block text-xs text-gray-300">
                      {t("dashboard.tripwire.currentOccupancy")}
                      <input
                        type="number"
                        min="0"
                        step="1"
                        required
                        value={tripwireForm.currentOccupancy}
                        onChange={(event) =>
                          setTripwireForm((current) => ({
                            ...current,
                            currentOccupancy: event.target.value,
                          }))
                        }
                        className="mt-2 w-full rounded-lg border border-white/15 bg-black/30 px-3 py-2 text-white"
                      />
                    </label>
                    <fieldset>
                      <legend className="text-xs text-gray-300">
                        {t("dashboard.tripwire.entryDirection")}
                      </legend>
                      <div className="mt-2 grid grid-cols-2 gap-3">
                        {(
                          [
                            ["left", directionLeftImage],
                            ["right", directionRightImage],
                          ] as const
                        ).map(([direction, image]) => (
                          <button
                            key={direction}
                            type="button"
                            onClick={() =>
                              setTripwireForm((current) => ({
                                ...current,
                                direction,
                              }))
                            }
                            className={`rounded-xl border p-2 transition ${
                              tripwireForm.direction === direction
                                ? "border-ag-success bg-ag-success/15"
                                : "border-white/15 bg-black/20 hover:border-white/35"
                            }`}
                          >
                            <img
                              src={image}
                              alt={t(
                                direction === "left"
                                  ? "dashboard.tripwire.directionLeft"
                                  : "dashboard.tripwire.directionRight",
                              )}
                              className="h-12 w-full object-contain"
                            />
                          </button>
                        ))}
                      </div>
                    </fieldset>
                    <p className="min-h-4 text-xs text-red-300">
                      {drawingInstructions ===
                      t("dashboard.tripwire.invalidConfiguration")
                        ? drawingInstructions
                        : ""}
                    </p>
                    <div className="flex justify-end gap-2">
                      {!confirmationZone ? (
                        <button
                          type="button"
                          onClick={() => {
                            setTripwireModalOpen(false);
                            if (!confirmationZone) {
                              setTripwireDraftPoints(null);
                              setDrawingPointsByType((current) => ({
                                ...current,
                                tripwire: [],
                              }));
                              setAnnotationHistory((history) =>
                                history.filter(
                                  (action) =>
                                    action.type !== "point-added" ||
                                    action.mode !== "tripwire",
                                ),
                              );
                            }
                          }}
                          className="rounded-lg border border-white/15 px-4 py-2 text-xs text-gray-300"
                        >
                          {t("common.cancel")}
                        </button>
                      ) : null}
                      <button
                        type="submit"
                        className="rounded-lg bg-ag-success px-4 py-2 text-xs font-semibold text-black"
                      >
                        {confirmationZone
                          ? t("dashboard.tripwire.confirm")
                          : t("common.save")}
                      </button>
                    </div>
                  </form>
                </div>
              ) : null}

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

                    {/* Current drawing points */}
                    <div className="space-y-1 text-[11px] text-gray-400">
                      <div className="uppercase tracking-[0.2em]">
                        Current Drawing
                      </div>
                      <div>
                        {t("common.points")}:{" "}
                        <span className="text-white font-bold">
                          {drawingPoints.length}
                        </span>
                      </div>
                    </div>

                    <div className="space-y-2 rounded-2xl border border-white/10 bg-white/5 p-3 text-white">
                      <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.24em] text-gray-400">
                        <span>{t("dashboard.savedZones")}</span>
                        <span className="text-white/70">
                          {filteredSavedZones.length}
                        </span>
                      </div>
                      {filteredSavedZones.length > 0 ? (
                        <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                          {filteredSavedZones.map((zone) => (
                            <div
                              key={zone.zone_id}
                              className="flex items-center justify-between gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2"
                            >
                              <div className="min-w-0 text-[11px] text-white/90 overflow-hidden text-ellipsis whitespace-nowrap">
                                <div className="overflow-hidden text-ellipsis whitespace-nowrap">
                                  {zone.zone_name}
                                </div>
                                <div className="text-[10px] text-gray-400">
                                  {t("common.points")}:{" "}
                                  {zone.polygon_coords.length}
                                </div>
                                {zone.zone_type.toLowerCase().includes("tripwire") ? (
                                  tripwireStates[zone.zone_id]
                                    ?.occupancy_confirmation_required ? (
                                    <div className="mt-1 text-[10px] text-amber-200">
                                      {t("dashboard.tripwire.confirmationPending")}
                                    </div>
                                  ) : (
                                    <div className="mt-1 flex gap-2 text-[10px]">
                                      <span className="text-blue-300">
                                        {t("dashboard.tripwire.remaining")}:{" "}
                                        {tripwireStates[zone.zone_id]
                                          ?.remaining_group_count ??
                                          Math.max(
                                            0,
                                            (zone.tripwire_allowed_group_size ?? 0) -
                                              (zone.tripwire_current_occupancy ?? 0),
                                          )}
                                      </span>
                                      <span className="text-green-300">
                                        {t("dashboard.tripwire.inside")}:{" "}
                                        {tripwireStates[zone.zone_id]
                                          ?.current_occupancy ??
                                          zone.tripwire_current_occupancy ??
                                          0}
                                      </span>
                                      {(tripwireStates[zone.zone_id]
                                        ?.over_limit_count ??
                                        Math.max(
                                          0,
                                          (zone.tripwire_current_occupancy ?? 0) -
                                            (zone.tripwire_allowed_group_size ?? 0),
                                        )) > 0 ? (
                                        <span className="animate-pulse text-red-300">
                                          {t("dashboard.tripwire.overLimit")}:{" "}
                                          {tripwireStates[zone.zone_id]
                                            ?.over_limit_count ??
                                            0}
                                        </span>
                                      ) : null}
                                    </div>
                                  )
                                ) : null}
                              </div>
                              {zone.tripwire_requires_confirmation ? (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setConfirmationZone(zone);
                                    setTripwireForm({
                                      name: zone.zone_name || "Tripwire",
                                      allowedGroupSize: String(
                                        zone.tripwire_allowed_group_size ?? "",
                                      ),
                                      currentOccupancy: "",
                                      direction:
                                        zone.tripwire_entry_direction ?? "",
                                    });
                                    setTripwireModalOpen(true);
                                  }}
                                  className="rounded-lg border border-amber-300/40 px-2 py-1 text-[10px] text-amber-200 hover:bg-amber-300/10"
                                >
                                  {t("dashboard.tripwire.confirm")}
                                </button>
                              ) : null}
                              <button
                                onClick={() => deleteZone(zone.zone_id)}
                                className="rounded-full bg-white/5 px-2 py-1 text-[10px] text-gray-200 hover:bg-white/10 transition"
                              >
                                {t("common.delete")}
                              </button>
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>

                    {/* Action Buttons */}
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={startNewRegion}
                        className="rounded-full border border-ag-success/50 bg-ag-success/10 px-3 py-1 text-[11px] text-ag-success hover:bg-ag-success/20 transition cursor-pointer"
                      >
                        Add Region
                      </button>
                      <button
                        onClick={undoLastAction}
                        className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[11px] text-gray-200 hover:bg-white/10 transition cursor-pointer"
                      >
                        {t("common.undo")}
                      </button>
                      <button
                        onClick={saveAnnotations}
                        disabled={isSavingAnnotations}
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
              <div
                key={cam.camera_id}
                className="flex shrink-0 items-center gap-1"
              >
                <button
                  type="button"
                  onClick={async () => {
                    if (cam.camera_id === selectedCamera) {
                      return;
                    }
                    handleCameraSelection(cam.camera_id, cam.status);
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
                  {alarmStateByCamera[cam.camera_id]?.active ? (
                    <span
                      aria-label="Active alarm"
                      title="Active alarm"
                      className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-[10px] font-bold leading-none text-white animate-pulse"
                    >
                      !
                    </span>
                  ) : null}
                </button>
                <button
                  type="button"
                  onClick={() => toggleCameraMute(cam.camera_id)}
                  disabled={!alarmStateByCamera[cam.camera_id]?.active}
                  aria-pressed={!!mutedCameraIds[cam.camera_id]}
                  aria-label={t(
                    mutedCameraIds[cam.camera_id]
                      ? "dashboard.controls.unmuteCamera"
                      : "dashboard.controls.muteCamera",
                    { camera: cam.camera_name },
                  )}
                  title={t(
                    mutedCameraIds[cam.camera_id]
                      ? "dashboard.controls.unmuteCamera"
                      : "dashboard.controls.muteCamera",
                    { camera: cam.camera_name },
                  )}
                  className="rounded-xl border border-white/10 bg-black/20 p-2 text-gray-300 transition hover:border-white/20 hover:text-white disabled:cursor-not-allowed disabled:opacity-35"
                >
                  {mutedCameraIds[cam.camera_id] ? (
                    <VolumeX size={16} />
                  ) : (
                    <Volume2 size={16} />
                  )}
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
