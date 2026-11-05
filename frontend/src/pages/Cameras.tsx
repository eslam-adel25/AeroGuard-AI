import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { cameraService } from "../services/api";
import { useNotification } from "../components/NotificationSystem/useNotification";
import {
  Plus,
  Play,
  Upload,
  Radio,
  X,
  Loader2,
  Video,
  MapPin,
  Map,
  Link,
  Eye,
  Shield,
  Laptop,
  CheckCircle2,
  Sliders,
  FolderOpen,
  Camera as CameraIcon,
  Compass,
} from "lucide-react";

const isValidLiveRtspUrl = (value: string) => {
  try {
    const parsed = new URL(value.trim());
    return (
      ["rtsp:", "rtsps:"].includes(parsed.protocol) &&
      parsed.hostname.length > 0
    );
  } catch {
    return false;
  }
};

const getLiveProvisionErrorDetail = (
  error: unknown,
  fallback: string,
  probeFailure: string,
) => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })
    ?.response?.data?.detail;
  const safeDetails = new Set([
    "A valid RTSP URL is required",
    "The RTSP camera could not be opened or did not provide a frame",
  ]);
  if (typeof detail !== "string" || !safeDetails.has(detail)) {
    return fallback;
  }

  return detail ===
    "The RTSP camera could not be opened or did not provide a frame"
    ? probeFailure
    : fallback;
};

interface Camera {
  camera_id: string;
  camera_name: string;
  location: string;
  camera_type: string;
  stream_url: string;
  status: string;
}

