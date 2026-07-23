import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNotification } from "../components/NotificationSystem/useNotification";
import {
  Bell,
  Save,
  RotateCcw,
  Globe,
  Loader2,
  Zap,
  Shield,
  Eye,
  Settings as SettingsIcon,
  HelpCircle,
  Plus,
  Minus,
  Volume2,
  Clock,
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
  loitering_enabled: false,
  loitering_seconds: 30,
  crowd_density_enabled: false,
  crowd_density_threshold: 10,
  abandoned_bag_enabled: false,
  abandoned_bag_seconds: 20,
  wrong_direction_enabled: false,
  wrong_direction_angle_threshold: 150,
  restricted_area_enabled: false,
  fire_detection_enabled: false,
  smoke_detection_enabled: false,
  max_objects: 50,
  gpu_enabled: false,
  frame_skip: 0,
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

const Toggle = ({
  enabled,
  onToggle,
}: {
  enabled: boolean;
  onToggle: () => void;
}) => (
  <button
    onClick={onToggle}
    className={`w-10 h-5 flex items-center rounded-full p-1 cursor-pointer transition-colors duration-300 ease-in-out ${
      enabled ? "bg-[#34c759]" : "bg-[#3e404a]"
    }`}
  >
    <div
      className={`bg-white w-3 h-3 rounded-full shadow-md transform transition-transform duration-300 ease-in-out ${
        enabled ? "translate-x-5" : "translate-x-0"
      }`}
    />
  </button>
);

const Settings = () => {
  const { t } = useTranslation();
  const { confirm, toast } = useNotification();
  const [config, setConfig] = useState<ISystemSettings>(DEFAULT_SETTINGS);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const res = await settingsService.get();
        if (res.data) setConfig(res.data);
      } catch {
        console.error("Failed to load settings from server");
      } finally {
        setIsLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    let toastId: string | null = null;
    try {
      toastId = toast.loading("Processing", "Please wait...");
      await settingsService.update(config);
      if (toastId) {
        toast.update(toastId, {
          type: "success",
          title: "Success",
          description: t("settings.saveSuccess"),
        });
      }
    } catch {
      if (toastId) {
        toast.update(toastId, {
          type: "error",
          title: "Operation Failed",
          description: t("settings.saveFailed"),
        });
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleLoadDefaults = () => {
    confirm({
      title: t("settings.factoryDefaultsTitle"),
      description: t("settings.factoryDefaultsConfirm"),
      type: "danger",
      confirmLabel: t("common.load"),
      cancelLabel: t("common.cancel"),
      onConfirm: () => {
        setConfig(DEFAULT_SETTINGS);
      },
    });
  };

  if (isLoading)
    return (
      <div className="h-screen w-full flex items-center justify-center bg-[#090a11]">
        <Loader2 className="animate-spin text-blue-500" size={48} />
      </div>
    );

  return (
    <div className="p-6 bg-[#090a11] min-h-screen text-white font-sans max-w-[1400px] mx-auto space-y-6">
      {/* Header */}
      <header className="flex justify-between items-center mb-8">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600/10 p-2 rounded-lg">
            <SettingsIcon className="text-blue-500" size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              {t("settings.title")}
            </h1>
            <p className="text-gray-500 text-xs font-semibold uppercase tracking-wider mt-0.5">
              {t("settings.subtitle")}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleLoadDefaults}
            className="px-4 py-2 rounded-lg bg-[#11131a] border border-[#1e212b] text-sm font-bold text-gray-300 flex items-center gap-2 hover:bg-[#1a1c26] transition-colors"
          >
            <RotateCcw size={14} /> {t("settings.loadDefaults")}
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-6 py-2 rounded-lg bg-[#0084ff] text-white text-sm font-bold flex items-center gap-2 hover:bg-blue-600 transition-all disabled:opacity-50"
          >
            {isSaving ? (
              <Loader2 className="animate-spin" size={18} />
            ) : (
              <Save size={18} />
            )}
            {t("settings.saveDeploy")}
          </button>
          <button className="p-2 text-gray-500 hover:text-white transition-colors">
            <HelpCircle size={20} />
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-6">
          {/* Environment */}
          <section className="bg-[#11131a] border border-[#1e212b] rounded-xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Globe className="text-blue-500" size={18} />
              <h3 className="text-sm font-bold uppercase tracking-wider">
                {t("settings.environment")}
              </h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div className="space-y-2">
                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                  {t("settings.airportName")}
                </label>
                <input
                  value={config.airport_name}
                  onChange={(e) =>
                    setConfig({ ...config, airport_name: e.target.value })
                  }
                  className="w-full bg-[#0d0e14] border border-[#1e212b] p-3 rounded-lg text-sm font-semibold outline-none focus:border-blue-500/50"
                  placeholder="e.g. Dubai International (DXB)"
                />
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                  {t("settings.timeZone")}
                </label>
                <select
                  value={config.timezone}
                  onChange={(e) =>
                    setConfig({ ...config, timezone: e.target.value })
                  }
                  className="w-full bg-[#0d0e14] border border-[#1e212b] p-3 rounded-lg text-sm font-semibold outline-none focus:border-blue-500/50 appearance-none"
                >
                  <option value="UTC">UTC (GMT+0)</option>
                  <option value="Africa/Cairo">Africa/Cairo (GMT+2)</option>
                  <option value="Europe/London">Europe/London (GMT+0)</option>
                  <option value="Europe/Paris">Europe/Paris (GMT+1)</option>
                  <option value="Europe/Istanbul">
                    Europe/Istanbul (GMT+3)
                  </option>
                  <option value="Asia/Riyadh">Asia/Riyadh (GMT+3)</option>
                  <option value="Asia/Dubai">Asia/Dubai (GST, GMT+4)</option>
                  <option value="Asia/Karachi">Asia/Karachi (GMT+5)</option>
                  <option value="Asia/Kolkata">Asia/Kolkata (GMT+5:30)</option>
                  <option value="Asia/Singapore">Asia/Singapore (GMT+8)</option>
                  <option value="Asia/Tokyo">Asia/Tokyo (GMT+9)</option>
                  <option value="Australia/Sydney">
                    Australia/Sydney (GMT+10)
                  </option>
                  <option value="America/New_York">
                    America/New_York (EST, GMT-5)
                  </option>
                  <option value="America/Chicago">
                    America/Chicago (CST, GMT-6)
                  </option>
                  <option value="America/Los_Angeles">
                    America/Los_Angeles (PST, GMT-8)
                  </option>
                </select>
              </div>
            </div>
            <div className="flex items-center justify-between px-4 py-3 bg-[#0d0e14] border border-[#1e212b] rounded-lg">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
                <span className="text-xs text-gray-400 font-medium">
                  {t("settings.activeDeployment")}
                </span>
              </div>
              <span className="text-[10px] font-black text-blue-500 uppercase">
                {t("settings.connected")}
              </span>
            </div>
          </section>

          {/* Notification Engine */}
          <section className="bg-[#11131a] border border-[#1e212b] rounded-xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Bell className="text-orange-500" size={18} />
              <h3 className="text-sm font-bold uppercase tracking-wider">
                {t("settings.notificationEngine")}
              </h3>
            </div>
            <div className="flex justify-between items-center px-4 py-4 bg-[#0d0e14] border border-[#1e212b] rounded-lg">
              <div className="flex items-center gap-3">
                <Volume2 className="text-orange-500" size={18} />
                <div>
                  <div className="text-sm font-bold">
                    {t("settings.dashboardAudioSiren")}
                  </div>
                  <div className="text-[10px] text-gray-500 font-medium">
                    {t("settings.notificationEngineDescription")}
                  </div>
                </div>
              </div>
              <Toggle
                enabled={config.enable_alert_sounds}
                onToggle={() =>
                  setConfig({
                    ...config,
                    enable_alert_sounds: !config.enable_alert_sounds,
                  })
                }
              />
            </div>
          </section>

          {/* Security Lifecycle */}
          <section className="bg-[#11131a] border border-[#1e212b] rounded-xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Shield className="text-blue-500" size={18} />
              <h3 className="text-sm font-bold uppercase tracking-wider">
                {t("settings.securityLifecycle")}
              </h3>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center px-4 py-4 bg-[#0d0e14] border border-[#1e212b] rounded-lg">
                <div className="flex items-center gap-3">
                  <RotateCcw className="text-blue-500" size={18} />
                  <div>
                    <div className="text-sm font-bold">
                      {t("settings.securityLifecyclePersistent")}
                    </div>
                    <div className="text-[10px] text-gray-500 font-medium">
                      {t("settings.securityLifecyclePersistentDescription")}
                    </div>
                  </div>
                </div>
                <Toggle
                  enabled={config.auto_reconnect}
                  onToggle={() =>
                    setConfig({
                      ...config,
                      auto_reconnect: !config.auto_reconnect,
                    })
                  }
                />
              </div>
              <div className="flex justify-between items-center px-4 py-4 bg-[#0d0e14] border border-[#1e212b] rounded-lg">
                <div className="flex items-center gap-3">
                  <Clock className="text-orange-500" size={18} />
                  <div>
                    <div className="text-sm font-bold">
                      {t("settings.securityLifecycleAutoShutdown")}
                    </div>
                    <div className="text-[10px] text-gray-500 font-medium">
                      {t("settings.securityLifecycleAutoShutdownDescription")}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={config.jwt_expiration}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        jwt_expiration: parseInt(e.target.value) || 0,
                      })
                    }
                    className="w-12 bg-transparent text-right text-sm font-bold outline-none text-blue-500"
                  />
                  <span className="text-[10px] font-black bg-[#1a1c26] px-2 py-1 rounded text-gray-400">
                    {t("settings.hours")}
                  </span>
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* AI Core Intelligence */}
          <section className="bg-[#11131a] border border-[#1e212b] rounded-xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Zap className="text-orange-500" size={18} />
              <h3 className="text-sm font-bold uppercase tracking-wider">
                {t("settings.aiCore")}
              </h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex justify-between items-center p-4 bg-[#0d0e14] border border-[#1e212b] rounded-lg">
                <div className="flex items-center gap-2">
                  <Eye className="text-blue-400" size={16} />
                  <span className="text-xs font-bold">
                    {t("settings.faceRecognition")}
                  </span>
                </div>
                <Toggle
                  enabled={config.face_recognition_enabled}
                  onToggle={() =>
                    setConfig({
                      ...config,
                      face_recognition_enabled:
                        !config.face_recognition_enabled,
                    })
                  }
                />
              </div>
              <div className="flex justify-between items-center p-4 bg-[#0d0e14] border border-[#1e212b] rounded-lg">
                <div className="flex items-center gap-2">
                  <Zap className="text-blue-400" size={16} />
                  <span className="text-xs font-bold">
                    {t("settings.motionTracking")}
                  </span>
                </div>
                <Toggle
                  enabled={config.tracking_enabled}
                  onToggle={() =>
                    setConfig({
                      ...config,
                      tracking_enabled: !config.tracking_enabled,
                    })
                  }
                />
              </div>
            </div>
          </section>

          {/* AI Vision Modules */}
          <section className="bg-[#11131a] border border-[#1e212b] rounded-xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Eye className="text-orange-500" size={18} />
              <h3 className="text-sm font-bold uppercase tracking-wider">
                {t("settings.aiVisionModules")}
              </h3>
            </div>
            <div className="space-y-1">
              {[
                {
                  label: t("settings.modules.gpuAcceleration"),
                  sub: t("settings.modules.gpuAccelerationDescription"),
                  key: "gpu_enabled",
                },
                {
                  label: t("settings.modules.frameSkip"),
                  sub: t("settings.modules.frameSkipDescription"),
                  key: "frame_skip",
                  control: true,
                },
                {
                  label: t("settings.modules.loiteringDetection"),
                  sub: t("settings.modules.loiteringDetectionDescription"),
                  key: "loitering_enabled",
                },
                {
                  label: t("settings.modules.crowdDensity"),
                  sub: t("settings.modules.crowdDensityDescription"),
                  key: "crowd_density_enabled",
                },
                {
                  label: t("settings.modules.abandonedBag"),
                  sub: t("settings.modules.abandonedBagDescription"),
                  key: "abandoned_bag_enabled",
                },
                {
                  label: t("settings.modules.wrongDirection"),
                  sub: t("settings.modules.wrongDirectionDescription"),
                  key: "wrong_direction_enabled",
                },
                {
                  label: t("settings.modules.restrictedArea"),
                  sub: t("settings.modules.restrictedAreaDescription"),
                  key: "restricted_area_enabled",
                },
                {
                  label: t("settings.modules.fireDetection"),
                  sub: t("settings.modules.fireDetectionDescription"),
                  key: "fire_detection_enabled",
                },
                {
                  label: t("settings.modules.smokeDetection"),
                  sub: t("settings.modules.smokeDetectionDescription"),
                  key: "smoke_detection_enabled",
                },
              ].map((module) => (
                <div
                  key={module.key}
                  className="flex justify-between items-center py-3 border-b border-[#1e212b]/50 last:border-0 group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-500/20 group-hover:bg-blue-500 transition-colors"></div>
                    <div>
                      <div className="text-xs font-bold">{module.label}</div>
                      <div className="text-[10px] text-gray-500 font-medium">
                        {module.sub}
                      </div>
                    </div>
                  </div>
                  {module.control ? (
                    <div className="flex items-center bg-[#0d0e14] border border-[#1e212b] rounded-lg overflow-hidden">
                      <button
                        onClick={() =>
                          setConfig({
                            ...config,
                            frame_skip: Math.max(
                              0,
                              (config.frame_skip ?? 0) - 1,
                            ),
                          })
                        }
                        className="p-1.5 hover:bg-[#1a1c26] text-gray-400"
                      >
                        <Minus size={12} />
                      </button>
                      <input
                        type="number"
                        value={config.frame_skip ?? 0}
                        onChange={(e) =>
                          setConfig({
                            ...config,
                            frame_skip: parseInt(e.target.value) || 0,
                          })
                        }
                        className="w-10 bg-transparent text-center text-xs font-bold outline-none"
                      />
                      <button
                        onClick={() =>
                          setConfig({
                            ...config,
                            frame_skip: (config.frame_skip ?? 0) + 1,
                          })
                        }
                        className="p-1.5 hover:bg-[#1a1c26] text-gray-400"
                      >
                        <Plus size={12} />
                      </button>
                    </div>
                  ) : (
                    <Toggle
                      enabled={!!config[module.key as keyof ISystemSettings]}
                      onToggle={() =>
                        setConfig({
                          ...config,
                          [module.key]:
                            !config[module.key as keyof ISystemSettings],
                        })
                      }
                    />
                  )}
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default Settings;
