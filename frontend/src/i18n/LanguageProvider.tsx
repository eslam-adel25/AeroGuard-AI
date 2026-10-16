import { useEffect, type ReactNode } from "react";
import { I18nextProvider } from "react-i18next";
import i18n from ".";

interface LanguageProviderProps {
  children: ReactNode;
}

const LanguageProvider = ({ children }: LanguageProviderProps) => {
  useEffect(() => {
    const savedLanguage = localStorage.getItem("ag_language") || "en";
    const updateDocumentLanguage = (language: string) => {
      document.documentElement.dir = "ltr";
      document.documentElement.lang = language;
    };

    i18n.on("languageChanged", updateDocumentLanguage);
    updateDocumentLanguage(savedLanguage);
    void i18n.changeLanguage(savedLanguage);

    return () => {
      i18n.off("languageChanged", updateDocumentLanguage);
    };
  }, []);

  return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>;
};

export default LanguageProvider;
