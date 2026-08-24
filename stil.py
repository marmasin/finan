"""
Izgled web verzije — tokeni, CSS i HTML gradivni blokovi (Figma dizajn).

Zašto ovaj modul postoji: Streamlitove ugrađene komponente ne mogu dati izgled
iz dizajna (kartice s prigušenim rubom, brojevi u monospaceu, obojene značke,
traka napretka cilja). Zato se prikazi koji su SAMO ZA ČITANJE — „Danas”,
„Buduće”, „Detalji” — crtaju kao vlastiti HTML, a Streamlit widgeti se koriste
tamo gdje treba interakcija („Unos”).

Podjela odgovornosti:
    • .streamlit/config.toml — sve što Streamlit ume obojiti sam (tema, widgeti)
    • ovaj modul            — tokeni, dopunski CSS i HTML za vlastite prikaze
    • logika.py / ciljevi.py — svi izračuni i podaci (ovdje se ništa ne računa)

Tokeni su preslikani iz `:root` varijabli Figma verzije, pa su boje na jednom
mjestu i za temu i za CSS.
"""
import html
from datetime import date, datetime

import streamlit as st

import logika

# ---------------------------------------------------------------------------
# TOKENI  (identični `:root` varijablama iz Figma dizajna)
# ---------------------------------------------------------------------------

POZADINA = "#1a1a1a"
IZBORNIK = "#212121"
KARTICA = "#262626"
TEKST = "#ececec"
PRIGUSENO = "#8a8a8a"
NAGLASAK = "#c96442"
NAGLASAK_SVJETLIJI = "#e8956d"

RUB = "rgba(255, 255, 255, 0.08)"
RUB_BLAGI = "rgba(255, 255, 255, 0.06)"
PLOHA_BLAGA = "rgba(255, 255, 255, 0.04)"

ZELENA = "#34d399"
CRVENA = "#f87171"
NARANCASTA = "#fb923c"

# (ikona, naziv, ključ, boja) — boje su iz TABS konstante Figma verzije.
TABOVI = [
    ("📅", "Danas", "danas", "#3b82f6"),      # plava — sadašnjost
    ("🔮", "Buduće", "buduce", "#8b5cf6"),    # ljubičasta — projekcija
    ("✏️", "Unos", "unos", "#f59e0b"),        # jantarna — uređivanje
    ("📊", "Detalji", "detalji", "#10b981"),  # zelena — analiza
]

# Boja kružića uz naziv računa: (podloga, tekst). Iz `BankIcon` Figma verzije —
# prepoznavanje po dijelu naziva, pa radi i za „Erste Tekući”, „PBZ Žiro”…
_BOJE_RACUNA = [
    (("erste",), "rgba(227, 6, 19, 0.15)", "#f87171"),
    (("pbz",), "rgba(0, 48, 135, 0.30)", "#4a8edb"),
    (("gotovina", "keš", "kes", "cash"), "rgba(16, 185, 129, 0.12)", ZELENA),
    (("revolut",), "rgba(124, 92, 252, 0.18)", "#8b5cf6"),
]


def boja_racuna(naziv):
    """(podloga, boja_teksta) za kružić računa — po nazivu, s općim padom."""
    n = (naziv or "").lower()
    for kljucne, podloga, tekst in _BOJE_RACUNA:
        if any(k in n for k in kljucne):
            return podloga, tekst
    return "rgba(201, 100, 66, 0.14)", NAGLASAK


def inicijali(naziv):
    """Do dva znaka za kružić računa: 'PBZ Žiro' → 'PB', 'Gotovina' → 'GO'."""
    return (naziv or "?").strip()[:2].upper()


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def _tokeni_css():
    """CSS varijable iz Python tokena — ostatak stilske datoteke koristi var()."""
    return f"""
    :root {{
        --fin-pozadina: {POZADINA};
        --fin-izbornik: {IZBORNIK};
        --fin-kartica: {KARTICA};
        --fin-tekst: {TEKST};
        --fin-priguseno: {PRIGUSENO};
        --fin-naglasak: {NAGLASAK};
        --fin-rub: {RUB};
        --fin-rub-blagi: {RUB_BLAGI};
        --fin-ploha: {PLOHA_BLAGA};
        --fin-zelena: {ZELENA};
        --fin-crvena: {CRVENA};
    }}"""


