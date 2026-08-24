export type TipTransakcije = "Prihod" | "Rashod" | "Stanje";

export interface Transakcija {
  id: number;
  timeframe: string;
  datum: string; // DD.MM.YYYY
  opis: string;
  tip: TipTransakcije;
  iznos: number;
  racun: string;
}

export interface Cilj {
  id: number;
  racun: string; // account name or 'UKUPNO'
  rok: string; // DD.MM.YYYY
  iznos: number;
  napomena: string;
}

export interface AppData {
  racuni: string[];
  transakcije: Transakcija[];
  ciljevi: Cilj[];
  nextId: number;
  nextCiljId: number;
}
