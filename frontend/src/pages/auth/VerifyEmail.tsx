import axios, { AxiosError } from "axios";
import { useEffect, useMemo, useState, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { CheckCircle2, Loader2, Mail, Shield, AlertCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { authService } from "../../services/api";
import { motion, AnimatePresence } from "framer-motion";

/**
 * إعدادات ثابتة للعناصر المتحركة في الخلفية
 * تم نقلها خارج المكون لمنع استدعاء Math.random() أثناء الـ Render
 * ولحل مشاكل ESLint وضمان أداء ثابت.
 */
const BG_RECTS = Array.from({ length: 8 }, (_, i) => ({
  id: i,
  width: 100 + ((i * 15) % 50),
  height: 150 + ((i * 20) % 100),
  left: ((i * 12) % 100) + "%",
  duration: 20 + ((i * 5) % 10),
  delay: i * 2,
}));

const BG_PARTICLES = Array.from({ length: 20 }, (_, i) => ({
  id: i,
  left: ((i * 7) % 100) + "%",
  top: ((i * 13) % 100) + "%",
  duration: 5 + ((i * 2) % 5),
  delay: (i * 0.5) % 10,
}));

const AnimatedBackground = () => {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden bg-[#0a0c12]">
      {/* Grid Overlay */}
      <div
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: `linear-gradient(#1e293b 1px, transparent 1px), linear-gradient(90deg, #1e293b 1px, transparent 1px)`,
          backgroundSize: "80px 80px",
        }}
      />

      {/* Floating Glowing Rectangles */}
      {BG_RECTS.map((rect) => (
        <motion.div
          key={`rect-${rect.id}`}
          className="absolute rounded-sm border border-blue-500/30 bg-blue-500/5"
          initial={{
            width: rect.width,
            height: rect.height,
            left: rect.left,
            top: "110%",
            opacity: 0.1,
          }}
          animate={{
            top: "-20%",
            opacity: [0.1, 0.3, 0.1],
          }}
          transition={{
            duration: rect.duration,
            repeat: Infinity,
            ease: "linear",
            delay: rect.delay,
          }}
        />
      ))}

      {/* Floating Particles */}
      {BG_PARTICLES.map((p) => (
        <motion.div
          key={`particle-${p.id}`}
          className="absolute h-1 w-1 rounded-full bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.8)]"
          initial={{
            left: p.left,
            top: p.top,
            opacity: 0,
          }}
          animate={{
            opacity: [0, 0.8, 0],
            scale: [0, 1.5, 0],
          }}
          transition={{
            duration: p.duration,
            repeat: Infinity,
            ease: "easeInOut",
            delay: p.delay,
          }}
        />
      ))}

      {/* Moving Digital Scanning Line */}
      <motion.div
        className="absolute left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-blue-500/50 to-transparent shadow-[0_0_15px_rgba(59,130,246,0.5)]"
        animate={{ top: ["0%", "100%", "0%"] }}
        transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
      />
    </div>
  );
};

