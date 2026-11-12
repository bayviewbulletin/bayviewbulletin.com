"""Find event listings on business websites listed in content/directory.json.

Usage:
  python3 scripts/site_events.py                 # every business with a "website"
  python3 scripts/site_events.py "Cactus Club"   # one business (name match)

For each website it loads the homepage, follows likely event/calendar/music/shows links
(same site only), and prints:
  - schema.org Event data (name, startDate, location, url, image) when the site has it
  - otherwise the event-page URLs and short text lines that contain a date
Use the output as leads: open the page, confirm details, and write the event in your own
words. Sites that block the workspace (403, timeouts) are listed at the end; check those
in Chrome instead.
"""
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"}
EVENT_WORDS = re.compile(r"event|calendar|shows?|music|concert|live|tickets|happenings|whats-on|what-s-on|classes|workshops|trivia|schedule", re.I)
DATE_RE = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}\b|\b\d{1,2}/\d{1,2}\b|\b(mon|tue|wed|thu|fri|sat|sun)[a-z]*day\b", re.I)


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "ignore")


def jsonld_events(page):
    out = []
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page, re.S | re.I):
        try:
            data = json.loads(html.unescape(block.strip()))
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                if "@graph" in x:
                    stack.extend(x["@graph"])
                t = x.get("@type")
                if t == "Event" or (isinstance(t, list) and "Event" in t) or str(t).endswith("Event"):
                    loc = x.get("location") or {}
                    out.append({"name": x.get("name"), "start": x.get("startDate"), "url": x.get("url"),
                                "location": loc.get("name") if isinstance(loc, dict) else loc,
                                "image": (x.get("image") if isinstance(x.get("image"), str) else (x.get("image") or [None])[0] if isinstance(x.get("image"), list) else None)})
            elif isinstance(x, list):
                stack.extend(x)
    return out


def text_lines(page):
    page = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", page, flags=re.S | re.I)
    txt = html.unescape(re.sub(r"<[^>]+>", "\n", page))
    lines = [re.sub(r"\s+", " ", l).strip() for l in txt.splitlines()]
    return [l for l in lines if 6 < len(l) < 160 and DATE_RE.search(l)]


def scan(name, site):
    base = site if site.startswith("http") else "https://" + site
    host = urllib.parse.urlparse(base).netloc.replace("www.", "")
    home = get(base)
    links = set()
    for href, label in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', home, re.S | re.I):
        u = urllib.parse.urljoin(base, html.unescape(href))
        if host in urllib.parse.urlparse(u).netloc.replace("www.", "") and (EVENT_WORDS.search(u) or EVENT_WORDS.search(re.sub(r"<[^>]+>", "", label))):
            links.add(u.split("?")[0])
    pages = [(base, home)] + [(u, None) for u in sorted(links)[:4]]
    print(f"\n=== {name}  ({base})")
    found = False
    for u, page in pages:
        try:
            page = page or get(u)
        except Exception as ex:
            print(f"  ! {u}: {ex}")
            continue
        evs = jsonld_events(page)
        if evs:
            found = True
            for ev in evs[:15]:
                print(f"  EVENT {ev['start']} | {ev['name']} | {ev['location']} | {ev['url'] or u} | img={ev['image']}")
        elif u != base:
            lines = text_lines(page)[:12]
            if lines:
                found = True
                print(f"  page {u}")
                for l in lines:
                    print(f"    - {l}")
    if not found:
        print("  (no dated events found; check the site or its Instagram in Chrome)")


def main():
    dirs = json.loads((ROOT / "content/directory.json").read_text())
    want = sys.argv[1].lower() if len(sys.argv) > 1 else None
    blocked = []
    for b in dirs:
        if not b.get("website") or (want and want not in b["name"].lower()):
            continue
        try:
            scan(b["name"], b["website"])
        except Exception as ex:
            blocked.append(f"{b['name']} ({b['website']}): {ex}")
    if blocked:
        print("\nCould not load (check in Chrome):\n  " + "\n  ".join(blocked))


if __name__ == "__main__":
    main()
