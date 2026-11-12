#!/usr/bin/env python3
"""Bay View Bulletin v2 layout prototype: front page + story pages + events + Milwaukee.
Reads the same content/issues/*.json; writes preview_v2/ (not published)."""
import html, json, re, shutil, math, datetime as dt
from pathlib import Path

ROOT = Path(__file__).parent
import sys
OUT = ROOT / ("preview_v2" if "--preview" in sys.argv else "docs")
TIPS = "https://docs.google.com/forms/d/e/1FAIpQLSfXNc2RsIhvMPCfcZ9CYb6QIx78RZSr2Ar3YzT5ik9xyPhi7Q/viewform"
e = lambda s: html.escape(str(s or ""), quote=True)
NAV = [("Today", "/"), ("Events", "/events.html"), ("Map", "/map.html"), ("Food & Drink", "/section/food.html"), ("City Hall", "/section/city.html"),
       ("Safety", "/section/safety.html"), ("Milwaukee", "/milwaukee.html"), ("More", "/section/more.html"), ("Search", "/search.html")]
SECTION_OF = {"top": "Bay View", "openings": "Food & Drink", "development": "City Hall", "streets": "Streets", "schools": "Schools",
              "parks": "Parks", "protests": "Protests", "safety": "Safety", "realestate": "Real estate", "help": "Ways to help",
              "fishfry": "Fish fry", "pets": "Pets", "sports": "Sports", "remembrances": "Remembrances", "spotlight": "Business spotlight"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def dek(it):
    if it.get("dek"):
        return it["dek"]
    b = it.get("body", "")
    abbr = r"(?<!\bSt)(?<!\bS)(?<!\bN)(?<!\bE)(?<!\bW)(?<!\bAve)(?<!\bDec)(?<!\bNov)(?<!\bJan)(?<!\bFeb)(?<!\bOct)(?<!\bSept)(?<!\bMr)(?<!\bMs)(?<!\bDr)(?<!\bAld)(?<!\bp\.m)(?<!\ba\.m)"
    m = re.match(r"(.+?" + abbr + r"[.!?])(\s+[A-Z\"']|$)", b)
    return (m.group(1) if m else b)[:200]


CM = lambda f: "https://commons.wikimedia.org/wiki/Special:FilePath/" + f.replace(" ", "_") + "?width=500"
VENUES = [("Cactus Club", CM("Milwaukee January 2025 04 (Cactus Club).jpg")), ("Puddler", CM("2024 08 07 Puddler's Hall 1.jpg")),
          ("Library", CM("Bay View Branch.jpg")), ("Garibaldi", CM("Milwaukee January 2025 16 (S. Kinnickinnic Avenue).jpg")),
          ("Kinnickinnic", CM("Milwaukee January 2025 16 (S. Kinnickinnic Avenue).jpg")), ("Methodist", CM("SouthShore Park 1.jpg")),
          ("", CM("Milwaukee January 2025 16 (S. Kinnickinnic Avenue).jpg"))]
WARM = {"Business spotlight", "Food & Drink", "Ways to help", "Parks", "Fish fry", "Pets"}


def venue_img(ev):
    if ev.get("image"):
        return ev["image"]
    for k, u in VENUES:
        if k in ev["where"] or k in ev["title"]:
            return u


def sunrise_sunset(day, lat=42.99, lon=-87.89, tz=-6):
    n = day.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    decl = 0.006918 - 0.399912*math.cos(g) + 0.070257*math.sin(g) - 0.006758*math.cos(2*g) + 0.000907*math.sin(2*g) - 0.002697*math.cos(3*g) + 0.00148*math.sin(3*g)
    eqt = 229.18*(0.000075 + 0.001868*math.cos(g) - 0.032077*math.sin(g) - 0.014615*math.cos(2*g) - 0.040849*math.sin(2*g))
    ha = math.degrees(math.acos(math.cos(math.radians(90.833))/(math.cos(math.radians(lat))*math.cos(decl)) - math.tan(math.radians(lat))*math.tan(decl)))
    fmt = lambda mins: (dt.datetime(2000, 1, 1) + dt.timedelta(minutes=mins + tz*60)).strftime("%-I:%M")
    return fmt(720 - 4*(lon + ha) - eqt), fmt(720 - 4*(lon - ha) - eqt)


CSS = """
:root{--paper:#FFFFFF;--ink:#121212;--muted:#5C6066;--rule:#E3E1DC;--soft:#F6F4EF;--lake:#1F4E79;--lake-soft:#E8EFF6;--alert:#B5361B;--warm:#C9541F;--warm-soft:#FBEDE3;
--serif:"Source Serif 4",Georgia,serif;--plate:"Playfair Display",Georgia,serif;--sans:"Source Sans 3","Helvetica Neue",Arial,sans-serif;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--paper:#111315;--ink:#ECEAE4;--muted:#A1A6AD;--rule:#2A2E33;--soft:#1A1D21;--lake:#8DBDE3;--lake-soft:#17232F;--alert:#F08C70;--warm:#F29A55;--warm-soft:#2B1E16;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:400 17px/1.5 var(--sans)}
a{color:inherit;text-decoration:none}a:hover h2,a:hover h3,a:hover .hl{text-decoration:underline;text-underline-offset:3px}
a:focus-visible{outline:3px solid var(--lake);outline-offset:2px}img{display:block;max-width:100%}
.wrap{max-width:1140px;margin:0 auto;padding:0 20px}
.plate{text-align:center;padding:18px 0 10px}.dateline{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);display:flex;justify-content:center;gap:14px;flex-wrap:wrap}
.plate .rule{border-top:3px double var(--ink);margin:10px 0 0}.plate h1{font:900 clamp(38px,6.4vw,68px)/1.05 var(--plate);margin:8px 0 2px;letter-spacing:-.01em}
.plate .tag{font:italic 400 16px var(--serif);color:var(--muted);margin:0 0 10px}
nav.sections{border-top:1px solid var(--ink);border-bottom:1px solid var(--rule);overflow-x:auto;white-space:nowrap}
nav.sections ul{list-style:none;margin:0 auto;padding:0 20px;max-width:1140px;display:flex;gap:26px;justify-content:center}
nav.sections a{display:inline-block;padding:11px 0;font:600 15px var(--sans)}nav.sections a.on{box-shadow:inset 0 -3px var(--lake)}
@media(max-width:700px){nav.sections ul{justify-content:flex-start}}
.utils{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));border-bottom:1px solid var(--rule);margin-bottom:22px}
.util{padding:12px 14px;border-right:1px solid var(--rule);display:grid;gap:2px;align-content:start}.util:last-child{border-right:0}
.util .k{font:700 11px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}.util .v{font:700 17px var(--serif)}.util .s{font-size:13px;color:var(--muted)}
.util.alert .v{color:var(--warm)}.util .k::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--lake);margin-right:6px;vertical-align:1px}.util.warm .k::before{background:var(--warm)}
@media(max-width:900px){.utils{grid-template-columns:repeat(3,1fr)}.util:nth-child(3n){border-right:0}.util:nth-child(-n+3){border-bottom:1px solid var(--rule)}}
@media(max-width:520px){.utils{display:flex;overflow-x:auto}.util{min-width:150px;border-bottom:0!important;border-right:1px solid var(--rule)!important}}
.ticker{display:flex;gap:12px;align-items:center;font-size:15px;border-bottom:1px solid var(--rule);padding:0 0 12px;margin:-10px 0 22px;overflow:hidden;white-space:nowrap}.ticker b{flex:0 0 auto;font:700 11px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:#fff;background:var(--warm);padding:3px 7px;border-radius:2px;position:relative;z-index:1}.ticker .vp{flex:1;overflow:hidden;-webkit-mask-image:linear-gradient(90deg,transparent,#000 24px,#000 calc(100% - 40px),transparent);mask-image:linear-gradient(90deg,transparent,#000 24px,#000 calc(100% - 40px),transparent)}.ticker .track{display:inline-flex;animation:tick var(--dur,40s) linear infinite}.ticker:hover .track,.ticker:focus-within .track{animation-play-state:paused}.ticker .set{display:inline-flex}.ticker .set span{padding-right:14px}.ticker .set span::after{content:"\\00B7";margin-left:14px;color:var(--muted)}@keyframes tick{from{transform:translateX(0)}to{transform:translateX(-50%)}}@media(prefers-reduced-motion:reduce){.ticker .vp{overflow-x:auto}.ticker .track{animation:none}.ticker .set+.set{display:none}}
.front{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:28px;padding-bottom:24px;border-bottom:1px solid var(--ink)}
@media(max-width:820px){.front{grid-template-columns:1fr}}
.lead figure{margin:0 0 12px}.lead img{width:100%;aspect-ratio:16/9;object-fit:cover;background:var(--soft)}
.kicker{font:700 12px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--lake)}.kicker.w{color:var(--warm)}
.lead h2{font:700 clamp(28px,3.4vw,40px)/1.12 var(--serif);margin:4px 0 8px;text-wrap:balance}.lead p{margin:0;font-size:18px;color:var(--muted);max-width:60ch}
.meta{font-size:13px;color:var(--muted);margin-top:6px}
.side{display:grid;align-content:start}.side a{padding:12px 0;border-bottom:1px solid var(--rule);display:block}.side a:first-child{padding-top:0}
.side h3{font:700 19px/1.25 var(--serif);margin:2px 0 4px;text-wrap:balance}.side p{margin:0;font-size:15px;color:var(--muted)}
.tonight{margin:22px 0;padding:14px 16px;background:var(--warm-soft);border-top:4px solid var(--warm);border-radius:0 0 4px 4px}
.tonight h2{font:700 13px var(--sans);letter-spacing:.08em;text-transform:uppercase;margin:0 0 10px;display:flex;justify-content:space-between}
.tonight h2 a{color:var(--warm);font-weight:600;letter-spacing:0;text-transform:none;font-size:14px}
.chips{display:flex;gap:10px;overflow-x:auto;padding-bottom:2px}.chip{flex:0 0 auto;background:var(--paper);border:1px solid var(--rule);border-radius:4px;width:200px;overflow:hidden}.chip img{width:100%;height:110px;object-fit:cover;background:var(--soft)}.chip .in{padding:8px 12px 10px;display:grid;gap:2px}
.chip .t{font:700 13px var(--sans);color:var(--warm)}.chip .n{font:700 15px/1.25 var(--serif);display:block}.chip .w{font-size:13px;color:var(--muted)}
.block{padding:22px 0;border-top:1px solid var(--ink)}.block>h2{font:800 22px var(--serif);margin:0 0 14px;display:flex;justify-content:space-between;align-items:baseline}
.block>h2 a{font:600 14px var(--sans);color:var(--lake)}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px 28px}@media(max-width:820px){.grid{grid-template-columns:1fr}}
.row{display:grid;grid-template-columns:96px minmax(0,1fr);gap:14px;align-items:start}.row.noimg{grid-template-columns:1fr}
.row img{width:96px;height:96px;object-fit:cover;background:var(--soft)}.row h3{font:700 18px/1.25 var(--serif);margin:2px 0 4px;text-wrap:balance}.row p{margin:0;font-size:15px;color:var(--muted)}
.mke{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:16px;border:1px solid var(--ink);border-left:6px solid var(--lake);margin:22px 0}
.mke .k{font:700 12px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}.mke .hl{font:700 20px var(--serif)}
.mke .go{font:700 15px var(--sans);color:var(--lake);white-space:nowrap}
.hist{display:grid;grid-template-columns:200px minmax(0,1fr);gap:18px;align-items:start}@media(max-width:600px){.hist{grid-template-columns:1fr}}
.hist img{width:100%;aspect-ratio:4/3;object-fit:cover}.hist .yr{font:900 34px var(--plate);color:var(--lake)}
.cap{font-size:12px;color:var(--muted);margin-top:4px}
footer{border-top:3px double var(--ink);margin-top:30px;padding:18px 0 40px;font-size:14px;color:var(--muted);text-align:center}
footer a{color:var(--lake)}
.story{max-width:700px;margin:26px auto 0}.story h1{font:700 clamp(30px,4vw,42px)/1.12 var(--serif);margin:6px 0 12px;text-wrap:balance}
.story .body{font:400 19px/1.6 var(--serif)}.story figure{margin:16px 0}.story img{width:100%;aspect-ratio:16/9;object-fit:cover}
.btn{display:inline-block;margin:18px 0;padding:12px 18px;background:var(--lake);color:var(--paper);font:700 16px var(--sans);border-radius:4px}
.more h2{font:800 20px var(--serif);border-top:1px solid var(--ink);padding-top:16px;margin-top:30px}
.cal-day{font:700 13px var(--sans);letter-spacing:.08em;text-transform:uppercase;border-bottom:1px solid var(--ink);padding:18px 0 6px}
.ev{display:grid;grid-template-columns:72px 90px minmax(0,1fr) auto;gap:14px;padding:10px 0;border-bottom:1px solid var(--rule);align-items:center}
.ev img{width:72px;height:54px;object-fit:cover;background:var(--soft)}.ev .t{font:700 15px var(--sans);color:var(--warm)}.ev .n{font:700 17px var(--serif)}.ev .w{font-size:14px;color:var(--muted)}
.pill{font:700 11px var(--sans);letter-spacing:.06em;text-transform:uppercase;border:1px solid var(--rule);padding:3px 7px;border-radius:99px;color:var(--muted)}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0 4px}.filters span{border:1px solid var(--ink);padding:6px 12px;border-radius:99px;font:600 14px var(--sans)}.filters span.on{background:var(--ink);color:var(--paper)}
.list a{display:block;padding:16px 0;border-bottom:1px solid var(--rule)}.list h3{font:700 21px/1.25 var(--serif);margin:2px 0 4px}.list p{margin:0;color:var(--muted)}
.pagehead{font:800 34px var(--serif);margin:24px 0 2px}.topics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 36px;padding-top:6px}@media(max-width:820px){.topics{grid-template-columns:1fr}}.topic{padding:18px 0 6px}.topic>h2{font:800 20px var(--serif);margin:0 0 4px;padding-top:10px;border-top:4px solid var(--lake);display:flex;justify-content:space-between;align-items:baseline}.topic.w>h2{border-top-color:var(--warm)}.topic>h2 a{font:600 14px var(--sans);color:var(--lake)}.topic.w>h2 a{color:var(--warm)}.topic .row{padding:12px 0;border-bottom:1px solid var(--rule)}.topic .row:last-child{border-bottom:0}.pagedek{color:var(--muted);margin:0 0 10px}
"""
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@900&family=Source+Sans+3:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,700;8..60,800&display=swap" rel="stylesheet">')


SITE = "https://bayviewbulletin.com"


def ext_links(html):
    """External links open in a new tab; internal links stay in the same tab."""
    def fix(m):
        tag, url = m.group(0), m.group(1)
        if url.startswith(SITE) or "target=" in tag:
            return tag
        return tag[:-1].replace(' rel="noopener"', '') + ' target="_blank" rel="noopener">'
    return re.sub(r'<a\b[^>]*?href="(https?://[^"]+)"[^>]*>', fix, html)


def shell(title, body, d, active="Today", og=None, path="/", head=""):
    og = og or {}
    ogt, ogd = og.get("title", title), og.get("desc", "Daily news for Milwaukee's Bay View neighborhood, every morning.")
    ogi = og.get("image") or SITE + "/og-default.png"
    meta = (f'<meta name="description" content="{e(ogd)}"><link rel="canonical" href="{SITE}{e(path)}">'
            f'<meta property="og:site_name" content="The Bay View Bulletin"><meta property="og:type" content="{og.get("type", "website")}">'
            f'<meta property="og:title" content="{e(ogt)}"><meta property="og:description" content="{e(ogd)}"><meta property="og:image" content="{e(ogi)}">'
            f'<meta property="og:url" content="{SITE}{e(path)}"><meta name="twitter:card" content="summary_large_image">'
            '<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="icon" href="/favicon-32.png" sizes="32x32"><link rel="apple-touch-icon" href="/apple-touch-icon.png">'
            '<meta name="theme-color" content="#1F4E79">' + head)
    nav = "".join(f'<li><a href="{h}"{" class=on" if n == active else ""}>{n}</a></li>' for n, h in NAV)
    return ext_links(f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>{meta}{FONTS}<link rel="stylesheet" href="/assets/v2.css"></head><body>
<header class="plate wrap"><div class="dateline"><span>{e(d['display_date'])}</span><span>Bay View, Milwaukee</span></div>
<div class="rule"></div><h1><a href="/">The Bay View Bulletin</a></h1><p class="tag">Bay View's morning paper</p></header>
<nav class="sections" aria-label="Sections"><ul>{nav}</ul></nav>
<div class="wrap">{body}</div>
<footer><div class="wrap">Covering Bay View from the harbor and Jones Island to Holt and Morgan avenues, I-43 to the lake.<br>
Every item links to the original reporting. Photos belong to their credited owners. <a href="{TIPS}">Send a tip</a> · <a href="/about.html">About</a> · <a href="/archive.html">Archive</a></div></footer>
<script>document.addEventListener('click',function(ev){{var a=ev.target.closest&&ev.target.closest('a[href]');if(a&&a.host&&a.host!==location.host){{a.target='_blank';a.rel='noopener'}}}},true);</script></body></html>""")


ALL_STORIES = []


def build_one(d, newest):
    day = dt.date.fromisoformat(d["date"])

    stories = []
    for key, items in d["sections"].items():
        for it in items:
            if it.get("hold") or it.get("tag") == "Listings":
                continue
            it = dict(it, section=SECTION_OF.get(key, key), key=key, url=f"/story/{d['date']}-{slug(it['title'])}.html")
            stories.append(it)
            ALL_STORIES.append(dict(it, issue_date=d["date"], display_date=d["display_date"]))
    # The daily business spotlight always gets its own block and is never the lead or a side headline.
    news = [s for s in stories if s["key"] != "spotlight"] or stories
    lead = next((s for s in news if s.get("image")), news[0])
    rest = [s for s in stories if s is not lead]

    # story pages
    for s in stories:
        others = "".join(f'<a href="{o["url"]}"><span class="kicker">{e(o["section"])}</span><h3>{e(o["title"])}</h3><p>{e(dek(o))}</p></a>' for o in stories if o is not s)[:6000]
        img = (f'<figure><img src="{e(s["image"]["src"])}" alt="{e(s["image"]["alt"])}"><div class="cap">Photo: <a href="{e(s["image"]["credit_url"])}">{e(s["image"]["credit"])}</a></div></figure>') if s.get("image") else ""
        src = f'<a class="btn" href="{e(s["source_url"])}">Read the full story at {e(s["source_name"])} →</a>' if s.get("source_url") else ""
        body = (f'<article class="story"><span class="kicker">{e(s["section"])} · {e(d["display_date"])}</span><h1>{e(s["title"])}</h1>{img}'
                f'<div class="body"><p>{e(s.get("body"))}</p></div>{src}<section class="more side"><h2>More from Bay View today</h2>{others}</section></article>')
        (OUT / s["url"].lstrip("/")).write_text(shell(s["title"] + " · The Bay View Bulletin", body, d, "", {"title": s["title"], "desc": dek(s), "image": (s.get("image") or {}).get("src"), "type": "article"}, s["url"]))

    # utilities
    rise, sset = sunrise_sunset(day)
    today_events = [ev for ev in d["events"] if ev["day"].startswith("Today")]
    days_to_winter = (dt.date(day.year, 12, 1) - day).days
    U = d.get("utilities", {})
    def ut(key, label, fallback_v, fallback_s, href=""):
        x = U.get(key) or {}
        return (label, x.get("v") or fallback_v, x.get("s") or fallback_s, x.get("class", ""), x.get("href") or href)
    utils = [
        ut("weather", "Weather", "Today's forecast →", "National Weather Service", "https://forecast.weather.gov/MapClick.php?lat=42.99&lon=-87.89"),
        ut("lake", "Lake", "Marine forecast →", "Wind & waves off South Shore", "https://forecast.weather.gov/MapClick.php?zoneid=LMZ645"),
        ("Parking", f"Winter rules in {days_to_winter} days" if days_to_winter > 0 else "Winter rules in effect", "Dec 1 – Mar 1", "warm" if 0 < days_to_winter <= 7 else "", "https://city.milwaukee.gov/mpw/parking/meter"),
        ("Tonight", f"{len(today_events)} things to do" if today_events else "Quiet night", "See tonight's list", "warm", "/events.html"),
        ut("pickup", "Pickup & roads", "Your pickup day →", "City sanitation schedule", "https://city.milwaukee.gov/sanitation"),
        ("Sun over the lake", f"↑ {rise} · ↓ {sset}", "Bay View shoreline", "", ""),
    ]
    util_html = "".join((f'<a class="util {c}" href="{e(h)}">' if h else f'<div class="util {c}">') + f'<span class="k">{k}</span><span class="v">{e(v)}</span><span class="s">{e(s_)}</span>' + ("</a>" if h else "</div>") for k, v, s_, c, h in utils)
    tick = [s for s in stories if s["key"] == "openings"] or []
    ticker_items = d.get("ticker") or [c["title"] for c in d.get("catching_up", []) if re.search(r"open|clos|coming|leav|lease", c["title"], re.I)][:6]
    _set = "".join(f"<span>{e(t)}</span>" for t in ticker_items)
    _dur = max(25, sum(len(t) for t in ticker_items) // 5)
    ticker = (f'<div class="ticker" aria-label="Recent openings and closings"><b>Opened &amp; closed</b><div class="vp"><div class="track" style="--dur:{_dur}s"><div class="set">{_set}</div><div class="set" aria-hidden="true">{_set}</div></div></div></div>') if ticker_items else ""

    tops = [s for s in rest if s["key"] == "top"]; side_items = (tops + [s for s in rest if s["key"] not in ("top", "spotlight")])[:max(3, len(tops))]
    side = "".join(f'<a href="{s["url"]}"><span class="kicker">{e(s["section"])}</span><h3>{e(s["title"])}</h3><p>{e(dek(s))}</p></a>' for s in side_items)
    lead_img = f'<figure><img src="{e(lead["image"]["src"])}" alt="{e(lead["image"]["alt"])}"><div class="cap">Photo: {e(lead["image"]["credit"])}</div></figure>' if lead.get("image") else ""
    chips = "".join(f'<a class="chip" href="/events.html"><img src="{e(venue_img(ev))}" alt="" loading="lazy"><span class="in"><span class="t">{e(ev["when"])}</span><span class="n">{e(ev["title"])}</span><span class="w">{e(ev["where"].split(",")[0].split(" · ")[0])}</span></span></a>' for ev in today_events)

    def row(s, kicker=True):
        img = f'<img src="{e(s["image"]["src"])}" alt="">' if s.get("image") else ""
        return f'<a class="row{"" if img else " noimg"}" href="{s["url"]}">{img}<div>{('<span class="kicker">' + e(s["section"]) + '</span>') if kicker else ""}<h3>{e(s["title"])}</h3><p>{e(dek(s))}</p><div class="meta">{e(s["source_name"])}</div></div></a>'
    groups = {}
    for s_ in rest:
        if s_ in side_items:
            continue
        groups.setdefault(s_["section"], []).append(s_)
    if "Business spotlight" in groups:  # spotlight block comes first among the topic blocks
        groups = {"Business spotlight": groups.pop("Business spotlight"), **groups}
    topics = "".join(f'<section class="topic{" w" if sec in WARM else ""}"><h2>{e(sec)}<a href="/section/{slug(sec)}.html">More →</a></h2>{"".join(row(x, False) for x in xs[:3])}</section>' for sec, xs in groups.items())
    mke = d.get("milwaukee", [])
    h = d.get("history")
    hist = (f'<section class="block"><h2>Bay View history</h2><div class="hist"><div><img src="{e(h["image"]["src"])}" alt="{e(h["image"]["alt"])}"><div class="cap">{e(h["image"]["credit"])}</div></div>'
            f'<div><div class="yr">{e(h["year"])}</div><p>{e(h["text"])}</p><a class="kicker" href="{e(h["source_url"])}">{e(h["source_name"])} →</a></div></div></section>') if h else ""
    home = (f'<div class="utils">{util_html}</div>{ticker}'
            f'<section class="front"><a class="lead" href="{lead["url"]}">{lead_img}<span class="kicker">{e(lead["section"])}</span><h2>{e(lead["title"])}</h2><p>{e(dek(lead))}</p><div class="meta">{e(lead["source_name"])}</div></a>'
            f'<div class="side">{side}</div></section>'
            f'<section class="tonight"><h2><span>Tonight in Bay View</span><a href="/events.html">All events →</a></h2><div class="chips">{chips}</div></section>'
            f'<div class="topics">{topics}</div>'
            f'<a class="mke" href="/milwaukee.html"><div><div class="k">Milwaukee today · {len(mke)} stories</div><div class="hl">{e(mke[0]["title"]) if mke else ""}</div></div><span class="go">Read Milwaukee →</span></a>'
            f'{hist}')
    (OUT / "issues").mkdir(exist_ok=True)
    (OUT / "issues" / f'{d["date"]}.html').write_text(shell("The Bay View Bulletin · " + d["display_date"], home, d))
    if not newest:
        return
    (OUT / "index.html").write_text(shell("The Bay View Bulletin", home, d, "Today", {"title": "The Bay View Bulletin · " + d["display_date"], "desc": lead["title"]}, "/"))

    # events
    cal, cur = [], None
    for ev in d["events"]:
        if ev["day"] != cur:
            cur = ev["day"]
            cal.append(f'<div class="cal-day">{e(cur)}</div>')
        cal.append(f'<div class="ev"><img src="{e(venue_img(ev))}" alt="" loading="lazy"><span class="t">{e(ev["when"])}</span><div><a href="{e(ev["link"])}" class="n">{e(ev["title"])}</a><div class="w">{e(ev["where"])}</div></div><span class="pill">{e(ev["kind"])}</span></div>')
    kinds = sorted({ev["kind"] for ev in d["events"]})
    filt = '<div class="filters"><span class="on">All</span>' + "".join(f"<span>{e(k)}</span>" for k in kinds) + "</div>"
    (OUT / "events.html").write_text(shell("Events · The Bay View Bulletin", f'<h1 class="pagehead">Events in Bay View</h1><p class="pagedek">Shows, family time, markets and meetings, today and ahead.</p>{filt}{"".join(cal)}', d, "Events"))

    # milwaukee
    lst = "".join(f'<a href="{e(m["source_url"])}"><span class="kicker">{e(m.get("tag"))}</span><h3>{e(m["title"])}</h3><p>{e(m.get("body"))}</p><div class="meta">{e(m["source_name"])}</div></a>' for m in mke)
    (OUT / "milwaukee.html").write_text(shell("Milwaukee · The Bay View Bulletin", f'<h1 class="pagehead">Milwaukee today</h1><p class="pagedek">The citywide news that matters to Bay View: as many stories as the day calls for.</p><div class="list">{lst}</div>', d, "Milwaukee"))


SECTION_PAGES = {"food": ("Food & Drink", {"Food & Drink", "Fish fry"}), "city": ("City Hall", {"City Hall", "Streets", "Bay View"}),
                 "safety": ("Safety", {"Safety", "Protests"}), "more": ("More from Bay View", None)}


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "story").mkdir(parents=True)
    (OUT / "section").mkdir()
    (OUT / "assets").mkdir()
    (OUT / "assets/v2.css").write_text(CSS)
    (OUT / "CNAME").write_text("bayviewbulletin.com\n")
    (OUT / ".nojekyll").write_text("")
    for f in (ROOT / "static").iterdir():
        (shutil.copytree if f.is_dir() else shutil.copy)(f, OUT / f.name)
    files = sorted((ROOT / "content/issues").glob("*.json"))
    issues = [json.loads(f.read_text()) for f in files]
    for i, d in enumerate(issues):
        build_one(d, i == len(issues) - 1)
    d = issues[-1]
    recent = [s for s in reversed(ALL_STORIES)][:400]

    def listing(items):
        return '<div class="list">' + "".join(f'<a href="{s["url"]}"><span class="kicker">{e(s["section"])} · {e(s["display_date"])}</span><h3>{e(s["title"])}</h3><p>{e(dek(s))}</p></a>' for s in items) + "</div>"
    labels = sorted({s["section"] for s in recent})
    for lab in labels:
        items = [s for s in recent if s["section"] == lab]
        (OUT / "section" / f"{slug(lab)}.html").write_text(shell(lab + " · The Bay View Bulletin", f'<h1 class="pagehead">{e(lab)}</h1><p class="pagedek">Recent {e(lab.lower())} news from Bay View.</p>' + (listing(items) or "<p>Nothing yet.</p>"), d))
    for key, (title, labs) in SECTION_PAGES.items():
        items = [s for s in recent if labs is None or s["section"] in labs]
        active = {"food": "Food & Drink", "city": "City Hall", "safety": "Safety", "more": "More"}[key]
        body = f'<h1 class="pagehead">{e(title)}</h1>' + (listing(items) if items else '<p class="pagedek">No recent items. Check back tomorrow morning.</p>')
        (OUT / "section" / f"{key}.html").write_text(shell(title + " · The Bay View Bulletin", body, d, active))
    arch = "".join(f'<a href="/issues/{x["date"]}.html"><h3>{e(x["display_date"])}</h3><p>{e(x["greeting"][:160])}…</p></a>' for x in reversed(issues))
    (OUT / "archive.html").write_text(shell("Archive · The Bay View Bulletin", f'<h1 class="pagehead">Archive</h1><p class="pagedek">Every day&rsquo;s front page, newest first.</p><div class="list">{arch}</div>', d, ""))
    dirs = json.loads((ROOT / "content/directory.json").read_text())
    def socials(b):
        links = []
        if b.get("instagram"): links.append(f'<a href="https://www.instagram.com/{e(b["instagram"])}/" rel="noopener">Instagram</a>')
        if b.get("facebook"): links.append(f'<a href="https://www.facebook.com/{e(b["facebook"])}" rel="noopener">Facebook</a>')
        if b.get("x"): links.append(f'<a href="https://x.com/{e(b["x"])}" rel="noopener">X</a>')
        if b.get("website"): links.append(f'<a href="{e(b["website"])}" rel="noopener">Website</a>')
        return (' · ' + ' · '.join(links)) if links else ''
    rows = "".join(f'<div class="ev" style="grid-template-columns:minmax(0,1fr) auto"><div><span class="n">{e(b["name"])}</span><div class="w">{e(b["address"])}{" (verifying)" if b.get("verify") else ""}{socials(b)}</div></div><span class="pill">{e(b["type"])}</span></div>' for b in sorted(dirs, key=lambda b: b["name"].lower()))
    (OUT / "directory.html").write_text(shell("Directory · The Bay View Bulletin", f'<h1 class="pagehead">Bay View business directory</h1><p class="pagedek">The shops, venues and institutions we watch. Missing one? <a href="{TIPS}" style="color:var(--lake)">Tell us</a>.</p>{rows}', d, ""))
    about = f"""<article class="story"><h1>Bay View's morning paper</h1><div class="body">
<p>The Bay View Bulletin is a free daily guide to what's happening in Milwaukee's Bay View neighborhood, updated every morning. We gather it from local news outlets, the neighborhood's own businesses and organizations, public social media posts and city records, and every item links back to the people who did the reporting.</p>
<p><strong>Where we cover:</strong> Bay View as neighbors know it, from the harbor and Jones Island south to Holt and Morgan avenues, and from I-43 east to Lake Michigan.</p>
<p><strong>How we report:</strong> news from the last 24 hours plus what's coming up. Safety coverage sticks to notable incidents, and we never name private individuals. Protests and rallies are listed neutrally, for any cause. Photos come from the original source or free-licensed collections, always credited; if you own a photo and want it removed, tell us and it comes down.</p>
<p><a class="btn" href="{TIPS}">Send a tip or a correction</a></p></div></article>"""
    (OUT / "about.html").write_text(shell("About · The Bay View Bulletin", about, d, ""))
    # search index + page
    idx = [{"t": s["title"], "d": dek(s), "u": s["url"], "k": s["section"], "dt": s["display_date"]} for s in recent]
    idx += [{"t": m["title"], "d": m.get("body", "")[:160], "u": m["source_url"], "k": "Milwaukee", "dt": x["display_date"]} for x in issues for m in x.get("milwaukee", [])]
    idx += [{"t": b["name"], "d": b["type"] + " · " + b["address"], "u": "/directory.html", "k": "Directory", "dt": ""} for b in dirs]
    idx += [{"t": ev["title"], "d": ev["when"] + " · " + ev["where"], "u": "/events.html", "k": "Event", "dt": ev["day"]} for ev in d["events"]]
    (OUT / "search.json").write_text(json.dumps(idx, ensure_ascii=False))
    search = f"""<h1 class="pagehead">Search</h1><p class="pagedek">Stories, events, Milwaukee news and Bay View businesses.</p>
<input id="q" type="search" placeholder="Try: pizza, Cactus Club, parking, MPS" autofocus style="width:100%;font:400 20px var(--sans);padding:12px 14px;border:2px solid var(--ink);border-radius:4px;background:var(--paper);color:var(--ink)">
<p id="n" class="pagedek" style="margin-top:10px"></p><div class="list" id="r"></div>
<script>
let I=[];fetch('/search.json').then(r=>r.json()).then(j=>{{I=j;go()}});
const q=document.getElementById('q'),r=document.getElementById('r'),n=document.getElementById('n');
const esc=s=>String(s).replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}})[c]);
function go(){{const w=q.value.toLowerCase().split(' ').filter(Boolean);
 const hits=w.length?I.filter(x=>w.every(t=>(x.t+' '+x.d+' '+x.k).toLowerCase().includes(t))):[];
 n.textContent=w.length?hits.length+' result'+(hits.length==1?'':'s'):'';
 r.innerHTML=hits.slice(0,60).map(x=>'<a href="'+esc(x.u)+'"><span class="kicker">'+esc(x.k)+(x.dt?' · '+esc(x.dt):'')+'</span><h3>'+esc(x.t)+'</h3><p>'+esc(x.d)+'</p></a>').join('');}}
