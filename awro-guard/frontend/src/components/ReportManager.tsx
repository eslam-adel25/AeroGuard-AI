import React, { useEffect, useState } from "react";
import { reportService, cameraService } from "../services/api";
import { Loader2 } from "lucide-react";

interface ReportItem {
  report_id: string;
  title?: string;
  generated_at: string;
}

const ReportManager: React.FC = () => {
  const [cameras, setCameras] = useState<
    Array<{ camera_id: string; camera_name: string }>
  >([]);
  const [loading, setLoading] = useState(false);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [filters, setFilters] = useState({
    start_date: "",
    end_date: "",
    camera_id: "",
  });

  useEffect(() => {
    (async () => {
      try {
        const res = await cameraService.getAll();
        setCameras(res.data || []);
      } catch {
        setCameras([]);
      }
      await loadReports();
    })();
  }, []);

  const loadReports = async () => {
    setLoading(true);
    try {
      const res = await reportService.getAllReports();
      setReports(res.data.items || []);
    } catch (err) {
      console.warn("Failed to load reports", err);
      setReports([]);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!filters.start_date || !filters.end_date)
      return alert("Please select start and end dates");
    setLoading(true);
    try {
      const payload = {
        start_date: filters.start_date,
        end_date: filters.end_date,
        camera_id: filters.camera_id || undefined,
      };
      const res = await reportService.generateReport(payload);
      alert("Report generated: " + (res.data.report_id || ""));
      await loadReports();
    } catch (err) {
      console.warn(err);
      alert("Failed to generate report");
    } finally {
      setLoading(false);
    }
  };

  const handleExportCsv = async (id: string) => {
    try {
      const res = await reportService.exportCsv(id);
      const blob = new Blob([res.data], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report-${id}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.warn(err);
      alert("Failed to export CSV");
    }
  };

  return (
    <div className="bg-ag-card p-6 rounded-2xl border border-white/5 space-y-4">
      <h3 className="text-lg font-black">Reports Manager</h3>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
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
          onClick={handleGenerate}
          className="bg-ag-success text-white rounded-xl px-4 py-2 font-bold text-sm"
        >
          {loading ? <Loader2 className="animate-spin" /> : "Generate"}
        </button>
      </div>

      <div>
        <h4 className="font-bold">History</h4>
        {loading ? (
          <div className="py-4">
            <Loader2 className="animate-spin" />
          </div>
        ) : (
          <div className="space-y-2 max-h-48 overflow-auto">
            {reports.length === 0 && (
              <div className="text-sm text-gray-400">No reports yet</div>
            )}
            {reports.map((r) => (
              <div
                key={r.report_id}
                className="flex items-center justify-between"
              >
                <div>
                  <div className="font-mono text-sm">{r.report_id}</div>
                  <div className="text-xs text-gray-400">
                    {r.title || "Report"} —{" "}
                    {new Date(r.generated_at).toLocaleString()}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleExportCsv(r.report_id)}
                    className="text-sm bg-ag-primary text-white px-3 py-1 rounded"
                  >
                    CSV
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportManager;
