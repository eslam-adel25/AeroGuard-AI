import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ComponentType } from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { aiService, cameraService, reportService } from "../services/api";
import { createSocket, type WSMessage } from "../services/socket";
import { useNotification } from "../components/NotificationSystem/useNotification";
import {
  AlertTriangle,
  Car,
  Copy,
  Crosshair,
  Eye,
  FileText,
  Flame,
  Gauge,
  ImageOff,
  Loader2,
  Radar,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Siren,
  Users,
  Video,
  X,
  Calendar,
  ChevronDown,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  LabelList,
  type TooltipContentProps,
} from "recharts";

type CameraOption = {
  camera_id: string;
  camera_name: string;
  location?: string;
};

const alertTypeDescriptions: Record<string, string> = {
  ABANDONED_BAG: "analytics.alertDescriptions.abandonedBag",
  LOITERING: "analytics.alertDescriptions.loitering",
  "RESTRICTED AREA": "analytics.alertDescriptions.restrictedArea",
};

const getAlertDescription = (value: unknown, t: TFunction) => {
  const eventType = typeof value === "string" ? value.trim() : "";
  if (!eventType) return t("analytics.alertDescriptions.unknown");

  return (
    (alertTypeDescriptions[eventType.toUpperCase()]
      ? t(alertTypeDescriptions[eventType.toUpperCase()])
      : null) ??
    eventType
      .replace(/[_-]+/g, " ")
      .toLowerCase()
      .replace(/\b[a-z]/g, (character) => character.toUpperCase())
  );
};

const getAlertEventErrorMessage = (error: string, t: TFunction) => {
  const errorKeys: Record<string, string> = {
    "Please enter an Event ID.": "analytics.alertInvestigation.enterEventId",
    "Please enter a valid Event ID.":
      "analytics.alertInvestigation.invalidEventId",
    "Please sign in to continue.":
      "analytics.alertInvestigation.signInRequired",
    "You are not authorized to view this alert.":
      "analytics.alertInvestigation.unauthorized",
  };
  const key = errorKeys[error];
  return key ? t(key) : error;
};

