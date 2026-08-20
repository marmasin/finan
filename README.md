# Financijski menadžer

Alat za kontrolu likvidnosti — praćenje prihoda, rashoda i salda po računima
kroz vrijeme. Ista poslovna logika ([logika.py](logika.py)) pokreće i web
verziju ([app.py](app.py), Streamlit) i terminalsku verziju
([financija.py](financija.py)).

## Pokretanje lokalno

Potreban je [uv](https://docs.astral.sh/uv/) (`winget install astral-sh.uv`).

```powershell
uv venv --python 3.12
uv pip install -r requirements.txt

# Web (Streamlit)
uv run streamlit run app.py

# Terminal
uv run financija.py
```

`uv venv` sam kreira `.venv` u korijenu projekta, a `uv run` ga automatski
koristi — ručna aktivacija (`.venv\Scripts\activate`) nije potrebna.

Lokalno se baza čuva u `financije_baza.json` (nije u gitu — osobni podaci).

## Pohrana i konfiguracija

Putanje i pohrana su podesivi varijablama okruženja:

| Varijabla          | Čemu služi                                            |
|--------------------|-------------------------------------------------------|
| `FINAN_DB_PATH`    | putanja lokalne baze (zadano: uz kod)                 |
| `FINAN_GCS_BUCKET` | ime Google Cloud Storage bucketa (bez njega → lokalno)|
| `FINAN_GCS_OBJECT` | ime objekta u bucketu (zadano `financije_baza.json`)  |
| `FINAN_LOZINKA`    | lozinka za prijavu u web app (bez nje → otključano)   |

## Deploy u oblak

Upute za deploy na Google Cloud Run (privatno, s bazom u GCS-u) su u
[DEPLOY.md](DEPLOY.md).

## Napomena o privatnosti

Osobni financijski podaci (`financije_baza.json`) i tajne (lozinke, ključevi)
su u [.gitignore](.gitignore) i **ne nalaze se u repozitoriju**.
