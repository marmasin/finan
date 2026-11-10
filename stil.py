"""
Izgled web verzije — tokeni, CSS i HTML gradivni blokovi (Windows 11 / Fluent,
po uzoru na PowerToys postavke).

Zašto ovaj modul postoji: Streamlitove ugrađene komponente ne mogu dati izgled
PowerToys postavki (kartice-postavke s ikonom, naslovom i opisom lijevo te
vrijednošću desno, sloj sadržaja zaobljen uz navigaciju, Fluent boje). Zato se
prikazi koji su SAMO ZA ČITANJE crtaju kao vlastiti HTML, a Streamlit widgeti
se koriste tamo gdje treba interakcija i samo se preboje CSS-om.

Podjela odgovornosti:
    • .streamlit/config.toml — sve što Streamlit ume obojiti sam (tema, widgeti)
    • ovaj modul            — tokeni, dopunski CSS i HTML za vlastite prikaze
    • logika.py / ciljevi.py — svi izračuni i podaci (ovdje se ništa ne računa)

Tokeni su Fluentove tamne „theme resources” vrijednosti (Mica, Layer, Card,
TextFillColor…), preračunate u neprozirne boje jer Streamlit ne zna za Micu.
"""
import html
from datetime import date, datetime

import streamlit as st

import logika

# ---------------------------------------------------------------------------
# TOKENI  (Fluent / WinUI 3, tamna tema)
# ---------------------------------------------------------------------------

MICA = "#202020"          # podloga prozora i navigacije
SLOJ = "#272727"          # sloj sadržaja (LayerFillColorDefault preko Mice)
KARTICA = "#2b2b2b"       # CardBackgroundFillColorDefault
KARTICA_HOVER = "#323232"
RUB_KARTICE = "#1d1d1d"   # CardStrokeColorDefault
RAZDJELNIK = "rgba(255, 255, 255, 0.0837)"
TEKST = "#ffffff"
TEKST_2 = "#c5c5c5"       # TextFillColorSecondary
TEKST_3 = "#9a9a9a"       # TextFillColorTertiary
NAGLASAK = "#60cdff"      # zadani Windows naglasak u tamnoj temi
NAGLASAK_PLOHA = "rgba(96, 205, 255, 0.12)"

ZELENA = "#6ccb5f"        # SystemFillColorSuccess
CRVENA = "#ff99a4"        # SystemFillColorCritical
ZUTA = "#fce100"          # SystemFillColorCaution

# Ikone su Material Symbols (najbliže Segoe Fluent Icons što radi i na
# telefonu). Google Fonts šalje samo ove znakove — popis MORA biti abecedni.
IKONE = sorted({
    "account_balance", "account_balance_wallet", "add", "calendar_month",
    "cancel", "check_circle", "error", "flag", "history", "lock", "menu",
    "payments",
    "receipt_long", "savings", "schedule", "shield", "trending_down",
    "trending_up", "warning",
})

# Boja pločice uz naziv računa: (podloga, tekst) — prepoznavanje po dijelu
# naziva, pa radi i za „Erste Tekući”, „PBZ Žiro”…
_BOJE_RACUNA = [
    (("erste",), "rgba(255, 99, 99, 0.16)", "#ff8f8f"),
    (("pbz",), "rgba(96, 165, 250, 0.18)", "#8cc4ff"),
    (("gotovina", "keš", "kes", "cash"), "rgba(108, 203, 95, 0.16)", ZELENA),
    (("revolut",), "rgba(167, 139, 250, 0.18)", "#c4b5fd"),
]


def boja_racuna(naziv):
    """(podloga, boja_teksta) za pločicu računa — po nazivu, s općim padom."""
    n = (naziv or "").lower()
    for kljucne, podloga, tekst in _BOJE_RACUNA:
        if any(k in n for k in kljucne):
            return podloga, tekst
    return NAGLASAK_PLOHA, NAGLASAK


