"""
Web (Streamlit) verzija financijskog menadžera.

Unos se uređuje IZRAVNO u tablici (st.data_editor); ugrađena alatna traka
tablice je skrivena jer sve njezine radnje stoje u bočnom izborniku.
Redovi se označavaju kvačicom u stupcu „✓”, a odjeljak „⚡ Rad sa stavkama” u
bočnom izborniku nudi tri gumba jedan ispod drugoga:
    • „Dodaj stavku”   → popup s obrascem (datum, iznos, opis, tip, izvor)
    • ikona kopiranja  → kopija svake označene stavke (datum = danas)
    • ikona koša       → brisanje označenih; otvara popup za potvrdu
Ispod je „🧰 Alati tablice”: prikaz stupaca, izvoz u CSV i traženje. Traženje
samo filtrira prikaz — skrivene stavke se pri svakoj akciji vraćaju
nepromijenjene, pa se ne mogu izgubiti.
Izvori se dodaju/brišu u odjeljku „Upravljanje izvorima” (zaštićeni se ne brišu;
pri brisanju se bira račun na koji se premještaju stavke).
Ispod toga je „🎯 Ciljevi po izvorima” — gumb „Postavi cilj” otvara popup za
novi cilj, izmjenu ili brisanje (koliko želim da OSTANE na izvoru do zadanog
roka). Napredak po ciljevima prikazuje se u tabu „🔮 Buduće”. Logika je u
`ciljevi.py`, istom modulu koji koristi i samostalna skripta `uv run ciljevi.py`.
Promjene se potvrđuju gumbom „Spremi promjene”, nakon čega se preračunava
tablica sljedivosti. Sva logika i podaci dolaze iz `logika.py` – isti izvor
kao terminalska verzija.

Pokretanje:
    uv run streamlit run app.py
"""

import contextlib
import os
from datetime import date, datetime

import pandas as pd
import streamlit as st

import ciljevi
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


