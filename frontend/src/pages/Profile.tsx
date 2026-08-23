import React, { useState, useEffect, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { userService } from "../services/api";
import type { IUserProfile } from "../services/api";
import { useNotification } from "../components/NotificationSystem/useNotification";
import {
  User,
  LogIn,
  Key,
  Save,
  Loader2,
  ChevronRight,
  RefreshCw,
  Info,
  Eye,
  EyeOff,
  Lock,
  Edit2,
  Database,
  Activity,
} from "lucide-react";

interface UserSession {
  token: string;
  expires_at: string | null;
  revoked: boolean;
  created_at: string | null;
  user_agent?: string | null;
  operating_system?: string | null;
  browser?: string | null;
  device_category?: string | null;
  device_type?: string | null;
  device_model?: string | null;
}

const getSessionDeviceLabel = (session: UserSession) => {
  const deviceType = session.device_type?.trim();
  if (deviceType && deviceType !== "Unknown") {
    return deviceType;
  }

  const operatingSystem = session.operating_system?.trim();
  const browser = session.browser?.trim();
  if (operatingSystem && browser) {
    return `${operatingSystem} • ${browser}`;
  }
  if (operatingSystem) {
    return operatingSystem;
  }
  if (browser) {
    return browser;
  }
  if (session.device_model?.trim()) {
    return session.device_model.trim();
  }

  return "Unknown";
};

const Profile: React.FC = () => {
  const { t } = useTranslation();
  const { confirm, toast } = useNotification();

  // --- States ---
  const [profile, setProfile] = useState<IUserProfile | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [sessions, setSessions] = useState<UserSession[]>([]);

  // Password visibility states
  const [showOldPass, setShowOldPass] = useState(false);
  const [showNewPass, setShowNewPass] = useState(false);
  const [showConfirmPass, setShowConfirmPass] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const [passwords, setPasswords] = useState({
    old_password: "",
    new_password: "",
    confirm_password: "",
  });

  // --- Functions ---

  const loadProfile = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await userService.getProfile();
      setProfile(res.data);
    } catch {
      console.error("❌ Failed to load security profile");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadSessions = async () => {
    try {
      const res = await userService.getSessions();
      setSessions(res.data || []);
    } catch (err) {
      console.warn("Failed to load sessions", err);
    }
  };

  useEffect(() => {
    loadProfile();
    loadSessions();
  }, [loadProfile]);

  const handleUpdateInfo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) return;
    setIsSaving(true);

    let toastId: string | null = null;
    try {
      toastId = toast.loading(t("common.processing"), t("common.pleaseWait"));
      await userService.updateProfile(profile);
      setIsEditing(false);
      if (toastId) {
        toast.update(toastId, {
          type: "success",
          title: t("common.done"),
          description: t("auth.securityIdentityUpdated"),
        });
      }
    } catch {
      if (toastId) {
        toast.update(toastId, {
          type: "error",
          title: t("common.status"),
          description: t("auth.profileUpdateFailed"),
        });
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handlePasswordRotate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwords.new_password !== passwords.confirm_password) {
      toast.error(t("common.status"), t("auth.passwordMismatch"));
      return;
    }

    let toastId: string | null = null;
    try {
      toastId = toast.loading(t("common.processing"), t("common.pleaseWait"));
      await userService.updatePassword({
        old_password: passwords.old_password,
        new_password: passwords.new_password,
      });
      if (toastId) {
        toast.update(toastId, {
          type: "success",
          title: t("common.done"),
          description: t("auth.credentialsRotated"),
        });
      }
      setPasswords({
        old_password: "",
        new_password: "",
        confirm_password: "",
      });
    } catch {
      if (toastId) {
        toast.update(toastId, {
          type: "error",
          title: t("common.status"),
          description: t("auth.invalidPassword"),
        });
      }
    }
  };

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    setIsUploading(true);
    let toastId: string | null = null;
    try {
      toastId = toast.loading(t("common.processing"), t("common.pleaseWait"));
      await userService.uploadAvatar(formData);
      await loadProfile();
      if (toastId) {
        toast.update(toastId, {
          type: "success",
          title: t("common.done"),
          description: t("auth.avatarUpdated"),
        });
      }
    } catch {
      if (toastId) {
        toast.update(toastId, {
          type: "error",
          title: t("common.status"),
          description: t("auth.avatarUploadFailed"),
        });
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleChangeEmail = async () => {
    const newEmail = window.prompt(t("profile.changeEmailPrompt"));
    if (!newEmail) return;

    let toastId: string | null = null;
    try {
      toastId = toast.loading(t("common.processing"), t("common.pleaseWait"));
      await userService.changeEmail(newEmail);
      if (toastId) {
        toast.update(toastId, {
          type: "success",
          title: t("common.done"),
          description: t("auth.verifyEmailResendSuccess"),
        });
      }
    } catch (err) {
      console.warn("Failed to request email change", err);
      if (toastId) {
        toast.update(toastId, {
          type: "error",
          title: t("common.status"),
          description: t("auth.verifyEmailResendFailed"),
        });
      }
    }
  };

  const handleLogoutAll = async () => {
    confirm({
      title: t("profile.logoutAll"),
      description: t("profile.logoutAllDescription"),
      confirmLabel: t("sidebar.logout"),
      cancelLabel: t("common.cancel"),
      type: "warning",
      onConfirm: async () => {
        let toastId: string | null = null;
        try {
          toastId = toast.loading(
            t("common.processing"),
            t("common.pleaseWait"),
          );
          await userService.logoutAllSessions();
          loadSessions();
          if (toastId) {
            toast.update(toastId, {
              type: "success",
              title: t("common.done"),
              description: t("auth.credentialsRotated"),
            });
          }
        } catch {
          if (toastId) {
            toast.update(toastId, {
              type: "error",
              title: t("common.status"),
              description: t("auth.profileUpdateFailed"),
            });
          }
        }
      },
    });
  };

  const sortedSessions = [...sessions].sort((a, b) => {
    const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
    const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
    return bTime - aTime;
  });

  if (isLoading)
    return (
      <div className="h-screen flex items-center justify-center bg-[#0c0e12]">
        <Loader2 className="animate-spin text-[#3b82f6]" size={48} />
      </div>
    );

  return (
    <div className="min-h-screen bg-[#0c0e12] text-white p-6 font-sans">
      {/* Top Header Navigation */}
      <header className="flex justify-between items-center mb-8 px-2">
        <div className="flex flex-col">
          <div className="flex items-center gap-2 text-xs text-gray-500 font-medium">
            <span>Aeroguard ai</span>
            <ChevronRight size={12} />
            <span className="text-blue-400">{t("profile.title")}</span>
          </div>
          <h1 className="text-2xl font-bold mt-1 tracking-tight">
            {t("profile.title")}
          </h1>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-[1600px] mx-auto">
        {/* Left Column (Security Profile & History) */}
        <div className="lg:col-span-4 space-y-6">
          {/* Security Profile Card */}
          <section className="bg-[#16191f] rounded-2xl p-6 border border-white/5 shadow-xl">
            <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-8">
              {t("profile.accountStatus")}
            </h2>
            <div className="flex flex-col items-center">
              <div className="relative mb-6">
                <div className="w-28 h-28 rounded-2xl bg-[#0c0e12] overflow-hidden border border-white/10 shadow-2xl">
                  {profile?.profile_picture ? (
                    <img
                      src={profile.profile_picture}
                      className="w-full h-full object-cover"
                      alt="Avatar"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center bg-gray-800">
                      <User size={40} />
                    </div>
                  )}
                  {isUploading && (
                    <div className="absolute inset-0 bg-black/60 flex items-center justify-center rounded-2xl">
                      <Loader2 className="animate-spin text-white" />
                    </div>
                  )}
                </div>
                <input
                  type="file"
                  ref={fileInputRef}
                  hidden
                  onChange={handleAvatarChange}
                  accept="image/*"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="absolute -bottom-2 -right-2 p-1.5 bg-blue-500 text-white rounded-lg shadow-xl hover:bg-blue-400 transition-colors"
                >
                  <Edit2 size={14} />
                </button>
              </div>

              <h3 className="text-xl font-bold mb-3">
                {profile?.full_name || t("profile.defaultName")}
              </h3>

              <div className="flex gap-2 mb-8">
                <span className="px-3 py-0.5 bg-indigo-500/10 text-indigo-400 text-[10px] font-bold rounded-md uppercase tracking-wider">
                  Global
                </span>
                <span className="px-3 py-0.5 bg-gray-800 text-gray-400 text-[10px] font-bold rounded-md uppercase tracking-wider">
                  {profile?.role?.role_name?.toLowerCase() || "admin"}
                </span>
              </div>

              <div className="w-full space-y-4 pt-6 border-t border-white/5">
                <div className="flex justify-between items-center text-[11px] font-medium">
                  <span className="text-gray-500">
                    {t("profile.accountStatus")}
                  </span>
                  <span className="text-green-500 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>{" "}
                    {t("profile.online")}
                  </span>
                </div>
                <div className="flex justify-between items-center text-[11px] font-medium">
                  <span className="text-gray-500">{t("profile.systemId")}</span>
                  <span className="bg-[#0c0e12] px-2 py-1 rounded text-white font-mono text-[10px]">
                    {profile?.user_id?.slice(0, 8).toUpperCase() ||
                      t("profile.defaultSystemId")}
                  </span>
                </div>
              </div>
            </div>
          </section>

          {/* Access History Card */}
          <section className="bg-[#16191f] rounded-2xl p-6 border border-white/5 shadow-xl">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest">
                {t("profile.accessHistory")}
              </h2>
              <button className="text-[11px] text-blue-400 hover:underline">
                {t("profile.viewLogs")}
              </button>
            </div>

            <div className="space-y-8 relative">
              <div className="absolute left-[7px] top-2 bottom-2 w-0.5 bg-white/5"></div>

              <div className="flex gap-4 relative">
                <div className="w-4 h-4 rounded-full border-2 border-gray-600 bg-[#16191f] z-10 flex-shrink-0 mt-1"></div>
                <div className="space-y-1">
                  <p className="text-sm font-bold">
                    {t("profile.commissionedOn")}
                  </p>
                  <p className="text-[10px] text-gray-500">
                    {profile?.created_at
                      ? new Date(profile.created_at).toLocaleDateString(
                          "en-US",
                          { month: "long", day: "numeric", year: "numeric" },
                        )
                      : "July 07, 2026"}
                  </p>
                  <p className="text-[11px] text-gray-400 leading-relaxed">
                    {t("profile.initialInstantiation")}
                  </p>
                </div>
              </div>

              <div className="flex gap-4 relative">
                <div className="w-4 h-4 rounded-full bg-blue-500 flex items-center justify-center z-10 flex-shrink-0 mt-1">
                  <LogIn size={8} className="text-white" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-bold">{t("profile.lastLogin")}</p>
                  <p className="text-[10px] text-gray-500">
                    {profile?.last_login
                      ? t("profile.active")
                      : "5 minutes ago"}
                  </p>
                  <p className="text-[11px] text-gray-400 leading-relaxed">
                    {t("profile.lastLoginDescription")}
                  </p>
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* Right Column (Registry & Credentials) */}
        <div className="lg:col-span-8 space-y-6">
          {/* Registry Data Form */}
          <section className="bg-[#16191f] rounded-2xl p-6 border border-white/5 shadow-xl">
            <header className="flex justify-between items-start mb-10">
              <div className="flex items-center gap-3">
                <div className="bg-[#0c0e12] p-2.5 rounded-xl border border-white/5">
                  <Database size={20} className="text-blue-400" />
                </div>
                <h2 className="text-xl font-bold">
                  {t("profile.registryData")}
                </h2>
              </div>
              <button
                onClick={() => setIsEditing(!isEditing)}
                className="px-6 py-2 bg-white/5 border border-white/5 text-[11px] font-bold rounded-lg hover:bg-white/10 transition-colors"
              >
                {isEditing
                  ? t("profile.discardChanges")
                  : t("profile.modifyRecord")}
              </button>
            </header>

            <form onSubmit={handleUpdateInfo} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-6">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-gray-500 uppercase ml-1">
                    {t("profile.fullIdentityName")}
                  </label>
                  <input
                    disabled={!isEditing}
                    value={profile?.full_name || ""}
                    onChange={(e) =>
                      setProfile({ ...profile!, full_name: e.target.value })
                    }
                    className="w-full bg-[#0c0e12] border border-white/5 p-4 rounded-xl text-sm font-medium outline-none focus:border-blue-500/50 disabled:text-gray-400 transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-gray-500 uppercase ml-1">
                    {t("profile.corporateEmail")}
                  </label>
                  <div className="flex gap-2">
                    <input
                      disabled={!isEditing}
                      value={profile?.email || ""}
                      onChange={(e) =>
                        setProfile({ ...profile!, email: e.target.value })
                      }
                      className="flex-1 bg-[#0c0e12] border border-white/5 p-4 rounded-xl text-sm font-medium outline-none focus:border-blue-500/50 disabled:text-gray-400 transition-all"
                    />
                    <button
                      type="button"
                      onClick={handleChangeEmail}
                      className="px-4 py-2 bg-white/5 border border-white/5 rounded-xl text-[10px] font-bold text-gray-400 hover:text-white"
                    >
                      {t("profile.changeEmail")}
                    </button>
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-gray-500 uppercase ml-1">
                    {t("profile.secureContactLine")}
                  </label>
                  <input
                    disabled={!isEditing}
                    value={profile?.phone || ""}
                    onChange={(e) =>
                      setProfile({ ...profile!, phone: e.target.value })
                    }
                    className="w-full bg-[#0c0e12] border border-white/5 p-4 rounded-xl text-sm font-medium outline-none focus:border-blue-500/50 disabled:text-gray-400 transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-gray-500 uppercase ml-1">
                    {t("profile.assignedOrganization")}
                  </label>
                  <input
                    disabled={!isEditing}
                    value={profile?.organization || ""}
                    onChange={(e) =>
                      setProfile({ ...profile!, organization: e.target.value })
                    }
                    className="w-full bg-[#0c0e12] border border-white/5 p-4 rounded-xl text-sm font-medium outline-none focus:border-blue-500/50 disabled:text-gray-400 transition-all"
                  />
                </div>
              </div>

              {isEditing && (
                <button
                  type="submit"
                  disabled={isSaving}
                  className="mt-4 px-10 py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl text-sm flex items-center gap-2 shadow-lg transition-all"
                >
                  {isSaving ? (
                    <Loader2 className="animate-spin" size={18} />
                  ) : (
                    <>
                      <Save size={18} /> Commit Update
                    </>
                  )}
                </button>
              )}

              <div className="bg-blue-600/10 border border-blue-500/20 rounded-xl p-4 flex gap-4 mt-8">
                <Info
                  size={20}
                  className="text-blue-400 flex-shrink-0 mt-0.5"
                />
                <p className="text-[11px] text-blue-300/80 leading-relaxed">
                  {t("profile.registryNotice")}
                </p>
              </div>
            </form>
          </section>

          {/* Credential Rotation Card */}
          <section className="bg-[#16191f] rounded-2xl p-6 border border-white/5 shadow-xl">
            <header className="flex items-center gap-3 mb-10">
              <div className="bg-[#0c0e12] p-2.5 rounded-xl border border-white/5">
                <Key size={20} className="text-blue-400" />
              </div>
              <h2 className="text-xl font-bold">
                {t("profile.credentialRotation")}
              </h2>
            </header>

            <form onSubmit={handlePasswordRotate} className="space-y-6">
              <div className="space-y-2">
                <label className="text-[10px] font-bold text-gray-500 uppercase ml-1">
                  {t("profile.currentSystemPassword")}
                </label>
                <div className="relative">
                  <input
                    type={showOldPass ? "text" : "password"}
                    required
                    value={passwords.old_password}
                    onChange={(e) =>
                      setPasswords({
                        ...passwords,
                        old_password: e.target.value,
                      })
                    }
                    className="w-full bg-[#0c0e12] border border-white/5 p-4 pr-24 rounded-xl text-sm font-medium outline-none focus:border-blue-500/50 transition-all placeholder:text-gray-700 font-mono"
                    placeholder={t("profile.passwordPlaceholder")}
                  />
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 flex gap-3 text-gray-600">
                    <button
                      type="button"
                      onClick={() => setShowOldPass(!showOldPass)}
                    >
                      {showOldPass ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                    <Lock size={18} />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-gray-500 uppercase ml-1">
                    {t("profile.newSecurePassword")}
                  </label>
                  <div className="relative">
                    <input
                      type={showNewPass ? "text" : "password"}
                      required
                      value={passwords.new_password}
                      onChange={(e) =>
                        setPasswords({
                          ...passwords,
                          new_password: e.target.value,
                        })
                      }
                      className="w-full bg-[#0c0e12] border border-white/5 p-4 rounded-xl text-sm font-medium outline-none focus:border-blue-500/50 transition-all placeholder:text-gray-700 font-mono"
                      placeholder={t("profile.passwordHint")}
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPass(!showNewPass)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-600"
                    >
                      {showNewPass ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-gray-500 uppercase ml-1">
                    {t("profile.confirmNewPassword")}
                  </label>
                  <div className="relative">
                    <input
                      type={showConfirmPass ? "text" : "password"}
                      required
                      value={passwords.confirm_password}
                      onChange={(e) =>
                        setPasswords({
                          ...passwords,
                          confirm_password: e.target.value,
                        })
                      }
                      className="w-full bg-[#0c0e12] border border-white/5 p-4 rounded-xl text-sm font-medium outline-none focus:border-blue-500/50 transition-all placeholder:text-gray-700 font-mono"
                      placeholder={t("profile.passwordReenter")}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPass(!showConfirmPass)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-600"
                    >
                      {showConfirmPass ? (
                        <EyeOff size={18} />
                      ) : (
                        <Eye size={18} />
                      )}
                    </button>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                className="mt-4 px-8 py-3 bg-gradient-to-r from-blue-300 via-blue-400 to-indigo-300 hover:from-blue-200 hover:to-indigo-200 text-black font-bold rounded-xl text-sm transition-all shadow-lg active:scale-[0.98]"
              >
                {t("profile.rotateCredentials")}
              </button>
            </form>
          </section>
        </div>

        {/* Bottom Section: Active Sessions */}
        <section className="lg:col-span-12 bg-[#16191f] rounded-2xl p-6 border border-white/5 shadow-xl mb-10 flex flex-col">
          <header className="flex justify-between items-center mb-4 shrink-0">
            <div className="flex items-center gap-3">
              <Activity size={18} className="text-blue-400" />
              <h2 className="text-sm font-bold">
                {t("profile.activeSessions")}
              </h2>
            </div>
            <div className="flex gap-3">
              <button
                onClick={loadSessions}
                className="flex items-center gap-2 px-6 py-2 bg-[#0c0e12] border border-white/5 rounded-lg text-[11px] font-bold text-gray-400 hover:text-white transition-colors"
              >
                <RefreshCw size={14} /> {t("common.refresh")}
              </button>
              <button
                onClick={handleLogoutAll}
                className="px-6 py-2 border border-red-500/30 text-red-400 rounded-lg text-[11px] font-bold hover:bg-red-500/10 transition-colors"
              >
                {t("profile.logoutAll")}
              </button>
            </div>
          </header>

          <div className="overflow-hidden rounded-xl border border-white/5 bg-[#0c0e12]">
            <div className="max-h-[420px] overflow-y-auto overflow-x-auto scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
              <table className="w-full text-left border-collapse">
                <thead className="sticky top-0 z-10 bg-[#0c0e12]">
                  <tr className="text-[10px] text-gray-500 font-bold uppercase border-b border-white/5 tracking-wider">
                    <th className="pb-4 pt-4 px-4 font-bold">
                      {t("profile.sessionId")}
                    </th>
                    <th className="pb-4 pt-4 px-4 font-bold">
                      {t("profile.loginDateTime")}
                    </th>
                    <th className="pb-4 pt-4 px-4 font-bold">
                      {t("profile.deviceType")}
                    </th>
                    <th className="pb-4 pt-4 px-4 text-right font-bold">
                      {t("common.status")}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {sortedSessions.length === 0 ? (
                    <tr>
                      <td
                        colSpan={4}
                        className="py-8 text-center text-gray-600 text-sm"
                      >
                        {t("profile.noActiveSessions")}
                      </td>
                    </tr>
                  ) : (
                    sortedSessions.map((s, idx) => (
                      <tr
                        key={s.token}
                        className="text-xs group hover:bg-white/[0.02] transition-colors"
                      >
                        <td className="py-6 px-4 font-mono text-gray-400">
                          sess_{s.token.slice(0, 4)}...{s.token.slice(-3)}
                        </td>
                        <td className="py-6 px-4 text-gray-400">
                          {s.created_at
                            ? new Date(s.created_at).toLocaleString()
                            : "—"}
                        </td>
                        <td className="py-6 px-4 text-gray-400">
                          {getSessionDeviceLabel(s)}
                        </td>
                        <td className="py-6 px-4 text-right">
                          <span
                            className={`px-3 py-1 rounded-md text-[10px] font-bold ${idx === 0 ? "bg-blue-600/20 text-blue-400" : "bg-gray-800 text-gray-500"}`}
                          >
                            {idx === 0
                              ? t("profile.active")
                              : t("profile.idle")}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>

      {/* Footer */}
      <footer className="max-w-[1600px] mx-auto border-t border-white/5 py-8 mt-10 px-2 flex flex-col md:flex-row justify-between items-center gap-6">
        <p className="text-xs text-gray-600 font-medium tracking-tight">
          © 2027 AeroGuard AI. All rights reserved.
        </p>
        <div className="flex gap-8 text-[11px] text-gray-500 font-bold tracking-tight uppercase">
          <Link
            to="/privacy-policy"
            className="hover:text-white transition-colors"
          >
            {t("profile.privacyPolicy")}
          </Link>
          <Link
            to="/terms-of-service"
            className="hover:text-white transition-colors"
          >
            {t("profile.termsOfService")}
          </Link>
          <button className="hover:text-white transition-colors">
            {t("profile.documentation")}
          </button>
          <button className="hover:text-white transition-colors">
            {t("profile.support")}
          </button>
          <button className="hover:text-white transition-colors">
            {t("profile.contact")}
          </button>
        </div>
      </footer>
    </div>
  );
};

export default Profile;