def inicijali(naziv):
    """Do dva znaka za pločicu računa: 'PBZ Žiro' → 'PB', 'Gotovina' → 'GO'."""
    return (naziv or "?").strip()[:2].upper()


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def _tokeni_css():
    """CSS varijable iz Python tokena — ostatak stilske datoteke koristi var()."""
    return f"""
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,300,0..1,0&icon_names={",".join(IKONE)}&display=block');
    :root {{
        --fin-mica: {MICA};
        --fin-sloj: {SLOJ};
        --fin-kartica: {KARTICA};
        --fin-kartica-hover: {KARTICA_HOVER};
        --fin-rub-kartice: {RUB_KARTICE};
        --fin-razdjelnik: {RAZDJELNIK};
        --fin-tekst: {TEKST};
        --fin-tekst-2: {TEKST_2};
        --fin-tekst-3: {TEKST_3};
        --fin-naglasak: {NAGLASAK};
        --fin-naglasak-ploha: {NAGLASAK_PLOHA};
        --fin-zelena: {ZELENA};
        --fin-crvena: {CRVENA};
        --fin-zuta: {ZUTA};
    }}"""


# Glavni stil. Namjerno NIJE f-string (CSS je pun vitičastih zagrada) — sve
# promjenjivo ulazi kroz var(--fin-*) iz `_tokeni_css`.
_STIL = """
    /* --- Prozor: Mica + zaobljeni sloj sadržaja uz navigaciju ------------ */
    .stApp { background: var(--fin-mica); }
    header[data-testid="stHeader"] { background: transparent; }
    section[data-testid="stMain"] {
        background: var(--fin-sloj);
        border-top-left-radius: 8px;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        border-left: 1px solid rgba(255, 255, 255, 0.05);
    }
    .block-container {
        max-width: 1100px;
        padding: 2.4rem 2.5rem calc(3rem + env(safe-area-inset-bottom, 0px)) !important;
    }
    div[data-testid="stVerticalBlock"] { gap: 0.5rem; }
    body, .stApp { font-variant-numeric: tabular-nums; }

    /* --- Navigacija (NavigationView) ------------------------------------- */
    section[data-testid="stSidebar"] { border-right: none !important; }
    section[data-testid="stSidebar"] > div { background: var(--fin-mica); }
    [data-testid="stSidebarNavItems"] { padding-top: 0.25rem; }
    a[data-testid="stSidebarNavLink"] {
        position: relative; min-height: 36px; border-radius: 4px;
        margin: 2px 0; padding-left: 14px !important;
        transition: background 0.1s ease;
    }
    a[data-testid="stSidebarNavLink"]:hover { background: rgba(255, 255, 255, 0.06); }
    a[data-testid="stSidebarNavLink"] span { color: var(--fin-tekst) !important; font-size: 14px; }
    a[data-testid="stSidebarNavLink"][aria-current="page"] { background: rgba(255, 255, 255, 0.06); }
    /* Okomita „pilula” naglaska uz odabranu stavku, kao u WinUI-ju. */
    a[data-testid="stSidebarNavLink"][aria-current="page"]::before {
        content: ""; position: absolute; left: 0; top: 50%;
        width: 3px; height: 16px; margin-top: -8px; border-radius: 2px;
        background: var(--fin-naglasak);
    }
    a[data-testid="stSidebarNavLink"][aria-current="page"] span { font-weight: 600; }
    [data-testid="stNavSectionHeader"] {
        color: var(--fin-tekst-3) !important; font-size: 12px !important;
        font-weight: 600 !important; text-transform: none !important;
        letter-spacing: 0 !important; padding-left: 14px;
    }
    [data-testid="stSidebarNavSeparator"] { border-color: var(--fin-razdjelnik); }

    /* --- Tipografija stranice -------------------------------------------- */
    .fin-naslov {
        font-size: 28px; font-weight: 600; line-height: 36px;
        color: var(--fin-tekst); margin: 0 0 0.9rem 0; letter-spacing: 0;
    }
    /* Naslov skupine kartica („Body Strong”). */
    .fin-oznaka {
        font-size: 14px; font-weight: 600; color: var(--fin-tekst);
        margin: 1.4rem 0 0.25rem 0;
    }
    .fin-mali { font-size: 12px; color: var(--fin-tekst-2); margin: 0; }

    /* --- Ikone ----------------------------------------------------------- */
    .fin-ik {
        font-family: 'Material Symbols Rounded'; font-weight: 300;
        font-style: normal; font-size: 20px; line-height: 1;
        letter-spacing: normal; text-transform: none; white-space: nowrap;
        direction: ltr; -webkit-font-smoothing: antialiased;
        font-feature-settings: 'liga'; display: inline-block;
        color: var(--fin-tekst);
    }

    /* --- Kartica-postavka (SettingsCard) -------------------------------- */
    .fin-grupa { display: flex; flex-direction: column; gap: 4px; }
    .fin-kartica {
        display: flex; align-items: center; flex-wrap: wrap; gap: 4px 16px;
        min-height: 68px; box-sizing: border-box; padding: 12px 16px;
        background: var(--fin-kartica); border: 1px solid var(--fin-rub-kartice);
        border-radius: 4px; transition: background 0.1s ease;
    }
    .fin-kartica:hover { background: var(--fin-kartica-hover); }
    .fin-kartica-ikona {
        width: 32px; display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
    }
    .fin-kartica-tekst { flex: 1 1 180px; min-width: 0; }
    .fin-kartica-naslov {
        font-size: 14px; color: var(--fin-tekst); line-height: 20px;
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .fin-kartica-opis { font-size: 12px; color: var(--fin-tekst-2); line-height: 16px; }
    .fin-kartica-desno {
        display: flex; align-items: center; gap: 12px; margin-left: auto;
        flex-wrap: wrap; justify-content: flex-end;
    }
    /* Tijelo kartice ispod zaglavlja (npr. traka napretka cilja). */
    .fin-kartica-tijelo {
        flex-basis: 100%; margin: 8px -16px -12px; padding: 12px 16px 14px 64px;
        border-top: 1px solid var(--fin-razdjelnik);
    }

    /* Pločica s inicijalima računa. */
    .fin-znak {
        width: 32px; height: 32px; border-radius: 6px; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center;
        font-size: 11px; font-weight: 600; letter-spacing: 0.02em;
    }

    /* --- Hero: zaglavlje stranice s velikom pločicom (kao PowerToys) ----- */
    .fin-hero {
        display: flex; flex-wrap: wrap; align-items: center; gap: 16px 24px;
        padding: 20px; border-radius: 8px;
        background: var(--fin-kartica); border: 1px solid var(--fin-rub-kartice);
    }
    .fin-hero-plocica {
        width: 64px; height: 64px; border-radius: 12px; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center;
        background: linear-gradient(135deg, #60cdff, #005fb8);
    }
    .fin-hero-plocica .fin-ik { font-size: 34px; color: #fff; }
    .fin-hero-oznaka { font-size: 12px; color: var(--fin-tekst-2); margin: 0 0 2px 0; }
    .fin-hero-glavno { font-size: 32px; font-weight: 600; line-height: 40px;
        color: var(--fin-tekst); margin: 0; }
    .fin-hero-drugo { font-size: 20px; font-weight: 600; line-height: 28px;
        color: var(--fin-tekst); margin: 0; }
    .fin-hero-desno {
        display: flex; align-items: center; gap: 16px; margin-left: auto;
        padding-left: 24px; border-left: 1px solid var(--fin-razdjelnik);
    }

    /* --- Brojevi i značke ------------------------------------------------ */
    .fin-broj { font-size: 14px; color: var(--fin-tekst); white-space: nowrap; }
    .fin-broj.fin-manjak { color: var(--fin-crvena); }
    .fin-znacka {
        display: inline-flex; align-items: center; gap: 4px;
        padding: 2px 8px; border-radius: 4px;
        font-size: 12px; white-space: nowrap; line-height: 16px;
    }
    .fin-znacka-prihod, .fin-znacka-rast { background: rgba(108, 203, 95, 0.14); color: var(--fin-zelena); }
    .fin-znacka-rashod, .fin-znacka-pad { background: rgba(255, 153, 164, 0.14); color: var(--fin-crvena); }
    .fin-znacka-stanje { background: rgba(255, 255, 255, 0.08); color: var(--fin-tekst-2); }
    .fin-znacka-naglasak { background: var(--fin-naglasak-ploha); color: var(--fin-naglasak); }

    /* --- Cilj: mjerila i traka napretka (ProgressBar) ------------------- */
    .fin-mjerila { display: flex; flex-wrap: wrap; gap: 8px 28px; margin-bottom: 12px; }
    .fin-mjerilo-oznaka { font-size: 12px; color: var(--fin-tekst-3); margin: 0; }
    .fin-traka {
        width: 100%; height: 4px; border-radius: 2px; overflow: hidden;
        background: rgba(255, 255, 255, 0.12);
    }
    .fin-traka > div { height: 100%; border-radius: 2px; }

    /* --- Tablica sljedivosti (DataGrid) --------------------------------- */
    .fin-tablica-okvir {
        overflow-x: auto; border: 1px solid var(--fin-rub-kartice);
        border-radius: 4px; background: var(--fin-kartica);
    }
    .fin-tablica { width: 100%; border-collapse: collapse; font-size: 13px; }
    .fin-tablica th {
        position: sticky; top: 0; background: var(--fin-kartica);
        padding: 10px 12px; text-align: left; white-space: nowrap;
        font-size: 12px; font-weight: 600; color: var(--fin-tekst-2);
        border-bottom: 1px solid var(--fin-razdjelnik);
    }
    /* Streamlit tablicama u markdownu crta okomite crte — DataGrid ih nema. */
    .fin-tablica th, .fin-tablica td { border-left: none !important; border-right: none !important; border-top: none !important; }
    .fin-tablica th.fin-desno, .fin-tablica td.fin-desno { text-align: right; }
    .fin-tablica td {
        padding: 8px 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        color: var(--fin-tekst); vertical-align: middle; white-space: nowrap;
    }
    .fin-tablica tr:last-child td { border-bottom: none; }
    .fin-tablica tbody tr:hover td { background: rgba(255, 255, 255, 0.03); }
    .fin-tablica tr.fin-buduca td { opacity: 0.55; }
    .fin-tablica td.fin-tudji { color: var(--fin-tekst-3); }
    .fin-tablica td.fin-ukupno { color: var(--fin-naglasak); font-weight: 600; }

    /* --- Streamlit widgeti u Fluent ruhu -------------------------------- */
    /* Primarni (AccentButton): naglasak s tamnim tekstom, kao u WinUI-ju. */
    button[kind="primary"], button[kind="primaryFormSubmit"] {
        background: var(--fin-naglasak) !important; border-color: var(--fin-naglasak) !important;
        color: #000 !important;
    }
    button[kind="primary"] *, button[kind="primaryFormSubmit"] * { color: #000 !important; }
    button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover { filter: brightness(0.92); }
    button[kind="secondary"], button[kind="secondaryFormSubmit"] {
        background: rgba(255, 255, 255, 0.06) !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
    }
    button[kind="secondary"]:hover { background: rgba(255, 255, 255, 0.083) !important; }

    /* Expander kao SettingsExpander. */
    div[data-testid="stExpander"] details {
        background: var(--fin-kartica); border: 1px solid var(--fin-rub-kartice);
        border-radius: 4px;
    }
    div[data-testid="stExpander"] summary { min-height: 52px; padding: 0 16px; font-size: 14px; }
    div[data-testid="stExpander"] summary:hover { background: var(--fin-kartica-hover); }

    /* Kontejneri s ključem „kartica_*” = kartica-postavka s pravim widgetima. */
    div[class*="st-key-kartica_"] {
        background: var(--fin-kartica); border: 1px solid var(--fin-rub-kartice);
        border-radius: 4px; padding: 14px 16px;
    }

    /* Popup (ContentDialog). */
    div[role="dialog"] {
        background: var(--fin-kartica) !important; border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* Oznake u višestrukom odabiru — neutralne, kao Fluent „TokenItem”. */
    span[data-baseweb="tag"] {
        background: rgba(255, 255, 255, 0.08) !important; color: var(--fin-tekst) !important;
    }
    span[data-baseweb="tag"] * { color: var(--fin-tekst) !important; }

    /* Gumb za otvaranje navigacije: ☰ (PaneToggleButton) umjesto „»”. */
    [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"] {
        font-size: 0 !important;
    }
    [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"]::after {
        content: "menu"; font-family: 'Material Symbols Rounded';
        font-size: 24px; font-feature-settings: 'liga'; color: var(--fin-tekst);
    }

    div[data-testid="stElementToolbarButtonContainer"] { display: none !important; }
    * { scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.25) transparent; }

    /* --- Telefon --------------------------------------------------------- */
    @media (max-width: 640px) {
        .block-container { padding: 3.4rem 0.9rem calc(2rem + env(safe-area-inset-bottom, 0px)) !important; }
        section[data-testid="stMain"] { border-radius: 0; border: none; }
        .fin-naslov { font-size: 24px; line-height: 32px; }
        .fin-hero { padding: 16px; }
        .fin-hero-plocica { width: 48px; height: 48px; border-radius: 10px; }
        .fin-hero-plocica .fin-ik { font-size: 26px; }
        .fin-hero-glavno { font-size: 26px; line-height: 32px; }
        .fin-hero-desno { margin-left: 0; padding-left: 0; border-left: none;
            flex-basis: 100%; }
        .fin-kartica-tijelo { padding-left: 16px; }
        /* Traka naredbi: „Spremi” preko cijele širine, ostalo dva u redu
           (Streamlit bi inače svaki stupac složio u zaseban red). */
        .st-key-traka_naredbi div[data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important; gap: 0.5rem !important;
        }
        .st-key-traka_naredbi div[data-testid="stColumn"] {
            flex: 1 1 calc(50% - 0.25rem) !important;
            min-width: calc(50% - 0.25rem) !important;
        }
        .st-key-traka_naredbi div[data-testid="stColumn"]:first-child {
            flex-basis: 100% !important;
        }
    }
"""


