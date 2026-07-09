import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./translations/en";
import ar from "./translations/ar";

const storedLanguage = localStorage.getItem("ag_language") || "en";

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    ar: { translation: ar },
  },
  lng: storedLanguage,
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
