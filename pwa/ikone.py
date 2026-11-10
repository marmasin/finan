"""
Crta ikone aplikacije za početni zaslon telefona (PWA).

Pokreće se RUČNO, samo kad se mijenja izgled ikone — gotovi PNG-ovi su u gitu,
pa ih Docker build ne mora crtati (u Linux slici nema fonta Segoe UI):

    uv run pwa/ikone.py

Izgled prati Windows 11 / Fluent: zaobljeni kvadrat s plavim prijelazom
(boje naglaska iz `stil.py`) i bijeli znak „€”.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

MAPA = Path(__file__).parent
FONT = "C:/Windows/Fonts/seguisb.ttf"  # Segoe UI Semibold
FONT_ZAMJENA = "C:/Windows/Fonts/segoeuib.ttf"

TAMNA = (0, 95, 184)      # #005fb8 — Fluent naglasak (tamniji)
SVIJETLA = (96, 205, 255)  # #60cdff — Fluent naglasak u tamnoj temi


def _prijelaz(velicina):
    """Dijagonalni prijelaz od svijetle (gore lijevo) do tamne (dolje desno)."""
    slika = Image.new("RGB", (velicina, velicina))
    px = slika.load()
    for y in range(velicina):
        for x in range(velicina):
            t = (x + y) / (2 * (velicina - 1))
            px[x, y] = tuple(round(s + (t_ - s) * t) for s, t_ in zip(SVIJETLA, TAMNA))
    return slika


def _font(velicina):
    for put in (FONT, FONT_ZAMJENA):
        if Path(put).exists():
            return ImageFont.truetype(put, velicina)
    return ImageFont.load_default(velicina)


def ikona(velicina, maskabilna=False):
    """
    `maskabilna=True` → pozadina do ruba (Android sam reže oblik), znak unutar
    sigurne zone od 60 %. Inače zaobljeni kvadrat s prozirnim rubom.
    """
    platno = Image.new("RGBA", (velicina, velicina), (0, 0, 0, 0))
    if maskabilna:
        platno.paste(_prijelaz(velicina), (0, 0))
        znak_vel = int(velicina * 0.42)
    else:
        rub = int(velicina * 0.06)
        unutra = velicina - 2 * rub
        maska = Image.new("L", (unutra, unutra), 0)
        ImageDraw.Draw(maska).rounded_rectangle(
            (0, 0, unutra - 1, unutra - 1), radius=int(unutra * 0.22), fill=255
        )
        platno.paste(_prijelaz(unutra), (rub, rub), maska)
        znak_vel = int(velicina * 0.56)

    crtac = ImageDraw.Draw(platno)
    crtac.text(
        (velicina / 2, velicina / 2), "€", font=_font(znak_vel),
        fill="white", anchor="mm",
    )
    return platno


def logo(visina=96):
    """
    Ikona + „Finan” za vrh bočnog izbornika (`st.logo`), kao naslovna traka
    PowerToys postavki. Crta se u 3× razlučivosti (prikaz je 32 px visok).
    """
    font = _font(int(visina * 0.5))
    sirina_teksta = int(font.getlength("Finan"))
    razmak = int(visina * 0.3)
    platno = Image.new(
        "RGBA", (visina + razmak + sirina_teksta + 4, visina), (0, 0, 0, 0)
    )
    platno.paste(ikona(visina), (0, 0), ikona(visina))
    ImageDraw.Draw(platno).text(
        (visina + razmak, visina / 2), "Finan", font=font, fill="white", anchor="lm"
    )
    return platno


if __name__ == "__main__":
    ikona(192).save(MAPA / "ikona-192.png")
    ikona(512).save(MAPA / "ikona-512.png")
    ikona(512, maskabilna=True).save(MAPA / "ikona-maskabilna-512.png")
    # iOS ne podržava prozirnost na početnom zaslonu → maskabilna (puna) verzija.
    ikona(180, maskabilna=True).convert("RGB").save(MAPA / "apple-touch-icon.png")
    ikona(64).save(MAPA / "favicon.png")
    logo().save(MAPA / "logo.png")
    print("Ikone spremljene u", MAPA)
