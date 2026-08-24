"""
Ciljevi po izvorima (računima) — koliko želim da mi OSTANE na zadani rok.

Cilj je trojka (Račun, Rok, Iznos): „na računu Erste Tekući želim imati barem
1.500 € na 30.09.2026”. Za rok se uzima projekcija iz istih podataka koje
koristi ostatak appa (`logika.stanja_po_racunima(..., na_dan=rok)`), pa je
napredak uvijek u skladu s tablicom sljedivosti — ništa se ne računa dvaput.

Poseban račun `UKUPNO` znači cilj za zbroj svih izvora.

Pohrana je u ISTOJ datoteci kao baza, pod ključem "ciljevi". Zato je
`logika.spremi` prilagođen da ne briše nepoznate ključeve — inače bi svako
spremanje stavki iz appa pobrisalo ciljeve. Prednost jedne datoteke: sinkro s
Google Cloud Storageom (storage.py) radi bez ikakve dodatne postavke.

Modul je čista logika + pohrana, kao `logika.py` — bez ispisa i bez unosa.
Na dnu je i mali terminalski izbornik, pa se može pokrenuti samostalno:

    uv run ciljevi.py
"""
import json
import os
from datetime import date, datetime

import logika

# Naziv „računa” koji označava cilj za zbroj svih izvora.
UKUPNO = "UKUPNO"

# Statusi cilja (vraća ih `napredak`).
OSTVAREN = "ostvaren"      # rok prošao, cilj dosegnut
PROMASEN = "promašen"      # rok prošao, cilj nije dosegnut
NA_PUTU = "na putu"        # rok pred nama, projekcija dosiže cilj
MANJAK = "manjak"          # rok pred nama, projekcija NE dosiže cilj


# ---------------------------------------------------------------------------
# POHRANA
# ---------------------------------------------------------------------------

def ucitaj():
    """
    Vraća listu ciljeva iz baze (prazna lista ako ih još nema).

    Namjerno NE poziva `logika.ucitaj()` — ovdje nas zanima samo ključ
    "ciljevi", a `logika.ucitaj` bi usput mogao kreirati početnu bazu.
    """
    if not os.path.exists(logika.DATOTEKA):
        return []
    try:
        with open(logika.DATOTEKA, "r", encoding="utf-8") as f:
            podaci = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise OSError(f"Datoteku nije moguće pročitati: {e}") from e
    if not isinstance(podaci, dict):
        return []  # stari format (samo lista transakcija) — ciljeva još nema
    ciljevi = podaci.get("ciljevi", [])
    return ciljevi if isinstance(ciljevi, list) else []


def spremi(ciljevi):
    """
    Sprema ciljeve u bazu, čuvajući račune i transakcije.

    Čita datoteku pa upisuje samo ključ "ciljevi" — tako se dva modula
    (ovaj i `logika`) ne gaze međusobno.
    """
    podaci = logika._postojeci_json()
    podaci["ciljevi"] = ciljevi
    with open(logika.DATOTEKA, "w", encoding="utf-8") as f:
        json.dump(podaci, f, ensure_ascii=False, indent=2)
    # Isti put u oblak kao u logika.spremi — inače bi cilj nestao pri restartu.
    if logika.storage.omogucen():
        try:
            logika.storage.posalji(logika.DATOTEKA)
        except Exception as e:  # noqa: BLE001
            raise OSError(f"Ne mogu spremiti ciljeve u oblak: {e}") from e


# ---------------------------------------------------------------------------
# VALIDACIJA I CRUD  (bacaju ValueError — UI hvata i prikazuje)
# ---------------------------------------------------------------------------

def provjeri_racun(racun, racuni):
    """Račun mora postojati na popisu izvora, ili biti `UKUPNO`."""
    racun = str(racun or "").strip()
    if not racun:
        raise ValueError("Izvor je obavezan.")
    if racun != UKUPNO and racun not in racuni:
        raise ValueError(f"Nepoznat izvor: {racun}")
    return racun


def provjeri_iznos_cilja(vrijednost):
    """
    Ciljani iznos. Dopušta 0 i negativno — cilj može biti „ne ispod −200 €”
    (npr. dopušteni minus), što `logika.provjeri_iznos` ne bi propustio.
    """
    if vrijednost is None or str(vrijednost).strip() == "":
        raise ValueError("Ciljani iznos je obavezan.")
    try:
        return round(float(str(vrijednost).replace(",", ".").strip()), 2)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Neispravan iznos: {vrijednost}") from e


