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

st.set_page_config(
    page_title="Financijski menadžer",
    page_icon="💶",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def ubaci_mobilni_css():
    """
    CSS za izgled i ugodan rad na mobitelu.

    Samo na mobitelu, @media (max-width: 640px):
      • uži bočni razmaci (više prostora za sadržaj),
      • manji naslovi,
      • metrike se prelamaju u 2 po redu umjesto da se stisnu u jedan red,
      • kompaktniji font vrijednosti/oznaka metrika.
    """
    st.markdown(
        """
        <style>
        @media (max-width: 640px) {
            .block-container {
                padding: 1rem 0.8rem 3rem 0.8rem !important;
            }
            h1 { font-size: 1.5rem !important; }
            h2, h3 { font-size: 1.15rem !important; }

            /* Metrike/kolone: umjesto stiskanja u jedan red, prelom u mrežu */
            div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: 0.5rem !important;
            }
            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
                flex: 1 1 45% !important;
                min-width: 45% !important;
            }
            div[data-testid="stMetricValue"] { font-size: 1.1rem !important; }
            div[data-testid="stMetricLabel"] p { font-size: 0.8rem !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


ubaci_mobilni_css()


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


def redovi_sljedivosti(racuni, transakcije, danas, racun=None, buducnost=False):
    """
    Redovi sljedivosti (Datum, Opis, Tip, Iznos, Stanje nakon) za drill-down.

    racun=None → svi računi zajedno (stupac „Stanje nakon” je ukupni raspoloživ
    iznos); inače samo taj račun. buducnost=False → stavke s datumom <= danas
    (put do današnjeg stanja); True → stavke s datumom > danas (buduće).
    Poštuje „Stanje” resete po računu.
    """
    if buducnost:
        bal = logika.stanja_po_racunima(racuni, transakcije, na_dan=danas)
    else:
        bal = {r: 0.0 for r in racuni}
    redovi = []
    for t in sorted(transakcije, key=logika.kljuc_datuma):
        d = logika._datum_stavke(t)
        if d is None or (buducnost and d <= danas) or (not buducnost and d > danas):
            continue
        r = t["Račun"]
        bal.setdefault(r, 0.0)
        if t["Tip"] == logika.STANJE:
            bal[r] = t["Iznos"]
            znak = "="
        elif t["Tip"] == logika.RASHOD:
            bal[r] -= t["Iznos"]
            znak = "-"
        else:
            bal[r] += t["Iznos"]
            znak = "+"
        if racun is not None and r != racun:
            continue  # saldo je ažuriran, ali ovaj red ne prikazujemo
        saldo = bal[r] if racun is not None else sum(bal.values())
        redovi.append(
            {
                "Datum": t["Datum"],
                "Opis": t["Opis"],
                "Tip": t["Tip"],
                "Iznos (EUR)": f"{znak}{logika.hrvatski_broj(t['Iznos'])}",
                "Stanje nakon (EUR)": logika.hrvatski_broj(saldo),
            }
        )
    return redovi


def render_metrike(racuni, stanja, stanja_danas=None):
    """
    Red metrika: svaki račun + RASPOLOŽIVO. Ako je zadan stanja_danas, uz svaku
    vrijednost prikazuje se i Δ (razlika prema današnjem stanju). Bez klikanja
    (koristi se za sažetak današnjeg stanja).
    """
    def _delta(vrijednost, osnova):
        if stanja_danas is None:
            return None
        raz = vrijednost - osnova
        return f"{logika.hrvatski_broj(raz)} €" if raz else None

    cols = st.columns(len(racuni) + 1)
    for col, r in zip(cols, racuni):
        vr = stanja.get(r, 0.0)
        col.metric(
            r,
            f"{logika.hrvatski_broj(vr)} €",
            delta=_delta(vr, (stanja_danas or {}).get(r, 0.0)),
        )
    total = sum(stanja.values())
    cols[-1].metric(
        "💰 RASPOLOŽIVO",
        f"{logika.hrvatski_broj(total)} €",
        delta=_delta(total, sum((stanja_danas or {}).values())),
    )


# Posebna oznaka odabira za „RASPOLOŽIVO” (svi računi zajedno).
UKUPNO = "__ukupno__"


def render_stanja(state_key, racuni, transakcije, danas, stanja, buducnost,
                  stanja_danas=None):
    """
    Red metrika s KLIKABILNIM naslovima (svaki račun + RASPOLOŽIVO). Klik na
    naslov otvara/zatvara sljedivost tog računa ispod (toggle). Za buducnost=True
    prikazuje Δ i buduće stavke; inače stavke do današnjeg dana.
    """
    def _delta(vrijednost, osnova):
        if not (buducnost and stanja_danas is not None):
            return None
        raz = vrijednost - osnova
        return f"{logika.hrvatski_broj(raz)} €" if raz else None

    def _toggle(oznaka):
        st.session_state[state_key] = (
            None if st.session_state.get(state_key) == oznaka else oznaka
        )

    cols = st.columns(len(racuni) + 1)
    for col, r in zip(cols, racuni):
        vr = stanja.get(r, 0.0)
        if col.button(r, key=f"{state_key}_btn_{r}", type="tertiary", width="stretch"):
            _toggle(r)
        col.metric(
            r,
            f"{logika.hrvatski_broj(vr)} €",
            delta=_delta(vr, (stanja_danas or {}).get(r, 0.0)),
            label_visibility="collapsed",
        )

    total = sum(stanja.values())
    if cols[-1].button(
        "💰 RASPOLOŽIVO", key=f"{state_key}_btn_ukupno", type="tertiary",
        width="stretch",
    ):
        _toggle(UKUPNO)
    cols[-1].metric(
        "💰 RASPOLOŽIVO",
        f"{logika.hrvatski_broj(total)} €",
        delta=_delta(total, sum((stanja_danas or {}).values())),
        label_visibility="collapsed",
    )

    odabrani = st.session_state.get(state_key)
    if odabrani:
        racun = None if odabrani == UKUPNO else odabrani
        redovi_dd = redovi_sljedivosti(
            racuni, transakcije, danas, racun=racun, buducnost=buducnost
        )
        if redovi_dd:
            st.dataframe(redovi_dd, hide_index=True, width="stretch")
        else:
            ime = "sve račune" if racun is None else f"„{racun}”"
            kada = "budućih stavki" if buducnost else "stavki do danas"
            st.info(f"Nema {kada} za {ime}.")


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
danas = date.today()

# --- Sažetak: stanje na današnji dan -----------------------------------------
stanja_danas = logika.stanja_po_racunima(racuni, transakcije, na_dan=danas)
st.subheader(f"💰 Stanje na današnji dan · {danas.strftime('%d.%m.%Y')}")
render_metrike(racuni, stanja_danas)


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


# --- Buduće stanje na datum posljednje unesene stavke ------------------------
zadnji_datum_str = logika.zadnja_stavka_datum(transakcije)
if zadnji_datum_str and parsiraj_datum(zadnji_datum_str) > danas:
    stanja_buduce = logika.stanja_po_racunima(racuni, transakcije)  # sve stavke = do kraja
    st.subheader(f"🔮 Buduće stanje · na {zadnji_datum_str}")
    st.caption(
        "Projekcija salda nakon svih unesenih stavki (uključujući buduće datume). "
        "Δ = promjena u odnosu na danas. Klikni na naziv računa za buduće stavke."
    )
    render_stanja(
        "odabrani_buduci_racun", racuni, transakcije, danas, stanja_buduce,
        buducnost=True, stanja_danas=stanja_danas,
    )


# --- Bočni izbornik: upravljanje izvorima/računima ---------------------------
with st.sidebar:
    st.header("🏦 Upravljanje izvorima")
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
        za_brisanje = st.selectbox("Obriši izvor", obrisivi, key="del_racun")
        ciljevi = [r for r in racuni if r != za_brisanje]
        cilj = st.selectbox("Premjesti njegove stavke u", ciljevi, key="cilj_racun")
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


# --- Detalji (sklopivo) ------------------------------------------------------
st.divider()

with st.expander("📊 Tablica sljedivosti (obračun stanja po svakoj stavci)"):
    if redovi:
        st.dataframe(
            redovi,
            column_order=logika.stupci_tablice(racuni),
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("Baza je prazna — dodaj prvi red u tablici iznad.")
