"""
Čista poslovna logika financijskog menadžera – BEZ korisničkog unosa/ispisa.

Ovaj modul ne zna ništa o CLI-u ni o webu: samo učitava/sprema podatke,
računa stanja i obavlja CRUD nad transakcijama i računima. Zato ga mogu
koristiti i terminalska verzija (financija.py) i web aplikacija (app.py).
"""
import json
import os
from datetime import datetime

import storage  # sinkronizacija baze s Google Cloud Storageom (ako je uključena)

# Putanja datoteke u koju se trajno sprema baza.
# Po zadanome baza se sprema uz ovu skriptu, ali putanju možeš prebaciti na
# mapu koja se sinkronizira između računala (npr. OneDrive/Google Drive/Dropbox)
# postavljanjem varijable okruženja FINAN_DB_PATH na drugom PC-u. Tako podaci
# putuju s tobom, a datoteka nikad ne ide u git repozitorij.
DATOTEKA = os.environ.get(
    "FINAN_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "financije_baza.json"),
)

PRIHOD = "Prihod"
RASHOD = "Rashod"
# "Stanje" nije priljev/odljev nego SNIMKA stanja računa na taj datum:
# u obračunu postavlja saldo tog računa na apsolutni iznos i time "zaboravlja"
# sve prijašnje transakcije tog računa. Koristi se npr. za mjesečno usklađenje.
STANJE = "Stanje"

# Svi dopušteni tipovi stavke.
TIPOVI = (PRIHOD, RASHOD, STANJE)

# Zaštićeni (preddefinirani) izvori/računi – uvijek su dostupni u padajućem
# izborniku i NE mogu se obrisati. Ostali (dodani od korisnika) se mogu brisati.
ZASTICENI_RACUNI = ["Erste Tekući", "PBZ Žiro", "Gotovina", "Revolut", "Dugovanja drugih"]

# Računi koji postoje pri prvom pokretanju (jednaki zaštićenima).
POCETNI_RACUNI = list(ZASTICENI_RACUNI)

# Hrvatski nazivi mjeseci za automatsko slaganje Timeframe-a iz datuma.
HRVATSKI_MJESECI = {
    1: "Siječanj", 2: "Veljača", 3: "Ožujak", 4: "Travanj",
    5: "Svibanj", 6: "Lipanj", 7: "Srpanj", 8: "Kolovoz",
    9: "Rujan", 10: "Listopad", 11: "Studeni", 12: "Prosinac",
}

# Početne stavke koje se koriste samo ako datoteka još ne postoji.
POCETNA_BAZA = [
    {"ID": 1, "Timeframe": "Svibanj 2026", "Datum": "26.05.2026", "Opis": "Početno stanje: Erste Tekući", "Tip": "Prihod", "Iznos": 712.35, "Račun": "Erste Tekući"},
    {"ID": 2, "Timeframe": "Svibanj 2026", "Datum": "26.05.2026", "Opis": "Početno stanje: PBZ Žiro", "Tip": "Prihod", "Iznos": 450.00, "Račun": "PBZ Žiro"},
    {"ID": 3, "Timeframe": "Svibanj 2026", "Datum": "26.05.2026", "Opis": "Početno stanje: Gotovina (Keš)", "Tip": "Prihod", "Iznos": 200.00, "Račun": "Gotovina"},
    {"ID": 4, "Timeframe": "Lipanj 2026", "Datum": "01.06.2026", "Opis": "Naplata oba Erste kredita odjednom", "Tip": "Rashod", "Iznos": 426.17, "Račun": "Erste Tekući"},
    {"ID": 5, "Timeframe": "Lipanj 2026", "Datum": "02.06.2026", "Opis": "Priliv od najma nekretnine na PBZ", "Tip": "Prihod", "Iznos": 550.00, "Račun": "PBZ Žiro"},
    {"ID": 6, "Timeframe": "Lipanj 2026", "Datum": "10.06.2026", "Opis": "Priliv redovne plaće + regresa", "Tip": "Prihod", "Iznos": 1900.00, "Račun": "Erste Tekući"},
    {"ID": 7, "Timeframe": "Lipanj 2026", "Datum": "11.06.2026", "Opis": "Plaćanje režija, pretplata i poreza", "Tip": "Rashod", "Iznos": 295.15, "Račun": "Erste Tekući"},
    {"ID": 8, "Timeframe": "Lipanj 2026", "Datum": "12.06.2026", "Opis": "Izvanredna uplata u Erste kredit (Napad)", "Tip": "Rashod", "Iznos": 710.00, "Račun": "Erste Tekući"},
]


