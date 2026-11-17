"""Checks the built site in docs/ (run by GitHub Actions after every push, or locally after build.py).

Fails (exit 1) on: missing CNAME or a wrong domain in it, broken internal links or images, a story page without a photo,
an unreadable feed.xml/sitemap.xml/events.ics. Warns on photos over 600 KB.
Usage: python3 scripts/site_check.py [docs]
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlparse

D = Path(sys.argv[1] if len(sys.argv) > 1 else "docs")
errors, warnings = [], []

if not (D / "CNAME").exists() or (D / "CNAME").read_text().strip() != "bayviewbulletin.com":
    errors.append("docs/CNAME missing or not exactly bayviewbulletin.com")
for f in ("feed.xml", "sitemap.xml"):
    try:
        ET.parse(D / f)
    except Exception as ex:  # noqa: BLE001
        errors.append(f"{f}: {ex}")
ics = D / "events.ics"
if not ics.exists() or not ics.read_text().startswith("BEGIN:VCALENDAR"):
    errors.append("events.ics missing or malformed")

pages = list(D.rglob("*.html"))
missing = {}
for p in pages:
    h = p.read_text(errors="ignore")
    for attr, url in re.findall(r'\b(href|src)="(/[^"#]*)', h):
        if url.startswith("//"):
            continue
        path = unquote(urlparse(url).path)
        t = D / path.lstrip("/")
        if path.endswith("/"):
            t = t / "index.html"
        if not t.exists():
            missing.setdefault(path, set()).add(str(p.relative_to(D)))
    if p.parent.name == "story" and "<figure>" not in h:
        errors.append(f"story without a photo: {p.relative_to(D)}")
for path, where in sorted(missing.items()):
    errors.append(f"broken internal link {path} (on {len(where)} page(s), e.g. {sorted(where)[0]})")
for img in (D / "photos").glob("*.jpg"):
    if img.stat().st_size > 600_000:
        warnings.append(f"large photo {img.name}: {img.stat().st_size // 1000} KB")

print(f"Checked {len(pages)} pages.")
for w in warnings:
    print("WARNING:", w)
for e in errors:
    print("ERROR:", e)
if errors:
    sys.exit(1)
print("Site check passed.")
