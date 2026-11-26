"""Make the site's link-preview (Open Graph) images: static/og-default.png and static/og/<section>.png.

Run once after a branding change: python3 scripts/make_og.py
Needs the logo at static/mark.svg (rendered with rsvg-convert) and downloads the site's Google Fonts
(Playfair Display 900, Source Serif 4, Source Sans 3) from the @fontsource npm packages on jsDelivr.
"""
import io
import subprocess
import sys
import urllib.request
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path("/tmp/bvb-fonts")
FONTS = {"plate": "playfair-display/files/playfair-display-latin-900-normal", "serif_i": "source-serif-4/files/source-serif-4-latin-400-italic",
         "serif_b": "source-serif-4/files/source-serif-4-latin-700-normal", "sans_b": "source-sans-3/files/source-sans-3-latin-700-normal"}
# Brand palette (see claude/bay-view-bulletin-brand.md)
PAPER, INK, MUTED, RULE = "#FFFFFF", "#121212", "#5C6066", "#E3E1DC"
LAKE, WARM, BUZZ, HOT = "#1F4E79", "#C9541F", "#FFE14D", "#D7261E"

PAGES = {
    "default": ("The Bay View Bulletin", "Bay View's morning paper", None),
    "events": ("Events in Bay View", "Shows, markets, family time and meetings, today and ahead", "EVENTS"),
    "buzz": ("The Bay View Buzz", "What the neighborhood is posting about", "BUZZ"),
    "spotlight": ("Business Spotlight", "One independent Bay View business, every day", "SPOTLIGHT"),
    "history": ("Bay View History", "A story from the neighborhood's past, every day", "HISTORY"),
    "food": ("Food & Drink", "Openings, closings, specials and fish fries in Bay View", "FOOD & DRINK"),
    "city": ("City Hall", "Development, streets and the city decisions that shape Bay View", "CITY HALL"),
    "safety": ("Safety", "Notable incidents and public safety news in Bay View", "SAFETY"),
    "schools": ("School Days Off", "MPS and Bay View school calendars", "SCHOOLS"),
    "directory": ("Business Directory", "The shops, venues and institutions of Bay View", "DIRECTORY"),
}


def font(key, size):
    CACHE.mkdir(exist_ok=True)
    ttf = CACHE / (key + ".ttf")
    if not ttf.exists():
        url = f"https://cdn.jsdelivr.net/npm/@fontsource/{FONTS[key].split('/')[0]}@5.1.0/{FONTS[key].split('/', 1)[1]}.woff2"
        data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()
        try:
            import brotli  # noqa: F401  (fontTools needs it to read .woff2)
        except ImportError:  # fresh containers lack it (Nov. 26, 2026)
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "brotli", "--break-system-packages"], check=True)
        t = TTFont(io.BytesIO(data))
        t.flavor = None
        t.save(ttf)
    return ImageFont.truetype(str(ttf), size)


def mark(size):
    png = subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), str(ROOT / "static/mark.svg")], capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(png)).convert("RGBA")


def fit(draw, text, key, size, maxw):
    while size > 20:
        f = font(key, size)
        if draw.textlength(text, font=f) <= maxw:
            return f
        size -= 4
    return font(key, size)


def make(key, title, sub, label):
    buzz = key == "buzz"
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), BUZZ if buzz else PAPER)
    dr = ImageDraw.Draw(im)
    m = mark(150)
    im.paste(m, (80, 70), m)
    dr.text((256, 92), "THE BAY VIEW BULLETIN", font=font("sans_b", 30), fill=INK)
    dr.text((256, 134), "Bay View's morning paper" if label else "Bay View · Milwaukee · Daily", font=font("serif_i", 30), fill=INK if buzz else MUTED)
    if label:
        f = font("sans_b", 24)
        tw = dr.textlength(label, font=f)
        dr.rectangle((80, 290, 80 + tw + 28, 330), fill=HOT if buzz else (WARM if key in ("food", "spotlight") else LAKE))
        dr.text((94, 293), label, font=f, fill="#FFFFFF")
    tf = fit(dr, title, "plate", 104 if label else 112, W - 160)
    dr.text((80, 345 if label else 290), title, font=tf, fill=INK)
    sf = fit(dr, sub, "serif_i", 38, W - 160)
    dr.text((80, 480 if label else 430), sub, font=sf, fill=INK if buzz else MUTED)
    if buzz:
        dr.rectangle((0, 0, W - 1, H - 1), outline=INK, width=10)
    else:
        dr.rectangle((0, H - 16, int(W * 0.7), H), fill=LAKE)
        dr.rectangle((int(W * 0.7), H - 16, W, H), fill=WARM)
    out = ROOT / "static" / ("og-default.png" if key == "default" else f"og/{key}.png")
    out.parent.mkdir(exist_ok=True)
    im.save(out, optimize=True)
    return out


if __name__ == "__main__":
    for k, (t, s, lab) in PAGES.items():
        print(make(k, t, s, lab))