q.addEventListener('input',go);const p=new URLSearchParams(location.search).get('q');if(p){{q.value=p}}
</script>"""
    (OUT / "search.html").write_text(shell("Search · The Bay View Bulletin", search, d, "Search", None, "/search.html"))
    # map
    # Map shows events and stories only; the directory is used just to place event venues.
    pts = []
    for ev in d["events"]:
        v = next((b for b in dirs if b.get("lat") and (b["name"].split(" (")[0] in ev["where"] or b["address"].split(" ")[0] in ev["where"])), None)
        if ev.get("lat") or v:
            pts.append({"n": ev["title"], "s": ev["day"] + " · " + ev["when"] + " · " + ev["where"], "lat": ev.get("lat") or v["lat"], "lon": ev.get("lon") or v["lon"], "c": "ev", "u": ev["link"]})
    for mk in d.get("milwaukee", []):
        if mk.get("lat"):
            pts.append({"n": mk["title"], "s": "Milwaukee · " + mk.get("tag", ""), "lat": mk["lat"], "lon": mk["lon"], "c": "mke", "u": mk["source_url"]})
    for st in [x for x in ALL_STORIES if x["issue_date"] == d["date"] and x.get("lat")]:
        pts.append({"n": st["title"], "s": st["section"], "lat": st["lat"], "lon": st["lon"], "c": "story", "u": st["url"]})
    leaflet = '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>'
    mapbody = f"""<h1 class="pagehead">Bay View map</h1><p class="pagedek"><span style="color:var(--warm)">●</span> Events &nbsp; <span style="color:var(--lake)">●</span> Today's Bay View stories &nbsp; <span style="color:#6B4FA0">●</span> Milwaukee stories</p>