# ---------------------------------------------------------------------------
# TRAJNO SPREMANJE (perzistencija)
# ---------------------------------------------------------------------------

def ucitaj():
    """ Vraća (racuni, transakcije). Ako datoteka ne postoji, kreira početne. """
    # Ako je uključen GCS, prvo povuci najnoviju bazu iz bucketa u lokalni cache.
    if storage.omogucen():
        try:
            storage.preuzmi(DATOTEKA)
        except Exception as e:  # noqa: BLE001 – ne rušimo app zbog mrežne greške
            raise IOError(f"Ne mogu dohvatiti bazu iz oblaka: {e}") from e

    if os.path.exists(DATOTEKA):
        try:
            with open(DATOTEKA, "r", encoding="utf-8") as f:
                podaci = json.load(f)
            if isinstance(podaci, dict):
                # Novi format: {"racuni": [...], "transakcije": [...]}
                transakcije = podaci.get("transakcije", [])
                racuni = podaci.get("racuni", [])
            else:
                # Stari format: datoteka je bila samo lista transakcija.
                transakcije = podaci
                racuni = list(POCETNI_RACUNI)
            racuni = _sa_zasticenima(racuni)
            racuni = _sa_racunima_iz_transakcija(racuni, transakcije)
            return racuni, transakcije
        except (json.JSONDecodeError, OSError) as e:
            raise IOError(f"Datoteku nije moguće pročitati: {e}") from e
    # Prvi put pokrenuto – kreni od početnih podataka i spremi.
    racuni = list(POCETNI_RACUNI)
    transakcije = [dict(t) for t in POCETNA_BAZA]
    spremi(racuni, transakcije)
    return racuni, transakcije


def _sa_zasticenima(racuni):
    """ Vraća popis s zaštićenim računima na početku (u zadanom redu), pa ostatak. """
    rezultat = list(ZASTICENI_RACUNI)
    for r in racuni:
        if r not in rezultat:
            rezultat.append(r)
    return rezultat


def _sa_racunima_iz_transakcija(racuni, transakcije):
    """ Osigurava da svi računi spomenuti u transakcijama postoje na popisu. """
    racuni = list(racuni)
    for t in transakcije:
        if t.get("Račun") and t["Račun"] not in racuni:
            racuni.append(t["Račun"])
    return racuni


def spremi(racuni, transakcije):
    """ Trajno sprema račune i transakcije u JSON datoteku (i u GCS ako je uključen). """
    with open(DATOTEKA, "w", encoding="utf-8") as f:
        json.dump({"racuni": racuni, "transakcije": transakcije},
                  f, ensure_ascii=False, indent=2)
    # Nakon lokalnog zapisa vrati bazu u oblak da promjena preživi restart instance.
    if storage.omogucen():
        try:
            storage.posalji(DATOTEKA)
        except Exception as e:  # noqa: BLE001
            raise IOError(f"Ne mogu spremiti bazu u oblak: {e}") from e


# ---------------------------------------------------------------------------
# POMOĆNE / VALIDACIJSKE FUNKCIJE  (bacaju ValueError – UI hvata i prikazuje)
# ---------------------------------------------------------------------------

def provjeri_datum(datum):
    """ Vraća datum ako je u formatu DD.MM.YYYY, inače baca ValueError. """
    datetime.strptime(datum, "%d.%m.%Y")  # baca ValueError ako ne valja
    return datum


def timeframe_iz_datuma(datum):
    """ Iz 'DD.MM.YYYY' slaže Timeframe, npr. '15.06.2026' -> 'Lipanj 2026'. """
    d = datetime.strptime(datum, "%d.%m.%Y")
    return f"{HRVATSKI_MJESECI[d.month]} {d.year}"


def provjeri_iznos(vrijednost):
    """ Pretvara u float i provjerava da je > 0; inače baca ValueError. """
    iznos = float(str(vrijednost).replace(",", "."))
    if iznos <= 0:
        raise ValueError("Iznos mora biti veći od nule.")
    return iznos


