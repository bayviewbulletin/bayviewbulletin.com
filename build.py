#!/usr/bin/env python3
"""Build The Bay View Bulletin static site.

Input:  content/issues/YYYY-MM-DD.json, content/directory.json
Output: docs/ (index.html = newest issue, issues/<date>.html, archive, about, directory, assets, CNAME)

Items with "hold": true are never published; they are written to review/<date>.md for Ben.
"""
import html, json, shutil
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "docs"
TAGLINE = "Bay View's morning paper"
TIPS_URL = "https://forms.gle/REPLACE_WITH_GOOGLE_FORM"   # swap in once the Google Form exists
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,700;9..144,800&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&display=swap" rel="stylesheet">')

SECTIONS = [  # key, heading, dek
    ("top", "Top stories", ""),
    ("openings", "Openings & closings", ""),
    ("development", "Development & City Hall", ""),
    ("streets", "Streets & parking", ""),
    ("schools", "Schools & family", ""),
    ("parks", "Parks & lakefront", ""),
    ("protests", "Protests & rallies", "Neutral listings for any cause: what, when, where and who's organizing."),
    ("safety", "Safety", "Notable, safety-relevant incidents only. We don't name private individuals."),
    ("realestate", "Real estate", ""),
    ("help", "Ways to help", ""),
    ("fishfry", "Fish Fry Friday", ""),
    ("pets", "Lost & found pets", ""),
    ("sports", "Bay View High sports", ""),
    ("remembrances", "Remembrances", ""),
]

e = lambda s: html.escape(str(s or ""), quote=True)


