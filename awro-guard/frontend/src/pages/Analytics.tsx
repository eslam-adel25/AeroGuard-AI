import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { cameraService, reportService } from "../services/api";
import {
  AlertTriangle,
  Brain,
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
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
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
  fire?: number;
  persons?: number;
  vehicles?: number;
  active_cameras?: number;
  ai_accuracy?: number | null;
};

type DetectionTypeItem = {
  type: string;
  count: number;
};

type TimelineItem = {
  label: string;
  day: string;
  hour: number;
  count: number;
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
  icon: React.ComponentType<{ size?: number; className?: string }>;
  tone: string;
  trend?: string;
};

const PIE_COLORS = ["#ef4444", "#f59e0b", "#3b82f6", "#22c55e"];

const toDateInput = (date: Date) => date.toISOString().slice(0, 10);

const SkeletonCard = memo(() => (
  <div className="rounded-2xl border border-white/5 bg-ag-card p-5 animate-pulse">
    <div className="h-4 w-24 bg-white/10 rounded mb-4" />
    <div className="h-8 w-16 bg-white/10 rounded" />
    <div className="h-3 w-20 bg-white/10 rounded mt-3" />
  </div>
));

const EmptyState = memo(() => {
  const { t } = useTranslation();
  return (
    <div className="rounded-3xl border border-white/10 bg-ag-card p-10 text-center">
      <Radar className="mx-auto mb-4 text-gray-500" size={38} />
      <h3 className="text-xl font-black text-white mb-2">
        {t("analytics.noDataTitle")}
      </h3>
      <p className="text-gray-400 text-sm">{t("analytics.noDataSubtitle")}</p>
    </div>
  );
});

