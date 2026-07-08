import { useState } from "react";

import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Cameras from "./pages/Cameras";
import Analytics from "./pages/Analytics";

import Users from "./pages/Profile";
import Settings from "./pages/Settings";
import Login from "./pages/Login";

function App() {
  const [activePage, setActivePage] = useState("dashboard");

  const [isAuthenticated, setIsAuthenticated] = useState(
    !!localStorage.getItem("ag_token"),
  );

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

      <main className="flex-1 overflow-y-auto">
        {activePage === "dashboard" && <Dashboard />}
        {activePage === "cameras" && <Cameras />}
        {activePage === "reports" && <Analytics />}
        {activePage === "users" && <Users />}
        {activePage === "settings" && <Settings />}
      </main>
    </div>
  );
}

export default App;
