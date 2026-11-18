"""Post-publish check of the LIVE site (Ben, Nov. 18). Run after pushing, once GitHub Pages has deployed.

Usage: python3 scripts/post_check.py [YYYY-MM-DD] [--shots DIR]

Prints a report in four parts. It never edits anything; the daily run fixes what it finds, rebuilds and re-pushes.
  1. LIVE: today's edition is on the homepage; every page and image the day uses returns 200.
  2. IMAGES: items whose photo could likely be upgraded:
       - stories and Buzz items using a stock photo (alt ends "(stock photo)") or a Wikimedia Commons credit,
       - Buzz items from Facebook posts (the post's own photo can be screenshotted in Chrome; see the plan doc),
       - events with no flyer (the site falls back to a venue photo), with the og:image found on the event's own link
         when there is one (Facebook/Instagram/Reddit links can't be fetched here; check those in Chrome).
  3. LINKS AND RULES: source links that don't load; deks over 120 characters; event descs outside about 8-30 words;
     event kinds outside the allowed list; quotes of 15+ words; Buzz credits that look like full names.
  4. LAYOUT: Playwright screenshots of the live homepage, events, Buzz, spotlight and history pages at phone (390 px)
     and desktop (1280 px) widths, flagging horizontal scroll and broken images. Look at the screenshots yourself.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://bayviewbulletin.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"}
KINDS = {"Music", "Family", "Community", "Social", "Shopping", "Give", "Food", "Civic"}
NOFETCH = ("facebook.com", "instagram.com", "reddit.com", "x.com", "twitter.com", "jsonline.com")

args = [a for a in sys.argv[1:] if not a.startswith("--")]
shots = sys.argv[sys.argv.index("--shots") + 1] if "--shots" in sys.argv else None
if shots in args:
    args.remove(shots)
files = sorted((ROOT / "content/issues").glob("*.json"))
day = args[0] if args else files[-1].stem
d = json.load(open(ROOT / f"content/issues/{day}.json"))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def get(url, n=200000):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read(n).decode("utf8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # noqa: BLE001
        return 0, str(e)[:80]


def og_image(html):
    m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html) or re.search(r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"', html)
    return m.group(1) if m else None


out = {"LIVE": [], "IMAGES": [], "LINKS AND RULES": [], "LAYOUT": []}
stories = [(sec, it) for sec, items in d["sections"].items() for it in items if not it.get("hold")]

# 1. LIVE
st, home = get(SITE + "/")
if st != 200:
    out["LIVE"].append(f"homepage returned {st}")
elif d["display_date"].split(",")[1].strip() not in home and d["display_date"] not in home:
    out["LIVE"].append(f"homepage does not show today's date ({d['display_date']}); Pages may not have deployed yet")
pages = ["/", "/events.html", "/buzz.html", "/spotlight.html", "/history.html"]
pages += [f"/story/{day}-{slug(it['title'])}.html" for _, it in stories]
srcs = {it["image"]["src"] for _, it in stories if it.get("image")}
srcs |= {b["image"]["src"] for b in d.get("buzz", []) if b.get("image") and not b.get("hold")}
srcs |= {e["image"] for e in d.get("events", []) if isinstance(e.get("image"), str)}
if d.get("history", {}).get("image"):
    srcs.add(d["history"]["image"]["src"])
for p in pages + sorted(srcs):
    s, _ = get(SITE + p, 512)
    if s != 200:
        out["LIVE"].append(f"{p} returned {s}")

# 2. IMAGES
def stockish(img):
    return img and ("(stock photo)" in img.get("alt", "") or "Wikimedia Commons" in img.get("credit", ""))

for sec, it in stories:
    if not it.get("image"):
        out["IMAGES"].append(f"[{sec}] NO PHOTO: {it['title']}")
    elif stockish(it["image"]):
        out["IMAGES"].append(f"[{sec}] stock photo, look for the real subject: {it['title']} (source {it.get('source_url', '')})")
for b in d.get("buzz", []):
    if b.get("hold"):
        continue
    if not b.get("image"):
        out["IMAGES"].append(f"[buzz] NO PHOTO: {b['headline']}")
    elif stockish(b["image"]):
        hint = " -> Facebook post: screenshot its own photo in Chrome if it passes the privacy rules" if "facebook.com" in b.get("source_url", "") else ""
        out["IMAGES"].append(f"[buzz] stock photo: {b['headline']} ({b.get('source_url', '')}){hint}")
for e in d.get("events", []):
    if e.get("image"):
        continue
    link = e.get("link", "")
    cand = ""
    if link and not any(x in link for x in NOFETCH):
        s, h = get(link)
        og = og_image(h) if s == 200 else None
        cand = f" -> og:image {og}" if og else f" -> no og:image on link ({s})"
    else:
        cand = " -> check the organizer's/performers' Instagram or the venue's post in Chrome"
    out["IMAGES"].append(f"[event] venue fallback: {e['day']} {e['title']} @ {e['where'].split(',')[0]}{cand}")
if d.get("history") and stockish(d["history"].get("image")) and "(current photo)" not in d["history"]["image"].get("alt", ""):
    out["IMAGES"].append("[history] stock photo: " + d["history"]["title"])

# 3. LINKS AND RULES
links = [(it["title"], it.get("source_url")) for _, it in stories] + [(b["headline"], b.get("source_url")) for b in d.get("buzz", [])]
links += [(e["title"], e.get("link")) for e in d.get("events", [])]
for _, it in stories:
    links += [(it["title"] + " / " + l["label"], l["url"]) for l in it.get("links", [])]
links += [("history / " + l["label"], l["url"]) for l in d.get("history", {}).get("links", [])]
seen = set()
for name, u in links:
    if not u or u in seen or any(x in u for x in NOFETCH) or not u.startswith("http"):
        continue
    seen.add(u)
    s, _ = get(u, 2048)
    if s not in (200, 301, 302, 403, 429):  # 403/429 = bot blocking, not a dead link
        out["LINKS AND RULES"].append(f"link {s}: {name} -> {u}")
for sec, it in stories:
    if sec != "spotlight" and len(it.get("dek", "")) >= 120:
        out["LINKS AND RULES"].append(f"dek {len(it['dek'])} chars: {it['title']}")
    for q in re.findall(r'"([^"]+)"', it.get("body", "")):
        if len(q.split()) >= 15:
            out["LINKS AND RULES"].append(f"quote of {len(q.split())} words in: {it['title']}")
for e in d.get("events", []):
    n = len(e.get("desc", "").split())
    if n < 8 or n > 30:
        out["LINKS AND RULES"].append(f"event desc {n} words: {e['title']}")
    if e.get("kind") not in KINDS:
        out["LINKS AND RULES"].append(f"event kind {e.get('kind')!r}: {e['title']}")
for b in d.get("buzz", []):
    who = b.get("who", "")
    if re.fullmatch(r"[A-Z][a-z]+ [A-Z][a-z]{2,}", who) and "facebook.com/groups" in b.get("source_url", ""):
        out["LINKS AND RULES"].append(f"Buzz credit looks like a full name (use first name + last initial): {who}")

# 4. LAYOUT
if shots:
    from playwright.sync_api import sync_playwright
    Path(shots).mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        for w, label in ((390, "phone"), (1280, "desktop")):
            pg = br.new_page(viewport={"width": w, "height": 900})
            for p in pages[:5]:
                pg.goto(SITE + p, wait_until="networkidle", timeout=45000)
                pg.wait_for_timeout(600)
                bad = pg.evaluate("[...document.images].filter(i=>i.complete&&i.naturalWidth===0).map(i=>i.getAttribute('src'))")
                over = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
                name = (p.strip("/").replace(".html", "") or "index") + f"-{label}.png"
                pg.screenshot(path=f"{shots}/{name}", full_page=True)
                if bad:
                    out["LAYOUT"].append(f"{label} {p}: {len(bad)} broken image(s): {bad[:3]}")
                if over:
                    out["LAYOUT"].append(f"{label} {p}: horizontal scroll")
        br.close()
    out["LAYOUT"].append(f"screenshots saved in {shots}; look at them")

print(f"Post-publish check for {day} ({SITE})")
for k, v in out.items():
    print(f"\n== {k}: {len([x for x in v if not x.startswith('screenshots')])} item(s)")
    for x in v:
        print("  -", x)
