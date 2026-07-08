import { useState, useEffect } from "react";
import {
  
  Bell,
  Save,
  RotateCcw,
  
  Globe,
  Loader2,
  Zap,
  Clock,
  Activity,
} from "lucide-react";
import { settingsService } from "../services/api";
import type { ISystemSettings } from "../services/api";
const DEFAULT_SETTINGS: ISystemSettings = {
  organization_name: "AeroGuard AI",
  airport_name: "Main International Airport",
  language: "en",
  timezone: "UTC",
  system_name: "AeroGuard AI v1.0",
  detection_confidence: 0.5,
  tracking_enabled: true,
  object_detection_enabled: true,
  face_detection_enabled: true,
  face_recognition_enabled: true,
  max_objects: 50,
  enable_alert_sounds: true,
  alert_duration: 5,
  min_alert_confidence: 0.6,
  show_alert_labels: true,
  default_fps: 30,
  recording_quality: "High",
  frame_buffer: 5,
  auto_reconnect: true,
  video_resolution: "1080p",
  compression_enabled: true,
  jpeg_quality: 70,
  jwt_expiration: 60,
  session_timeout: 30,
};

const Settings = () => {
  const [config, setConfig] = useState<ISystemSettings>(DEFAULT_SETTINGS);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const res = await settingsService.get();
        if (res.data) setConfig(res.data);
      } catch {
        // تم حذف (err) لحل خطأ no-unused-vars
        console.error("Failed to load settings from server");
      } finally {
        setIsLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await settingsService.update(config);
      alert("✅ System configuration deployed successfully!");
    } catch {
      // تم حذف (error) لحل خطأ no-unused-vars
      alert("❌ Critical Error: Could not sync settings with the AI Engine.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleLoadDefaults = () => {
    if (
      window.confirm("Restore factory defaults? Current changes will be lost.")
    ) {
      setConfig(DEFAULT_SETTINGS);
    }
  };

  if (isLoading)
    return (
      <div className="h-screen w-full flex items-center justify-center bg-ag-dark">
        <Loader2 className="animate-spin text-ag-danger" size={48} />
      </div>
    );

  return (
    <div className="p-8 space-y-8 bg-ag-dark min-h-screen text-ag-primary pb-24">
      {/* Header */}
      <div className="flex justify-between items-end sticky top-0 z-50 bg-ag-dark/80 backdrop-blur-xl py-4 border-b border-white/5">
        <div>
          <h2 className="text-4xl font-black tracking-tighter uppercase">
            System Settings
          </h2>
          <p className="text-gray-500 font-medium">
            Core Intelligence & Infrastructure Parameters
          </p>
        </div>
        <div className="flex gap-4">
          <button
            onClick={handleLoadDefaults}
            className="px-6 py-3 rounded-2xl bg-white/5 hover:bg-white/10 font-bold text-xs flex items-center gap-2 border border-white/10 transition-all"
          >
            <RotateCcw size={16} /> Load Defaults
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="bg-ag-success hover:bg-green-600 text-white px-10 py-3 rounded-2xl font-black text-sm flex items-center gap-3 transition-all shadow-xl shadow-green-900/20"
          >
            {isSaving ? (
              <Loader2 className="animate-spin" />
            ) : (
              <>
                <Save size={20} /> SAVE & DEPLOY
              </>
            )}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* General Settings */}
        <section className="bg-ag-card p-8 rounded-[2.5rem] border border-white/5 shadow-2xl space-y-6">
          <div className="flex items-center gap-3 text-ag-success mb-2">
            <Globe size={24} />
            <h3 className="text-xl font-black uppercase tracking-widest">
              Environment
            </h3>
          </div>
          <div className="grid grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-[10px] font-black text-gray-500 uppercase ml-2">
                Airport Name
              </label>
              <input
                value={config.airport_name}
                onChange={(e) =>
                  setConfig({ ...config, airport_name: e.target.value })
                }
                className="w-full bg-ag-dark border border-white/10 p-4 rounded-2xl outline-none focus:border-ag-success font-bold"
              />
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-black text-gray-500 uppercase ml-2">
                Time Zone
              </label>
              <input
                value={config.timezone}
                onChange={(e) =>
                  setConfig({ ...config, timezone: e.target.value })
                }
                className="w-full bg-ag-dark border border-white/10 p-4 rounded-2xl outline-none focus:border-ag-success font-bold"
              />
            </div>
          </div>
        </section>

        {/* AI Control */}
        <section className="bg-ag-card p-8 rounded-[2.5rem] border border-white/5 shadow-2xl space-y-6">
          <div className="flex items-center gap-3 text-ag-warning mb-2">
            <Zap size={24} />
            <h3 className="text-xl font-black uppercase tracking-widest">
              AI Core
            </h3>
          </div>
          <div className="space-y-6">
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-xs font-bold text-gray-400">
                  Object Confidence Threshold
                </label>
                <span className="text-ag-warning font-mono font-bold">
                  {Math.round(config.detection_confidence * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0.1"
                max="0.9"
                step="0.05"
                value={config.detection_confidence}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    detection_confidence: parseFloat(e.target.value),
                  })
                }
                className="w-full accent-ag-warning"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex justify-between items-center p-4 bg-ag-dark/40 rounded-2xl border border-white/5">
                <span className="text-xs font-bold">Face Recognition</span>
                <button
                  onClick={() =>
                    setConfig({
                      ...config,
                      face_recognition_enabled:
                        !config.face_recognition_enabled,
                    })
                  }
                  className={`w-12 h-6 rounded-full relative transition-all ${config.face_recognition_enabled ? "bg-ag-success" : "bg-gray-700"}`}
                >
                  <div
                    className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-all ${config.face_recognition_enabled ? "right-1" : "left-1"}`}
                  ></div>
                </button>
              </div>
              <div className="flex justify-between items-center p-4 bg-ag-dark/40 rounded-2xl border border-white/5">
                <span className="text-xs font-bold">Motion Tracking</span>
                <button
                  onClick={() =>
                    setConfig({
                      ...config,
                      tracking_enabled: !config.tracking_enabled,
                    })
                  }
                  className={`w-12 h-6 rounded-full relative transition-all ${config.tracking_enabled ? "bg-ag-success" : "bg-gray-700"}`}
                >
                  <div
                    className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-all ${config.tracking_enabled ? "right-1" : "left-1"}`}
                  ></div>
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Alert Protocol */}
        <section className="bg-ag-card p-8 rounded-[2.5rem] border border-white/5 shadow-2xl space-y-6">
          <div className="flex items-center gap-3 text-ag-danger mb-2">
            <Bell size={24} />
            <h3 className="text-xl font-black uppercase tracking-widest">
              Notification Engine
            </h3>
          </div>
          <div className="flex justify-between items-center p-5 bg-ag-dark/40 rounded-2xl border border-white/5">
            <div className="flex items-center gap-3">
              <Activity className="text-ag-danger" size={20} />
              <span className="font-bold">Dashboard Audio Siren</span>
            </div>
            <button
              onClick={() =>
                setConfig({
                  ...config,
                  enable_alert_sounds: !config.enable_alert_sounds,
                })
              }
              className={`w-14 h-7 rounded-full relative transition-all ${config.enable_alert_sounds ? "bg-ag-danger" : "bg-gray-700"}`}
            >
              <div
                className={`w-5 h-5 bg-white rounded-full absolute top-1 transition-all ${config.enable_alert_sounds ? "right-1" : "left-1"}`}
              ></div>
            </button>
          </div>
        </section>

        {/* Security & Access */}
        <section className="bg-ag-card p-8 rounded-[2.5rem] border border-white/5 shadow-2xl space-y-6">
          <div className="flex items-center gap-3 text-blue-400 mb-2">
            <Clock size={24} />
            <h3 className="text-xl font-black uppercase tracking-widest">
              Security Lifecycle
            </h3>
          </div>
          <div className="space-y-2">
            <label className="text-[10px] font-black text-gray-500 uppercase ml-2">
              Session Expiration (Minutes)
            </label>
            <input
              type="number"
              value={config.jwt_expiration}
              onChange={(e) =>
                setConfig({
                  ...config,
                  jwt_expiration: parseInt(e.target.value),
                })
              }
              className="w-full bg-ag-dark border border-white/10 p-4 rounded-2xl outline-none font-bold"
            />
          </div>
        </section>
      </div>
    </div>
  );
};

export default Settings;
