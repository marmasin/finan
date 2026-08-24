"""
Terminalska (CLI) verzija financijskog menadžera.

Sva poslovna logika je u modulu `logika.py`; ovdje je samo korisničko
sučelje u terminalu (izbornik, unos, ispis tablice). Web verzija (app.py)
koristi isti `logika.py`, pa su podaci i obračun zajamčeno isti.
"""
import sys

import logika

# Na Windows konzoli (cp1252) hrvatski znakovi i emoji ruše ispis – forsiramo UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

# Učitano stanje (puni se u main()).
racuni = []
transakcije = []


def spremi():
    """ Sprema trenutno stanje i javlja eventualnu grešku. """
    try:
        logika.spremi(racuni, transakcije)
    except OSError as e:
        print(f"❌ Spremanje nije uspjelo: {e}")


# ---------------------------------------------------------------------------
# POMOĆNE FUNKCIJE ZA UNOS (interaktivno ponavljaju dok unos nije ispravan)
# ---------------------------------------------------------------------------

def unesi_datum(zadano=None):
    """ Traži datum DD.MM.YYYY. Prazan unos vraća 'zadano'. """
    poruka = f"Unesi datum (npr. 15.06.2026){f' [{zadano}]' if zadano else ''}: "
    while True:
        unos = input(poruka).strip()
        if not unos:
            return zadano
        try:
            return logika.provjeri_datum(unos)
        except ValueError:
            print("❌ Neispravan format. Koristi DD.MM.YYYY (npr. 15.06.2026).")


def unesi_pozitivan_iznos(zadano=None):
    """ Traži pozitivan iznos. Prazan unos vraća 'zadano' (None = obavezno). """
    while True:
        unos = input(f"Unesi iznos u EUR (pozitivan broj, npr. 50.00){f' [{zadano}]' if zadano is not None else ''}: ").strip()
        if not unos and zadano is not None:
            return zadano
        try:
            return logika.provjeri_iznos(unos)
        except ValueError as e:
            print(f"❌ {e if str(e) != '' else 'Neispravan iznos.'}")


def dodaj_novi_racun():
    """ Pita za naziv novog računa, dodaje ga i sprema. Vraća naziv ili None. """
    naziv = input("Naziv novog računa/izvora (npr. Revolut, Kredit): ").strip()
    if not naziv:
        print("Otkazano – naziv je prazan.")
        return None
    if logika.dodaj_racun(racuni, naziv):
        spremi()
        print(f"✅ Novi račun '{naziv}' dodan.")
    else:
        print(f"ℹ️  Račun '{naziv}' već postoji.")
    return naziv


def unesi_racun(zadano=None):
    """ Prikazuje popis računa i vraća odabrani; opcija 0 dodaje novi. """
    while True:
        print("Račun:")
        for i, r in enumerate(racuni, 1):
            print(f"  {i}. {r}")
        print("  0. + Dodaj novi račun (izvor)")
        izbor = input(f"Izbor (1-{len(racuni)}, ili 0 za novi){f' [{zadano}]' if zadano else ''}: ").strip()

        if not izbor:
            if zadano:
                return zadano
            print("❌ Moraš odabrati račun.")
            continue
        if izbor == "0":
            novi = dodaj_novi_racun()
            if novi:
                return novi
            continue
        if izbor.isdigit() and 1 <= int(izbor) <= len(racuni):
            return racuni[int(izbor) - 1]
        print("❌ Neispravan izbor, pokušaj ponovno.")


# ---------------------------------------------------------------------------
# PRIKAZ
# ---------------------------------------------------------------------------

def formatiraj_tablicu(redovi):
    """ Slaže poravnatu tekstualnu tablicu (bez vanjskih biblioteka). """
    stupci = logika.stupci_tablice(racuni)
    sirine = {s: len(s) for s in stupci}
    for red in redovi:
        for s in stupci:
            sirine[s] = max(sirine[s], len(str(red.get(s, ""))))

    zaglavlje = "  ".join(s.rjust(sirine[s]) for s in stupci)
    linije = [zaglavlje]
    for red in redovi:
        linije.append("  ".join(str(red.get(s, "")).rjust(sirine[s]) for s in stupci))
    return "\n".join(linije)


def prikazi_tablicu():
    redovi = logika.preracunaj_tablicu(racuni, transakcije)
    print("\n" + "=" * 110)
    if not redovi:
        print("(Baza je prazna – nema stavki za prikaz.)")
    else:
        print(formatiraj_tablicu(redovi))
    print("=" * 110)


# ---------------------------------------------------------------------------
# CRUD OPERACIJE (terminalsko sučelje)
# ---------------------------------------------------------------------------

def dodaj_transakciju():
    print("\n--- DODAVANJE NOVE STAVKE ---")
    datum = unesi_datum()
    print(f"📅 Timeframe automatski dodijeljen: {logika.timeframe_iz_datuma(datum)}")
    opis = input("Unesi opis stavke: ")

    print("Tip: 1. Prihod | 2. Rashod")
    tip = logika.PRIHOD if input("Izbor (1-2): ") == "1" else logika.RASHOD

    iznos = unesi_pozitivan_iznos()
    racun = unesi_racun()

    stavka = logika.dodaj_transakciju(transakcije, datum, opis, tip, iznos, racun)
    spremi()
    print(f"✅ Stavka pod ID-em {stavka['ID']} uspješno dodana i spremljena!")