def _css_tabova():
    """
    Tabovi kao „segmentirani” izbornik iz dizajna: prigušene pilule, a odabrana
    dobije prozirnu podlogu i tekst u boji svog taba.

    Boja se veže na `:nth-of-type(n)` jer Streamlit tabovima ne daje stabilan
    razred — redoslijed je zadan konstantom TABOVI, pa je indeks pouzdan.
    """
    pravila = []
    for i, (_, naziv, _, boja) in enumerate(TABOVI, start=1):
        pravila.append(f"""
    /* {naziv} */
    div[data-testid="stTabs"] button[data-baseweb="tab"]:nth-of-type({i})[aria-selected="true"] {{
        background: color-mix(in srgb, {boja} 16%, transparent);
        box-shadow: inset 0 0 0 1px color-mix(in srgb, {boja} 35%, transparent);
    }}
    div[data-testid="stTabs"] button[data-baseweb="tab"]:nth-of-type({i})[aria-selected="true"] p {{
        color: {boja} !important;
    }}""")
    return "\n".join(pravila)


# Glavni stil. Namjerno NIJE f-string (CSS je pun vitičastih zagrada) — sve
# promjenjivo ulazi kroz var(--fin-*) iz `_tokeni_css`.
_STIL = """
    /* Inter za tekst, DM Mono za brojeve — kao u Figma verziji. */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

    /* --- Prostor stranice ------------------------------------------------ */
    .block-container {
        padding-top: 2.2rem !important;
        padding-bottom: 3rem !important;
        max-width: 1400px;
    }
    /* Zbijeniji okomiti ritam — dizajn je gušći od Streamlitovog zadanog. */
    div[data-testid="stVerticalBlock"] { gap: 0.85rem; }
    header[data-testid="stHeader"] { background: transparent; }

    /* --- Marka („Liquidity” iz dizajna) --------------------------------- */
    .fin-marka {
        display: flex; align-items: center; gap: 10px; margin-bottom: 1.1rem;
    }
    .fin-marka-znak {
        width: 28px; height: 28px; border-radius: 8px;
        background: var(--fin-naglasak);
        display: flex; align-items: center; justify-content: center;
        font-size: 14px; line-height: 1; flex-shrink: 0;
    }
    .fin-marka-ime {
        font-size: 15px; font-weight: 600; color: var(--fin-tekst);
        letter-spacing: -0.01em;
    }

    /* --- Naslov odjeljka (mala razmaknuta verzalna oznaka) --------------- */
    .fin-oznaka {
        font-size: 11px; font-weight: 500; color: var(--fin-priguseno);
        text-transform: uppercase; letter-spacing: 0.12em;
        margin: 0 0 0.7rem 0; display: flex; align-items: center; gap: 7px;
    }

    /* --- Hero traka ----------------------------------------------------- */
    .fin-hero {
        display: flex; flex-wrap: wrap; align-items: center; gap: 1.5rem;
        padding: 0 0 1.15rem 0; margin-bottom: 1.1rem;
        border-bottom: 1px solid var(--fin-rub-blagi);
    }
    .fin-hero-glavno { font-size: 34px; font-weight: 600; line-height: 1;
        letter-spacing: -0.02em; color: var(--fin-tekst); }
    .fin-hero-drugo { font-size: 20px; font-weight: 600; line-height: 1;
        letter-spacing: -0.01em; color: var(--fin-tekst); }
    .fin-hero-desno {
        display: flex; align-items: center; gap: 1rem;
        padding-left: 1.5rem; border-left: 1px solid var(--fin-rub);
    }
    @media (max-width: 640px) {
        .fin-hero-glavno { font-size: 27px; }
        .fin-hero-desno { padding-left: 0; border-left: none; }
    }

    /* --- Kartica i redovi ----------------------------------------------- */
    .fin-kartica {
        background: var(--fin-kartica); border: 1px solid var(--fin-rub);
        border-radius: 12px; overflow: hidden;
    }
    .fin-kartica-tijelo { padding: 1rem 1.05rem; }
    .fin-red {
        display: flex; align-items: center; justify-content: space-between;
        gap: 12px; padding: 0.85rem 1.05rem;
        border-bottom: 1px solid var(--fin-rub-blagi);
    }
    .fin-red:last-child { border-bottom: none; }
    .fin-red-lijevo { display: flex; align-items: center; gap: 12px; min-width: 0; }
    .fin-ime { font-size: 14px; color: var(--fin-tekst); overflow: hidden;
        text-overflow: ellipsis; white-space: nowrap; }

    /* Kružić s inicijalima računa (zamjena za ikone banaka iz dizajna). */
    .fin-znak {
        width: 32px; height: 32px; border-radius: 999px; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center;
        font-size: 10.5px; font-weight: 700; letter-spacing: 0.02em;
        border: 1px solid var(--fin-rub);
    }

    /* --- Brojevi -------------------------------------------------------- */
    .fin-broj {
        font-family: 'DM Mono', ui-monospace, monospace;
        font-variant-numeric: tabular-nums; font-size: 14px; font-weight: 500;
        color: var(--fin-tekst); white-space: nowrap;
    }
    .fin-broj.fin-manjak { color: var(--fin-crvena); }
    .fin-mali { font-size: 12px; color: var(--fin-priguseno); }

    /* Zbirni red na dnu kartice — zelen kad je pozitivan, crven kad nije. */
    .fin-zbroj {
        display: flex; align-items: center; justify-content: space-between;
        gap: 12px; padding: 0.85rem 1.05rem; font-weight: 600; font-size: 14px;
        background: rgba(16, 185, 129, 0.08); border-top: 1px solid rgba(16, 185, 129, 0.2);
        color: var(--fin-zelena);
    }
    .fin-zbroj.fin-manjak {
        background: rgba(239, 68, 68, 0.08); border-top-color: rgba(239, 68, 68, 0.2);
        color: var(--fin-crvena);
    }
    .fin-zbroj .fin-broj { color: inherit; font-weight: 600; }

    /* --- Značke (tip stavke, razlika) ----------------------------------- */
    .fin-znacka {
        display: inline-block; padding: 2px 9px; border-radius: 999px;
        font-size: 11px; font-weight: 500; white-space: nowrap;
    }
    .fin-znacka-prihod { background: rgba(16, 185, 129, 0.1); color: var(--fin-zelena); }
    .fin-znacka-rashod { background: rgba(239, 68, 68, 0.1); color: var(--fin-crvena); }
    .fin-znacka-stanje { background: rgba(255, 255, 255, 0.06); color: var(--fin-priguseno); }
    .fin-znacka-rast { background: rgba(16, 185, 129, 0.1); color: var(--fin-zelena); }
    .fin-znacka-pad { background: rgba(251, 146, 60, 0.12); color: #fb923c; }

    /* --- Cilj: traka napretka ------------------------------------------- */
    .fin-traka {
        width: 100%; height: 6px; border-radius: 999px; overflow: hidden;
        background: rgba(255, 255, 255, 0.08); margin-top: 0.15rem;
    }
    .fin-traka > div { height: 100%; border-radius: 999px; }
    .fin-mjerila { display: flex; flex-wrap: wrap; gap: 1.5rem; margin: 0.85rem 0; }
    .fin-mjerilo-oznaka {
        font-size: 11px; color: var(--fin-priguseno); text-transform: uppercase;
        letter-spacing: 0.08em; margin-bottom: 2px;
    }

    /* --- Tablica sljedivosti -------------------------------------------- */
    .fin-tablica-okvir {
        overflow-x: auto; border: 1px solid var(--fin-rub);
        border-radius: 12px; background: var(--fin-kartica);
    }
    .fin-tablica { width: 100%; border-collapse: collapse; font-size: 13px; }
    .fin-tablica th {
        position: sticky; top: 0; background: var(--fin-izbornik);
        padding: 0.7rem 0.85rem; text-align: left; white-space: nowrap;
        font-size: 11px; font-weight: 500; color: var(--fin-priguseno);
        text-transform: uppercase; letter-spacing: 0.07em;
        border-bottom: 1px solid var(--fin-rub);
    }
    .fin-tablica th.fin-desno, .fin-tablica td.fin-desno { text-align: right; }
    .fin-tablica td {
        padding: 0.55rem 0.85rem; border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        color: var(--fin-tekst); vertical-align: middle;
    }
    .fin-tablica tr:last-child td { border-bottom: none; }
    .fin-tablica tr.fin-parni td { background: rgba(255, 255, 255, 0.02); }
    /* Buduće stavke su prigušene — isto kao `opacity-60` u dizajnu. */
    .fin-tablica tr.fin-buduca td { opacity: 0.6; }
    .fin-tablica td.fin-tudji { color: #555; }
    .fin-tablica td.fin-ukupno { color: var(--fin-zelena); font-weight: 600; }
    .fin-stupac-racun {
        display: inline-block; padding: 1px 7px; border-radius: 6px;
        background: rgba(201, 100, 66, 0.08); color: rgba(201, 100, 66, 0.85);
        border: 1px solid rgba(201, 100, 66, 0.2);
    }
    .fin-stupac-ukupno {
        display: inline-block; padding: 1px 7px; border-radius: 6px;
        background: rgba(16, 185, 129, 0.1); color: var(--fin-zelena);
        border: 1px solid rgba(16, 185, 129, 0.25);
    }

    /* --- Tabovi --------------------------------------------------------- */
    div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
        gap: 6px; border-bottom: 1px solid var(--fin-rub-blagi);
        padding-bottom: 0.6rem; margin-bottom: 0.4rem;
    }
    div[data-testid="stTabs"] button[data-baseweb="tab"] {
        flex: 1 1 0; height: auto; min-height: 0;
        padding: 0.6rem 0.9rem; border-radius: 10px;
        background: rgba(255, 255, 255, 0.03);
        transition: background 0.15s ease, box-shadow 0.15s ease;
    }
    div[data-testid="stTabs"] button[data-baseweb="tab"] p {
        font-size: 13.5px !important; font-weight: 500 !important;
        color: var(--fin-priguseno) !important;
    }
    div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
        background: rgba(255, 255, 255, 0.06);
    }
    /* Zadana crvena podvlaka bi se borila s bojama pilula. */
    div[data-testid="stTabs"] div[data-baseweb="tab-highlight"],
    div[data-testid="stTabs"] div[data-baseweb="tab-border"] { display: none !important; }
    @media (max-width: 640px) {
        /* Četiri taba u redu su preuska → 2×2. */
        div[data-testid="stTabs"] div[data-baseweb="tab-list"] { flex-wrap: wrap !important; }
        div[data-testid="stTabs"] button[data-baseweb="tab"] { flex: 1 1 44% !important; }
        .block-container { padding-left: 0.9rem !important; padding-right: 0.9rem !important; }
    }

    /* --- Streamlit widgeti: uklopi u dizajn ----------------------------- */
    div[data-testid="stExpander"] details {
        background: var(--fin-kartica); border: 1px solid var(--fin-rub);
        border-radius: 12px;
    }
    div[data-testid="stExpander"] summary { font-size: 14px; }
    div[data-testid="stElementToolbarButtonContainer"] { display: none !important; }
    /* Tanki „scrollbar” kao u dizajnu. */
    * { scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.1) transparent; }
    *::-webkit-scrollbar { width: 4px; height: 4px; }
    *::-webkit-scrollbar-track { background: transparent; }
    *::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
"""


