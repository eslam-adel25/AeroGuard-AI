import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNotification } from "../components/NotificationSystem/useNotification";
import { reportService, cameraService } from "../services/api";
import { Loader2, BarChart3, TriangleAlert, ShieldCheck } from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ReportManager from "../components/ReportManager";

type CameraItem = {
  camera_id: string;
  camera_name: string;
};

type TimelinePoint = {
  label: string;
  date: string;
  count: number;
};

type DetectionTypeItem = {
  type: string;
  count: number;
};

type TopCameraItem = {
  camera_id: string;
  camera_name: string;
  location: string;
  status: string;
  count: number;
};

type SeverityItem = {
  severity: string;
  count: number;
  percentage: number;
};

type ReportResponse = {
  summary: {
    total: number;
    violations: number;
    unknown_persons: number;
    average_confidence: number;
    total_detections?: number;
    critical_alerts?: number;
    high_alerts?: number;
    medium_alerts?: number;
    low_alerts?: number;
    fire_detections?: number;
    smoke_detections?: number;
    weapon_detections?: number;
    person_detections?: number;
    vehicle_detections?: number;
    active_cameras?: number;
    ai_accuracy?: number | null;
  };
  details: DetectionTypeItem[];
  charts?: {
    timeline?: TimelinePoint[];
    threat_distribution?: DetectionTypeItem[];
    severity_distribution?: SeverityItem[];
    top_cameras?: TopCameraItem[];
    heatmap?: Array<{ hour: number; label: string; count: number }>;
  };
  recent_alerts?: Array<{
    time: string;
    camera_id: string;
    camera_name: string;
    detection_type: string;
    confidence: number;
    severity: string;
  }>;
};

const toDateInput = (date: Date) => date.toISOString().slice(0, 10);