def uredi_transakciju():
    print("\n--- UREĐIVANJE (EDITOR) POSTOJEĆIH STAVKI ---")
    prikazi_tablicu()

    try:
        odabir_id = int(input("\nUnesi ID stavke koju želiš promijeniti / editirati: "))
    except ValueError:
        print("❌ Neispravan unos ID-a.")
        return

    stavka = logika.dohvati_stavku(transakcije, odabir_id)
    if not stavka:
        print("❌ Stavka s tim ID-em ne postoji.")
        return

    print(f"\nMijenjaš stavku: {stavka['Opis']} ({stavka['Iznos']} EUR) | Timeframe: {stavka['Timeframe']}")
    print("*(Stisni samo ENTER ako ne želiš mijenjati to polje)*")

    novi_datum = unesi_datum(zadano=stavka["Datum"])
    novi_opis = input(f"Novi Opis [{stavka['Opis']}]: ") or None
    novi_tip_izbor = input(f"Novi Tip (1. Prihod, 2. Rashod) [{stavka['Tip']}]: ")
    novi_tip = (logika.PRIHOD if novi_tip_izbor == "1" else logika.RASHOD) if novi_tip_izbor else None
    novi_iznos = unesi_pozitivan_iznos(zadano=stavka["Iznos"])
    print(f"Trenutni račun: {stavka['Račun']}")
    novi_racun = unesi_racun(zadano=stavka["Račun"])

    logika.uredi_transakciju(
        transakcije, odabir_id,
        Datum=novi_datum, Opis=novi_opis, Tip=novi_tip,
        Iznos=novi_iznos, Račun=novi_racun,
    )
    print(f"📅 Timeframe automatski postavljen na: {stavka['Timeframe']}")
    spremi()
    print(f"✅ Stavka {odabir_id} je uspješno izmijenjena, spremljena i tablica je preračunata!")


def obrisi_transakciju():
    print("\n--- BRISANJE STAVKI ---")
    prikazi_tablicu()

    unos = input("\nUnesi ID-eve stavki koje želiš obrisati (npr. 3, 5, 8): ").strip()
    if not unos:
        print("Brisanje otkazano.")
        return

    try:
        trazeni_ids = {int(d) for d in unos.replace(",", " ").split()}
    except ValueError:
        print("❌ Neispravan unos – dopušteni su samo brojevi odvojeni zarezom ili razmakom.")
        return

    za_brisanje = [logika.dohvati_stavku(transakcije, i) for i in trazeni_ids]
    za_brisanje = [t for t in za_brisanje if t]
    if not za_brisanje:
        print("❌ Nijedna od navedenih stavki ne postoji. Ništa nije obrisano.")
        return

    print("\nBrišu se sljedeće stavke:")
    for t in za_brisanje:
        print(f"  • ID {t['ID']}: {t['Opis']} ({t['Iznos']} EUR)")

    potvrda = input(f"\nSigurno brišeš {len(za_brisanje)} stavki? (d/N): ")
    if potvrda.strip().lower() == "d":
        obrisani, nepostojeci = logika.obrisi_transakcije(transakcije, trazeni_ids)
        if nepostojeci:
            print(f"⚠️  Preskočeni nepostojeći ID-evi: {', '.join(map(str, nepostojeci))}")
        spremi()
        print(f"🗑️  Obrisane stavke ({', '.join(map(str, obrisani))}) i baza je spremljena.")
    else:
        print("Brisanje otkazano.")


def main():
    global racuni, transakcije
    try:
        racuni, transakcije = logika.ucitaj()
    except IOError as e:
        print(f"⚠️  {e}. Prekidam.")
        return

    while True:
        print("\n" + "#" * 45)
        print("   FINANCIJSKI MENADŽER - KONTROLA LIKVIDNOSTI   ")
        print("#" * 45)
        print("1. Prikaži tablicu sljedivosti i RASPOLOŽIV IZNOS")
        print("2. Dodaj novu stavku (Prihod / Rashod)")
        print("3. Uredi (Editiraj) postojeću stavku")
        print("4. Obriši stavke (jednu ili više)")
        print("5. Dodaj novi izvor / račun (npr. Revolut, kredit)")
        print("6. Izlaz")

        izbor = input("\nOdaberi opciju (1-6): ")

        if izbor == "1":
            prikazi_tablicu()
        elif izbor == "2":
            dodaj_transakciju()
        elif izbor == "3":
            uredi_transakciju()
        elif izbor == "4":
            obrisi_transakciju()
        elif izbor == "5":
            dodaj_novi_racun()
        elif izbor == "6":
            print("\nSve izmjene su trajno spremljene na disk. Pozdrav, Marko! 👋")
            break
        else:
            print("❌ Nepostojeća opcija.")


if __name__ == "__main__":
    main()