def ubaci_css():
    """Ubaci stil — pozvati JEDNOM, na početku skripte."""
    st.markdown(
        f"<style>{_tokeni_css()}{_STIL}{_css_tabova()}</style>",
        unsafe_allow_html=True,
    )


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


def marka(ime="Liquidity"):
    """Zaglavlje s markom iz dizajna."""
    return (
        '<div class="fin-marka">'
        '<div class="fin-marka-znak">💶</div>'
        f'<div class="fin-marka-ime">{_e(ime)}</div>'
        "</div>"
    )


def oznaka(tekst):
    """Mala razmaknuta verzalna oznaka odjeljka."""
    return f'<p class="fin-oznaka">{_e(tekst)}</p>'


def znacka_tipa(tip):
    """Značka za tip stavke (Prihod / Rashod / Stanje)."""
    razred = {
        logika.PRIHOD: "fin-znacka-prihod",
        logika.RASHOD: "fin-znacka-rashod",
        logika.STANJE: "fin-znacka-stanje",
    }.get(tip, "fin-znacka-stanje")
    return f'<span class="fin-znacka {razred}">{_e(tip)}</span>'


def znacka_razlike(razlika):
    """Značka s promjenom u odnosu na danas (zelena za rast, narančasta za pad)."""
    razred = "fin-znacka-rast" if razlika >= 0 else "fin-znacka-pad"
    return (
        f'<span class="fin-znacka {razred}">'
        f"{_predznak(razlika)}{eur(razlika)}</span>"
    )


