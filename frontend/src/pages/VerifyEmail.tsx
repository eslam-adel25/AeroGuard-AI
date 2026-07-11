import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { CheckCircle2, Loader2 } from "lucide-react";
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

  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const token = searchParams.get("token");
    if (!token) {
      setStatus("error");
      setMessage("Verification token is missing.");
      return;
    }

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
  }, [location.search]);

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

        {status !== "loading" && (
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
