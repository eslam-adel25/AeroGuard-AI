import { useMemo, useState } from "react";
import { Bell } from "lucide-react";
import { useTranslation } from "react-i18next";

import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Cameras from "./pages/Cameras";
import Analytics from "./pages/Analytics";
import Users from "./pages/Profile";
import Settings from "./pages/Settings";
import Login from "./pages/Login";
import LanguageSwitcher from "./components/LanguageSwitcher";

function App() {
  const { t } = useTranslation();
  const [activePage, setActivePage] = useState("dashboard");
  const [isAuthenticated, setIsAuthenticated] = useState(
    !!localStorage.getItem("ag_token"),
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
  };

  const handleLogout = () => {
    localStorage.removeItem("ag_token");
    setIsAuthenticated(false);
    setActivePage("dashboard");
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

          <div className="flex items-center gap-3">
            <LanguageSwitcher />
            <button
              type="button"
              className="rounded-full border border-white/10 bg-white/10 p-2.5 text-gray-300 transition-all hover:bg-white/20 hover:text-white"
              aria-label={t("common.notifications")}
            >
              <Bell size={18} />
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto">
          {activePage === "dashboard" && <Dashboard />}
          {activePage === "cameras" && <Cameras />}
          {activePage === "reports" && <Analytics />}
          {activePage === "users" && <Users />}
          {activePage === "settings" && <Settings />}
        </main>
      </div>
    </div>
  );
}

export default App;