def ubaci_css():
    """Ubaci stil — pozvati JEDNOM, na početku skripte."""
    st.markdown(f"<style>{_tokeni_css()}{_STIL}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# HTML GRADIVNI BLOKOVI
#
# Svaki blok vraća JEDAN string i crta se jednim `st.markdown` pozivom —
# više poziva bi Streamlit razdvojio u zasebne kontejnere s prazninom između.
# ---------------------------------------------------------------------------

def _e(vrijednost):
    """Escape — nazivi računa i opisi su korisnički unos i idu u HTML."""
    return html.escape(str(vrijednost), quote=True)


def _datum(datum_str):
    """'DD.MM.YYYY' → date; neispravan datum ide „u budućnost” kao i u logici."""
    try:
        return datetime.strptime(datum_str, "%d.%m.%Y").date()  # noqa: DTZ007
    except (TypeError, ValueError):
        return date.max


def eur(vrijednost):
    """Iznos u hrvatskom formatu s valutom: 1234.5 → '1.234,50 €'."""
    return f"{logika.hrvatski_broj(vrijednost)} €"


def _predznak(vrijednost):
    """'+' za pozitivno, '' za negativno (minus već nosi sam broj)."""
    return "+" if vrijednost >= 0 else ""


def crtaj(html_kod):
    """Ispiši gotov HTML blok."""
    st.markdown(html_kod, unsafe_allow_html=True)


def ikona(ime, boja=None, velicina=None):
    """Material Symbols znak (ime iz IKONE) kao Fluent glif."""
    stil = ";".join(filter(None, [
        f"color:{boja}" if boja else "",
        f"font-size:{velicina}px" if velicina else "",
    ]))
    return f'<span class="fin-ik" style="{stil}">{ime}</span>'


def naslov(tekst):
    """Naslov stranice („Title”, 28 px) — kao naziv alata u PowerToys."""
    return f'<div class="fin-naslov">{_e(tekst)}</div>'


def oznaka(tekst):
    """Naslov skupine kartica."""
    return f'<div class="fin-oznaka">{_e(tekst)}</div>'


def kartica(ikona_html, naslov_teksta, opis="", desno="", tijelo=""):
    """
    Kartica-postavka (SettingsCard): ikona, naslov i opis lijevo, vrijednost
    desno; `tijelo` (neobavezno) ide ispod, odvojeno crtom. Na uskom ekranu
    desni dio sam prelazi ispod teksta.
    """
    opis_html = f'<div class="fin-kartica-opis">{opis}</div>' if opis else ""
    tijelo_html = f'<div class="fin-kartica-tijelo">{tijelo}</div>' if tijelo else ""
    return (
        '<div class="fin-kartica">'
        f'<div class="fin-kartica-ikona">{ikona_html}</div>'
        '<div class="fin-kartica-tekst">'
        f'<div class="fin-kartica-naslov">{_e(naslov_teksta)}</div>{opis_html}</div>'
        f'<div class="fin-kartica-desno">{desno}</div>'
        f"{tijelo_html}</div>"
    )


def grupa(kartice):
    """Niz kartica razmaknutih 4 px — jedan blok, bez Streamlitovih praznina."""
    return f'<div class="fin-grupa">{"".join(kartice)}</div>'


def kartica_s_widgetom(kljuc, ikona_ime, naslov_teksta, opis=""):
    """
    Kartica-postavka kojoj je desna strana pravi Streamlit widget (gumb,
    izbornik…). Vraća stupac u koji pozivatelj crta widget.

    Okvir dolazi iz CSS-a za kontejnere s ključem „kartica_*”.
    """
    with st.container(key=f"kartica_{kljuc}"):
        lijevo, desno = st.columns([2.6, 1], vertical_alignment="center")
        lijevo.markdown(
            '<div class="fin-kartica" style="background:none;border:none;'
            'padding:0;min-height:0">'
            f'<div class="fin-kartica-ikona">{ikona(ikona_ime)}</div>'
            '<div class="fin-kartica-tekst">'
            f'<div class="fin-kartica-naslov">{_e(naslov_teksta)}</div>'
            f'<div class="fin-kartica-opis">{_e(opis)}</div></div></div>',
            unsafe_allow_html=True,
        )
    return desno


def znacka_tipa(tip):
    """Značka za tip stavke (Prihod / Rashod / Stanje)."""
    razred = {
        logika.PRIHOD: "fin-znacka-prihod",
        logika.RASHOD: "fin-znacka-rashod",
        logika.STANJE: "fin-znacka-stanje",
    }.get(tip, "fin-znacka-stanje")
    return f'<span class="fin-znacka {razred}">{_e(tip)}</span>'


def znacka_razlike(razlika):
    """Značka s promjenom u odnosu na danas (zelena za rast, crvena za pad)."""
    razred = "fin-znacka-rast" if razlika >= 0 else "fin-znacka-pad"
    return (
        f'<span class="fin-znacka {razred}">'
        f"{_predznak(razlika)}{eur(razlika)}</span>"
    )


def hero(ukupno_danas, datum_danas, projekcija=None, datum_projekcije=None):
    """
    Zaglavlje stranice: velika pločica, ukupno raspoloživo danas i (ako ima
    budućih stavki) projekcija s razlikom — kao kartica s ilustracijom na vrhu
    svake stranice PowerToys postavki.
    """
    dijelovi = [
        '<div class="fin-hero">',
        f'<div class="fin-hero-plocica">{ikona("account_balance_wallet")}</div>',
        "<div>",
        f'<div class="fin-hero-oznaka">Ukupno raspoloživo · {_e(datum_danas)}</div>',
        f'<div class="fin-hero-glavno">{eur(ukupno_danas)}</div>',
        "</div>",
    ]
    if projekcija is not None:
        razlika = projekcija - ukupno_danas
        dijelovi += [
            '<div class="fin-hero-desno">',
            "<div>",
            f'<div class="fin-hero-oznaka">Projekcija · {_e(datum_projekcije)}</div>',
            f'<div class="fin-hero-drugo">{eur(projekcija)}</div>',
            "</div>",
            znacka_razlike(razlika),
            "</div>",
        ]
    dijelovi.append("</div>")
    return "".join(dijelovi)


def znak_racuna(racun):
    """Pločica s inicijalima u boji banke."""
    podloga, boja = boja_racuna(racun)
    return (
        f'<div class="fin-znak" style="background:{podloga};color:{boja}">'
        f"{_e(inicijali(racun))}</div>"
    )


def _broj(vrijednost, jak=False):
    manjak = " fin-manjak" if vrijednost < 0 else ""
    tezina = ' style="font-weight:600"' if jak else ""
    return f'<span class="fin-broj{manjak}"{tezina}>{eur(vrijednost)}</span>'


def kartica_stanja(racuni, stanja, opisi=None):
    """
    Stanja po računima kao niz kartica-postavki + zbirna kartica na dnu.

    `stanja` je {račun: iznos} iz `logika.stanja_po_racunima`; `opisi` je
    neobavezan {račun: tekst} za sivi redak ispod naziva.
    """
    opisi = opisi or {}
    kartice = [
        kartica(znak_racuna(r), r, _e(opisi.get(r, "")), _broj(stanja.get(r, 0.0)))
        for r in racuni
    ]
    ukupno = sum(stanja.get(r, 0.0) for r in racuni)
    kartice.append(
        kartica(
            ikona("savings", ZELENA if ukupno >= 0 else CRVENA),
            "Ukupno raspoloživo",
            f"Zbroj svih izvora ({len(racuni)})",
            _broj(ukupno, jak=True),
        )
    )
    return grupa(kartice)


def _mjerilo(oznaka_teksta, vrijednost, boja=None):
    """Jedan par „oznaka + vrijednost” u kartici cilja."""
    stil = f' style="color:{boja}"' if boja else ""
    return (
        "<div>"
        f'<div class="fin-mjerilo-oznaka">{_e(oznaka_teksta)}</div>'
        f'<span class="fin-broj"{stil}>{vrijednost}</span>'
        "</div>"
    )


def kartica_cilja(n, ikona_statusa, boja_statusa):
    """
    Kartica jednog cilja: zaglavlje kao kartica-postavka, a ispod mjerila i
    traka napretka.

    `n` je red iz `ciljevi.napredak` (Račun, Rok, Iznos, Projekcija, Razlika,
    Status, Dana, Postotak, Mjesecno, Napomena). Ovdje se NIŠTA ne računa.
    """
    dosegnut = n["Razlika"] >= 0
    boja_proj = ZELENA if dosegnut else CRVENA

    opis = f"Rok {_e(n['Rok'])}"
    if n["Napomena"]:
        opis += f" · {_e(n['Napomena'])}"
    desno = (
        f'<span class="fin-znacka" style="background:rgba(255,255,255,0.06);'
        f'color:{boja_statusa}">{_e(str(n["Status"]).capitalize())}</span>'
    )

    mjerila = [
        _mjerilo("Cilj", eur(n["Iznos"])),
        _mjerilo("Projekcija", eur(n["Projekcija"]), boja_proj),
        _mjerilo("Dana do roka" if n["Dana"] >= 0 else "Dana od roka", str(abs(n["Dana"]))),
    ]
    if not dosegnut and n["Mjesecno"]:
        mjerila.append(_mjerilo("Nedostaje mjesečno", eur(n["Mjesecno"]), CRVENA))

    # Traka napretka ima smisla samo za pozitivan cilj (kod „ne ispod −200 €”
    # postotak ne znači ništa) — isto pravilo kao u `ciljevi.napredak`.
    traka = ""
    if n["Iznos"] > 0:
        sirina = min(max(n["Postotak"], 0.0), 100.0)
        boja_trake = ZELENA if dosegnut else NAGLASAK
        traka = (
            f'<div class="fin-traka"><div style="width:{sirina:.1f}%;'
            f'background:{boja_trake}"></div></div>'
            f'<div class="fin-mali" style="text-align:right;margin-top:4px">'
            f'{n["Postotak"]:.1f} %</div>'
        )

    return kartica(
        ikona(ikona_statusa, boja_statusa),
        n["Račun"],
        opis,
        desno,
        tijelo=f'<div class="fin-mjerila">{"".join(mjerila)}</div>{traka}',
    )


def red_zbroja(naslov_teksta, vrijednost, razlika=None):
    """Istaknuta zbirna kartica (npr. „Ukupno raspoloživo” u projekciji)."""
    znak = znacka_razlike(razlika) if razlika is not None else ""
    return kartica(
        ikona("savings", NAGLASAK),
        naslov_teksta,
        "Nakon svih unesenih budućih stavki",
        f"{znak}{_broj(vrijednost, jak=True)}",
    )


def tablica_sljedivosti(redovi, racuni, danas):
    """
    Tablica revizijskog traga.

    `redovi` su iz `logika.preracunaj_tablicu`; sirove vrijednosti se čitaju iz
    ključa „Stavka” koji ta funkcija dodaje. Buduće stavke (datum > danas) su
    prigušene, a stanje računa na koji stavka pripada je istaknuto.
    """
    STUPCI = [
        ("Datum", False), ("Opis", False), ("Tip", False),
        ("Iznos", True), ("Izvor", False),
    ]
    zaglavlje = "".join(
        f'<th class="{"fin-desno" if desno else ""}">{tekst}</th>'
        for tekst, desno in STUPCI
    )
    zaglavlje += "".join(f'<th class="fin-desno">{_e(r)}</th>' for r in racuni)
    zaglavlje += (
        f'<th class="fin-desno" style="color:{NAGLASAK}">Ukupno</th>'
    )

    tijelo = []
    for red in redovi:
        s = red["Stavka"]
        razred = "fin-buduca" if _datum(red["Datum"]) > danas else ""
        boja_iznosa = {
            logika.PRIHOD: ZELENA,
            logika.RASHOD: CRVENA,
        }.get(s["Tip"], TEKST_2)

        celije = [
            f'<td class="fin-mali">{_e(red["Datum"])}</td>',
            f'<td>{_e(red["Opis transakcije"])}</td>',
            f"<td>{znacka_tipa(s['Tip'])}</td>",
            f'<td class="fin-desno fin-broj" style="color:{boja_iznosa}">'
            f'{_e(red["Iznos (EUR)"])}</td>',
            f'<td class="fin-mali">{_e(s["Račun"])}</td>',
        ]
        for r in racuni:
            svoj = "" if r == s["Račun"] else " fin-tudji"
            celije.append(
                f'<td class="fin-desno fin-broj{svoj}">{_e(red[r])}</td>'
            )
        celije.append(
            f'<td class="fin-desno fin-broj fin-ukupno">'
            f'{_e(red["RASPOLOŽIV IZNOS"])}</td>'
        )
        tijelo.append(f'<tr class="{razred}">{"".join(celije)}</tr>')

    return (
        '<div class="fin-tablica-okvir"><table class="fin-tablica">'
        f"<thead><tr>{zaglavlje}</tr></thead>"
        f'<tbody>{"".join(tijelo)}</tbody></table></div>'
    )
