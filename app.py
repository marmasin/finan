"""
Web (Streamlit) verzija financijskog menadžera.

Sve akcije rade se IZRAVNO u tablici (st.data_editor):
    • uređivanje ćelije            → uredi stavku
    • dodavanje novog reda (＋)     → nova stavka (datum je unaprijed = danas)
    • brisanje reda (🗑)           → obriši stavku
    • „Račun” je padajući izbornik preddefiniranih + dodanih izvora
Izvori se dodaju/brišu u odjeljku „Upravljanje izvorima” (zaštićeni se ne brišu;
pri brisanju se bira račun na koji se premještaju stavke).
Promjene se potvrđuju gumbom „Spremi promjene”, nakon čega se preračunava
tablica sljedivosti. Sva logika i podaci dolaze iz `logika.py` – isti izvor
kao terminalska verzija.

Pokretanje:
    .venv\\Scripts\\streamlit run app.py
"""

import os
from datetime import date, datetime

import pandas as pd
import streamlit as st

import logika

st.set_page_config(page_title="Financijski menadžer", page_icon="💶", layout="wide")


def _ocekivana_lozinka():
    """Lozinka za pristup: iz st.secrets ili varijable okruženja FINAN_LOZINKA."""
    try:
        if "FINAN_LOZINKA" in st.secrets:
            return str(st.secrets["FINAN_LOZINKA"])
    except Exception:  # noqa: BLE001 – secrets.toml ne mora postojati lokalno
        pass
    return os.environ.get("FINAN_LOZINKA")


def zahtijevaj_prijavu():
    """
    Zaključava app lozinkom. Ako lozinka nije postavljena (lokalni razvoj),
    pristup je slobodan. U oblaku (Cloud Run) postavi FINAN_LOZINKA kao secret.
    """
    lozinka = _ocekivana_lozinka()
    if not lozinka:  # nije postavljeno → ne zaključavamo (npr. lokalno)
        return
    if st.session_state.get("prijavljen"):
        return

    st.title("🔒 Prijava")
    unos = st.text_input("Lozinka", type="password")
    if st.button("Prijavi se"):
        if unos == lozinka:
            st.session_state["prijavljen"] = True
            st.rerun()
        else:
            st.error("Pogrešna lozinka.")
    st.stop()


zahtijevaj_prijavu()


def parsiraj_datum(datum_str):
    """'DD.MM.YYYY' -> datetime.date za DateColumn."""
    return datetime.strptime(datum_str, "%d.%m.%Y").date()


def df_iz_transakcija(transakcije):
    """Slaže uređivljivi DataFrame (kronološki) iz liste transakcija."""
    redovi = [
        {
            "ID": t["ID"],
            "Datum": parsiraj_datum(t["Datum"]),
            "Opis": t["Opis"],
            "Tip": t["Tip"],
            "Iznos": float(t["Iznos"]),
            "Račun": t["Račun"],
        }
        for t in sorted(transakcije, key=logika.kljuc_datuma)
    ]
    df = pd.DataFrame(redovi, columns=["ID", "Datum", "Opis", "Tip", "Iznos", "Račun"])
    # Datum kao pravi datetime tip da ga data_editor vrati kao Timestamp, ne string.
    df["Datum"] = pd.to_datetime(df["Datum"])
    return df


def datum_u_str(cell):
    """
    Pretvara ćeliju datuma iz editora u 'DD.MM.YYYY'. Ćelija može biti
    datetime.date / pandas.Timestamp ili string (npr. ISO 'YYYY-MM-DD').
    Vraća None ako je prazna.
    """
    if pd.isna(cell):
        return None
    if hasattr(cell, "strftime"):
        return cell.strftime("%d.%m.%Y")
    s = str(cell).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):  # editor vraća ISO; podržimo i hrv. zapis
        try:
            return datetime.strptime(s[:10], fmt).strftime("%d.%m.%Y")
        except ValueError:
            continue
    return pd.to_datetime(s).strftime("%d.%m.%Y")