const Cameras = () => {
  const { t } = useTranslation();
  const { confirm, toast } = useNotification();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [uploadType, setUploadType] = useState<"LIVE" | "UPLOAD" | "USB">(
    "LIVE",
  );

  const [formData, setFormData] = useState({
    camera_name: "",
    location: "",
    stream_url: "",
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [startingId, setStartingId] = useState<string | null>(null);

  // Drag and drop state for video file upload area
  const [isDragActive, setIsDragActive] = useState(false);
  const [liveRtspProvisionError, setLiveRtspProvisionError] = useState<
    string | null
  >(null);
  const liveRtspUrlInvalid =
    uploadType === "LIVE" &&
    formData.stream_url.trim().length > 0 &&
    !isValidLiveRtspUrl(formData.stream_url);

  const fetchCameras = async () => {
    try {
      const res = await cameraService.getAll();
      setCameras(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    const load = async () => {
      try {
        const res = await cameraService.getAll();
        setCameras(res.data);
      } catch (err) {
        console.error(err);
      }
    };

    load();
  }, []);

  const resetForm = () => {
    setFormData({
      camera_name: "",
      location: "",
      stream_url: "",
    });
    setSelectedFile(null);
    setUploadType("LIVE");
    setIsDragActive(false);
    setLiveRtspProvisionError(null);
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    if (uploadType === "UPLOAD" && !selectedFile) {
      toast.error(
        t("common.operationFailed"),
        t("cameras.uploadFileRequired") || "Please select a video file.",
      );
      setLoading(false);
      return;
    }

    const data = new FormData();
    data.append("camera_name", formData.camera_name);
    data.append("location", formData.location);
    data.append("camera_type", uploadType);

    if (uploadType === "LIVE") {
      data.append("stream_url", formData.stream_url);
    } else if (uploadType === "UPLOAD") {
      data.append("video_file", selectedFile as File);
      data.append("stream_url", "FILE_UPLOADED");
    } else if (uploadType === "USB") {
      data.append("stream_url", "0");
    }

    let created = false;
    let toastId: string | null = null;
    try {
      toastId = toast.loading(
        t("common.processing"),
        t("common.pleaseWait"),
      );
      const res = await cameraService.create(data);
      created = true;
      await cameraService.start(res.data.camera_id);
      setShowModal(false);
      resetForm();
      if (toastId) {
        toast.update(toastId, {
          type: "success",
          title: t("common.success"),
          description: t("cameras.provisionSuccess"),
        });
      }
    } catch (error) {
      if (uploadType === "LIVE") {
        setLiveRtspProvisionError(
          getLiveProvisionErrorDetail(
            error,
            t("cameras.liveProvisionFailed"),
            t("cameras.liveProvisionProbeFailed"),
          ),
        );
      }
      if (toastId) {
        if (!created) {
          toast.update(toastId, {
            type: "error",
            title: t("common.operationFailed"),
            description: t("cameras.provisionFailed"),
          });
        } else {
          toast.update(toastId, {
            type: "error",
            title: t("common.operationFailed"),
            description:
              t("cameras.provisionPartial") ||
              "Camera created, but AI initialization failed.",
          });
        }
      }
    } finally {
      if (created) {
        fetchCameras();
      }
      setLoading(false);
    }
  };

  // Drag & Drop handlers for Video Archive
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true);
    } else if (e.type === "dragleave") {
      setIsDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="min-height-screen bg-ag-dark p-6 md:p-8 flex flex-col items-center">
      {/* Container to restrict width and align with desktop precision */}
      <div className="w-full max-w-7xl">
        {/* Surveillance Header Panel */}
        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 mb-8 bg-ag-card border border-white/10 p-6 rounded-xl shadow-xl">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-bold text-white tracking-tight font-sans">
                {t("cameras.title")}
              </h2>
              {/* Count Pill matching screenshot */}
              <span className="flex items-center gap-1 px-2.5 py-1 bg-white/5 border border-white/10 text-ag-success text-[10px] font-semibold font-mono rounded uppercase tracking-wider">
                <span className="w-1.5 h-1.5 rounded-full bg-ag-success animate-pulse"></span>
                {cameras.length}{" "}
                {t(
                  cameras.length === 1
                    ? "cameras.cameraSingular"
                    : "cameras.cameraPlural",
                )}
              </span>
            </div>
            <p className="text-gray-400 text-xs mt-1.5 font-sans font-medium flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500/20 border border-emerald-500 animate-ping"></span>
              {t("cameras.subtitle")}
            </p>
          </div>

          <button
            id="add-camera-btn"
            onClick={() => {
              resetForm();
              setShowModal(true);
            }}
            className="self-start sm:self-center bg-ag-primary text-black px-5 py-3 rounded-lg flex items-center gap-2 text-xs font-bold uppercase tracking-wider transition-colors shadow-lg shadow-black/20 hover:bg-white/90"
          >
            <Plus size={16} strokeWidth={2.5} />
            {t("cameras.addButton")}
          </button>
        </div>

        {/* Camera Node CCTV Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {cameras.map((cam) => {
            const liveStatus = cam.status || "Offline";
            const isRtspCamera = ["LIVE", "NVR"].includes(
              cam.camera_type?.toUpperCase() ?? "",
            );
            const isLive =
              isRtspCamera
                ? ["ACTIVE", "Online", "Processing", "Running"].includes(
                    liveStatus,
                  )
                : cam.status === "ACTIVE";
            const statusLabel =
              isRtspCamera
                ? (() => {
                    switch (liveStatus.toUpperCase()) {
                      case "ACTIVE":
                        return t("common.active");
                      case "ONLINE":
                        return t("common.online");
                      case "PROCESSING":
                        return t("dashboard.status.processing");
                      case "RUNNING":
                        return t("dashboard.status.running");
                      case "OFFLINE":
                        return t("common.offline");
                      case "DISCONNECTED":
                        return t("cameras.status.disconnected");
                      case "PENDING":
                        return t("cameras.status.pending");
                      default:
                        return liveStatus.toUpperCase();
                    }
                  })()
                : cam.status === "ACTIVE"
                  ? t("common.active")
                  : t("cameras.status.pending");
            return (
              <div
                key={cam.camera_id}
                id={`camera-card-${cam.camera_id}`}
                className="bg-ag-card border border-white/10 rounded-xl overflow-hidden shadow-lg hover:border-ag-success/40 transition-all flex flex-col group"
              >
                {/* CCTV Monitor Viewport */}
                <div className="relative aspect-video w-full bg-ag-dark overflow-hidden flex items-center justify-center border-b border-white/10">
                  {/* Grid/Scanline overlay for realistic monitoring screen */}
                  <div className="absolute inset-0 bg-[linear-gradient(rgba(18,24,38,0)_96%,rgba(18,24,38,0.35)_96%),linear-gradient(90deg,rgba(18,24,38,0)_96%,rgba(18,24,38,0.35)_96%)] bg-[size:16px_16px] pointer-events-none opacity-40"></div>
                  <div className="absolute inset-0 bg-[linear-gradient(rgba(0,202,149,0.02)_50%,rgba(0,0,0,0.15)_50%)] bg-[size:100%_4px] pointer-events-none"></div>

                  {/* Dynamic central visual element */}
                  <div className="flex flex-col items-center justify-center text-gray-500 group-hover:text-ag-success/50 transition-colors">
                    {isRtspCamera ? (
                      <Radio size={40} className="stroke-[1.5] animate-pulse" />
                    ) : (
                      <Video size={40} className="stroke-[1.5]" />
                    )}
                  </div>

                  {/* Top-Left Channel Status Pill */}
                  <div className="absolute top-3 left-3 flex items-center gap-1.5 px-2 py-1 bg-black/60 backdrop-blur-sm rounded text-[9px] font-mono font-semibold uppercase tracking-widest border border-white/5">
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${isLive ? "bg-ag-success animate-ping" : "bg-ag-warning animate-pulse"}`}
                    ></span>
                    <span
                      className={isLive ? "text-ag-success" : "text-amber-300"}
                    >
                      {isLive
                        ? t("cameras.status.liveFeed")
                        : t("cameras.status.disconnected")}
                    </span>
                  </div>

                  {/* Bottom-Right Monospace Channel Identifier */}
                  <div className="absolute bottom-3 right-3 bg-black/80 border border-white/10 px-2 py-0.5 rounded text-[10px] text-gray-400 font-mono font-semibold tracking-tight">
                    {cam.camera_id}
                  </div>
                </div>

                {/* Card Content info panel */}
                <div className="p-5 flex flex-col flex-grow">
                  <div className="flex justify-between items-start gap-2 mb-3">
                    <h3 className="text-base font-bold text-white tracking-tight">
                      {cam.camera_name}
                    </h3>

                    {/* Status badge */}
                    <span
                      className={`px-2 py-0.5 text-[9px] font-mono font-bold uppercase rounded border ${
                        isLive
                          ? "bg-ag-success/10 text-ag-success border-ag-success/20"
                          : "bg-ag-warning/10 text-amber-300 border-amber-400/20"
                      }`}
                    >
                      {statusLabel}
                    </span>
                  </div>

                  <p className="text-gray-400 text-xs font-medium flex items-center gap-1.5 mb-6">
                    <MapPin size={13} className="text-gray-500" />
                    <span className="font-mono tracking-tight text-[11px] text-gray-400">
                      📍 {cam.location}
                    </span>
                  </p>

                  {/* Control actions */}
                  <div className="space-y-2 mt-auto">
                    <button
                      onClick={async () => {
                        setStartingId(cam.camera_id);
                        let toastId: string | null = null;
                        try {
                          toastId = toast.loading(
                            t("common.processing"),
                            t("common.pleaseWait"),
                          );
                          await cameraService.start(cam.camera_id);
                          if (toastId) {
                            toast.update(toastId, {
                              type: "success",
                              title: t("common.success"),
                              description: t("cameras.aiActive"),
                            });
                          }
                        } catch (err) {
                          console.error(err);
                          if (toastId) {
                            toast.update(toastId, {
                              type: "error",
                              title: t("common.operationFailed"),
                              description: t("cameras.aiInitFailed"),
                            });
                          }
                        } finally {
                          setStartingId(null);
                        }
                      }}
                      disabled={startingId === cam.camera_id}
                      className="w-full bg-ag-success hover:bg-green-600 border border-transparent text-white py-3 rounded-lg flex items-center justify-center gap-2 text-xs font-bold transition-all uppercase tracking-wider disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {startingId === cam.camera_id ? (
                        <span className="flex items-center gap-2">
                          <Loader2 size={12} className="animate-spin" />
                          {t("cameras.starting")}
                        </span>
                      ) : (
                        <>
                          <Play size={13} fill="currentColor" stroke="none" />{" "}
                          {t("cameras.initializeAi")}
                        </>
                      )}
                    </button>

                    <button
                      onClick={() => {
                        confirm({
                          title:
                            t("cameras.deleteCamera"),
                          description:
                            t("cameras.confirmDeleteCamera"),
                          type: "danger",
                          confirmLabel: t("common.delete"),
                          cancelLabel: t("common.cancel"),
                          onConfirm: async () => {
                            setDeletingId(cam.camera_id);
                            let toastId: string | null = null;
                            try {
                              toastId = toast.loading(
                                t("common.processing"),
                                t("common.pleaseWait"),
                              );
                              await cameraService.delete(cam.camera_id);
                              setCameras((current) =>
                                current.filter(
                                  (camera) =>
                                    camera.camera_id !== cam.camera_id,
                                ),
                              );
                              if (toastId) {
                                toast.update(toastId, {
                                  type: "success",
                                  title: t("common.success"),
                                  description: t("cameras.deleteSuccess"),
                                });
                              }
                            } catch (err) {
                              console.error(err);
                              if (toastId) {
                                toast.update(toastId, {
                                  type: "error",
                                  title: t("common.operationFailed"),
                                  description: t("cameras.deleteFailed"),
                                });
                              }
                            } finally {
                              setDeletingId(null);
                            }
                          },
                        });
                      }}
                      disabled={deletingId === cam.camera_id}
                      className="w-full text-gray-400 hover:text-ag-danger text-[11px] font-bold uppercase tracking-wider transition-colors py-2 block text-center disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {deletingId === cam.camera_id ? (
                        <span className="flex items-center justify-center gap-1">
                          <Loader2 size={12} className="animate-spin" />
                          {t("cameras.deletingNode")}
                        </span>
                      ) : (
                        <span>{t("cameras.deleteCamera")}</span>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Modern surveillance Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/85 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
          <form
            onSubmit={handleAdd}
            className="bg-ag-card w-full max-w-lg rounded-xl border border-white/10 shadow-2xl relative overflow-hidden animate-in zoom-in-95 duration-150 flex flex-col"
          >
            {/* Modal Header Panel */}
            <div className="p-6 border-b border-white/10 flex justify-between items-start gap-4">
              <div className="flex gap-3 items-center">
                <div className="p-2.5 bg-ag-success/10 text-ag-success rounded-lg">
                  <CameraIcon size={20} strokeWidth={2.5} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white tracking-tight">
                    {t("cameras.modalTitle")}
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5 font-medium leading-normal">
                    {t("cameras.modalDescription")}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowModal(false);
                  resetForm();
                }}
                className="text-gray-400 hover:text-white p-1 rounded hover:bg-white/5 transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            {/* Content body */}
            <div className="p-6 overflow-y-auto max-h-[75vh] space-y-6">
              {/* Type Selector Tabs */}
              <div className="flex bg-ag-dark p-1 rounded-lg border border-white/10">
                <button
                  type="button"
                  onClick={() => setUploadType("LIVE")}
                  className={`flex-1 py-2 rounded font-semibold text-xs transition-all flex items-center justify-center gap-1.5 uppercase tracking-wider ${
                    uploadType === "LIVE"
                      ? "bg-ag-success text-black"
                      : "text-gray-400 hover:text-white"
                  }`}
                >
                  <Sliders size={13} />
                  {t("cameras.types.live")}
                </button>

                <button
                  type="button"
                  onClick={() => setUploadType("UPLOAD")}
                  className={`flex-1 py-2 rounded font-semibold text-xs transition-all flex items-center justify-center gap-1.5 uppercase tracking-wider ${
                    uploadType === "UPLOAD"
                      ? "bg-ag-success text-black"
                      : "text-gray-400 hover:text-white"
                  }`}
                >
                  <FolderOpen size={13} />
                  {t("cameras.types.upload")}
                </button>

                <button
                  type="button"
                  onClick={() => setUploadType("USB")}
                  className={`flex-1 py-2 rounded font-semibold text-xs transition-all flex items-center justify-center gap-1.5 uppercase tracking-wider ${
                    uploadType === "USB"
                      ? "bg-ag-success text-black"
                      : "text-gray-400 hover:text-white"
                  }`}
                >
                  <Laptop size={13} />
                  {t("cameras.types.usb")}
                </button>
              </div>

              {/* Form Input fields */}
              <div className="space-y-4">
                {/* Node Alias Input */}
                <div>
                  <label className="text-[10px] font-mono font-bold text-ag-success uppercase tracking-wider block mb-1.5">
                    {t("cameras.cameraAliasPlaceholder")}
                  </label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none text-gray-500">
                      <Sliders size={15} />
                    </span>
                    <input
                      value={formData.camera_name}
                      className="w-full bg-ag-dark border border-white/10 py-2.5 pl-10 pr-10 rounded-lg text-white text-xs outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-all font-sans font-semibold placeholder:text-gray-500"
                      placeholder={t("cameras.cameraAliasPlaceholder")}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          camera_name: e.target.value,
                        })
                      }
                      required
                    />
                    <span className="absolute inset-y-0 right-0 flex items-center pr-3.5 pointer-events-none text-gray-500">
                      <Compass size={15} />
                    </span>
                  </div>
                </div>

                {/* Physical Location Input */}
                <div>
                  <label className="text-[10px] font-mono font-bold text-ag-success uppercase tracking-wider block mb-1.5">
                    {t("cameras.locationPlaceholder")}
                  </label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none text-gray-500">
                      <MapPin size={15} />
                    </span>
                    <input
                      value={formData.location}
                      className="w-full bg-ag-dark border border-white/10 py-2.5 pl-10 pr-10 rounded-lg text-white text-xs outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-all font-sans font-semibold placeholder:text-gray-500"
                      placeholder={t("cameras.locationPlaceholder")}
                      onChange={(e) =>
                        setFormData({ ...formData, location: e.target.value })
                      }
                      required
                    />
                    <span className="absolute inset-y-0 right-0 flex items-center pr-3.5 pointer-events-none text-gray-500">
                      <Map size={15} />
                    </span>
                  </div>
                </div>

                {/* Contextual form inputs based on selected tab */}
                {uploadType === "LIVE" ? (
                  <div>
                    <label className="text-[10px] font-mono font-bold text-ag-success uppercase tracking-wider block mb-1.5">
                      RTSP URL
                    </label>
                    <div className="relative">
                      <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none text-gray-500">
                        <Link size={15} />
                      </span>
                      <input
                        value={formData.stream_url}
                        className="w-full bg-ag-dark border border-white/10 py-2.5 pl-10 pr-10 rounded-lg text-white font-mono text-xs outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-all placeholder:text-gray-500"
                        placeholder={t("cameras.streamPlaceholder")}
                        onChange={(e) =>
                          (() => {
                            const value = e.target.value;
                            setFormData({ ...formData, stream_url: value });
                            if (isValidLiveRtspUrl(value)) {
                              setLiveRtspProvisionError(null);
                            }
                          })()
                        }
                        required
                      />
                      <span className="absolute inset-y-0 right-0 flex items-center pr-3.5 pointer-events-none text-gray-500">
                        <Eye size={15} />
                      </span>
                    </div>

                    {liveRtspUrlInvalid && (
                      <p className="text-amber-300 text-[11px] leading-relaxed mt-2">
                        {t("cameras.invalidStreamFormat")}
                      </p>
                    )}

                    {!liveRtspUrlInvalid && liveRtspProvisionError && (
                      <p className="text-amber-300 text-[11px] leading-relaxed mt-2">
                        {liveRtspProvisionError}
                      </p>
                    )}

                    {/* Industrial feedback box */}
                    <div className="flex items-start gap-3 bg-white/5 border border-white/10 rounded-lg p-3.5 text-xs text-sky-300 mt-4">
                      <span className="text-lg mt-0.5 leading-none">ⓘ</span>
                      <span className="font-sans font-medium text-[11px] leading-relaxed">
                        {t("cameras.rtspAccessibilityHint")}
                      </span>
                    </div>
                  </div>
                ) : uploadType === "UPLOAD" ? (
                  <div>
                    <label className="text-[10px] font-mono font-bold text-ag-success uppercase tracking-wider block mb-1.5">
                      {t("cameras.videoFile")}
                    </label>
                    <div className="relative group">
                      <input
                        type="file"
                        accept="video/*"
                        onChange={(e) =>
                          setSelectedFile(e.target.files?.[0] || null)
                        }
                        className="hidden"
                        id="video-upload"
                      />
                      <label
                        htmlFor="video-upload"
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                        className={`w-full bg-ag-dark border-2 border-dashed rounded-lg p-6 flex flex-col items-center justify-center cursor-pointer transition-all ${
                          isDragActive
                            ? "border-ag-success bg-ag-success/10"
                            : "border-white/10 hover:border-ag-success/50"
                        }`}
                      >
                        <Upload
                          className={`text-gray-500 group-hover:text-ag-success mb-2.5 transition-colors ${isDragActive ? "text-ag-success" : ""}`}
                          size={28}
                        />
                        <span className="text-gray-300 font-sans font-bold text-xs text-center mb-1">
                          {t("cameras.uploadDropPrompt")}
                        </span>
                        <span className="text-gray-500 text-[10px] font-medium text-center">
                          {t("cameras.uploadBrowsePrompt")}
                        </span>
                        <span className="text-gray-600 text-[9px] font-mono text-center mt-3">
                          {t("cameras.uploadFormats")}
                        </span>
                      </label>
                    </div>

                    {/* Uploaded File Preview Card matching the screenshot */}
                    {selectedFile && (
                      <div className="mt-4 bg-white/5 border border-white/10 rounded-lg p-3 flex items-center justify-between">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="p-2 bg-white/5 text-ag-success rounded">
                            <Video size={16} />
                          </div>
                          <div className="min-w-0">
                            <p className="text-xs font-semibold text-white truncate pr-2">
                              {selectedFile.name}
                            </p>
                            <p className="text-[10px] text-gray-500 font-mono mt-0.5">
                              {(selectedFile.size / (1024 * 1024)).toFixed(1)}{" "}
                              MB •{" "}
                              {selectedFile.name
                                .split(".")
                                .pop()
                                ?.toUpperCase() || "MP4"}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <span className="p-0.5 bg-emerald-500/20 text-emerald-400 rounded-full">
                            <CheckCircle2 size={14} />
                          </span>
                          <button
                            type="button"
                            onClick={() => setSelectedFile(null)}
                            className="text-gray-500 hover:text-white p-1 rounded"
                          >
                            <X size={14} />
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div>
                    <label className="text-[10px] font-mono font-bold text-ag-success uppercase tracking-wider block mb-1.5">
                      {t("cameras.laptopCameraInfoTitle")}
                    </label>
                    <div className="bg-ag-dark border border-white/10 rounded-lg p-5 flex items-start gap-4">
                      {/* Interactive miniature camera preview frame */}
                      <div className="w-14 h-14 bg-black/80 border border-white/10 rounded flex items-center justify-center relative flex-shrink-0">
                        <Laptop
                          className="text-ag-success stroke-[1.5]"
                          size={22}
                        />
                        <span className="absolute bottom-1 right-1 w-2 h-2 rounded-full bg-ag-success animate-ping"></span>
                        <span className="absolute bottom-1 right-1 w-2 h-2 rounded-full bg-ag-success"></span>
                      </div>

                      <div>
                        <p className="text-white font-sans font-bold text-xs flex items-center gap-1.5">
                          {t("cameras.cameraUsedMessage")}
                        </p>
                        <div className="mt-1.5 space-y-1">
                          <p className="text-ag-success text-[11px] font-mono flex items-center gap-1.5">
                            <span className="w-1 h-1 rounded-full bg-ag-success"></span>
                            {t("cameras.defaultCamera")}
                          </p>
                          <p className="text-ag-success text-[11px] font-mono flex items-center gap-1.5">
                            <span className="w-1 h-1 rounded-full bg-ag-success"></span>
                            {t("cameras.cameraReady")}
                          </p>
                        </div>
                        <p className="text-gray-400 text-[10px] font-mono mt-2 leading-relaxed">
                          {t("cameras.cameraAutoConnect")}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Modal Actions Footer */}
            <div className="p-6 border-t border-white/10 bg-ag-dark/90">
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-ag-success hover:bg-green-600 text-white py-3.5 rounded-lg font-bold transition-all flex items-center justify-center gap-2 uppercase text-xs tracking-wider shadow-lg shadow-black/20 disabled:opacity-50"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <Loader2 size={16} className="animate-spin" />
                    {t("cameras.provisioning")}
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Shield size={14} />
                    {t("cameras.provisionButton")}
                  </span>
                )}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

export default Cameras;