const ErrorCard = memo(({ onRetry }: { onRetry: () => void }) => {
  const { t } = useTranslation();
  return (
    <div className="rounded-3xl border border-red-500/30 bg-red-500/10 p-8">
      <div className="flex items-start gap-4">
        <AlertTriangle className="text-red-400 mt-1" size={24} />
        <div className="flex-1">
          <h3 className="text-lg font-black text-white">
            {t("analytics.errorTitle")}
          </h3>
          <p className="text-red-200/80 text-sm mt-1">
            {t("analytics.errorSubtitle")}
          </p>
        </div>
        <button
          onClick={onRetry}
          className="rounded-xl bg-red-600 hover:bg-red-700 px-4 py-2 text-sm font-bold text-white"
        >
          {t("common.retry")}
        </button>
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

  const hasData = useMemo(() => {
    if (!summary) {
      return false;
    }
    return (summary.total_detections ?? summary.total ?? 0) > 0;
  }, [summary]);

  const kpis = useMemo<KPIItem[]>(() => {
    const total = summary?.total_detections ?? summary?.total ?? 0;
    const critical = summary?.critical_alerts ?? 0;
    const high = summary?.high_alerts ?? 0;
    const medium = summary?.medium_alerts ?? 0;
    const low = summary?.low_alerts ?? 0;
    const weapons = summary?.weapons ?? 0;
    const fire = summary?.fire ?? 0;
    const persons = summary?.persons ?? 0;
    const vehicles = summary?.vehicles ?? 0;
    const avgConf = summary?.average_confidence ?? 0;
    const active = summary?.active_cameras ?? 0;
    const accuracy = summary?.ai_accuracy;

    return [
      {
        key: "total",
        title: t("analytics.kpis.totalDetections"),
        value: total.toLocaleString(),
        icon: Radar,
        tone: "text-red-300",
      },
      {
        key: "critical",
        title: t("analytics.kpis.criticalAlerts"),
        value: critical.toLocaleString(),
        icon: Siren,
        tone: "text-red-400",
      },
      {
        key: "high",
        title: t("analytics.kpis.highAlerts"),
        value: high.toLocaleString(),
        icon: ShieldAlert,
        tone: "text-orange-300",
      },
      {
        key: "medium",
        title: t("analytics.kpis.mediumAlerts"),
        value: medium.toLocaleString(),
        icon: AlertTriangle,
        tone: "text-amber-300",
      },
      {
        key: "low",
        title: t("analytics.kpis.lowAlerts"),
        value: low.toLocaleString(),
        icon: ShieldCheck,
        tone: "text-emerald-300",
      },
      {
        key: "weapons",
        title: t("analytics.kpis.weapons"),
        value: weapons.toLocaleString(),
        icon: Shield,
        tone: "text-red-300",
      },
      {
        key: "fire",
        title: t("analytics.kpis.fire"),
        value: fire.toLocaleString(),
        icon: Flame,
        tone: "text-orange-300",
      },
      {
        key: "persons",
        title: t("analytics.kpis.persons"),
        value: persons.toLocaleString(),
        icon: Users,
        tone: "text-blue-300",
      },
      {
        key: "vehicles",
        title: t("analytics.kpis.vehicles"),
        value: vehicles.toLocaleString(),
        icon: Car,
        tone: "text-cyan-300",
      },
      {
        key: "avg",
        title: t("analytics.kpis.averageConfidence"),
        value: `${avgConf.toFixed(2)}%`,
        icon: Crosshair,
        tone: "text-violet-300",
      },
      {
        key: "active",
        title: t("analytics.kpis.activeCameras"),
        value: active.toLocaleString(),
        icon: Video,
        tone: "text-green-300",
      },
      {
        key: "accuracy",
        title: t("analytics.kpis.aiAccuracy"),
        value:
          accuracy === null || accuracy === undefined ? "N/A" : `${accuracy}%`,
        icon: Brain,
        tone: "text-sky-300",
      },
    ];
  }, [summary, t]);

  const severityPieData = useMemo(
    () =>
      severity.map((item) => ({
        name: item.severity,
        value: item.percentage,
      })),
    [severity],
  );

  const threatBarData = useMemo(
    () => details.map((d) => ({ type: d.type, count: d.count })),
    [details],
  );

  return (
    <div className="p-4 md:p-8 space-y-6 md:space-y-8">
      <section className="bg-ag-card/40 border border-white/5 rounded-3xl p-6 md:p-8 backdrop-blur-xl">
        <div className="flex flex-col xl:flex-row xl:items-end xl:justify-between gap-6">
          <div>
            <h2 className="text-3xl md:text-4xl font-black tracking-tight text-white">
              {t("analytics.pageTitle")}
            </h2>
            <p className="text-gray-400 mt-2 text-sm md:text-base">
              {t("analytics.pageSubtitle")}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 w-full xl:w-auto">
            <input
              type="date"
              value={filters.start_date}
              onChange={(e) =>
                setFilters((prev) => ({ ...prev, start_date: e.target.value }))
              }
              className="bg-ag-dark border border-white/10 rounded-xl px-3 py-2 text-sm"
            />
            <input
              type="date"
              value={filters.end_date}
              onChange={(e) =>
                setFilters((prev) => ({ ...prev, end_date: e.target.value }))
              }
              className="bg-ag-dark border border-white/10 rounded-xl px-3 py-2 text-sm"
            />
            <select
              value={filters.camera_id}
              onChange={(e) =>
                setFilters((prev) => ({ ...prev, camera_id: e.target.value }))
              }
              className="bg-ag-dark border border-white/10 rounded-xl px-3 py-2 text-sm"
            >
              <option value="">{t("analytics.allCameras")}</option>
              {cameraOptions.map((cam) => (
                <option key={cam.camera_id} value={cam.camera_id}>
                  {cam.camera_name}
                </option>
              ))}
            </select>
            <button
              onClick={onRefresh}
              disabled={refreshing}
              className="inline-flex items-center justify-center gap-2 bg-ag-success hover:bg-green-600 disabled:opacity-70 text-white rounded-xl px-4 py-2 font-bold text-sm"
            >
              <RefreshCw
                size={16}
                className={refreshing ? "animate-spin" : ""}
              />
              {t("common.refresh")}
            </button>
          </div>
        </div>
      </section>

      {error ? (
        <ErrorCard onRetry={onRefresh} />
      ) : loading ? (
        <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {Array.from({ length: 12 }).map((_, idx) => (
            <SkeletonCard key={idx} />
          ))}
        </section>
      ) : !hasData ? (
        <EmptyState />
      ) : (
        <>
          <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {kpis.map((kpi) => (
              <article
                key={kpi.key}
                className="rounded-2xl border border-white/5 bg-ag-card p-5 transition-all duration-300 hover:-translate-y-1 hover:border-white/15"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="text-xs uppercase tracking-widest text-gray-400 font-bold">
                    {kpi.title}
                  </div>
                  <kpi.icon size={20} className={kpi.tone} />
                </div>
                <div className="text-3xl font-black text-white">
                  {kpi.value}
                </div>
                <div className="text-[11px] text-gray-500 mt-2">
                  {kpi.trend ?? t("analytics.liveDataset")}
                </div>
              </article>
            ))}
          </section>

          <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <div className="rounded-2xl border border-white/5 bg-ag-card p-5">
              <h3 className="text-lg font-black mb-4">
                {t("analytics.chartTitles.timeline")}
              </h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={timeline}>
                    <defs>
                      <linearGradient
                        id="timelineGradient"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="5%"
                          stopColor="#ef4444"
                          stopOpacity={0.45}
                        />
                        <stop
                          offset="95%"
                          stopColor="#ef4444"
                          stopOpacity={0.03}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff12" />
                    <XAxis
                      dataKey="label"
                      stroke="#94a3b8"
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis stroke="#94a3b8" allowDecimals={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#10151f",
                        border: "1px solid #ffffff22",
                        borderRadius: "12px",
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="count"
                      stroke="#ef4444"
                      strokeWidth={2}
                      fill="url(#timelineGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-2xl border border-white/5 bg-ag-card p-5">
              <h3 className="text-lg font-black mb-4">
                {t("analytics.chartTitles.distribution")}
              </h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={threatBarData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff12" />
                    <XAxis
                      dataKey="type"
                      stroke="#94a3b8"
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis stroke="#94a3b8" allowDecimals={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#10151f",
                        border: "1px solid #ffffff22",
                        borderRadius: "12px",
                      }}
                    />
                    <Bar dataKey="count" fill="#f59e0b" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>

          <section className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <div className="xl:col-span-2 rounded-2xl border border-white/5 bg-ag-card p-5">
              <h3 className="text-lg font-black mb-4">
                {t("analytics.chartTitles.frequency")}
              </h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={timeline}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff12" />
                    <XAxis
                      dataKey="label"
                      stroke="#94a3b8"
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis stroke="#94a3b8" allowDecimals={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#10151f",
                        border: "1px solid #ffffff22",
                        borderRadius: "12px",
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="count"
                      stroke="#38bdf8"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-2xl border border-white/5 bg-ag-card p-5">
              <h3 className="text-lg font-black mb-4">
                {t("analytics.chartTitles.severity")}
              </h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#10151f",
                        border: "1px solid #ffffff22",
                        borderRadius: "12px",
                      }}
                    />
                    <Legend />
                    <Pie
                      data={severityPieData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={50}
                      outerRadius={88}
                      paddingAngle={4}
                    >
                      {severityPieData.map((entry, index) => (
                        <Cell
                          key={`${entry.name}-${index}`}
                          fill={PIE_COLORS[index % PIE_COLORS.length]}
                        />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>

          <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <div className="rounded-2xl border border-white/5 bg-ag-card p-5">
              <h3 className="text-lg font-black mb-4">
                {t("analytics.chartTitles.topCameras")}
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-400 border-b border-white/10">
                      <th className="py-2">
                        {t("analytics.tableHeaders.camera")}
                      </th>
                      <th className="py-2">
                        {t("analytics.tableHeaders.location")}
                      </th>
                      <th className="py-2">
                        {t("analytics.tableHeaders.detections")}
                      </th>
                      <th className="py-2">
                        {t("analytics.tableHeaders.status")}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {topCameras.map((cam) => (
                      <tr
                        key={cam.camera_id}
                        className="border-b border-white/5"
                      >
                        <td className="py-2 font-semibold text-white">
                          {cam.camera_name}
                        </td>
                        <td className="py-2 text-gray-300">{cam.location}</td>
                        <td className="py-2 text-gray-300">{cam.count}</td>
                        <td className="py-2">
                          <span
                            className={`px-2 py-1 rounded-full text-xs font-bold ${
                              cam.status.toLowerCase() === "online"
                                ? "bg-green-500/20 text-green-300"
                                : "bg-gray-500/20 text-gray-300"
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

            <div className="rounded-2xl border border-white/5 bg-ag-card p-5">
              <h3 className="text-lg font-black mb-4">
                {t("analytics.chartTitles.recentAlerts")}
              </h3>
              <div className="space-y-3 max-h-[340px] overflow-auto pr-1">
                {recentAlerts.map((alert, idx) => (
                  <div
                    key={`${alert.camera_id}-${alert.time}-${idx}`}
                    className="rounded-xl bg-black/20 border border-white/5 p-3"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm font-bold text-white">
                        {alert.detection_type}
                      </p>
                      <span className="text-[11px] text-gray-400">
                        {new Date(alert.time).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-xs text-gray-300">
                      <span>{alert.camera_name}</span>
                      <span>{(alert.confidence * 100).toFixed(1)}%</span>
                      <span>{alert.severity}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-white/5 bg-ag-card p-5">
            <h3 className="text-lg font-black mb-4">
              {t("analytics.chartTitles.heatmap")}
            </h3>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={heatmap}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff12" />
                  <XAxis dataKey="label" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#10151f",
                      border: "1px solid #ffffff22",
                      borderRadius: "12px",
                    }}
                  />
                  <Bar dataKey="count" fill="#a855f7" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>
        </>
      )}

      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Gauge size={14} />
        <span>{t("analytics.poweredBy")}</span>
      </div>
    </div>
  );
};

export default memo(Analytics);
