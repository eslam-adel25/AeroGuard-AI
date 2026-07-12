import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { CheckCircle2, Loader2, Mail } from "lucide-react";
import { useTranslation } from "react-i18next";
import { authService } from "../services/api";

const VerifyEmail = () => {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading",
  );
  const [message, setMessage] = useState<string>("");
  const [code, setCode] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);

  const searchParams = useMemo(
    () => new URLSearchParams(location.search),
    [location.search],
  );

  useEffect(() => {
    const token = searchParams.get("token");
    const emailFromQuery = searchParams.get("email") || "";
    if (emailFromQuery) {
      setEmail(emailFromQuery);
    }

    if (token) {
      authService
        .verifyEmail(token)
        .then(() => {
          setStatus("success");
          setMessage(
            "Your email has been verified. You may now log in with your credentials.",
          );
        })
        .catch((err) => {
          setStatus("error");
          setMessage(
            err.response?.data?.detail ||
              "Verification failed. The link may have expired.",
          );
        });
      return;
    }

    if (!emailFromQuery) {
      setStatus("error");
      setMessage("Enter your email address to receive and verify your code.");
    } else {
      setStatus("error");
      setMessage("Enter the verification code sent to your email.");
    }
  }, [searchParams]);

  const handleVerifyCode = async () => {
    if (!email.trim() || !code.trim()) {
      setStatus("error");
      setMessage("Please enter your email and verification code.");
      return;
    }

    setSubmitting(true);
    setMessage("");
    try {
      await authService.verifyOtp(email, code);
      setStatus("success");
      setMessage("Your email has been verified. You may now log in.");
    } catch (err: any) {
      setStatus("error");
      setMessage(
        err.response?.data?.detail ||
          "Verification failed. The code may be invalid or expired.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    if (!email.trim()) {
      setStatus("error");
      setMessage("Please enter your email address first.");
      return;
    }

    setResending(true);
    try {
      await authService.resendVerification(email);
      setStatus("error");
      setMessage("A new verification code has been sent.");
    } catch (err: any) {
      setStatus("error");
      setMessage(
        err.response?.data?.detail || "Unable to resend the verification code.",
      );
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen bg-ag-dark flex items-center justify-center p-4">
      <div className="bg-ag-card w-full max-w-lg p-10 rounded-3xl border border-white/10 shadow-2xl">
        <div className="text-center mb-8">
          <div className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-3xl bg-ag-danger/10 text-ag-danger">
            {status === "loading" ? (
              <Loader2 className="animate-spin" size={32} />
            ) : (
              <CheckCircle2 size={32} />
            )}
          </div>
          <h1 className="text-3xl font-black text-white tracking-tight">
            {t("auth.verifyEmailTitle")}
          </h1>
          <p className="text-gray-400 mt-3">
            {status === "loading" ? "Verifying your email address..." : message}
          </p>
        </div>

        {status !== "loading" && status !== "success" && (
          <div className="space-y-4">
            <div className="relative">
              <Mail className="absolute left-4 top-4 text-gray-500" size={18} />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-ag-dark px-11 py-3 text-white outline-none"
                placeholder="Enter your email"
              />
            </div>
            <div className="relative">
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-ag-dark px-4 py-3 text-white outline-none"
                placeholder="Enter 6-digit verification code"
              />
            </div>
            <button
              type="button"
              onClick={handleVerifyCode}
              disabled={submitting}
              className="w-full rounded-2xl bg-ag-danger px-5 py-4 text-sm font-semibold text-white transition hover:bg-red-600 disabled:opacity-60"
            >
              {submitting ? "Verifying..." : "Verify Code"}
            </button>
            <button
              type="button"
              onClick={handleResend}
              disabled={resending}
              className="w-full rounded-2xl border border-white/10 px-5 py-3 text-sm font-semibold text-gray-300 transition hover:bg-white/5 disabled:opacity-60"
            >
              {resending ? "Sending..." : "Resend code"}
            </button>
          </div>
        )}

        {status === "success" && (
          <div className="space-y-4">
            <button
              type="button"
              onClick={() => navigate("/login")}
              className="w-full rounded-2xl bg-ag-danger px-5 py-4 text-sm font-semibold text-white transition hover:bg-red-600"
            >
              Back to Login
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default VerifyEmail;
