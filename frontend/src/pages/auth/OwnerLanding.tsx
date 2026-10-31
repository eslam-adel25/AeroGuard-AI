import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  Menu,
  Shield,
  UsersRound,
  X,
} from "lucide-react";
import LanguageSwitcher from "../../components/LanguageSwitcher";

interface OwnerLandingProps {
  onLogout: () => void;
}

const navigation = [
  { to: "/owner/requests/unread", label: "owner.navigation.unread", icon: LayoutDashboard },
  { to: "/owner/requests/under-review", label: "owner.navigation.underReview", icon: ClipboardList },
  { to: "/owner/customers", label: "owner.navigation.customers", icon: UsersRound },
];

const OWNER_SIDEBAR_STORAGE_KEY = "aeroguard_owner_sidebar_state";

const OwnerLanding = ({ onLogout }: OwnerLandingProps) => {
  const { t } = useTranslation();
  const [isCollapsed, setIsCollapsed] = useState(
    () => localStorage.getItem(OWNER_SIDEBAR_STORAGE_KEY) === "collapsed",
  );
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem(
      OWNER_SIDEBAR_STORAGE_KEY,
      isCollapsed ? "collapsed" : "expanded",
    );
  }, [isCollapsed]);

  useEffect(() => {
    if (!isMobileOpen) return;

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsMobileOpen(false);
    };

    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [isMobileOpen]);

  return (
    <div className="flex min-h-screen w-full overflow-x-clip bg-[#0c0e12] text-white">
      {isMobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-black/60 md:hidden"
          aria-label={t("owner.navigation.close")}
          onClick={() => setIsMobileOpen(false)}
        />
      )}
      <aside
        id="owner-sidebar"
        className={`fixed inset-y-0 left-0 z-50 flex h-full w-64 shrink-0 flex-col border-r border-white/10 bg-[#111419] p-5 transition-transform duration-200 ease-in-out md:sticky md:top-0 md:h-screen md:translate-x-0 md:transition-[width] md:duration-200 ${
          isMobileOpen ? "translate-x-0" : "-translate-x-full invisible md:visible"
        } ${isCollapsed ? "md:w-[72px] md:p-3" : "md:w-64"}`}
      >
        <div
          className={`flex items-center gap-3 px-2 py-4 ${
            isCollapsed ? "md:flex-col md:px-0" : ""
          }`}
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#adc6ff]/10 text-[#adc6ff]">
            <Shield size={22} />
          </div>
          <div className={isCollapsed ? "md:hidden" : ""}>
            <p className="font-semibold">AeroGuard AI</p>
            <p className="text-xs text-gray-500">{t("owner.header")}</p>
          </div>
          <button
            type="button"
            onClick={() => setIsCollapsed((collapsed) => !collapsed)}
            className={`ml-auto hidden h-10 w-10 shrink-0 items-center justify-center rounded-xl text-gray-400 transition hover:bg-white/5 hover:text-white md:flex ${
              isCollapsed ? "md:ml-0" : ""
            }`}
            aria-label={t(
              isCollapsed ? "owner.navigation.expand" : "owner.navigation.collapse",
            )}
            aria-expanded={!isCollapsed}
            title={t(
              isCollapsed
                ? "owner.navigation.expandTitle"
                : "owner.navigation.collapseTitle",
            )}
          >
            {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
          <button
            type="button"
            onClick={() => setIsMobileOpen(false)}
            className="ml-auto flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-gray-400 transition hover:bg-white/5 hover:text-white md:hidden"
            aria-label={t("owner.navigation.close")}
            title={t("common.close")}
          >
            <X size={18} />
          </button>
        </div>
        <nav className="mt-8 space-y-2" aria-label={t("owner.navigation.label")}>
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setIsMobileOpen(false)}
              aria-label={t(item.label)}
              title={isCollapsed ? t(item.label) : undefined}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-4 py-3 text-sm transition ${
                  isCollapsed ? "md:justify-center md:px-0" : ""
                } ${
                  isActive
                    ? "bg-[#adc6ff]/10 font-semibold text-[#adc6ff]"
                    : "text-gray-400 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <item.icon
                size={18}
                aria-hidden="true"
                className={`shrink-0 ${isCollapsed ? "" : "md:hidden"}`}
              />
              <span className={isCollapsed ? "md:hidden" : ""}>{t(item.label)}</span>
            </NavLink>
          ))}
        </nav>
        <button
          type="button"
          onClick={onLogout}
          title={isCollapsed ? t("owner.navigation.logout") : undefined}
          aria-label={t("owner.navigation.logout")}
          className={`mt-auto flex items-center gap-3 rounded-xl px-4 py-3 text-sm text-gray-400 hover:bg-white/5 hover:text-white ${
            isCollapsed ? "md:justify-center md:px-0" : ""
          }`}
        >
          <LogOut size={17} aria-hidden="true" className="shrink-0" />
          <span className={isCollapsed ? "md:hidden" : ""}>
            {t("owner.navigation.logout")}
          </span>
        </button>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-white/10 px-5 py-4 md:px-8">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setIsMobileOpen(true)}
              className="flex h-10 w-10 items-center justify-center rounded-lg text-gray-300 transition hover:bg-white/5 hover:text-white md:hidden"
              aria-label={t("owner.navigation.open")}
              aria-controls="owner-sidebar"
              aria-expanded={isMobileOpen}
              title={t("owner.navigation.open")}
            >
              <Menu size={20} />
            </button>
            <LayoutDashboard size={20} className="text-[#adc6ff] md:hidden" />
            <span className="font-semibold md:hidden">{t("owner.header")}</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="hidden text-sm text-gray-400 md:block">
              {t("owner.customerAdministration")}
            </div>
            <LanguageSwitcher />
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-5 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default OwnerLanding;
