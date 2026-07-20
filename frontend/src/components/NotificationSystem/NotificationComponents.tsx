import React, { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle,
  Info,
  TriangleAlert,
  CircleX,
  Loader,
  X,
  AlertTriangle,
} from "lucide-react";
import { useNotification } from "./useNotification.ts";
import type { Toast } from "./NotificationContext.ts";

// ==========================================
// TOAST ITEM COMPONENT
// ==========================================

export const ToastItem: React.FC<{ toast: Toast }> = ({ toast }) => {
  const { dismissToast } = useNotification();
  const { id, type, title, description, duration } = toast;

  const [hovered, setHovered] = useState(false);
  const [remainingTime, setRemainingTime] = useState<number>(duration || 0);
  const startTimeRef = useRef<number | null>(null);
  const timerIdRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync remaining time if ID or duration updates
  useEffect(() => {
    setRemainingTime(duration || 0);
  }, [id, duration]);

  // Auto-dismiss with hover pause
  useEffect(() => {
    if (!duration) return;

    if (!hovered) {
      startTimeRef.current = Date.now();
      timerIdRef.current = setTimeout(() => {
        dismissToast(id);
      }, remainingTime);
    }

    return () => {
      if (timerIdRef.current) {
        clearTimeout(timerIdRef.current);
        timerIdRef.current = null;
      }
    };
  }, [id, duration, hovered, dismissToast, remainingTime]);

  const handleMouseEnter = () => {
    setHovered(true);
    if (duration && startTimeRef.current) {
      const elapsed = Date.now() - startTimeRef.current;
      setRemainingTime((prev) => Math.max(0, prev - elapsed));
    }
  };

  const handleMouseLeave = () => {
    setHovered(false);
  };

  // Type specific configurations
  const getConfig = () => {
    switch (type) {
      case "success":
        return {
          bgClass: "bg-[#0b1324]/95 border-[#1e2d4a]",
          accentBg: "bg-emerald-500",
          iconBg: "bg-emerald-950/40 border border-emerald-500/20",
          iconColor: "text-emerald-400",
          icon: <CheckCircle className="w-5 h-5" id={`toast-icon-${id}`} />,
        };
      case "info":
        return {
          bgClass: "bg-[#0b1324]/95 border-[#1e2d4a]",
          accentBg: "bg-blue-500",
          iconBg: "bg-blue-950/40 border border-blue-500/20",
          iconColor: "text-blue-400",
          icon: <Info className="w-5 h-5" id={`toast-icon-${id}`} />,
        };
      case "warning":
        return {
          bgClass: "bg-[#0b1324]/95 border-[#1e2d4a]",
          accentBg: "bg-amber-500",
          iconBg: "bg-amber-950/40 border border-amber-500/20",
          iconColor: "text-amber-400",
          icon: <TriangleAlert className="w-5 h-5" id={`toast-icon-${id}`} />,
        };
      case "error":
        return {
          bgClass: "bg-[#0b1324]/95 border-[#1e2d4a]",
          accentBg: "bg-rose-500",
          iconBg: "bg-rose-950/40 border border-rose-500/20",
          iconColor: "text-rose-400",
          icon: <CircleX className="w-5 h-5" id={`toast-icon-${id}`} />,
        };
      case "loading":
        return {
          bgClass: "bg-[#0b1324]/95 border-[#1e2d4a]",
          accentBg: "bg-slate-500",
          iconBg: "bg-slate-950/40 border border-slate-500/20",
          iconColor: "text-slate-400",
          icon: (
            <Loader className="w-5 h-5 animate-spin" id={`toast-icon-${id}`} />
          ),
        };
    }
  };

  const config = getConfig();

  return (
    <motion.div
      layout
      id={`toast-card-${id}`}
      initial={{ opacity: 0, x: 50, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 100, scale: 0.9, transition: { duration: 0.2 } }}
      transition={{ type: "spring", stiffness: 350, damping: 25 }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className={`relative flex items-center w-full md:w-[380px] rounded-[14px] p-4 ${config.bgClass} border shadow-lg shadow-black/50 overflow-hidden pointer-events-auto group`}
    >
      <div className="flex gap-3.5 items-start w-full pr-6">
        {/* Rounded square icon container 40x40px */}
        <div
          id={`toast-icon-container-${id}`}
          className={`flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-xl ${config.iconBg} ${config.iconColor}`}
        >
          {config.icon}
        </div>

        {/* Center: Title & Description */}
        <div id={`toast-content-${id}`} className="flex-grow min-w-0 pt-0.5">
          <h4
            id={`toast-title-${id}`}
            className="text-[14px] font-bold text-white tracking-wide"
          >
            {title}
          </h4>
          <p
            id={`toast-desc-${id}`}
            className="text-[13px] font-medium text-slate-400 mt-1 leading-normal"
          >
            {description}
          </p>
        </div>
      </div>

      {/* Right: Absolute Close button */}
      <button
        id={`toast-close-${id}`}
        onClick={() => dismissToast(id)}
        className="absolute top-3 right-3 flex-shrink-0 text-slate-500 hover:text-slate-300 opacity-70 hover:opacity-100 transition-all focus:outline-none p-1.5"
      >
        <X className="w-3.5 h-3.5" />
      </button>

      {/* Dynamic progress bar animating from 100% to 0% and pausing on hover */}
      {duration && (
        <motion.div
          id={`toast-progress-${id}`}
          initial={{ width: "100%" }}
          animate={{
            width: hovered ? `${(remainingTime / duration) * 100}%` : "0%",
          }}
          transition={{
            duration: hovered ? 0 : remainingTime / 1000,
            ease: "linear",
          }}
          className={`absolute bottom-0 left-0 h-[2.5px] ${config.accentBg}`}
        />
      )}
    </motion.div>
  );
};

// ==========================================
// TOAST CONTAINER COMPONENT
// ==========================================

export const ToastContainer: React.FC = () => {
  const { toasts } = useNotification();

  return (
    <div
      id="toast-container"
      className="fixed top-6 right-6 z-50 flex flex-col gap-3 w-full max-w-[400px] px-4 md:px-0 pointer-events-none"
    >
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} />
        ))}
      </AnimatePresence>
    </div>
  );
};

