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


def tablica_stanja(racuni, stanja):
    """Uredan popis {Račun, Stanje (EUR)} za prikaz u tablici (mobilno čisto)."""
    return [
        {"Račun": r, "Stanje (EUR)": logika.hrvatski_broj(stanja.get(r, 0.0))}
        for r in racuni
    ]


def render_unos(racuni, transakcije):
    """Uređivljiva tablica stavki + gumb za spremanje (tab „Unos”)."""
    st.caption(
        "Uredi ćeliju · dodaj red (＋) za novu stavku (datum = danas) · označi i "
        "obriši (🗑) · tip „Stanje” = snimka salda (poništava prijašnje stavke tog "
        "računa). Zatim „Spremi promjene”."
    )
    uredjeno = st.data_editor(
        df_iz_transakcija(transakcije),
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        key="editor_stavki",
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
        postojeci = [int(r["ID"]) for _, r in uredjeno.iterrows() if pd.notna(r["ID"])]
        sljedeci = (max(postojeci) + 1) if postojeci else 1
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


# --- Učitavanje podataka (isti izvor kao CLI) --------------------------------
try:
    racuni, transakcije = logika.ucitaj()
except IOError as e:
    st.error(f"Greška pri učitavanju podataka: {e}")
    st.stop()


# =============================================================================
# GLAVNI PROSTOR
# =============================================================================
st.title("💶 Financijski menadžer")

redovi = logika.preracunaj_tablicu(racuni, transakcije)
danas = date.today()
stanja_danas = logika.stanja_po_racunima(racuni, transakcije, na_dan=danas)
stanja_buduce = logika.stanja_po_racunima(racuni, transakcije)
zadnji_datum_str = logika.zadnja_stavka_datum(transakcije)
ima_buducnost = bool(zadnji_datum_str and parsiraj_datum(zadnji_datum_str) > danas)

# --- Hero: raspoloživo danas (+ buduće) --------------------------------------
h1, h2 = st.columns(2)
h1.metric(
    f"💰 Danas · {danas.strftime('%d.%m.%Y')}",
    f"{logika.hrvatski_broj(sum(stanja_danas.values()))} €",
)
if ima_buducnost:
    razlika = sum(stanja_buduce.values()) - sum(stanja_danas.values())
    h2.metric(
        f"🔮 Buduće · {zadnji_datum_str}",
        f"{logika.hrvatski_broj(sum(stanja_buduce.values()))} €",
        delta=f"{logika.hrvatski_broj(razlika)} €" if razlika else None,
    )

tab_danas, tab_buduce, tab_unos, tab_detalji = st.tabs(
    ["📅 Danas", "🔮 Buduće", "✏️ Unos", "📊 Detalji"]
)

# --- Tab: Danas --------------------------------------------------------------
with tab_danas:
    st.caption(f"Stanje po računima na {danas.strftime('%d.%m.%Y')}")
    st.dataframe(
        tablica_stanja(racuni, stanja_danas), hide_index=True, width="stretch"
    )
    st.metric(
        "💰 RASPOLOŽIVO", f"{logika.hrvatski_broj(sum(stanja_danas.values()))} €"
    )

# --- Tab: Buduće -------------------------------------------------------------
with tab_buduce:
    if not ima_buducnost:
        st.info("Nema unesenih stavki nakon današnjeg dana.")
    else:
        st.caption(
            f"Projekcija na {zadnji_datum_str} · Δ = promjena u odnosu na danas. "
            "Otvori račun za pripadajuće buduće stavke."
        )
        for r in racuni:
            redovi_r = redovi_sljedivosti(
                racuni, transakcije, danas, racun=r, buducnost=True
            )
            if not redovi_r:
                continue  # račun bez budućih stavki se ne prikazuje
            bud = stanja_buduce.get(r, 0.0)
            raz = bud - stanja_danas.get(r, 0.0)
            strelica = "▲" if raz > 0 else ("▼" if raz < 0 else "•")
            with st.expander(
                f"{r} · {logika.hrvatski_broj(bud)} € "
                f"({strelica} {logika.hrvatski_broj(abs(raz))} €)"
            ):
                st.dataframe(redovi_r, hide_index=True, width="stretch")

        ukupno = sum(stanja_buduce.values())
        raz_uk = ukupno - sum(stanja_danas.values())
        strelica_uk = "▲" if raz_uk >= 0 else "▼"
        with st.expander(
            f"💰 RASPOLOŽIVO · {logika.hrvatski_broj(ukupno)} € "
            f"({strelica_uk} {logika.hrvatski_broj(abs(raz_uk))} €)"
        ):
            st.dataframe(
                redovi_sljedivosti(
                    racuni, transakcije, danas, racun=None, buducnost=True
                ),
                hide_index=True,
                width="stretch",
            )

# --- Tab: Unos ---------------------------------------------------------------
with tab_unos:
    render_unos(racuni, transakcije)

# --- Tab: Detalji ------------------------------------------------------------
with tab_detalji:
    st.caption("Sljedivost: obračun stanja po svakoj pojedinoj stavci.")
    if redovi:
        st.dataframe(
            redovi,
            column_order=logika.stupci_tablice(racuni),
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("Baza je prazna — dodaj prvi red u tabu „Unos”.")


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