const Reports = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [cameras, setCameras] = useState<CameraItem[]>([]);
  const [data, setData] = useState<ReportResponse | null>(null);
  const [filters, setFilters] = useState({
    start_date: "",
    end_date: "",
    camera_id: "",
  });

  const { toast } = useNotification();

  const loadReports = async (activeFilters = filters) => {
    setLoading(true);
    try {
      const res = await reportService.getDashboard({
        start_date: activeFilters.start_date,
        end_date: activeFilters.end_date,
        camera_id: activeFilters.camera_id || undefined,
      });
      setData(res.data);
    } catch {
      setData(null);
      toast.error("Operation Failed", "Failed to fetch analytics data.");
    } finally {
      setLoading(false);
    }
  };

  const timeline = useMemo(() => data?.charts?.timeline ?? [], [data]);

  const threatDistribution = useMemo(
    () => data?.charts?.threat_distribution ?? data?.details ?? [],
    [data],
  );

  const severityDistribution = useMemo(
    () => data?.charts?.severity_distribution ?? [],
    [data],
  );

  const topCameras = useMemo(() => data?.charts?.top_cameras ?? [], [data]);

  // hasData not currently used in UI

  useEffect(() => {
    const now = new Date();
    const defaults = {
      start_date: toDateInput(
        new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000),
      ),
      end_date: toDateInput(now),
      camera_id: "",
    };

    setFilters(defaults);

    (async () => {
      // inline loadCameras
      try {
        const res = await cameraService.getAll();
        setCameras(res.data);
      } catch {
        setCameras([]);
      }

      // inline loadReports
      setLoading(true);
      try {
        const res = await reportService.getDashboard({
          start_date: defaults.start_date,
          end_date: defaults.end_date,
          camera_id: undefined,
        });
        setData(res.data);
      } catch {
        setData(null);
        toast.error(t("common.status"), t("reports.fetchFailed"));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="p-8 space-y-8">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between bg-ag-card/30 p-6 rounded-3xl border border-white/5">
        <div>
          <h2 className="text-3xl font-black tracking-tight text-white">
            {t("reports.pageTitle")}
          </h2>
          <p className="text-gray-500 text-sm">{t("reports.pageSubtitle")}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 w-full xl:w-auto">
          <input
            type="date"
            value={filters.start_date}
            onChange={(e) =>
              setFilters((p) => ({ ...p, start_date: e.target.value }))
            }
            className="bg-ag-dark border border-white/10 rounded-xl px-3 py-2 text-sm"
          />
          <input
            type="date"
            value={filters.end_date}
            onChange={(e) =>
              setFilters((p) => ({ ...p, end_date: e.target.value }))
            }
            className="bg-ag-dark border border-white/10 rounded-xl px-3 py-2 text-sm"
          />
          <select
            value={filters.camera_id}
            onChange={(e) =>
              setFilters((p) => ({ ...p, camera_id: e.target.value }))
            }
            className="bg-ag-dark border border-white/10 rounded-xl px-3 py-2 text-sm"
          >
            <option value="">{t("reports.allCameras")}</option>
            {cameras.map((c) => (
              <option key={c.camera_id} value={c.camera_id}>
                {c.camera_name}
              </option>
            ))}
          </select>
          <button
            onClick={() => {
              void loadReports();
            }}
            disabled={loading}
            className="bg-ag-success hover:bg-green-600 text-white rounded-xl px-4 py-2 font-bold text-sm"
          >
            {loading ? t("common.loading") : t("common.apply")}
          </button>
        </div>
      </div>

      <ReportManager />

      {loading ? (
        <div className="h-56 flex items-center justify-center bg-ag-card rounded-3xl border border-white/5">
          <Loader2 className="animate-spin text-ag-danger" size={34} />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-ag-card p-5 rounded-2xl border border-white/5">
              <div className="flex items-center gap-2 text-gray-400 text-xs uppercase tracking-widest mb-2">
                <BarChart3 size={14} /> {t("analytics.kpis.totalDetections")}
              </div>
              <p className="text-3xl font-black">{data?.summary.total ?? 0}</p>
            </div>
            <div className="bg-ag-card p-5 rounded-2xl border border-white/5">
              <div className="flex items-center gap-2 text-gray-400 text-xs uppercase tracking-widest mb-2">
                <TriangleAlert size={14} /> {t("analytics.kpis.criticalAlerts")}
              </div>
              <p className="text-3xl font-black text-ag-danger">
                {data?.summary.violations ?? 0}
              </p>
            </div>
            <div className="bg-ag-card p-5 rounded-2xl border border-white/5">
              <div className="flex items-center gap-2 text-gray-400 text-xs uppercase tracking-widest mb-2">
                <ShieldCheck size={14} />{" "}
                {t("analytics.kpis.averageConfidence")}
              </div>
              <p className="text-3xl font-black text-ag-success">
                {data?.summary.average_confidence ?? 0}%
              </p>
            </div>
          </div>

          <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <div className="rounded-2xl border border-white/5 bg-ag-card p-5">
              <h3 className="text-xl font-bold mb-4">
                {t("analytics.chartTitles.timeline")}
              </h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={timeline}>
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
                      stroke="#3b82f6"
                      fill="#3b82f6"
                      fillOpacity={0.18}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-2xl border border-white/5 bg-ag-card p-5">
              <h3 className="text-xl font-bold mb-4">
                {t("analytics.chartTitles.distribution")}
              </h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={threatDistribution}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff12" />
                    <XAxis
                      dataKey="type"
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
                    <Bar dataKey="count" fill="#f59e0b" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>

          <section className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <div className="xl:col-span-2 rounded-2xl border border-white/5 bg-ag-card p-5">
              <h3 className="text-xl font-bold mb-4">
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
              <h3 className="text-xl font-bold mb-4">
                {t("analytics.chartTitles.severity")}
              </h3>
              {severityDistribution.length ? (
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
                        data={severityDistribution}
                        dataKey="percentage"
                        nameKey="severity"
                        innerRadius={42}
                        outerRadius={88}
                        paddingAngle={4}
                      >
                        {severityDistribution.map((entry, index) => (
                          <Cell
                            key={`${entry.severity}-${index}`}
                            fill={
                              ["#ef4444", "#f59e0b", "#3b82f6", "#22c55e"][
                                index % 4
                              ]
                            }
                          />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-gray-400 text-sm">
                  {t("analytics.noSeverityChart")}
                </p>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
};

export default Reports;