// ==========================================
// CONFIRMATION DIALOG COMPONENT
// ==========================================

export const ConfirmationDialog: React.FC = () => {
  const { activeConfirmation, closeConfirmation } = useNotification();
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!activeConfirmation) return null;

  const {
    title,
    description,
    confirmLabel = "Confirm",
    cancelLabel = "Cancel",
    type = "warning",
    onConfirm,
    onCancel,
  } = activeConfirmation;

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      await onConfirm();
    } catch (e) {
      console.error(e);
    } finally {
      setIsSubmitting(false);
      closeConfirmation();
    }
  };

  const handleCancel = () => {
    if (onCancel) onCancel();
    closeConfirmation();
  };

  const getTheme = () => {
    switch (type) {
      case "danger":
        return {
          iconColor: "text-rose-400",
          iconBg: "bg-rose-500/10 border border-rose-500/20",
          confirmBtn:
            "bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-white",
          accentBg: "bg-rose-500",
        };
      case "warning":
        return {
          iconColor: "text-amber-400",
          iconBg: "bg-amber-500/10 border border-amber-500/20",
          confirmBtn:
            "bg-amber-600 hover:bg-amber-500 active:bg-amber-700 text-white",
          accentBg: "bg-amber-500",
        };
      case "info":
      default:
        return {
          iconColor: "text-blue-400",
          iconBg: "bg-blue-500/10 border border-blue-500/20",
          confirmBtn:
            "bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white",
          accentBg: "bg-blue-500",
        };
    }
  };

  const theme = getTheme();

  return (
    <AnimatePresence>
      <div
        id="confirm-modal-overlay"
        className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto"
      >
        {/* Soft blur backdrop overlay */}
        <motion.div
          id="confirm-modal-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-slate-950/80 backdrop-blur-md"
          onClick={handleCancel}
        />

        {/* Modal Dialog container */}
        <motion.div
          id="confirm-modal-card"
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ type: "spring", duration: 0.3, bounce: 0.15 }}
          className="relative w-full max-w-md bg-[#0d1527] border border-[#1e2d4a] rounded-2xl shadow-2xl shadow-black/80 overflow-hidden p-6 z-10"
        >
          <div className="flex flex-col items-center text-center mt-2">
            {/* Large warning/action icon */}
            <div
              className={`w-14 h-14 rounded-full flex items-center justify-center mb-4 ${theme.iconBg} ${theme.iconColor}`}
            >
              <AlertTriangle className="w-7 h-7" id="confirm-modal-icon" />
            </div>

            {/* Title */}
            <h3
              id="confirm-modal-title"
              className="text-lg font-bold text-white tracking-wide"
            >
              {title}
            </h3>

            {/* Description */}
            <p
              id="confirm-modal-desc"
              className="text-sm font-medium text-slate-400 mt-2 leading-relaxed max-w-sm"
            >
              {description}
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-center gap-3 mt-6">
            <button
              id="confirm-modal-cancel-btn"
              type="button"
              disabled={isSubmitting}
              onClick={handleCancel}
              className="flex-1 max-w-[140px] px-4 py-2.5 rounded-lg border border-slate-700 hover:border-slate-600 bg-slate-900/60 text-slate-300 hover:text-white font-medium text-sm transition-all focus:outline-none"
            >
              {cancelLabel}
            </button>
            <button
              id="confirm-modal-confirm-btn"
              type="button"
              disabled={isSubmitting}
              onClick={handleConfirm}
              className={`flex-1 max-w-[140px] px-4 py-2.5 rounded-lg font-medium text-sm transition-all focus:outline-none flex items-center justify-center gap-1.5 ${theme.confirmBtn} disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {isSubmitting ? (
                <>
                  <Loader className="w-4 h-4 animate-spin" />
                  Processing
                </>
              ) : (
                confirmLabel
              )}
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

// ==========================================
// COMBINED NOTIFICATION RENDERER
// ==========================================

export const NotificationRenderer: React.FC = () => {
  return (
    <>
      <ToastContainer />
      <ConfirmationDialog />
    </>
  );
};