const formatEventTimestamp = (value: unknown, language: string) => {
  if (typeof value !== "string") return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";

  return new Intl.DateTimeFormat(language, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
};

type SummaryPayload = {
  total: number;
  violations: number;
  unknown_persons: number;
  average_confidence: number;
  total_detections?: number;
  critical_alerts?: number;
  high_alerts?: number;
  medium_alerts?: number;
  low_alerts?: number;
  weapons?: number;
  suspicious_objects?: number;
  fire?: number;
  persons?: number;
  vehicles?: number;
  active_cameras?: number;
  fire_detections?: number;
  smoke_detections?: number;
  weapon_detections?: number;
  person_detections?: number;
  vehicle_detections?: number;
};

type DetectionTypeItem = {
  type: string;
  count: number;
};

type TimelineItem = {
  bucket_value?: string;
  label: string;
  day?: string;
  hour?: number;
  camera_id?: string;
  camera_name?: string;
  count: number;
  critical?: number;
};

type FrequencyBucket = {
  label: string;
  values: Record<string, number>;
};

type FrequencyTimelineData = {
  data: Array<Record<string, number | string>>;
  cameras: Array<[string, string]>;
};

type SeverityItem = {
  severity: "Critical" | "High" | "Medium" | "Low";
  count: number;
  percentage: number;
};

type TopCameraItem = {
  camera_id: string;
  camera_name: string;
  location: string;
  status: string;
  count: number;
};

type HeatmapItem = {
  hour: number;
  label: string;
  count: number;
};

type RecentAlertItem = {
  time: string;
  camera_id: string;
  camera_name: string;
  detection_type: string;
  confidence: number;
  severity: "Critical" | "High" | "Medium" | "Low" | "Unknown";
};

type DashboardResponse = {
  summary: SummaryPayload;
  details: DetectionTypeItem[];
  charts?: {
    timeline?: TimelineItem[];
    threat_distribution?: DetectionTypeItem[];
    severity_distribution?: SeverityItem[];
    top_cameras?: TopCameraItem[];
    heatmap?: HeatmapItem[];
    frequency_by_zone?: Array<{ name: string; count: number }>;
  };
  recent_alerts?: RecentAlertItem[];
  cameras?: Array<{
    camera_id: string;
    camera_name: string;
    location: string;
    status: string;
  }>;
};

type FiltersState = {
  start_date: string;
  end_date: string;
  camera_id: string;
};

type KPIItem = {
  key: string;
  title: string;
  value: string;
  icon: ComponentType<{ size?: number; className?: string }>;
  tone: string;
  trend?: string;
  trendColor?: string;
  iconColor?: string;
  valueColor?: string;
};

const toDateInput = (date: Date) => date.toISOString().slice(0, 10);

const SkeletonCard = memo(() => (
  <div className="rounded-xl border border-white/5 bg-[#0d1527] p-5 animate-pulse h-[116px]">
    <div className="flex items-start justify-between mb-4">
      <div className="h-3 w-24 bg-white/10 rounded" />
      <div className="h-5 w-5 bg-white/10 rounded-full" />
    </div>
    <div className="h-6 w-16 bg-white/10 rounded" />
    <div className="h-3 w-28 bg-white/10 rounded mt-3" />
  </div>
));

const EmptyState = memo(() => {
  const { t } = useTranslation();
  return (
    <div className="rounded-2xl border border-[#162235] bg-[#0d1527] p-12 text-center max-w-md mx-auto my-12 shadow-xl">
      <Radar className="mx-auto mb-4 text-[#10b981] animate-pulse" size={44} />
      <h3 className="text-xl font-bold font-display text-white mb-2">
        {t("analytics.noDataTitle")}
      </h3>
      <p className="text-slate-400 text-sm leading-relaxed">
        {t("analytics.noDataSubtitle")}
      </p>
    </div>
  );
});

const ErrorCard = memo(({ onRetry }: { onRetry: () => void }) => {
  const { t } = useTranslation();
  return (
    <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-8 max-w-xl mx-auto my-12 shadow-lg backdrop-blur-sm">
      <div className="flex items-start gap-4">
        <div className="p-3 bg-red-500/10 rounded-xl text-red-400">
          <AlertTriangle size={24} />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-bold font-display text-white">
            {t("analytics.errorTitle")}
          </h3>
          <p className="text-red-200/60 text-sm mt-1 leading-relaxed">
            {t("analytics.errorSubtitle")}
          </p>
          <button
            onClick={onRetry}
            className="mt-4 rounded-lg bg-red-600 hover:bg-red-700 px-4 py-2 text-xs font-bold text-white transition-colors cursor-pointer"
          >
            {t("common.retry")}
          </button>
        </div>
      </div>
    </div>
  );
});

const Analytics = () => {
  const { t, i18n } = useTranslation();
  const [filters, setFilters] = useState<FiltersState>({
    start_date: "",
    end_date: "",
    camera_id: "",
  });
  const [cameraOptions, setCameraOptions] = useState<CameraOption[]>([]);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [alertEventId, setAlertEventId] = useState("");
  const [alertEvent, setAlertEvent] = useState<Record<string, unknown> | null>(
    null,
  );
  const [alertEventError, setAlertEventError] = useState("");
  const [isSearchingAlert, setIsSearchingAlert] = useState(false);
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);
  const [screenshotLoading, setScreenshotLoading] = useState(false);
  const [showScreenshotModal, setShowScreenshotModal] = useState(false);
  const [eventSuggestions, setEventSuggestions] = useState<
    Array<Record<string, unknown>>
  >([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlightedSuggestionIndex, setHighlightedSuggestionIndex] =
    useState(0);
  const screenshotUrlRef = useRef<string | null>(null);
  const suggestionRequestId = useRef(0);
  const { toast } = useNotification();

  const revokeScreenshotUrl = useCallback(() => {
    if (screenshotUrlRef.current) {
      URL.revokeObjectURL(screenshotUrlRef.current);
      screenshotUrlRef.current = null;
    }
    setScreenshotUrl(null);
  }, []);

  const clearAlertInvestigation = useCallback(() => {
    setAlertEventId("");
    setAlertEvent(null);
    setAlertEventError("");
    setIsSearchingAlert(false);
    setScreenshotLoading(false);
    setEventSuggestions([]);
    setSuggestionsLoading(false);
    setShowSuggestions(false);
    setHighlightedSuggestionIndex(0);
    revokeScreenshotUrl();
    setShowScreenshotModal(false);
  }, [revokeScreenshotUrl]);

  const performAlertSearch = useCallback(
    async (nextValue: string) => {
      const normalizedValue = nextValue.trim();
      if (!normalizedValue) {
        setAlertEventError("Please enter an Event ID.");
        return;
      }
      if (
        !/^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$/i.test(
          normalizedValue,
        )
      ) {
        setAlertEventError("Please enter a valid Event ID.");
        return;
      }

      setAlertEventError("");
      setIsSearchingAlert(true);
      setAlertEvent(null);
      setShowSuggestions(false);
      revokeScreenshotUrl();

      try {
        const response = await aiService.getEvent(normalizedValue);
        const payload = response.data as Record<string, unknown>;
        setAlertEvent(payload);

        setScreenshotLoading(true);
        try {
          const screenshotResponse =
            await aiService.downloadScreenshot(normalizedValue);
          const blob = screenshotResponse.data as Blob;
          if (!(blob instanceof Blob) || blob.size === 0) {
            return;
          }
          const objectUrl = URL.createObjectURL(blob);
          screenshotUrlRef.current = objectUrl;
          setScreenshotUrl(objectUrl);
        } catch {
          return;
        } finally {
          setScreenshotLoading(false);
        }
      } catch (error: unknown) {
        const status = (error as { response?: { status?: number } })?.response
          ?.status;
        if (status === 404) {
          setAlertEventError("Alert not found");
        } else if (status === 401) {
          setAlertEventError("Please sign in to continue.");
        } else if (status === 403) {
          setAlertEventError("You are not authorized to view this alert.");
        } else {
          setAlertEventError("Alert not found");
        }
      } finally {
        setIsSearchingAlert(false);
      }
    },
    [revokeScreenshotUrl],
  );

  useEffect(() => {
    return () => {
      revokeScreenshotUrl();
    };
  }, [revokeScreenshotUrl]);

  useEffect(() => {
    const trimmed = alertEventId.trim();
    const isCompleteEventId =
      /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$/i.test(
        trimmed,
      );
    if (!trimmed || trimmed.length < 4 || isCompleteEventId) {
      setEventSuggestions([]);
      setShowSuggestions(false);
      setSuggestionsLoading(false);
      return;
    }

    const requestId = ++suggestionRequestId.current;
    const timeout = window.setTimeout(async () => {
      setSuggestionsLoading(true);
      try {
        const response = await aiService.listEvents({
          event_id_prefix: trimmed,
          limit: 8,
        });
        const payload = response.data as Record<string, unknown>;
        const rawItems = Array.isArray(payload?.items)
          ? (payload.items as Array<Record<string, unknown>>)
          : Array.isArray(payload)
            ? (payload as Array<Record<string, unknown>>)
            : [];
        const matches = rawItems
          .filter((item) => {
            const value =
              typeof item.event_id === "string" ? item.event_id : "";
            return value.toLowerCase().startsWith(trimmed.toLowerCase());
          })
          .slice(0, 8)
          .map((item) => ({
            event_id: String(item.event_id ?? ""),
            detection_type: item.detection_type ?? "",
            severity: item.severity ?? "",
            camera_name: item.camera_name ?? item.camera_id ?? "",
          }));

        if (requestId !== suggestionRequestId.current) {
          return;
        }
        setEventSuggestions(matches);
        setShowSuggestions(true);
        setHighlightedSuggestionIndex(0);
      } catch {
        if (requestId === suggestionRequestId.current) {
          setEventSuggestions([]);
          setShowSuggestions(true);
        }
      } finally {
        if (requestId === suggestionRequestId.current) {
          setSuggestionsLoading(false);
        }
      }
    }, 250);

    return () => window.clearTimeout(timeout);
  }, [alertEventId]);

  const loadCameras = useCallback(async () => {
    const res = await cameraService.getAll();
    const mapped = (res.data as CameraOption[]).map((cam) => ({
      camera_id: cam.camera_id,
      camera_name: cam.camera_name,
      location: cam.location,
    }));
    setCameraOptions(mapped);
  }, []);

  const fetchDashboard = useCallback(
    async (active: FiltersState, soft = false) => {
      if (!active.start_date || !active.end_date) {
        return;
      }

      if (soft) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      try {
        setError(null);
        const res = await reportService.getDashboard({
          start_date: active.start_date,
          end_date: active.end_date,
          camera_id: active.camera_id || undefined,
        });
        setDashboard(res.data as DashboardResponse);
      } catch {
        setError("request_failed");
        setDashboard(null);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [],
  );

  useEffect(() => {
    const now = new Date();
    const defaults: FiltersState = {
      start_date: toDateInput(
        new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000),
      ),
      end_date: toDateInput(now),
      camera_id: "",
    };

    setFilters(defaults);

    void (async () => {
      try {
        await loadCameras();
      } catch {
        setCameraOptions([]);
      }
      await fetchDashboard(defaults, false);
    })();
  }, [fetchDashboard, loadCameras]);

  useEffect(() => {
    if (!filters.start_date || !filters.end_date) {
      return;
    }
    void fetchDashboard(filters, true);
  }, [filters, fetchDashboard]);

  useEffect(() => {
    const socket = createSocket((message: WSMessage) => {
      if (
        (message.event === "new_alert" ||
          message.event === "ai_event" ||
          message.event === "camera_status" ||
          message.event === "ai_status") &&
        filters.start_date &&
        filters.end_date
      ) {
        void fetchDashboard(filters, true);
      }
    });

    return () => {
      socket.close();
    };
  }, [fetchDashboard, filters]);

  const onRefresh = useCallback(() => {
    void fetchDashboard(filters, true);
  }, [fetchDashboard, filters]);

  const summary = dashboard?.summary;
  const details = useMemo(
    () => dashboard?.charts?.threat_distribution ?? dashboard?.details ?? [],
    [dashboard],
  );
  const timeline = useMemo(
    () => dashboard?.charts?.timeline ?? [],
    [dashboard],
  );
  const severity = useMemo(
    () => dashboard?.charts?.severity_distribution ?? [],
    [dashboard],
  );
  const topCameras = useMemo(
    () => dashboard?.charts?.top_cameras ?? [],
    [dashboard],
  );
  const heatmap = useMemo(() => dashboard?.charts?.heatmap ?? [], [dashboard]);
  const frequencyData = useMemo(() => {
    const buckets = new Map<string, { label: string; count: number }>();
    timeline.forEach((row) => {
      const bucketKey = row.bucket_value ?? row.label;
      const current = buckets.get(bucketKey);
      if (current) {
        current.count += row.count;
      } else {
        buckets.set(bucketKey, { label: row.label, count: row.count });
      }
    });
    return Array.from(buckets.values());
  }, [timeline]);

  const hasData = useMemo(() => {
    if (!summary) {
      return false;
    }
    return (summary.total_detections ?? summary.total ?? 0) > 0;
  }, [summary]);

  const selectedCameraName = useMemo(() => {
    if (!filters.camera_id) {
      return t("analytics.allCameras");
    }
    return (
      cameraOptions.find((cam) => cam.camera_id === filters.camera_id)
        ?.camera_name ?? t("analytics.allCameras")
    );
  }, [cameraOptions, filters.camera_id, t]);
  const alertCamera = alertEvent
    ? cameraOptions.find(
        (camera) => camera.camera_id === String(alertEvent.camera_id ?? ""),
      )
    : undefined;

  // Map and style KPIs according to reference screenshot layout
  const kpis = useMemo<KPIItem[]>(() => {
    const total = summary?.total_detections ?? summary?.total ?? 0;
    const critical = summary?.critical_alerts ?? 0;
    const high = summary?.high_alerts ?? 0;
    const medium = summary?.medium_alerts ?? 0;
    const low = summary?.low_alerts ?? 0;
    const suspiciousObjects = summary?.suspicious_objects ?? 0;
    const fire = summary?.fire ?? 0;
    const persons = summary?.persons ?? 0;
    const vehicles = summary?.vehicles ?? 0;
    const avgConf = summary?.average_confidence ?? 0;
    const active = summary?.active_cameras ?? 0;

    return [
      {
        key: "total",
        title: t("analytics.kpis.totalDetections"),
        value: total.toLocaleString(),
        icon: Radar,
        tone: "text-[#10b981]",
        trend: t("analytics.kpiTrends.totalWindow", {
          count: total.toLocaleString(),
        }),
        trendColor: "text-[#10b981]",
        iconColor: "text-[#10b981]",
      },
      {
        key: "critical",
        title: t("analytics.kpis.criticalAlerts"),
        value: critical.toLocaleString(),
        icon: Siren,
        tone: "text-[#ef4444]",
        trend: t("analytics.kpiTrends.criticalDatabase", {
          count: critical.toLocaleString(),
        }),
        trendColor: "text-[#ef4444]/90",
        iconColor: "text-[#ef4444]",
        valueColor: "text-[#ef4444]",
      },
      {
        key: "high",
        title: t("analytics.kpis.highAlerts"),
        value: high.toLocaleString(),
        icon: ShieldAlert,
        tone: "text-[#f97316]",
        trend: t("analytics.kpiTrends.highSeverity", {
          count: high.toLocaleString(),
        }),
        trendColor: "text-slate-400",
        iconColor: "text-[#f97316]",
      },
      {
        key: "medium",
        title: t("analytics.kpis.mediumAlerts"),
        value: medium.toLocaleString(),
        icon: AlertTriangle,
        tone: "text-[#f59e0b]",
        trend: t("analytics.kpiTrends.mediumSeverity", {
          count: medium.toLocaleString(),
        }),
        trendColor: "text-slate-400",
        iconColor: "text-[#f59e0b]",
      },
      {
        key: "low",
        title: t("analytics.kpis.lowAlerts"),
        value: low.toLocaleString(),
        icon: ShieldCheck,
        tone: "text-[#3b82f6]",
        trend: t("analytics.kpiTrends.lowSeverity", {
          count: low.toLocaleString(),
        }),
        trendColor: "text-slate-400",
        iconColor: "text-[#3b82f6]",
      },
      {
        key: "suspicious",
        title: t("analytics.kpis.suspiciousObjects"),
        value: suspiciousObjects.toLocaleString(),
        icon: Shield,
        tone: "text-[#ef4444]",
        trend: t("analytics.kpiTrends.suspiciousObjects", {
          count: suspiciousObjects.toLocaleString(),
        }),
        trendColor: "text-slate-400",
        iconColor: "text-[#ef4444]",
      },
      {
        key: "fire",
        title: t("analytics.kpis.fire"),
        value: fire.toLocaleString(),
        icon: Flame,
        tone: "text-[#ef4444]",
        trend: t("analytics.kpiTrends.fireDetections", {
          count: fire.toLocaleString(),
        }),
        trendColor: "text-slate-400",
        iconColor: "text-[#ef4444]",
      },
      {
        key: "persons",
        title: t("analytics.kpis.persons"),
        value: persons.toLocaleString(),
        icon: Users,
        tone: "text-[#10b981]",
        trend: t("analytics.kpiTrends.personDetections", {
          count: persons.toLocaleString(),
        }),
        trendColor: "text-slate-400",
        iconColor: "text-[#10b981]",
      },
      {
        key: "vehicles",
        title: t("analytics.kpis.vehicles"),
        value: vehicles.toLocaleString(),
        icon: Car,
        tone: "text-[#10b981]",
        trend: t("analytics.kpiTrends.vehicleDetections", {
          count: vehicles.toLocaleString(),
        }),
        trendColor: "text-slate-400",
        iconColor: "text-[#10b981]",
      },
      {
        key: "avg",
        title: t("analytics.kpis.averageConfidence"),
        value: `${avgConf.toFixed(1)}%`,
        icon: Crosshair,
        tone: "text-[#10b981]",
        trend: t("analytics.kpiTrends.averageConfidence", {
          value: avgConf.toFixed(1),
        }),
        trendColor: "text-[#10b981]",
        iconColor: "text-[#10b981]",
      },
      {
        key: "active",
        title: t("analytics.kpis.activeCameras"),
        value: active.toLocaleString(),
        icon: Video,
        tone: "text-[#10b981]",
        trend: t("analytics.kpiTrends.activeCameras", {
          count: active.toLocaleString(),
          cameraName: selectedCameraName,
        }),
        trendColor: "text-[#10b981]",
        iconColor: "text-[#10b981]",
      },
    ];
  }, [selectedCameraName, summary, t]);

  // Construct donut pie chart data with ordered categories and precise colors
  const severityPieData = useMemo(() => {
    const order = ["Critical", "Low", "Medium", "High"];
    return order
      .map((name) => {
        const item = severity.find((s) => s.severity === name);
        return {
          name: name,
          value: item ? item.count : 0,
          percentage: item ? item.percentage : 0,
        };
      })
      .filter((d) => d.value > 0);
  }, [severity]);

  const severityColors: Record<string, string> = {
    Critical: "#ef4444",
    Low: "#10b981",
    Medium: "#f59e0b",
    High: "#f97316",
  };

  const totalAlerts = useMemo(() => {
    return severity.reduce((acc, curr) => acc + curr.count, 0).toLocaleString();
  }, [severity]);

  const threatBarData = useMemo(() => {
    const categoryOrder = [
      "Person",
      "Baggage",
      "Fire",
      "Vehicle",
      "Suspicious Object",
    ];

    const countsByCategory = new Map<string, number>();
    details.forEach((item) => {
      const normalized = item.type?.trim().toLowerCase();
      if (!normalized) return;
      if (
        normalized.includes("fire") ||
        normalized.includes("smoke") ||
        normalized.includes("flame")
      ) {
        countsByCategory.set(
          "Fire",
          (countsByCategory.get("Fire") ?? 0) + item.count,
        );
        return;
      }
      if (
        normalized.includes("person") ||
        normalized.includes("human") ||
        normalized.includes("intruder")
      ) {
        countsByCategory.set(
          "Person",
          (countsByCategory.get("Person") ?? 0) + item.count,
        );
        return;
      }
      if (
        ["baggage", "bag", "backpack", "suitcase", "luggage"].some((label) =>
          normalized.includes(label),
        ) ||
        normalized.includes("owned_bag") ||
        normalized.includes("unattended")
      ) {
        countsByCategory.set(
          "Baggage",
          (countsByCategory.get("Baggage") ?? 0) + item.count,
        );
        return;
      }
      if (
        ["vehicle", "car", "truck", "bus", "motorcycle", "bicycle"].some(
          (label) => normalized.includes(label),
        )
      ) {
        countsByCategory.set(
          "Vehicle",
          (countsByCategory.get("Vehicle") ?? 0) + item.count,
        );
        return;
      }
      if (
        ["suspicious", "unknown", "unidentified", "object"].some((label) =>
          normalized.includes(label),
        )
      ) {
        countsByCategory.set(
          "Suspicious Object",
          (countsByCategory.get("Suspicious Object") ?? 0) + item.count,
        );
        return;
      }
    });

    const prepared = categoryOrder.map((category) => ({
      type: category,
      count: countsByCategory.get(category) ?? 0,
    }));

    return [...prepared].sort((a, b) => {
      if (b.count !== a.count) {
        return b.count - a.count;
      }
      return categoryOrder.indexOf(a.type) - categoryOrder.indexOf(b.type);
    });
  }, [details]);

  const frequencyTimelineData = useMemo<FrequencyTimelineData>(() => {
    const buckets = new Map<string, FrequencyBucket>();
    const cameras = new Map<string, string>();

    timeline.forEach((row) => {
      const bucketKey = row.bucket_value ?? row.label;
      const bucketLabel = row.label ?? bucketKey;
      const cameraId = row.camera_id ?? "unknown";
      const cameraName = row.camera_name ?? "Unknown Camera";
      cameras.set(cameraId, cameraName);

      const bucket = buckets.get(bucketKey);
      if (bucket) {
        bucket.values[cameraId] = (bucket.values[cameraId] || 0) + row.count;
      } else {
        buckets.set(bucketKey, {
          label: bucketLabel,
          values: {
            [cameraId]: row.count,
          },
        });
      }
    });

    const cameraOrder = Array.from(cameras.entries()).sort((a, b) => {
      const totalA = Array.from(buckets.values()).reduce(
        (sum, entry) => sum + (entry.values[a[0]] || 0),
        0,
      );
      const totalB = Array.from(buckets.values()).reduce(
        (sum, entry) => sum + (entry.values[b[0]] || 0),
        0,
      );
      return totalB - totalA;
    });

    const cameraIds = cameraOrder.map(([cameraId]) => cameraId);

    return {
      data: Array.from(buckets.values()).map((bucket) => {
        const row: Record<string, number | string> = { label: bucket.label };
        cameraIds.forEach((cameraId) => {
          row[cameraId] = bucket.values[cameraId] ?? 0;
        });
        return row;
      }),
      cameras: cameraOrder,
    };
  }, [timeline]);

  const renderFrequencyTooltip = useCallback((props: TooltipContentProps) => {
    const { active, payload, label } = props;
    if (!active || !payload || payload.length === 0) {
      return null;
    }

    const total = payload.reduce((sum: number, entry) => {
      const value = typeof entry.value === "number" ? entry.value : 0;
      return sum + value;
    }, 0);

    return (
      <div className="rounded-xl border border-[#162235] bg-[#0d1527] p-3 text-xs text-slate-100">
        <div className="text-slate-300 mb-2 text-[11px] font-semibold">
          {label}
        </div>
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center justify-between gap-4">
            <span className="text-slate-300">{entry.name}</span>
            <span className="font-semibold text-white">
              {typeof entry.value === "number" ? entry.value : entry.value}
            </span>
          </div>
        ))}
        <div className="border-t border-white/10 mt-2 pt-2 flex items-center justify-between text-slate-300">
          <span>{t("common.total")}</span>
          <span className="font-semibold text-white">{total}</span>
        </div>
      </div>
    );
  }, [t]);

  const heatmapMaxCount = useMemo(() => {
    const counts = heatmap.map((item) => item.count);
    return counts.length > 0 ? Math.max(...counts) : 0;
  }, [heatmap]);

  return (
    <div className="min-h-screen bg-[#070e17] text-[#f8fafc] p-4 md:p-6 lg:p-8 font-sans antialiased space-y-6">
      {/* HEADER SECTION */}
      <header className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4 pb-2">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white font-display">
            {t("analytics.pageTitle")}
          </h1>
          <p className="text-slate-400 mt-1 text-xs md:text-sm">
            {t("analytics.pageSubtitle")}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full xl:w-auto justify-start xl:justify-end">
          {/* Start Date */}
          <div className="relative flex items-center bg-[#0d1527] border border-[#162235] hover:border-slate-700/60 rounded-lg px-3 py-2 text-xs font-semibold text-slate-200 transition-colors">
            <Calendar size={14} className="text-[#10b981] mr-2" />
            <input
              type="date"
              value={filters.start_date}
              onChange={(e) =>
                setFilters((prev) => ({ ...prev, start_date: e.target.value }))
              }
              className="bg-transparent border-none text-slate-200 focus:outline-none text-xs cursor-pointer w-[102px] scheme-dark"
            />
          </div>

          {/* End Date */}
          <div className="relative flex items-center bg-[#0d1527] border border-[#162235] hover:border-slate-700/60 rounded-lg px-3 py-2 text-xs font-semibold text-slate-200 transition-colors">
            <Calendar size={14} className="text-[#10b981] mr-2" />
            <input
              type="date"
              value={filters.end_date}
              onChange={(e) =>
                setFilters((prev) => ({ ...prev, end_date: e.target.value }))
              }
              className="bg-transparent border-none text-slate-200 focus:outline-none text-xs cursor-pointer w-[102px] scheme-dark"
            />
          </div>

          {/* Camera Dropdown Selector */}
          <div className="relative flex items-center bg-[#0d1527] border border-[#162235] hover:border-slate-700/60 rounded-lg px-3 py-2 text-xs font-semibold text-slate-200 transition-colors">
            <Video size={14} className="text-[#3b82f6] mr-2" />
            <select
              value={filters.camera_id}
              onChange={(e) =>
                setFilters((prev) => ({ ...prev, camera_id: e.target.value }))
              }
              className="bg-transparent border-none text-slate-200 focus:outline-none text-xs cursor-pointer font-semibold pr-5 appearance-none"
            >
              <option value="" className="bg-[#0d1527]">
                {t("analytics.allCameras")}
              </option>
              {cameraOptions.map((cam) => (
                <option
                  key={cam.camera_id}
                  value={cam.camera_id}
                  className="bg-[#0d1527]"
                >
                  {cam.camera_name}
                </option>
              ))}
            </select>
            <ChevronDown
              size={12}
              className="text-slate-400 absolute right-3 pointer-events-none"
            />
          </div>

          {/* Export PDF Button */}
          <button
            onClick={async () => {
              try {
                const payload = {
                  start_date: filters.start_date,
                  end_date: filters.end_date,
                  camera_id: filters.camera_id || undefined,
                  title: `Analytics Report ${filters.start_date} - ${filters.end_date}`,
                  report_type: "analytics",
                };
                const reportRes = await reportService.generateReport(payload);
                const reportId = reportRes.data?.report_id;
                if (!reportId) {
                  throw new Error("No report id returned");
                }
                const pdfRes = await reportService.exportPdf(reportId);
                const blob = new Blob([pdfRes.data], {
                  type: "application/pdf",
                });
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = url;
                link.download = `analytics-${reportId}.pdf`;
                link.click();
                window.URL.revokeObjectURL(url);
              } catch (err) {
                console.error("PDF export failed", err);
                setError("pdf_export_failed");
              }
            }}
            className="inline-flex items-center gap-1.5 bg-[#ef4444] hover:bg-[#dc2626] text-white text-xs font-bold rounded-lg px-3.5 py-2 transition-colors cursor-pointer shadow-md shadow-red-950/20"
          >
            <FileText size={14} />
            <span>PDF</span>
          </button>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={refreshing}
            className="inline-flex items-center justify-center bg-[#0d1527] border border-[#162235] hover:bg-[#162235] text-slate-200 rounded-lg p-2.5 transition-colors cursor-pointer disabled:opacity-50"
          >
            <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
          </button>
        </div>
      </header>

      {error ? (
        <ErrorCard onRetry={onRefresh} />
      ) : loading ? (
        <section className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, idx) => (
            <SkeletonCard key={idx} />
          ))}
        </section>
      ) : !hasData ? (
        <EmptyState />
      ) : (
        <>
          {/* STATISTICS CARDS GRID */}
          <section className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
            {kpis.map((kpi) => (
              <article
                key={kpi.key}
                className="bg-[#0d1527] border border-[#162235] rounded-xl p-4 flex flex-col justify-between h-[116px] relative overflow-hidden transition-all duration-300 hover:border-slate-700/40 hover:shadow-lg hover:shadow-black/20"
              >
                <div className="flex items-start justify-between">
                  <span className="text-[10px] font-bold tracking-wider text-slate-400 uppercase select-none">
                    {kpi.title}
                  </span>
                  <kpi.icon
                    size={16}
                    className={`${kpi.iconColor || "text-slate-400"}`}
                  />
                </div>
                <div className="mt-2">
                  <span
                    className={`text-2xl font-bold font-display tracking-tight ${kpi.valueColor || "text-white"}`}
                  >
                    {kpi.value}
                  </span>
                  <p
                    className={`text-[10px] font-medium mt-1.5 flex items-center gap-1 leading-none ${kpi.trendColor || "text-slate-500"}`}
                  >
                    {kpi.trend}
                  </p>
                </div>
              </article>
            ))}
          </section>

          {/* SECOND ROW - TIMELINE & SEVERITY */}
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Detection Timeline */}
            <div className="bg-[#0d1527] border border-[#162235] rounded-xl p-5 flex flex-col">
              <div className="flex items-center justify-between mb-5">
                <h3 className="text-sm font-bold font-display tracking-wide text-white">
                  {t("analytics.chartTitles.timeline")}
                </h3>
                {/* Custom HTML Legend */}
                <div className="flex flex-wrap items-center gap-3 text-[10px] font-semibold">
                  {frequencyTimelineData.cameras.map((camera, index) => (
                    <span
                      key={camera[0]}
                      className="flex items-center gap-1.5 text-slate-300"
                    >
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{
                          backgroundColor: [
                            "#10b981",
                            "#22c55e",
                            "#0ea5e9",
                            "#f97316",
                            "#a855f7",
                            "#ec4899",
                          ][index % 6],
                        }}
                      />
                      {camera[1]}
                    </span>
                  ))}
                </div>
              </div>

              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={frequencyTimelineData.data}
                    margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#162235"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="label"
                      stroke="#475569"
                      fontSize={10}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      stroke="#475569"
                      fontSize={10}
                      tickLine={false}
                      axisLine={false}
                      domain={[0, "auto"]}
                      tickCount={6}
                    />
                    <Tooltip
                      content={renderFrequencyTooltip}
                      contentStyle={{
                        backgroundColor: "#0d1527",
                        borderColor: "#162235",
                        borderRadius: "8px",
                      }}
                      itemStyle={{ color: "#f8fafc", fontSize: "11px" }}
                      labelStyle={{
                        color: "#94a3b8",
                        fontSize: "10px",
                        fontWeight: 600,
                      }}
                    />
                    {frequencyTimelineData.cameras.map((camera, index) => (
                      <Bar
                        key={`camera-${camera[0]}`}
                        name={camera[1]}
                        dataKey={camera[0]}
                        stackId="a"
                        fill={
                          [
                            "#10b981",
                            "#22c55e",
                            "#0ea5e9",
                            "#f97316",
                            "#a855f7",
                            "#ec4899",
                          ][index % 6]
                        }
                        radius={[4, 4, 0, 0]}
                      />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Severity Distribution */}
            <div className="bg-[#0d1527] border border-[#162235] rounded-xl p-5 flex flex-col">
              <h3 className="text-sm font-bold font-display tracking-wide text-white mb-5">
                {t("analytics.chartTitles.severity")}
              </h3>

              <div className="flex flex-col sm:flex-row items-center justify-between gap-6 flex-1 h-56">
                {/* Donut Chart with Absolute Core Stats */}
                <div className="relative w-44 h-44 flex items-center justify-center">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={severityPieData}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={58}
                        outerRadius={76}
                        paddingAngle={3}
                        stroke="#0d1527"
                        strokeWidth={2}
                      >
                        {severityPieData.map((entry) => (
                          <Cell
                            key={`cell-${entry.name}`}
                            fill={severityColors[entry.name] || "#1e293b"}
                          />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  {/* Central Text Panel */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-center select-none pointer-events-none">
                    <span className="text-3xl font-bold font-display tracking-tight text-white leading-none">
                      {totalAlerts}
                    </span>
                    <span className="text-[10px] font-bold text-slate-400 mt-1 uppercase tracking-widest">
                      Alerts
                    </span>
                  </div>
                </div>

                {/* Custom Styled HTML Legend */}
                <div className="flex-1 w-full flex flex-col justify-center gap-3 pr-4">
                  {severityPieData.map((item) => (
                    <div
                      key={item.name}
                      className="flex items-center justify-between text-xs font-semibold py-1.5 border-b border-white/5 last:border-0"
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: severityColors[item.name] }}
                        />
                        <span className="text-slate-300 font-medium">
                          {item.name}
                        </span>
                      </div>
                      <span className="text-slate-400 font-mono">
                        ({item.percentage}%)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* THIRD ROW - THREE COLUMNS */}
          <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Threat Distribution (Horizontal Bar Chart) */}
            <div className="bg-[#0d1527] border border-[#162235] rounded-xl p-5 flex flex-col justify-between">
              <h3 className="text-sm font-bold font-display tracking-wide text-white mb-5">
                {t("analytics.chartTitles.distribution")}
              </h3>
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={threatBarData}
                    layout="vertical"
                    margin={{ top: 5, right: 35, left: -25, bottom: 5 }}
                  >
                    <XAxis type="number" hide />
                    <YAxis
                      dataKey="type"
                      type="category"
                      stroke="#94a3b8"
                      fontSize={10}
                      tickLine={false}
                      axisLine={false}
                      width={85}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0d1527",
                        borderColor: "#162235",
                        borderRadius: "8px",
                      }}
                      itemStyle={{ color: "#f8fafc", fontSize: "11px" }}
                    />
                    <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={16}>
                      {threatBarData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={
                            entry.type === "Fire/Smoke" ? "#ef4444" : "#10b981"
                          }
                        />
                      ))}
                      <LabelList
                        dataKey="count"
                        position="right"
                        fill="#94a3b8"
                        fontSize={10}
                        style={{ fontWeight: 600, paddingLeft: 6 }}
                      />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Detection Frequency Over Time (Vertical Bar Chart) */}
            <div className="bg-[#0d1527] border border-[#162235] rounded-xl p-5 flex flex-col justify-between">
              <h3 className="text-sm font-bold font-display tracking-wide text-white mb-5">
                {t("analytics.chartTitles.frequency")}
              </h3>
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={frequencyData}
                    margin={{ top: 10, right: 5, left: -25, bottom: 5 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#162235"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="label"
                      stroke="#475569"
                      fontSize={9}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      stroke="#475569"
                      fontSize={10}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0d1527",
                        borderColor: "#162235",
                        borderRadius: "8px",
                      }}
                      itemStyle={{ color: "#f8fafc", fontSize: "11px" }}
                    />
                    <Bar
                      dataKey="count"
                      fill="#10b981"
                      radius={[3, 3, 0, 0]}
                      barSize={20}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Alert Investigation */}
            <div className="bg-[#111b2e] border border-[#162235] rounded-xl p-5 flex flex-col justify-between">
              <h3 className="text-sm font-bold font-display tracking-wide text-white mb-5">
                Alert Investigation
              </h3>

              <div className="space-y-3.5 flex-1 overflow-y-auto max-h-[224px] pr-1 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
                <div className="space-y-3">
                  <label className="block text-[10px] font-bold uppercase tracking-[0.18em] text-slate-300">
                    {t("analytics.alertInvestigation.searchByAlertId")}
                  </label>

                  <div className="flex items-start gap-2">
                    <div className="relative flex-1 min-w-0">
                      <input
                        value={alertEventId}
                        onChange={(event) => {
                          const nextValue = event.target.value;
                          setAlertEventId(nextValue);
                          setAlertEventError("");
                          if (!nextValue.trim()) {
                            setEventSuggestions([]);
                            setShowSuggestions(false);
                          }
                        }}
                        onFocus={() => {
                          if (alertEventId.trim().length >= 4) {
                            setShowSuggestions(true);
                          }
                        }}
                        onBlur={() => {
                          window.setTimeout(
                            () => setShowSuggestions(false),
                            120,
                          );
                        }}
                        onKeyDown={(event) => {
                          if (
                            event.key === "ArrowDown" &&
                            showSuggestions &&
                            eventSuggestions.length > 0
                          ) {
                            event.preventDefault();
                            setHighlightedSuggestionIndex((current) =>
                              current + 1 < eventSuggestions.length
                                ? current + 1
                                : 0,
                            );
                            return;
                          }
                          if (
                            event.key === "ArrowUp" &&
                            showSuggestions &&
                            eventSuggestions.length > 0
                          ) {
                            event.preventDefault();
                            setHighlightedSuggestionIndex((current) =>
                              current - 1 >= 0
                                ? current - 1
                                : eventSuggestions.length - 1,
                            );
                            return;
                          }
                          if (event.key === "Escape") {
                            setShowSuggestions(false);
                            return;
                          }
                          if (event.key === "Enter") {
                            event.preventDefault();
                            if (!isSearchingAlert) {
                              if (
                                showSuggestions &&
                                eventSuggestions.length > 0
                              ) {
                                const selected =
                                  eventSuggestions[highlightedSuggestionIndex];
                                if (selected?.event_id) {
                                  setAlertEventId(String(selected.event_id));
                                  setShowSuggestions(false);
                                  void performAlertSearch(
                                    String(selected.event_id),
                                  );
                                  return;
                                }
                              }
                              void performAlertSearch(alertEventId);
                            }
                          }
                        }}
                        placeholder={t(
                          "analytics.alertInvestigation.eventIdPlaceholder",
                        )}
                        className="h-14 w-full min-w-0 rounded-xl border border-[#1f2e45] bg-[#0b1220] px-4 py-3 text-sm font-mono text-slate-100 shadow-inner placeholder:text-slate-500 focus:border-[#3b82f6] focus:outline-none"
                      />

                      {showSuggestions && (
                        <div className="absolute left-0 right-0 top-[calc(100%+8px)] z-20 rounded-xl border border-[#1f2e45] bg-[#0b1220] shadow-xl">
                          {suggestionsLoading ? (
                            <div className="flex items-center gap-2 px-3 py-2 text-[10px] text-slate-300">
                              <Loader2 size={10} className="animate-spin" />
                              {t(
                                "analytics.alertInvestigation.loadingMatches",
                              )}
                            </div>
                          ) : eventSuggestions.length > 0 ? (
                            <div className="max-h-44 overflow-y-auto">
                              {eventSuggestions.map((suggestion, index) => (
                                <button
                                  type="button"
                                  key={String(suggestion.event_id)}
                                  onMouseDown={(mouseEvent) =>
                                    mouseEvent.preventDefault()
                                  }
                                  onClick={() => {
                                    const selectedId = String(
                                      suggestion.event_id,
                                    );
                                    setAlertEventId(selectedId);
                                    setShowSuggestions(false);
                                    void performAlertSearch(selectedId);
                                  }}
                                  className={`flex w-full items-start justify-between gap-2 border-b border-white/5 px-3 py-2 text-left last:border-b-0 ${
                                    highlightedSuggestionIndex === index
                                      ? "bg-[#142235]"
                                      : "bg-transparent"
                                  }`}
                                >
                                  <div className="min-w-0">
                                    <div className="truncate font-mono text-[10px] text-slate-100">
                                      {String(suggestion.event_id)}
                                    </div>
                                    <div className="mt-1 truncate text-[9px] text-slate-400">
                                      {String(suggestion.detection_type || "")}{" "}
                                      {suggestion.detection_type &&
                                      suggestion.severity
                                        ? "·"
                                        : ""}{" "}
                                      {String(suggestion.severity || "")}
                                      {suggestion.camera_name
                                        ? ` · ${String(suggestion.camera_name)}`
                                        : ""}
                                    </div>
                                  </div>
                                </button>
                              ))}
                            </div>
                          ) : (
                            <div className="px-3 py-2 text-[10px] text-slate-400">
                              {t(
                                "analytics.alertInvestigation.noMatchingAlertIds",
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    <button
                      type="button"
                      onClick={() => void performAlertSearch(alertEventId)}
                      disabled={isSearchingAlert}
                      className="inline-flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-[#1d4ed8] text-white shadow-md transition hover:bg-[#2d5ce8] disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isSearchingAlert ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <Search size={16} />
                      )}
                    </button>
                  </div>

                  <p className="text-[10px] text-slate-400">
                    {t("analytics.alertInvestigation.eventIdPlaceholder")}
                  </p>

                  {alertEventError && (
                    <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-2 py-2 text-[11px] text-red-200">
                      {alertEventError === "Alert not found" ? (
                        <>
                          <div className="font-bold">
                            {t("analytics.alertInvestigation.alertNotFound")}
                          </div>
                          <div className="text-red-200/80">
                            {t("analytics.alertInvestigation.noAlertMatches")}
                          </div>
                        </>
                      ) : (
                        getAlertEventErrorMessage(alertEventError, t)
                      )}
                    </div>
                  )}
                </div>

                {!alertEvent && !alertEventError && !isSearchingAlert && (
                  <div className="rounded-lg border border-dashed border-[#1f2e45] bg-[#0b1220]/60 p-3 text-[11px] text-slate-400">
                    {t("analytics.alertInvestigation.noAlertSelected")}
                  </div>
                )}

                {isSearchingAlert && (
                  <div className="flex items-center gap-2 rounded-lg border border-[#1f2e45] bg-[#0b1220] px-3 py-2 text-[11px] text-slate-300">
                    <Loader2
                      size={12}
                      className="animate-spin text-[#60a5fa]"
                    />
                    {t("analytics.alertInvestigation.loadingAlertDetails")}
                  </div>
                )}

                {alertEvent && !isSearchingAlert && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0 text-sm font-bold text-white">
                        {getAlertDescription(alertEvent.detection_type, t)}
                      </div>
                      <button
                        type="button"
                        onClick={clearAlertInvestigation}
                        className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-[#1f2e45] bg-[#0b1220] px-2 py-1 text-[10px] text-slate-200"
                      >
                        <X size={10} /> {t("common.clear")}
                      </button>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-300">
                      <div className="rounded-lg border border-[#1f2e45] bg-[#0b1220] p-2">
                        <div className="text-slate-500">
                          {t("analytics.alertInvestigation.severity")}
                        </div>
                        <div className="mt-1 text-slate-100">
                          {String(alertEvent.severity ?? "-")}
                        </div>
                      </div>
                      <div className="rounded-lg border border-[#1f2e45] bg-[#0b1220] p-2">
                        <div className="text-slate-500">
                          {t("analytics.alertInvestigation.confidence")}
                        </div>
                        <div className="mt-1 text-slate-100">
                          {typeof alertEvent.confidence === "number"
                            ? `${(alertEvent.confidence * 100).toFixed(1)}%`
                            : "-"}
                        </div>
                      </div>
                      <div className="rounded-lg border border-[#1f2e45] bg-[#0b1220] p-2">
                        <div className="text-slate-500">
                          {t("analytics.alertInvestigation.camera")}
                        </div>
                        <div className="mt-1 text-slate-100">
                          {alertCamera?.camera_name ?? "-"}
                        </div>
                      </div>
                      <div className="rounded-lg border border-[#1f2e45] bg-[#0b1220] p-2">
                        <div className="text-slate-500">
                          {t("analytics.alertInvestigation.location")}
                        </div>
                        <div className="mt-1 text-slate-100">
                          {alertCamera?.location ?? "-"}
                        </div>
                      </div>
                      <div className="col-span-2 rounded-lg border border-[#1f2e45] bg-[#0b1220] p-2">
                        <div className="text-slate-500">
                          {t("analytics.alertInvestigation.detectedAt")}
                        </div>
                        <div className="mt-1 text-slate-100">
                          {formatEventTimestamp(
                            alertEvent.created_at,
                            i18n.language,
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="rounded-lg border border-[#1f2e45] bg-[#0b1220] p-3">
                      <div className="mb-2 flex items-center justify-between text-[10px] font-bold uppercase tracking-[0.18em] text-slate-300">
                        <span>
                          {t("analytics.alertInvestigation.evidence")}
                        </span>
                        {screenshotUrl && (
                          <button
                            type="button"
                            onClick={() => setShowScreenshotModal(true)}
                            className="inline-flex items-center gap-1 text-slate-200"
                          >
                            <Eye size={10} /> {t("common.view")}
                          </button>
                        )}
                      </div>

                      {screenshotLoading ? (
                        <div className="flex min-h-[120px] items-center justify-center gap-2 rounded-lg border border-dashed border-[#1f2e45] bg-[#0b1220] text-[11px] text-slate-300">
                          <Loader2 size={12} className="animate-spin" />{" "}
                          {t("analytics.alertInvestigation.loadingEvidence")}
                        </div>
                      ) : screenshotUrl ? (
                        <img
                          src={screenshotUrl}
                          alt={t("analytics.alertInvestigation.alertEvidenceAlt")}
                          className="max-h-[160px] w-full rounded-lg object-contain"
                        />
                      ) : (
                        <div className="flex min-h-[120px] items-center justify-center gap-2 rounded-lg border border-dashed border-[#1f2e45] bg-[#0b1220] text-[11px] text-slate-400">
                          <ImageOff size={12} />{" "}
                          {t("analytics.alertInvestigation.evidenceUnavailable")}
                        </div>
                      )}
                    </div>

                    <div className="rounded-lg border border-[#1f2e45] bg-[#0b1220] p-2">
                      <div className="flex items-center justify-between gap-2">
                        <div>
                          <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-300">
                            {t("analytics.alertInvestigation.technicalReference")}
                          </div>
                          <div className="mt-1 text-slate-500">
                            {t("analytics.alertInvestigation.eventId")}
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={async () => {
                            const eventId = String(alertEvent.event_id ?? "");
                            if (!eventId) return;
                            try {
                              await navigator.clipboard.writeText(eventId);
                              toast.success(
                                "Event ID copied",
                                "The Event ID was copied to the clipboard.",
                              );
                            } catch {
                              toast.error(
                                "Copy failed",
                                "Unable to copy the Event ID.",
                              );
                            }
                          }}
                          className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-[#1f2e45] bg-[#0d1527] px-2 py-1 text-[10px] text-slate-200"
                        >
                          <Copy size={10} />{" "}
                          {t("analytics.alertInvestigation.copyId")}
                        </button>
                      </div>
                      <div className="mt-1 break-all font-mono text-[10px] text-slate-100">
                        {String(alertEvent.event_id ?? "-")}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {showScreenshotModal && screenshotUrl && (
              <div className="fixed inset-0 z-[50] flex items-center justify-center bg-black/70 p-4">
                <div className="relative max-h-[90vh] max-w-[90vw] overflow-hidden rounded-xl border border-[#162235] bg-[#0d1527] p-3">
                  <button
                    type="button"
                    onClick={() => setShowScreenshotModal(false)}
                    className="absolute right-3 top-3 rounded-md bg-white/5 p-1 text-slate-300"
                  >
                    <X size={14} />
                  </button>
                  <img
                    src={screenshotUrl}
                    alt="Expanded alert evidence"
                    className="max-h-[80vh] max-w-[80vw] rounded-lg object-contain"
                  />
                </div>
              </div>
            )}
          </section>

          {/* FOURTH ROW - HEATMAP & TOP CAMERAS */}
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Detection Heatmap */}
            <div className="bg-[#0d1527] border border-[#162235] rounded-xl p-5 flex flex-col justify-between">
              <h3 className="text-sm font-bold font-display tracking-wide text-white mb-5">
                {t("analytics.chartTitles.heatmap")}
              </h3>

              <div className="grid grid-cols-12 gap-2 py-2 flex-1 items-end">
                {heatmap.map((item, index) => {
                  const intensity =
                    heatmapMaxCount > 0
                      ? Math.min(1, item.count / heatmapMaxCount)
                      : 0;
                  let bgClass = "bg-[#064e3b]";
                  if (intensity > 0.8) bgClass = "bg-[#22c55e]";
                  else if (intensity > 0.6) bgClass = "bg-[#10b981]";
                  else if (intensity > 0.4) bgClass = "bg-[#059669]";
                  else if (intensity > 0.2) bgClass = "bg-[#047857]";
                  else if (intensity > 0.05) bgClass = "bg-[#065f46]";

                  return (
                    <div
                      key={index}
                      className="flex flex-col items-center gap-2"
                    >
                      <div
                        className={`w-full h-8 rounded-sm ${bgClass} border border-white/5 transition-all duration-300 hover:brightness-125 hover:-translate-y-0.5 cursor-help`}
                        title={`${item.count} detections`}
                      />
                      <span className="text-[10px] font-mono text-slate-500 font-bold tracking-tight select-none">
                        {item.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Top Cameras by Activity Table */}
            <div className="bg-[#0d1527] border border-[#162235] rounded-xl p-5 flex flex-col justify-between">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold font-display tracking-wide text-white">
                  {t("analytics.chartTitles.topCameras")}
                </h3>
                <a
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    console.log("Viewing all devices...");
                  }}
                  className="text-xs font-semibold text-[#10b981] hover:underline"
                >
                  View All Devices
                </a>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="text-[#64748b] border-b border-[#162235] font-semibold text-[10px] tracking-wider">
                      <th className="pb-2">
                        {t("analytics.tableHeaders.camera")}
                      </th>
                      <th className="pb-2">
                        {t("analytics.tableHeaders.location")}
                      </th>
                      <th className="pb-2">
                        {t("analytics.tableHeaders.detections")}
                      </th>
                      <th className="pb-2 text-right">
                        {t("analytics.tableHeaders.status")}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {topCameras.map((cam) => (
                      <tr
                        key={cam.camera_id}
                        className="hover:bg-white/[0.01] transition-colors"
                      >
                        <td className="py-2.5 flex items-center gap-2 font-bold text-white pr-2">
                          <div className="p-1.5 bg-[#162235] text-slate-300 rounded">
                            <Video size={12} />
                          </div>
                          <span className="truncate max-w-[130px]">
                            {cam.camera_name}
                          </span>
                        </td>
                        <td className="py-2.5 text-slate-400 font-medium truncate max-w-[140px] pr-2">
                          {cam.location}
                        </td>
                        <td className="py-2.5 text-slate-300 font-semibold font-mono">
                          {cam.count > 0 ? cam.count.toLocaleString() : "—"}
                        </td>
                        <td className="py-2.5 text-right">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-[8px] font-black tracking-wider uppercase border select-none ${
                              (cam.status || "").toLowerCase() ===
                                "operational" ||
                              (cam.status || "").toLowerCase() === "running" ||
                              (cam.status || "").toLowerCase() ===
                                "processing" ||
                              (cam.status || "").toLowerCase() ===
                                "streaming" ||
                              (cam.status || "").toLowerCase() === "connected"
                                ? "bg-[#10b981]/10 text-[#10b981] border-[#10b981]/20"
                                : "bg-[#f97316]/10 text-[#f97316] border-[#f97316]/20"
                            }`}
                          >
                            {cam.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </>
      )}

      {/* FOOTER POWERED BY PANEL */}
      <footer className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 pt-4 tracking-wide select-none">
        <Gauge size={12} />
        <span>{t("analytics.poweredBy").toUpperCase()}</span>
      </footer>
    </div>
  );
};

export default memo(Analytics);
