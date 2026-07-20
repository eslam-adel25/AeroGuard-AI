import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import LanguageProvider from "./i18n/LanguageProvider";
import { NotificationProvider } from "./components/NotificationSystem";
import "./i18n";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <LanguageProvider>
      <NotificationProvider>
        <App />
      </NotificationProvider>
    </LanguageProvider>
  </React.StrictMode>,
);
