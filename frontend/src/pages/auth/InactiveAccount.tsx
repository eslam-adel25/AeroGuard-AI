import { LogOut, ShieldOff } from "lucide-react";

interface InactiveAccountProps {
  onLogout: () => void;
}

const InactiveAccount = ({ onLogout }: InactiveAccountProps) => (
  <main className="flex min-h-screen items-center justify-center bg-[#0c0e12] px-6 text-white">
    <section className="w-full max-w-lg rounded-3xl border border-white/10 bg-[#16191f] p-8 text-center shadow-2xl">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-400/10 text-amber-300">
        <ShieldOff size={28} />
      </div>
      <div className="mt-6 text-sm font-semibold text-gray-300">AeroGuard AI</div>
      <h1 className="mt-4 text-2xl font-bold">Account currently inactive</h1>
      <p className="mt-3 text-sm leading-6 text-gray-400">
        This account cannot access the platform. Please contact customer
        service for assistance.
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

export default InactiveAccount;