def hero(ukupno_danas, datum_danas, projekcija=None, datum_projekcije=None):
    """
    Hero traka: ukupno raspoloživo danas i (ako ima budućih stavki) projekcija
    sa razlikom — kao `Hero.tsx` u Figma verziji.
    """
    dijelovi = [
        '<div class="fin-hero">',
        "<div>",
        f'<p class="fin-oznaka">Ukupno danas · {_e(datum_danas)}</p>',
        f'<p class="fin-hero-glavno">{eur(ukupno_danas)}</p>',
        "</div>",
    ]
    if projekcija is not None:
        razlika = projekcija - ukupno_danas
        dijelovi += [
            '<div class="fin-hero-desno">',
            "<div>",
            f'<p class="fin-oznaka">Projekcija · {_e(datum_projekcije)}</p>',
            f'<p class="fin-hero-drugo">{eur(projekcija)}</p>',
            "</div>",
            znacka_razlike(razlika),
            "</div>",
        ]
    dijelovi.append("</div>")
    return "".join(dijelovi)


def _znak_racuna(racun):
    """Kružić s inicijalima u boji banke."""
    podloga, boja = boja_racuna(racun)
    return (
        f'<div class="fin-znak" style="background:{podloga};color:{boja}">'
        f"{_e(inicijali(racun))}</div>"
    )


