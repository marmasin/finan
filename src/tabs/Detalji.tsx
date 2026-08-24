import { useMemo, useState } from "react";
import { useStore } from "../store";
import { preracunajTablicu, hrBroj, parseDate } from "../logic";
import { Transakcija } from "../types";

const TIP_COLOR: Record<Transakcija["tip"], string> = {
  Prihod: "text-emerald-400",
  Rashod: "text-red-400",
  Stanje: "text-[#8a8a8a]",
};

const TIP_BG: Record<Transakcija["tip"], string> = {
  Prihod: "bg-emerald-500/10 text-emerald-400",
  Rashod: "bg-red-500/10 text-red-400",
  Stanje: "bg-white/[0.06] text-[#8a8a8a]",
};

// buducnost=false → rows up to today (path to current balance)
// buducnost=true  → rows after today (future entries only)
type Mode = "sve" | "proslost" | "buducnost";

export default function Detalji() {
  const { data } = useStore();
  const [mode, setMode] = useState<Mode>("sve");

  const allRows = useMemo(
    () => preracunajTablicu(data.racuni, data.transakcije),
    [data.racuni, data.transakcije]
  );

  const todayTs = new Date().setHours(0, 0, 0, 0);

  const rows = useMemo(() => {
    if (mode === "sve") return allRows;
    return allRows.filter(r => {
      const ts = parseDate(r.datum).getTime();
      return mode === "proslost" ? ts <= todayTs : ts > todayTs;
    });
  }, [allRows, mode, todayTs]);

  const btnCls = (m: Mode) =>
    `px-3 py-1 rounded-lg text-[12px] font-medium transition-colors ${
      mode === m
        ? "bg-emerald-500/15 text-emerald-400"
        : "text-[#8a8a8a] hover:bg-white/[0.06] hover:text-[#ececec]"
    }`;

  return (
    <div className="flex-1 overflow-auto">
      <div className="flex items-center justify-between px-5 md:px-6 py-3 border-b border-white/[0.06] sticky top-0 bg-[#1a1a1a] z-10">
        <p className="text-[11px] font-medium text-[#8a8a8a] uppercase tracking-widest">
          Revizijski trag &mdash; {rows.length} stavki
        </p>
        <div className="flex items-center gap-1 bg-white/[0.04] rounded-lg p-0.5">
          <button className={btnCls("sve")} onClick={() => setMode("sve")}>Sve</button>
          <button className={btnCls("proslost")} onClick={() => setMode("proslost")}>Proslost</button>
          <button className={btnCls("buducnost")} onClick={() => setMode("buducnost")}>Buducnost</button>
        </div>
      </div>
      <table className="w-full text-[13px] min-w-[900px]">
        <thead className="sticky top-[49px] bg-[#1a1a1a] z-10">
          <tr className="border-b border-white/[0.06]">
            {["Datum", "Opis", "Tip", "Iznos", "Izvor"].map((h) => (
              <th key={h} className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wider whitespace-nowrap text-[#8a8a8a]">
                {h}
              </th>
            ))}
            {data.racuni.map((racun) => (
              <th key={racun} className="px-4 py-3 text-right text-[11px] font-medium uppercase tracking-wider whitespace-nowrap">
                <span className="inline-flex items-center gap-1.5 bg-[#c96442]/[0.08] border border-[#c96442]/20 text-[#c96442]/80 px-2 py-0.5 rounded-md">
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <rect x="0.5" y="2" width="9" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.1"/>
                    <path d="M0.5 4.5h9" stroke="currentColor" strokeWidth="1.1"/>
                  </svg>
                  {racun}
                </span>
              </th>
            ))}
            <th className="px-4 py-3 text-right text-[11px] font-medium uppercase tracking-wider whitespace-nowrap">
              <span className="inline-flex items-center gap-1.5 bg-emerald-500/[0.1] border border-emerald-500/25 text-emerald-400 px-2 py-0.5 rounded-md">
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                  <path d="M5 1v8M1 5h8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
                </svg>
                UKUPNO
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const isFuture = parseDate(row.datum).getTime() > todayTs;
            return (
              <tr
                key={row.id}
                className={`border-b border-white/[0.04] last:border-0 ${
                  isFuture ? "opacity-60" : ""
                } ${i % 2 === 0 ? "" : "bg-white/[0.02]"}`}
              >
                <td className="px-4 py-2.5 font-mono text-[12px] text-[#8a8a8a] whitespace-nowrap">{row.datum}</td>
                <td className="px-4 py-2.5 text-[#ececec] max-w-[180px] truncate">{row.opis}</td>
                <td className="px-4 py-2.5">
                  <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${TIP_BG[row.tip]}`}>
                    {row.tip}
                  </span>
                </td>
                <td className={`px-4 py-2.5 font-mono tabular-nums text-right whitespace-nowrap text-[13px] ${TIP_COLOR[row.tip]}`}>
                  {row.tip === "Rashod" ? "-" : row.tip === "Prihod" ? "+" : ""}
                  {hrBroj(row.iznos)}
                </td>
                <td className="px-4 py-2.5 text-[13px]">
                  <span className="inline-flex items-center gap-1.5 text-[#8a8a8a]">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                      <rect x="0.5" y="2.5" width="11" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.1"/>
                      <path d="M0.5 5.5h11" stroke="currentColor" strokeWidth="1.1"/>
                    </svg>
                    {row.racun}
                  </span>
                </td>
                {data.racuni.map((r) => (
                  <td
                    key={r}
                    className={`px-4 py-2.5 font-mono tabular-nums text-right whitespace-nowrap text-[13px] ${
                      r === row.racun ? "text-[#ececec] font-medium" : "text-[#555]"
                    }`}
                  >
                    {hrBroj(row.stanja[r] ?? 0)}
                  </td>
                ))}
                <td className="px-4 py-2.5 font-mono tabular-nums text-right text-emerald-400 font-semibold whitespace-nowrap text-[13px]">
                  {hrBroj(row.raspoloziv)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