def sakrij_ugradenu_alatnu():
    """
    Skriva ugrađenu alatnu traku tablica u tabovima „Unos” i „Detalji”
    (＋ Add row, Show/hide columns, Download as CSV, Search, Fullscreen).

    U „Unosu” sve te radnje stoje u bočnom izborniku, pa bi ih dvostruko nuditi
    samo zbunjivalo; „Detalji” je skriva da izgleda isto. Pravilo se veže na
    klasu `st-key-<ključ>` koju Streamlit doda na `st.container(key=...)` — tako
    tablice u „Danas” i „Buduće” zadrže alatnu traku (tamo je izvoz u CSV,
    traženje i cijeli ekran jedini način da se do njih dođe).
    """
    st.markdown(
        """
        <style>
        .st-key-tablica_unosa div[data-testid="stElementToolbarButtonContainer"],
        .st-key-tablica_detalji div[data-testid="stElementToolbarButtonContainer"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


BOJE_TABOVA = [
    # (ikona, naziv, ključ kontejnera, boja)
    ("📅", "Danas", "danas", "#1264A3"),      # plava – sadašnjost
    ("🔮", "Buduće", "buduce", "#6B3FA0"),    # ljubičasta – projekcija
    ("✏️", "Unos", "unos", "#A2590F"),        # jantarna – rad/uređivanje
    ("📊", "Detalji", "detalji", "#146B54"),  # zelena – analiza
]


# Podloga glavnog prostora (stMainBlockContainer). Tema u .streamlit/config.toml
# namjerno prati sistemsku postavku, pa uz svjetlo sivu treba i tamni par —
# inače bi u tamnoj temi svijetli tekst pao na svijetlu podlogu.
SIVA_PODLOGA = "#F0F2F6"        # svijetla tema: svjetlo siva
SIVA_PODLOGA_TAMNA = "#1B1F27"  # tamna tema: sivo malo svjetlije od pozadine


def u_rgba(hx, alfa):
    """'#1264A3' + prozirnost → 'rgba(18, 100, 163, 0.07)'.

    Prozirna boja se stapa s pozadinom stranice, pa isti ton radi i u svijetloj
    i u tamnoj temi (puna boja bi u jednoj od njih bila preagresivna).
    """
    r, g, b = (int(hx[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r}, {g}, {b}, {alfa})"


def ubaci_css_tabova():
    """
    Veći tabovi na vrhu stranice, svaki u svojoj boji, i stranica ispod u istom
    tonu.

    Svaki tab je puna ploha svoje boje s bijelim tekstom — zato je čitljiv i u
    svijetloj i u tamnoj temi (boja ne ovisi o pozadini stranice). Neodabrani su
    prigušeni `filterom` (a ne prozirnošću teksta) da kontrast bijelog na boji
    ostane isti. Zadana crvena podvlaka Streamlita se skriva.

    Sadržaj svakog taba je u `st.container(key="stranica_<ključ>")`, pa mu ide
    blaga prozirna podloga iste boje i obojena gornja crta — stranica se time
    vidno spaja s tabom iznad.
    """
    pravila = "\n".join(
        f'        div[data-testid="stTabs"] button[data-baseweb="tab"]'
        f":nth-of-type({i}) {{ background: {boja}; }}"
        f"  /* {naziv} */"
        for i, (_, naziv, _, boja) in enumerate(BOJE_TABOVA, start=1)
    )
    stranice = "\n".join(
        f"""
        /* Stranica taba „{naziv}” */
        .st-key-stranica_{kljuc} {{
            background: {u_rgba(boja, 0.06)};
            border-top: 4px solid {boja};
            border-radius: 0 0 0.7rem 0.7rem;
            padding: 1.1rem 1.25rem 1.4rem 1.25rem;
        }}
        .st-key-stranica_{kljuc} hr {{ border-color: {u_rgba(boja, 0.35)}; }}
        .st-key-stranica_{kljuc} div[data-testid="stExpander"] details {{
            border-color: {u_rgba(boja, 0.35)};
        }}"""
        for _, naziv, kljuc, boja in BOJE_TABOVA
    )
    st.markdown(
        f"""
        <style>
        /* Naslov je uklonjen → tabovi idu bliže vrhu stranice. */
        .block-container {{ padding-top: 2rem !important; }}

        /* Glavni prostor: svjetlo siva podloga. */
        div[data-testid="stMainBlockContainer"] {{
            background: {SIVA_PODLOGA};
            border-radius: 0.8rem;
        }}
        @media (prefers-color-scheme: dark) {{
            div[data-testid="stMainBlockContainer"] {{
                background: {SIVA_PODLOGA_TAMNA};
            }}
        }}

        div[data-testid="stTabs"] div[data-baseweb="tab-list"] {{
            gap: 0.4rem;
            border-bottom: none;
        }}
        div[data-testid="stTabs"] button[data-baseweb="tab"] {{
            flex: 1 1 0;                        /* jednake širine, cijela traka */
            height: auto;
            min-height: 3.4rem;
            padding: 0.85rem 1rem;
            border-radius: 0.7rem 0.7rem 0 0;
            filter: saturate(0.5) brightness(0.85);
            transition: filter 0.15s ease, transform 0.15s ease;
        }}
        div[data-testid="stTabs"] button[data-baseweb="tab"] p {{
            font-size: 1.1rem !important;
            font-weight: 600 !important;
            color: #ffffff !important;
        }}
        div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {{
            filter: saturate(0.8) brightness(0.95);
        }}
        div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {{
            filter: none;                       /* odabrani je u punoj boji */
            box-shadow: 0 -3px 10px rgba(0, 0, 0, 0.18);
        }}
{pravila}
        /* Zadana podvlaka/okvir bi se borili s bojama. */
        div[data-testid="stTabs"] div[data-baseweb="tab-highlight"],
        div[data-testid="stTabs"] div[data-baseweb="tab-border"] {{
            display: none !important;
        }}

        @media (max-width: 640px) {{
            /* Na mobitelu 4 taba u jednom redu su preuski → 2 po redu. */
            div[data-testid="stTabs"] div[data-baseweb="tab-list"] {{
                flex-wrap: wrap !important;
            }}
            div[data-testid="stTabs"] button[data-baseweb="tab"] {{
                flex: 1 1 45% !important;
                min-height: 3rem;
                padding: 0.7rem 0.5rem;
            }}
            div[data-testid="stTabs"] button[data-baseweb="tab"] p {{
                font-size: 0.95rem !important;
            }}
            /* Uži rubovi stranice na malom ekranu. */
            div[class*="st-key-stranica_"] {{
                padding: 0.9rem 0.7rem 1.1rem 0.7rem !important;
            }}
        }}
{stranice}
        </style>
        """,
        unsafe_allow_html=True,
    )


ubaci_mobilni_css()
sakrij_ugradenu_alatnu()
ubaci_css_tabova()


def _ocekivana_lozinka():
    """Lozinka za pristup: iz st.secrets ili varijable okruženja FINAN_LOZINKA."""
    # secrets.toml ne mora postojati (lokalni razvoj) — tada pada na okruženje.
    with contextlib.suppress(Exception):
        if "FINAN_LOZINKA" in st.secrets:
            return str(st.secrets["FINAN_LOZINKA"])
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


def danasnji_datum():
    """
    Današnji datum — lokalno i bez vremenske zone, namjerno.

    App radi isključivo s DATUMIMA (bez vremena), za jednog korisnika u jednoj
    zoni, pa „aware” datum ne bi ništa dodao. Jedno mjesto s izuzetkom je
    čitljivije od `noqa` uz svaki poziv.
    """
    return date.today()  # noqa: DTZ011 – vidi docstring


def _parsiraj(vrijednost, oblik):
    """strptime bez vremenske zone — iz istog razloga kao `danasnji_datum`."""
    return datetime.strptime(vrijednost, oblik)  # noqa: DTZ007 – datum bez vremena


def parsiraj_datum(datum_str):
    """'DD.MM.YYYY' -> datetime.date za DateColumn."""
    return _parsiraj(datum_str, "%d.%m.%Y").date()


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
            return _parsiraj(s[:10], fmt).strftime("%d.%m.%Y")
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


KOL_ODABIR = "✓"
SVI_STUPCI = ["Datum", "Opis", "Tip", "Iznos", "Račun"]
UPUTA = (
    "Uredi ćeliju pa „Spremi promjene” · „Dodaj stavku” otvara popup za unos · "
    "označi „✓” pa klikni ikonu za dupliciranje ili brisanje · tip „Stanje” = "
    "snimka salda (poništava prijašnje stavke tog računa)."
)


def je_oznacen(row):
    """True ako je red označen kvačicom u stupcu „✓” (za akcije u izborniku)."""
    v = row.get(KOL_ODABIR)
    return bool(v) if pd.notna(v) else False


def kljuc_editora(upit=""):
    """
    Ključ editora: verzija + aktivni upit.

    Verzija se poveća nakon spremanja/dupliciranja/brisanja pa Streamlit izgradi
    svjež editor bez zaostalih izmjena i kvačica. Upit je dio ključa jer filtar
    mijenja skup redova — stare izmjene (edited_rows) odnosile bi se na pogrešne
    redove i tiho pokvarile podatke.
    """
    return f"editor_stavki_{st.session_state.get('verzija_editora', 0)}_{upit}"


def osvjezi_editor():
    """Prisili svježi editor pri sljedećem crtanju (poništi izmjene i kvačice)."""
    st.session_state["verzija_editora"] = st.session_state.get("verzija_editora", 0) + 1


def filtriraj_transakcije(transakcije, upit):
    """
    Dijeli stavke na (vidljive, skrivene) prema tekstu upita — traži po datumu,
    opisu, tipu, iznosu i računu, bez obzira na velika/mala slova.

    Skrivene stavke se pri svakoj akciji vraćaju NEPROMIJENJENE, pa filtriranje
    nikad ne briše podatke.
    """
    upit = (upit or "").strip().lower()
    if not upit:
        return list(transakcije), []
    vidljive, skrivene = [], []
    for t in transakcije:
        tekst = " ".join(
            str(t.get(k, "")) for k in ("Datum", "Opis", "Tip", "Iznos", "Račun")
        ).lower()
        (vidljive if upit in tekst else skrivene).append(t)
    return vidljive, skrivene


def prikupi_stavke(uredjeno, racuni, zauzeti_ids=()):
    """
    Validira uređenu tablicu → (stavke, greske, novi_racuni, sljedeci_id).

    `stavke` su parovi (broj_reda, stavka) da se zna koji red editora odgovara
    kojoj stavci — potrebno za dupliciranje/brisanje označenih. Prazni redovi
    (dodani pa neispunjeni) se preskaču; neispravni idu u `greske`.

    `zauzeti_ids` su ID-evi stavki koje filtar skriva — ulaze u izračun novog
    ID-a da nova stavka ne preuzme ID skrivene.
    """
    stavke, greske = [], []
    postojeci = [int(r["ID"]) for _, r in uredjeno.iterrows() if pd.notna(r["ID"])]
    postojeci += [int(i) for i in zauzeti_ids]
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

            stavke.append(
                (
                    i,
                    {
                        "ID": sid,
                        "Timeframe": logika.timeframe_iz_datuma(datum),
                        "Datum": datum,
                        "Opis": opis,
                        "Tip": tip,
                        "Iznos": iznos,
                        "Račun": racun,
                    },
                )
            )
        except ValueError as e:
            greske.append(f"Red {i}: {e}")

    return stavke, greske, novi_racuni, sljedeci


def spremi_stavke(novi_racuni, stavke):
    """Spremi stavke uz dopunjenu listu računa; vraća konačnu listu računa."""
    konacni = logika._sa_zasticenima(novi_racuni)
    konacni = logika._sa_racunima_iz_transakcija(konacni, stavke)
    logika.spremi(konacni, stavke)
    return konacni


def upozori_na_greske(greske):
    """Jedinstvena poruka kad validacija padne (ništa se ne sprema)."""
    st.warning(
        "Promjene nisu spremljene — ispravi greške:\n\n"
        + "\n".join(f"- {g}" for g in greske)
    )


def dupliciraj_oznacene(uredjeno, racuni, skrivene=()):
    """
    Duplicira redove označene u stupcu „✓” — kopija dobiva novi ID i današnji
    datum. Sprema i ostale zatečene izmjene (kao „Spremi promjene”) da se ne
    izgube, uz `skrivene` (filtrirane) stavke nepromijenjene. Vraća broj kopija,
    ili None ako validacija nije prošla.
    """
    stavke, greske, novi_racuni, sljedeci = prikupi_stavke(
        uredjeno, racuni, zauzeti_ids=[t["ID"] for t in skrivene]
    )
    if greske:
        upozori_na_greske(greske)
        return None

    oznaceni = {
        i for i, (_, r) in enumerate(uredjeno.iterrows(), start=1) if je_oznacen(r)
    }
    datum = danasnji_datum().strftime("%d.%m.%Y")
    kopije = []
    for i, stavka in stavke:
        if i not in oznaceni:
            continue
        kopija = dict(stavka)
        kopija["ID"] = sljedeci
        kopija["Datum"] = datum
        kopija["Timeframe"] = logika.timeframe_iz_datuma(datum)
        sljedeci += 1
        kopije.append(kopija)

    spremi_stavke(novi_racuni, [s for _, s in stavke] + kopije + list(skrivene))
    return len(kopije)


def obrisi_oznacene(uredjeno, racuni, skrivene=()):
    """
    Trajno briše redove označene u stupcu „✓”.

    Označeni redovi se izbacuju PRIJE validacije — tako se može obrisati i red
    koji je neispravan (npr. bez opisa), što bi inače blokiralo spremanje. Ostale
    zatečene izmjene se spremaju (kao „Spremi promjene”), a `skrivene`
    (filtrirane) stavke ostaju nepromijenjene. Vraća broj obrisanih stavki, ili
    None ako validacija ostatka nije prošla (tada se ništa ne mijenja).
    """
    oznake = pd.Series(
        [je_oznacen(r) for _, r in uredjeno.iterrows()],
        index=uredjeno.index,
        dtype=bool,
    )
    stavke, greske, novi_racuni, _ = prikupi_stavke(
        uredjeno[~oznake], racuni, zauzeti_ids=[t["ID"] for t in skrivene]
    )
    if greske:
        upozori_na_greske(greske)
        return None

    spremi_stavke(novi_racuni, [s for _, s in stavke] + list(skrivene))
    # Prazan označen red nije bio stavka u bazi → ne računa se kao obrisan.
    return sum(
        1 for _, r in uredjeno.iterrows() if je_oznacen(r) and not red_je_prazan(r)
    )


def render_alati(uredjeno, transakcije):
    """
    Alati tablice u izborniku: prikaz stupaca, izvoz CSV, traženje.

    Vrijednosti „prikaza” i „traženja” čitaju se u `render_unos` PRIJE tablice
    (iz session_state prošlog prolaza), jer se ovi widgeti crtaju nakon nje.
    """
    st.subheader("🧰 Alati tablice")

    st.multiselect(
        "👁 Prikaz stupaca",
        SVI_STUPCI,
        default=SVI_STUPCI,
        key="vidljivi_stupci",
        help="Sakrij stupce iz prikaza. Sakriveni stupci se i dalje spremaju.",
    )

    izvoz = uredjeno.drop(columns=[KOL_ODABIR, "ID"], errors="ignore").copy()
    if "Datum" in izvoz:
        izvoz["Datum"] = izvoz["Datum"].map(lambda c: datum_u_str(c) or "")
    st.download_button(
        "⤓ Izvoz CSV",
        data=izvoz.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name=f"stavke_{danasnji_datum().strftime('%Y-%m-%d')}.csv",
        mime="text/csv",
        width="stretch",
        help="Preuzmi prikazane redove (razdjelnik „;” i zarez za decimale → Excel).",
    )

    st.text_input(
        "🔍 Traži",
        key="upit_trazi",
        placeholder="opis, račun, tip, datum, iznos…",
        help=(
            f"Filtrira {len(transakcije)} stavki. Nevidljive stavke ostaju "
            "sačuvane pri spremanju. Promjena upita odbacuje neupisane izmjene."
        ),
    )


KLJUC_POPUPA = "potvrda_brisanja_otvorena"
KLJUC_POPUPA_NOVA = "nova_stavka_otvorena"


def zatvori_popup():
    """
    Očisti zastavicu koja drži popup potvrde brisanja otvorenim.

    Poziva se i na „X” u kutu (on_dismiss): bez toga bi zastavica ostala i popup
    bi se ponovno otvorio pri prvoj sljedećoj interakciji.
    """
    st.session_state.pop(KLJUC_POPUPA, None)


def zatvori_popup_nove():
    """Isto, za popup unosa nove stavke (vidi `zatvori_popup`)."""
    st.session_state.pop(KLJUC_POPUPA_NOVA, None)


@st.dialog(
    "Nova stavka",
    icon=":material/add:",
    width="large",
    on_dismiss=zatvori_popup_nove,
)
def dijalog_nove_stavke(uredjeno, racuni, skrivene):
    """
    Popup za unos nove stavke: datum, iznos, opis, tip i izvor jedno ispod
    drugoga, sa „Snimi stavku” na dnu.

    Polja su u `st.form` pa se ništa ne osvježava dok se tipka — sve se čita tek
    na potvrdu. Kao dupliciranje i brisanje, snima i zatečene izmjene tablice, a
    `skrivene` (filtrirane) stavke vraća nepromijenjene.
    """
    with st.form("obrazac_nove_stavke", border=False):
        datum = st.date_input("Datum", value=danasnji_datum(), format="DD.MM.YYYY")
        iznos = st.number_input(
            "Iznos (EUR)",
            min_value=0.01,
            step=10.0,
            value=None,
            placeholder="npr. 743,00",
        )
        opis = st.text_input("Opis", placeholder="npr. Plaća za kolovoz")
        tip = st.selectbox(
            "Tip",
            list(logika.TIPOVI),
            index=list(logika.TIPOVI).index(logika.RASHOD),
            help="„Stanje” = snimka salda računa: poništava prijašnje stavke tog računa.",
        )
        racun = st.selectbox(
            "Izvor / račun",
            list(racuni),
            help="Nove izvore dodaj u „Upravljanje izvorima”.",
        )
        st.divider()
        snimi = st.form_submit_button(
            "Snimi stavku",
            icon=":material/save:",
            type="primary",
            width="stretch",
        )

    if not snimi:
        return

    # Obavezna polja koja number_input/text_input mogu ostaviti prazna.
    if iznos is None:
        st.error("Iznos je obavezan.")
        return
    if not str(opis or "").strip():
        st.error("Opis je obavezan.")
        return

    # Tablica mora biti ispravna jer se sprema zajedno s novom stavkom.
    stavke, greske, novi_racuni, _ = prikupi_stavke(
        uredjeno, racuni, zauzeti_ids=[t["ID"] for t in skrivene]
    )
    if greske:
        upozori_na_greske(greske)
        return

    sve = [s for _, s in stavke] + list(skrivene)
    try:
        # ID računa iz cijele liste (uključivo skrivene) → bez sudara.
        nova = logika.dodaj_transakciju(
            sve, datum.strftime("%d.%m.%Y"), str(opis).strip(), tip, float(iznos), racun
        )
    except ValueError as e:
        st.error(str(e))
        return

    spremi_stavke(novi_racuni, sve)
    st.session_state["poruka_unosa"] = (
        f"Dodana stavka: {nova['Opis']} · {nova['Datum']} · "
        f"{logika.hrvatski_broj(nova['Iznos'])} € · {nova['Račun']}."
    )
    zatvori_popup_nove()
    osvjezi_editor()
    st.rerun()


@st.dialog(
    "Potvrda brisanja",
    icon=":material/delete:",
    width="medium",
    on_dismiss=zatvori_popup,
)
def dijalog_brisanja(uredjeno, racuni, skrivene, broj):
    """
    Popup potvrde brisanja: prikaže što se briše, pa „Odustani” / „Obriši”.

    `st.dialog` se ponaša kao fragment — klik unutar popupa u pravilu pokreće
    samo ovu funkciju. Otvorenost ipak držimo u `session_state` (KLJUC_POPUPA),
    da popup preživi i puni rerun cijele skripte; inače bi se zatvorio prije
    nego što klik na „Obriši” stigne do posla.
    """
    st.write(
        f"Trajno obrisati **{broj}** "
        f"{'stavku' if broj == 1 else 'stavke'}? Ovo se ne može poništiti."
    )

    maska = pd.Series(
        [je_oznacen(r) for _, r in uredjeno.iterrows()],
        index=uredjeno.index,
        dtype=bool,
    )
    pregled = uredjeno[maska].drop(columns=[KOL_ODABIR, "ID"], errors="ignore")
    if "Datum" in pregled:
        pregled = pregled.assign(
            Datum=pregled["Datum"].map(lambda c: datum_u_str(c) or "")
        )
    st.dataframe(pregled, hide_index=True, width="stretch")

    odustani, obrisi = st.columns(2)
    if odustani.button("Odustani", key="dlg_odustani", width="stretch"):
        zatvori_popup()
        st.rerun()  # zatvori popup bez ikakve promjene
    if obrisi.button(
        "Obriši",
        key="dlg_obrisi",
        icon=":material/delete:",
        type="primary",
        width="stretch",
    ):
        n = obrisi_oznacene(uredjeno, racuni, skrivene)
        if n is not None:
            st.session_state["poruka_unosa"] = f"Obrisano stavki: {n}."
            zatvori_popup()
            osvjezi_editor()
            st.rerun()  # zatvori popup i osvježi tablicu


def render_akcije(uredjeno, racuni, skrivene, transakcije):
    """
    Rad sa stavkama u bočnom izborniku: dodaj stavku, dupliciraj, briši — jedno
    ispod drugoga. Brisanje traži potvrdu u popupu (`dijalog_brisanja`).

    Zove se IZ tab-a „Unos”, nakon editora, jer joj trebaju uređeni redovi. Kako
    se ovaj kod izvodi prije bloka „Upravljanje izvorima” na kraju skripte,
    akcije završe na vrhu izbornika.
    """
    with st.sidebar:
        st.header("⚡ Rad sa stavkama")
        st.caption(UPUTA)
        broj = sum(je_oznacen(r) for _, r in uredjeno.iterrows())
        if broj:
            st.caption(f"Označeno redova: **{broj}**")
        else:
            st.caption("Označi redove kvačicom „✓” u tablici (tab „Unos”).")

        # Sva tri gumba idu jedno ispod drugoga, punom širinom izbornika.
        # Dupliciraj i briši su samo ikone (značenje nosi tooltip, broj označenih
        # natpis iznad). Stabilni `key` je nužan jer bez njega Streamlit gumb
        # prepoznaje po parametrima i izgubi klik kad se oni promijene.
        if st.button(
            "Dodaj stavku",
            icon=":material/add:",
            key="gumb_dodaj_stavku",
            width="stretch",
            help="Otvara popup za unos nove stavke.",
        ):
            st.session_state[KLJUC_POPUPA_NOVA] = True
            # Naraz može biti otvoren samo jedan popup.
            zatvori_popup()
            zatvori_popup_cilja()

        if st.button(
            "",
            icon=":material/content_copy:",
            key="gumb_dupliciraj",
            width="stretch",
            disabled=broj == 0,
            help=f"Dupliciraj označeno ({broj}) — kopija dobiva datum = danas.",
        ):
            n = dupliciraj_oznacene(uredjeno, racuni, skrivene)
            if n is not None:
                # Poruka preživi st.rerun() — inače je novi prolaz obriše.
                st.session_state["poruka_unosa"] = (
                    f"Duplicirano stavki: {n} · datum = "
                    f"{danasnji_datum().strftime('%d.%m.%Y')}."
                )
                osvjezi_editor()
                st.rerun()

        # Sam klik ništa ne briše — samo zatraži potvrdu u popupu.
        if st.button(
            "",
            icon=":material/delete:",
            key="gumb_obrisi",
            width="stretch",
            disabled=broj == 0,
            help=f"Obriši označeno ({broj}) — otvara popup za potvrdu.",
        ):
            st.session_state[KLJUC_POPUPA] = True
            # Naraz može biti otvoren samo jedan popup.
            zatvori_popup_nove()
            zatvori_popup_cilja()

        st.divider()
        render_alati(uredjeno, transakcije)
        st.divider()

    # Popupi se otvaraju IZVAN `with st.sidebar` — inače bi ih Streamlit
    # ugnijezdio u izbornik umjesto da ih prikaže preko cijele stranice.
    # Zastavica (a ne lokalna varijabla) drži popup otvorenim i kroz puni rerun.
    if st.session_state.get(KLJUC_POPUPA):
        dijalog_brisanja(uredjeno, racuni, skrivene, broj)
    elif st.session_state.get(KLJUC_POPUPA_NOVA):
        dijalog_nove_stavke(uredjeno, racuni, skrivene)


def render_unos(racuni, transakcije):
    """Uređivljiva tablica stavki + spremanje; uputa, alati i akcije su u izborniku."""
    # Alati se crtaju u izborniku NAKON tablice (trebaju uređene redove), pa im
    # vrijednosti čitamo iz prošlog prolaza — widget ih je već upisao u stanje.
    upit = st.session_state.get("upit_trazi", "")
    stupci = st.session_state.get("vidljivi_stupci") or SVI_STUPCI

    poruka = st.session_state.pop("poruka_unosa", None)
    if poruka:
        st.success(poruka)

    vidljive, skrivene = filtriraj_transakcije(transakcije, upit)
    if upit:
        st.caption(
            f"🔍 „{upit}” · prikazano {len(vidljive)} od {len(transakcije)} — "
            f"skrivenih {len(skrivene)} ostaje sačuvano pri spremanju."
        )

    df = df_iz_transakcija(vidljive)
    df.insert(0, KOL_ODABIR, False)

    # Kontejner s ključem → klasa `st-key-tablica_unosa`, na koju je vezan CSS
    # koji skriva ugrađenu alatnu traku (vidi sakrij_ugradenu_alatnu).
    with st.container(key="tablica_unosa"):
        uredjeno = st.data_editor(
            df,
            # „fixed”: ugrađeno dodavanje/brisanje redova je skriveno zajedno s
            # alatnom trakom, pa bi „dynamic” samo ostavio mrtav stupac s
            # kvačicama za odabir. Redovi se dodaju gumbom „＋ Dodaj red”, a
            # brišu preko „✓” + „🗑 Obriši” u izborniku.
            num_rows="fixed",
            hide_index=True,
            width="stretch",
            key=kljuc_editora(upit),
            column_order=[KOL_ODABIR] + [s for s in SVI_STUPCI if s in stupci],
            column_config={
                KOL_ODABIR: st.column_config.CheckboxColumn(
                    KOL_ODABIR,
                    default=False,
                    width="small",
                    help="Označi redove pa odaberi akciju u bočnom izborniku.",
                ),
                "Datum": st.column_config.DateColumn(
                    "Datum",
                    format="DD.MM.YYYY",
                    default=danasnji_datum(),
                    required=True,
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

    render_akcije(uredjeno, racuni, skrivene, transakcije)

    if st.button("💾 Spremi promjene", type="primary", width="stretch"):
        stavke, greske, novi_racuni, _ = prikupi_stavke(
            uredjeno, racuni, zauzeti_ids=[t["ID"] for t in skrivene]
        )
        if greske:
            upozori_na_greske(greske)
        else:
            nove = [s for _, s in stavke] + list(skrivene)
            konacni = spremi_stavke(novi_racuni, nove)
            st.session_state["poruka_unosa"] = (
                f"Spremljeno · ukupno stavki: {len(nove)} · računa: {len(konacni)}"
            )
            osvjezi_editor()
            st.rerun()


ZNAK_STATUSA = {
    ciljevi.OSTVAREN: "✅",
    ciljevi.PROMASEN: "❌",
    ciljevi.NA_PUTU: "🟢",
    ciljevi.MANJAK: "🟠",
}


def _prikazi_cilj(n):
    """Jedan cilj u glavnom prostoru: naslov, traka napretka i dvije metrike."""
    st.markdown(
        f"{ZNAK_STATUSA.get(n['Status'], '•')} **{n['Račun']}** · cilj "
        f"{logika.hrvatski_broj(n['Iznos'])} € do {n['Rok']}"
    )
    # Traka ima smisla samo za pozitivan cilj (kod „ne ispod −200 €” nema).
    if n["Iznos"] > 0:
        st.progress(min(n["Postotak"] / 100, 1.0))

    lijevo, desno = st.columns(2)
    lijevo.metric(
        "Projekcija na rok",
        f"{logika.hrvatski_broj(n['Projekcija'])} €",
        delta=f"{logika.hrvatski_broj(n['Razlika'])} €",
    )
    if n["Status"] == ciljevi.MANJAK and n["Mjesecno"]:
        desno.metric(
            "Manjak",
            f"{logika.hrvatski_broj(abs(n['Razlika']))} €",
            delta=f"treba ~{logika.hrvatski_broj(n['Mjesecno'])} €/mj",
            delta_color="off",
        )
    elif n["Dana"] >= 0:
        desno.metric("Dana do roka", n["Dana"])
    else:
        desno.metric("Rok prošao", f"{abs(n['Dana'])} d")
    if n["Napomena"]:
        st.caption(f"„{n['Napomena']}”")


KLJUC_POPUPA_CILJ = "ciljevi_popup_otvoren"


def zatvori_popup_cilja():
    """Zatvori popup ciljeva (i „X” u kutu) — vidi `zatvori_popup`."""
    st.session_state.pop(KLJUC_POPUPA_CILJ, None)


NOVI_CILJ = "➕ Novi cilj"


@st.dialog(
    "Ciljevi po izvorima",
    icon=":material/flag:",
    width="large",
    on_dismiss=zatvori_popup_cilja,
)
def dijalog_ciljeva(racuni, transakcije, danas):
    """
    Popup za rad s ciljevima: novi, izmjena i brisanje.

    Gornji izbornik bira na čemu radimo — „Novi cilj” ili jedan postojeći. Kod
    postojećeg se obrazac popuni njegovim vrijednostima, pa se može promijeniti
    i izvor i rok. Kako je identitet cilja par (Račun, Rok), izmjena se izvodi
    kao „obriši stari + postavi novi” — inače bi promjena roka ostavila i stari
    cilj. Taj izbornik je IZVAN `st.form` da promjena odabira odmah osvježi polja.
    """
    try:
        popis = ciljevi.ucitaj()
    except OSError as e:
        st.error(f"Ne mogu pročitati ciljeve: {e}")
        return

    st.caption(
        "Cilj = koliko želiš da OSTANE na izvoru do zadanog roka. Projekcija "
        "uzima sve unesene stavke do tog datuma, pa se poklapa s tabom „Buduće”. "
        f"Izvor „{ciljevi.UKUPNO}” je cilj za zbroj svih računa."
    )

    napreci = ciljevi.pregled(popis, racuni, transakcije, danas=danas)
    # Par (Račun, Rok) je jedinstven, pa je i oznaka jedinstvena.
    oznake = {
        f"{n['Račun']} · {n['Rok']} · {logika.hrvatski_broj(n['Iznos'])} €": n
        for n in napreci
    }
    odabir = st.selectbox("Cilj", [NOVI_CILJ, *oznake], key="odabir_cilja")
    izvorni = oznake.get(odabir)
    uredjuje = izvorni is not None

    izbori = [*racuni, ciljevi.UKUPNO]
    with st.form("obrazac_cilja", border=False):
        izvor = st.selectbox(
            "Izvor",
            izbori,
            index=izbori.index(izvorni["Račun"]) if uredjuje else 0,
        )
        iznos = st.number_input(
            "Koliko želim da ostane (EUR)",
            step=50.0,
            value=izvorni["Iznos"] if uredjuje else None,
            placeholder="npr. 1.500 (može i negativno, npr. dopušteni minus)",
        )
        rok = st.date_input(
            "Rok",
            value=(ciljevi._datum(izvorni["Rok"]) or danas) if uredjuje else danas,
            format="DD.MM.YYYY",
        )
        napomena = st.text_input(
            "Napomena",
            value=izvorni["Napomena"] if uredjuje else "",
            placeholder="neobavezno",
        )
        st.divider()
        postavi = st.form_submit_button(
            "Snimi promjene" if uredjuje else "Snimi cilj",
            icon=":material/save:",
            type="primary",
            width="stretch",
        )

    if postavi:
        if iznos is None:
            st.error("Ciljani iznos je obavezan.")
        else:
            try:
                novi = popis
                if uredjuje:
                    # Izmjena može promijeniti izvor/rok → prvo skloni stari.
                    novi, _ = ciljevi.obrisi(
                        novi, izvorni["Račun"], izvorni["Rok"]
                    )
                novi, prepisan = ciljevi.postavi(
                    novi, izvor, iznos, rok.strftime("%d.%m.%Y"), racuni, napomena
                )
                ciljevi.spremi(novi)
                st.session_state["poruka_ciljeva"] = (
                    f"Cilj {'izmijenjen' if uredjuje or prepisan else 'postavljen'}: "
                    f"{izvor} · {logika.hrvatski_broj(iznos)} € do "
                    f"{rok.strftime('%d.%m.%Y')}."
                )
                zatvori_popup_cilja()
                st.rerun()
            except (ValueError, OSError) as e:
                st.error(str(e))

    if uredjuje and st.button(
        "Obriši ovaj cilj",
        icon=":material/delete:",
        key="gumb_brisi_cilj",
        width="stretch",
    ):
        try:
            novi, n_obr = ciljevi.obrisi(popis, izvorni["Račun"], izvorni["Rok"])
            ciljevi.spremi(novi)
            st.session_state["poruka_ciljeva"] = f"Obrisano ciljeva: {n_obr}."
            zatvori_popup_cilja()
            st.rerun()
        except (ValueError, OSError) as e:
            st.error(str(e))


def render_ciljevi_gumb():
    """
    Odjeljak „Ciljevi po izvorima” u izborniku, ispod „Upravljanje izvorima”.

    Samo gumb koji otvara popup (novi / izmjena / brisanje) — pregled napretka
    stoji u tabu „🔮 Buduće”, gdje mu je i mjesto jer je riječ o projekciji.
    """
    st.header("🎯 Ciljevi po izvorima")
    poruka = st.session_state.pop("poruka_ciljeva", None)
    if poruka:
        st.success(poruka)

    st.caption("Pregled napretka je u tabu „🔮 Buduće”.")
    if st.button(
        "Postavi cilj",
        icon=":material/flag:",
        key="gumb_postavi_cilj",
        width="stretch",
        help="Otvara popup za novi cilj, izmjenu ili brisanje postojećeg.",
    ):
        st.session_state[KLJUC_POPUPA_CILJ] = True
        # Naraz može biti otvoren samo jedan popup.
        zatvori_popup()
        zatvori_popup_nove()


def render_ciljevi_pregled(racuni, transakcije, danas):
    """Napredak po ciljevima — prikazuje se u tabu „Buduće”."""
    st.subheader("🎯 Ciljevi po izvorima")
    try:
        popis = ciljevi.ucitaj()
    except OSError as e:
        st.error(f"Ne mogu pročitati ciljeve: {e}")
        return

    napreci = ciljevi.pregled(popis, racuni, transakcije, danas=danas)
    if not napreci:
        st.caption(
            "Nema postavljenih ciljeva — postavi ih gumbom „Postavi cilj” u "
            "bočnom izborniku."
        )
        return

    for n in napreci:
        _prikazi_cilj(n)
    with st.expander("📋 Tablica svih ciljeva"):
        st.dataframe(
            ciljevi.redovi_za_tablicu(popis, racuni, transakcije, danas=danas),
            hide_index=True,
            width="stretch",
        )


# --- Učitavanje podataka (isti izvor kao CLI) --------------------------------
try:
    racuni, transakcije = logika.ucitaj()
except OSError as e:
    st.error(f"Greška pri učitavanju podataka: {e}")
    st.stop()


# =============================================================================
# GLAVNI PROSTOR
# =============================================================================
redovi = logika.preracunaj_tablicu(racuni, transakcije)
danas = danasnji_datum()
stanja_danas = logika.stanja_po_racunima(racuni, transakcije, na_dan=danas)
stanja_buduce = logika.stanja_po_racunima(racuni, transakcije)
zadnji_datum_str = logika.zadnja_stavka_datum(transakcije)
ima_buducnost = bool(zadnji_datum_str and parsiraj_datum(zadnji_datum_str) > danas)


def render_hero():
    """
    Raspoloživo danas (+ buduće) — crta se na vrhu SVAKOG taba.

    Tabovi su prvi element stranice (nema naslova iznad njih), pa hero više ne
    može stajati iznad njih. Ponavljanjem u svakom tabu saldo ostaje vidljiv
    odakle god gledaš; u prikazu je uvijek samo jedan tab, pa se ne dvoji.
    """
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
    st.divider()


# Tabovi su PRVI element stranice; boje i veličina su u ubaci_css_tabova().
tab_danas, tab_buduce, tab_unos, tab_detalji = st.tabs(
    [f"{ikona} {naziv}" for ikona, naziv, _, _ in BOJE_TABOVA]
)

# Sadržaj svakog taba ide u `st.container(key="stranica_<ključ>")` — na tu klasu
# je vezana boja stranice (vidi ubaci_css_tabova).
# --- Tab: Danas --------------------------------------------------------------
with tab_danas, st.container(key="stranica_danas"):
    render_hero()
    st.caption(f"Stanje po računima na {danas.strftime('%d.%m.%Y')}")
    st.dataframe(tablica_stanja(racuni, stanja_danas), hide_index=True, width="stretch")

# --- Tab: Buduće -------------------------------------------------------------
with tab_buduce, st.container(key="stranica_buduce"):
    render_hero()
    render_ciljevi_pregled(racuni, transakcije, danas)
    st.divider()
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
with tab_unos, st.container(key="stranica_unos"):
    render_hero()
    render_unos(racuni, transakcije)

# --- Tab: Detalji ------------------------------------------------------------
with tab_detalji, st.container(key="stranica_detalji"):
    render_hero()
    st.caption("Sljedivost: obračun stanja po svakoj pojedinoj stavci.")
    if redovi:
        # Isti ključ-kontejner kao tablica unosa → i ovdje bez alatne trake
        # (vidi sakrij_ugradenu_alatnu). Danas i Buduće je zadržavaju.
        with st.container(key="tablica_detalji"):
            st.dataframe(
                redovi,
                column_order=logika.stupci_tablice(racuni),
                hide_index=True,
                width="stretch",
            )
    else:
        st.info("Baza je prazna — dodaj prvu stavku u tabu „Unos”.")


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

    # Ciljevi stoje ispod upravljanja izvorima — vežu se na iste izvore.
    st.divider()
    render_ciljevi_gumb()

# Popup ciljeva se crta IZVAN `with st.sidebar` (inače bi bio ugniježđen u
# izborniku) i tek nakon njega — a nikad uz drugi popup, jer Streamlit dopušta
# samo jedan dijalog po prolazu.
if st.session_state.get(KLJUC_POPUPA_CILJ) and not (
    st.session_state.get(KLJUC_POPUPA) or st.session_state.get(KLJUC_POPUPA_NOVA)
):
    dijalog_ciljeva(racuni, transakcije, danas)