def postavi(ciljevi, racun, iznos, rok, racuni, napomena=""):
    """
    Dodaje ili mijenja cilj za (Račun, Rok). Vraća (novi_popis, je_promjena).

    Za isti izvor i isti rok postoji najviše jedan cilj — ponovno postavljanje
    prepisuje iznos. Različiti rokovi za isti izvor su dopušteni (rujan, listopad…).
    """
    racun = provjeri_racun(racun, racuni)
    iznos = provjeri_iznos_cilja(iznos)
    rok = logika.provjeri_datum(rok)

    cilj = {
        "Račun": racun,
        "Rok": rok,
        "Iznos": iznos,
        "Napomena": str(napomena or "").strip(),
    }
    novi = [c for c in ciljevi if not _isti(c, racun, rok)]
    je_promjena = len(novi) != len(ciljevi)
    novi.append(cilj)
    return _sortirani(novi), je_promjena


def obrisi(ciljevi, racun, rok):
    """Briše cilj za (Račun, Rok). Vraća (novi_popis, broj_obrisanih)."""
    rok = logika.provjeri_datum(rok)
    novi = [c for c in ciljevi if not _isti(c, racun, rok)]
    return novi, len(ciljevi) - len(novi)


def _isti(cilj, racun, rok):
    return cilj.get("Račun") == racun and cilj.get("Rok") == rok


def _sortirani(ciljevi):
    """Kronološki po roku, pa po nazivu izvora."""
    def kljuc(c):
        d = _datum(c.get("Rok"))
        return (d or date.max, str(c.get("Račun", "")))
    return sorted(ciljevi, key=kljuc)


def _datum(rok):
    """'DD.MM.YYYY' → date, ili None ako je neispravan."""
    try:
        return datetime.strptime(str(rok), "%d.%m.%Y").date()  # noqa: DTZ007
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# OBRAČUN NAPRETKA
# ---------------------------------------------------------------------------

def stanje_na_rok(racun, rok, racuni, transakcije):
    """
    Projicirano stanje izvora na dan `rok` (date), po istim pravilima kao app.

    Uzima u obzir „Stanje” resete i sve stavke s datumom <= rok, uključujući
    buduće koje su već unesene.
    """
    stanja = logika.stanja_po_racunima(racuni, transakcije, na_dan=rok)
    if racun == UKUPNO:
        return sum(stanja.values())
    return stanja.get(racun, 0.0)


def napredak(cilj, racuni, transakcije, danas=None):
    """
    Vraća rječnik s obračunom jednog cilja:

        Račun, Rok, Iznos (cilj), Projekcija (stanje na rok), Razlika,
        Status (OSTVAREN/PROMASEN/NA_PUTU/MANJAK), Dana (do roka, negativno
        ako je prošao), Postotak (0–100+, koliko je cilja pokriveno),
        Mjesecno (koliko treba mjesečno da se pokrije manjak, ili None).

    Baca ValueError ako je rok cilja neispravan.
    """
    danas = danas or date.today()  # noqa: DTZ011 – app radi s lokalnim datumima
    rok = _datum(cilj.get("Rok"))
    if rok is None:
        raise ValueError(f"Cilj ima neispravan rok: {cilj.get('Rok')!r}")

    racun = cilj.get("Račun", UKUPNO)
    ciljani = float(cilj.get("Iznos", 0.0))
    projekcija = stanje_na_rok(racun, rok, racuni, transakcije)
    razlika = round(projekcija - ciljani, 2)
    dana = (rok - danas).days
    dosegnut = razlika >= 0

    if dana < 0:
        status = OSTVAREN if dosegnut else PROMASEN
    else:
        status = NA_PUTU if dosegnut else MANJAK

    # Postotak pokrivenosti ima smisla samo za pozitivan cilj.
    if ciljani > 0:
        postotak = max(0.0, round(projekcija / ciljani * 100, 1))
    else:
        postotak = 100.0 if dosegnut else 0.0

    # Koliko mjesečno treba dodati da se manjak pokrije do roka.
    mjesecno = None
    if not dosegnut and dana > 0:
        mjeseci = max(dana / 30.44, 1 / 30.44)
        mjesecno = round(abs(razlika) / mjeseci, 2)

    return {
        "Račun": racun,
        "Rok": cilj["Rok"],
        "Iznos": ciljani,
        "Projekcija": round(projekcija, 2),
        "Razlika": razlika,
        "Status": status,
        "Dana": dana,
        "Postotak": postotak,
        "Mjesecno": mjesecno,
        "Napomena": cilj.get("Napomena", ""),
    }


