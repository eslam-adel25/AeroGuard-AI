import { useMemo, useState, useEffect, useRef } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { createPortal } from "react-dom";
import { Bell, X, CheckCircle2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Cameras from "./pages/Cameras";
import Analytics from "./pages/Analytics";
import Users from "./pages/Profile";
import Settings from "./pages/Settings";
import Login from "./pages/Login";
import Register from "./pages/Register";
import VerifyEmail from "./pages/VerifyEmail";
import LanguageSwitcher from "./components/LanguageSwitcher";
import AlertHistory from "./pages/AlertHistory";
import ScreenshotModal from "./components/ScreenshotModal";
import {
  aiService,
  cameraService,
  formatScreenshotFilename,
  getFilenameFromContentDisposition,
  getStoredAuthToken,
} from "./services/api";
import { closeActiveSocket } from "./services/socket";
import {
  notificationService,
  type NotificationItem,
  type NotificationSeverity,
} from "./services/notificationService";

function App() {
  const { t } = useTranslation();
  const [activePage, setActivePage] = useState("dashboard");
  const [isAuthenticated, setIsAuthenticated] =
    useState(!!getStoredAuthToken());
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [cameraMap, setCameraMap] = useState<Record<string, string>>({});
  const [screenshotModalEventId, setScreenshotModalEventId] = useState<
    string | null
  >(null);
  const [screenshotCache] = useState(() => new Map<string, string>());
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [panelPosition, setPanelPosition] = useState({ top: 0, left: 0 });

  const panelRef = useRef<HTMLDivElement>(null);
  const bellRef = useRef<HTMLButtonElement>(null);

  const unreadCount = notifications.filter(
    (item) => item.status === "Unread",
  ).length;

  const sortedNotifications = useMemo(
    () =>
      [...notifications].sort(
        (a, b) => new Date(b.time).getTime() - new Date(a.time).getTime(),
      ),
    [notifications],
  );

  const pageTitle = useMemo(() => {
    switch (activePage) {
      case "cameras":
        return t("sidebar.cameras");
      case "reports":
        return t("sidebar.analytics");
      case "users":
        return t("sidebar.profile");
      case "settings":
        return t("sidebar.control");
      default:
        return t("sidebar.monitoring");
    }
  }, [activePage, t]);

  const handleLogin = (token: string) => {
    localStorage.setItem("ag_token", token);
    setIsAuthenticated(true);
    setActivePage("dashboard");
  };

  // Load user-specific settings after login
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const mod = await import("./services/api");
        const res = await mod.settingsService.get();
        if (res?.data) {
          localStorage.setItem("ag_settings", JSON.stringify(res.data));
        }
      } catch (err) {
        console.warn("Failed to load user settings after login", err);
      }
    };

    if (isAuthenticated) {
      loadSettings();
    }
  }, [isAuthenticated]);

  const handleLogout = () => {
    closeActiveSocket();
    localStorage.removeItem("ag_token");
    setIsAuthenticated(false);
    setActivePage("dashboard");
  };

  useEffect(() => {
    const handleDocumentClick = (event: MouseEvent) => {
      if (
        !panelRef.current ||
        !bellRef.current ||
        panelRef.current.contains(event.target as Node) ||
        bellRef.current.contains(event.target as Node)
      ) {
        return;
      }
      setIsNotificationsOpen(false);
    };

    const handleDocumentKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsNotificationsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleDocumentClick);
    document.addEventListener("keydown", handleDocumentKeyDown);

    return () => {
      document.removeEventListener("mousedown", handleDocumentClick);
      document.removeEventListener("keydown", handleDocumentKeyDown);
    };
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    const token = getStoredAuthToken();
    if (!token) {
      return;
    }

    let socketHandle: { close: () => void } | null = null;

    const hydrateNotification = (notification: NotificationItem) => {
      const resolvedCameraName =
        notification.cameraName &&
        notification.cameraId &&
        notification.cameraName !== notification.cameraId
          ? notification.cameraName
          : notification.cameraId && cameraMap[notification.cameraId]
            ? cameraMap[notification.cameraId]
            : notification.cameraName ||
              notification.cameraId ||
              "Unknown Camera";

      return {
        ...notification,
        cameraName: resolvedCameraName,
      };
    };

    const loadNotifications = async () => {
      const fetched = await notificationService.fetchNotifications();
      const hydrated = fetched.map(hydrateNotification);
      const sorted = [...hydrated].sort(
        (a, b) => new Date(b.time).getTime() - new Date(a.time).getTime(),
      );
      setNotifications((prev) => {
        const byId = new Map(prev.map((item) => [item.id, item]));
        sorted.forEach((item) => {
          const existing = byId.get(item.id);
          byId.set(item.id, existing ? { ...item, ...existing } : item);
        });
        return [...byId.values()].sort(
          (a, b) => new Date(b.time).getTime() - new Date(a.time).getTime(),
        );
      });
    };

    loadNotifications();

    socketHandle = notificationService.subscribeToLiveAlerts((notification) => {
      const hydrated = hydrateNotification(notification);
      setNotifications((prev) => {
        if (prev.some((item) => item.id === hydrated.id)) {
          return prev.map((item) =>
            item.id === hydrated.id ? { ...item, ...hydrated } : item,
          );
        }
        return [hydrated, ...prev];
      });
    });

    return () => {
      socketHandle?.close();
    };
  }, [isAuthenticated, cameraMap]);

  const fetchAndCacheScreenshot = async (eventId?: string | null) => {
    if (!eventId) return null;
    if (screenshotCache.has(eventId))
      return screenshotCache.get(eventId) as string;
    try {
      const resp = await aiService.downloadScreenshot(eventId);
      const blob = resp.data as Blob;
      const url = URL.createObjectURL(blob);
      screenshotCache.set(eventId, url);
      return url;
    } catch (err) {
      console.error("Failed to fetch screenshot", err);
      return null;
    }
  };

  useEffect(() => {
    if (!isAuthenticated) return;

    const loadCameras = async () => {
      try {
        const res = await cameraService.getAll();
        if (Array.isArray(res.data)) {
          const map = (res.data as Array<Record<string, unknown>>).reduce(
            (acc: Record<string, string>, item) => {
              const cameraId = String(item.camera_id ?? "");
              const cameraName = String(item.camera_name ?? "");
              if (cameraId && cameraName) {
                acc[cameraId] = cameraName;
              }
              return acc;
            },
            {},
          );
          setCameraMap(map);
        }
      } catch (err) {
        console.warn("Failed to load camera metadata", err);
      }
    };

    loadCameras();
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isNotificationsOpen || !bellRef.current) {
      return;
    }

    const updatePosition = () => {
      const rect = bellRef.current?.getBoundingClientRect();
      if (!rect) return;

      const panelWidth = 448;
      const left = Math.min(
        Math.max(rect.left + rect.width - panelWidth, 12),
        window.innerWidth - panelWidth - 12,
      );
      setPanelPosition({ top: rect.bottom + 12, left });
    };

    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);

    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [isNotificationsOpen]);

  const closeNotifications = () => setIsNotificationsOpen(false);

  const markNotificationAsRead = async (id: string) => {
    const notification = notifications.find((item) => item.id === id);
    if (notification?.eventId) {
      try {
        await aiService.markEventRead(notification.eventId);
      } catch (err) {
        console.error("Failed to mark notification as read", err);
        return;
      }
    }
    setNotifications((prev) =>
      prev.map((item) => (item.id === id ? { ...item, status: "Read" } : item)),
    );
  };

  const markAllAsRead = async () => {
    try {
      await aiService.markAllEventsRead();
    } catch (err) {
      console.error("Failed to mark notifications as read", err);
      return;
    }
    setNotifications((prev) =>
      prev.map((item) => ({ ...item, status: "Read" })),
    );
  };

  const clearNotifications = () => setNotifications([]);

  const getSeverityStyle = (severity: NotificationSeverity) => {
    switch (severity) {
      case "Critical":
        return "text-red-300 bg-red-500/10 border-red-400/20";
      case "High":
        return "text-orange-300 bg-orange-500/10 border-orange-400/20";
      case "Medium":
        return "text-amber-300 bg-amber-500/10 border-amber-400/20";
      case "Low":
        return "text-sky-300 bg-sky-500/10 border-sky-400/20";
      default:
        return "text-slate-300 bg-slate-500/10 border-slate-400/20";
    }
  };

  const formatNotificationDateTime = (isoTime: string) => {
    const date = new Date(isoTime);
    if (Number.isNaN(date.getTime())) {
      return { dateLabel: isoTime, timeLabel: "" };
    }

    return {
      dateLabel: date.toLocaleDateString(undefined, {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }),
      timeLabel: date.toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true,
      }),
    };
  };

  const authenticatedShell = (
    <div className="flex min-h-screen bg-ag-dark text-ag-primary">
      <Sidebar
        activePage={activePage}
        setActivePage={setActivePage}
        onLogout={handleLogout}
      />

      <div className="flex flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-white/10 bg-ag-card/70 px-4 backdrop-blur-xl md:px-6">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-gray-400">
              {t("app.dashboardTitle")}
            </p>
            <h2 className="text-lg font-black text-white">{pageTitle}</h2>
          </div>

          <div className="relative flex items-center gap-3">
            <LanguageSwitcher />

            <div className="relative">
              <button
                ref={bellRef}
                type="button"
                onClick={() => setIsNotificationsOpen((open) => !open)}
                className="relative rounded-full border border-white/10 bg-white/10 p-2.5 text-gray-300 transition-all hover:bg-white/20 hover:text-white"
                aria-label={t("common.notifications")}
                aria-expanded={isNotificationsOpen}
              >
                <Bell size={18} />
                {unreadCount > 0 && (
                  <span className="absolute -right-1 -top-1 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-red-500 px-1.5 text-[11px] font-semibold text-white">
                    {unreadCount}
                  </span>
                )}
              </button>

              {typeof document !== "undefined"
                ? createPortal(
                    <div
                      ref={panelRef}
                      className={`pointer-events-none fixed z-[99999] w-[min(100vw-2rem,28rem)] overflow-hidden rounded-3xl border border-white/10 bg-[#0b1220]/95 p-4 shadow-[0_24px_70px_rgba(0,0,0,0.65)] backdrop-blur-xl transition-all duration-300 ${
                        isNotificationsOpen
                          ? "pointer-events-auto opacity-100 scale-100"
                          : "pointer-events-none opacity-0 scale-95"
                      }`}
                      style={{
                        top: panelPosition.top,
                        left: panelPosition.left,
                        minWidth: 320,
                        overscrollBehavior: "contain",
                      }}
                    >
                      <div className="flex items-center justify-between gap-3 pb-4">
                        <div>
                          <p className="text-xs uppercase tracking-[0.28em] text-gray-400">
                            {t("common.notifications")}
                          </p>
                          <h3 className="text-lg font-black text-white">
                            {notifications.length > 0
                              ? t("app.notifications.title")
                              : t("app.notifications.noNewAlerts")}
                          </h3>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <button
                            type="button"
                            onClick={markAllAsRead}
                            className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-white transition hover:bg-white/10"
                          >
                            {t("app.notifications.markAllRead")}
                          </button>
                          <button
                            type="button"
                            onClick={clearNotifications}
                            className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-white transition hover:bg-white/10"
                          >
                            {t("app.notifications.clear")}
                          </button>
                          <button
                            type="button"
                            onClick={closeNotifications}
                            className="rounded-full border border-white/10 bg-white/5 p-2 text-gray-300 transition hover:bg-white/10 hover:text-white"
                            aria-label={t("common.close")}
                          >
                            <X size={16} />
                          </button>
                        </div>
                      </div>

                      <div
                        className="space-y-3 overflow-y-auto pr-1"
                        style={{
                          maxHeight: "calc(100vh - 212px)",
                          overscrollBehavior: "contain",
                        }}
                      >
                        {sortedNotifications.length === 0 ? (
                          <div className="rounded-3xl border border-dashed border-white/10 bg-white/5 p-6 text-center text-sm text-gray-400">
                            {t("app.notifications.empty")}
                          </div>
                        ) : (
                          sortedNotifications.map((notification) => (
                            <div
                              key={notification.id}
                              className="rounded-3xl border border-white/10 bg-white/5 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
                            >
                              <div className="flex items-start justify-between gap-4">
                                <div className="min-w-0">
                                  <p className="text-sm font-semibold text-white">
                                    {notification.detectionType}
                                  </p>
                                  <p className="mt-1 text-xs text-gray-400">
                                    {t("app.notifications.camera")}:{" "}
                                    {notification.cameraName}
                                  </p>
                                  <div className="mt-3 space-y-1 text-xs text-gray-400">
                                    <div>
                                      {
                                        formatNotificationDateTime(
                                          notification.time,
                                        ).dateLabel
                                      }
                                    </div>
                                    <div>
                                      {
                                        formatNotificationDateTime(
                                          notification.time,
                                        ).timeLabel
                                      }
                                    </div>
                                  </div>
                                </div>
                                <span
                                  className={`rounded-full border px-2 py-1 text-xs font-semibold ${getSeverityStyle(
                                    notification.severity,
                                  )}`}
                                >
                                  {notification.severity}
                                </span>
                              </div>

                              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-gray-400">
                                <span
                                  className={`inline-flex rounded-full px-2 py-1 text-[11px] uppercase tracking-[0.18em] ${
                                    notification.status === "Unread"
                                      ? "bg-white/10 text-white"
                                      : "bg-white/5 text-gray-400"
                                  }`}
                                >
                                  {notification.status}
                                </span>
                                <div className="flex flex-wrap items-center justify-end gap-2">
                                  <button
                                    type="button"
                                    onClick={() =>
                                      markNotificationAsRead(notification.id)
                                    }
                                    className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[11px] font-semibold text-white transition hover:bg-white/10"
                                  >
                                    <CheckCircle2 size={14} />
                                    {t("app.notifications.read")}
                                  </button>
                                  {notification.screenshot ? (
                                    <>
                                      <button
                                        onClick={async () => {
                                          if (notification.eventId) {
                                            setScreenshotModalEventId(
                                              notification.eventId,
                                            );
                                          } else if (notification.screenshot) {
                                            window.open(
                                              notification.screenshot as string,
                                              "_blank",
                                            );
                                          }
                                        }}
                                        className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[11px] font-semibold text-white transition hover:bg-white/10"
                                      >
                                        {t("app.notifications.view")}
                                      </button>
                                      <button
                                        onClick={async () => {
                                          try {
                                            if (notification.eventId) {
                                              const resp =
                                                await aiService.downloadScreenshot(
                                                  notification.eventId,
                                                );
                                              const blob = resp.data as Blob;
                                              const a =
                                                document.createElement("a");
                                              a.href =
                                                URL.createObjectURL(blob);
                                              const responseFilename =
                                                getFilenameFromContentDisposition(
                                                  resp.headers[
                                                    "content-disposition"
                                                  ],
                                                );
                                              a.download =
                                                responseFilename ||
                                                formatScreenshotFilename(
                                                  notification.cameraName ||
                                                    t("common.unknownCamera"),
                                                  notification.detectionType,
                                                  notification.time,
                                                );
                                              document.body.appendChild(a);
                                              a.click();
                                              a.remove();
                                            } else if (
                                              notification.screenshot
                                            ) {
                                              const a =
                                                document.createElement("a");
                                              a.href =
                                                notification.screenshot as string;
                                              a.download = `ai_event_${notification.id}.jpg`;
                                              a.click();
                                            }
                                          } catch (err) {
                                            console.error(err);
                                          }
                                        }}
                                        className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[11px] font-semibold text-white transition hover:bg-white/10"
                                      >
                                        {t("app.notifications.download")}
                                      </button>
                                    </>
                                  ) : null}
                                </div>
                              </div>

                              <div className="mt-4 h-20 w-full overflow-hidden rounded-md bg-white/5">
                                {notification.eventId && notification.screenshot ? (
                                  screenshotCache.has(notification.eventId) ? (
                                    <img
                                      src={screenshotCache.get(
                                        notification.eventId,
                                      )}
                                      alt="thumb"
                                      className="h-20 w-full object-cover"
                                    />
                                  ) : (
                                    <div
                                      onMouseEnter={() =>
                                        fetchAndCacheScreenshot(
                                          notification.eventId,
                                        )
                                      }
                                      className="flex h-20 w-full items-center justify-center rounded-md bg-white/5 text-xs text-gray-400"
                                    >
                                      Preview
                                    </div>
                                  )
                                ) : (
                                  <div className="flex h-20 w-full items-center justify-center rounded-md bg-white/5 text-xs text-gray-400">
                                    Preview
                                  </div>
                                )}
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>,
                    document.body,
                  )
                : null}
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto">
          {activePage === "dashboard" && (
            <Dashboard onAlertBadgeClick={() => setIsNotificationsOpen(true)} />
          )}
          {activePage === "cameras" && <Cameras />}
          {activePage === "reports" && <Analytics />}
          {activePage === "alerts" && <AlertHistory />}
          {activePage === "users" && <Users />}
          {activePage === "settings" && <Settings />}
        </main>
        {screenshotModalEventId && (
          <ScreenshotModal
            eventId={screenshotModalEventId}
            onClose={() => setScreenshotModalEventId(null)}
          />
        )}
      </div>
    </div>
  );

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            isAuthenticated ? (
              <Navigate to="/" replace />
            ) : (
              <Login onLoginSuccess={handleLogin} />
            )
          }
        />
        <Route
          path="/register"
          element={isAuthenticated ? <Navigate to="/" replace /> : <Register />}
        />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route
          path="/"
          element={
            isAuthenticated ? (
              authenticatedShell
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route
          path="*"
          element={<Navigate to={isAuthenticated ? "/" : "/login"} replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
