import { useEffect } from "react";
import { ArrowUpRight, Globe2, Mail, Phone, ShieldAlert } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

const emailAddress = "Eslam.Adel2596@gmail.com";
const phoneNumber = "+201093397961";
const socialLinks = {
  github: "https://github.com/eslam-adel25",
  linkedin: "https://www.linkedin.com/in/eslam-adel-jadalrab-808862361",
  facebook: "https://www.facebook.com/eslam20057",
};

const Contact = () => {
  const { t, i18n } = useTranslation();

  useEffect(() => {
    document.title = t("contactPage.pageTitle");
  }, [i18n.language, t]);

  const socialMethods = [
    { key: "github", href: socialLinks.github },
    { key: "linkedin", href: socialLinks.linkedin },
    { key: "facebook", href: socialLinks.facebook },
  ];

  return (
    <div className="min-h-screen bg-[#07111f] text-slate-100">
      <header className="border-b border-white/10 bg-[#0a1728]/95 px-5 py-14 sm:px-8 lg:px-12">
        <div className="mx-auto max-w-6xl">
          <p className="mb-4 text-xs font-bold uppercase tracking-[0.28em] text-emerald-400">
            {t("contactPage.eyebrow")}
          </p>
          <div className="flex flex-col justify-between gap-7 md:flex-row md:items-end">
            <div>
              <h1 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                {t("contactPage.title")}
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-8 text-slate-300">
                {t("contactPage.intro")}
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                to="/support"
                className="inline-flex items-center gap-2 rounded-lg bg-emerald-400 px-4 py-3 text-sm font-semibold text-slate-950 hover:bg-emerald-300 focus:outline-none focus:ring-2 focus:ring-emerald-300"
              >
                {t("contactPage.visitSupport")}
                <ArrowUpRight size={15} />
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8 lg:px-12">
        <section
          aria-labelledby="primary-contact"
          className="rounded-2xl border border-emerald-400/25 bg-[#0d1d2f] p-6 sm:p-8"
        >
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-emerald-400">
            {t("contactPage.primaryEyebrow")}
          </p>
          <h2
            id="primary-contact"
            className="mt-3 text-2xl font-semibold text-white"
          >
            {t("contactPage.primaryTitle")}
          </h2>
          <div className="mt-7 divide-y divide-white/10">
            <div className="flex flex-col gap-5 py-5 first:pt-0 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex min-w-0 items-start gap-4">
                <Mail className="mt-1 shrink-0 text-emerald-400" size={22} />
                <div>
                  <h3 className="font-semibold text-white">
                    {t("contactPage.methods.email.title")}
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-slate-400">
                    {t("contactPage.methods.email.description")}
                  </p>
                  <a
                    href={`mailto:${emailAddress}`}
                    className="mt-2 block break-all text-base font-semibold text-emerald-300 hover:text-emerald-200"
                  >
                    {emailAddress}
                  </a>
                </div>
              </div>
              <a
                href="mailto:Eslam.Adel2596@gmail.com"
                className="inline-flex w-fit shrink-0 items-center gap-2 rounded-lg border border-emerald-400/40 px-4 py-3 text-sm font-semibold text-emerald-300 hover:bg-emerald-400/10 focus:outline-none focus:ring-2 focus:ring-emerald-300"
              >
                {t("contactPage.emailAeroGuard")}
                <ArrowUpRight size={15} />
              </a>
            </div>
            <div className="flex flex-col gap-5 py-5 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex min-w-0 items-start gap-4">
                <Phone className="mt-1 shrink-0 text-emerald-400" size={22} />
                <div>
                  <h3 className="font-semibold text-white">
                    {t("contactPage.methods.phone.title")}
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-slate-400">
                    {t("contactPage.methods.phone.description")}
                  </p>
                  <a
                    href={`tel:${phoneNumber}`}
                    className="mt-2 block text-base font-semibold text-emerald-300 hover:text-emerald-200"
                  >
                    +20 109 339 7961
                  </a>
                </div>
              </div>
              <a
                href={`tel:${phoneNumber}`}
                className="inline-flex w-fit shrink-0 items-center gap-2 rounded-lg border border-white/15 px-4 py-3 text-sm font-semibold text-white hover:border-emerald-400 hover:text-emerald-300 focus:outline-none focus:ring-2 focus:ring-emerald-300"
              >
                {t("contactPage.call")}
                <ArrowUpRight size={15} />
              </a>
            </div>
          </div>
        </section>

        <section aria-labelledby="social-contact" className="mt-12">
          <div className="mb-5">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-emerald-400">
              {t("contactPage.secondaryEyebrow")}
            </p>
            <h2
              id="social-contact"
              className="mt-3 text-2xl font-semibold text-white"
            >
              {t("contactPage.secondaryTitle")}
            </h2>
          </div>
          <div className="divide-y divide-white/10 border-y border-white/10">
            {socialMethods.map(({ key, href }) => (
              <div
                key={key}
                className="flex flex-col gap-4 py-5 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex items-center gap-4">
                  <Globe2 className="text-slate-300" size={21} />
                  <div>
                    <h3 className="font-semibold text-white">
                      {t(`contactPage.methods.${key}.title`)}
                    </h3>
                    <p className="mt-1 text-sm text-slate-400">
                      {t(`contactPage.methods.${key}.description`)}
                    </p>
                  </div>
                </div>
                <a
                  href={href}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex w-fit items-center gap-2 text-sm font-semibold text-emerald-300 hover:text-emerald-200 focus:outline-none focus:ring-2 focus:ring-emerald-300"
                >
                  {t(`contactPage.methods.${key}.action`)}
                  <ArrowUpRight size={15} />
                </a>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-12 rounded-2xl border border-emerald-400/20 bg-emerald-400/5 p-6 sm:p-8">
          <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
            <div>
              <h2 className="text-2xl font-semibold text-white">
                {t("contactPage.supportTitle")}
              </h2>
              <p className="mt-2 max-w-2xl leading-7 text-slate-300">
                {t("contactPage.supportText")}
              </p>
            </div>
            <Link
              to="/support"
              className="inline-flex w-fit items-center gap-2 rounded-lg bg-emerald-400 px-4 py-3 text-sm font-bold text-slate-950 hover:bg-emerald-300 focus:outline-none focus:ring-2 focus:ring-emerald-300"
            >
              {t("contactPage.supportButton")}
              <ArrowUpRight size={16} />
            </Link>
          </div>
        </section>

        <div className="mt-10 grid gap-8 lg:grid-cols-[1fr_1.2fr]">
          <section className="rounded-2xl border border-amber-400/25 bg-amber-400/5 p-6">
            <div className="flex gap-3">
              <ShieldAlert className="shrink-0 text-amber-300" size={21} />
              <div>
                <h2 className="font-semibold text-amber-100">
                  {t("contactPage.securityTitle")}
                </h2>
                <p className="mt-2 text-sm leading-7 text-amber-100/80">
                  {t("contactPage.securityText")}
                </p>
              </div>
            </div>
          </section>
          <section className="rounded-2xl border border-white/10 bg-[#0b192a] p-6">
            <h2 className="text-xl font-semibold text-white">
              {t("contactPage.faqTitle")}
            </h2>
            <div className="mt-5 space-y-5">
              {[
                "howContact",
                "technicalHelp",
                "github",
                "linkedinFacebook",
                "call",
              ].map((key) => (
                <div key={key}>
                  <h3 className="font-semibold text-white">
                    {t(`contactPage.faq.${key}.question`)}
                  </h3>
                  <p className="mt-1 text-sm leading-6 text-slate-400">
                    {t(`contactPage.faq.${key}.answer`)}
                  </p>
                </div>
              ))}
            </div>
          </section>
        </div>

        <section className="mt-10 border-t border-white/10 pt-8">
          <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
            <div>
              <h2 className="text-lg font-semibold text-white">
                {t("contactPage.summaryTitle")}
              </h2>
              <p className="mt-2 text-sm text-slate-400">AeroGuard AI</p>
            </div>
            <div className="grid gap-2 text-sm text-slate-400 sm:grid-cols-2">
              <a
                href={`mailto:${emailAddress}`}
                className="hover:text-emerald-300"
              >
                {emailAddress}
              </a>
              <a href={`tel:${phoneNumber}`} className="hover:text-emerald-300">
                +20 109 339 7961
              </a>
              <a
                href={socialLinks.github}
                target="_blank"
                rel="noreferrer"
                className="hover:text-emerald-300"
              >
                GitHub
              </a>
              <a
                href={socialLinks.linkedin}
                target="_blank"
                rel="noreferrer"
                className="hover:text-emerald-300"
              >
                LinkedIn
              </a>
              <a
                href={socialLinks.facebook}
                target="_blank"
                rel="noreferrer"
                className="hover:text-emerald-300"
              >
                Facebook
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/5 px-5 py-8 sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 text-xs font-medium text-slate-500 md:flex-row">
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
            <Link to="/support" className="hover:text-white">
              {t("profile.support")}
            </Link>
            <Link
              to="/contact"
              className="text-emerald-400 hover:text-emerald-300"
            >
              {t("profile.contact")}
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Contact;