def red_je_prazan(row):
    """True ako je red u editoru potpuno prazan (npr. dodan pa neispunjen)."""
    return (
        pd.isna(row["Datum"])
        and not str(row["Opis"] or "").strip()
        and not str(row["Račun"] or "").strip()
        and pd.isna(row["Iznos"])
    )


# --- Učitavanje podataka (isti izvor kao CLI) --------------------------------
try:
    racuni, transakcije = logika.ucitaj()
except IOError as e:
    st.error(f"Greška pri učitavanju podataka: {e}")
    st.stop()


# =============================================================================
# GLAVNI PROSTOR
# =============================================================================
st.title("💶 Financijski menadžer — kontrola likvidnosti")
st.caption(
    "Web verzija · podaci i obračun dijele se s terminalskom verzijom (logika.py)"
)

redovi = logika.preracunaj_tablicu(racuni, transakcije)

# --- Sažetak stanja po računima ----------------------------------------------
if redovi:
    zadnji = redovi[-1]
    cols = st.columns(len(racuni) + 1)
    for col, r in zip(cols, racuni):
        col.metric(r, f"{zadnji[r]} €")
    cols[-1].metric("💰 RASPOLOŽIVO", f"{zadnji['RASPOLOŽIV IZNOS']} €")


# --- Trenutna stanja po računima/izvorima ------------------------------------
st.subheader("🏦 Stanja po računima")
st.caption(
    "Trenutni saldo svakog izvora. Snimka tipa „Stanje” poništava prijašnje "
    "stavke tog računa — saldo tada kreće od unesenog iznosa."
)
st.dataframe(
    logika.pregled_racuna(racuni, transakcije),
    hide_index=True,
    width="stretch",
)


# --- Upravljanje izvorima/računima -------------------------------------------
with st.expander("🏦 Upravljanje izvorima / računima"):
    st.caption(
        "Preddefinirani (zaštićeni) izvori — ne mogu se obrisati: "
        + ", ".join(logika.ZASTICENI_RACUNI)
    )

    with st.form("dodaj_racun", clear_on_submit=True):
        naziv = st.text_input("Naziv novog izvora / računa (npr. Wallet, Kredit)")
        if st.form_submit_button("➕ Dodaj izvor"):
            try:
                if logika.dodaj_racun(racuni, naziv):
                    logika.spremi(racuni, transakcije)
                    st.success(f"Izvor „{naziv.strip()}” dodan.")
                    st.rerun()
                else:
                    st.info(f"Izvor „{naziv.strip()}” već postoji.")
            except ValueError as e:
                st.warning(str(e))

    st.divider()
    obrisivi = [r for r in racuni if not logika.je_zasticen(r)]
    if not obrisivi:
        st.caption("Trenutno nema izvora koji se mogu obrisati.")
    else:
        c1, c2 = st.columns(2)
        za_brisanje = c1.selectbox("Obriši izvor", obrisivi, key="del_racun")
        ciljevi = [r for r in racuni if r != za_brisanje]
        cilj = c2.selectbox("Premjesti njegove stavke u", ciljevi, key="cilj_racun")
        if st.button("🗑 Obriši izvor i premjesti stavke", type="primary"):
            try:
                n = logika.obrisi_racun(racuni, transakcije, za_brisanje, cilj)
                logika.spremi(racuni, transakcije)
                st.success(
                    f"Izvor „{za_brisanje}” obrisan · premješteno stavki: {n} → „{cilj}”."
                )
                st.rerun()
            except ValueError as e:
                st.warning(str(e))


# --- Uređivljiva tablica: sve akcije na jednom mjestu ------------------------
st.subheader("✏️ Stavke — uredi izravno u tablici")
st.caption(
    "Uredi ćeliju · dodaj red (＋) za novu stavku (datum = danas) · označi i obriši (🗑) · "
    "„Račun” biraš iz izbornika · tip „Stanje” = mjesečna snimka salda "
    "(poništava prijašnje stavke tog računa). Zatim „Spremi promjene”."
)

