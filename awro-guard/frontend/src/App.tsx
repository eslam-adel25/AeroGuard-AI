import { useMemo, useState, useEffect, useRef } from "react";
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
import LanguageSwitcher from "./components/LanguageSwitcher";
import AlertHistory from "./pages/AlertHistory";
import ScreenshotModal from "./components/ScreenshotModal";
import { aiService } from "./services/api";
import {
  notificationService,
  type NotificationItem,
  type NotificationSeverity,
} from "./services/notificationService";

function App() {
  const { t } = useTranslation();
  const [activePage, setActivePage] = useState("dashboard");
  const [isAuthenticated, setIsAuthenticated] = useState(
    !!localStorage.getItem("ag_token"),
  );
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [screenshotModalEventId, setScreenshotModalEventId] = useState<
    string | null
  >(null);
  const [screenshotCache] = useState(() => new Map<string, string>());
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [currentTime, setCurrentTime] = useState(() => Date.now());
  const [panelPosition, setPanelPosition] = useState({ top: 0, left: 0 });

  const panelRef = useRef<HTMLDivElement>(null);
  const bellRef = useRef<HTMLButtonElement>(null);

  const unreadCount = notifications.filter(
    (item) => item.status === "Unread",
  ).length;

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
    let socket: WebSocket | null = null;

    const loadNotifications = async () => {
      const fetched = await notificationService.fetchNotifications();
      const sorted = [...fetched].sort(
        (a, b) => new Date(b.time).getTime() - new Date(a.time).getTime(),
      );
      setNotifications(sorted);
    };

    loadNotifications();

    socket = notificationService.subscribeToLiveAlerts((notification) => {
      setNotifications((prev) => [notification, ...prev]);
    });

    return () => {
      socket?.close();
    };
  }, []);

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
    const intervalId = window.setInterval(() => {
      setCurrentTime(Date.now());
    }, 60000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, []);

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

  const markNotificationAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((item) => (item.id === id ? { ...item, status: "Read" } : item)),
    );
  };

  const markAllAsRead = () => {
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

  const formatRelativeTime = (isoTime: string, referenceTime: number) => {
    const delta = referenceTime - new Date(isoTime).getTime();
    const minutes = Math.round(delta / 60000);
    if (minutes < 1) return "Just now";
    if (minutes === 1) return "1 minute ago";
    if (minutes < 60) return `${minutes} minutes ago`;
    return new Date(isoTime).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLogin} />;
  }

  return (
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
                      }}
                    >
                      <div className="flex items-center justify-between gap-3 pb-4">
                        <div>
                          <p className="text-xs uppercase tracking-[0.28em] text-gray-400">
                            {t("common.notifications")}
                          </p>
                          <h3 className="text-lg font-black text-white">
                            {notifications.length > 0
                              ? "Security Notifications"
                              : "No new alerts"}
                          </h3>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <button
                            type="button"
                            onClick={markAllAsRead}
                            className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-white transition hover:bg-white/10"
                          >
                            Mark all read
                          </button>
                          <button
                            type="button"
                            onClick={clearNotifications}
                            className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-white transition hover:bg-white/10"
                          >
                            Clear
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

                      <div className="space-y-3">
                        {notifications.length === 0 ? (
                          <div className="rounded-3xl border border-dashed border-white/10 bg-white/5 p-6 text-center text-sm text-gray-400">
                            No notifications available yet.
                          </div>
                        ) : (
                          notifications.map((notification) => (
                            <div
                              key={notification.id}
                              className="rounded-3xl border border-white/10 bg-white/5 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
                            >
                              <div className="flex items-start justify-between gap-4">
                                <div className="min-w-0">
                                  <p className="text-sm font-semibold text-white">
                                    {notification.detectionType}
                                  </p>
                                  <p className="text-xs text-gray-400">
                                    Camera: {notification.cameraName}
                                  </p>
                                </div>
                                <span
                                  className={`rounded-full border px-2 py-1 text-xs font-semibold ${getSeverityStyle(
                                    notification.severity,
                                  )}`}
                                >
                                  {notification.severity}
                                </span>
                              </div>

                              <div className="mt-4 flex items-center justify-between gap-3 text-sm text-gray-400">
                                <p>
                                  {formatRelativeTime(
                                    notification.time,
                                    currentTime,
                                  )}
                                </p>
                                <div className="flex items-center gap-2">
                                  <span
                                    className={`rounded-full px-2 py-1 text-[11px] uppercase tracking-[0.18em] ${
                                      notification.status === "Unread"
                                        ? "bg-white/10 text-white"
                                        : "bg-white/5 text-gray-400"
                                    }`}
                                  >
                                    {notification.status}
                                  </span>
                                  <button
                                    type="button"
                                    onClick={() =>
                                      markNotificationAsRead(notification.id)
                                    }
                                    className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[11px] font-semibold text-white transition hover:bg-white/10"
                                  >
                                    <CheckCircle2 size={14} />
                                    Read
                                  </button>
                                  {notification.eventId ||
                                  notification.screenshot ? (
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
                                        View
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
                                              a.download = `ai_event_${notification.eventId}.jpg`;
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
                                        Download
                                      </button>
                                    </>
                                  ) : null}
                                </div>
                              </div>
                              {notification.eventId ? (
                                <div className="mt-3">
                                  {screenshotCache.has(notification.eventId) ? (
                                    <img
                                      src={screenshotCache.get(
                                        notification.eventId,
                                      )}
                                      alt="thumb"
                                      className="h-20 w-28 rounded-md object-cover"
                                    />
                                  ) : (
                                    <div
                                      onMouseEnter={() =>
                                        fetchAndCacheScreenshot(
                                          notification.eventId,
                                        )
                                      }
                                      className="flex h-20 w-28 items-center justify-center rounded-md bg-white/5 text-xs text-gray-400"
                                    >
                                      Preview
                                    </div>
                                  )}
                                </div>
                              ) : null}
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
          {activePage === "dashboard" && <Dashboard />}
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
}

export default App;
