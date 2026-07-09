import { useEffect, useState } from "react";
import { reportService, cameraService } from "../services/api";
import { Loader2, BarChart3, TriangleAlert, ShieldCheck } from "lucide-react";

type CameraItem = {
  camera_id: string;
  camera_name: string;
};

type ReportResponse = {
  summary: {
    total: number;
    violations: number;
    unknown_persons: number;
    average_confidence: number;
  };
  details: Array<{ type: string; count: number }>;
};

const toDateInput = (date: Date) => date.toISOString().slice(0, 10);

const Reports = () => {
  const [loading, setLoading] = useState(false);
  const [cameras, setCameras] = useState<CameraItem[]>([]);
  const [data, setData] = useState<ReportResponse | null>(null);
  const [filters, setFilters] = useState({
    start_date: "",
    end_date: "",
    camera_id: "",
  });

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
      alert("Failed to fetch analytics data.");
    } finally {
      setLoading(false);
    }
  };

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
        alert("Failed to fetch analytics data.");
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
            Analytics Reports
          </h2>
          <p className="text-gray-500 text-sm">
            Unified view of detections and violations
          </p>
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
            <option value="">All Cameras</option>
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
            {loading ? "Loading..." : "Apply"}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="h-56 flex items-center justify-center bg-ag-card rounded-3xl border border-white/5">
          <Loader2 className="animate-spin text-ag-danger" size={34} />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-ag-card p-5 rounded-2xl border border-white/5">
              <div className="flex items-center gap-2 text-gray-400 text-xs uppercase tracking-widest mb-2">
                <BarChart3 size={14} /> Total Detections
              </div>
              <p className="text-3xl font-black">{data?.summary.total ?? 0}</p>
            </div>
            <div className="bg-ag-card p-5 rounded-2xl border border-white/5">
              <div className="flex items-center gap-2 text-gray-400 text-xs uppercase tracking-widest mb-2">
                <TriangleAlert size={14} /> Violations
              </div>
              <p className="text-3xl font-black text-ag-danger">
                {data?.summary.violations ?? 0}
              </p>
            </div>
            <div className="bg-ag-card p-5 rounded-2xl border border-white/5">
              <div className="flex items-center gap-2 text-gray-400 text-xs uppercase tracking-widest mb-2">
                <ShieldCheck size={14} /> Avg Confidence
              </div>
              <p className="text-3xl font-black text-ag-success">
                {data?.summary.average_confidence ?? 0}%
              </p>
            </div>
          </div>

          <div className="bg-ag-card p-6 rounded-3xl border border-white/5">
            <h3 className="text-xl font-bold mb-4">Detection Types</h3>
            {data?.details?.length ? (
              <div className="space-y-3">
                {data.details.map((item, idx) => (
                  <div
                    key={`${item.type}-${idx}`}
                    className="flex items-center justify-between bg-black/20 rounded-xl px-4 py-3"
                  >
                    <span className="text-sm font-semibold text-gray-300">
                      {item.type}
                    </span>
                    <span className="text-sm font-black text-white">
                      {item.count}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">
                No data in selected range.
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default Reports;
