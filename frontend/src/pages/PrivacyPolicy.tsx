import { useEffect } from "react";
import {
  ArrowUpRight,
  Camera,
  CheckCircle2,
  CircleUserRound,
  Eye,
  FileText,
  LockKeyhole,
  ShieldCheck,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

const sectionIds = [
  "overview",
  "information",
  "camera",
  "ai",
  "use",
  "account",
  "security",
  "retention",
  "sharing",
  "rights",
  "cookies",
  "thirdParty",
  "changes",
  "contact",
] as const;

const glanceIcons = [LockKeyhole, Camera, Eye, FileText];

const PrivacyPolicy = () => {
  const { t, i18n } = useTranslation();

  useEffect(() => {
    document.title = t("privacyPolicy.pageTitle");
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
            {t("privacyPolicy.eyebrow")}
          </p>
          <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
            <div>
              <h1 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                {t("privacyPolicy.title")}
              </h1>
              <p className="mt-4 max-w-3xl text-base leading-8 text-slate-300">
                {t("privacyPolicy.intro")}
              </p>
            </div>
            <p className="shrink-0 text-sm text-slate-400">
              <span className="text-slate-500">
                {t("privacyPolicy.lastUpdatedLabel")}
              </span>{" "}
              {t("privacyPolicy.lastUpdated")}
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8 lg:px-12">
        <section
          aria-labelledby="privacy-glance"
          className="mb-12 rounded-2xl border border-emerald-400/20 bg-[#0d1d2f] p-6 shadow-2xl shadow-black/10 sm:p-8"
        >
          <div className="mb-6 flex items-center gap-3">
            <ShieldCheck className="text-emerald-400" size={22} />
            <h2
              id="privacy-glance"
              className="text-xl font-semibold text-white"
            >
              {t("privacyPolicy.glanceTitle")}
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
                  {t(`privacyPolicy.glance.${index}.title`)}
                </h3>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  {t(`privacyPolicy.glance.${index}.text`)}
                </p>
              </div>
            ))}
          </div>
        </section>

        <div className="grid gap-10 lg:grid-cols-[210px_minmax(0,1fr)] lg:items-start">
          <aside className="lg:sticky lg:top-6">
            <label htmlFor="policy-sections" className="sr-only">
              {t("privacyPolicy.sectionNavigation")}
            </label>
            <select
              id="policy-sections"
              className="mb-4 w-full rounded-lg border border-white/10 bg-[#0d1d2f] px-3 py-3 text-sm text-slate-200 outline-none focus:border-emerald-400 lg:hidden"
              onChange={(event) => scrollToSection(event.target.value)}
              defaultValue="overview"
            >
              {sectionIds.map((id, index) => (
                <option key={id} value={id}>
                  {t(`privacyPolicy.sections.${id}.title`, {
                    index: index + 1,
                  })}
                </option>
              ))}
            </select>
            <nav
              aria-label={t("privacyPolicy.sectionNavigation")}
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
                  {t(`privacyPolicy.sections.${id}.title`, {
                    index: index + 1,
                  })}
                </a>
              ))}
            </nav>
          </aside>

          <article className="min-w-0 rounded-2xl border border-white/10 bg-[#0b192a] p-6 sm:p-10">
            {sectionIds.map((id, index) => {
              const section = `privacyPolicy.sections.${id}`;
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
                    {[1, 2, 3, 4].map((item) => {
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
                  {id === "contact" && (
                    <Link
                      to="#contact"
                      className="mt-6 inline-flex items-center gap-2 rounded-lg bg-emerald-400 px-4 py-3 text-sm font-bold text-slate-950 transition-colors hover:bg-emerald-300 focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:ring-offset-2 focus:ring-offset-[#0b192a]"
                    >
                      <CircleUserRound size={17} />
                      {t("privacyPolicy.contactButton")}
                      <ArrowUpRight size={16} />
                    </Link>
                  )}
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
              className="text-emerald-400 transition-colors hover:text-emerald-300"
            >
              {t("profile.privacyPolicy")}
            </Link>
            <Link
              to="/terms-of-service"
              className="transition-colors hover:text-white"
            >
              {t("profile.termsOfService")}
            </Link>
            <Link to="/docs" className="transition-colors hover:text-white">
              {t("profile.documentation")}
            </Link>
            <Link to="/support" className="transition-colors hover:text-white">
              {t("profile.support")}
            </Link>
            <Link to="/contact" className="transition-colors hover:text-white">
              {t("profile.contact")}
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default PrivacyPolicy;
