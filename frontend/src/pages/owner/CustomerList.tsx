import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Search, RefreshCw, ChevronLeft, ChevronRight } from "lucide-react";
import {
  ownerService,
  type OwnerCustomerSummary,
  type OwnerQueue,
} from "../../services/ownerService";

const headings: Record<OwnerQueue, { title: string; description: string }> = {
  unread: {
    title: "owner.sections.unread.title",
    description: "owner.sections.unread.description",
  },
  "under-review": {
    title: "owner.sections.underReview.title",
    description: "owner.sections.underReview.description",
  },
  customers: {
    title: "owner.sections.customers.title",
    description: "owner.sections.customers.description",
  },
};

const PAGE_SIZE = 25;

const formatDate = (value: string | null, language: string) =>
  value ? new Date(value).toLocaleDateString(language) : "—";

const accountStatusKey: Record<string, string> = {
  ACTIVE: "owner.status.active",
  INACTIVE: "owner.status.inactive",
  PENDING: "owner.status.pending",
};

const CustomerList = ({ queue }: { queue: OwnerQueue }) => {
  const { t, i18n } = useTranslation();
  const [customers, setCustomers] = useState<OwnerCustomerSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [submittedSearch, setSubmittedSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [errorKey, setErrorKey] = useState("");
  const section = headings[queue];

  const loadCustomers = useCallback(async () => {
    setLoading(true);
    setErrorKey("");
    try {
      const { data } = await ownerService.listCustomers(queue, {
        search: queue === "unread" ? undefined : submittedSearch || undefined,
        limit: PAGE_SIZE,
        offset,
      });
      setCustomers(data.items);
      setTotal(data.total);
    } catch (requestError) {
      console.error("Failed to load Owner customer list", requestError);
      setErrorKey("owner.customersLoadFailed");
    } finally {
      setLoading(false);
    }
  }, [offset, queue, submittedSearch]);

  useEffect(() => {
    void loadCustomers();
  }, [loadCustomers]);

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setOffset(0);
    setSubmittedSearch(search.trim());
  };

  return (
    <section className="mx-auto max-w-6xl">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-[#adc6ff]">{t("owner.workflow")}</p>
          <h1 className="mt-2 text-3xl font-semibold">{t(section.title)}</h1>
          <p className="mt-2 text-sm text-gray-400">{t(section.description)}</p>
        </div>
        {queue !== "unread" && (
          <form onSubmit={submitSearch} className="flex gap-2">
            <label className="sr-only" htmlFor="customer-search">
              {t("owner.searchLabel")}
            </label>
            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-[#15191f] px-3">
              <Search size={16} className="text-gray-500" />
              <input
                id="customer-search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={t("owner.searchPlaceholder")}
                className="w-44 bg-transparent py-2.5 text-sm outline-none placeholder:text-gray-600"
              />
            </div>
            <button type="submit" className="rounded-xl bg-[#adc6ff] px-4 text-sm font-semibold text-[#111722]">
              {t("owner.search")}
            </button>
          </form>
        )}
      </div>

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-[#111419]">
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
          <p className="text-sm text-gray-400">
            {t("owner.customerCount", { count: total })}
          </p>
          <button type="button" onClick={() => void loadCustomers()} disabled={loading} className="text-gray-400 hover:text-white disabled:opacity-50" aria-label={t("owner.refresh")} title={t("owner.refresh")}>
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
        {errorKey ? (
          <div className="p-8 text-center">
            <p className="text-sm text-red-300">{t(errorKey)}</p>
            <button type="button" onClick={() => void loadCustomers()} className="mt-3 text-sm text-[#adc6ff]">{t("owner.retry")}</button>
          </div>
        ) : loading ? (
          <p className="p-10 text-center text-sm text-gray-400">{t("owner.loadingCustomers")}</p>
        ) : customers.length === 0 ? (
          <p className="p-10 text-center text-sm text-gray-400">{t("owner.noCustomers")}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left text-sm">
              <thead className="bg-white/[0.03] text-xs uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="px-5 py-3 font-medium">{t("owner.table.customer")}</th>
                  <th className="px-5 py-3 font-medium">{t("owner.table.phone")}</th>
                  <th className="px-5 py-3 font-medium">{t("owner.table.organization")}</th>
                  <th className="px-5 py-3 font-medium">{t("owner.table.registered")}</th>
                  <th className="px-5 py-3 font-medium">{t("owner.table.status")}</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.06]">
                {customers.map((customer) => (
                  <tr key={customer.customer_profile_id} className="hover:bg-white/[0.025]">
                    <td className="px-5 py-4">
                      <p className="font-medium">{customer.full_name}</p>
                      <p className="mt-1 text-xs text-gray-500">
                        {t(customer.is_verified ? "owner.emailVerified" : "owner.emailNotVerified")}
                      </p>
                    </td>
                    <td className="px-5 py-4 text-gray-300">{customer.phone || "—"}</td>
                    <td className="px-5 py-4 text-gray-300">{customer.organization || "—"}</td>
                    <td className="px-5 py-4 text-gray-300">{formatDate(customer.registration_date, i18n.language)}</td>
                    <td className="px-5 py-4">
                      <span className={`rounded-full px-2.5 py-1 text-xs ${customer.account_status === "ACTIVE" ? "bg-emerald-500/10 text-emerald-300" : customer.account_status === "INACTIVE" ? "bg-rose-500/10 text-rose-300" : "bg-amber-500/10 text-amber-300"}`}>
                        {t(accountStatusKey[customer.account_status] ?? "owner.status.pending")}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      <Link className="font-medium text-[#adc6ff] hover:underline" to={`/owner/customers/${customer.customer_profile_id}`}>
                        {t("owner.open")}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!loading && total > PAGE_SIZE && (
          <div className="flex items-center justify-end gap-3 border-t border-white/10 px-5 py-3">
            <button type="button" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={offset === 0} className="rounded-lg p-2 text-gray-300 hover:bg-white/5 disabled:opacity-30" aria-label={t("owner.previousPage")} title={t("owner.previousPage")}>
              <ChevronLeft size={18} />
            </button>
            <span className="text-xs text-gray-500">
              {t("owner.pagination", {
                from: offset + 1,
                to: Math.min(offset + PAGE_SIZE, total),
                total,
              })}
            </span>
            <button type="button" onClick={() => setOffset(offset + PAGE_SIZE)} disabled={offset + PAGE_SIZE >= total} className="rounded-lg p-2 text-gray-300 hover:bg-white/5 disabled:opacity-30" aria-label={t("owner.nextPage")} title={t("owner.nextPage")}>
              <ChevronRight size={18} />
            </button>
          </div>
        )}
      </div>
    </section>
  );
};

export default CustomerList;
