import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { cameraService } from "../services/api";
import {
  Plus,
  Play,
  Upload,
  Radio,
  X,
  Loader2,
  Video,
  Trash,
} from "lucide-react";

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

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const data = new FormData();
    data.append("camera_name", formData.camera_name);
    data.append("location", formData.location);
    data.append("camera_type", uploadType);

    if (uploadType === "LIVE") {
      data.append("stream_url", formData.stream_url);
    } else if (uploadType === "UPLOAD" && selectedFile) {
      data.append("video_file", selectedFile);
      data.append("stream_url", "FILE_UPLOADED");
    } else if (uploadType === "USB") {
      data.append("stream_url", "0");
    }

    try {
      const res = await cameraService.create(data);
      await cameraService.start(res.data.camera_id);
      setShowModal(false);
      fetchCameras();
      alert(t("cameras.provisionSuccess"));
    } catch {
      alert(t("cameras.provisionFailed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-center mb-10 bg-ag-card/30 p-8 rounded-[2rem] border border-white/5 backdrop-blur-md">
        <div>
          <h2 className="text-3xl font-black text-white tracking-tighter">
            {t("cameras.title")}
          </h2>
          <p className="text-gray-500 text-sm mt-1">{t("cameras.subtitle")}</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="bg-ag-success text-white px-8 py-4 rounded-2xl flex items-center gap-3 font-black shadow-xl shadow-green-900/20 hover:scale-105 transition-all"
        >
          <Plus size={22} /> {t("cameras.addButton")}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {cameras.map((cam) => (
          <div
            key={cam.camera_id}
            className="bg-ag-card rounded-3xl border border-white/5 p-6 hover:border-white/10 transition-all group relative overflow-hidden"
          >
            <div className="flex justify-between items-start mb-6">
              <div
                className={`p-4 rounded-2xl ${cam.camera_type === "LIVE" ? "bg-red-500/10 text-red-500" : "bg-blue-500/10 text-blue-400"}`}
              >
                {cam.camera_type === "LIVE" ? (
                  <Radio size={24} />
                ) : (
                  <Video size={24} />
                )}
              </div>
              <span className="text-[10px] bg-black/40 px-3 py-1.5 rounded-full text-gray-500 font-mono tracking-widest">
                {cam.camera_type}
              </span>
            </div>

            <h3 className="text-xl font-bold text-white mb-1">
              {cam.camera_name}
            </h3>
            <p className="text-gray-500 text-sm mb-6 flex items-center gap-2">
              📍 {cam.location}
            </p>

            <div className="space-y-3">
              <button
                onClick={() =>
                  cameraService
                    .start(cam.camera_id)
                    .then(() => alert("AI Active"))
                }
                className="w-full bg-white/5 hover:bg-ag-success hover:text-white text-gray-300 py-4 rounded-2xl flex items-center justify-center gap-3 font-bold transition-all"
              >
                <Play size={18} /> Initialize AI Node
              </button>

              <button
                onClick={async () => {
                  const confirmed = window.confirm(
                    t("cameras.confirmDeleteCamera") ||
                      "Delete this camera and all related data?",
                  );
                  if (!confirmed) return;

                  setDeletingId(cam.camera_id);
                  try {
                    await cameraService.delete(cam.camera_id);
                    setCameras((current) =>
                      current.filter(
                        (camera) => camera.camera_id !== cam.camera_id,
                      ),
                    );
                    alert(t("cameras.deleteSuccess"));
                  } catch (err) {
                    console.error(err);
                    alert(t("cameras.deleteFailed"));
                  } finally {
                    setDeletingId(null);
                  }
                }}
                disabled={deletingId === cam.camera_id}
                className="w-full bg-red-600/10 border border-red-500/10 hover:bg-red-600 hover:text-white text-red-300 py-4 rounded-2xl flex items-center justify-center gap-3 font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {deletingId === cam.camera_id ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Trash size={18} />
                )}
                {t("cameras.deleteCamera")}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Modern Add Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-ag-dark/95 backdrop-blur-xl flex items-center justify-center z-50 p-4 animate-in zoom-in duration-300">
          <form
            onSubmit={handleAdd}
            className="bg-ag-card w-full max-w-xl p-12 rounded-[3.5rem] border border-white/10 shadow-2xl relative"
          >
            <div className="flex justify-between items-center mb-10">
              <h3 className="text-3xl font-black text-white tracking-tighter">
                {t("cameras.modalTitle")}
              </h3>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="text-gray-500 hover:text-white p-2"
              >
                <X size={28} />
              </button>
            </div>

            {/* Type Selector Tabs */}
            <div className="flex bg-ag-dark p-1.5 rounded-2xl mb-8 border border-white/5">
              <button
                type="button"
                onClick={() => setUploadType("LIVE")}
                className={`flex-1 py-3 rounded-xl font-bold text-sm transition-all ${
                  uploadType === "LIVE"
                    ? "bg-ag-danger text-white"
                    : "text-gray-500"
                }`}
              >
                {t("cameras.types.live")}
              </button>

              <button
                type="button"
                onClick={() => setUploadType("UPLOAD")}
                className={`flex-1 py-3 rounded-xl font-bold text-sm transition-all ${
                  uploadType === "UPLOAD"
                    ? "bg-blue-600 text-white"
                    : "text-gray-500"
                }`}
              >
                {t("cameras.types.upload")}
              </button>

              <button
                type="button"
                onClick={() => setUploadType("USB")}
                className={`flex-1 py-3 rounded-xl font-bold text-sm transition-all ${
                  uploadType === "USB"
                    ? "bg-green-600 text-white"
                    : "text-gray-500"
                }`}
              >
                Laptop Camera
              </button>
            </div>

            <div className="space-y-5">
              <input
                className="w-full bg-ag-dark border border-white/10 p-5 rounded-2xl text-white outline-none focus:border-ag-success font-bold"
                placeholder={t("cameras.cameraAliasPlaceholder")}
                onChange={(e) =>
                  setFormData({ ...formData, camera_name: e.target.value })
                }
                required
              />
              <input
                className="w-full bg-ag-dark border border-white/10 p-5 rounded-2xl text-white outline-none focus:border-ag-success font-bold"
                placeholder={t("cameras.locationPlaceholder")}
                onChange={(e) =>
                  setFormData({ ...formData, location: e.target.value })
                }
                required
              />

              {uploadType === "LIVE" ? (
                <input
                  className="w-full bg-ag-dark border border-white/10 p-5 rounded-2xl text-white font-mono text-sm outline-none focus:border-ag-danger"
                  placeholder={t("cameras.streamPlaceholder")}
                  onChange={(e) =>
                    setFormData({ ...formData, stream_url: e.target.value })
                  }
                  required
                />
              ) : uploadType === "UPLOAD" ? (
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
                    className="w-full bg-ag-dark border-2 border-dashed border-white/10 p-8 rounded-2xl flex flex-col items-center justify-center cursor-pointer group-hover:border-blue-500 transition-all"
                  >
                    <Upload
                      className="text-gray-500 group-hover:text-blue-400 mb-2"
                      size={32}
                    />
                    <span className="text-gray-500 font-bold">
                      {selectedFile
                        ? selectedFile.name
                        : t("cameras.uploadLabel")}
                    </span>
                  </label>
                </div>
              ) : (
                <div className="bg-green-500/10 border border-green-500/20 rounded-2xl p-6 text-center">
                  <Radio className="mx-auto mb-3 text-green-500" size={32} />
                  <p className="text-green-400 font-bold">
                    {t("cameras.cameraUsedMessage")}
                  </p>
                  <p className="text-gray-500 text-sm mt-2">
                    {t("cameras.cameraUsedDetail")}
                  </p>
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-ag-success text-white py-5 rounded-3xl font-black shadow-xl mt-10 flex items-center justify-center gap-3"
            >
              {loading ? (
                <Loader2 className="animate-spin" />
              ) : (
                t("cameras.provisionButton")
              )}
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default Cameras;
