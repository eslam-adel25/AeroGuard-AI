import { useEffect, useMemo, useState } from "react";
import {
  AlarmClock,
  ArrowRight,
  Camera,
  ChevronRight,
  CircleHelp,
  FileWarning,
  KeyRound,
  Mail,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

const supportEmail = "Eslam.Adel2596@gmail.com";
const articleIds = [
  "overview",
  "beforeContacting",
  "loginProblems",
  "permissionProblems",
  "sessionProblems",
  "browserProblems",
  "cameraOffline",
  "rtspProblems",
  "provisioning",
  "streamProblems",
  "cameraStatus",
  "noDetection",
  "incorrectDetection",
  "personIds",
  "ownership",
  "abandonedBags",
  "noAlerts",
  "notificationProblems",
  "eventHistory",
  "alarmSoundProblems",
  "fireSmoke",
  "annotationProblems",
  "commonIssues",
  "faq",
] as const;
const groups = [
  {
    key: "center",
    icon: ShieldCheck,
    articles: ["overview", "beforeContacting"],
  },
  {
    key: "account",
    icon: KeyRound,
    articles: [
      "loginProblems",
      "permissionProblems",
      "sessionProblems",
      "browserProblems",
    ],
  },
  {
    key: "cameras",
    icon: Camera,
    articles: [
      "cameraOffline",
      "rtspProblems",
      "provisioning",
      "streamProblems",
      "cameraStatus",
    ],
  },
  {
    key: "ai",
    icon: ShieldCheck,
    articles: [
      "noDetection",
      "incorrectDetection",
      "personIds",
      "ownership",
      "abandonedBags",
      "fireSmoke",
    ],
  },
  {
    key: "alerts",
    icon: AlarmClock,
    articles: [
      "noAlerts",
      "notificationProblems",
      "eventHistory",
      "alarmSoundProblems",
    ],
  },
  {
    key: "annotations",
    icon: SlidersHorizontal,
    articles: ["annotationProblems"],
  },
  { key: "general", icon: CircleHelp, articles: ["commonIssues", "faq"] },
] as const;
const quickArticles = [
  "cameraOffline",
  "rtspProblems",
  "noAlerts",
  "alarmSoundProblems",
] as const;

const Support = () => {
  const { t, i18n } = useTranslation();
  const [selectedId, setSelectedId] =
    useState<(typeof articleIds)[number]>("overview");
  const [query, setQuery] = useState("");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    () => new Set(),
  );

  useEffect(() => {
    document.title = t("support.pageTitle");
  }, [i18n.language, t]);
  const catalog = useMemo(
    () =>
      articleIds.map((id) => {
        const group = groups.find((candidate) =>
          (candidate.articles as readonly string[]).includes(id),
        );
        return {
          id,
          title: t(`support.articles.${id}.title`),
          summary: t(`support.articles.${id}.summary`),
          body: t(`support.articles.${id}.body`),
          category: group?.key ?? "general",
          categoryTitle: t(`support.groups.${group?.key ?? "general"}`),
        };
      }),
    [t],
  );
  const results = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase().replace(/\s+/g, " ");
    if (!normalized) return [];
    return catalog
      .map((article) => {
        const fields = [
          article.title,
          article.categoryTitle,
          article.summary,
          article.body,
        ].map((value) => value.toLocaleLowerCase());
        let score = fields[3].includes(normalized) ? 10 : 0;
        if (fields[0] === normalized) score += 1000;
        else if (fields[0].includes(normalized)) score += 500;
        if (fields[1].includes(normalized)) score += 250;
        if (fields[2].includes(normalized)) score += 100;
        normalized.split(" ").forEach((token) => {
          if (token && fields[0].includes(token)) score += 40;
          else if (token && fields[1].includes(token)) score += 20;
          else if (token && fields[2].includes(token)) score += 10;
          else if (token && fields[3].includes(token)) score += 2;
        });
        return { article, score };
      })
      .filter(({ score }) => score > 0)
      .sort((a, b) => b.score - a.score)
      .map(({ article }) => article);
  }, [catalog, query]);
  const currentIndex = articleIds.indexOf(selectedId);
  const currentGroup = groups.find((group) =>
    (group.articles as readonly string[]).includes(selectedId),
  );
  useEffect(() => {
    if (!currentGroup) return;
    setExpandedGroups((current) => {
      if (current.has(currentGroup.key)) return current;
      const next = new Set(current);
      next.add(currentGroup.key);
      return next;
    });
  }, [currentGroup]);
  const toggleGroup = (groupKey: string) => {
    setExpandedGroups((current) => {
      const next = new Set(current);
      if (next.has(groupKey)) next.delete(groupKey);
      else next.add(groupKey);
      return next;
    });
  };
  const selectArticle = (id: (typeof articleIds)[number]) => {
    setSelectedId(id);
    setQuery("");
    setMobileNavOpen(false);
  };
  const mailto = (subject: string) =>
    `mailto:${supportEmail}?subject=${encodeURIComponent(subject)}`;

  return (
    <div className="min-h-screen bg-[#07111f] text-slate-100">
      <header className="border-b border-white/10 bg-[#0a1728]/95 px-5 py-12 sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-7xl flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="mb-3 text-xs font-bold uppercase tracking-[0.28em] text-emerald-400">
              {t("support.eyebrow")}
            </p>
            <h1 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">
              {t("support.title")}
            </h1>
            <p className="mt-4 max-w-2xl leading-8 text-slate-300">
              {t("support.intro")}
            </p>
          </div>
          <div className="relative w-full lg:max-w-sm">
            <label htmlFor="support-search" className="sr-only">
              {t("support.searchLabel")}
            </label>
            <Search
              className="absolute start-3 top-3.5 text-slate-500"
              size={18}
            />
            <input
              id="support-search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t("support.searchPlaceholder")}
              className="w-full rounded-lg border border-white/10 bg-[#10243a] py-3 pe-10 ps-10 text-sm text-white outline-none placeholder:text-slate-500 focus:border-emerald-400"
            />
            {query && (
              <button
                type="button"
                aria-label={t("support.clearSearch")}
                onClick={() => setQuery("")}
                className="absolute end-3 top-3 text-slate-500 hover:text-white"
              >
                <X size={18} />
              </button>
            )}
            {query && (
              <div className="absolute z-20 mt-2 max-h-80 w-full overflow-y-auto rounded-lg border border-white/10 bg-[#10243a] p-2 shadow-2xl">
                {results.length ? (
                  results.map((article) => (
                    <button
                      type="button"
                      key={article.id}
                      onClick={() => selectArticle(article.id)}
                      className="block w-full rounded-md px-3 py-2 text-start hover:bg-white/10"
                    >
                      <span className="block text-sm text-slate-200">
                        {article.title}
                      </span>
                      <span className="mt-1 block text-[11px] font-bold uppercase tracking-wider text-emerald-400">
                        {article.categoryTitle}
                      </span>
                      <span className="mt-1 block text-xs leading-5 text-slate-400">
                        {article.summary}
                      </span>
                    </button>
                  ))
                ) : (
                  <div className="p-2 text-sm text-slate-300">
                    <p>{t("support.noResults")}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {t("support.noResultsHint")}
                    </p>
                    <a
                      href={mailto("AeroGuard Support Request")}
                      className="mt-3 inline-flex items-center gap-2 font-semibold text-emerald-300 hover:text-emerald-200"
                    >
                      {t("support.contactButton")}
                      <ArrowRight size={15} />
                    </a>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-12">
        <section className="mb-10 rounded-2xl border border-emerald-400/20 bg-[#0d1d2f] p-6 sm:p-8">
          <div className="mb-6 flex items-center gap-3">
            <ShieldCheck className="text-emerald-400" size={22} />
            <h2 className="text-xl font-semibold text-white">
              {t("support.quickHelp")}
            </h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {quickArticles.map((id) => (
              <button
                type="button"
                key={id}
                onClick={() => selectArticle(id)}
                className="rounded-xl border border-white/10 bg-[#10243a] p-4 text-start transition-colors hover:border-emerald-400/50"
              >
                <Camera size={19} className="mb-4 text-emerald-400" />
                <h3 className="font-semibold text-white">
                  {t(`support.articles.${id}.title`)}
                </h3>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  {t(`support.articles.${id}.summary`)}
                </p>
              </button>
            ))}
          </div>
        </section>
        <div className="mb-4 flex items-center justify-between lg:hidden">
          <span className="text-sm font-semibold text-white">
            {t("support.navigation")}
          </span>
          <button
            type="button"
            onClick={() => setMobileNavOpen((open) => !open)}
            aria-expanded={mobileNavOpen}
            className="rounded-lg border border-white/10 p-2 text-slate-300 hover:border-emerald-400"
          >
            <Search size={18} />
          </button>
        </div>
        <div className="grid gap-10 lg:grid-cols-[250px_minmax(0,1fr)] lg:items-start">
          <aside className={`${mobileNavOpen ? "block" : "hidden"} lg:block`}>
            <nav
              aria-label={t("support.navigation")}
              className="lg:sticky lg:top-6"
            >
              {groups.map(({ key, icon: Icon, articles }) => {
                const isExpanded = expandedGroups.has(key);
                return (
                  <div key={key} className="mb-3">
                    <button
                      type="button"
                      aria-expanded={isExpanded}
                      aria-controls={`support-group-${key}`}
                      onClick={() => toggleGroup(key)}
                      className="flex w-full items-center justify-between rounded-md px-3 py-3 text-start text-xs font-bold uppercase tracking-wider text-emerald-400 transition-colors hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-emerald-400/60"
                    >
                      <span className="flex items-center gap-2">
                        <Icon size={15} />
                        {t(`support.groups.${key}`)}
                      </span>
                      <ChevronRight
                        size={16}
                        className={`transition-transform duration-200 ${isExpanded ? "rotate-90" : ""}`}
                      />
                    </button>
                    {isExpanded && (
                      <div
                        id={`support-group-${key}`}
                        className="mt-1 border-s border-white/10 ps-2"
                      >
                        {articles.map((id) => (
                          <button
                            type="button"
                            key={id}
                            aria-current={
                              selectedId === id ? "page" : undefined
                            }
                            onClick={() => selectArticle(id)}
                            className={`flex w-full rounded-md px-3 py-2 text-start text-sm ${selectedId === id ? "bg-emerald-400/10 text-emerald-300" : "text-slate-400 hover:bg-white/5 hover:text-white"}`}
                          >
                            {t(`support.articles.${id}.title`)}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </nav>
          </aside>
          <article className="min-w-0">
            <div className="mb-6 flex flex-wrap items-center gap-2 text-sm text-slate-500">
              <span>{t("support.title")}</span>
              <ArrowRight size={15} />
              <span>
                {currentGroup && t(`support.groups.${currentGroup.key}`)}
              </span>
              <ArrowRight size={15} />
              <span className="text-slate-300">
                {t(`support.articles.${selectedId}.title`)}
              </span>
            </div>
            <div className="rounded-2xl border border-white/10 bg-[#0b192a] p-6 sm:p-10">
              <h2 className="text-3xl font-semibold tracking-tight text-white">
                {t(`support.articles.${selectedId}.title`)}
              </h2>
              <p className="mt-4 text-lg leading-8 text-slate-300">
                {t(`support.articles.${selectedId}.summary`)}
              </p>
              <div className="mt-8 space-y-5 text-[15px] leading-8 text-slate-300">
                {t(`support.articles.${selectedId}.body`)
                  .split("\n")
                  .map((paragraph, index) => (
                    <p
                      key={index}
                      className={
                        paragraph.startsWith("rtsp://")
                          ? "overflow-x-auto rounded-lg border border-white/10 bg-[#07111f] px-4 py-3 font-mono text-sm text-emerald-300"
                          : ""
                      }
                    >
                      {paragraph}
                    </p>
                  ))}
              </div>
              {selectedId === "beforeContacting" && (
                <div className="mt-8 rounded-xl border border-amber-400/30 bg-amber-400/5 p-5">
                  <div className="flex gap-3">
                    <FileWarning
                      className="shrink-0 text-amber-300"
                      size={20}
                    />
                    <p className="text-sm leading-7 text-amber-100">
                      {t("support.securityWarning")}
                    </p>
                  </div>
                </div>
              )}
            </div>
            <div className="mt-8 flex items-center justify-between gap-4 border-t border-white/10 pt-6">
              <button
                type="button"
                disabled={currentIndex === 0}
                onClick={() => selectArticle(articleIds[currentIndex - 1])}
                className="rounded-lg border border-white/10 px-4 py-3 text-sm text-slate-300 hover:border-emerald-400 disabled:invisible"
              >
                {t("support.previous")}
              </button>
              <button
                type="button"
                disabled={currentIndex === articleIds.length - 1}
                onClick={() => selectArticle(articleIds[currentIndex + 1])}
                className="rounded-lg border border-white/10 px-4 py-3 text-sm text-slate-300 hover:border-emerald-400 disabled:invisible"
              >
                {t("support.next")}
              </button>
            </div>
          </article>
        </div>
        <section className="mt-10">
          <div className="rounded-2xl border border-white/10 bg-[#0d1d2f] p-6">
            <h2 className="text-xl font-semibold text-white">
              {t("support.contactTitle")}
            </h2>
            <p className="mt-3 leading-7 text-slate-300">
              {t("support.contactText")}
            </p>
            <p className="mt-4 break-all font-semibold text-emerald-300">
              {supportEmail}
            </p>
            <a
              href={mailto("AeroGuard Support Request")}
              className="mt-5 inline-flex items-center gap-2 rounded-lg bg-emerald-400 px-4 py-3 text-sm font-bold text-slate-950 hover:bg-emerald-300"
            >
              <Mail size={17} />
              {t("support.emailSupport")}
            </a>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/5 px-5 py-8 sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 text-xs font-medium text-slate-500 md:flex-row">
          <p>{t("profile.copyright")}</p>
          <div className="flex flex-wrap justify-center gap-6">
            <Link to="/privacy-policy" className="hover:text-white">
              {t("profile.privacyPolicy")}
            </Link>
            <Link to="/terms-of-service" className="hover:text-white">
              {t("profile.termsOfService")}
            </Link>
            <Link to="/docs" className="hover:text-white">
              {t("profile.documentation")}
            </Link>
            <Link
              to="/support"
              className="text-emerald-400 hover:text-emerald-300"
            >
              {t("profile.support")}
            </Link>
            <Link to="/contact" className="hover:text-white">
              {t("profile.contact")}
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Support;
