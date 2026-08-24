import {
  createContext,
  useContext,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { AppData, Cilj, Transakcija, TipTransakcije } from "./types";
import { timeframeFromDate, todayStr, ZASTICENI_RACUNI } from "./logic";

const SEED: AppData = {
  racuni: ["Erste Tekući", "PBZ Žiro", "Gotovina", "Revolut"],
  transakcije: [
    { id: 1, timeframe: "Lipanj 2026", datum: "01.06.2026", opis: "Početno stanje", tip: "Stanje", iznos: 3500, racun: "Erste Tekući" },
    { id: 2, timeframe: "Lipanj 2026", datum: "01.06.2026", opis: "Početno stanje", tip: "Stanje", iznos: 12000, racun: "PBZ Žiro" },
    { id: 3, timeframe: "Lipanj 2026", datum: "01.06.2026", opis: "Početno stanje", tip: "Stanje", iznos: 850, racun: "Gotovina" },
    { id: 4, timeframe: "Lipanj 2026", datum: "01.06.2026", opis: "Početno stanje", tip: "Stanje", iznos: 2100, racun: "Revolut" },
    { id: 5, timeframe: "Lipanj 2026", datum: "05.06.2026", opis: "Plaća lipanj", tip: "Prihod", iznos: 4200, racun: "Erste Tekući" },
    { id: 6, timeframe: "Lipanj 2026", datum: "07.06.2026", opis: "Režije", tip: "Rashod", iznos: 420, racun: "Erste Tekući" },
    { id: 7, timeframe: "Lipanj 2026", datum: "10.06.2026", opis: "Namirnice", tip: "Rashod", iznos: 185, racun: "Revolut" },
    { id: 8, timeframe: "Lipanj 2026", datum: "15.06.2026", opis: "Najam stana", tip: "Rashod", iznos: 900, racun: "PBZ Žiro" },
    { id: 9, timeframe: "Lipanj 2026", datum: "20.06.2026", opis: "Freelance projekt", tip: "Prihod", iznos: 1500, racun: "Revolut" },
    { id: 10, timeframe: "Srpanj 2026", datum: "05.07.2026", opis: "Plaća srpanj", tip: "Prihod", iznos: 4200, racun: "Erste Tekući" },
    { id: 11, timeframe: "Srpanj 2026", datum: "08.07.2026", opis: "Režije", tip: "Rashod", iznos: 380, racun: "Erste Tekući" },
    { id: 12, timeframe: "Srpanj 2026", datum: "15.07.2026", opis: "Najam stana", tip: "Rashod", iznos: 900, racun: "PBZ Žiro" },
    { id: 13, timeframe: "Srpanj 2026", datum: "22.07.2026", opis: "Namirnice", tip: "Rashod", iznos: 210, racun: "Revolut" },
    { id: 14, timeframe: "Kolovoz 2026", datum: "05.08.2026", opis: "Plaća kolovoz", tip: "Prihod", iznos: 4200, racun: "Erste Tekući" },
    { id: 15, timeframe: "Kolovoz 2026", datum: "08.08.2026", opis: "Režije", tip: "Rashod", iznos: 405, racun: "Erste Tekući" },
    { id: 16, timeframe: "Kolovoz 2026", datum: "15.08.2026", opis: "Najam stana", tip: "Rashod", iznos: 900, racun: "PBZ Žiro" },
    { id: 17, timeframe: "Kolovoz 2026", datum: "18.08.2026", opis: "Namirnice", tip: "Rashod", iznos: 175, racun: "Revolut" },
    { id: 18, timeframe: "Kolovoz 2026", datum: "20.08.2026", opis: "Frizerski salon", tip: "Rashod", iznos: 45, racun: "Gotovina" },
    { id: 19, timeframe: "Rujan 2026", datum: "05.09.2026", opis: "Plaća rujan", tip: "Prihod", iznos: 4200, racun: "Erste Tekući" },
    { id: 20, timeframe: "Rujan 2026", datum: "08.09.2026", opis: "Režije", tip: "Rashod", iznos: 400, racun: "Erste Tekući" },
    { id: 21, timeframe: "Rujan 2026", datum: "15.09.2026", opis: "Najam stana", tip: "Rashod", iznos: 900, racun: "PBZ Žiro" },
    { id: 22, timeframe: "Listopad 2026", datum: "05.10.2026", opis: "Plaća listopad", tip: "Prihod", iznos: 4200, racun: "Erste Tekući" },
    { id: 23, timeframe: "Listopad 2026", datum: "15.10.2026", opis: "Najam stana", tip: "Rashod", iznos: 900, racun: "PBZ Žiro" },
  ],
  ciljevi: [
    { id: 1, racun: "PBZ Žiro", rok: "31.12.2026", iznos: 10000, napomena: "Fond za hitne slučajeve" },
    { id: 2, racun: "UKUPNO", rok: "30.06.2027", iznos: 30000, napomena: "Godišnja uštedina" },
  ],
  nextId: 24,
  nextCiljId: 3,
};

const STORAGE_KEY = "finan_data";

function loadData(): AppData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return SEED;
}

