import { useStore } from "../store";
import { ukupnoStanje, hrBroj, todayStr } from "../logic";

export default function Hero() {
  const { data } = useStore();

  const today = ukupnoStanje(data.racuni, data.transakcije, todayStr());

  const todayTs = new Date().setHours(0, 0, 0, 0);
  const futureDates = data.transakcije
    .filter((t) => {
      const [d, m, y] = t.datum.split(".").map(Number);
      return new Date(y, m - 1, d).getTime() > todayTs;
    })
    .map((t) => t.datum);

  const latestFuture = futureDates.sort((a, b) => {
    const pd = (s: string) => { const [d,m,y] = s.split(".").map(Number); return new Date(y,m-1,d).getTime(); };
    return pd(b) - pd(a);
  })[0];

  const projected = latestFuture
    ? ukupnoStanje(data.racuni, data.transakcije, latestFuture)
    : null;
  const delta = projected !== null ? projected - today : null;

  const todayLabel = new Date().toLocaleDateString("hr-HR", {
    day: "numeric", month: "long", year: "numeric",
  });

  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-4 px-5 md:px-8 py-5 border-b border-white/[0.06] shrink-0">
      <div>
        <p className="text-[11px] font-medium text-[#8a8a8a] mb-1.5 uppercase tracking-widest">
          Ukupno danas &middot; {todayLabel}
        </p>
        <p className="text-[28px] md:text-[34px] font-semibold text-[#ececec] leading-none tracking-tight">
          {hrBroj(today)}
        </p>
      </div>

      {projected !== null && delta !== null && (
        <div className="flex items-center gap-4 sm:ml-8 sm:pl-8 sm:border-l sm:border-white/[0.08]">
          <div>
            <p className="text-[11px] font-medium text-[#8a8a8a] mb-1.5 uppercase tracking-widest">
              Projekcija &middot; {latestFuture}
            </p>
            <p className="text-xl font-semibold tabular-nums text-[#ececec] leading-none tracking-tight">
              {hrBroj(projected)}
            </p>
          </div>
          <span className={`text-sm font-medium px-2.5 py-1 rounded-full ${
            delta >= 0
              ? "bg-emerald-500/10 text-emerald-400"
              : "bg-orange-500/10 text-orange-400"
          }`}>
            {delta >= 0 ? "+" : ""}{hrBroj(delta)}
          </span>
        </div>
      )}
    </div>
  );
}
