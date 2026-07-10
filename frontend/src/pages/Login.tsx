import React, { useState } from "react";
import { Shield, Lock, User, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import api from "../services/api";

interface LoginProps {
  onLoginSuccess: (token: string) => void;
}

const Login = ({ onLoginSuccess }: LoginProps) => {
  const { t } = useTranslation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await api.post("/auth/login", {
        username,
        password,
      });

      if (response.data.access_token) {
        onLoginSuccess(response.data.access_token);
      }
    } catch {
      setError(t("auth.invalidCredentials"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ag-dark flex items-center justify-center p-4">
      <div className="bg-ag-card w-full max-w-md p-8 rounded-3xl border border-white/5 shadow-2xl">
        {/* Logo & Header */}
        <div className="text-center mb-10">
          <div className="inline-flex p-4 bg-ag-danger/10 rounded-2xl mb-4">
            <Shield className="text-ag-danger" size={48} />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">
            {t("auth.loginTitle")}
          </h1>
          <p className="text-gray-500 mt-2">{t("auth.loginSubtitle")}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-500/10 border border-red-500/50 text-red-500 p-3 rounded-lg text-sm text-center">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              {t("auth.username")}
            </label>
            <div className="relative">
              <User
                className="absolute left-3 top-3.5 text-gray-500"
                size={18}
              />
              <input
                type="text"
                className="w-full bg-black/20 border border-white/10 rounded-xl py-3 px-10 text-white focus:border-ag-danger outline-none transition-all"
                placeholder={t("auth.enterUsername")}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              {t("auth.password")}
            </label>
            <div className="relative">
              <Lock
                className="absolute left-3 top-3.5 text-gray-500"
                size={18}
              />
              <input
                type="password"
                className="w-full bg-black/20 border border-white/10 rounded-xl py-3 px-10 text-white focus:border-ag-danger outline-none transition-all"
                placeholder={t("auth.enterPassword")}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-ag-danger hover:bg-red-600 text-white font-bold py-4 rounded-xl transition-all flex items-center justify-center gap-2"
          >
            {loading ? (
              <Loader2 className="animate-spin" size={20} />
            ) : (
              t("auth.authorizeAccess")
            )}
          </button>
        </form>

        <p className="text-center text-gray-600 text-xs mt-8 uppercase tracking-widest">
          {t("auth.secureInfrastructureNode")}
        </p>
      </div>
    </div>
  );
};

export default Login;
