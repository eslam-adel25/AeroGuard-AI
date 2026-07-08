import { useState, useEffect } from "react";
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
  // تذكر حالة القائمة (Section 8)
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
    { id: "dashboard", label: "Monitoring", icon: LayoutDashboard },
    { id: "cameras", label: "Cameras", icon: Video },
    { id: "reports", label: "Analytics", icon: FileText },
    { id: "users", label: "Profile", icon: User },
    { id: "settings", label: "Control", icon: Settings },
  ];

  return (
    <aside
      className={`bg-ag-card/95 backdrop-blur-xl border-r border-white/5 flex flex-col h-screen sticky top-0 transition-all duration-300 ease-out shadow-2xl z-[100]
      ${isCollapsed ? "w-22" : "w-72"}`}
    >
      {/* Collapse Toggle Button */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3 top-16 bg-ag-danger text-white rounded-full p-1.5 border-4 border-ag-dark shadow-xl hover:scale-110 transition-all"
      >
        {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>

      <div
        className={`px-5 py-5 flex items-center gap-3 border-b border-white/5 mb-4 ${isCollapsed ? "justify-center" : ""}`}
      >
        <div className="bg-ag-danger p-2.5 rounded-2xl shadow-lg shadow-red-900/20">
          <Shield className="text-white" size={24} />
        </div>
        {!isCollapsed && (
          <span className="font-black text-xl tracking-tight text-white uppercase">
            AeroGuard
          </span>
        )}
      </div>

      <nav className="flex-1 px-3 py-2 space-y-1.5">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActivePage(item.id)}
            className={`w-full flex items-center gap-4 px-4 py-3.5 rounded-2xl transition-all duration-200 group border
            ${
              activePage === item.id
                ? "bg-ag-danger text-white shadow-xl shadow-red-900/25 border-ag-danger/70"
                : "text-gray-500 hover:bg-white/5 hover:text-gray-200 border-transparent hover:border-white/5"
            }`}
          >
            <item.icon
              size={20}
              className={
                activePage === item.id
                  ? "text-white"
                  : "group-hover:text-ag-danger transition-colors"
              }
            />
            {!isCollapsed && (
              <span className="font-bold text-[12px] uppercase tracking-[0.22em]">
                {item.label}
              </span>
            )}
          </button>
        ))}
      </nav>

      <div className="p-3">
        <button
          onClick={onLogout}
          className={`w-full flex items-center gap-4 px-4 py-3.5 rounded-2xl transition-all duration-200 text-ag-danger bg-ag-danger/5 hover:bg-ag-danger hover:text-white font-black border border-transparent hover:border-ag-danger/30
            ${isCollapsed ? "justify-center" : ""}`}
        >
          <LogOut size={20} />
          {!isCollapsed && (
            <span className="text-[11px] tracking-[0.22em] uppercase">Logout</span>
          )}
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