function saveData(data: AppData) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

interface Store {
  data: AppData;
  addTransakcija: (fields: Omit<Transakcija, "id" | "timeframe">) => void;
  editTransakcija: (id: number, fields: Partial<Omit<Transakcija, "id">>) => void;
  deleteTransakcije: (ids: Set<number>) => void;
  addRacun: (name: string) => string | null;
  deleteRacun: (name: string, moveTo: string) => void;
  addCilj: (fields: Omit<Cilj, "id">) => void;
  editCilj: (id: number, fields: Partial<Omit<Cilj, "id">>) => void;
  deleteCilj: (id: number) => void;
}

const Ctx = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<AppData>(loadData);

  const update = useCallback((fn: (d: AppData) => AppData) => {
    setData((prev) => {
      const next = fn(prev);
      saveData(next);
      return next;
    });
  }, []);

  const addTransakcija = useCallback(
    (fields: Omit<Transakcija, "id" | "timeframe">) => {
      update((d) => ({
        ...d,
        transakcije: [
          ...d.transakcije,
          {
            ...fields,
            id: d.nextId,
            timeframe: timeframeFromDate(fields.datum),
          },
        ],
        nextId: d.nextId + 1,
      }));
    },
    [update]
  );

  const editTransakcija = useCallback(
    (id: number, fields: Partial<Omit<Transakcija, "id">>) => {
      update((d) => ({
        ...d,
        transakcije: d.transakcije.map((t) =>
          t.id === id
            ? {
                ...t,
                ...fields,
                timeframe: fields.datum
                  ? timeframeFromDate(fields.datum)
                  : t.timeframe,
              }
            : t
        ),
      }));
    },
    [update]
  );

  const deleteTransakcije = useCallback(
    (ids: Set<number>) => {
      update((d) => ({
        ...d,
        transakcije: d.transakcije.filter((t) => !ids.has(t.id)),
      }));
    },
    [update]
  );

  const addRacun = useCallback(
    (name: string): string | null => {
      name = name.trim();
      if (!name) return "Naziv ne smije biti prazan.";
      let error: string | null = null;
      update((d) => {
        if (d.racuni.includes(name)) {
          error = "Račun s tim nazivom već postoji.";
          return d;
        }
        return { ...d, racuni: [...d.racuni, name] };
      });
      return error;
    },
    [update]
  );

  const deleteRacun = useCallback(
    (name: string, moveTo: string) => {
      if (ZASTICENI_RACUNI.includes(name)) return;
      update((d) => ({
        ...d,
        racuni: d.racuni.filter((r) => r !== name),
        transakcije: d.transakcije.map((t) =>
          t.racun === name ? { ...t, racun: moveTo } : t
        ),
      }));
    },
    [update]
  );

  const addCilj = useCallback(
    (fields: Omit<Cilj, "id">) => {
      update((d) => ({
        ...d,
        ciljevi: [...d.ciljevi, { ...fields, id: d.nextCiljId }],
        nextCiljId: d.nextCiljId + 1,
      }));
    },
    [update]
  );

  const editCilj = useCallback(
    (id: number, fields: Partial<Omit<Cilj, "id">>) => {
      update((d) => ({
        ...d,
        ciljevi: d.ciljevi.map((c) => (c.id === id ? { ...c, ...fields } : c)),
      }));
    },
    [update]
  );

  const deleteCilj = useCallback(
    (id: number) => {
      update((d) => ({ ...d, ciljevi: d.ciljevi.filter((c) => c.id !== id) }));
    },
    [update]
  );

  return (
    <Ctx.Provider
      value={{
        data,
        addTransakcija,
        editTransakcija,
        deleteTransakcije,
        addRacun,
        deleteRacun,
        addCilj,
        editCilj,
        deleteCilj,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useStore(): Store {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useStore outside StoreProvider");
  return ctx;
}