def page(title, body, desc="Daily news for Milwaukee's Bay View neighborhood.", hero=None, edition=""):
    if hero:
        mast = (f'<header class="masthead"><img class="hero" src="{e(hero["src"])}" alt="{e(hero["alt"])}">'
                f'<div class="hero-credit">Photo: <a href="{e(hero["credit_url"])}">{e(hero["credit"])}</a></div>')
    else:
        mast = '<header class="masthead plain">'
    mast += (f'<div class="masthead-inner"><div class="edition">{edition}</div>'
             f'<h1 class="title"><a href="/">The Bay View Bulletin</a></h1><p class="tagline">{TAGLINE}</p></div></header>')
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
{FONTS}<link rel="stylesheet" href="/assets/style.css"></head><body>
<div class="topbar"><div class="topbar-inner"><span>Bay View, Milwaukee · Weekdays by 6:30 a.m.</span>
<nav aria-label="Site"><a href="/">Today</a><a href="/archive.html">Archive</a><a href="/directory.html">Directory</a><a href="/about.html">About</a><a href="{TIPS_URL}">Send a tip</a></nav></div></div>
{mast}
{body}
<footer class="site"><p><strong>The Bay View Bulletin</strong> covers Bay View from the harbor and Jones Island south to Holt and Morgan avenues, and from I-43 east to the lake.</p>
<p>Every item links to its original reporting. Summaries are ours; photos belong to the credited owners and link back to them. Spot a mistake or want a photo removed? <a href="{TIPS_URL}">Tell us</a>.</p></footer>
</body></html>"""


def figure(img):
    if not img:
        return ""
    return (f'<figure><img src="{e(img["src"])}" alt="{e(img["alt"])}" loading="lazy">'
            f'<figcaption>Photo: <a href="{e(img["credit_url"])}">{e(img["credit"])}</a></figcaption></figure>')


def item(it):
    src = ""
    if it.get("source_url"):
        src = f'<a href="{e(it["source_url"])}">{e(it["source_name"])}{" · " + e(it["date"]) if it.get("date") else ""}</a>'
    elif it.get("source_name"):
        src = f'<span>{e(it["source_name"])}</span>'
    tag = f'<span class="tag">{e(it["tag"])}</span>' if it.get("tag") else ""
    cls = "item has-img" if it.get("image") else "item"
    return (f'<li class="{cls}"><div class="text"><h3>{e(it["title"])}</h3>'
            f'{"<p>" + e(it["body"]) + "</p>" if it.get("body") else ""}<div class="meta">{tag}{src}</div></div>'
            f'{figure(it.get("image"))}</li>')


def issue_page(d, review_lines):
    secs = d["sections"]
    nav, parts, quiet = [], [], []
    for key, head, dek in SECTIONS:
        items = [i for i in secs.get(key, []) if not i.get("hold")]
        review_lines += [f"- **{head}:** {i['title']} ({i.get('source_url','')})\n  - Why held: {i.get('hold_reason','')}" for i in secs.get(key, []) if i.get("hold")]
        if not items:
            if key != "fishfry":
                quiet.append(head)
            continue
        nav.append(f'<li><a href="#{key}">{e(head)} <span class="n">{len(items)}</span></a></li>')
        parts.append(f'<section id="{key}"><h2>{e(head)}</h2>{"<p class=dek>" + e(dek) + "</p>" if dek else ""}'
                     f'<ul class="items">{"".join(item(i) for i in items)}</ul></section>')
        if key == "top":  # events + catch-up go right after the top stories
            if d.get("events"):
                rows, cur = [], None
                for ev in d["events"]:
                    if ev["day"] != cur:
                        cur = ev["day"]
                        rows.append(f'<tr class="day"><td colspan="2">{e(cur)}</td></tr>')
                    rows.append(f'<tr><td class="when">{e(ev["when"])}</td><td class="what"><strong>{e(ev["title"])}</strong> · {e(ev["where"])} · <a href="{e(ev["link"])}">Details</a></td></tr>')
                nav.append(f'<li><a href="#events">Events & music <span class="n">{len(d["events"])}</span></a></li>')
                parts.append(f'<section id="events"><h2>Events & music</h2><p class="dek">Today and coming up in the neighborhood.</p>'
                             f'<div class="cal-wrap"><table class="cal"><tbody>{"".join(rows)}</tbody></table></div></section>')
            if d.get("catching_up"):
                lis = "".join(f'<li>{e(c["title"])} · <a href="{e(c["source_url"])}">{e(c["source_name"])}, {e(c["date"])}</a></li>' for c in d["catching_up"])
                nav.append('<li><a href="#catching-up">Catching up</a></li>')
                parts.append(f'<section id="catching-up" class="catchup"><h2>Catching up</h2><p class="dek">First issue, so here\'s what you may have missed in recent weeks.</p><ul>{lis}</ul></section>')
    if d.get("milwaukee"):
        nav.append(f'<li><a href="#milwaukee">Milwaukee top {len(d["milwaukee"])} <span class="n">{len(d["milwaukee"])}</span></a></li>')
        parts.append(f'<section id="milwaukee"><h2>Milwaukee top {len(d["milwaukee"])}</h2><p class="dek">The biggest stories from the rest of the city.</p>'
                     f'<ol class="items mke">{"".join(item(i) for i in d["milwaukee"])}</ol></section>')
    h = d.get("history")
    nav.append('<li><a href="#weather">Weather & history</a></li>')
    hist = ""
    if h:
        hist = (f'<div class="card"><h3>Bay View history moment</h3><div class="big">{e(h["year"])}</div>{figure(h.get("image"))}'
                f'<p>{e(h["text"])}</p><p><a href="{e(h["source_url"])}">{e(h["source_name"])}</a></p></div>')
    weather = d.get("weather") or {"text": "Today's National Weather Service forecast for the Bay View shoreline, with lake winds and waves for walkers on the lakefront path.", "url": "https://forecast.weather.gov/MapClick.php?lat=42.99&lon=-87.89"}
    parts.append(f'<section id="weather"><h2>Weather & history</h2><div class="two"><div class="card"><h3>Lakefront forecast</h3><p>{e(weather["text"])}</p>'
                 f'<p><a class="btn" href="{e(weather["url"])}">See today\'s forecast</a></p></div>{hist}</div></section>')
    if quiet:
        parts.append(f'<p class="quiet"><strong>Quiet today:</strong> {e(", ".join(quiet))}. {e(d.get("quiet_note",""))}</p>')
    nav.append(f'<li><a href="{TIPS_URL}">Send a tip</a></li>')
    body = (f'<div class="wrap"><nav class="index" aria-label="Sections in this issue"><h2>In this issue</h2><ol>{"".join(nav)}</ol></nav>'
            f'<main><p class="greeting">{e(d["greeting"])}</p>{"".join(parts)}</main></div>')
    ed = f'<span class="badge">No. {d["number"]}</span><span>{e(d["display_date"])}</span>'
    return page(f'The Bay View Bulletin · {d["display_date"]}', body, d["greeting"], d.get("lead_image"), ed)


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "issues").mkdir(parents=True)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    (OUT / "CNAME").write_text("bayviewbulletin.com\n")
    (OUT / ".nojekyll").write_text("")
    (ROOT / "review").mkdir(exist_ok=True)

    issues = sorted((ROOT / "content/issues").glob("*.json"), reverse=True)
    archive = []
    for i, f in enumerate(issues):
        d = json.loads(f.read_text())
        review = []
        doc = issue_page(d, review)
        (OUT / "issues" / f"{d['date']}.html").write_text(doc)
        if i == 0:
            (OUT / "index.html").write_text(doc)
        if review:
            (ROOT / "review" / f"{d['date']}.md").write_text(f"# Held for review: {d['display_date']}\n\n" + "\n".join(review) + "\n")
        archive.append(f'<li><a href="/issues/{d["date"]}.html">{e(d["display_date"])}</a><span>No. {d["number"]}</span></li>')

    (OUT / "archive.html").write_text(page("Archive · The Bay View Bulletin",
        f'<div class="wrap single"><main><section><h2>Every issue</h2><ul class="archive">{"".join(archive)}</ul></section></main></div>'))

    rows = "".join(f'<tr><td><strong>{e(b["name"])}</strong></td><td>{e(b["type"])}</td><td>{e(b["address"])}{" <em>(verifying)</em>" if b.get("verify") else ""}</td></tr>'
                   for b in sorted(json.loads((ROOT / "content/directory.json").read_text()), key=lambda b: b["name"].lower()))
    (OUT / "directory.html").write_text(page("Directory · The Bay View Bulletin",
        f'<div class="wrap single"><main><section><h2>Bay View business directory</h2><p class="dek">The shops, venues and institutions we watch every week. Missing a business? <a href="{TIPS_URL}">Add it</a>.</p>'
        f'<div class="cal-wrap"><table class="dir"><thead><tr><th>Business</th><th>Type</th><th>Address</th></tr></thead><tbody>{rows}</tbody></table></div></section></main></div>'))

    about = f"""<div class="wrap single"><main class="prose">
