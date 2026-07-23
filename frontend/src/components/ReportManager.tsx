import React, { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { reportService, cameraService } from "../services/api";
import { useNotification } from "./NotificationSystem/useNotification";
import {
  Loader2,
  FileText,
  FileSpreadsheet,
  Trash2,
  Search,
} from "lucide-react";

interface ReportItem {
  report_id: string;
  title?: string;
  generated_at: string;
  report_type?: string;
  filters?: Record<string, unknown>;
  export_history?: Array<{ type: string; timestamp: string }>;
}

const ReportManager: React.FC = () => {
  const { t } = useTranslation();
  const { confirm, toast } = useNotification();
  const [cameras, setCameras] = useState<
    Array<{ camera_id: string; camera_name: string }>
  >([]);
  const [loading, setLoading] = useState(false);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [filters, setFilters] = useState({
    start_date: "",
    end_date: "",
    camera_id: "",
    query: "",
  });
  const [title, setTitle] = useState("");
  const [reportType, setReportType] = useState("custom");

  const loadReports = useCallback(async () => {
    setLoading(true);
    try {
      const res = await reportService.getAllReports({
        limit: 100,
        offset: 0,
        query: filters.query || undefined,
        camera_id: filters.camera_id || undefined,
        start_date: filters.start_date || undefined,
        end_date: filters.end_date || undefined,
      });
      setReports(res.data.items || []);
    } catch (err) {
      console.warn("Failed to load reports", err);
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

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
  }, [loadReports]);

  const handleFilterSearch = async () => {
    await loadReports();
  };

  const downloadFile = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  const handleExport = async (id: string, type: "csv" | "excel" | "pdf") => {
    let toastId: string | null = null;
    try {
      toastId = toast.loading(t("common.processing"), t("common.pleaseWait"));
      let res;
      if (type === "csv") {
        res = await reportService.exportCsv(id);
      } else if (type === "excel") {
        res = await reportService.exportExcel(id);
      } else {
        res = await reportService.exportPdf(id);
      }
      if (toastId) {
        toast.update(toastId, {
          type: "success",
          title: t("reports.exportStarted"),
          description: t("reports.exportStartedDescription"),
        });
      }
      if (type === "csv") {
        downloadFile(res.data, `report-${id}.csv`);
      } else if (type === "excel") {
        downloadFile(res.data, `report-${id}.xlsx`);
      } else {
        downloadFile(res.data, `report-${id}.pdf`);
      }
      await loadReports();
    } catch (err) {
      console.warn(err);
      if (toastId) {
        toast.update(toastId, {
          type: "error",
          title: t("common.status"),
          description: t("reports.exportFailed", { type: type.toUpperCase() }),
        });
      }
    }
  };

  const handleDeleteReport = async (id: string) => {
    confirm({
      title: t("reports.deleteTitle"),
      description: t("reports.deleteDescription"),
      confirmLabel: t("common.delete"),
      cancelLabel: t("common.cancel"),
      type: "warning",
      onConfirm: async () => {
        setLoading(true);
        let toastId: string | null = null;
        try {
          toastId = toast.loading(
            t("common.processing"),
            t("common.pleaseWait"),
          );
          await reportService.deleteReport(id);
          await loadReports();
          if (toastId) {
            toast.update(toastId, {
              type: "success",
              title: t("common.done"),
              description: t("reports.deleteSuccess"),
            });
          }
        } catch (err) {
          console.warn(err);
          if (toastId) {
            toast.update(toastId, {
              type: "error",
              title: t("common.status"),
              description: t("reports.deleteFailed"),
            });
          }
        } finally {
          setLoading(false);
        }
      },
    });
  };

  const handleGenerate = async () => {
    if (!filters.start_date || !filters.end_date) {
      const toastId = toast.loading(
        t("common.processing"),
        t("common.pleaseWait"),
      );
      toast.update(toastId, {
        type: "error",
        title: t("common.status"),
        description: t("reports.generateMissingDates"),
      });
      return;
    }

    setLoading(true);
    let toastId: string | null = null;
    try {
      toastId = toast.loading("Processing", "Please wait...");
      const payload = {
        start_date: filters.start_date,
        end_date: filters.end_date,
        camera_id: filters.camera_id || undefined,
        title: title || undefined,
        report_type: reportType || undefined,
      };
      const res = await reportService.generateReport(payload);
      if (toastId) {
        toast.update(toastId, {
          type: "success",
          title: t("common.done"),
          description: t("reports.generateSuccess", {
            id: res.data.report_id || "",
          }),
        });
      }
      await loadReports();
    } catch (err) {
      console.warn(err);
      if (toastId) {
        toast.update(toastId, {
          type: "error",
          title: t("common.status"),
          description: t("reports.generateFailed"),
        });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-ag-card p-6 rounded-2xl border border-white/5 space-y-4">
      <h3 className="text-lg font-black">{t("reports.managerTitle")}</h3>
      <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={t("reports.titlePlaceholder")}
          className="col-span-2 bg-ag-dark border border-white/10 rounded-xl px-3 py-2 text-sm"
        />
        <select
          value={reportType}
          onChange={(e) => setReportType(e.target.value)}
          className="bg-ag-dark border border-white/10 rounded-xl px-3 py-2 text-sm"
        >
          <option value="custom">{t("reports.reportTypeCustom")}</option>
          <option value="summary">{t("reports.reportTypeSummary")}</option>
          <option value="compliance">
            {t("reports.reportTypeCompliance")}
          </option>
        </select>
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
      </div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <button
          onClick={handleGenerate}
          className="inline-flex items-center justify-center gap-2 bg-ag-success text-white rounded-xl px-4 py-2 font-bold text-sm"
        >
          {loading ? (
            <Loader2 className="animate-spin" />
          ) : (
            t("reports.generateReport")
          )}
        </button>
        <div className="relative w-full sm:w-auto">
          <input
            type="text"
            value={filters.query}
            onChange={(e) =>
              setFilters((p) => ({ ...p, query: e.target.value }))
            }
            placeholder={t("reports.searchReports")}
            className="w-full rounded-xl border border-white/10 bg-ag-dark px-10 py-2 text-sm"
          />
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        </div>
        <button
          onClick={handleFilterSearch}
          className="inline-flex items-center justify-center gap-2 bg-ag-primary text-white rounded-xl px-4 py-2 font-bold text-sm"
        >
          {t("common.search")}
        </button>
      </div>

      <div>
        <h4 className="font-bold">{t("reports.history")}</h4>
        {loading ? (
          <div className="py-4">
            <Loader2 className="animate-spin" />
          </div>
        ) : (
          <div className="space-y-2 max-h-96 overflow-auto">
            {reports.length === 0 && (
              <div className="text-sm text-gray-400">
                {t("reports.noReports")}
              </div>
            )}
            {reports.map((r) => (
              <div
                key={r.report_id}
                className="rounded-2xl border border-white/10 bg-black/10 p-3"
              >
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="font-mono text-sm text-gray-100">
                      {r.report_id}
                    </div>
                    <div className="text-xs text-gray-400">
                      {r.title || t("reports.managerTitle")} —{" "}
                      {new Date(r.generated_at).toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      {r.report_type ?? "custom"} •{" "}
                      {r.filters?.camera_id
                        ? `${t("common.camera")}: ${r.filters.camera_id}`
                        : t("reports.allCameras")}
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={() => handleExport(r.report_id, "csv")}
                      className="inline-flex items-center gap-2 rounded-xl bg-slate-700 px-3 py-2 text-xs font-semibold text-white"
                    >
                      <FileText size={14} /> CSV
                    </button>
                    <button
                      onClick={() => handleExport(r.report_id, "excel")}
                      className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-3 py-2 text-xs font-semibold text-white"
                    >
                      <FileSpreadsheet size={14} /> XLSX
                    </button>
                    <button
                      onClick={() => handleExport(r.report_id, "pdf")}
                      className="inline-flex items-center gap-2 rounded-xl bg-rose-600 px-3 py-2 text-xs font-semibold text-white"
                    >
                      <FileText size={14} /> PDF
                    </button>
                    <button
                      onClick={() => handleDeleteReport(r.report_id)}
                      className="inline-flex items-center gap-2 rounded-xl bg-red-500 px-3 py-2 text-xs font-semibold text-white"
                    >
                      <Trash2 size={14} /> Delete
                    </button>
                  </div>
                </div>
                {r.export_history?.length ? (
                  <div className="mt-3 text-xs text-gray-400">
                    Exported:{" "}
                    {r.export_history
                      .map(
                        (entry) =>
                          `${entry.type.toUpperCase()} @ ${new Date(entry.timestamp).toLocaleString()}`,
                      )
                      .join(" • ")}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportManager;
