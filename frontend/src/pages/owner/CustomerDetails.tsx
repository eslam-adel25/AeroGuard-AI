import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { useTranslation } from "react-i18next";
import { ArrowLeft, Loader2, Save } from "lucide-react";
import { useNotification } from "../../components/NotificationSystem/useNotification";
import {
  ownerService,
  type OwnerCustomerActivation,
  type OwnerCustomerConfiguration,
  type OwnerCustomerDetails as CustomerDetailsData,
} from "../../services/ownerService";

interface ConfigurationForm {
  max_camera_count: string;
  owner_notes: string;
}

const toForm = (customer: CustomerDetailsData): ConfigurationForm => ({
  max_camera_count:
    customer.max_camera_count === null ? "" : String(customer.max_camera_count),
  owner_notes: customer.owner_notes ?? "",
});

const formatDate = (value: string | null, language: string) =>
  value ? new Date(value).toLocaleString(language) : "—";

const workflowStatusKey: Record<string, string> = {
  AWAITING_EMAIL_VERIFICATION: "owner.status.awaitingEmailVerification",
  UNREAD: "owner.status.unread",
  UNDER_REVIEW: "owner.status.underReview",
  PLATFORM_CUSTOMER: "owner.status.platformCustomer",
};

const accountStatusKey: Record<string, string> = {
  PENDING: "owner.status.pending",
  ACTIVE: "owner.status.active",
  INACTIVE: "owner.status.inactive",
};

const requestErrorKey: Record<string, string> = {
  "Customer profile not found": "owner.errors.profileNotFound",
  "Unable to save customer changes": "owner.errors.changesSaveFailed",
  "Request cannot move to review": "owner.errors.moveToReviewFailed",
  "Customer cannot be activated": "owner.errors.activationFailed",
  "Customer is not pending": "owner.errors.customerNotPending",
  "Customer email is not verified": "owner.errors.emailNotVerified",
  "Maximum camera count must be configured":
    "owner.errors.cameraCountRequired",
  "Maximum camera count is invalid": "owner.errors.cameraCountInvalid",
  "Customer is not active": "owner.errors.customerNotActive",
  "Customer is not inactive": "owner.errors.customerNotInactive",
};

