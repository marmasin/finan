import { useState, useMemo } from "react";
import { useStore } from "../store";
import { hrBroj, parseDate, todayStr, ZASTICENI_RACUNI } from "../logic";
import { Transakcija, TipTransakcije } from "../types";
import Modal from "../components/Modal";
import { toast } from "../components/Toast";

const TIP_BG: Record<TipTransakcije, string> = {
  Prihod: "bg-emerald-500/10 text-emerald-400",
  Rashod: "bg-red-500/10 text-red-400",
  Stanje: "bg-white/[0.06] text-[#8a8a8a]",
};

interface FormState {
  datum: string;
  opis: string;
  tip: TipTransakcije;
  iznos: string;
  racun: string;
}

function emptyForm(racuni: string[]): FormState {
  return { datum: todayStr(), opis: "", tip: "Rashod", iznos: "", racun: racuni[0] ?? "" };
}

const inputCls = "w-full bg-[#1a1a1a] border border-white/[0.1] rounded-lg px-3 py-2.5 text-[14px] text-[#ececec] focus:outline-none focus:border-[#c96442] transition-colors placeholder-[#555]";

export default function Unos() {
  const { data, addTransakcija, editTransakcija, deleteTransakcije, addRacun, deleteRacun } = useStore();

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [editingTx, setEditingTx] = useState<Transakcija | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [form, setForm] = useState<FormState>(emptyForm(data.racuni));

  const [showRacunDialog, setShowRacunDialog] = useState(false);
  const [newRacunName, setNewRacunName] = useState("");
  const [deleteRacunName, setDeleteRacunName] = useState(
    data.racuni.find((r) => !ZASTICENI_RACUNI.includes(r)) ?? ""
  );
  const [moveToRacun, setMoveToRacun] = useState(data.racuni[0] ?? "");
  const [racunError, setRacunError] = useState("");

  const sorted = useMemo(
    () => [...data.transakcije].sort((a, b) => parseDate(b.datum).getTime() - parseDate(a.datum).getTime()),
    [data.transakcije]
  );

  const filtered = useMemo(() => {
    if (!search.trim()) return sorted;
    const q = search.toLowerCase();
    return sorted.filter(t =>
      t.opis.toLowerCase().includes(q) || t.racun.toLowerCase().includes(q) ||
      t.tip.toLowerCase().includes(q) || t.datum.includes(q)
    );
  }, [sorted, search]);

  function toggleSelect(id: number) {
    setSelected(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  }

  function toggleAll() {
    setSelected(selected.size === filtered.length ? new Set() : new Set(filtered.map(t => t.id)));
  }

  function openAdd() { setEditingTx(null); setForm(emptyForm(data.racuni)); setShowAdd(true); }

  function openEdit(tx: Transakcija) {
    setEditingTx(tx);
    setForm({ datum: tx.datum, opis: tx.opis, tip: tx.tip, iznos: String(tx.iznos), racun: tx.racun });
    setShowAdd(true);
  }

  function submitForm() {
    const iznos = parseFloat(form.iznos.replace(",", "."));
    if (!iznos || iznos <= 0 || !form.datum || !form.opis) return;
    if (editingTx) { editTransakcija(editingTx.id, { ...form, iznos }); toast("Stavka azurirana"); }
    else { addTransakcija({ ...form, iznos }); toast("Stavka snimljena"); }
    setShowAdd(false);
  }

  function duplicateSelected() {
    const today = todayStr();
    for (const id of selected) {
      const tx = data.transakcije.find(t => t.id === id);
      if (tx) addTransakcija({ datum: today, opis: tx.opis, tip: tx.tip, iznos: tx.iznos, racun: tx.racun });
    }
    setSelected(new Set());
  }

  function confirmDelete() {
    const n = selected.size;
    deleteTransakcije(selected);
    setSelected(new Set());
    setShowDeleteConfirm(false);
    toast(`Obrisano ${n} ${n === 1 ? "stavka" : "stavki"}`);
  }

  function submitNewRacun() {
    const err = addRacun(newRacunName);
    if (err) { setRacunError(err); return; }
    setNewRacunName(""); setRacunError("");
  }

  function submitDeleteRacun() {
    if (!deleteRacunName || ZASTICENI_RACUNI.includes(deleteRacunName)) return;
    deleteRacun(deleteRacunName, moveToRacun);
    setDeleteRacunName(data.racuni.find(r => !ZASTICENI_RACUNI.includes(r) && r !== deleteRacunName) ?? "");
  }

  const deletableRacuni = data.racuni.filter(r => !ZASTICENI_RACUNI.includes(r));

  function exportCSV() {
    const header = ["Datum", "Opis", "Tip", "Iznos", "Racun", "Timeframe"];
    const rows = filtered.map(t =>
      [t.datum, `"${t.opis.replace(/"/g, '""')}"`, t.tip, String(t.iznos).replace(".", ","), t.racun, t.timeframe].join(";")
    );
    const bom = "﻿";
    const csv = bom + [header.join(";"), ...rows].join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "finan_izvoz.csv"; a.click();
    URL.revokeObjectURL(url);
    toast("CSV izvezen");
  }

  return (
    <div className="flex h-full overflow-hidden">
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-2 px-4 md:px-6 py-3 border-b border-white/[0.06] shrink-0">
          <button
            onClick={openAdd}
            title="Dodaj stavku"
            className="flex items-center justify-center w-8 h-8 bg-[#c96442] text-white rounded-lg hover:bg-[#b5573a] transition-colors shrink-0"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
            </svg>
          </button>

          {selected.size > 0 && (
            <>
              <button
                onClick={duplicateSelected}
                title={`Duplikat (${selected.size})`}
                className="relative flex items-center justify-center w-8 h-8 text-[#8a8a8a] bg-white/[0.06] rounded-lg hover:bg-white/[0.1] transition-colors"
              >
                <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                  <rect x="4" y="4" width="9" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.3"/>
                  <path d="M2 11V3a1 1 0 011-1h8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
                </svg>
                <span className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-[#8a8a8a] text-[#1a1a1a] text-[9px] font-bold rounded-full flex items-center justify-center leading-none">
                  {selected.size}
                </span>
              </button>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                title={`Obrisi (${selected.size})`}
                className="relative flex items-center justify-center w-8 h-8 text-red-400 bg-red-500/10 rounded-lg hover:bg-red-500/20 transition-colors"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M2 3.5h10M5 3.5V2.5a1 1 0 011-1h2a1 1 0 011 1v1M5.5 6v4.5M8.5 6v4.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
                  <rect x="2.5" y="3.5" width="9" height="8.5" rx="1.5" stroke="currentColor" strokeWidth="1.3"/>
                </svg>
                <span className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-red-400 text-[#1a1a1a] text-[9px] font-bold rounded-full flex items-center justify-center leading-none">
                  {selected.size}
                </span>
              </button>
            </>
          )}

          <div className="ml-auto flex items-center gap-2">
            <div className="relative flex items-center">
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none" className="absolute left-2.5 text-[#555] pointer-events-none">
                <circle cx="5.5" cy="5.5" r="4" stroke="currentColor" strokeWidth="1.3"/>
                <path d="M8.5 8.5L11 11" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
              </svg>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Pretrazi..."
                className="bg-[#262626] border border-white/[0.08] rounded-lg pl-8 pr-3 py-1.5 text-[13px] text-[#ececec] w-36 md:w-52 focus:outline-none focus:border-[#c96442] transition-colors placeholder-[#555]"
              />
            </div>
            <button
              onClick={exportCSV}
              title="Izvoz u CSV"
              className="flex items-center justify-center w-8 h-8 text-[#8a8a8a] bg-white/[0.06] rounded-lg hover:bg-white/[0.1] transition-colors"
            >
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                <path d="M7.5 2v8M4.5 7.5l3 3 3-3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M2 11v1.5a1 1 0 001 1h9a1 1 0 001-1V11" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
              </svg>
            </button>
            <button
              onClick={() => setShowRacunDialog(true)}
              title="Upravljanje racunima"
              className="flex items-center justify-center w-8 h-8 text-[#8a8a8a] bg-white/[0.06] rounded-lg hover:bg-white/[0.1] transition-colors"
            >
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                <rect x="1" y="2.5" width="13" height="10" rx="2" stroke="currentColor" strokeWidth="1.3"/>
                <path d="M1 6h13" stroke="currentColor" strokeWidth="1.3"/>
                <circle cx="4.5" cy="9" r="1" fill="currentColor"/>
              </svg>
            </button>
          </div>
        </div>

        {search && (
          <p className="px-5 py-2 text-[12px] text-[#8a8a8a] border-b border-white/[0.06] shrink-0">
            {filtered.length} / {sorted.length} stavki
          </p>
        )}

        {/* Mobile card list */}
        <div className="md:hidden flex-1 overflow-y-auto divide-y divide-white/[0.06]">
          {filtered.map((t) => (
            <div
              key={t.id}
              onClick={() => openEdit(t)}
              className={`flex items-center gap-3 px-4 py-3.5 cursor-pointer transition-colors ${
                selected.has(t.id) ? "bg-[#c96442]/[0.06]" : "hover:bg-white/[0.02]"
              }`}
            >
              <div onClick={(e) => { e.stopPropagation(); toggleSelect(t.id); }}>
                <input type="checkbox" checked={selected.has(t.id)} readOnly className="accent-[#c96442] w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-[14px] text-[#ececec] truncate font-medium">{t.opis}</p>
                  <span className={`shrink-0 text-[11px] font-medium px-2 py-0.5 rounded-full ${TIP_BG[t.tip]}`}>{t.tip}</span>
                </div>
                <p className="text-[12px] text-[#8a8a8a] mt-0.5">{t.datum} &middot; {t.racun}</p>
              </div>
              <span className={`text-[14px] font-medium tabular-nums font-mono shrink-0 ${
                t.tip === "Rashod" ? "text-red-400" : "text-emerald-400"
              }`}>
                {t.tip === "Rashod" ? "-" : t.tip === "Prihod" ? "+" : ""}{hrBroj(t.iznos)}
              </span>
            </div>
          ))}
        </div>

        {/* Desktop table */}
        <div className="hidden md:block flex-1 overflow-y-auto">
          <table className="w-full text-[13px]">
            <thead className="sticky top-0 bg-[#1a1a1a] z-10">
              <tr className="border-b border-white/[0.06]">
                <th className="w-10 px-4 py-3">
                  <input type="checkbox" checked={selected.size === filtered.length && filtered.length > 0} onChange={toggleAll} className="accent-[#c96442] w-4 h-4" />
                </th>
                {["Datum", "Opis", "Tip", "Iznos", "Racun"].map(h => (
                  <th key={h} className="text-left px-3 py-3 text-[11px] font-medium text-[#8a8a8a] uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((t, i) => (
                <tr
                  key={t.id}
                  onClick={() => openEdit(t)}
                  className={`border-b border-white/[0.04] last:border-0 cursor-pointer transition-colors ${
                    selected.has(t.id) ? "bg-[#c96442]/[0.06]" : i % 2 === 0 ? "hover:bg-white/[0.02]" : "bg-white/[0.01] hover:bg-white/[0.03]"
                  }`}
                >
                  <td className="w-10 px-4 py-2.5" onClick={(e) => { e.stopPropagation(); toggleSelect(t.id); }}>
                    <input type="checkbox" checked={selected.has(t.id)} readOnly className="accent-[#c96442] w-4 h-4" />
                  </td>
                  <td className="px-3 py-2.5 font-mono text-[12px] text-[#8a8a8a] whitespace-nowrap">{t.datum}</td>
                  <td className="px-3 py-2.5 text-[#ececec] max-w-[200px] truncate">{t.opis}</td>
                  <td className="px-3 py-2.5">
                    <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${TIP_BG[t.tip]}`}>{t.tip}</span>
                  </td>
                  <td className={`px-3 py-2.5 font-mono tabular-nums text-right font-medium ${t.tip === "Rashod" ? "text-red-400" : "text-emerald-400"}`}>
                    {t.tip === "Rashod" ? "-" : t.tip === "Prihod" ? "+" : ""}{hrBroj(t.iznos)}
                  </td>
                  <td className="px-3 py-2.5 text-[#8a8a8a]">{t.racun}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add/Edit Dialog */}
      {showAdd && (
        <Modal title={editingTx ? "Uredi stavku" : "Nova stavka"} onClose={() => setShowAdd(false)}>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="text-[12px] font-medium text-[#8a8a8a] uppercase tracking-wider mb-2 block">Datum</span>
                <input type="text" value={form.datum} onChange={(e) => setForm({ ...form, datum: e.target.value })} placeholder="DD.MM.YYYY" className={inputCls} />
              </label>
              <label className="block">
                <span className="text-[12px] font-medium text-[#8a8a8a] uppercase tracking-wider mb-2 block">Iznos (EUR)</span>
                <input type="number" min="0" step="0.01" value={form.iznos} onChange={(e) => setForm({ ...form, iznos: e.target.value })} placeholder="0.00" className={inputCls} />
              </label>
            </div>
            <label className="block">
              <span className="text-[12px] font-medium text-[#8a8a8a] uppercase tracking-wider mb-2 block">Opis</span>
              <input type="text" value={form.opis} onChange={(e) => setForm({ ...form, opis: e.target.value })} className={inputCls} />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="text-[12px] font-medium text-[#8a8a8a] uppercase tracking-wider mb-2 block">Tip</span>
                <select value={form.tip} onChange={(e) => setForm({ ...form, tip: e.target.value as TipTransakcije })} className={inputCls}>
                  <option value="Rashod">Rashod</option>
                  <option value="Prihod">Prihod</option>
                  <option value="Stanje">Stanje</option>
                </select>
              </label>
              <label className="block">
                <span className="text-[12px] font-medium text-[#8a8a8a] uppercase tracking-wider mb-2 block">Racun</span>
                <select value={form.racun} onChange={(e) => setForm({ ...form, racun: e.target.value })} className={inputCls}>
                  {data.racuni.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </label>
            </div>
            <div className="flex gap-2 pt-1">
              <button onClick={submitForm} className="flex-1 bg-[#c96442] text-white text-[14px] font-semibold py-2.5 rounded-lg hover:bg-[#b5573a] transition-colors">
                {editingTx ? "Spremi promjene" : "Snimi stavku"}
              </button>
              <button onClick={() => setShowAdd(false)} className="px-4 bg-white/[0.06] text-[#8a8a8a] text-[14px] py-2.5 rounded-lg hover:bg-white/[0.1] transition-colors">
                Odustani
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Delete Confirmation */}
      {showDeleteConfirm && (
        <Modal title="Potvrda brisanja" onClose={() => setShowDeleteConfirm(false)}>
          <p className="text-[14px] text-red-400 mb-4">
            Obrisat ce se {selected.size} {selected.size === 1 ? "stavka" : "stavki"}. Ova radnja je nepovratna.
          </p>
          <div className="border border-white/[0.08] rounded-xl overflow-hidden mb-4 max-h-48 overflow-y-auto">
            <table className="w-full text-[13px]">
              <tbody>
                {[...selected].map((id) => {
                  const tx = data.transakcije.find(t => t.id === id);
                  if (!tx) return null;
                  return (
                    <tr key={id} className="border-b border-white/[0.06] last:border-0">
                      <td className="px-4 py-2.5 font-mono text-[12px] text-[#8a8a8a]">{tx.datum}</td>
                      <td className="px-4 py-2.5 text-[#ececec]">{tx.opis}</td>
                      <td className="px-4 py-2.5 font-mono text-right text-red-400">{hrBroj(tx.iznos)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowDeleteConfirm(false)} className="flex-1 bg-white/[0.06] text-[#8a8a8a] text-[14px] font-semibold py-2.5 rounded-lg hover:bg-white/[0.1] transition-colors">
              Odustani
            </button>
            <button onClick={confirmDelete} className="flex-1 bg-red-500 text-white text-[14px] font-semibold py-2.5 rounded-lg hover:bg-red-600 transition-colors">
              Obrisi
            </button>
          </div>
        </Modal>
      )}

      {/* Account Management */}
      {showRacunDialog && (
        <Modal title="Upravljanje racunima" onClose={() => setShowRacunDialog(false)}>
          <div className="space-y-5">
            <div>
              <p className="text-[12px] font-medium text-[#8a8a8a] uppercase tracking-wider mb-3">Dodaj novi racun</p>
              <div className="flex gap-2">
                <input type="text" value={newRacunName} onChange={(e) => { setNewRacunName(e.target.value); setRacunError(""); }} placeholder="Naziv racuna" className={inputCls + " flex-1"} />
                <button onClick={submitNewRacun} className="px-4 bg-[#c96442] text-white text-[14px] font-semibold rounded-lg hover:bg-[#b5573a] transition-colors">Dodaj</button>
              </div>
              {racunError && <p className="text-[12px] text-red-400 mt-1">{racunError}</p>}
            </div>

            {deletableRacuni.length > 0 && (
              <div className="border-t border-white/[0.06] pt-4 space-y-2">
                <p className="text-[12px] font-medium text-[#8a8a8a] uppercase tracking-wider mb-3">Obrisi racun</p>
                <select value={deleteRacunName} onChange={(e) => setDeleteRacunName(e.target.value)} className={inputCls}>
                  {deletableRacuni.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
                <p className="text-[12px] text-[#8a8a8a]">Premjesti stavke na:</p>
                <select value={moveToRacun} onChange={(e) => setMoveToRacun(e.target.value)} className={inputCls}>
                  {data.racuni.filter(r => r !== deleteRacunName).map(r => <option key={r} value={r}>{r}</option>)}
                </select>
                <button onClick={submitDeleteRacun} className="w-full bg-red-500/10 text-red-400 text-[14px] font-semibold py-2.5 rounded-lg hover:bg-red-500/20 transition-colors">
                  Obrisi i premjesti
                </button>
              </div>
            )}

            <div className="border-t border-white/[0.06] pt-4">
              <p className="text-[12px] font-medium text-[#8a8a8a] uppercase tracking-wider mb-2">Zasticeni racuni</p>
              <div className="flex flex-wrap gap-2">
                {ZASTICENI_RACUNI.map(r => (
                  <span key={r} className="text-[12px] text-[#8a8a8a] bg-white/[0.06] px-2.5 py-1 rounded-lg">{r}</span>
                ))}
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
