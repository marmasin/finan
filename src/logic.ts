import { Cilj, Transakcija } from "./types";

export const ZASTICENI_RACUNI = ["Erste Tekući", "PBZ Žiro", "Gotovina", "Revolut"];
export const TIPOVI = ["Prihod", "Rashod", "Stanje"] as const;

const MONTHS = [
  "Siječanj", "Veljača", "Ožujak", "Travanj", "Svibanj", "Lipanj",
  "Srpanj", "Kolovoz", "Rujan", "Listopad", "Studeni", "Prosinac",
];

export function parseDate(s: string): Date {
  const [d, m, y] = s.split(".").map(Number);
  return new Date(y, m - 1, d);
}

export function formatDate(d: Date): string {
  return `${String(d.getDate()).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}.${d.getFullYear()}`;
}

export function todayStr(): string {
  return formatDate(new Date());
}

export function timeframeFromDate(s: string): string {
  const d = parseDate(s);
  return `${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

export function hrBroj(n: number, symbol = true): string {
  const formatted = Math.abs(n).toLocaleString("hr-HR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const prefix = n < 0 ? "−" : "";
  return symbol ? `${prefix}${formatted} €` : `${prefix}${formatted}`;
}

export function stanjaPo(
  racuni: string[],
  transakcije: Transakcija[],
  naDan?: string
): Record<string, number> {
  const result: Record<string, number> = {};
  for (const r of racuni) result[r] = 0;

  const cutoff = naDan ? parseDate(naDan).getTime() : Infinity;
  const sorted = [...transakcije].sort(
    (a, b) => parseDate(a.datum).getTime() - parseDate(b.datum).getTime()
  );

  for (const t of sorted) {
    if (parseDate(t.datum).getTime() > cutoff) continue;
    if (!(t.racun in result)) result[t.racun] = 0;
    if (t.tip === "Stanje") result[t.racun] = t.iznos;
    else if (t.tip === "Prihod") result[t.racun] += t.iznos;
    else if (t.tip === "Rashod") result[t.racun] -= t.iznos;
  }
  return result;
}

export function ukupnoStanje(
  racuni: string[],
  transakcije: Transakcija[],
  naDan?: string
): number {
  return Object.values(stanjaPo(racuni, transakcije, naDan)).reduce(
    (s, v) => s + v,
    0
  );
}

export interface LedgerRow extends Transakcija {
  stanja: Record<string, number>;
  raspoloziv: number;
}

export function preracunajTablicu(
  racuni: string[],
  transakcije: Transakcija[]
): LedgerRow[] {
  const running: Record<string, number> = {};
  for (const r of racuni) running[r] = 0;

  const sorted = [...transakcije].sort((a, b) => {
    const diff = parseDate(a.datum).getTime() - parseDate(b.datum).getTime();
    return diff !== 0 ? diff : a.id - b.id;
  });

  return sorted.map((t) => {
    if (t.tip === "Stanje") running[t.racun] = t.iznos;
    else if (t.tip === "Prihod") running[t.racun] = (running[t.racun] || 0) + t.iznos;
    else running[t.racun] = (running[t.racun] || 0) - t.iznos;

    const raspoloziv = Object.values(running).reduce((s, v) => s + v, 0);
    return { ...t, stanja: { ...running }, raspoloziv };
  });
}

export interface GoalProgress {
  projekcija: number;
  razlika: number;
  dana: number;
  postotak: number;
  mjesecno: number;
  status: "ostvaren" | "promašen" | "na putu" | "manjak";
}

export function goalProgress(
  cilj: Cilj,
  racuni: string[],
  transakcije: Transakcija[]
): GoalProgress {
  const today = new Date();
  const rok = parseDate(cilj.rok);
  const dana = Math.round((rok.getTime() - today.getTime()) / 86_400_000);

  const projekcija =
    cilj.racun === "UKUPNO"
      ? ukupnoStanje(racuni, transakcije, cilj.rok)
      : (stanjaPo(racuni, transakcije, cilj.rok)[cilj.racun] ?? 0);

  const razlika = projekcija - cilj.iznos;
  const met = razlika >= 0;
  const postotak =
    cilj.iznos <= 0 ? 100 : Math.max(0, Math.min(100, (projekcija / cilj.iznos) * 100));

  const status: GoalProgress["status"] =
    dana < 0
      ? met ? "ostvaren" : "promašen"
      : met ? "na putu" : "manjak";

  const mjesecno = !met && dana > 0 ? Math.abs(razlika) / (dana / 30.44) : 0;

  return { projekcija, razlika, dana, postotak, mjesecno, status };
}

export const STATUS_ICON: Record<GoalProgress["status"], string> = {
  ostvaren: "✅",
  promašen: "❌",
  "na putu": "🟢",
  manjak: "🟠",
};
