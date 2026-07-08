import React, { useState } from "react";
import { Shield, Lock, User, Loader2 } from "lucide-react";
import axios from "axios";

interface LoginProps {
  onLoginSuccess: (token: string) => void;
}

const Login = ({ onLoginSuccess }: LoginProps) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await axios.post(
        "http://127.0.0.1:8000/api/v1/auth/login",
        {
          username,
          password,
        },
      );

      if (response.data.access_token) {
        onLoginSuccess(response.data.access_token);
      }
    } catch  {
      setError("Invalid credentials. Please try again.");
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
            AeroGuard AI
          </h1>
          <p className="text-gray-500 mt-2">Smart Surveillance Platform</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-500/10 border border-red-500/50 text-red-500 p-3 rounded-lg text-sm text-center">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Username
            </label>
            <div className="relative">
              <User
                className="absolute left-3 top-3.5 text-gray-500"
                size={18}
              />
              <input
                type="text"
                className="w-full bg-black/20 border border-white/10 rounded-xl py-3 px-10 text-white focus:border-ag-danger outline-none transition-all"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Password
            </label>
            <div className="relative">
              <Lock
                className="absolute left-3 top-3.5 text-gray-500"
                size={18}
              />
              <input
                type="password"
                className="w-full bg-black/20 border border-white/10 rounded-xl py-3 px-10 text-white focus:border-ag-danger outline-none transition-all"
                placeholder="••••••••"
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
              "Authorize Access"
            )}
          </button>
        </form>

        <p className="text-center text-gray-600 text-xs mt-8 uppercase tracking-widest">
          Secure Infrastructure Node
        </p>
      </div>
    </div>
  );
};

export default Login;