const CustomerDetails = () => {
  const { t, i18n } = useTranslation();
  const { customerProfileId = "" } = useParams();
  const navigate = useNavigate();
  const { confirm, toast } = useNotification();
  const requestSequence = useRef(0);
  const currentProfileId = useRef(customerProfileId);
  const [customer, setCustomer] = useState<CustomerDetailsData | null>(null);
  const [loadedProfileId, setLoadedProfileId] = useState<string | null>(null);
  const [form, setForm] = useState<ConfigurationForm | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [transitioning, setTransitioning] = useState(false);
  const [errorKey, setErrorKey] = useState("");
  const [errorProfileId, setErrorProfileId] = useState<string | null>(null);

  useLayoutEffect(() => {
    currentProfileId.current = customerProfileId;
  }, [customerProfileId]);

  const load = useCallback(async () => {
    const profileId = customerProfileId;
    const sequence = ++requestSequence.current;
    setLoading(true);
    setErrorKey("");
    setErrorProfileId(null);
    setCustomer(null);
    setLoadedProfileId(null);
    setForm(null);
    setSaving(false);
    setTransitioning(false);
    try {
      const customerResponse = await ownerService.getCustomer(profileId);
      if (
        sequence !== requestSequence.current ||
        currentProfileId.current !== profileId
      ) {
        return;
      }
      setCustomer(customerResponse.data);
      setLoadedProfileId(profileId);
      setForm(toForm(customerResponse.data));
    } catch (requestError) {
      if (
        sequence !== requestSequence.current ||
        currentProfileId.current !== profileId
      ) {
        return;
      }
      console.error("Failed to load Owner customer details", requestError);
      setCustomer(null);
      setLoadedProfileId(null);
      setForm(null);
      setErrorKey("owner.customerLoadFailed");
      setErrorProfileId(profileId);
    } finally {
      if (
        sequence === requestSequence.current &&
        currentProfileId.current === profileId
      ) {
        setLoading(false);
      }
    }
  }, [customerProfileId]);

  useEffect(() => {
    void load();
    return () => {
      requestSequence.current += 1;
    };
  }, [load]);

  const updateForm = <K extends keyof ConfigurationForm>(
    key: K,
    value: ConfigurationForm[K],
  ) => setForm((current) => (current ? { ...current, [key]: value } : current));

  const saveConfiguration = async (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    if (!form) return;
    const cameraLimit =
      form.max_camera_count.trim() === ""
        ? null
        : Number(form.max_camera_count);
    if (
      cameraLimit !== null &&
      (!Number.isInteger(cameraLimit) || cameraLimit < 0)
    ) {
      setErrorKey("owner.errors.maximumCameras");
      return;
    }
    setSaving(true);
    setErrorKey("");
    const profileId = customerProfileId;
    const sequence = requestSequence.current;
    try {
      const configuration: OwnerCustomerConfiguration = {
        max_camera_count: cameraLimit,
        owner_notes: form.owner_notes.trim() || null,
      };
      const { data } = await ownerService.updateConfiguration(
        profileId,
        configuration,
      );
      if (
        sequence !== requestSequence.current ||
        currentProfileId.current !== profileId
      ) {
        return;
      }
      setCustomer(data);
      setForm(toForm(data));
      toast.success(
        t("owner.success.configurationSaved"),
        t("owner.success.configurationUpdated"),
      );
    } catch (requestError) {
      if (
        sequence !== requestSequence.current ||
        currentProfileId.current !== profileId
      ) {
        return;
      }
      console.error("Failed to save customer configuration", requestError);
      setErrorKey(
        getRequestMessageKey(requestError, "owner.errors.configurationSaveFailed"),
      );
    } finally {
      if (
        sequence === requestSequence.current &&
        currentProfileId.current === profileId
      ) {
        setSaving(false);
      }
    }
  };

  const runTransition = (
    action: "under-review" | "activate" | "deactivate" | "reactivate",
  ) => {
    if (!form) return;
    const profileId = customerProfileId;
    const sequence = requestSequence.current;
    const customerName = customer?.full_name;
    const activation: OwnerCustomerActivation | undefined =
      action === "activate"
        ? { max_camera_count: Number(form.max_camera_count) }
        : undefined;
    const actionLabelKey =
      action === "under-review"
        ? "owner.actions.moveToReview"
        : `owner.actions.${action}`;
    const confirmationKey =
      action === "under-review" ? "owner.confirm.moveToReview" : `owner.confirm.${action}`;
    const confirmationTitleKey =
      action === "under-review"
        ? "owner.confirm.moveToReviewTitle"
        : `owner.confirm.${action}Title`;
    const successKey =
      action === "under-review"
        ? "owner.success.movedToReview"
        : `owner.success.${action === "activate" ? "activated" : `${action}d`}`;
    const actionLabel = t(actionLabelKey);
    confirm({
      title: t(confirmationTitleKey),
      description: t(confirmationKey, { name: customerName }),
      confirmLabel: actionLabel,
      cancelLabel: t("common.cancel"),
      type: action === "deactivate" ? "danger" : "info",
      onConfirm: async () => {
        if (
          sequence !== requestSequence.current ||
          currentProfileId.current !== profileId
        ) {
          return;
        }
        setTransitioning(true);
        setErrorKey("");
        try {
          const { data } = await ownerService.transition(
            profileId,
            action,
            activation,
          );
          if (
            sequence !== requestSequence.current ||
            currentProfileId.current !== profileId
          ) {
            return;
          }
          setCustomer(data);
          setForm(toForm(data));
          toast.success(t("owner.success.customerUpdated"), t(successKey));
          if (action === "under-review") {
            navigate("/owner/requests/under-review", { replace: true });
          } else if (action === "activate") {
            navigate("/owner/customers", { replace: true });
          }
        } catch (requestError) {
          if (
            sequence !== requestSequence.current ||
            currentProfileId.current !== profileId
          ) {
            return;
          }
          console.error("Failed to update customer workflow", requestError);
          setErrorKey(
            getRequestMessageKey(requestError, "owner.errors.customerUpdateFailed"),
          );
        } finally {
          if (
            sequence === requestSequence.current &&
            currentProfileId.current === profileId
          ) {
            setTransitioning(false);
          }
        }
      },
    });
  };

  const isCurrentCustomerLoaded = loadedProfileId === customerProfileId;
  const currentError =
    errorProfileId === customerProfileId ? errorKey : "";

  if (loading || (!isCurrentCustomerLoaded && !currentError)) {
    return (
      <p className="py-16 text-center text-sm text-gray-400">
        {t("owner.loadingCustomer")}
      </p>
    );
  }
  if (currentError) {
    return (
      <div className="mx-auto max-w-3xl rounded-2xl border border-white/10 bg-[#111419] p-8 text-center">
        <p className="text-sm text-red-300">{t(currentError)}</p>
        <button type="button" onClick={() => void load()} className="mt-4 text-sm text-[#adc6ff]">{t("owner.retry")}</button>
      </div>
    );
  }
  if (!isCurrentCustomerLoaded || !customer || !form) return null;

  const canActivate =
    customer.is_verified &&
    form.max_camera_count.trim() !== "" &&
    Number.isInteger(Number(form.max_camera_count)) &&
    Number(form.max_camera_count) >= 0;

  return (
    <section className="mx-auto max-w-5xl">
      <Link to="/owner/requests/unread" className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white">
        <ArrowLeft size={16} /> {t("owner.details.customerWorkflow")}
      </Link>
      <div className="mt-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">{customer.full_name}</h1>
          <p className="mt-2 text-sm text-gray-400">
            {t(workflowStatusKey[customer.workflow_status] ?? "owner.status.unread")} ·{" "}
            {t(accountStatusKey[customer.account_status] ?? "owner.status.pending")}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {customer.workflow_status === "UNREAD" && (
            <button type="button" disabled={transitioning || !customer.is_verified} onClick={() => runTransition("under-review")} className="rounded-xl border border-white/10 px-4 py-2.5 text-sm font-medium hover:bg-white/5 disabled:opacity-40">
              {t("owner.details.moveToReview")}
            </button>
          )}
          {customer.account_status === "PENDING" && (
            <button type="button" disabled={transitioning || !canActivate} onClick={() => runTransition("activate")} className="rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-[#07120d] hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40">
              {transitioning ? <Loader2 className="animate-spin" size={16} /> : t("owner.details.activate")}
            </button>
          )}
          {customer.account_status === "ACTIVE" && (
            <button type="button" disabled={transitioning} onClick={() => runTransition("deactivate")} className="rounded-xl border border-rose-400/30 px-4 py-2.5 text-sm font-medium text-rose-300 hover:bg-rose-500/10 disabled:opacity-40">
              {t("owner.details.deactivate")}
            </button>
          )}
          {customer.account_status === "INACTIVE" && (
            <button type="button" disabled={transitioning} onClick={() => runTransition("reactivate")} className="rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-[#07120d] hover:bg-emerald-400 disabled:opacity-40">
              {t("owner.details.reactivate")}
            </button>
          )}
        </div>
      </div>

      {errorKey && <p role="alert" className="mt-5 rounded-xl border border-red-400/20 bg-red-500/5 p-3 text-sm text-red-300">{t(errorKey)}</p>}

      <div className="mt-7 grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <section className="h-fit rounded-2xl border border-white/10 bg-[#111419] p-5">
          <h2 className="text-lg font-semibold">{t("owner.details.customerDetails")}</h2>
          <dl className="mt-5 space-y-4 text-sm">
            <Detail label={t("owner.details.username")} value={customer.username} />
            <Detail label={t("owner.details.email")} value={customer.email} />
            <Detail label={t("owner.details.password")} value={customer.password} />
            <Detail label={t("owner.details.phone")} value={customer.phone || "—"} />
            <Detail label={t("owner.details.organization")} value={customer.organization || "—"} />
            <Detail label={t("owner.details.registrationDate")} value={formatDate(customer.registration_date, i18n.language)} />
            <Detail label={t("owner.details.lastUpdated")} value={formatDate(customer.last_updated, i18n.language)} />
            <Detail label={t("owner.details.emailVerification")} value={t(customer.is_verified ? "owner.status.verified" : "owner.status.notVerified")} />
          </dl>
        </section>

        <form noValidate onSubmit={(event) => void saveConfiguration(event)} className="rounded-2xl border border-white/10 bg-[#111419] p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold">{t("owner.details.platformConfiguration")}</h2>
              <p className="mt-1 text-xs text-gray-500">{t("owner.details.configurationDescription")}</p>
            </div>
            <button type="submit" disabled={saving} className="inline-flex items-center gap-2 rounded-xl bg-[#adc6ff] px-4 py-2.5 text-sm font-semibold text-[#111722] disabled:opacity-50">
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              {saving ? t("owner.details.saving") : t("owner.details.save")}
            </button>
          </div>

          <label className="mt-6 block text-sm font-medium" htmlFor="camera-limit">{t("owner.details.maximumCameraCount")}</label>
          <input
            id="camera-limit"
            type="number"
            min="0"
            step="1"
            value={form.max_camera_count}
            onChange={(event) => updateForm("max_camera_count", event.target.value)}
            placeholder={t("owner.details.notConfigured")}
            className="mt-2 w-full rounded-xl border border-white/10 bg-[#0c0e12] px-3 py-2.5 text-sm outline-none focus:border-[#adc6ff]/50"
          />

          <label className="mt-5 block text-sm font-medium" htmlFor="owner-notes">{t("owner.details.privateOwnerNotes")}</label>
          <textarea
            id="owner-notes"
            rows={4}
            maxLength={4000}
            value={form.owner_notes}
            onChange={(event) => updateForm("owner_notes", event.target.value)}
            className="mt-2 w-full resize-y rounded-xl border border-white/10 bg-[#0c0e12] px-3 py-2.5 text-sm outline-none focus:border-[#adc6ff]/50"
          />
          {customer.account_status === "PENDING" && !canActivate && (
            <p className="mt-3 text-xs text-amber-300">
              {t("owner.details.activationRequirement")}
            </p>
          )}
        </form>
      </div>
    </section>
  );
};

const Detail = ({ label, value }: { label: string; value: string }) => (
  <div className="flex flex-col gap-1 border-b border-white/[0.06] pb-3 last:border-0 last:pb-0 sm:flex-row sm:justify-between sm:gap-4">
    <dt className="text-gray-500">{label}</dt>
    <dd dir="ltr" className="break-all text-gray-200 sm:text-right">{value}</dd>
  </div>
);

const getRequestMessageKey = (
  error: unknown,
  fallbackKey: string,
) => {
  if (axios.isAxiosError<{ detail?: string }>(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") {
      return requestErrorKey[detail] ?? fallbackKey;
    }
  }
  return fallbackKey;
};

export default CustomerDetails;
