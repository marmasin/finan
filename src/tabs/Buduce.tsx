import { useState } from "react";
import { useStore } from "../store";
import { goalProgress, hrBroj, parseDate, stanjaPo, todayStr, STATUS_ICON } from "../logic";
import { Cilj } from "../types";
import Modal from "../components/Modal";

function GoalCard({ cilj, onEdit }: { cilj: Cilj; onEdit: () => void }) {
  const { data } = useStore();
  const prog = goalProgress(cilj, data.racuni, data.transakcije);
  const isOk = prog.status === "ostvaren" || prog.status === "na putu";

  return (
    <div className="bg-[#262626] border border-white/[0.08] rounded-xl p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-base">{STATUS_ICON[prog.status]}</span>
          <div>
            <p className="text-[14px] font-medium text-[#ececec]">{cilj.racun}</p>
            {cilj.napomena && (
              <p className="text-[12px] text-[#8a8a8a]">{cilj.napomena}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[12px] text-[#8a8a8a] font-mono">{cilj.rok}</span>
          <button
            onClick={onEdit}
            className="text-[12px] text-[#8a8a8a] hover:text-[#c96442] transition-colors"
          >
            Uredi
          </button>
        </div>
      </div>

      <div className="flex items-center gap-6 mb-3">
        <div>
          <p className="text-[11px] text-[#8a8a8a] uppercase tracking-wider mb-0.5">Cilj</p>
          <p className="text-[13px] font-medium font-mono tabular-nums text-[#ececec]">{hrBroj(cilj.iznos)}</p>
        </div>
        <div>
          <p className="text-[11px] text-[#8a8a8a] uppercase tracking-wider mb-0.5">Projekcija</p>
          <p className={`text-[13px] font-medium font-mono tabular-nums ${isOk ? "text-emerald-400" : "text-red-400"}`}>
            {hrBroj(prog.projekcija)}
          </p>
        </div>
        <div>
          <p className="text-[11px] text-[#8a8a8a] uppercase tracking-wider mb-0.5">{prog.dana >= 0 ? "Dana" : "Proslo"}</p>
          <p className="text-[13px] font-medium font-mono tabular-nums text-[#ececec]">{Math.abs(prog.dana)}</p>
        </div>
        {!isOk && prog.dana > 0 && (
          <div>
            <p className="text-[11px] text-[#8a8a8a] uppercase tracking-wider mb-0.5">Nedostaje/mj</p>
            <p className="text-[13px] font-medium font-mono tabular-nums text-red-400">{hrBroj(prog.mjesecno)}</p>
          </div>
        )}
      </div>

      {cilj.iznos > 0 && (
        <>
          <div className="w-full bg-white/[0.08] rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${isOk ? "bg-emerald-500" : "bg-[#c96442]"}`}
              style={{ width: `${prog.postotak}%` }}
            />
          </div>
          <p className="text-[11px] text-[#8a8a8a] mt-1 text-right">{prog.postotak.toFixed(1)}%</p>
        </>
      )}
    </div>
  );
}

function AccountProj({ racun, todayBal, futureRows }: {
  racun: string;
  todayBal: number;
  futureRows: { datum: string; opis: string; tip: string; iznos: number; running: number }[];
}) {
  const [open, setOpen] = useState(false);
  const projected = futureRows.length > 0 ? futureRows[futureRows.length - 1].running : todayBal;
  const delta = projected - todayBal;

  return (
    <div className="bg-[#262626] border border-white/[0.08] rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-4 py-3.5 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-full bg-[#c96442]/10 flex items-center justify-center text-[11px] font-semibold text-[#c96442]">
            {racun.slice(0, 2).toUpperCase()}
          </div>
          <span className="text-[14px] text-[#ececec]">{racun}</span>
          <span className="text-[12px] text-[#8a8a8a]">{futureRows.length} stavki</span>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-[12px] font-medium px-2 py-0.5 rounded-full ${
            delta >= 0 ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
          }`}>
            {delta >= 0 ? "+" : ""}{hrBroj(delta)}
          </span>
          <span className="text-[14px] font-medium font-mono tabular-nums text-[#ececec]">{hrBroj(projected)}</span>
          <span className="text-[#8a8a8a] text-[12px]">{open ? "^" : "v"}</span>
        </div>
      </button>

      {open && futureRows.length > 0 && (
        <div className="border-t border-white/[0.06]">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="bg-white/[0.03]">
                {["Datum", "Opis", "Tip", "Iznos", "Stanje"].map(h => (
                  <th key={h} className="px-4 py-2.5 text-left text-[11px] text-[#8a8a8a] uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {futureRows.map((t, i) => (
                <tr key={i} className="border-t border-white/[0.04]">
                  <td className="px-4 py-2.5 font-mono text-[12px] text-[#8a8a8a]">{t.datum}</td>
                  <td className="px-4 py-2.5 text-[#ececec]">{t.opis}</td>
                  <td className="px-4 py-2.5">
                    <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${
                      t.tip === "Prihod" ? "bg-emerald-500/10 text-emerald-400"
                      : t.tip === "Rashod" ? "bg-red-500/10 text-red-400"
                      : "bg-white/[0.06] text-[#8a8a8a]"
                    }`}>{t.tip}</span>
                  </td>
                  <td className={`px-4 py-2.5 font-mono tabular-nums text-right ${t.tip === "Rashod" ? "text-red-400" : "text-emerald-400"}`}>
                    {t.tip === "Rashod" ? "-" : t.tip === "Prihod" ? "+" : ""}{hrBroj(t.iznos)}
                  </td>
                  <td className="px-4 py-2.5 font-mono tabular-nums text-right text-[#ececec]">{hrBroj(t.running)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function Buduce() {
  const { data, addCilj, editCilj, deleteCilj } = useStore();
  const [showCiljDialog, setShowCiljDialog] = useState(false);
  const [editingCilj, setEditingCilj] = useState<Cilj | null>(null);
  const [form, setForm] = useState({ racun: data.racuni[0] ?? "UKUPNO", rok: "", iznos: "", napomena: "" });

  function openAdd() {
    setEditingCilj(null);
    setForm({ racun: data.racuni[0] ?? "UKUPNO", rok: "", iznos: "", napomena: "" });
    setShowCiljDialog(true);
  }

  function openEdit(c: Cilj) {
    setEditingCilj(c);
    setForm({ racun: c.racun, rok: c.rok, iznos: String(c.iznos), napomena: c.napomena });
    setShowCiljDialog(true);
  }

  function submitCilj() {
    const iznos = parseFloat(form.iznos.replace(",", ".")) || 0;
    if (!form.rok) return;
    if (editingCilj) editCilj(editingCilj.id, { racun: form.racun, rok: form.rok, iznos, napomena: form.napomena });
    else addCilj({ racun: form.racun, rok: form.rok, iznos, napomena: form.napomena });
    setShowCiljDialog(false);
  }

  const todayBalances = stanjaPo(data.racuni, data.transakcije, todayStr());
  const todayTs = new Date().setHours(0, 0, 0, 0);

  const projections = data.racuni.map((racun) => {
    const futureTx = data.transakcije
      .filter((t) => {
        const [d, m, y] = t.datum.split(".").map(Number);
        return t.racun === racun && new Date(y, m - 1, d).getTime() > todayTs;
      })
      .sort((a, b) => parseDate(a.datum).getTime() - parseDate(b.datum).getTime());

    let running = todayBalances[racun] ?? 0;
    const withRunning = futureTx.map((t) => {
      if (t.tip === "Stanje") running = t.iznos;
      else if (t.tip === "Prihod") running += t.iznos;
      else running -= t.iznos;
      return { datum: t.datum, opis: t.opis, tip: t.tip, iznos: t.iznos, running };
    });

    return { racun, todayBal: todayBalances[racun] ?? 0, futureRows: withRunning };
  });

  const totalToday = Object.values(todayBalances).reduce((s, v) => s + v, 0);
  const totalProjected = projections.reduce((s, p) =>
    s + (p.futureRows.length > 0 ? p.futureRows[p.futureRows.length - 1].running : p.todayBal), 0);

  const inputCls = "w-full bg-[#1a1a1a] border border-white/[0.1] rounded-lg px-3 py-2.5 text-[14px] text-[#ececec] focus:outline-none focus:border-[#c96442] transition-colors placeholder-[#555]";

  return (
    <div className="p-5 md:p-8 space-y-8 max-w-3xl">
      {/* Goals */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <p className="text-[11px] font-medium text-[#8a8a8a] uppercase tracking-widest">Ciljevi</p>
          <button
            onClick={openAdd}
            className="text-[13px] font-medium text-[#c96442] hover:text-[#e8956d] transition-colors"
          >
            + Postavi cilj
          </button>
        </div>
        {data.ciljevi.length === 0 ? (
          <p className="text-[14px] text-[#8a8a8a]">Nema postavljenih ciljeva.</p>
        ) : (
          <div className="space-y-3">
            {data.ciljevi.map((c) => (
              <GoalCard key={c.id} cilj={c} onEdit={() => openEdit(c)} />
            ))}
          </div>
        )}
      </section>

      {/* Projections — only accounts that have future transactions */}
      <section>
        <p className="text-[11px] font-medium text-[#8a8a8a] uppercase tracking-widest mb-4">Buduce stavke po racunima</p>
        <div className="space-y-2">
          {projections.filter(p => p.futureRows.length > 0).map((p) => (
            <AccountProj key={p.racun} {...p} />
          ))}
        </div>

        <div className="mt-3 bg-[#c96442]/[0.08] border border-[#c96442]/20 rounded-xl px-4 py-3.5 flex items-center justify-between">
          <span className="text-[14px] font-semibold text-[#c96442]">Ukupno raspolozivo</span>
          <div className="flex items-center gap-3">
            <span className={`text-[12px] font-medium px-2 py-0.5 rounded-full ${
              totalProjected - totalToday >= 0 ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
            }`}>
              {totalProjected - totalToday >= 0 ? "+" : ""}{hrBroj(totalProjected - totalToday)}
            </span>
            <span className="text-[15px] font-semibold font-mono tabular-nums text-[#c96442]">{hrBroj(totalProjected)}</span>
          </div>
        </div>
      </section>

      {/* Goal Dialog */}
      {showCiljDialog && (
        <Modal title={editingCilj ? "Uredi cilj" : "Postavi cilj"} onClose={() => setShowCiljDialog(false)}>
          <div className="space-y-4">
            <label className="block">
              <span className="text-[12px] font-medium text-[#8a8a8a] uppercase tracking-wider mb-2 block">Izvor</span>
              <select value={form.racun} onChange={(e) => setForm({ ...form, racun: e.target.value })} className={inputCls}>
                <option value="UKUPNO">UKUPNO (svi racuni)</option>
                {data.racuni.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="text-[12px] font-medium text-[#8a8a8a] uppercase tracking-wider mb-2 block">Ciljani iznos (EUR)</span>
              <input type="number" value={form.iznos} onChange={(e) => setForm({ ...form, iznos: e.target.value })} placeholder="0.00" className={inputCls} />
            </label>
            <label className="block">
              <span className="text-[12px] font-medium text-[#8a8a8a] uppercase tracking-wider mb-2 block">Rok (DD.MM.YYYY)</span>
              <input type="text" value={form.rok} onChange={(e) => setForm({ ...form, rok: e.target.value })} placeholder="31.12.2026" className={inputCls} />
            </label>
            <label className="block">
              <span className="text-[12px] font-medium text-[#8a8a8a] uppercase tracking-wider mb-2 block">Napomena (opcionalno)</span>
              <input type="text" value={form.napomena} onChange={(e) => setForm({ ...form, napomena: e.target.value })} className={inputCls} />
            </label>
            <div className="flex gap-2 pt-1">
              <button onClick={submitCilj} className="flex-1 bg-[#c96442] text-white text-[14px] font-semibold py-2.5 rounded-lg hover:bg-[#b5573a] transition-colors">
                {editingCilj ? "Spremi promjene" : "Snimi cilj"}
              </button>
              {editingCilj && (
                <button onClick={() => { deleteCilj(editingCilj.id); setShowCiljDialog(false); }} className="px-4 bg-red-500/10 text-red-400 text-[14px] font-semibold py-2.5 rounded-lg hover:bg-red-500/20 transition-colors">
                  Obrisi
                </button>
              )}
              <button onClick={() => setShowCiljDialog(false)} className="px-4 bg-white/[0.06] text-[#8a8a8a] text-[14px] py-2.5 rounded-lg hover:bg-white/[0.1] transition-colors">
                Odustani
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