const VerifyEmail = () => {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading",
  );
  const [message, setMessage] = useState<string>("");
  const [code, setCode] = useState(["", "", "", "", "", ""]);
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [timer, setTimer] = useState(120); // 02:00
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const searchParams = useMemo(
    () => new URLSearchParams(location.search),
    [location.search],
  );

  // منطق العداد التنازلي
  useEffect(() => {
    if (timer > 0) {
      const interval = setInterval(() => setTimer((t) => t - 1), 1000);
      return () => clearInterval(interval);
    }
  }, [timer]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

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
            "سيتم التواصل معك من قبل خدمة العملاء خلال 24 ساعة لتفعيل حسابكم",
          );
        })
        .catch((err: unknown) => {
          let detailMessage = "Verification failed. The link may have expired.";

          if (axios.isAxiosError(err)) {
            const axiosError = err as AxiosError<{ detail?: string }>;
            detailMessage = axiosError.response?.data?.detail ?? detailMessage;
          }

          setStatus("error");
          setMessage(detailMessage);
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
  }, [searchParams, navigate]);

  const handleOtpChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;
    const newCode = [...code];
    newCode[index] = value.slice(-1);
    setCode(newCode);

    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handleVerifyCode = async () => {
    const fullCode = code.join("");
    if (!email.trim() || fullCode.length < 6) {
      setStatus("error");
      setMessage("Please complete the 6-digit verification code.");
      return;
    }

    setSubmitting(true);
    try {
      await authService.verifyOtp(email, fullCode);
      setStatus("success");
      setMessage(
        "سيتم التواصل معك من قبل خدمة العملاء خلال 24 ساعة لتفعيل حسابكم",
      );
    } catch (err: unknown) {
      let detailMessage = "Verification failed. Invalid authentication packet.";

      if (axios.isAxiosError(err)) {
        const axiosError = err as AxiosError<{ detail?: string }>;
        detailMessage = axiosError.response?.data?.detail ?? detailMessage;
      }

      setStatus("error");
      setCode(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
      setMessage(detailMessage);
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    if (!email.trim() || timer > 0) return;

    setResending(true);
    try {
      await authService.resendVerification(email);
      setTimer(120);
      setStatus("error");
      setMessage("A secure verification packet has been re-transmitted.");
    } catch (err: unknown) {
      let detailMessage = "Unable to resend. Please try again later.";

      if (axios.isAxiosError(err)) {
        const axiosError = err as AxiosError<{ detail?: string }>;
        detailMessage = axiosError.response?.data?.detail ?? detailMessage;
      }

      setMessage(detailMessage);
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center p-4">
      <AnimatedBackground />

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{
          opacity: 1,
          scale: 1,
          y: 0,
          x: status === "error" && submitting ? [0, -10, 10, -10, 10, 0] : 0,
        }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <div className="relative overflow-hidden rounded-[2rem] border border-blue-500/20 bg-[#121620]/80 p-8 shadow-[0_20px_50px_rgba(0,0,0,0.5)] backdrop-blur-xl md:p-10">
          {/* Header Icon */}
          <div className="mb-8 flex justify-center">
            <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl border border-blue-500/20 bg-blue-500/10 shadow-[0_0_20px_rgba(59,130,246,0.2)]">
              <AnimatePresence mode="wait">
                {status === "loading" || submitting ? (
                  <motion.div
                    key="loader"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <Loader2 className="animate-spin text-blue-400" size={30} />
                  </motion.div>
                ) : status === "success" ? (
                  <motion.div
                    key="success"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="text-green-400"
                  >
                    <CheckCircle2 size={32} />
                  </motion.div>
                ) : (
                  <motion.div
                    key="shield"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-blue-400"
                  >
                    <Shield size={30} />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          <div className="text-center">
            <h1 className="text-xl font-bold text-white tracking-tight">
              {t("Verify Your Email")}
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-gray-400">
              We've sent a secure 6-digit verification code to your email
              address.
            </p>
          </div>

          <div className="mt-8 rounded-xl border border-white/5 bg-white/[0.03] p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white/5">
                <Mail className="text-blue-400" size={18} />
              </div>
              <div className="flex-1 overflow-hidden">
                <p className="truncate text-sm font-medium text-white">
                  {email || "user@example.com"}
                </p>
                <p className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-green-500">
                  <span className="h-1 w-1 animate-pulse rounded-full bg-green-500" />
                  {status === "success"
                    ? "Email verified; activation pending"
                    : "Code Sent"}
                </p>
              </div>
              <button
                onClick={() => navigate(-1)}
                className="text-xs font-bold text-blue-400 transition-colors hover:text-blue-300"
              >
                Change
              </button>
            </div>
          </div>

          <div className="mt-8">
            <div className="flex justify-between gap-2 md:gap-3">
              {code.map((digit, idx) => (
                <motion.input
                  key={idx}
                  ref={(el) => {
                    inputRefs.current[idx] = el;
                  }}
                  type="text"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handleOtpChange(idx, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(idx, e)}
                  className={`h-12 w-full rounded-xl border bg-white/5 text-center text-xl font-bold text-white outline-none transition-all focus:scale-105 focus:ring-2 md:h-14 ${
                    status === "success"
                      ? "border-green-500/50 ring-green-500/20 shadow-[0_0_15px_rgba(34,197,94,0.2)]"
                      : status === "error" && submitting
                        ? "border-red-500/50"
                        : "border-white/10 focus:border-blue-500/50 focus:ring-blue-500/20"
                  }`}
                />
              ))}
            </div>

            <div className="mt-6 flex flex-col items-center gap-1">
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-500">
                {submitting ? (
                  <span className="flex items-center gap-1">
                    Encrypting Authentication Packet
                    <motion.span
                      animate={{ opacity: [0, 1, 0] }}
                      transition={{ repeat: Infinity, duration: 1.5 }}
                    >
                      ...
                    </motion.span>
                  </span>
                ) : status === "success" ? (
                  <span className="text-green-500">Access Granted</span>
                ) : (
                  "Secure Channel Established"
                )}
              </p>
              {message && status === "error" && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-1.5 text-xs text-red-400"
                >
                  <AlertCircle size={14} /> {message}
                </motion.div>
              )}
              {status === "success" && (
                <div className="mt-4 space-y-4">
                  <p className="text-sm leading-7 text-white" dir="rtl" lang="ar">
                    {message}
                  </p>
                  <button
                    type="button"
                    onClick={() => navigate("/login")}
                    className="rounded-xl bg-blue-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-blue-400"
                  >
                    Proceed to login
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="mt-8 space-y-4">
            <button
              onClick={handleVerifyCode}
              disabled={submitting || status === "success"}
              className="relative w-full overflow-hidden rounded-xl bg-blue-500 py-4 text-sm font-bold text-white shadow-lg transition-all hover:bg-blue-400 hover:shadow-blue-500/20 active:scale-[0.98] disabled:opacity-50"
            >
              <AnimatePresence mode="wait">
                {submitting ? (
                  <motion.div
                    key="submitting"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex items-center justify-center gap-2"
                  >
                    <Loader2 className="animate-spin" size={18} />
                    Validating...
                  </motion.div>
                ) : (
                  <motion.span
                    key="verify"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    Verify Email
                  </motion.span>
                )}
              </AnimatePresence>
            </button>

            <div className="flex flex-col items-center gap-2">
              <p className="text-xs font-medium text-gray-500">
                Didn't receive the code?{" "}
                <button
                  onClick={handleResend}
                  disabled={timer > 0 || resending}
                  className={`font-bold transition-colors ${timer > 0 ? "text-gray-600" : "text-blue-400 hover:text-blue-300"}`}
                >
                  {timer > 0
                    ? `Resend in ${formatTime(timer)}`
                    : resending
                      ? "Transmitting..."
                      : "Send New Code"}
                </button>
              </p>
            </div>
          </div>
        </div>

        {/* Footer Disclaimer */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="mt-8 text-center text-xs text-gray-500"
        >
          By verifying, you agree to AeroGuard AI's{" "}
          <span className="cursor-pointer text-gray-400 underline decoration-gray-600">
            Security Terms
          </span>
          .
        </motion.p>
      </motion.div>
    </div>
  );
};

export default VerifyEmail;
