import { useEffect } from "react";
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  CircleUserRound,
  KeyRound,
  ShieldCheck,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

const sectionIds = [
  "acceptance",
  "service",
  "eligibility",
  "acceptableUse",
  "cameraResponsibilities",
  "aiAlerts",
  "securityCredentials",
  "userContent",
  "externalCameras",
  "availability",
  "intellectualProperty",
  "suspension",
  "disclaimers",
  "liability",
  "changes",
  "contact",
] as const;

const glanceIcons = [KeyRound, CircleUserRound, Camera, AlertTriangle];

const TermsOfService = () => {
  const { t, i18n } = useTranslation();

  useEffect(() => {
    document.title = t("termsOfServicePage.pageTitle");
  }, [i18n.language, t]);

  const scrollToSection = (id: string) => {
    document
      .getElementById(id)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="min-h-screen bg-[#07111f] text-slate-100">
      <header className="border-b border-white/10 bg-[#0a1728]/90 px-5 py-14 sm:px-8 lg:px-12">
        <div className="mx-auto max-w-6xl">
          <p className="mb-4 text-xs font-bold uppercase tracking-[0.28em] text-emerald-400">
            {t("termsOfServicePage.eyebrow")}
          </p>
          <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
            <div>
              <h1 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                {t("termsOfServicePage.title")}
              </h1>
              <p className="mt-4 max-w-3xl text-base leading-8 text-slate-300">
                {t("termsOfServicePage.intro")}
              </p>
            </div>
            <p className="shrink-0 text-sm text-slate-400">
              <span className="text-slate-500">
                {t("termsOfServicePage.lastUpdatedLabel")}
              </span>{" "}
              {t("termsOfServicePage.lastUpdated")}
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8 lg:px-12">
        <section
          aria-labelledby="terms-glance"
          className="mb-12 rounded-2xl border border-emerald-400/20 bg-[#0d1d2f] p-6 shadow-2xl shadow-black/10 sm:p-8"
        >
          <div className="mb-6 flex items-center gap-3">
            <ShieldCheck className="text-emerald-400" size={22} />
            <h2 id="terms-glance" className="text-xl font-semibold text-white">
              {t("termsOfServicePage.glanceTitle")}
            </h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {glanceIcons.map((Icon, index) => (
              <div
                key={index}
                className="rounded-xl border border-white/10 bg-[#10243a] p-4"
              >
                <Icon size={19} className="mb-4 text-emerald-400" />
                <h3 className="font-semibold text-white">
                  {t(`termsOfServicePage.glance.${index}.title`)}
                </h3>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  {t(`termsOfServicePage.glance.${index}.text`)}
                </p>
              </div>
            ))}
          </div>
        </section>

        <div className="grid gap-10 lg:grid-cols-[230px_minmax(0,1fr)] lg:items-start">
          <aside className="lg:sticky lg:top-6">
            <label htmlFor="terms-sections" className="sr-only">
              {t("termsOfServicePage.sectionNavigation")}
            </label>
            <select
              id="terms-sections"
              className="mb-4 w-full rounded-lg border border-white/10 bg-[#0d1d2f] px-3 py-3 text-sm text-slate-200 outline-none focus:border-emerald-400 lg:hidden"
              onChange={(event) => scrollToSection(event.target.value)}
              defaultValue="acceptance"
            >
              {sectionIds.map((id, index) => (
                <option key={id} value={id}>
                  {t(`termsOfServicePage.sections.${id}.title`, {
                    index: index + 1,
                  })}
                </option>
              ))}
            </select>
            <nav
              aria-label={t("termsOfServicePage.sectionNavigation")}
              className="hidden border-s border-white/10 lg:block"
            >
              {sectionIds.map((id, index) => (
                <a
                  key={id}
                  href={`#${id}`}
                  onClick={(event) => {
                    event.preventDefault();
                    scrollToSection(id);
                  }}
                  className="block border-s-2 border-transparent px-4 py-2 text-sm text-slate-400 transition-colors hover:border-emerald-400 hover:text-white"
                >
                  {t(`termsOfServicePage.sections.${id}.title`, {
                    index: index + 1,
                  })}
                </a>
              ))}
            </nav>
          </aside>

          <article className="min-w-0 rounded-2xl border border-white/10 bg-[#0b192a] p-6 sm:p-10">
            {sectionIds.map((id, index) => {
              const section = `termsOfServicePage.sections.${id}`;
              return (
                <section
                  key={id}
                  id={id}
                  className="scroll-mt-8 border-b border-white/10 py-8 first:pt-0 last:border-0 last:pb-0"
                >
                  <h2 className="text-2xl font-semibold tracking-tight text-white">
                    {t(`${section}.title`, { index: index + 1 })}
                  </h2>
                  <p className="mt-4 leading-8 text-slate-300">
                    {t(`${section}.p1`)}
                  </p>
                  <p className="mt-4 leading-8 text-slate-300">
                    {t(`${section}.p2`)}
                  </p>
                  <ul className="mt-4 space-y-2 text-slate-300">
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((item) => {
                      const value = t(`${section}.item${item}`, {
                        defaultValue: "",
                      });
                      return value ? (
                        <li key={item} className="flex gap-3 leading-7">
                          <CheckCircle2
                            size={17}
                            className="mt-1 shrink-0 text-emerald-400"
                          />
                          {value}
                        </li>
                      ) : null;
                    })}
                  </ul>
                </section>
              );
            })}
          </article>
        </div>
      </main>

      <footer className="border-t border-white/5 px-5 py-8 sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 text-xs font-medium text-slate-500 md:flex-row">
          <p>{t("profile.copyright")}</p>
          <div className="flex flex-wrap justify-center gap-6">
            <Link
              to="/privacy-policy"
              className="transition-colors hover:text-white"
            >
              {t("profile.privacyPolicy")}
            </Link>
            <Link
              to="/terms-of-service"
              className="text-emerald-400 transition-colors hover:text-emerald-300"
            >
              {t("profile.termsOfService")}
            </Link>
            <Link to="/docs" className="transition-colors hover:text-white">
              {t("profile.documentation")}
            </Link>
            <Link to="/support" className="transition-colors hover:text-white">
              {t("profile.support")}
            </Link>
            <button className="transition-colors hover:text-white">
              {t("profile.contact")}
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default TermsOfService;
