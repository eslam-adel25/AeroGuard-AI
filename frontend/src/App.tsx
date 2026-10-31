import { useMemo, useState, useEffect, useRef, useCallback } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { createPortal } from "react-dom";
import { Bell, X, CheckCircle2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import Sidebar, { type ActivePage } from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Cameras from "./pages/Cameras";
import Analytics from "./pages/Analytics";
import Users from "./pages/Profile";
import Settings from "./pages/Settings";
import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";
import VerifyEmail from "./pages/auth/VerifyEmail";
import PrivacyPolicy from "./pages/public/PrivacyPolicy";
import TermsOfService from "./pages/public/TermsOfService";
import Documentation from "./pages/public/Documentation";
import Support from "./pages/public/Support";
import Contact from "./pages/public/Contact";
import ActivationPending from "./pages/auth/ActivationPending";
import InactiveAccount from "./pages/auth/InactiveAccount";
import OwnerLanding from "./pages/auth/OwnerLanding";
import CustomerList from "./pages/owner/CustomerList";
import CustomerDetails from "./pages/owner/CustomerDetails";
import LanguageSwitcher from "./components/LanguageSwitcher";
import AlertHistory from "./pages/AlertHistory";
import ScreenshotModal from "./components/ScreenshotModal";
import { AlertAudioProvider } from "./components/AlertAudioProvider";
import {
  aiService,
  cameraService,
  formatScreenshotFilename,
  getFilenameFromContentDisposition,
  getStoredAuthToken,
  authService,
  clearAuthState,
  persistAuthState,
  type AuthState,
} from "./services/api";
import { closeActiveSocket } from "./services/socket";
import {
  notificationService,
  type NotificationItem,
  type NotificationSeverity,
} from "./services/notificationService";

const ACTIVE_PAGE_IDS = [
  "dashboard",
  "cameras",
  "reports",
  "alerts",
  "users",
  "settings",
] as const satisfies readonly ActivePage[];
const PAGE_FEATURES: Partial<Record<ActivePage, string[]>> = {
  dashboard: ["dashboard", "cameras"],
  cameras: ["cameras"],
  reports: ["analytics"],
  alerts: ["alerts"],
  settings: ["settings"],
};

const isActivePage = (page: string): page is ActivePage =>
  ACTIVE_PAGE_IDS.some((validPage) => validPage === page);

const getStoredActivePage = (): ActivePage | null => {
  const savedPage = localStorage.getItem("ag_active_page");

  if (!savedPage || !isActivePage(savedPage)) {
    return null;
  }

  return savedPage;
};

function App() {
  const { t, i18n } = useTranslation();
  const [activePage, setActivePage] = useState<ActivePage>(() => {
    if (!getStoredAuthToken()) {
      return "dashboard";
    }

    return getStoredActivePage() ?? "reports";
  });
  const [authState, setAuthState] = useState<AuthState | null>(null);
  const currentUserIdRef = useRef<string | null>(null);
  currentUserIdRef.current = authState?.user_id ?? null;
  const [isResolvingAuth, setIsResolvingAuth] = useState(
    () => !!getStoredAuthToken(),
  );
  const isAuthenticated = !!authState && !!getStoredAuthToken();
  const isActiveCustomer =
    isAuthenticated &&
    authState?.account_status === "ACTIVE" &&
    authState.workflow_status === "PLATFORM_CUSTOMER" &&
    !authState.is_owner;
  const isPendingCustomer =
    isAuthenticated &&
    !authState?.is_owner &&
    (authState?.account_status === "PENDING" ||
      authState?.workflow_status !== "PLATFORM_CUSTOMER");
  const canAccessCameras =
    authState?.enabled_features?.includes("cameras") ?? true;
  const canAccessAlerts =
    authState?.enabled_features?.includes("alerts") ?? true;
  const canAccessSettings =
    authState?.enabled_features?.includes("settings") ?? true;
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadNotificationCount, setUnreadNotificationCount] = useState(0);
  const knownNotificationIdsRef = useRef(new Set<string>());
  const liveNotificationIdsRef = useRef(new Set<string>());
  const [cameraMap, setCameraMap] = useState<Record<string, string>>({});
  const [screenshotModalEventId, setScreenshotModalEventId] = useState<
    string | null
  >(null);
  const [screenshotCache] = useState(() => new Map<string, string>());
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [panelPosition, setPanelPosition] = useState({ top: 0, left: 0 });

  const panelRef = useRef<HTMLDivElement>(null);
  const bellRef = useRef<HTMLButtonElement>(null);

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

  const clearCustomerPresentationState = useCallback(() => {
    setNotifications([]);
    setUnreadNotificationCount(0);
    knownNotificationIdsRef.current.clear();
    liveNotificationIdsRef.current.clear();
    setCameraMap({});
    setScreenshotModalEventId(null);
    setIsNotificationsOpen(false);
    screenshotCache.forEach((url) => {
      if (url.startsWith("blob:")) URL.revokeObjectURL(url);
    });
    screenshotCache.clear();
  }, [screenshotCache]);

  const handleLogin = (token: string, user: AuthState) => {
    closeActiveSocket();
    clearCustomerPresentationState();
    localStorage.setItem("ag_token", token);
    persistAuthState(user);
    localStorage.removeItem("ag_active_page");
    setAuthState(user);
    setIsResolvingAuth(false);
    setActivePage("reports");
  };

  useEffect(() => {
    const token = getStoredAuthToken();
    if (!token) {
      setIsResolvingAuth(false);
      setAuthState(null);
      return;
    }

    let active = true;
    authService
      .getMe()
      .then(({ data }) => {
        if (active) {
          setAuthState(data);
          persistAuthState(data);
        }
      })
      .catch(() => {
        if (active) {
          closeActiveSocket();
          clearAuthState();
          clearCustomerPresentationState();
          setAuthState(null);
        }
      })
      .finally(() => {
        if (active) setIsResolvingAuth(false);
      });

    return () => {
      active = false;
    };
  }, [clearCustomerPresentationState]);

  const authenticatedDestination = () => {
    if (authState?.is_owner || authState?.role === "Owner") return "/owner";
    if (authState?.account_status === "INACTIVE") return "/account-inactive";
    if (isPendingCustomer) return "/activation-pending";
    return "/";
  };

  useEffect(() => {
    if (!isAuthenticated) {
      localStorage.removeItem("ag_active_page");
      return;
    }

    localStorage.setItem("ag_active_page", activePage);
  }, [activePage, isAuthenticated]);

  useEffect(() => {
    if (!isActiveCustomer || !authState?.enabled_features) return;
    const requiredFeatures = PAGE_FEATURES[activePage];
    if (
      requiredFeatures &&
      requiredFeatures.some(
        (feature) => !authState.enabled_features?.includes(feature),
      )
    ) {
      setActivePage("users");
    }
  }, [activePage, authState?.enabled_features, isActiveCustomer]);

  // Load user-specific settings after login
  useEffect(() => {
    let active = true;
    const loadSettings = async () => {
      try {
        const mod = await import("./services/api");
        const res = await mod.settingsService.get();
        if (active && res?.data) {
          localStorage.setItem("ag_settings", JSON.stringify(res.data));
        }
      } catch (err) {
        console.warn("Failed to load user settings after login", err);
      }
    };

    if (isActiveCustomer && canAccessSettings) {
      loadSettings();
    }
    return () => {
      active = false;
    };
  }, [isActiveCustomer, canAccessSettings, authState?.user_id]);

  const handleLogout = async () => {
    closeActiveSocket();
    if (isActiveCustomer) {
      try {
        const response = await cameraService.getAll();
        if (Array.isArray(response.data)) {
          const activeCameras = (
            response.data as Array<{ camera_id: string; status?: string }>
          ).filter((camera) =>
            ["Processing", "Running"].includes(camera.status ?? ""),
          );
          await Promise.allSettled(
            activeCameras.map((camera) => cameraService.stop(camera.camera_id)),
          );
        }
      } catch (error) {
        console.warn("Failed to stop active cameras during logout", error);
      }
    }

    clearAuthState();
    clearCustomerPresentationState();
    setAuthState(null);
    setIsResolvingAuth(false);
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
    setNotifications([]);
    setUnreadNotificationCount(0);
    knownNotificationIdsRef.current.clear();
    liveNotificationIdsRef.current.clear();
    setCameraMap({});
    setScreenshotModalEventId(null);
    setIsNotificationsOpen(false);
    screenshotCache.forEach((url) => {
      if (url.startsWith("blob:")) URL.revokeObjectURL(url);
    });
    screenshotCache.clear();
  }, [authState?.user_id, screenshotCache]);

  useEffect(() => {
    if (!isActiveCustomer || !canAccessAlerts) {
      setNotifications([]);
      setUnreadNotificationCount(0);
      knownNotificationIdsRef.current.clear();
      liveNotificationIdsRef.current.clear();
      return;
    }

    const token = getStoredAuthToken();
    if (!token) {
      return;
    }

    let socketHandle: { close: () => void } | null = null;
    let active = true;

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

    const mergeNotification = (
      existing: NotificationItem,
      incoming: NotificationItem,
    ): NotificationItem => ({
      ...existing,
      ...incoming,
      eventId: incoming.eventId ?? existing.eventId,
      status: existing.status === "Read" ? "Read" : incoming.status,
      screenshot: incoming.screenshot ?? existing.screenshot ?? null,
    });

    const loadNotifications = async () => {
      try {
        const fetched = await notificationService.fetchNotifications();
        if (!active) return;
        const hydrated = fetched.items.map(hydrateNotification);
        const fetchedIds = new Set(hydrated.map((item) => item.id));
        hydrated.forEach((item) => knownNotificationIdsRef.current.add(item.id));
        const liveOnlyCount = [...liveNotificationIdsRef.current].filter(
          (id) => !fetchedIds.has(id),
        ).length;
        setUnreadNotificationCount(fetched.unreadCount + liveOnlyCount);
        const sorted = [...hydrated].sort(
          (a, b) => new Date(b.time).getTime() - new Date(a.time).getTime(),
        );
        setNotifications((prev) => {
          const byId = new Map(prev.map((item) => [item.id, item]));
          sorted.forEach((item) => {
            const existing = byId.get(item.id);
            byId.set(
              item.id,
              existing ? mergeNotification(existing, item) : item,
            );
          });
          return [...byId.values()].sort(
            (a, b) => new Date(b.time).getTime() - new Date(a.time).getTime(),
          );
        });
      } catch (error) {
        if (active) console.error("Could not load customer notifications", error);
      }
    };

    loadNotifications();

    socketHandle = notificationService.subscribeToLiveAlerts((notification) => {
      if (!active) return;
      const hydrated = hydrateNotification(notification);
      const alreadyTracked =
        knownNotificationIdsRef.current.has(hydrated.id) ||
        liveNotificationIdsRef.current.has(hydrated.id);
      liveNotificationIdsRef.current.add(hydrated.id);
      if (!alreadyTracked && hydrated.status === "Unread") {
        setUnreadNotificationCount((count) => count + 1);
      }
      setNotifications((prev) => {
        if (prev.some((item) => item.id === hydrated.id)) {
          return prev.map((item) =>
            item.id === hydrated.id ? mergeNotification(item, hydrated) : item,
          );
        }
        return [hydrated, ...prev];
      });
    });

    return () => {
      active = false;
      socketHandle?.close();
    };
  }, [isActiveCustomer, canAccessAlerts, cameraMap, authState?.user_id]);

  const fetchAndCacheScreenshot = async (eventId?: string | null) => {
    if (!eventId) return null;
    if (screenshotCache.has(eventId))
      return screenshotCache.get(eventId) as string;
    const requestingUserId = currentUserIdRef.current;
    try {
      const resp = await aiService.downloadScreenshot(eventId);
      const blob = resp.data as Blob;
      const url = URL.createObjectURL(blob);
      if (!requestingUserId || currentUserIdRef.current !== requestingUserId) {
        URL.revokeObjectURL(url);
        return null;
      }
      screenshotCache.set(eventId, url);
      return url;
    } catch (err) {
      console.error("Failed to fetch screenshot", err);
      return null;
    }
  };

  useEffect(() => {
    let active = true;
    setCameraMap({});
    if (!isActiveCustomer || !canAccessCameras) {
      return () => {
        active = false;
      };
    }

    const loadCameras = async () => {
      try {
        const res = await cameraService.getAll();
        if (active && Array.isArray(res.data)) {
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
    return () => {
      active = false;
    };
  }, [isActiveCustomer, canAccessCameras, authState?.user_id]);

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
    if (notification?.status === "Unread") {
      liveNotificationIdsRef.current.delete(notification.id);
      setUnreadNotificationCount((count) => Math.max(0, count - 1));
    }
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
    setUnreadNotificationCount(0);
    liveNotificationIdsRef.current.clear();
  };

  const clearNotifications = () => {
    setNotifications([]);
    setUnreadNotificationCount(0);
  };

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

  const getSeverityLabel = (severity: NotificationSeverity) => {
    switch (severity) {
      case "Critical":
        return t("analytics.severity.critical");
      case "High":
        return t("analytics.severity.high");
      case "Medium":
        return t("analytics.severity.medium");
      case "Low":
        return t("analytics.severity.low");
      case "Normal":
        return t("analytics.severity.normal");
      default:
        return severity;
    }
  };

  const getNotificationStatusLabel = (status: string) => {
    if (status === "Read") return t("common.read");
    if (status === "Unread") return t("common.unread");
    return status;
  };

  const formatNotificationDateTime = (isoTime: string) => {
    const date = new Date(isoTime);
    if (Number.isNaN(date.getTime())) {
      return { dateLabel: isoTime, timeLabel: "" };
    }

    return {
      dateLabel: date.toLocaleDateString(i18n.language, {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }),
      timeLabel: date.toLocaleTimeString(i18n.language, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true,
      }),
    };
  };

  const authenticatedShellContent = (
    <div className="flex min-h-screen bg-ag-dark text-ag-primary">
      <Sidebar
        activePage={activePage}
        setActivePage={setActivePage}
        onLogout={handleLogout}
        enabledFeatures={authState?.enabled_features}
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

            {canAccessAlerts && (
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
                {unreadNotificationCount > 0 && (
                  <span className="absolute -right-1 -top-1 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-red-500 px-1.5 text-[11px] font-semibold text-white">
                    {unreadNotificationCount}
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
                                  {getSeverityLabel(notification.severity)}
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
                                  {getNotificationStatusLabel(
                                    notification.status,
                                  )}
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
                                {notification.eventId &&
                                notification.screenshot ? (
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
                                      {t("app.notifications.preview")}
                                    </div>
                                  )
                                ) : (
                                  <div className="flex h-20 w-full items-center justify-center rounded-md bg-white/5 text-xs text-gray-400">
                                    {t("app.notifications.preview")}
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
            )}
          </div>
        </header>

        <main className="flex-1 overflow-y-auto">
          {activePage === "dashboard" && (
            <Dashboard
              onAlertBadgeClick={
                canAccessAlerts
                  ? () => setIsNotificationsOpen(true)
                  : undefined
              }
            />
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
  const authenticatedShell = (
    <AlertAudioProvider>{authenticatedShellContent}</AlertAudioProvider>
  );
  const authLoading = (
    <main className="flex min-h-screen items-center justify-center bg-[#0c0e12] text-sm text-gray-300">
      Checking account access…
    </main>
  );

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            isResolvingAuth ? (
              authLoading
            ) : isAuthenticated ? (
              <Navigate to={authenticatedDestination()} replace />
            ) : (
              <Login onLoginSuccess={handleLogin} />
            )
          }
        />
        <Route
          path="/register"
          element={
            isResolvingAuth ? (
              authLoading
            ) : isAuthenticated ? (
              <Navigate to={authenticatedDestination()} replace />
            ) : (
              <Register />
            )
          }
        />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route
          path="/activation-pending"
          element={
            isResolvingAuth ? (
              authLoading
            ) : isPendingCustomer ? (
              <ActivationPending onLogout={handleLogout} />
            ) : (
              <Navigate to={isAuthenticated ? authenticatedDestination() : "/login"} replace />
            )
          }
        />
        <Route
          path="/account-inactive"
          element={
            isResolvingAuth ? (
              authLoading
            ) : isAuthenticated &&
              authState?.account_status === "INACTIVE" ? (
              <InactiveAccount onLogout={handleLogout} />
            ) : (
              <Navigate to={isAuthenticated ? authenticatedDestination() : "/login"} replace />
            )
          }
        />
        <Route
          path="/owner"
          element={
            isResolvingAuth ? (
              authLoading
            ) : isAuthenticated &&
              (authState?.is_owner || authState?.role === "Owner") ? (
              <OwnerLanding onLogout={handleLogout} />
            ) : (
              <Navigate to={isAuthenticated ? authenticatedDestination() : "/login"} replace />
            )
          }
        >
          <Route index element={<Navigate to="requests/unread" replace />} />
          <Route
            path="requests/unread"
            element={<CustomerList queue="unread" />}
          />
          <Route
            path="requests/under-review"
            element={<CustomerList queue="under-review" />}
          />
          <Route path="customers" element={<CustomerList queue="customers" />} />
          <Route
            path="customers/:customerProfileId"
            element={<CustomerDetails />}
          />
        </Route>
        <Route path="/privacy-policy" element={<PrivacyPolicy />} />
        <Route path="/terms-of-service" element={<TermsOfService />} />
        <Route path="/docs" element={<Documentation />} />
        <Route path="/support" element={<Support />} />
        <Route path="/contact" element={<Contact />} />
        <Route
          path="/"
          element={
            isResolvingAuth ? (
              authLoading
            ) : isActiveCustomer ? (
              authenticatedShell
            ) : isAuthenticated ? (
              <Navigate to={authenticatedDestination()} replace />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route
          path="*"
          element={
            isResolvingAuth ? (
              authLoading
            ) : (
              <Navigate
                to={isAuthenticated ? authenticatedDestination() : "/login"}
                replace
              />
            )
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