def kljuc_datuma(t):
    """ Pretvara 'DD.MM.YYYY' u sortabilni datum; neispravne baca na kraj. """
    try:
        return (datetime.strptime(t["Datum"], "%d.%m.%Y"), t["ID"])
    except (ValueError, KeyError):
        return (datetime.max, t["ID"])


def novi_id(transakcije):
    """ Sljedeći slobodan ID. """
    return max([t["ID"] for t in transakcije]) + 1 if transakcije else 1


# ---------------------------------------------------------------------------
# OBRAČUN
# ---------------------------------------------------------------------------

def hrvatski_broj(vrijednost):
    """ Hrvatski format iznosa: točka za tisućice, zarez za decimale (npr. '1.743,00'). """
    s = f"{vrijednost:,.2f}"  # US format '1,743.00'
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def stupci_tablice(racuni):
    """ Redoslijed stupaca: fiksni + jedan po svakom računu + ukupno. """
    return (["ID", "Timeframe", "Datum", "Opis transakcije", "Iznos (EUR)"]
            + list(racuni)
            + ["RASPOLOŽIV IZNOS"])


def preracunaj_tablicu(racuni, transakcije):
    """ Sortira transakcije kronološki i generira sljedivost stanja od nule. """
    stanja = {r: 0.0 for r in racuni}
    redovi = []

    for t in sorted(transakcije, key=kljuc_datuma):
        iznos_vrijednost = t["Iznos"]
        tip = t["Tip"]

        stanja.setdefault(t["Račun"], 0.0)
        if tip == STANJE:
            # Snimka: postavi saldo na apsolutnu vrijednost (zaboravi prijašnje).
            stanja[t["Račun"]] = iznos_vrijednost
        elif tip == RASHOD:
            stanja[t["Račun"]] -= iznos_vrijednost
        else:
            stanja[t["Račun"]] += iznos_vrijednost
        raspolozivo = sum(stanja.values())

        if tip == STANJE:
            prikaz_iznosa = f"={hrvatski_broj(iznos_vrijednost)}"
        elif tip == RASHOD:
            prikaz_iznosa = f"-{hrvatski_broj(iznos_vrijednost)}"
        else:
            prikaz_iznosa = f"+{hrvatski_broj(iznos_vrijednost)}"

        red = {
            "ID": t["ID"],
            "Timeframe": t["Timeframe"],
            "Datum": t["Datum"],
            "Opis transakcije": t["Opis"],
            "Iznos (EUR)": prikaz_iznosa,
            "RASPOLOŽIV IZNOS": hrvatski_broj(raspolozivo),
        }
        for r in racuni:
            red[r] = hrvatski_broj(stanja.get(r, 0.0))
        redovi.append(red)

    return redovi


def stanja_po_racunima(racuni, transakcije):
    """
    Vraća {racun: trenutno_stanje} uzimajući u obzir 'Stanje' resete:
    zadnja snimka stanja nekog računa poništava sve prijašnje transakcije tog
    računa, a priljevi/odljevi nakon nje se pribrajaju/oduzimaju od te snimke.
    """
    stanja = {r: 0.0 for r in racuni}
    for t in sorted(transakcije, key=kljuc_datuma):
        stanja.setdefault(t["Račun"], 0.0)
        if t["Tip"] == STANJE:
            stanja[t["Račun"]] = t["Iznos"]
        elif t["Tip"] == RASHOD:
            stanja[t["Račun"]] -= t["Iznos"]
        else:
            stanja[t["Račun"]] += t["Iznos"]
    return stanja


def pregled_racuna(racuni, transakcije):
    """
    Za svaki račun vraća red s trenutnim stanjem i datumom zadnje snimke
    ('Stanje') od koje to stanje vrijedi. Pogodno za tablicu/prikaz.
    """
    stanja = {r: 0.0 for r in racuni}
    zadnja_snimka = {}
    for t in sorted(transakcije, key=kljuc_datuma):
        r = t["Račun"]
        stanja.setdefault(r, 0.0)
        if t["Tip"] == STANJE:
            stanja[r] = t["Iznos"]
            zadnja_snimka[r] = t["Datum"]
        elif t["Tip"] == RASHOD:
            stanja[r] -= t["Iznos"]
        else:
            stanja[r] += t["Iznos"]

    return [
        {
            "Račun / izvor": r,
            "Trenutno stanje (EUR)": hrvatski_broj(stanja.get(r, 0.0)),
            "Vrijedi od (zadnja snimka)": zadnja_snimka.get(r, "—"),
        }
        for r in racuni
    ]