uredjeno = st.data_editor(
    df_iz_transakcija(transakcije),
    num_rows="dynamic",
    hide_index=True,
    width="stretch",
    key="editor_stavki",
    # ID se ne prikazuje (izostavljen iz column_order), ali ostaje u podacima
    # radi prepoznavanja postojećih stavki pri spremanju.
    column_order=["Datum", "Opis", "Tip", "Iznos", "Račun"],
    column_config={
        "Datum": st.column_config.DateColumn(
            "Datum", format="DD.MM.YYYY", default=date.today(), required=True
        ),
        "Opis": st.column_config.TextColumn("Opis", required=True),
        "Tip": st.column_config.SelectboxColumn(
            "Tip",
            options=list(logika.TIPOVI),
            default=logika.RASHOD,
            required=True,
            help="„Stanje” = snimka salda računa: poništava prijašnje stavke tog računa.",
        ),
        "Iznos": st.column_config.NumberColumn(
            "Iznos (EUR)",
            min_value=0.01,
            step=10.0,
            format="localized",
            required=True,
            help="Zarez za decimale (npr. 743,00).",
        ),
        "Račun": st.column_config.SelectboxColumn(
            "Račun / izvor",
            options=list(racuni),
            required=True,
            help="Odaberi izvor. Nove izvore dodaj u „Upravljanje izvorima”.",
        ),
    },
)

if st.button("💾 Spremi promjene", type="primary", width="stretch"):
    nove = []
    greske = []
    # ID-evi postojećih redova → osnova za dodjelu ID-a novim redovima.
    postojeci = [int(r["ID"]) for _, r in uredjeno.iterrows() if pd.notna(r["ID"])]
    sljedeci = (max(postojeci) + 1) if postojeci else 1
    # Kreni od trenutnih računa da se sačuvaju i oni bez transakcija.
    novi_racuni = list(racuni)

    for i, (_, row) in enumerate(uredjeno.iterrows(), start=1):
        if red_je_prazan(row):
            continue
        try:
            datum = datum_u_str(row["Datum"])
            if datum is None:
                raise ValueError("Datum je obavezan.")
            datum = logika.provjeri_datum(datum)

            opis = str(row["Opis"] or "").strip()
            if not opis:
                raise ValueError("Opis je obavezan.")

            tip = str(row["Tip"])
            if tip not in logika.TIPOVI:
                raise ValueError(f"Nepoznat tip: {tip}")

            iznos = logika.provjeri_iznos(row["Iznos"])

            racun = str(row["Račun"] or "").strip()
            if not racun:
                raise ValueError("Račun je obavezan.")
            if racun not in novi_racuni:
                novi_racuni.append(racun)

            if pd.notna(row["ID"]):
                sid = int(row["ID"])
            else:
                sid = sljedeci
                sljedeci += 1

            nove.append(
                {
                    "ID": sid,
                    "Timeframe": logika.timeframe_iz_datuma(datum),
                    "Datum": datum,
                    "Opis": opis,
                    "Tip": tip,
                    "Iznos": iznos,
                    "Račun": racun,
                }
            )
        except ValueError as e:
            greske.append(f"Red {i}: {e}")

    if greske:
        st.warning(
            "Promjene nisu spremljene — ispravi greške:\n\n"
            + "\n".join(f"- {g}" for g in greske)
        )
    else:
        racuni = logika._sa_zasticenima(novi_racuni)
        racuni = logika._sa_racunima_iz_transakcija(racuni, nove)
        logika.spremi(racuni, nove)
        st.success(f"Spremljeno · ukupno stavki: {len(nove)} · računa: {len(racuni)}")
        st.rerun()


# --- Read-only tablica sljedivosti (obračun stanja) --------------------------
st.subheader("📊 Tablica sljedivosti")
if redovi:
    st.dataframe(
        redovi,
        column_order=logika.stupci_tablice(racuni),
        hide_index=True,
        width="stretch",
    )
else:
    st.info("Baza je prazna — dodaj prvi red u tablici iznad.")
