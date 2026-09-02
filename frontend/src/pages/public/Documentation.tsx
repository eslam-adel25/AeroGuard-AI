import { useEffect, useMemo, useState } from "react";
import {
  AlarmClock,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Camera,
  ChevronRight,
  CircleHelp,
  FileText,
  LayoutDashboard,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Users,
  X,
} from "lucide-react";
import { useTranslation } from "react-i18next";

const articleIds = [
  "introduction",
  "login",
  "quickStart",
  "roles",
  "cameraOverview",
  "liveRtsp",
  "videoArchive",
  "laptopCamera",
  "cameraStatus",
  "cameraSelection",
  "dashboard",
  "liveView",
  "cameraControls",
  "fullscreen",
  "aiDetection",
  "fireSmoke",
  "personTracking",
  "personIds",
  "ownership",
  "abandonedBags",
  "restrictedArea",
  "wrongDirection",
  "tripwire",
  "loitering",
  "annotationModes",
  "addRegion",
  "undo",
  "delete",
  "save",
  "cameraZones",
  "alertLevels",
  "notifications",
  "eventDetails",
  "evidence",
  "alarmSounds",
  "settings",
  "cameraOffline",
  "rtspProblems",
  "noAlerts",
  "noSound",
  "annotationProblems",
  "faq",
  "systemOverview",
] as const;

const groups = [
  {
    key: "gettingStarted",
    icon: BookOpen,
    articles: ["introduction", "login", "quickStart", "roles"],
  },
  {
    key: "cameras",
    icon: Camera,
    articles: [
      "cameraOverview",
      "liveRtsp",
      "videoArchive",
      "laptopCamera",
      "cameraStatus",
      "cameraSelection",
    ],
  },
  {
    key: "dashboard",
    icon: LayoutDashboard,
    articles: ["dashboard", "liveView", "cameraControls", "fullscreen"],
  },
  {
    key: "ai",
    icon: ShieldCheck,
    articles: [
      "aiDetection",
      "fireSmoke",
      "personTracking",
      "personIds",
      "ownership",
      "abandonedBags",
    ],
  },
  {
    key: "rules",
    icon: SlidersHorizontal,
    articles: ["restrictedArea", "wrongDirection", "tripwire", "loitering"],
  },
  {
    key: "annotations",
    icon: FileText,
    articles: [
      "annotationModes",
      "addRegion",
      "undo",
      "delete",
      "save",
      "cameraZones",
    ],
  },
  {
    key: "alerts",
    icon: AlarmClock,
    articles: [
      "alertLevels",
      "notifications",
      "eventDetails",
      "evidence",
      "alarmSounds",
    ],
  },
  { key: "users", icon: Users, articles: ["roles", "settings"] },
  {
    key: "troubleshooting",
    icon: CircleHelp,
    articles: [
      "cameraOffline",
      "rtspProblems",
      "noAlerts",
      "noSound",
      "annotationProblems",
    ],
  },
  { key: "reference", icon: BookOpen, articles: ["faq", "systemOverview"] },
] as const;

