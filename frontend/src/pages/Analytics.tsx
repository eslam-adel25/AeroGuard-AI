import { memo, useCallback, useEffect, useMemo, useState } from "react";
import type { ComponentType } from "react";
import { useTranslation } from "react-i18next";
import { cameraService, reportService } from "../services/api";
import { createSocket, type WSMessage } from "../services/socket";
import {
  AlertTriangle,
  Car,
  Crosshair,
  Flame,
  Gauge,
  Radar,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Siren,
  Users,
  Video,
  Shield,
  FileText,
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
  severity: "Critical" | "High" | "Medium" | "Low";
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
  const { t } = useTranslation();
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

  const loadCameras = useCallback(async () => {
    const res = await cameraService.getAll();
    const mapped = (res.data as CameraOption[]).map((cam) => ({
      camera_id: cam.camera_id,
      camera_name: cam.camera_name,
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
  const recentAlerts = useMemo(
    () => dashboard?.recent_alerts ?? [],
    [dashboard],
  );
  const heatmap = useMemo(() => dashboard?.charts?.heatmap ?? [], [dashboard]);
  const zoneFrequencyData = useMemo(
    () => dashboard?.charts?.frequency_by_zone ?? [],
    [dashboard],
  );

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
        trend: `${total.toLocaleString()} detections in the selected window`,
        trendColor: "text-[#10b981]",
        iconColor: "text-[#10b981]",
      },
      {
        key: "critical",
        title: t("analytics.kpis.criticalAlerts"),
        value: critical.toLocaleString(),
        icon: Siren,
        tone: "text-[#ef4444]",
        trend: `${critical.toLocaleString()} critical alerts from the database`,
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
        trend: `${high.toLocaleString()} high-severity detections`,
        trendColor: "text-slate-400",
        iconColor: "text-[#f97316]",
      },
      {
        key: "medium",
        title: t("analytics.kpis.mediumAlerts"),
        value: medium.toLocaleString(),
        icon: AlertTriangle,
        tone: "text-[#f59e0b]",
        trend: `${medium.toLocaleString()} medium-severity detections`,
        trendColor: "text-slate-400",
        iconColor: "text-[#f59e0b]",
      },
      {
        key: "low",
        title: t("analytics.kpis.lowAlerts"),
        value: low.toLocaleString(),
        icon: ShieldCheck,
        tone: "text-[#3b82f6]",
        trend: `${low.toLocaleString()} low-severity detections`,
        trendColor: "text-slate-400",
        iconColor: "text-[#3b82f6]",
      },
      {
        key: "suspicious",
        title: "Suspicious Objects",
        value: suspiciousObjects.toLocaleString(),
        icon: Shield,
        tone: "text-[#ef4444]",
        trend: `${suspiciousObjects.toLocaleString()} unknown or suspicious objects`,
        trendColor: "text-slate-400",
        iconColor: "text-[#ef4444]",
      },
      {
        key: "fire",
        title: t("analytics.kpis.fire"),
        value: fire.toLocaleString(),
        icon: Flame,
        tone: "text-[#ef4444]",
        trend: `${fire.toLocaleString()} fire or smoke detections`,
        trendColor: "text-slate-400",
        iconColor: "text-[#ef4444]",
      },
      {
        key: "persons",
        title: t("analytics.kpis.persons"),
        value: persons.toLocaleString(),
        icon: Users,
        tone: "text-[#10b981]",
        trend: `${persons.toLocaleString()} person detections`,
        trendColor: "text-slate-400",
        iconColor: "text-[#10b981]",
      },
      {
        key: "vehicles",
        title: t("analytics.kpis.vehicles"),
        value: vehicles.toLocaleString(),
        icon: Car,
        tone: "text-[#10b981]",
        trend: `${vehicles.toLocaleString()} vehicle detections`,
        trendColor: "text-slate-400",
        iconColor: "text-[#10b981]",
      },
      {
        key: "avg",
        title: t("analytics.kpis.averageConfidence"),
        value: `${avgConf.toFixed(1)}%`,
        icon: Crosshair,
        tone: "text-[#10b981]",
        trend: `${avgConf.toFixed(1)}% average confidence from detections`,
        trendColor: "text-[#10b981]",
        iconColor: "text-[#10b981]",
      },
      {
        key: "active",
        title: t("analytics.kpis.activeCameras"),
        value: active.toLocaleString(),
        icon: Video,
        tone: "text-[#10b981]",
        trend: `${active.toLocaleString()} connected cameras for ${selectedCameraName}`,
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
      if (normalized === "fire/smoke" || normalized === "fire") {
        countsByCategory.set("Fire", item.count);
        return;
      }
      if (normalized === "person" || normalized === "persons") {
        countsByCategory.set("Person", item.count);
        return;
      }
      if (normalized === "baggage" || normalized === "bag") {
        countsByCategory.set("Baggage", item.count);
        return;
      }
      if (normalized === "vehicle" || normalized === "vehicles") {
        countsByCategory.set("Vehicle", item.count);
        return;
      }
      if (normalized === "suspicious object" || normalized === "suspicious") {
        countsByCategory.set("Suspicious Object", item.count);
        return;
      }
      countsByCategory.set(item.type, item.count);
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
          <span>Total</span>
          <span className="font-semibold text-white">{total}</span>
        </div>
      </div>
    );
  }, []);

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

            {/* Detection Frequency by Zone (Vertical Bar Chart) */}
            <div className="bg-[#0d1527] border border-[#162235] rounded-xl p-5 flex flex-col justify-between">
              <h3 className="text-sm font-bold font-display tracking-wide text-white mb-5">
                {t("analytics.chartTitles.frequency")}
              </h3>
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={zoneFrequencyData}
                    margin={{ top: 10, right: 5, left: -25, bottom: 5 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#162235"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="name"
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

            {/* Recent Alerts Feed */}
            <div className="bg-[#0d1527] border border-[#162235] rounded-xl p-5 flex flex-col justify-between">
              <h3 className="text-sm font-bold font-display tracking-wide text-white mb-5">
                {t("analytics.chartTitles.recentAlerts")}
              </h3>

              <div className="space-y-3.5 flex-1 overflow-y-auto max-h-[224px] pr-1">
                {recentAlerts.map((alert, idx) => (
                  <div
                    key={`${alert.camera_id}-${alert.time}-${idx}`}
                    className="flex items-center justify-between gap-3 pb-3 border-b border-white/5 last:pb-0 last:border-0"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      {/* Alert Icon (Alarm Beacon style) */}
                      <div className="p-2 bg-[#ef4444]/10 border border-[#ef4444]/20 rounded-lg text-[#ef4444] shrink-0">
                        <Siren size={14} className="animate-pulse" />
                      </div>
                      <div className="min-w-0 leading-tight">
                        <p className="text-[11px] font-bold tracking-wide text-slate-100 uppercase truncate">
                          {alert.detection_type}
                        </p>
                        <p className="text-[10px] font-semibold text-slate-400 mt-1 uppercase">
                          {alert.camera_name}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0 text-right">
                      <div className="leading-tight">
                        <span className="text-[10px] font-mono text-slate-300 block">
                          {(alert.confidence * 100).toFixed(1)}%
                        </span>
                        <span className="text-[10px] font-bold text-[#ef4444] mt-0.5 block">
                          {alert.severity}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-500 max-w-[70px] truncate leading-tight block">
                        {new Date(alert.time).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
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