def kartica_stanja(racuni, stanja):
    """
    Kartica „stanja po računima” sa zbirnim redom na dnu — `Danas.tsx`.

    `stanja` je {račun: iznos} iz `logika.stanja_po_racunima`.
    """
    redovi = []
    for r in racuni:
        v = stanja.get(r, 0.0)
        manjak = " fin-manjak" if v < 0 else ""
        redovi.append(
            '<div class="fin-red">'
            f'<div class="fin-red-lijevo">{_znak_racuna(r)}'
            f'<span class="fin-ime">{_e(r)}</span></div>'
            f'<span class="fin-broj{manjak}">{eur(v)}</span>'
            "</div>"
        )

    ukupno = sum(stanja.get(r, 0.0) for r in racuni)
    manjak = " fin-manjak" if ukupno < 0 else ""
    zbroj = (
        f'<div class="fin-zbroj{manjak}">'
        "<span>Ukupno raspoloživo</span>"
        f'<span class="fin-broj">{eur(ukupno)}</span>'
        "</div>"
    )
    return f'<div class="fin-kartica">{"".join(redovi)}{zbroj}</div>'


def _mjerilo(oznaka_teksta, vrijednost, boja=None):
    """Jedan par „oznaka + vrijednost” u kartici cilja."""
    stil = f' style="color:{boja}"' if boja else ""
    return (
        "<div>"
        f'<p class="fin-mjerilo-oznaka">{_e(oznaka_teksta)}</p>'
        f'<span class="fin-broj"{stil}>{vrijednost}</span>'
        "</div>"
    )