# ---------------------------------------------------------------------------
# CRUD NAD PODACIMA  (mijenjaju liste na mjestu; UI je dužan pozvati spremi())
# ---------------------------------------------------------------------------

def dodaj_racun(racuni, naziv):
    """ Dodaje novi račun ako ne postoji. Vraća True ako je dodan. """
    naziv = naziv.strip()
    if not naziv:
        raise ValueError("Naziv računa ne smije biti prazan.")
    if naziv in racuni:
        return False
    racuni.append(naziv)
    return True


def je_zasticen(naziv):
    """ True ako je račun preddefiniran (zaštićen) i ne može se obrisati. """
    return naziv in ZASTICENI_RACUNI


def obrisi_racun(racuni, transakcije, naziv, cilj):
    """
    Briše nezaštićeni račun 'naziv' i premješta sve njegove stavke na 'cilj'.
    Vraća broj premještenih stavki. Baca ValueError na neispravan zahtjev.
    """
    if je_zasticen(naziv):
        raise ValueError(f"Račun '{naziv}' je preddefiniran i ne može se obrisati.")
    if naziv not in racuni:
        raise ValueError(f"Račun '{naziv}' ne postoji.")
    if cilj not in racuni or cilj == naziv:
        raise ValueError("Odaberi valjani ciljni račun za premještanje stavki.")

    premjesteno = 0
    for t in transakcije:
        if t.get("Račun") == naziv:
            t["Račun"] = cilj
            premjesteno += 1
    racuni.remove(naziv)
    return premjesteno


def dodaj_transakciju(transakcije, datum, opis, tip, iznos, racun):
    """ Validira ulaz, slaže novu transakciju i dodaje je. Vraća novu stavku. """
    datum = provjeri_datum(datum)
    iznos = provjeri_iznos(iznos)
    if tip not in TIPOVI:
        raise ValueError(f"Nepoznat tip: {tip}")

    stavka = {
        "ID": novi_id(transakcije),
        "Timeframe": timeframe_iz_datuma(datum),
        "Datum": datum,
        "Opis": opis,
        "Tip": tip,
        "Iznos": iznos,
        "Račun": racun,
    }
    transakcije.append(stavka)
    return stavka


def dohvati_stavku(transakcije, stavka_id):
    """ Vraća transakciju s danim ID-em ili None. """
    return next((t for t in transakcije if t["ID"] == stavka_id), None)


def uredi_transakciju(transakcije, stavka_id, **promjene):
    """
    Mijenja zadana polja stavke (Datum, Opis, Tip, Iznos, Račun).
    Datum i Iznos se validiraju; Timeframe se uvijek preračunava iz datuma.
    Vraća izmijenjenu stavku ili None ako ID ne postoji.
    """
    stavka = dohvati_stavku(transakcije, stavka_id)
    if stavka is None:
        return None

    if "Datum" in promjene and promjene["Datum"]:
        stavka["Datum"] = provjeri_datum(promjene["Datum"])
        stavka["Timeframe"] = timeframe_iz_datuma(stavka["Datum"])
    if promjene.get("Opis"):
        stavka["Opis"] = promjene["Opis"]
    if promjene.get("Tip") in TIPOVI:
        stavka["Tip"] = promjene["Tip"]
    if "Iznos" in promjene and promjene["Iznos"] not in (None, ""):
        stavka["Iznos"] = provjeri_iznos(promjene["Iznos"])
    if promjene.get("Račun"):
        stavka["Račun"] = promjene["Račun"]

    return stavka


def obrisi_transakcije(transakcije, ids):
    """ Briše sve stavke čiji je ID u 'ids'. Vraća (obrisani_ids, nepostojeci_ids). """
    trazeni = set(ids)
    za_brisanje = [t for t in transakcije if t["ID"] in trazeni]
    obrisani = [t["ID"] for t in za_brisanje]
    nepostojeci = sorted(trazeni - set(obrisani))
    for t in za_brisanje:
        transakcije.remove(t)
    return obrisani, nepostojeci
