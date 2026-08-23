import React, { useState } from "react";
import {
  Shield,
  Lock,
  User,
  Loader2,
  Eye,
  EyeOff,
  ShieldCheck,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import api from "../services/api";
import surveillanceImg from "../assets/images/auth/surveillance-control-room.png";

interface LoginProps {
  onLoginSuccess: (token: string) => void;
}

const Login = ({ onLoginSuccess }: LoginProps) => {
  const { t } = useTranslation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await api.post("/auth/login", {
        username,
        password,
      });

      const token = response.data?.access_token;
      if (
        typeof token === "string" &&
        token.trim() &&
        token !== "null" &&
        token !== "undefined"
      ) {
        localStorage.setItem("ag_token", token);
        localStorage.setItem("user", JSON.stringify(response.data.user ?? {}));
        onLoginSuccess(token);
        window.dispatchEvent(new Event("auth:login"));
      } else {
        setError(t("auth.invalidCredentials"));
      }
    } catch {
      setError(t("auth.invalidCredentials"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0c0e12] text-white font-sans flex flex-col">
      {/* Header */}
      <header className="flex justify-between items-center px-8 py-6 w-full max-w-screen-2xl mx-auto">
        <div className="flex items-center gap-2">
          <div className="bg-[#adc6ff] p-1.5 rounded-lg">
            <Shield className="text-[#0c0e12]" size={20} fill="currentColor" />
          </div>
          <span className="text-xl font-bold tracking-tight">AeroGuard AI</span>
        </div>
        <Link
          to="/register"
          className="text-sm font-medium hover:text-gray-300 transition-colors"
        >
          Create Account
        </Link>
      </header>

      {/* Main Section */}
      <main className="flex-grow flex flex-col lg:flex-row items-center justify-center px-6 lg:px-20 py-8 gap-12 lg:gap-24 max-w-screen-2xl mx-auto w-full">
        {/* Left Side: Marketing/Image */}
        <div className="flex-1 max-w-xl space-y-8">
          <div className="inline-block px-4 py-1.5 rounded-full bg-[#2a2d35] border border-white/5 text-[11px] font-bold tracking-widest text-gray-300 uppercase">
            AI-POWERED SMART SURVEILLANCE
          </div>

          <div className="space-y-6">
            <h1 className="text-5xl lg:text-6xl font-bold leading-[1.1] tracking-tight">
              Secure Access to
              <br />
              <span className="text-white">AeroGuard AI</span>
            </h1>
            <p className="text-gray-400 text-lg leading-relaxed max-w-md">
              Access the AeroGuard AI platform to monitor airports, railway
              stations, metro systems, and transportation hubs using AI-powered
              surveillance, real-time alerts, and centralized security
              management.
            </p>
          </div>

          <div className="relative">
            <div className="absolute inset-0 bg-blue-500/5 blur-3xl rounded-full"></div>
            <img
              src={surveillanceImg}
              alt="Surveillance Control Room"
              className="relative rounded-2xl border border-white/10 shadow-2xl w-full object-cover aspect-video"
            />
          </div>
        </div>

        {/* Right Side: Form */}
        <div className="flex-1 w-full max-w-md">
          <div className="mb-10">
            <h2 className="text-4xl font-bold mb-3">Welcome Back</h2>
            <p className="text-gray-400">
              Please enter your credentials to access your secure node.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl text-sm font-medium">
                {error}
              </div>
            )}

            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-400">
                Username
              </label>
              <div className="relative group">
                <User
                  className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600 group-focus-within:text-[#adc6ff] transition-colors"
                  size={20}
                />
                <input
                  type="text"
                  className="w-full bg-[#16191f] border border-[#2d3139] rounded-xl py-4 pl-12 pr-4 text-white focus:border-[#adc6ff]/50 outline-none transition-all placeholder:text-gray-700"
                  placeholder="admin_node_01"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <label className="block text-sm font-medium text-gray-400">
                  Password
                </label>
                <button
                  type="button"
                  className="text-xs font-bold text-gray-300 hover:text-white uppercase tracking-wider"
                >
                  Forgot?
                </button>
              </div>
              <div className="relative group">
                <Lock
                  className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600 group-focus-within:text-[#adc6ff] transition-colors"
                  size={20}
                />
                <input
                  type={showPassword ? "text" : "password"}
                  className="w-full bg-[#16191f] border border-[#2d3139] rounded-xl py-4 pl-12 pr-12 text-white focus:border-[#adc6ff]/50 outline-none transition-all placeholder:text-gray-700 font-mono"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-600 hover:text-gray-400"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="remember"
                className="w-4 h-4 rounded bg-[#16191f] border-[#2d3139] text-[#adc6ff] focus:ring-0 focus:ring-offset-0"
              />
              <label htmlFor="remember" className="text-sm text-gray-400">
                Remember this device for 30 days
              </label>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#adc6ff] hover:bg-[#97b8ff] text-[#0c0e12] font-bold py-4 rounded-xl transition-all shadow-lg shadow-[#adc6ff]/10 active:scale-[0.99] flex items-center justify-center gap-2 uppercase tracking-widest text-sm"
            >
              {loading ? (
                <Loader2 className="animate-spin" size={20} />
              ) : (
                "LOG IN"
              )}
            </button>
          </form>

          <div className="mt-12 pt-8 border-t border-white/5 flex flex-col items-center">
            <p className="text-gray-400 text-sm mb-10">
              Don't have an AeroGuard account?{" "}
              <Link
                to="/register"
                className="font-bold text-white hover:underline ml-1"
              >
                Create Account
              </Link>
            </p>

            <div className="flex items-center gap-12">
              <div className="flex flex-col items-center gap-1.5 opacity-40 hover:opacity-100 transition-opacity">
                <ShieldCheck size={20} className="text-gray-300" />
                <span className="text-[10px] font-bold uppercase tracking-tighter text-gray-400">
                  SECURE NODE
                </span>
              </div>
              <div className="w-[1px] h-8 bg-white/5"></div>
              <div className="flex flex-col items-center gap-1.5 opacity-40 hover:opacity-100 transition-opacity">
                <Lock size={18} className="text-gray-300" />
                <span className="text-[10px] font-bold uppercase tracking-tighter text-gray-400">
                  AES-256
                </span>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 px-8 py-6 w-full">
        <div className="max-w-screen-2xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-gray-500 font-medium">
          <div>© 2027 AeroGuard AI. All rights reserved.</div>
          <div className="flex flex-wrap justify-center gap-6">
            <Link
              to="/privacy-policy"
              className="hover:text-white transition-colors"
            >
              Privacy Policy
            </Link>
            <Link
              to="/terms-of-service"
              className="hover:text-white transition-colors"
            >
              Terms of Service
            </Link>
            <Link to="/docs" className="hover:text-white transition-colors">
              Documentation
            </Link>
            <Link to="/support" className="hover:text-white transition-colors">
              Support
            </Link>
            <button className="hover:text-white transition-colors">
              Contact
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Login;