def kartica_cilja(n, znak_statusa):
    """
    Kartica jednog cilja — `GoalCard` iz Figma verzije.

    `n` je red iz `ciljevi.napredak` (Račun, Rok, Iznos, Projekcija, Razlika,
    Status, Dana, Postotak, Mjesecno, Napomena). Ovdje se NIŠTA ne računa.
    """
    dosegnut = n["Razlika"] >= 0
    boja_proj = ZELENA if dosegnut else CRVENA

    napomena = (
        f'<p class="fin-mali">{_e(n["Napomena"])}</p>' if n["Napomena"] else ""
    )
    zaglavlje = (
        '<div style="display:flex;align-items:flex-start;'
        'justify-content:space-between;gap:12px">'
        '<div style="display:flex;align-items:center;gap:9px;min-width:0">'
        f'<span style="font-size:15px">{znak_statusa}</span>'
        "<div>"
        f'<p style="font-size:14px;font-weight:500;color:{TEKST};margin:0">'
        f'{_e(n["Račun"])}</p>{napomena}</div></div>'
        f'<span class="fin-mali fin-broj" style="font-size:12px">{_e(n["Rok"])}</span>'
        "</div>"
    )

    mjerila = [
        _mjerilo("Cilj", eur(n["Iznos"])),
        _mjerilo("Projekcija", eur(n["Projekcija"]), boja_proj),
        _mjerilo(
            "Dana" if n["Dana"] >= 0 else "Prošlo",
            str(abs(n["Dana"])),
        ),
    ]
    if not dosegnut and n["Mjesecno"]:
        mjerila.append(_mjerilo("Nedostaje/mj", eur(n["Mjesecno"]), CRVENA))

    # Traka napretka ima smisla samo za pozitivan cilj (kod „ne ispod −200 €”
    # postotak ne znači ništa) — isto pravilo kao u `ciljevi.napredak`.
    traka = ""
    if n["Iznos"] > 0:
        sirina = min(max(n["Postotak"], 0.0), 100.0)
        boja_trake = ZELENA if dosegnut else NAGLASAK
        traka = (
            f'<div class="fin-traka"><div style="width:{sirina:.1f}%;'
            f'background:{boja_trake}"></div></div>'
            f'<p class="fin-mali" style="text-align:right;margin:4px 0 0 0">'
            f'{n["Postotak"]:.1f}%</p>'
        )

    return (
        '<div class="fin-kartica"><div class="fin-kartica-tijelo">'
        f'{zaglavlje}<div class="fin-mjerila">{"".join(mjerila)}</div>{traka}'
        "</div></div>"
    )


def red_zbroja(naslov, vrijednost, razlika=None, boja=NAGLASAK):
    """Istaknuti zbirni red (npr. „Ukupno raspoloživo” u projekciji)."""
    znak = znacka_razlike(razlika) if razlika is not None else ""
    return (
        f'<div class="fin-kartica" style="background:rgba(201,100,66,0.08);'
        f'border-color:rgba(201,100,66,0.2)"><div class="fin-red" '
        'style="border-bottom:none">'
        f'<span style="font-size:14px;font-weight:600;color:{boja}">{_e(naslov)}</span>'
        '<span style="display:flex;align-items:center;gap:12px">'
        f'{znak}<span class="fin-broj" style="font-size:15px;font-weight:600;'
        f'color:{boja}">{eur(vrijednost)}</span></span>'
        "</div></div>"
    )


def tablica_sljedivosti(redovi, racuni, danas):
    """
    Tablica revizijskog traga — `Detalji.tsx`.

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
    zaglavlje += "".join(
        f'<th class="fin-desno"><span class="fin-stupac-racun">{_e(r)}</span></th>'
        for r in racuni
    )
    zaglavlje += (
        '<th class="fin-desno"><span class="fin-stupac-ukupno">UKUPNO</span></th>'
    )

    tijelo = []
    for i, red in enumerate(redovi):
        s = red["Stavka"]
        razredi = " ".join(
            filter(None, [
                "fin-parni" if i % 2 else "",
                "fin-buduca" if _datum(red["Datum"]) > danas else "",
            ])
        )
        boja_iznosa = {
            logika.PRIHOD: ZELENA,
            logika.RASHOD: CRVENA,
        }.get(s["Tip"], PRIGUSENO)

        celije = [
            f'<td class="fin-broj fin-mali">{_e(red["Datum"])}</td>',
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
        tijelo.append(f'<tr class="{razredi}">{"".join(celije)}</tr>')

    return (
        '<div class="fin-tablica-okvir"><table class="fin-tablica">'
        f"<thead><tr>{zaglavlje}</tr></thead>"
        f'<tbody>{"".join(tijelo)}</tbody></table></div>'
    )
