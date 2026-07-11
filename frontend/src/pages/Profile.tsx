import React, { useState, useEffect, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import { userService } from "../services/api";
import type { IUserProfile } from "../services/api";
import {
  User,
  Calendar,
  LogIn,
  Key,
  Camera as CameraIcon,
  Save,
  Loader2,
  Users as UsersIcon,
  ChevronRight,
  BadgeCheck,
  Building,
  Phone,
  Fingerprint,
} from "lucide-react";

interface UserActivity {
  id: string;
  user_id: string;
  event_type: string;
  details?: Record<string, unknown> | null;
  ip_address?: string | null;
  user_agent?: string | null;
  created_at: string;
}

interface UserSession {
  token: string;
  expires_at: string | null;
  revoked: boolean;
  created_at: string | null;
}

const Profile: React.FC = () => {
  const { t } = useTranslation();
  // --- States ---
  const [profile, setProfile] = useState<IUserProfile | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [activity, setActivity] = useState<UserActivity[]>([]);
  const [sessions, setSessions] = useState<UserSession[]>([]);

  // دالة مرجعية لفتح نافذة اختيار الصور
  const fileInputRef = useRef<HTMLInputElement>(null);

  // States لتغيير كلمة المرور
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

  const loadActivity = async () => {
    try {
      const res = await userService.getActivity();
      setActivity(res.data || []);
    } catch (err) {
      console.warn("Failed to load activity", err);
    }
  };

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
    loadActivity();
    loadSessions();
  }, [loadProfile]);

  // تحديث البيانات الأساسية (Section 3)
  const handleUpdateInfo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) return;
    setIsSaving(true);
    try {
      await userService.updateProfile(profile);
      alert("✅ Security identity updated successfully!");
      setIsEditing(false);
    } catch {
      alert("❌ Failed to update registry.");
    } finally {
      setIsSaving(false);
    }
  };

  // تغيير كلمة المرور (Section 1)
  const handlePasswordRotate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwords.new_password !== passwords.confirm_password) {
      return alert("❌ New passwords do not match!");
    }
    try {
      await userService.updatePassword({
        old_password: passwords.old_password,
        new_password: passwords.new_password,
      });
      alert("✅ Credentials rotated successfully!");
      setPasswords({
        old_password: "",
        new_password: "",
        confirm_password: "",
      });
    } catch {
      alert("❌ Authentication Error: Current password incorrect.");
    }
  };

  // رفع الصورة الشخصية (Section 3)
  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    setIsUploading(true);
    try {
      await userService.uploadAvatar(formData);
      await loadProfile(); // إعادة التحميل لإظهار الصورة الجديدة
      alert("✅ Avatar updated!");
      loadActivity();
    } catch {
      alert("❌ Failed to upload image.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleChangeEmail = async () => {
    const newEmail = window.prompt("Enter your new email:");
    if (!newEmail) return;
    try {
      await userService.changeEmail(newEmail);
      alert(
        "Verification email sent to new address. Follow the link to confirm.",
      );
      loadActivity();
    } catch (err) {
      console.warn("Failed to request email change", err);
      alert("Failed to request email change.");
    }
  };

  const handleLogoutAll = async () => {
    if (!window.confirm("Logout all sessions?")) return;
    try {
      await userService.logoutAllSessions();
      alert("All sessions logged out.");
      loadSessions();
      loadActivity();
    } catch {
      alert("Failed to logout sessions.");
    }
  };

  if (isLoading)
    return (
      <div className="h-screen flex items-center justify-center bg-ag-dark">
        <Loader2 className="animate-spin text-ag-danger" size={48} />
      </div>
    );

  return (
    <div className="p-8 font-sans animate-in fade-in duration-700 max-w-6xl mx-auto pb-20">
      {/* Header */}
      <div className="flex justify-between items-center mb-10">
        <div className="flex items-center gap-4">
          <div className="bg-ag-card p-3 rounded-2xl border border-white/5 shadow-xl">
            <Fingerprint className="text-ag-danger" size={24} />
          </div>
          <div>
            <h2 className="text-3xl font-black text-white tracking-tight uppercase">
              {t("profile.title")}
            </h2>
            <p className="text-gray-500 text-sm font-medium">
              {t("profile.subtitle")}: {profile?.role?.role_name}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* العمود الأيسر: بطاقة الهوية */}
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-ag-card rounded-[3rem] p-8 border border-white/5 shadow-2xl flex flex-col items-center text-center relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-24 bg-gradient-to-b from-ag-danger/20 to-transparent"></div>

            {/* Avatar Section */}
            <div className="relative group mb-6 mt-4">
              <div className="w-32 h-32 rounded-[2.5rem] bg-ag-dark border-4 border-ag-card shadow-2xl flex items-center justify-center overflow-hidden">
                {profile?.profile_picture ? (
                  <img
                    src={profile.profile_picture}
                    className="w-full h-full object-cover"
                    alt="Avatar"
                  />
                ) : (
                  <User size={48} className="text-gray-700" />
                )}
                {isUploading && (
                  <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
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
                className="absolute bottom-0 right-0 p-3 bg-ag-danger text-white rounded-2xl shadow-lg hover:scale-110 transition-all border-4 border-ag-card"
              >
                <CameraIcon size={18} />
              </button>
            </div>

            <h3 className="text-2xl font-black text-white tracking-tight">
              {profile?.full_name}
            </h3>
            <div className="flex items-center gap-2 mt-2 px-4 py-1.5 bg-ag-warning/10 text-ag-warning rounded-full border border-ag-warning/20">
              <BadgeCheck size={14} />
              <span className="text-[10px] font-black uppercase tracking-widest">
                {profile?.role?.role_name}
              </span>
            </div>

            <div className="w-full mt-8 pt-8 border-t border-white/5 space-y-4">
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-500 font-bold uppercase tracking-tighter">
                  {t("profile.accountStatus")}
                </span>
                <span className="text-ag-success font-black flex items-center gap-1">
                  ● {profile?.status}
                </span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-500 font-bold uppercase tracking-tighter">
                  {t("profile.systemId")}
                </span>
                <span className="text-white font-mono">
                  {profile?.user_id?.slice(0, 13)}
                </span>
              </div>
            </div>
          </div>

          {/* سجل الدخول (Access Logs) */}
          <div className="bg-ag-card/50 rounded-[2.5rem] p-6 border border-white/5 space-y-4 backdrop-blur-md">
            <h4 className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-4 ml-2">
              {t("profile.accessHistory")}
            </h4>
            <div className="flex items-start gap-4">
              <div className="p-2.5 bg-blue-500/10 text-blue-400 rounded-xl">
                <Calendar size={16} />
              </div>
              <div>
                <p className="text-[10px] text-gray-400 font-bold">
                  {t("profile.commissionedOn")}
                </p>
                <p className="text-xs text-white font-mono">
                  {new Date(profile?.created_at || "").toLocaleDateString()}
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="p-2.5 bg-ag-success/10 text-ag-success rounded-xl">
                <LogIn size={16} />
              </div>
              <div>
                <p className="text-[10px] text-gray-400 font-bold">
                  {t("profile.lastLogin")}
                </p>
                <p className="text-xs text-white font-mono">
                  {profile?.last_login
                    ? new Date(profile.last_login).toLocaleString()
                    : "First Session"}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* العمود الأيمن: النماذج */}
        <div className="lg:col-span-8 space-y-8">
          {/* General Info Form */}
          <form
            onSubmit={handleUpdateInfo}
            className="bg-ag-card rounded-[3rem] p-10 border border-white/5 shadow-2xl space-y-8"
          >
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-3 text-ag-primary">
                <UsersIcon size={20} className="text-ag-danger" />
                <h3 className="text-xl font-black uppercase tracking-tighter">
                  {t("profile.registryData")}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsEditing(!isEditing)}
                className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest transition-all ${isEditing ? "bg-ag-danger text-white" : "text-ag-danger border border-ag-danger/30 hover:bg-ag-danger/10"}`}
              >
                {isEditing
                  ? t("profile.discardChanges")
                  : t("profile.modifyRecord")}
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-[10px] text-gray-500 font-black uppercase ml-4">
                  {t("profile.fullIdentityName")}
                </label>
                <input
                  disabled={!isEditing}
                  value={profile?.full_name}
                  onChange={(e) =>
                    setProfile({ ...profile!, full_name: e.target.value })
                  }
                  className="w-full bg-ag-dark border border-white/5 p-4 rounded-2xl text-white outline-none focus:border-ag-danger disabled:opacity-40 transition-all font-bold"
                />
              </div>
              <div className="space-y-2">
                <label className="text-[10px] text-gray-500 font-black uppercase ml-4">
                  {t("profile.corporateEmail")}
                </label>
                <div className="flex gap-3">
                  <input
                    disabled={!isEditing}
                    value={profile?.email}
                    onChange={(e) =>
                      setProfile({ ...profile!, email: e.target.value })
                    }
                    className="flex-1 bg-ag-dark border border-white/5 p-4 rounded-2xl text-white outline-none focus:border-ag-danger disabled:opacity-40 transition-all font-bold"
                  />
                  <button
                    type="button"
                    onClick={handleChangeEmail}
                    className="px-3 py-2 rounded-lg bg-white/5 text-xs font-bold"
                  >
                    Change
                  </button>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-[10px] text-gray-500 font-black uppercase ml-4 flex items-center gap-2">
                  <Phone size={12} /> Secure Contact Line
                </label>
                <input
                  disabled={!isEditing}
                  value={profile?.phone || ""}
                  onChange={(e) =>
                    setProfile({ ...profile!, phone: e.target.value })
                  }
                  className="w-full bg-ag-dark border border-white/5 p-4 rounded-2xl text-white outline-none focus:border-ag-danger disabled:opacity-40 transition-all font-bold"
                />
              </div>
              <div className="space-y-2">
                <label className="text-[10px] text-gray-500 font-black uppercase ml-4 flex items-center gap-2">
                  <Building size={12} /> Assigned Organization
                </label>
                <input
                  disabled={!isEditing}
                  value={profile?.organization || ""}
                  onChange={(e) =>
                    setProfile({ ...profile!, organization: e.target.value })
                  }
                  className="w-full bg-ag-dark border border-white/5 p-4 rounded-2xl text-white outline-none focus:border-ag-danger disabled:opacity-40 transition-all font-bold"
                />
              </div>
            </div>

            {isEditing && (
              <button
                type="submit"
                disabled={isSaving}
                className="bg-ag-success text-white px-10 py-4 rounded-2xl font-black text-sm shadow-xl flex items-center gap-3 active:scale-95 transition-all"
              >
                {isSaving ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <>
                    <Save size={18} /> Commit Update
                  </>
                )}
              </button>
            )}
          </form>

          {/* Credential Rotation Form */}
          <form
            onSubmit={handlePasswordRotate}
            className="bg-ag-card rounded-[3rem] p-10 border border-white/5 shadow-2xl space-y-8"
          >
            <div className="flex items-center gap-3 text-ag-primary">
              <Key size={20} className="text-ag-warning" />
              <h3 className="text-xl font-black uppercase tracking-tighter">
                {t("profile.credentialRotation")}
              </h3>
            </div>

            <div className="space-y-5">
              <input
                type="password"
                required
                placeholder={t("profile.currentSystemPassword")}
                value={passwords.old_password}
                onChange={(e) =>
                  setPasswords({ ...passwords, old_password: e.target.value })
                }
                className="w-full bg-ag-dark border border-white/5 p-4 rounded-2xl text-white outline-none focus:border-ag-warning font-bold"
              />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input
                  type="password"
                  required
                  placeholder={t("profile.newSecurePassword")}
                  value={passwords.new_password}
                  onChange={(e) =>
                    setPasswords({ ...passwords, new_password: e.target.value })
                  }
                  className="w-full bg-ag-dark border border-white/5 p-4 rounded-2xl text-white outline-none focus:border-ag-warning font-bold"
                />
                <input
                  type="password"
                  required
                  placeholder={t("profile.confirmNewPassword")}
                  value={passwords.confirm_password}
                  onChange={(e) =>
                    setPasswords({
                      ...passwords,
                      confirm_password: e.target.value,
                    })
                  }
                  className="w-full bg-ag-dark border border-white/5 p-4 rounded-2xl text-white outline-none focus:border-ag-warning font-bold"
                />
              </div>
              <button
                type="submit"
                className="bg-white/5 text-ag-warning hover:bg-ag-warning/10 border border-ag-warning/20 px-8 py-4 rounded-2xl font-black text-sm transition-all shadow-lg active:scale-95"
              >
                {t("profile.rotateCredentials")}
              </button>
            </div>
          </form>

          {/* Admin Directory Link (Only for Admins - Section 3) */}
          {profile?.role?.role_name === "Administrator" && (
            <div className="bg-gradient-to-r from-ag-danger to-red-900 rounded-[2.5rem] p-10 flex justify-between items-center shadow-2xl ring-1 ring-white/10">
              <div>
                <h4 className="text-2xl font-black text-white tracking-tight">
                  {t("profile.personnelDirectory")}
                </h4>
                <p className="text-white/60 text-xs mt-1 font-medium">
                  Authorized to manage all system nodes and operator access
                  records
                </p>
              </div>
              <button className="bg-white text-ag-danger p-4 rounded-2xl font-black shadow-xl hover:scale-105 active:scale-95 transition-all">
                <ChevronRight size={24} />
              </button>
            </div>
          )}

          {/* Activity Timeline */}
          <div className="bg-ag-card rounded-[3rem] p-8 border border-white/5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-black">Activity Timeline</h3>
              <button onClick={loadActivity} className="text-sm text-gray-400">
                Refresh
              </button>
            </div>
            <div className="space-y-3 max-h-48 overflow-auto">
              {activity.length === 0 && (
                <p className="text-sm text-gray-500">No recent activity</p>
              )}
              {activity.map((a) => (
                <div key={a.id} className="flex items-start gap-3">
                  <div className="w-10 text-xs text-gray-400">
                    {new Date(a.created_at).toLocaleString()}
                  </div>
                  <div>
                    <div className="text-sm font-bold">{a.event_type}</div>
                    <div className="text-xs text-gray-400">
                      {JSON.stringify(a.details || {})}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Sessions */}
          <div className="bg-ag-card rounded-[3rem] p-8 border border-white/5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-black">Active Sessions</h3>
              <div className="flex gap-2">
                <button
                  onClick={loadSessions}
                  className="text-sm text-gray-400"
                >
                  Refresh
                </button>
                <button
                  onClick={handleLogoutAll}
                  className="text-sm bg-red-600 px-3 py-1 rounded text-white"
                >
                  Logout All
                </button>
              </div>
            </div>
            <div className="space-y-2">
              {sessions.length === 0 && (
                <p className="text-sm text-gray-500">No active sessions</p>
              )}
              {sessions.map((s) => (
                <div
                  key={s.token}
                  className="flex items-center justify-between text-sm"
                >
                  <div className="font-mono">
                    {s.token.slice(0, 8)}...{s.token.slice(-8)}
                  </div>
                  <div className="text-gray-400">
                    {s.created_at
                      ? new Date(s.created_at).toLocaleString()
                      : "—"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;
