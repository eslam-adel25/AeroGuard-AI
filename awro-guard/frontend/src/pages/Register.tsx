import React, { useState } from "react";
import axios from "axios";
import { useNavigate, Link } from "react-router-dom";
import { authService } from "../services/api";
import {
  ShieldCheck,
  User,
  Mail,
  Lock,
  Phone,
  Building,
  Loader2,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";

const Register = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
    setError("");

    // 1. التحقق من تطابق كلمات السر (Section 1)
    if (form.password !== form.confirm_password) {
      return setError("Passwords do not match");
    }

    setLoading(true);
    try {
      // 2. إرسال البيانات للباكيند
      await authService.register(form);
      alert("✅ Registration Successful! Please login with your credentials.");
      navigate("/login");
    }  catch (err) {
  if (axios.isAxiosError(err)) {
    setError(
      err.response?.data?.detail ??
      "Registration failed. Username or Email may be taken."
    );
  } else {
    setError("Registration failed.");
  }
}
  };

  return (
    <div className="min-h-screen bg-ag-dark flex items-center justify-center p-6 font-sans">
      <div className="absolute inset-0 opacity-10 pointer-events-none overflow-hidden">
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-ag-danger rounded-full blur-[150px]"></div>
        <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-ag-success rounded-full blur-[150px]"></div>
      </div>

      <div className="bg-ag-card w-full max-w-2xl p-12 rounded-[3.5rem] border border-white/5 shadow-2xl relative backdrop-blur-xl">
        <div className="text-center mb-12">
          <div className="inline-flex p-4 bg-ag-danger/10 rounded-3xl mb-4 border border-ag-danger/20">
            <ShieldCheck className="text-ag-danger" size={40} />
          </div>
          <h2 className="text-4xl font-black text-white tracking-tighter uppercase">
            Operator Registry
          </h2>
          <p className="text-gray-500 mt-2 font-medium">
            Provision a new node administrator account
          </p>
        </div>

        <form onSubmit={handleRegister} className="space-y-6">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 p-4 rounded-2xl flex items-center gap-3 text-red-500 text-sm font-bold animate-pulse">
              <ShieldAlert size={18} /> {error}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="space-y-2">
              <label className="text-[10px] font-black text-gray-500 uppercase ml-4">
                Full Identity Name
              </label>
              <div className="relative group">
                <User
                  className="absolute left-5 top-5 text-gray-600 group-focus-within:text-ag-danger transition-colors"
                  size={18}
                />
                <input
                  className="w-full bg-ag-dark border border-white/5 p-5 pl-14 rounded-2xl text-white outline-none focus:border-ag-danger transition-all font-bold"
                  placeholder="Eslam Ahmed"
                  onChange={(e) =>
                    setForm({ ...form, full_name: e.target.value })
                  }
                  required
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-black text-gray-500 uppercase ml-4">
                System Username
              </label>
              <div className="relative group">
                <User
                  className="absolute left-5 top-5 text-gray-600 group-focus-within:text-ag-danger transition-colors"
                  size={18}
                />
                <input
                  className="w-full bg-ag-dark border border-white/5 p-5 pl-14 rounded-2xl text-white outline-none focus:border-ag-danger transition-all font-bold"
                  placeholder="eslam_node1"
                  onChange={(e) =>
                    setForm({ ...form, username: e.target.value })
                  }
                  required
                />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="space-y-2">
              <label className="text-[10px] font-black text-gray-500 uppercase ml-4">
                Corporate Email
              </label>
              <div className="relative group">
                <Mail
                  className="absolute left-5 top-5 text-gray-600 group-focus-within:text-ag-danger transition-colors"
                  size={18}
                />
                <input
                  className="w-full bg-ag-dark border border-white/5 p-5 pl-14 rounded-2xl text-white outline-none focus:border-ag-danger transition-all font-bold"
                  type="email"
                  placeholder="admin@airport.gov"
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-black text-gray-500 uppercase ml-4">
                Secure Phone Line
              </label>
              <div className="relative group">
                <Phone
                  className="absolute left-5 top-5 text-gray-600 group-focus-within:text-ag-danger transition-colors"
                  size={18}
                />
                <input
                  className="w-full bg-ag-dark border border-white/5 p-5 pl-14 rounded-2xl text-white outline-none focus:border-ag-danger transition-all font-bold"
                  placeholder="+20 123..."
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  required
                />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="space-y-2">
              <label className="text-[10px] font-black text-gray-500 uppercase ml-4">
                Master Password
              </label>
              <div className="relative group">
                <Lock
                  className="absolute left-5 top-5 text-gray-600 group-focus-within:text-ag-danger transition-colors"
                  size={18}
                />
                <input
                  className="w-full bg-ag-dark border border-white/5 p-5 pl-14 rounded-2xl text-white outline-none focus:border-ag-danger transition-all font-bold"
                  type="password"
                  placeholder="••••••••"
                  onChange={(e) =>
                    setForm({ ...form, password: e.target.value })
                  }
                  required
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-black text-gray-500 uppercase ml-4">
                Confirm Encryption
              </label>
              <div className="relative group">
                <Lock
                  className="absolute left-5 top-5 text-gray-600 group-focus-within:text-ag-danger transition-colors"
                  size={18}
                />
                <input
                  className="w-full bg-ag-dark border border-white/5 p-5 pl-14 rounded-2xl text-white outline-none focus:border-ag-danger transition-all font-bold"
                  type="password"
                  placeholder="••••••••"
                  onChange={(e) =>
                    setForm({ ...form, confirm_password: e.target.value })
                  }
                  required
                />
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-[10px] font-black text-gray-500 uppercase ml-4">
              Organization (Optional)
            </label>
            <div className="relative group">
              <Building
                className="absolute left-5 top-5 text-gray-600 group-focus-within:text-ag-danger transition-colors"
                size={18}
              />
              <input
                className="w-full bg-ag-dark border border-white/5 p-5 pl-14 rounded-2xl text-white outline-none focus:border-ag-danger transition-all font-bold"
                placeholder="Airport Security Force"
                onChange={(e) =>
                  setForm({ ...form, organization: e.target.value })
                }
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-ag-danger hover:bg-red-600 text-white py-5 rounded-[2rem] font-black text-sm shadow-2xl shadow-red-900/40 hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-3 uppercase tracking-widest"
          >
            {loading ? (
              <Loader2 className="animate-spin" />
            ) : (
              <>
                Request Authorization <ArrowRight size={20} />
              </>
            )}
          </button>
        </form>

        <p className="text-center text-gray-600 text-xs mt-10 font-bold uppercase tracking-widest">
          Already authorized?{" "}
          <Link to="/login" className="text-ag-danger hover:underline">
            Establish Connection
          </Link>
        </p>
      </div>
    </div>
  );
};

export default Register;