def pregled(ciljevi, racuni, transakcije, danas=None):
    """Napredak svih ciljeva, kronološki. Neispravni ciljevi se preskaču."""
    redovi = []
    for c in _sortirani(ciljevi):
        try:
            redovi.append(napredak(c, racuni, transakcije, danas=danas))
        except ValueError:
            continue
    return redovi


def redovi_za_tablicu(ciljevi, racuni, transakcije, danas=None):
    """Pregled u obliku spremnom za prikaz (hrvatski brojevi, znakovi statusa)."""
    znak = {OSTVAREN: "✅", PROMASEN: "❌", NA_PUTU: "🟢", MANJAK: "🟠"}
    redovi = []
    for n in pregled(ciljevi, racuni, transakcije, danas=danas):
        redovi.append(
            {
                "Izvor": n["Račun"],
                "Rok": n["Rok"],
                "Cilj (EUR)": logika.hrvatski_broj(n["Iznos"]),
                "Projekcija (EUR)": logika.hrvatski_broj(n["Projekcija"]),
                "Razlika (EUR)": logika.hrvatski_broj(n["Razlika"]),
                "Status": f"{znak.get(n['Status'], '•')} {n['Status']}",
                "Dana do roka": n["Dana"],
            }
        )
    return redovi


# ---------------------------------------------------------------------------
# SAMOSTALNO POKRETANJE (mali terminalski izbornik)
# ---------------------------------------------------------------------------

def _ispisi(ciljevi, racuni, transakcije):
    redovi = pregled(ciljevi, racuni, transakcije)
    if not redovi:
        print("Nema postavljenih ciljeva.")
        return
    print(f"\n{'Izvor':<16}{'Rok':<12}{'Cilj':>12}{'Projekcija':>13}"
          f"{'Razlika':>12}  Status")
    print("-" * 80)
    for n in redovi:
        print(f"{n['Račun']:<16}{n['Rok']:<12}"
              f"{logika.hrvatski_broj(n['Iznos']):>12}"
              f"{logika.hrvatski_broj(n['Projekcija']):>13}"
              f"{logika.hrvatski_broj(n['Razlika']):>12}  {n['Status']}"
              + (f"  (treba ~{logika.hrvatski_broj(n['Mjesecno'])} €/mj)"
                 if n["Mjesecno"] else ""))
    print()


def _unos(poruka):
    """
    `input` koji na EOF uredno izađe.

    Bez ovoga skripta pukne s EOFError kad stdin presuši (Ctrl+Z, preusmjeren
    ulaz, pokretanje iz skripte).
    """
    try:
        return input(poruka).strip()
    except EOFError:
        print()
        raise SystemExit(0) from None


def _main():
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    racuni, transakcije = logika.ucitaj()
    ciljevi = ucitaj()

    while True:
        _ispisi(ciljevi, racuni, transakcije)
        print("1) Postavi/izmijeni cilj   2) Obriši cilj   0) Izlaz")
        odabir = _unos("Odabir: ")

        if odabir == "0":
            return
        if odabir == "1":
            print(f"Izvori: {', '.join([*racuni, UKUPNO])}")
            racun = _unos("Izvor: ")
            iznos = _unos("Koliko želim da ostane (EUR): ")
            rok = _unos("Rok (DD.MM.YYYY): ")
            napomena = _unos("Napomena (neobavezno): ")
            try:
                ciljevi, promijenjen = postavi(
                    ciljevi, racun, iznos, rok, racuni, napomena
                )
                spremi(ciljevi)
                print("✅ Cilj izmijenjen." if promijenjen else "✅ Cilj postavljen.")
            except (ValueError, OSError) as e:
                print(f"❌ {e}")
        elif odabir == "2":
            racun = _unos("Izvor: ")
            rok = _unos("Rok (DD.MM.YYYY): ")
            try:
                ciljevi, n = obrisi(ciljevi, racun, rok)
                spremi(ciljevi)
                print(f"✅ Obrisano ciljeva: {n}." if n else "Nema takvog cilja.")
            except (ValueError, OSError) as e:
                print(f"❌ {e}")
        else:
            print("Nepoznat odabir.")


if __name__ == "__main__":
    _main()
