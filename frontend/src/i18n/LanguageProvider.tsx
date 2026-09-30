import { useEffect, type ReactNode } from "react";
import { I18nextProvider } from "react-i18next";
import i18n from ".";

interface LanguageProviderProps {
  children: ReactNode;
}

const LanguageProvider = ({ children }: LanguageProviderProps) => {
  useEffect(() => {
    const savedLanguage = localStorage.getItem("ag_language") || "en";
    i18n.changeLanguage(savedLanguage);
    document.documentElement.dir = "ltr";
    document.documentElement.lang = savedLanguage;
  }, []);

  return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>;
};

export default LanguageProvider;