const Documentation = () => {
  const { t, i18n } = useTranslation();
  const [selectedId, setSelectedId] =
    useState<(typeof articleIds)[number]>("introduction");
  const [query, setQuery] = useState("");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    () => new Set(["gettingStarted"]),
  );

  useEffect(() => {
    document.title = t("documentation.pageTitle");
  }, [i18n.language, t]);

  const articleCatalog = useMemo(
    () =>
      articleIds.map((id) => {
        const group = groups.find((candidate) =>
          (candidate.articles as readonly string[]).includes(id),
        );
        return {
          id,
          category: group?.key ?? "reference",
          title: t(`documentation.articles.${id}.title`),
          summary: t(`documentation.articles.${id}.summary`),
          body: t(`documentation.articles.${id}.body`),
          categoryTitle: group
            ? t(`documentation.groups.${group.key}`)
            : t("documentation.groups.reference"),
        };
      }),
    [t],
  );
  const searchResults = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase().replace(/\s+/g, " ");
    if (!normalized) return [];

    return articleCatalog
      .map((article) => {
        const title = article.title.toLocaleLowerCase();
        const category = article.categoryTitle.toLocaleLowerCase();
        const summary = article.summary.toLocaleLowerCase();
        const body = article.body.toLocaleLowerCase();
        let score = 0;
        if (title === normalized) score += 1000;
        if (title.includes(normalized)) score += 500;
        if (category.includes(normalized)) score += 250;
        if (summary.includes(normalized)) score += 100;
        if (body.includes(normalized)) score += 25;
        for (const token of normalized.split(" ")) {
          if (token && title.includes(token)) score += 40;
          else if (token && category.includes(token)) score += 20;
          else if (token && summary.includes(token)) score += 10;
          else if (token && body.includes(token)) score += 2;
        }
        return { article, score };
      })
      .filter(({ score }) => score > 0)
      .sort((left, right) => right.score - left.score)
      .map(({ article }) => article);
  }, [articleCatalog, query]);
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

  return (
    <div className="min-h-screen bg-[#07111f] text-slate-100">
      <header className="border-b border-white/10 bg-[#0a1728]/95 px-5 py-8 sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-7xl flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="mb-3 text-xs font-bold uppercase tracking-[0.28em] text-emerald-400">
              {t("documentation.eyebrow")}
            </p>
            <h1 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">
              {t("documentation.title")}
            </h1>
            <p className="mt-4 max-w-2xl leading-8 text-slate-300">
              {t("documentation.intro")}
            </p>
          </div>
          <div className="relative w-full lg:max-w-sm">
            <label htmlFor="docs-search" className="sr-only">
              {t("documentation.searchLabel")}
            </label>
            <Search
              className="absolute start-3 top-3.5 text-slate-500"
              size={18}
            />
            <input
              id="docs-search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t("documentation.searchPlaceholder")}
              className="w-full rounded-lg border border-white/10 bg-[#10243a] py-3 pe-10 ps-10 text-sm text-white outline-none placeholder:text-slate-500 focus:border-emerald-400"
            />
            {query && (
              <button
                type="button"
                aria-label={t("documentation.clearSearch")}
                onClick={() => setQuery("")}
                className="absolute end-3 top-3 text-slate-500 hover:text-white"
              >
                <X size={18} />
              </button>
            )}
            {searchResults.length > 0 && (
              <div className="absolute z-20 mt-2 max-h-72 w-full overflow-y-auto rounded-lg border border-white/10 bg-[#10243a] p-2 shadow-2xl">
                {searchResults.map((article) => (
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
                ))}
              </div>
            )}
            {query && searchResults.length === 0 && (
              <p className="absolute z-20 mt-2 w-full rounded-lg border border-white/10 bg-[#10243a] p-3 text-sm text-slate-400">
                <span className="block text-slate-200">
                  {t("documentation.noResults")}
                </span>
                <span className="mt-1 block text-xs">
                  {t("documentation.noResultsHint")}
                </span>
              </p>
            )}
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-7xl items-center justify-between border-b border-white/10 px-5 py-3 sm:px-8 lg:hidden">
        <span className="text-sm font-semibold text-white">
          {t("documentation.navigation")}
        </span>
        <button
          type="button"
          onClick={() => setMobileNavOpen((open) => !open)}
          aria-expanded={mobileNavOpen}
          className="rounded-lg border border-white/10 p-2 text-slate-300 hover:border-emerald-400 hover:text-white"
        >
          <BookOpen size={18} />
        </button>
      </div>

      <main className="mx-auto grid max-w-7xl gap-10 px-5 py-8 sm:px-8 lg:grid-cols-[250px_minmax(0,1fr)] lg:px-12">
        <aside className={`${mobileNavOpen ? "block" : "hidden"} lg:block`}>
          <nav
            aria-label={t("documentation.navigation")}
            className="lg:sticky lg:top-6"
          >
            {groups.map(({ key, icon: Icon, articles }) => {
              const isExpanded = expandedGroups.has(key);
              return (
                <div key={key} className="mb-3">
                  <button
                    type="button"
                    aria-expanded={isExpanded}
                    aria-controls={`documentation-group-${key}`}
                    onClick={() => toggleGroup(key)}
                    className="flex w-full items-center justify-between rounded-md px-3 py-3 text-start text-xs font-bold uppercase tracking-wider text-emerald-400 transition-colors hover:bg-white/5"
                  >
                    <span className="flex items-center gap-2">
                      <Icon size={15} />
                      {t(`documentation.groups.${key}`)}
                    </span>
                    <ChevronRight
                      size={16}
                      className={`transition-transform duration-200 ${isExpanded ? "rotate-90" : ""}`}
                    />
                  </button>
                  {isExpanded && (
                    <div
                      id={`documentation-group-${key}`}
                      className="mt-1 border-s border-white/10 ps-2"
                    >
                      {articles.map((id) => (
                        <button
                          type="button"
                          key={id}
                          aria-current={selectedId === id ? "page" : undefined}
                          onClick={() =>
                            selectArticle(id as (typeof articleIds)[number])
                          }
                          className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-start text-sm transition-colors ${selectedId === id ? "bg-emerald-400/10 text-emerald-300" : "text-slate-400 hover:bg-white/5 hover:text-white"}`}
                        >
                          {t(`documentation.articles.${id}.title`)}
                          {selectedId === id && <ChevronRight size={15} />}
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
          <div className="mb-8 flex flex-wrap items-center gap-2 text-sm text-slate-500">
            <span>{t("documentation.title")}</span>
            <ChevronRight size={15} />
            {currentGroup && (
              <>
                <span>{t(`documentation.groups.${currentGroup.key}`)}</span>
                <ChevronRight size={15} />
              </>
            )}
            <span className="text-slate-300">
              {t(`documentation.articles.${selectedId}.title`)}
            </span>
          </div>
          <div className="rounded-2xl border border-white/10 bg-[#0b192a] p-6 sm:p-10">
            {selectedId === "introduction" && (
              <div className="mb-8 rounded-xl border border-emerald-400/20 bg-emerald-400/5 p-5">
                <p className="text-sm leading-7 text-emerald-100">
                  {t("documentation.heroCallout")}
                </p>
                <div className="mt-5 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => selectArticle("quickStart")}
                    className="rounded-lg bg-emerald-400 px-4 py-2.5 text-sm font-bold text-slate-950 hover:bg-emerald-300"
                  >
                    {t("documentation.getStarted")}
                  </button>
                  <button
                    type="button"
                    onClick={() => selectArticle("liveRtsp")}
                    className="rounded-lg border border-white/15 px-4 py-2.5 text-sm font-semibold text-white hover:border-emerald-400"
                  >
                    {t("documentation.cameraSetup")}
                  </button>
                </div>
              </div>
            )}
            <h2 className="text-3xl font-semibold tracking-tight text-white">
              {t(`documentation.articles.${selectedId}.title`)}
            </h2>
            <p className="mt-4 text-lg leading-8 text-slate-300">
              {t(`documentation.articles.${selectedId}.summary`)}
            </p>
            <div className="mt-8 space-y-5 text-[15px] leading-8 text-slate-300">
              {t(`documentation.articles.${selectedId}.body`)
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
          </div>
          <div className="mt-8 flex items-center justify-between gap-4 border-t border-white/10 pt-6">
            <button
              type="button"
              disabled={currentIndex === 0}
              onClick={() => selectArticle(articleIds[currentIndex - 1])}
              className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-4 py-3 text-sm text-slate-300 hover:border-emerald-400 hover:text-white disabled:invisible"
            >
              <ArrowLeft size={16} />
              {t("documentation.previous")}
            </button>
            <button
              type="button"
              disabled={currentIndex === articleIds.length - 1}
              onClick={() => selectArticle(articleIds[currentIndex + 1])}
              className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-4 py-3 text-sm text-slate-300 hover:border-emerald-400 hover:text-white disabled:invisible"
            >
              {t("documentation.next")}
              <ArrowRight size={16} />
            </button>
          </div>
        </article>
      </main>

      <footer className="border-t border-white/5 px-5 py-8 sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 text-xs font-medium text-slate-500 md:flex-row">
          <p>{t("profile.copyright")}</p>
          <div className="flex flex-wrap justify-center gap-6">
            <a
              href="/privacy-policy"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white"
            >
              {t("profile.privacyPolicy")}
            </a>
            <a
              href="/terms-of-service"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white"
            >
              {t("profile.termsOfService")}
            </a>
            <a
              href="/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-emerald-400 hover:text-emerald-300"
            >
              {t("profile.documentation")}
            </a>
            <a
              href="/support"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white"
            >
              {t("profile.support")}
            </a>
            <a
              href="/contact"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white"
            >
              {t("profile.contact")}
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Documentation;
