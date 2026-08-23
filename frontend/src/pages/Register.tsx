import React, { useState } from "react";
import axios from "axios";
import { useNavigate, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { authService } from "../services/api";
import surveillanceImg from "../assets/images/auth/surveillance-control-room.png";
import {
  Mail,
  Phone,
  Loader2,
  ShieldAlert,
  UserPlus,
  Cpu,
  Eye,
  Plane,
  Activity,
  Globe,
} from "lucide-react";

const Register = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [agreed, setAgreed] = useState(false);

  const [form, setForm] = useState({
    full_name: "",
    username: "",
    email: "",
    password: "",
    confirm_password: "",
    phone: "",
    organization: "",
  });

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agreed) return;
    setError("");

    if (!form.full_name.trim()) {
      return setError("Full name is required.");
    }
    if (!form.username.trim()) {
      return setError("Username is required.");
    }
    if (form.username.trim().length < 3) {
      return setError("Username must be at least 3 characters.");
    }
    if (!form.email.trim()) {
      return setError("Corporate email is required.");
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      return setError("Please enter a valid email address.");
    }
    if (!form.phone.trim()) {
      return setError("Phone number is required.");
    }
    if (!form.password || form.password.length < 8) {
      return setError("Password must be at least 8 characters.");
    }
    if (form.password !== form.confirm_password) {
      return setError(t("auth.passwordsDoNotMatch"));
    }

    setLoading(true);
    try {
      await authService.register(form);
      navigate(`/verify-email?email=${encodeURIComponent(form.email)}`);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail ?? t("auth.usernameOrEmailTaken"));
      } else {
        setError(t("auth.registrationFailed"));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0c0e12] text-white font-sans flex flex-col">
      {/* Header */}
      <header className="flex justify-between items-center px-8 py-6">
        <div className="text-xl font-bold tracking-tight">AeroGuard AI</div>
        <Link
          to="/login"
          className="text-sm font-medium hover:text-gray-300 transition-colors"
        >
          Log In
        </Link>
      </header>

      {/* Main Content */}
      <main className="flex-grow flex flex-col lg:flex-row items-center justify-center px-6 lg:px-20 py-10 gap-16 lg:gap-24">
        {/* Left Side: Branding */}
        <div className="flex-1 max-w-xl space-y-8">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-blue-500/30 bg-blue-500/10 text-[11px] font-bold tracking-widest text-blue-400 uppercase">
            <Globe size={14} className="animate-pulse" />
            AI-POWERED SMART SURVEILLANCE
          </div>

          <div className="space-y-4">
            <h1 className="text-5xl lg:text-6xl font-bold leading-[1.1] tracking-tight">
              Smarter Airport &<br />
              Transit Surveillance
            </h1>
            <p className="text-gray-400 text-lg leading-relaxed max-w-lg">
              Monitor airports, railway stations, metro systems, and
              transportation hubs using AI-powered video analytics, real-time
              detection, intelligent alerts, and centralized security
              management.
            </p>
          </div>

          <div className="relative group">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-2xl blur opacity-30 group-hover:opacity-50 transition duration-1000"></div>
            <img
              src={surveillanceImg}
              alt="Surveillance Control Room"
              className="relative rounded-2xl border border-white/10 shadow-2xl w-full h-auto object-cover"
            />
          </div>
        </div>

        {/* Right Side: Form */}
        <div className="flex-1 w-full max-w-md">
          <div className="space-y-2 mb-8">
            <h2 className="text-3xl font-bold">Create AeroGuard Account</h2>
            <p className="text-gray-400 text-sm">
              Create your secure AeroGuard AI account to access the intelligent
              surveillance platform.
            </p>
          </div>

          <form onSubmit={handleRegister} className="space-y-5">
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 p-4 rounded-xl flex items-center gap-3 text-red-400 text-sm font-medium">
                <ShieldAlert size={18} className="shrink-0" /> {error}
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">
                  Full Name
                </label>
                <input
                  className="w-full bg-[#161a21] border border-gray-800 p-3 rounded-lg text-white outline-none focus:border-blue-500/50 transition-all placeholder:text-gray-600"
                  placeholder="johnnathan doe"
                  value={form.full_name}
                  onChange={(e) =>
                    setForm({ ...form, full_name: e.target.value })
                  }
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">
                  Username
                </label>
                <input
                  className="w-full bg-[#161a21] border border-gray-800 p-3 rounded-lg text-white outline-none focus:border-blue-500/50 transition-all placeholder:text-gray-600"
                  placeholder="j.doe_admin"
                  value={form.username}
                  onChange={(e) =>
                    setForm({ ...form, username: e.target.value })
                  }
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">
                Email Address
              </label>
              <div className="relative group">
                <Mail
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-blue-400 transition-colors"
                  size={18}
                />
                <input
                  className="w-full bg-[#161a21] border border-gray-800 p-3 pl-10 rounded-lg text-white outline-none focus:border-blue-500/50 transition-all placeholder:text-gray-600"
                  type="email"
                  placeholder="j.doe@company.corp"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">
                Phone Number
              </label>
              <div className="relative group">
                <Phone
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-blue-400 transition-colors"
                  size={18}
                />
                <input
                  className="w-full bg-[#161a21] border border-gray-800 p-3 pl-10 rounded-lg text-white outline-none focus:border-blue-500/50 transition-all placeholder:text-gray-600"
                  placeholder="+1 (555) 000-0000"
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">
                Organization / Airport / Station
              </label>
              <input
                className="w-full bg-[#161a21] border border-gray-800 p-3 rounded-lg text-white outline-none focus:border-blue-500/50 transition-all placeholder:text-gray-600"
                placeholder="Global Logistics Corp"
                value={form.organization}
                onChange={(e) =>
                  setForm({ ...form, organization: e.target.value })
                }
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">
                  Password
                </label>
                <input
                  className="w-full bg-[#161a21] border border-gray-800 p-3 rounded-lg text-white outline-none focus:border-blue-500/50 transition-all placeholder:text-gray-600"
                  type="password"
                  placeholder="••••••••"
                  value={form.password}
                  onChange={(e) =>
                    setForm({ ...form, password: e.target.value })
                  }
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">
                  Confirm Password
                </label>
                <input
                  className="w-full bg-[#161a21] border border-gray-800 p-3 rounded-lg text-white outline-none focus:border-blue-500/50 transition-all placeholder:text-gray-600"
                  type="password"
                  placeholder="••••••••"
                  value={form.confirm_password}
                  onChange={(e) =>
                    setForm({ ...form, confirm_password: e.target.value })
                  }
                  required
                />
              </div>
            </div>

            <div className="flex items-center gap-3 py-2">
              <input
                type="checkbox"
                id="terms"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
                className="w-4 h-4 rounded bg-[#161a21] border-gray-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-0"
              />
              <label htmlFor="terms" className="text-sm text-gray-400">
                I agree to the{" "}
                <span className="text-gray-200 cursor-pointer hover:underline">
                  Terms & Conditions
                </span>{" "}
                and{" "}
                <span className="text-gray-200 cursor-pointer hover:underline">
                  Privacy Policy
                </span>
                .
              </label>
            </div>

            <button
              type="submit"
              disabled={loading || !agreed}
              className="w-full bg-[#7c8ca8]/80 hover:bg-[#7c8ca8] disabled:opacity-50 disabled:cursor-not-allowed text-white py-3.5 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 mt-4 shadow-lg shadow-black/20"
            >
              {loading ? (
                <Loader2 className="animate-spin" size={20} />
              ) : (
                <>
                  <UserPlus size={19} /> Create Account
                </>
              )}
            </button>
          </form>

          <div className="text-center mt-8">
            <p className="text-gray-400 text-sm">
              Already have an AeroGuard account?{" "}
              <Link to="/login" className="text-blue-400 hover:underline">
                Login Link
              </Link>
            </p>
          </div>

          <div className="mt-12 pt-8 border-t border-gray-800/50 flex flex-col items-center gap-6">
            <div className="flex items-center gap-4 w-full">
              <div className="h-[1px] flex-grow bg-gray-800/50"></div>
              <span className="text-[10px] font-bold text-gray-600 uppercase tracking-widest whitespace-nowrap">
                Trusted Security Platform
              </span>
              <div className="h-[1px] flex-grow bg-gray-800/50"></div>
            </div>
            <div className="flex items-center gap-8 text-gray-500">
              <Cpu
                size={20}
                className="hover:text-gray-300 transition-colors"
              />
              <Eye
                size={20}
                className="hover:text-gray-300 transition-colors"
              />
              <Plane
                size={20}
                className="hover:text-gray-300 transition-colors"
              />
              <Activity
                size={20}
                className="hover:text-gray-300 transition-colors"
              />
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-900 px-8 py-6 flex flex-col md:flex-row justify-between items-center gap-4">
        <p className="text-xs text-gray-500 font-medium">
          © 2027 AeroGuard AI. All rights reserved.
        </p>
        <div className="flex flex-wrap justify-center gap-6 text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
          <Link
            to="/privacy-policy"
            className="hover:text-white transition-colors"
          >
            Privacy Policy
          </Link>
          <button className="hover:text-white transition-colors">
            Terms of Service
          </button>
          <button className="hover:text-white transition-colors">
            Documentation
          </button>
          <button className="hover:text-white transition-colors">
            Support
          </button>
          <button className="hover:text-white transition-colors">
            Contact
          </button>
        </div>
      </footer>
    </div>
  );
};

export default Register;
