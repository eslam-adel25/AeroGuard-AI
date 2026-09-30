import { useTranslation } from "react-i18next";
import { Globe } from "lucide-react";

const LanguageSwitcher = () => {
  const { i18n } = useTranslation();

  const toggleLanguage = () => {
    const nextLanguage = i18n.language === "ar" ? "en" : "ar";
    i18n.changeLanguage(nextLanguage);
    localStorage.setItem("ag_language", nextLanguage);
    document.documentElement.dir = "ltr";
    document.documentElement.lang = nextLanguage;
  };

  return (
    <button
      type="button"
      onClick={toggleLanguage}
      className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-2 text-sm font-semibold text-white shadow-lg shadow-black/20 transition-all duration-200 hover:-translate-y-0.5 hover:bg-white/20"
      aria-label="Toggle language"
    >
      <Globe size={16} className="text-ag-danger" />
      <span className="tracking-[0.24em]">
        {i18n.language === "ar" ? "AR" : "EN"}
      </span>
    </button>
  );
};

export default LanguageSwitcher;
