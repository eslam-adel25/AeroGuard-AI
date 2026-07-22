import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  LayoutDashboard,
  Video,
  FileText,
  Settings,
  Shield,
  User,
  LogOut,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

interface SidebarProps {
  activePage: string;
  setActivePage: (page: string) => void;
  onLogout: () => void;
}

const Sidebar = ({ activePage, setActivePage, onLogout }: SidebarProps) => {
  const { t } = useTranslation();
  const [isCollapsed, setIsCollapsed] = useState(() => {
    return localStorage.getItem("sidebar_state") === "collapsed";
  });

  useEffect(() => {
    localStorage.setItem(
      "sidebar_state",
      isCollapsed ? "collapsed" : "expanded",
    );
  }, [isCollapsed]);

  const menuItems = [
    { id: "dashboard", label: t("sidebar.monitoring"), icon: LayoutDashboard },
    { id: "cameras", label: t("sidebar.cameras"), icon: Video },
    { id: "reports", label: t("sidebar.analytics"), icon: FileText },
    { id: "users", label: t("sidebar.profile"), icon: User },
    { id: "settings", label: t("sidebar.control"), icon: Settings },
  ];

  return (
    <aside
      className={`bg-ag-card/95 backdrop-blur-xl border-r border-white/6 flex flex-col h-screen sticky top-0 transition-all duration-300 ease-out shadow-xl z-[100]
      ${isCollapsed ? "w-20" : "w-72"}`}
    >
      {/* Collapse Toggle Button */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3 top-16 bg-ag-danger text-white rounded-full p-1.5 border-4 border-ag-dark shadow-md hover:scale-105 transition-transform"
        aria-label={isCollapsed ? t("sidebar.expand") : t("sidebar.collapse")}
      >
        {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>

      <div
        className={`px-4 py-4 flex items-center gap-3 border-b border-white/6 mb-4 ${isCollapsed ? "justify-center" : ""}`}
      >
        <div className="bg-ag-danger p-2 rounded-xl shadow-md">
          <Shield className="text-white" size={20} />
        </div>
        {!isCollapsed && (
          <span className="font-black text-lg tracking-tight text-white uppercase">
            AeroGuard
          </span>
        )}
      </div>

      <nav className="flex-1 px-2 py-2 space-y-2">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActivePage(item.id)}
            title={isCollapsed ? item.label : undefined}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group border
            ${
              activePage === item.id
                ? "bg-ag-danger text-white shadow-md border-ag-danger/60"
                : "text-gray-400 hover:bg-white/5 hover:text-gray-200 border-transparent hover:border-white/6"
            }`}
          >
            <item.icon
              size={18}
              className={
                activePage === item.id
                  ? "text-white"
                  : "group-hover:text-ag-danger transition-colors"
              }
            />
            {!isCollapsed && (
              <span className="font-semibold text-[12px] tracking-[0.18em]">
                {item.label}
              </span>
            )}
          </button>
        ))}
      </nav>

      <div className="p-3">
        <button
          onClick={onLogout}
          title={isCollapsed ? t("sidebar.logout") : undefined}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-ag-danger bg-ag-danger/6 hover:bg-ag-danger hover:text-white font-bold border border-transparent hover:border-ag-danger/30
            ${isCollapsed ? "justify-center" : ""}`}
        >
          <LogOut size={18} />
          {!isCollapsed && (
            <span className="text-[11px] tracking-[0.18em] uppercase">
              {t("sidebar.logout")}
            </span>
          )}
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