<h2>Bay View's morning paper</h2>
<p>The Bay View Bulletin is a free daily digest of what's happening in Milwaukee's Bay View neighborhood. It's put together every weekday morning from local news outlets, the neighborhood's own businesses and organizations, public social media posts, and city records. Every item links back to the people who did the reporting.</p>
<h2>What we cover</h2>
<p>Openings and closings, development and City Hall, streets and parking, schools and family, parks and the lakefront, events and live music, protests and rallies, safety, real estate, ways to help, Friday fish fries, lost and found pets, Bay View High sports, remembrances of community figures, and the ten biggest Milwaukee stories of the day.</p>
<h2>Where we cover</h2>
<p>Bay View as most neighbors know it: from the harbor and Jones Island south to Holt and Morgan avenues, and from I-43 east to Lake Michigan, including Humboldt Park, South Shore Park and the stretch along Kinnickinnic Avenue.</p>
<h2>How we report</h2>
<ul><li>News from the last 24 hours, plus upcoming events.</li>
<li>Safety coverage is limited to notable incidents, and we don't name private individuals.</li>
<li>Protests and rallies are listed neutrally, for any cause.</li>
<li>Photos come from the original source or free-licensed collections, always credited and linked. If you own a photo and want it removed, tell us and it comes down.</li>
<li>Found an error? <a href="{TIPS_URL}">Let us know</a> and we'll correct it.</li></ul>
<h2>Send a tip</h2>
<p>Saw paper go up on a storefront window? Heard about a show? <a class="btn" href="{TIPS_URL}">Send a tip</a></p>
</main></div>"""
    (OUT / "about.html").write_text(page("About · The Bay View Bulletin", about))
    print(f"Built {len(issues)} issue(s) into {OUT}")


if __name__ == "__main__":
    build()
