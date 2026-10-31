import { Clock3, LogOut, Shield } from "lucide-react";

interface ActivationPendingProps {
  onLogout: () => void;
}

const ActivationPending = ({ onLogout }: ActivationPendingProps) => (
  <main className="flex min-h-screen items-center justify-center bg-[#0c0e12] px-6 text-white">
    <section className="w-full max-w-lg rounded-3xl border border-white/10 bg-[#16191f] p-8 text-center shadow-2xl">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#adc6ff]/10 text-[#adc6ff]">
        <Clock3 size={28} />
      </div>
      <div className="mt-6 flex items-center justify-center gap-2 text-sm font-semibold text-gray-300">
        <Shield size={16} />
        AeroGuard AI
      </div>
      <h1 className="mt-4 text-2xl font-bold">Account activation pending</h1>
      <p className="mt-4 leading-8 text-gray-300" dir="rtl" lang="ar">
        سيتم التواصل معك من قبل خدمة العملاء خلال 24 ساعة لتفعيل حسابكم
      </p>
      <p className="mt-3 text-sm text-gray-400">
        Your email is verified. Platform access will be available after account
        activation.
      </p>
      <button
        type="button"
        onClick={onLogout}
        className="mt-8 inline-flex items-center gap-2 rounded-xl border border-white/10 px-5 py-3 text-sm font-semibold text-gray-200 transition hover:bg-white/5"
      >
        <LogOut size={16} />
        Log out
      </button>
    </section>
  </main>
);

export default ActivationPending;
