import { useStore } from "../store";
import { stanjaPo, hrBroj, todayStr } from "../logic";

function BankIcon({ name }: { name: string }) {
  const n = name.toLowerCase();
  if (n.includes("erste"))  return <ErsteIcon />;
  if (n.includes("pbz"))    return <PBZIcon />;
  if (n.includes("gotovina") || n.includes("cash")) return <CashIcon />;
  if (n.includes("revolut")) return <RevolutIcon />;
  return <DefaultBankIcon initials={name.slice(0, 2).toUpperCase()} />;
}

function ErsteIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <rect width="18" height="18" rx="4" fill="#E30613" fillOpacity="0.15"/>
      <text x="9" y="13" textAnchor="middle" fontSize="8" fontWeight="700" fill="#E30613" fontFamily="sans-serif">E</text>
    </svg>
  );
}

function PBZIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <rect width="18" height="18" rx="4" fill="#003087" fillOpacity="0.2"/>
      <text x="9" y="13" textAnchor="middle" fontSize="7" fontWeight="700" fill="#4a8edb" fontFamily="sans-serif">PBZ</text>
    </svg>
  );
}

function CashIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <rect width="18" height="18" rx="4" fill="#10b981" fillOpacity="0.12"/>
      <rect x="3" y="6" width="12" height="7" rx="1.5" stroke="#10b981" strokeWidth="1.3"/>
      <circle cx="9" cy="9.5" r="1.8" stroke="#10b981" strokeWidth="1.2"/>
    </svg>
  );
}

function RevolutIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <rect width="18" height="18" rx="4" fill="#7c5cfc" fillOpacity="0.15"/>
      <path d="M6 4h4.5a2.5 2.5 0 010 5H8m0 0l3.5 5" stroke="#8b5cf6" strokeWidth="1.4" strokeLinecap="round"/>
    </svg>
  );
}

function DefaultBankIcon({ initials }: { initials: string }) {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <rect width="18" height="18" rx="4" fill="#c96442" fillOpacity="0.12"/>
      <text x="9" y="13" textAnchor="middle" fontSize="7" fontWeight="700" fill="#c96442" fontFamily="sans-serif">{initials}</text>
    </svg>
  );
}

function WalletIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <rect x="1" y="4" width="14" height="10" rx="2" stroke="currentColor" strokeWidth="1.3"/>
      <path d="M1 7h14" stroke="currentColor" strokeWidth="1.3"/>
      <circle cx="11.5" cy="10.5" r="1" fill="currentColor"/>
      <path d="M4 4V3a2 2 0 012-2h4a2 2 0 012 2v1" stroke="currentColor" strokeWidth="1.3"/>
    </svg>
  );
}

export default function Danas() {
  const { data } = useStore();
  const stanja = stanjaPo(data.racuni, data.transakcije, todayStr());
  const ukupno = Object.values(stanja).reduce((s, v) => s + v, 0);

  return (
    <div className="p-5 md:p-8 max-w-lg">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-[#8a8a8a]"><WalletIcon /></span>
        <p className="text-[11px] font-medium text-[#8a8a8a] uppercase tracking-widest">
          Stanja po racunima
        </p>
      </div>

      <div className="rounded-xl overflow-hidden border border-white/[0.08] bg-[#262626]">
        {data.racuni.map((r, i) => {
          const val = stanja[r] ?? 0;
          return (
            <div
              key={r}
              className={`flex items-center justify-between px-4 py-3.5 ${
                i < data.racuni.length - 1 ? "border-b border-white/[0.06]" : ""
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-white/[0.04] border border-white/[0.08] flex items-center justify-center shrink-0">
                  <BankIcon name={r} />
                </div>
                <span className="text-[14px] text-[#ececec]">{r}</span>
              </div>
              <span className={`text-[14px] font-medium tabular-nums font-mono ${val < 0 ? "text-red-400" : "text-[#ececec]"}`}>
                {hrBroj(val)}
              </span>
            </div>
          );
        })}

        <div className={`flex items-center justify-between px-4 py-3.5 border-t ${ukupno < 0 ? "bg-red-500/[0.08] border-red-500/20" : "bg-emerald-500/[0.08] border-emerald-500/20"}`}>
          <div className="flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className={ukupno < 0 ? "text-red-400" : "text-emerald-400"}>
              <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            <span className={`text-[14px] font-semibold ${ukupno < 0 ? "text-red-400" : "text-emerald-400"}`}>Ukupno raspolozivo</span>
          </div>
          <span className={`text-[14px] font-semibold tabular-nums font-mono ${ukupno < 0 ? "text-red-400" : "text-emerald-400"}`}>
            {hrBroj(ukupno)}
          </span>
        </div>
      </div>
    </div>
  );
}