<div id="map" style="height:70vh;min-height:420px;border:1px solid var(--rule)"></div>
<script>
const P={json.dumps(pts, ensure_ascii=False)};
const m=L.map('map').setView([42.996,-87.895],14);const B=[];
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}}).addTo(m);
const C={{ev:'#C9541F',story:'#1F4E79',biz:'#7A7F86',mke:'#6B4FA0'}};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}})[c]);
P.forEach(p=>L.circleMarker([p.lat,p.lon],{{radius:p.c=='biz'?6:9,color:'#fff',weight:2,fillColor:C[p.c],fillOpacity:.95}}).addTo(m)
 .bindPopup('<strong>'+esc(p.n)+'</strong><br>'+esc(p.s)+'<br><a href="'+esc(p.u)+'">Details →</a>'));
const btn=L.control({{position:'topright'}});btn.onAdd=()=>{{const b=L.DomUtil.create('button');b.textContent='Show all of Milwaukee';b.style.cssText='font:600 14px sans-serif;padding:8px 12px;background:#fff;border:2px solid #121212;border-radius:4px;cursor:pointer';let z=0;b.onclick=e=>{{L.DomEvent.stop(e);z=!z;if(z){{m.fitBounds(L.latLngBounds(P.map(p=>[p.lat,p.lon])).pad(.1));b.textContent='Zoom to Bay View'}}else{{m.setView([42.996,-87.895],14);b.textContent='Show all of Milwaukee'}}}};return b}};btn.addTo(m);
</script>"""
    (OUT / "map.html").write_text(shell("Map · The Bay View Bulletin", mapbody, d, "Map", None, "/map.html", leaflet))
    print("built", OUT, len(issues), "issue(s)")


if __name__ == "__main__":
    build()

