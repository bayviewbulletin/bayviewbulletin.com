"""Download a business's own photo into static/photos/ so it never expires.

Usage:
  python3 scripts/fetch_image.py <source> <slug>

<source> can be:
  - an Instagram post or reel link (https://www.instagram.com/p/<code>/ or /<user>/p/<code>/)
    -> downloads the post image via instagram.com/p/<code>/media/?size=l
  - a web page (business website, article) -> uses its og:image / twitter:image
  - a direct image URL (.jpg/.png/.webp, Shopify/Squarespace/WordPress CDN, etc.)

Writes static/photos/<slug>.jpg (max 1600 px wide, JPEG q=82) and prints the site path
(/photos/<slug>.jpg) to use as image.src. Facebook pages need a login, so they can't be
fetched here; use the business's website or Instagram instead.
"""
import html
import io
import re
import sys
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read(), r.headers.get("Content-Type", "")


def image_url_for(src):
    m = re.search(r"instagram\.com/(?:[^/]+/)?(?:p|reel)/([A-Za-z0-9_-]+)", src)
    if m:
        return f"https://www.instagram.com/p/{m.group(1)}/media/?size=l"
    if re.search(r"\.(jpe?g|png|webp|gif)(\?|$)", src, re.I):
        return src
    body, ctype = get(src)
    if ctype.startswith("image/"):
        return src
    page = body.decode("utf-8", "ignore")
    for prop in ("og:image", "og:image:url", "twitter:image"):
        m = re.search(r'<meta[^>]+(?:property|name)="' + re.escape(prop) + r'"[^>]+content="([^"]+)"', page) or \
            re.search(r'<meta[^>]+content="([^"]+)"[^>]+(?:property|name)="' + re.escape(prop) + r'"', page)
        if m:
            u = html.unescape(m.group(1))
            return "https:" + u if u.startswith("//") else u.replace("http://", "https://", 1)
    raise SystemExit(f"No og:image found on {src}")


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    src, slug = sys.argv[1], re.sub(r"[^a-z0-9-]+", "-", sys.argv[2].lower()).strip("-")
    url = image_url_for(src)
    data, ctype = get(url)
    img = Image.open(io.BytesIO(data))
    img = img.convert("RGB")
    if img.width < 400:
        raise SystemExit(f"Image too small ({img.width}px wide); pick another photo")
    if img.width > 1600:
        img = img.resize((1600, round(img.height * 1600 / img.width)), Image.LANCZOS)
    out = ROOT / "static" / "photos" / f"{slug}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=82, optimize=True)
    print(f"/photos/{slug}.jpg  ({img.width}x{img.height}, from {src})")


if __name__ == "__main__":
    main()
