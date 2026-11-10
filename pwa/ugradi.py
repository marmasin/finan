"""
Pretvara Streamlit u instalabilnu aplikaciju (PWA) — ikona na početnom
zaslonu telefona, otvaranje preko cijelog ekrana, bez adresne trake.

Zašto ovako: Streamlit ne nudi način da se u <head> stranice doda manifest ni
service worker, a preglednik ih traži baš tamo (u <body> ih ignorira). Zato se
pri buildu Docker slike datoteke iz ove mape kopiraju u Streamlitovu mapu
`static/` (poslužuje se s korijena adrese), a u njegov `index.html` se umetne
blok oznaka. Skripta je idempotentna — ponovno pokretanje zamijeni stari blok.

    python pwa/ugradi.py          # Dockerfile to radi sam
    uv run pwa/ugradi.py          # lokalno, za probu u pregledniku
"""
import re
import shutil
from pathlib import Path

import streamlit

MAPA = Path(__file__).parent
STATIC = Path(streamlit.__file__).parent / "static"
INDEX = STATIC / "index.html"

DATOTEKE = [
    "finan.webmanifest",
    "sw.js",
    "offline.html",
    "ikona-192.png",
    "ikona-512.png",
    "ikona-maskabilna-512.png",
    "apple-touch-icon.png",
]

POCETAK, KRAJ = "<!-- finan-pwa -->", "<!-- /finan-pwa -->"

# `?v=` jer Streamlit sve osim .html poslužuje kao „immutable” — nova verzija
# ikone ili manifesta mora imati drugu adresu da je telefon uopće povuče.
BLOK = f"""{POCETAK}
    <link rel="manifest" href="./finan.webmanifest?v=1" />
    <meta name="theme-color" content="#202020" />
    <meta name="mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="black" />
    <meta name="apple-mobile-web-app-title" content="Finan" />
    <link rel="apple-touch-icon" href="./apple-touch-icon.png?v=1" />
    <style>html, body {{ background: #202020; }}</style>
    <script>
      if ("serviceWorker" in navigator) {{
        addEventListener("load", () => navigator.serviceWorker.register("./sw.js"));
      }}
    </script>
    {KRAJ}"""

# viewport-fit=cover → `env(safe-area-inset-*)` u stil.py dobije stvarne
# vrijednosti (urez i traka na dnu iPhonea).
VIEWPORT = (
    '<meta name="viewport" content="width=device-width, initial-scale=1, '
    'viewport-fit=cover" />'
)


def ugradi():
    for ime in DATOTEKE:
        shutil.copy2(MAPA / ime, STATIC / ime)

    kod = INDEX.read_text(encoding="utf-8")
    kod = re.sub(
        r"\s*" + re.escape(POCETAK) + r".*?" + re.escape(KRAJ) + r"\s*", "", kod,
        flags=re.DOTALL,
    )
    kod = re.sub(r"<meta\s+name=\"viewport\"[^>]*>", VIEWPORT, kod, count=1)
    kod = re.sub(r"<title>.*?</title>", "<title>Finan</title>", kod, count=1)
    kod = re.sub(r"\s*</head>", f"\n    {BLOK}\n  </head>", kod, count=1)
    INDEX.write_text(kod, encoding="utf-8")
    print(f"PWA OK: {STATIC}")  # ASCII — Windows konzola (cp1252) ne zna „đ”


if __name__ == "__main__":
    ugradi()
