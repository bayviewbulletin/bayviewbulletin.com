#!/usr/bin/env python3
"""Bay View Bulletin v2 layout prototype: front page + story pages + events + Milwaukee.
Reads the same content/issues/*.json; writes preview_v2/ (not published)."""
import html, json, re, shutil, math, datetime as dt
from pathlib import Path

ROOT = Path(__file__).parent
import sys
OUT = ROOT / ("preview_v2" if "--preview" in sys.argv else "docs")
SITE = "https://bayviewbulletin.com"
TIPS = "https://docs.google.com/forms/d/e/1FAIpQLSfXNc2RsIhvMPCfcZ9CYb6QIx78RZSr2Ar3YzT5ik9xyPhi7Q/viewform"
ASK = TIPS + "?usp=pp_url&entry.1019545553=Ask%20the%20Bulletin%3A%20"  # tip form prefilled for reader questions
LISTING = TIPS + "?usp=pp_url&entry.1019545553=Listing%20submission%3A%20"  # Nov. 25: agents submit Bay View listings
EXPLAINERS = []  # evergreen explainers from content/explainers.json
e = lambda s: html.escape(str(s or ""), quote=True)
NAV = [("Home", "/"), ("Events", "/events.html"), ("Buzz", "/buzz.html"), ("Spotlight", "/spotlight.html"), ("Food & Drink", "/section/food.html"), ("Real Estate", "/real-estate.html"), ("City Hall", "/section/city.html"),
       ("Safety", "/section/safety.html"), ("History", "/history.html"), ("More", "/section/more.html")]
SEARCH_ICON = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5 21 21"/></svg>'
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


WARM = {"Business spotlight", "Food & Drink", "Ways to help", "Parks", "Fish fry", "Pets"}
# Nov. 25: topic labels that have a combined menu page link there, and every label page underlines the right menu item.
LABEL_PAGE = {"Real estate": "/real-estate.html", "Food & Drink": "/section/food.html", "City Hall": "/section/city.html", "Safety": "/section/safety.html", "Business spotlight": "/spotlight.html"}
LABEL_ACTIVE = {"Real estate": "Real Estate", "Food & Drink": "Food & Drink", "Fish fry": "Food & Drink", "City Hall": "City Hall", "Streets": "City Hall", "Safety": "Safety", "Protests": "Safety", "Business spotlight": "Spotlight"}
GUIDES = []  # seasonal guides from content/guides.json (Nov. 25)
OPENINGS = []  # opened / closed / coming soon tracker from content/openings.json (Nov. 25)
LISTINGS = {}  # Bay View real estate from content/listings.json (Nov. 25)


def money(it):
    return it.get("price") or ("$" + format(it["price_num"], ",") if it.get("price_num") else "Price on request")


def listing_facts(it):
    bits = [money(it) + (" / mo" if it.get("deal") == "lease" and it.get("price_num") and it["price_num"] < 20000 else "")]
    if it.get("beds"):
        bits.append(f'{it["beds"]} bd')
    if it.get("baths"):
        bits.append(f'{it["baths"]} ba')
    if it.get("sqft"):
        bits.append(str(it["sqft"]) if not str(it["sqft"]).isdigit() else f'{int(it["sqft"]):,} sq. ft.')
    return " · ".join(bits)


RE_STATUS = {"new": "New", "active": "For sale", "price_cut": "Price cut", "pending": "Pending", "sold": "Sold", "off_market": "Off market", "open_house": "Open house"}
RE_KIND = {"home": "Home", "condo": "Condo", "multi": "Multi-family", "land": "Land", "commercial": "Commercial"}


def re_badge(it, today):
    st = it.get("status", "active")
    if it.get("deal") in ("lease", "sale or lease") and st == "active":
        lab = "For lease" if it["deal"] == "lease" else "Sale / lease"
    elif st == "active" and it.get("first_seen") and (dt.date.fromisoformat(today) - dt.date.fromisoformat(it["first_seen"])).days <= 7 and it.get("kind") != "commercial":
        lab = "New"
    else:
        lab = RE_STATUS.get(st, st.title())
    return f'<b class="rb {e(st)}">{e(lab)}</b>'


RE_MAPS = True  # Ben, Nov. 25: small locator map on listing cards without a photo (set False to turn off)


def re_map(lat, lon, label):
    """Locator thumbnail: 2x2 OpenStreetMap tiles at zoom 16 in an SVG, window clamped around the pin. Credited per OSM's tile policy."""
    import math
    z = 16
    n = 2 ** z
    fx = (lon + 180) / 360 * n
    fy = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    tx, ty = int(fx), int(fy)
    ox = tx - (1 if fx - tx < .5 else 0)
    oy = ty - (1 if fy - ty < .5 else 0)
    px, py = (fx - ox) * 256, (fy - oy) * 256
    W, H = 400, 300
    vx, vy = min(max(px - W / 2, 0), 512 - W), min(max(py - H / 2, 0), 512 - H)
    tiles = "".join(f'<image href="https://tile.openstreetmap.org/{z}/{ox + i}/{oy + j}.png" x="{i * 256}" y="{j * 256}" width="256" height="256"/>' for i in (0, 1) for j in (0, 1))
    pin = (f'<g transform="translate({px:.1f} {py:.1f})"><path d="M0 0 C-14 -18 -14 -34 0 -34 C14 -34 14 -18 0 0Z" fill="#C9541F" stroke="#fff" stroke-width="3"/>'
           f'<circle cx="0" cy="-23" r="5" fill="#fff"/></g>')
    return (f'<div class="rpic map"><svg viewBox="{vx:.0f} {vy:.0f} {W} {H}" preserveAspectRatio="xMidYMid slice" role="img" aria-label="Map: {e(label)}">{tiles}{pin}</svg>'
            f'<span class="rosm">© OpenStreetMap</span></div>')


def re_bigmap(items):
    """Ben, Nov. 26: interactive map of every live listing on the Real Estate page (Leaflet + OpenStreetMap tiles, loaded only on this page)."""
    pts = [{"a": it["address"], "f": listing_facts(it), "k": "c" if it.get("kind") == "commercial" else "r", "u": it["url"],
            "b": it.get("listed_by", ""), "lat": it["lat"], "lon": it["lon"]} for it in items if it.get("lat")]
    if not pts:
        return ""
    data = json.dumps(pts).replace("</", "<\\/")
    return ('<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">'
            '<div class="remap-wrap"><div id="remap" role="region" aria-label="Map of Bay View listings"></div>'
            '<div class="remap-key"><span><i class="dot r"></i>Homes and condos</span><span><i class="dot c"></i>Commercial</span><span>Tap a pin for details</span></div></div>'
            '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>'
            f'<script>(function(){{var P={data};if(!window.L)return;var m=L.map("remap",{{scrollWheelZoom:false}});'
            'L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:"&copy; <a href=\\"https://www.openstreetmap.org/copyright\\">OpenStreetMap</a> contributors"}).addTo(m);'
            'var g={},b=[];P.forEach(function(p){var k=p.lat.toFixed(5)+","+p.lon.toFixed(5);(g[k]=g[k]||[]).push(p);});'
            'Object.keys(g).forEach(function(k){var ps=g[k],p=ps[0];var c=ps.some(function(x){return x.k=="r"})?"#1F4E79":"#C9541F";'
            'var h="<b>"+p.a.replace(/\\s*\\(.*\\)/,"")+"</b>"+(ps.length>1?"<br>"+ps.length+" listings":"")+ps.map(function(x){return "<div style=\\"margin-top:6px\\">"+x.f+"<br><a href=\\""+x.u+"\\" target=\\"_blank\\" rel=\\"noopener\\">Listing: "+x.b+"</a></div>"}).join("");'
            'L.circleMarker([p.lat,p.lon],{radius:ps.length>1?10:8,color:"#fff",weight:2,fillColor:c,fillOpacity:.95}).addTo(m).bindPopup(h);b.push([p.lat,p.lon]);});'
            'm.fitBounds(b,{padding:[30,30],maxZoom:15});})();</script>')


def re_card(it, today, small=False):
    img = it.get("image")
    pic = (f'<div class="rpic"><img src="{e(img["src"])}" alt="{e(img.get("alt") or it["address"])}" loading="lazy"><span class="rcred">{cap_label(img)}{e(img.get("credit", ""))}</span></div>' if img
           else re_map(it["lat"], it["lon"], it["address"]) if RE_MAPS and it.get("lat")
           else f'<div class="rpic none"><span>{e(RE_KIND.get(it.get("kind"), "Property"))}</span><b>{e(money(it))}</b></div>')
    oh = ""
    for o in it.get("open_house") or []:
        if o.get("date", "") >= today:
            oh = f'<div class="roh">Open house {e(dt.date.fromisoformat(o["date"]).strftime("%a. %b. %-d"))}{(", " + e(o["time"])) if o.get("time") else ""}</div>'
            break
    sold = f' · Sold {e(it["sold"]["date"])}' if it.get("sold") else ""
    return (f'<a class="rcard{" small" if small else ""}" href="{e(it["url"])}">{pic}<div class="rtxt">{re_badge(it, today)}<span class="rk">{e(RE_KIND.get(it.get("kind"), ""))}</span>'
            f'<h3>{e(it["address"])}</h3><div class="rf">{e(listing_facts(it))}{sold}</div>{oh}'
            + ("" if small else f'<p>{e(it.get("note", ""))}</p>')
            + f'<div class="rsrc">Listing: {e(it.get("listed_by") or it.get("source", ""))}</div></div></a>')


def redirect_page(to):
    return f'<!DOCTYPE html><meta charset="utf-8"><title>The Bay View Bulletin</title><link rel="canonical" href="{to}"><meta http-equiv="refresh" content="0; url={to}"><a href="{to}">The Bay View Bulletin</a>'


def cap_label(img):
    """Caption prefix: stock photos say so (Nov. 25)."""
    return "Stock photo: " if "stock photo" in ((img or {}).get("alt", "") + (img or {}).get("credit", "")).lower() else "Photo: "


def is_weather(s):
    return bool(s.get("weather")) or bool(re.search(r"\b(forecast|weather)\b", s.get("title", ""), re.I))


CM = lambda f: "/photos/venues/" + re.sub(r"[^a-z0-9]+", "-", f.lower().rsplit(".", 1)[0]).strip("-") + ".jpg"  # local copies of Wikimedia Commons photos (Nov. 25)
VENUES = [("Cactus Club", CM("Milwaukee January 2025 04 (Cactus Club).jpg")), ("Puddler", CM("2024 08 07 Puddler's Hall 1.jpg")),
          ("Library", CM("Bay View Branch.jpg")), ("Garibaldi", CM("Milwaukee January 2025 16 (S. Kinnickinnic Avenue).jpg")),
          ("Kinnickinnic", CM("Milwaukee January 2025 16 (S. Kinnickinnic Avenue).jpg")), ("Methodist", CM("SouthShore Park 1.jpg")),
          ("", CM("Milwaukee January 2025 16 (S. Kinnickinnic Avenue).jpg"))]


_DIR_PHOTOS = None


def dir_photo(ev):
    """The venue's own photo from content/directory.json ("photo": {src, credit, credit_url}), matched by
    street address or business name (Ben, Nov. 26: events without a flyer show the business, inside or out)."""
    global _DIR_PHOTOS
    if _DIR_PHOTOS is None:
        _DIR_PHOTOS = []
        for b in json.loads((ROOT / "content/directory.json").read_text()):
            if b.get("photo", {}).get("src"):
                _DIR_PHOTOS.append((re.sub(r"\W", "", b.get("address", "").lower()), b["name"].lower(), b["photo"]))
    where = ev.get("where", "")
    w_addr = re.sub(r"\W", "", where.lower())
    venue = where.split(",")[0].strip().lower()
    for addr, name, ph in _DIR_PHOTOS:
        if (addr and addr in w_addr) or (venue and (venue == name or (len(name) > 5 and (venue in name or name in venue)))):
            return ph
    return None


def venue_img(ev):
    """The event's own flyer/photo, else a photo of its venue (Ben, Nov. 17: always show a photo, never a text tile)."""
    if ev.get("image"):
        return ev["image"]
    ph = dir_photo(ev)
    if ph:
        return ph["src"]
    for k, u in VENUES:
        if k in ev["where"] or k in ev["title"]:
            return u


def ev_thumb(ev, today, cls=""):
    alt = ("Flyer: " + ev["title"]) if ev.get("image") else ""
    return f'<img src="{e(venue_img(ev))}" alt="{e(alt)}" loading="lazy"{(" class=" + chr(34) + cls + chr(34)) if cls else ""}>'



MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def ev_date(ev, today):
    """Calendar date of an event from its day label ("Today, Tue. Nov. 17" / "Sat. Nov. 21"), relative to the issue date."""
    m = re.search(r"([A-Z][a-z]{2})[a-z]*\.? (\d{1,2})\b", ev["day"].split(",")[-1])
    if not m or m.group(1) not in MONTHS:
        return today
    y = today.year + (1 if MONTHS[m.group(1)] < today.month - 6 else 0)
    try:
        return dt.date(y, MONTHS[m.group(1)], int(m.group(2)))
    except ValueError:
        return today


def ev_when_tags(dd, today):
    """Date buckets for the Events page tabs: today, tomorrow, weekend (the coming Fri-Sun, or the current one), week (next 7 days)."""
    tags = []
    if dd == today: tags.append("today")
    if dd == today + dt.timedelta(days=1): tags.append("tomorrow")
    wd = today.weekday()  # Mon=0
    fri = today + dt.timedelta(days=(4 - wd) % 7) if wd <= 4 else today - dt.timedelta(days=wd - 4)
    if fri <= dd <= fri + dt.timedelta(days=2) and dd >= today: tags.append("weekend")
    if today <= dd <= today + dt.timedelta(days=6): tags.append("week")
    return " ".join(tags)


def ev_free(ev):
    return bool(re.search(r"\bfree\b", (ev.get("desc", "") + " " + ev.get("title", "")), re.I)) and not re.search(r"free (?:with|for members|pickle|shots?)\b", ev.get("desc", ""), re.I)


def ctoff(dstr):
    """UTC offset for Milwaukee on that date ("-06:00" in winter, "-05:00" in summer)."""
    import zoneinfo
    o = dt.datetime.fromisoformat(dstr[:10] + "T12:00").replace(tzinfo=zoneinfo.ZoneInfo("America/Chicago")).strftime("%z")
    return o[:3] + ":" + o[3:]


def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def abs_url(u):
    return u if not u or u.startswith("http") else SITE + u


FB_URL = "https://www.facebook.com/profile.php?id=61596882362012"  # the Bulletin's own Page and Instagram (Nov. 26)
IG_URL = "https://www.instagram.com/bayviewbulletin/"
PUBLISHER = {"@type": "NewsMediaOrganization", "name": "The Bay View Bulletin", "url": SITE + "/", "logo": {"@type": "ImageObject", "url": SITE + "/apple-touch-icon.png"}, "sameAs": [FB_URL, IG_URL]}


def story_ld(s, d):
    obj = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": s["title"][:110], "description": dek(s),
           "datePublished": d["date"] + "T06:00:00" + ctoff(d["date"]), "dateModified": (s.get("updated") or d["date"]) + "T06:00:00" + ctoff(s.get("updated") or d["date"]),
           "mainEntityOfPage": SITE + s["url"], "author": PUBLISHER, "publisher": PUBLISHER, "articleSection": s["section"],
           "contentLocation": {"@type": "Place", "name": "Bay View, Milwaukee, Wisconsin"}}
    if s.get("image"):
        obj["image"] = [abs_url(s["image"]["src"])]
    if s.get("source_url"):
        obj["isBasedOn"] = s["source_url"]
    return ld(obj)


def ev_start(ev, dd):
    m = re.match(r"\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?", ev.get("when", ""), re.I)
    ap = re.search(r"(am|pm|a\.m\.|p\.m\.)", ev.get("when", ""), re.I)
    if not m or not ap:
        return dd.isoformat()
    h = int(m.group(1)) % 12 + (12 if ap.group(1).lower().startswith("p") else 0)
    return f"{dd.isoformat()}T{h:02d}:{int(m.group(2) or 0):02d}:00" + ctoff(dd.isoformat())


def events_ld(events, today):
    out = []
    for ev in events:
        dd = ev_date(ev, today)
        where = ev["where"].split(" · ")[0]
        name, _, addr = where.partition(", ")
        x = {"@type": "Event", "name": ev["title"], "startDate": ev_start(ev, dd), "eventStatus": "https://schema.org/EventScheduled",
             "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
             "location": {"@type": "Place", "name": name, "address": {"@type": "PostalAddress", "streetAddress": addr or name, "addressLocality": "Milwaukee", "addressRegion": "WI", "addressCountry": "US"}},
             "url": ev.get("link") or SITE + "/events.html"}
        if ev.get("desc"): x["description"] = ev["desc"]
        if ev.get("image"): x["image"] = [abs_url(ev["image"])]
        if ev_free(ev): x["isAccessibleForFree"] = True
        out.append(x)
    return ld({"@context": "https://schema.org", "@graph": out})


VTZ = ("BEGIN:VTIMEZONE\r\nTZID:America/Chicago\r\nBEGIN:DAYLIGHT\r\nTZOFFSETFROM:-0600\r\nTZOFFSETTO:-0500\r\nTZNAME:CDT\r\nDTSTART:19700308T020000\r\n"
       "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU\r\nEND:DAYLIGHT\r\nBEGIN:STANDARD\r\nTZOFFSETFROM:-0500\r\nTZOFFSETTO:-0600\r\nTZNAME:CST\r\n"
       "DTSTART:19701101T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU\r\nEND:STANDARD\r\nEND:VTIMEZONE\r\n")


def ics_text(t):
    return str(t).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ev_ics(ev, today, stamp):
    """One VEVENT (and the Google Calendar link) for an event; 2 hours long when a start time is known, else all day."""
    dd = ev_date(ev, today)
    st = ev_start(ev, dd)
    uid = f"{dd.isoformat()}-{slug(ev['title'])[:40]}@bayviewbulletin.com"
    if "T" in st:
        t0 = dt.datetime.fromisoformat(st[:19])
        t1 = t0 + dt.timedelta(hours=2)
        when = f"DTSTART;TZID=America/Chicago:{t0:%Y%m%dT%H%M%S}\r\nDTEND;TZID=America/Chicago:{t1:%Y%m%dT%H%M%S}\r\n"
        gdates = f"{t0:%Y%m%dT%H%M%S}/{t1:%Y%m%dT%H%M%S}"
    else:
        when = f"DTSTART;VALUE=DATE:{dd:%Y%m%d}\r\nDTEND;VALUE=DATE:{dd + dt.timedelta(days=1):%Y%m%d}\r\n"
        gdates = f"{dd:%Y%m%d}/{dd + dt.timedelta(days=1):%Y%m%d}"
    where = ev["where"].split(" · ")[0] + ", Milwaukee, WI"
    desc = (ev.get("desc", "") + " " + (ev.get("link") or "")).strip() + " (via The Bay View Bulletin)"
    vevent = (f"BEGIN:VEVENT\r\nUID:{uid}\r\nDTSTAMP:{stamp}\r\n{when}SUMMARY:{ics_text(ev['title'])}\r\nLOCATION:{ics_text(where)}\r\n"
              f"DESCRIPTION:{ics_text(desc)}\r\n" + (f"URL:{ev['link']}\r\n" if ev.get("link") else "") + "END:VEVENT\r\n")
    import urllib.parse as _u
    gurl = "https://calendar.google.com/calendar/render?" + _u.urlencode({"action": "TEMPLATE", "text": ev["title"], "dates": gdates, "ctz": "America/Chicago", "details": desc, "location": where})
    return uid.split("@")[0], vevent, gurl


def ics_wrap(body, name="The Bay View Bulletin: Bay View events"):
    return ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//The Bay View Bulletin//Events//EN\r\nCALSCALE:GREGORIAN\r\nMETHOD:PUBLISH\r\n"
            f"X-WR-CALNAME:{name}\r\nX-WR-TIMEZONE:America/Chicago\r\n" + VTZ + body + "END:VCALENDAR\r\n")


def sunrise_sunset(day, lat=42.99, lon=-87.89, tz=-6):
    n = day.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    decl = 0.006918 - 0.399912*math.cos(g) + 0.070257*math.sin(g) - 0.006758*math.cos(2*g) + 0.000907*math.sin(2*g) - 0.002697*math.cos(3*g) + 0.00148*math.sin(3*g)
    eqt = 229.18*(0.000075 + 0.001868*math.cos(g) - 0.032077*math.sin(g) - 0.014615*math.cos(2*g) - 0.040849*math.sin(2*g))
    ha = math.degrees(math.acos(math.cos(math.radians(90.833))/(math.cos(math.radians(lat))*math.cos(decl)) - math.tan(math.radians(lat))*math.tan(decl)))
    fmt = lambda mins: (dt.datetime(2000, 1, 1) + dt.timedelta(minutes=mins + tz*60)).strftime("%-I:%M")
    return fmt(720 - 4*(lon + ha) - eqt), fmt(720 - 4*(lon - ha) - eqt)


CSS = """
:root{--paper:#FFFFFF;--ink:#121212;--muted:#5C6066;--rule:#E3E1DC;--soft:#F6F4EF;--lake:#1F4E79;--lake-soft:#E8EFF6;--warm:#C9541F;--warm-soft:#FBEDE3;--buzz:#FFE14D;--buzz-ink:#111111;--buzz-muted:#4A4A4A;--hot:#D7261E;--on-color:#FFFFFF;
--serif:"Source Serif 4",Georgia,serif;--plate:"Playfair Display",Georgia,serif;--sans:"Source Sans 3","Helvetica Neue",Arial,sans-serif;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--paper:#111315;--ink:#ECEAE4;--muted:#A1A6AD;--rule:#2A2E33;--soft:#1A1D21;--lake:#8DBDE3;--lake-soft:#17232F;--warm:#F29A55;--warm-soft:#2B1E16;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:400 17px/1.5 var(--sans)}
a{color:inherit;text-decoration:none}a:hover h2,a:hover h3,a:hover .hl{text-decoration:underline;text-underline-offset:3px}
a:focus-visible{outline:3px solid var(--lake);outline-offset:2px}img{display:block;max-width:100%}
.wrap{max-width:1140px;margin:0 auto;padding:0 20px}
.plate{text-align:center;padding:18px 0 10px}.dateline{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);display:flex;justify-content:center;gap:14px;flex-wrap:wrap}
.plate .rule{border-top:3px double var(--ink);margin:10px 0 0}.plate h1{font:900 clamp(38px,6.4vw,68px)/1.05 var(--plate);margin:8px 0 2px;letter-spacing:-.01em}
.plate .tag{font:italic 400 16px var(--serif);color:var(--muted);margin:0 0 10px}
nav.sections{border-top:1px solid var(--ink);border-bottom:1px solid var(--rule);white-space:nowrap}nav.sections ul{overflow-x:auto;scrollbar-width:none}nav.sections ul::-webkit-scrollbar{display:none}
nav.sections ul{list-style:none;margin:0 auto;padding:0 20px;max-width:1140px;display:flex;gap:26px;justify-content:center;align-items:stretch}
nav.sections a{display:inline-flex;align-items:center;height:100%;padding:11px 0;font:600 15px var(--sans)}nav.sections a.on{box-shadow:inset 0 -3px var(--lake)}
nav.sections li.find{border-left:1px solid var(--rule);padding-left:22px;margin-left:-4px}nav.sections li.find a{color:var(--muted)}nav.sections li.find a:hover,nav.sections li.find a.on{color:var(--ink)}
@media(max-width:700px){nav.sections ul{justify-content:flex-start;gap:22px;padding-right:20px}
nav.sections ul{-webkit-mask-image:linear-gradient(90deg,#000 calc(100% - 48px),transparent);mask-image:linear-gradient(90deg,#000 calc(100% - 48px),transparent)}
nav.sections ul.end{-webkit-mask-image:none;mask-image:none}}
.utils{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-bottom:1px solid var(--rule);margin-bottom:22px}
.util{padding:12px 14px;border-right:1px solid var(--rule);display:grid;gap:2px;align-content:start}.util:last-child{border-right:0}
.util .k{font:700 11px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}.util .v{font:700 17px var(--serif)}.util .s{font-size:13px;color:var(--muted)}
.util.alert .v{color:var(--warm)}.util .k::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--lake);margin-right:6px;vertical-align:1px}.util.warm .k::before{background:var(--warm)}
@media(max-width:900px){.utils{grid-template-columns:repeat(2,minmax(0,1fr))}.util:nth-child(2n){border-right:0}.util:nth-child(-n+2){border-bottom:1px solid var(--rule)}}
.school{border-top:1px solid var(--rule);padding:14px 0}.school h2{font:700 22px/1.2 var(--serif);margin:0 0 4px}.school ul{margin:8px 0;padding-left:18px;font:15px/1.6 var(--sans)}.school .src{font:13px var(--sans);color:var(--muted)}
.buzz{margin:26px 0;background:var(--buzz);color:var(--buzz-ink);border:3px solid var(--buzz-ink);box-shadow:6px 6px 0 var(--buzz-ink);padding:16px 18px 18px}
.buzz header{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;border-bottom:3px solid var(--buzz-ink);padding-bottom:8px;margin-bottom:14px}
.buzz header h2{font:900 italic 34px/1 var(--sans);text-transform:uppercase;letter-spacing:-.01em;margin:0}
.buzz header h2 span{background:var(--hot);color:var(--on-color);padding:0 8px;transform:skew(-6deg);display:inline-block}
.buzz header p{margin:0;font:700 13px var(--sans);text-transform:uppercase;letter-spacing:.06em}
.buzz header a{margin-left:auto;color:var(--buzz-ink);font:800 14px var(--sans);text-decoration:underline}
.bzgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px}
.bz{position:relative;background:var(--on-color);border:2px solid var(--buzz-ink);padding:12px 14px 12px}
.bz.hot{background:#FFF4F3}
.bzimg{margin:-12px -14px 10px}.bzimg img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;border-bottom:2px solid var(--buzz-ink);filter:contrast(1.08) saturate(1.15)}.bzimg figcaption{font:11px var(--sans);color:var(--buzz-muted);padding:3px 14px 0}.bzimg figcaption a{color:var(--buzz-muted)}
.bz .bk{display:inline-block;background:var(--buzz-ink);color:var(--buzz);font:900 11px var(--sans);text-transform:uppercase;letter-spacing:.1em;padding:3px 7px;margin-bottom:6px}
.bz.hot .bk{background:var(--hot);color:var(--on-color)}
.bz h3{font:900 21px/1.12 var(--sans);margin:2px 0 6px;text-transform:none}
.bz p{font:15px/1.45 var(--serif);margin:0 0 8px}
.bz .via{display:block;font:700 12px/1.4 var(--sans);color:var(--buzz-muted);text-decoration:none}.bz .via:hover{text-decoration:underline}
.stamp{position:absolute;z-index:2;top:8px;right:-6px;transform:rotate(8deg);border:2px solid var(--hot);color:var(--hot);font:900 11px var(--sans);letter-spacing:.12em;text-transform:uppercase;padding:2px 6px;background:var(--on-color)}
.buzz.page{margin-top:10px}.bzday{font:900 15px var(--sans);text-transform:uppercase;letter-spacing:.08em;margin:18px 0 10px}
.bznote{font:13px/1.5 var(--sans);margin:18px 0 0;color:var(--buzz-muted)}.bznote a{color:var(--buzz-ink)}
.bztease{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:22px 0;padding:10px 14px;background:var(--buzz);color:var(--buzz-ink);border:2px solid var(--buzz-ink);box-shadow:4px 4px 0 var(--buzz-ink);text-decoration:none}
.bztease:hover .bzh{text-decoration:underline}
.bzlogo{font:900 italic 18px/1 var(--sans);text-transform:uppercase}.bzlogo span{background:var(--hot);color:var(--on-color);padding:0 5px;display:inline-block;transform:skew(-6deg)}
.bzk{background:var(--buzz-ink);color:var(--buzz);font:900 11px var(--sans);text-transform:uppercase;letter-spacing:.1em;padding:3px 7px}
.bzh{font:900 18px/1.2 var(--sans);flex:1;min-width:200px}
.bzgo{font:800 14px var(--sans);text-decoration:underline}
@media (prefers-color-scheme:dark){.buzz,.bz,.bz h3,.bz p{color:var(--buzz-ink)}.bz .via{color:var(--buzz-muted)}}
@media(max-width:520px){.utils{grid-template-columns:repeat(2,minmax(0,1fr))}.util{border-right:0!important;border-bottom:1px solid var(--rule)!important;padding:10px 10px 10px 0}.util:nth-child(odd){border-right:1px solid var(--rule)!important;padding-right:10px}.util:nth-child(even){padding-left:12px}.util:nth-last-child(-n+2){border-bottom:0!important}.util .v{font-size:17px}}
.ticker{display:flex;gap:12px;align-items:center;font-size:15px;border-bottom:1px solid var(--rule);padding:10px 0;margin:0 0 18px;overflow:hidden;white-space:nowrap}.ticker b{flex:0 0 auto;font:700 11px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--on-color);background:var(--warm);padding:3px 7px;border-radius:2px;position:relative;z-index:1}.ticker .vp{flex:1;overflow:hidden;-webkit-mask-image:linear-gradient(90deg,transparent,#000 24px,#000 calc(100% - 40px),transparent);mask-image:linear-gradient(90deg,transparent,#000 24px,#000 calc(100% - 40px),transparent)}.ticker .track{display:inline-flex;animation:tick var(--dur,40s) linear infinite}.ticker:hover .track,.ticker:focus-within .track{animation-play-state:paused}.ticker .set{display:inline-flex}.ticker .set a{padding-right:14px;color:inherit;text-decoration:none;font-weight:600}.ticker .set a:hover{text-decoration:underline}.ticker .set a::after{content:"\\00B7";margin-left:14px;color:var(--muted);font-weight:400}@keyframes tick{from{transform:translateX(0)}to{transform:translateX(-50%)}}@media(prefers-reduced-motion:reduce){.ticker .vp{overflow-x:auto}.ticker .track{animation:none}.ticker .set+.set{display:none}}
.front{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:28px;padding-bottom:24px;border-bottom:1px solid var(--ink)}
@media(max-width:820px){.front{grid-template-columns:1fr}}
.feature{display:block;margin:6px 0 26px;padding-bottom:22px;border-bottom:1px solid var(--ink);max-width:860px}.feature h2{font:700 34px/1.12 var(--serif);margin:6px 0 8px}.feature p{font:18px/1.5 var(--serif);margin:0 0 8px}.feature .cap{font:12px var(--sans);color:var(--muted);margin:-6px 0 10px}
.lead figure{margin:0 0 12px}.lead img{width:100%;aspect-ratio:16/9;object-fit:cover;background:var(--soft)}
.kicker{font:700 12px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--lake)}.kicker.w{color:var(--warm)}
.lead h2{font:700 clamp(28px,3.4vw,40px)/1.12 var(--serif);margin:4px 0 8px;text-wrap:balance}.lead p{margin:0;font-size:18px;color:var(--muted);max-width:60ch}
.meta{font-size:13px;color:var(--muted);margin-top:6px}
.side{display:grid;align-content:start}.side a{padding:12px 0;border-bottom:1px solid var(--rule);display:block}.side a:first-child{padding-top:0}
.side h3{font:700 19px/1.25 var(--serif);margin:2px 0 4px;text-wrap:balance}.side p{margin:0;font-size:15px;color:var(--muted)}
.brief{margin:0 0 22px;padding:12px 16px 10px;border-left:4px solid var(--lake);background:var(--lake-soft)}.brief h2{font:700 13px var(--sans);letter-spacing:.08em;text-transform:uppercase;margin:0 0 6px;color:var(--lake)}.brief ul{margin:0;padding-left:18px}.brief li{font:16px/1.45 var(--serif);margin:3px 0}.brief li a{color:inherit;text-decoration:underline;text-decoration-color:var(--rule);text-underline-offset:2px}.brief li a:hover{text-decoration-color:var(--lake)}
.lead.textlead figure{float:right;width:40%;margin:6px 0 10px 18px}.lead.textlead img{aspect-ratio:4/3}.lead.textlead::after{content:"";display:block;clear:both}@media(max-width:520px){.lead.textlead figure{width:42%;margin-left:12px}.lead.textlead h2{font-size:26px}}
.tonight.weekend{border-top-color:var(--lake);background:var(--lake-soft)}.tonight.weekend h2 a{color:var(--lake)}.chip .d{display:block;font:700 12px var(--sans);color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
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
.story .body{font:400 19px/1.6 var(--serif)}.story .body p{margin:0 0 1em}
.gallery{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin:22px 0}.gallery figure{margin:0}.gallery img{width:100%;aspect-ratio:1/1;object-fit:cover}.gallery figcaption{font:12px/1.4 var(--sans);color:var(--muted);margin-top:4px}.gallery figcaption a{color:var(--muted)}
.morelinks{border-top:1px solid var(--rule);margin:22px 0;padding-top:12px}.morelinks h2{font:700 13px var(--sans);text-transform:uppercase;letter-spacing:.08em;margin:0 0 8px}.morelinks ul{margin:0;padding-left:18px;font:16px/1.7 var(--sans)}
.spot-past{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}.spot-past a{color:inherit;text-decoration:none}.spot-past img{width:100%;aspect-ratio:4/3;object-fit:cover}.spot-past h3{font:700 18px/1.2 var(--serif);margin:6px 0 2px}.story figure{margin:16px 0}.story img{width:100%;aspect-ratio:16/9;object-fit:cover}
.btn{display:inline-block;margin:18px 0;padding:12px 18px;background:var(--lake);color:var(--paper);font:700 16px var(--sans);border-radius:4px}
.more h2{font:800 20px var(--serif);border-top:1px solid var(--ink);padding-top:16px;margin-top:30px}
.cal-day{font:700 13px var(--sans);letter-spacing:.08em;text-transform:uppercase;border-bottom:1px solid var(--ink);padding:18px 0 6px}
.ev{display:grid;grid-template-columns:72px 90px minmax(0,1fr) auto;gap:14px;padding:10px 0;border-bottom:1px solid var(--rule);align-items:center}
.ev img{width:72px;height:54px;object-fit:cover;background:var(--soft)}.ev .t{font:700 15px var(--sans);color:var(--warm)}.ev .n{font:700 17px var(--serif)}.ev .w{font-size:14px;color:var(--muted)}.ev .d{font:15px/1.45 var(--serif);color:var(--ink);margin-top:3px;max-width:62ch}
.pill{font:700 11px var(--sans);letter-spacing:.06em;text-transform:uppercase;border:1px solid var(--rule);padding:3px 7px;border-radius:99px;color:var(--muted)}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0 4px}.filters button{border:1px solid var(--ink);padding:6px 12px;border-radius:99px;font:600 14px var(--sans);background:var(--paper);color:var(--ink);cursor:pointer}.filters button:hover{background:var(--soft)}.filters button.on{background:var(--ink);color:var(--paper)}.filters button:focus-visible{outline:2px solid var(--lake);outline-offset:2px}[hidden]{display:none!important}
.list a{display:block;padding:16px 0;border-bottom:1px solid var(--rule)}.list h3{font:700 21px/1.25 var(--serif);margin:2px 0 4px}.list p{margin:0;color:var(--muted)}
.pagehead{font:800 34px var(--serif);margin:24px 0 2px}.topics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 36px;padding-top:6px}@media(max-width:820px){.topics{grid-template-columns:1fr}}.topic{padding:18px 0 6px}.topic>h2{font:800 20px var(--serif);margin:0 0 4px;padding-top:10px;border-top:4px solid var(--lake);display:flex;justify-content:space-between;align-items:baseline}.topic.w>h2{border-top-color:var(--warm)}.topic>h2 a{font:600 14px var(--sans);color:var(--lake)}.topic.w>h2 a{color:var(--warm)}.topic .row{padding:12px 0;border-bottom:1px solid var(--rule)}.topic .row:last-child{border-bottom:0}.pagedek{color:var(--muted);margin:0 0 10px}.xbox{display:block;margin:18px 0;padding:12px 16px;border:1px solid var(--rule);border-left:4px solid var(--lake);background:var(--lake-soft);color:var(--ink);text-decoration:none}.xbox b{display:block;font:700 18px/1.3 var(--serif);margin-top:2px}.picks{display:grid;gap:12px;margin:14px 0 6px}.pick{display:grid;grid-template-columns:120px minmax(0,1fr);gap:14px;padding:12px;border:1px solid var(--rule);border-top:4px solid var(--warm);background:var(--paper);color:var(--ink);text-decoration:none}.pick img,.pick .evtile{width:120px;height:90px;object-fit:cover}.pick .evtile i{font-size:30px}.pick h3{font:700 19px/1.25 var(--serif);margin:2px 0 4px}.pick p{margin:0;font:15px/1.45 var(--serif)}.pick .t{font:700 13px var(--sans);color:var(--warm)}@media(max-width:520px){.pick{grid-template-columns:84px minmax(0,1fr)}.pick img,.pick .evtile{width:84px;height:66px}}.askbox{padding:16px 18px;background:var(--warm-soft);border-top:4px solid var(--warm);margin:14px 0 22px}.askbox p{margin:0 0 10px}.bzarch{font:600 15px/1.6 var(--sans);margin:18px 0 0;color:var(--buzz-ink)}.bzarch h3{font:800 18px var(--sans);margin:0 0 4px}.bzarch a{color:var(--buzz-ink);text-decoration:underline}.evtile{display:flex;flex-direction:column;align-items:center;justify-content:center;background:var(--lake);color:var(--on-color);font-family:var(--sans);line-height:1;text-align:center}.evtile b{font:700 10px var(--sans);letter-spacing:.1em;opacity:.85}.evtile i{font:800 22px var(--serif);font-style:normal;margin:2px 0}.evtile small{display:none;font:600 10px var(--sans);letter-spacing:.06em;text-transform:uppercase;opacity:.85}.evtile.k2{background:var(--ink);color:var(--paper)}.evtile.k3{background:var(--warm)}.evtile.k4{background:var(--warm-soft);color:var(--warm)}.evtile.k5{background:var(--lake-soft);color:var(--lake)}.ev .evtile{width:72px;height:54px}.chip .evtile{width:100%;height:110px}.chip .evtile i{font-size:40px}.chip .evtile b{font-size:12px}.chip .evtile small{display:block;margin-top:4px}@media(max-width:600px){.ev .evtile{grid-row:1/span 2;width:64px;height:48px}}.evcal{font:600 13px var(--sans);color:var(--muted);margin-top:4px}.evcal a{color:var(--lake)}@media(max-width:600px){.ev{grid-template-columns:64px minmax(0,1fr);gap:2px 12px;align-items:start}.ev img{grid-row:1/span 2;width:64px;height:48px}.ev .t{grid-column:2;font-size:14px}.ev>div{grid-column:2}.ev .pill{display:none}.ev[style*="grid-template-columns"]{grid-template-columns:minmax(0,1fr) auto!important}.ev[style*="grid-template-columns"]>div{grid-column:1}.ev[style*="grid-template-columns"] .pill{display:inline-block}}.filters.when{margin-bottom:0}.filters.kinds{margin-top:8px}.filters .free{border-color:var(--warm)!important}.filters button.on.free{background:var(--warm)!important;color:var(--on-color)!important;border-color:var(--warm)!important}@media(max-width:520px){.filters{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;padding-bottom:2px}.filters::-webkit-scrollbar{display:none}.filters button{flex:0 0 auto}}.corr{font:15px/1.5 var(--sans);background:var(--soft);border-left:4px solid var(--warm);padding:10px 14px;margin:18px 0}.story .body h2{font:800 20px var(--serif);margin:26px 0 6px}
/* Nov. 25: real estate */
.onmkt{margin:18px 0 0;padding:14px 16px;border:1px solid var(--rule);border-top:4px solid var(--lake)}.onmkt h2{display:flex;justify-content:space-between;align-items:baseline;margin:0 0 10px;font:800 18px var(--serif)}.onmkt h2 a{font:600 14px var(--sans);color:var(--lake)}
.rgrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.rgrid.big{grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin:8px 0 6px}@media(max-width:900px){.rgrid,.rgrid.big{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:520px){.rgrid,.rgrid.big{grid-template-columns:1fr}}
.rcard{display:flex;flex-direction:column;color:var(--ink);text-decoration:none;border:1px solid var(--rule);background:var(--paper)}.rcard:hover h3{color:var(--lake)}
.rpic{position:relative;aspect-ratio:4/3;overflow:hidden;background:var(--soft)}.rpic img{width:100%;height:100%;object-fit:cover;display:block}.rcred{position:absolute;right:6px;bottom:4px;font:11px var(--sans);color:#fff;text-shadow:0 1px 2px #000}
.rpic.map svg{width:100%;height:100%;display:block}.rosm{position:absolute;right:4px;bottom:2px;font:10px var(--sans);background:rgba(255,255,255,.8);padding:0 3px;color:#333}.rosm a{color:#333}
.rpic.none{display:flex;flex-direction:column;justify-content:flex-end;padding:12px 14px;background:var(--lake-soft)}.rpic.none span{font:700 11px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--lake)}.rpic.none b{font:900 26px/1.1 var(--plate);color:var(--lake)}
.rtxt{padding:10px 12px 12px}.rtxt h3{font:700 18px/1.25 var(--serif);margin:4px 0 2px}.rcard.small .rtxt h3{font-size:16px}.rf{font:600 14px var(--sans);color:var(--ink)}.rtxt p{margin:6px 0 0;font-size:15px;line-height:1.45;color:var(--muted)}
.rk{font:700 11px var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-left:6px}.rsrc{font:12px var(--sans);color:var(--muted);margin-top:6px}.roh{font:700 13px var(--sans);color:var(--warm);margin-top:4px}
.rb{display:inline-block;font:700 11px var(--sans);letter-spacing:.06em;text-transform:uppercase;padding:2px 6px;border-radius:2px;color:var(--on-color);background:var(--lake)}.rb.new,.rb.price_cut{background:var(--warm)}.rb.pending,.rb.sold,.rb.off_market{background:var(--muted)}
.rsum{margin:10px 0 0;font:14px var(--sans);color:var(--muted)}.rsec{font:800 22px var(--serif);margin:28px 0 8px;padding-top:10px;border-top:4px solid var(--lake)}.rsec span{font:700 14px var(--sans);color:var(--muted);margin-left:6px}
.rmkt{display:flex;flex-wrap:wrap;gap:12px 28px;padding:14px 16px;margin:10px 0;background:var(--lake-soft);border-left:4px solid var(--lake)}.rmkt div{display:flex;flex-direction:column}.rmkt b{font:900 26px var(--plate);color:var(--lake)}.rmkt span{font:600 13px var(--sans);color:var(--muted)}.rmkt p{flex-basis:100%;margin:0;font:13px var(--sans);color:var(--muted)}
.remap-wrap{margin:14px 0 4px}#remap{height:380px;border:1px solid var(--rule);z-index:0}@media(max-width:600px){#remap{height:300px}}.remap-key{display:flex;flex-wrap:wrap;gap:6px 18px;margin-top:6px;font:13px var(--sans);color:var(--muted)}.remap-key .dot{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:5px;vertical-align:-1px;border:2px solid #fff;box-shadow:0 0 0 1px var(--rule)}.dot.r{background:#1F4E79}.dot.c{background:#C9541F}.leaflet-popup-content{font:14px/1.4 var(--sans)}
/* Nov. 25: guides, openings tracker, City Hall this week */
.guidetease{display:flex;flex-wrap:wrap;gap:4px 12px;align-items:baseline;margin:14px 0 4px;padding:12px 16px;border:1px solid var(--rule);border-left:4px solid var(--warm);background:var(--warm-soft);color:var(--ink);text-decoration:none}.guidetease .k{font:700 11px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--on-color);background:var(--warm);padding:3px 7px;border-radius:2px}.guidetease b{font:700 19px/1.3 var(--serif)}.guidetease .go{font:600 14px var(--sans);color:var(--warm);margin-left:auto}.ocstrip{margin:18px 0 0;padding:14px 16px;border:1px solid var(--rule);border-top:4px solid var(--lake)}.ocstrip h2{display:flex;justify-content:space-between;align-items:baseline;margin:0 0 6px;font:800 18px var(--serif)}.ocstrip h2 a{font:600 14px var(--sans);color:var(--lake)}.ocstrip ul{list-style:none;margin:0;padding:0}.ocstrip li{padding:5px 0;font:16px/1.4 var(--serif)}.ocstrip li span{color:var(--muted);font-size:15px}.ocstrip b,.ocrow b{display:inline-block;font:700 11px var(--sans);letter-spacing:.06em;text-transform:uppercase;padding:2px 6px;border-radius:2px;margin-right:6px;color:var(--on-color);background:var(--lake)}.ocstrip b.closed,.ocrow b.closed,.ocstrip b.seasonal,.ocrow b.seasonal{background:var(--muted)}.ocstrip b.coming,.ocrow b.coming,.ocstrip b.closing,.ocrow b.closing{background:var(--warm)}.ocrow{display:grid;grid-template-columns:150px minmax(0,1fr);gap:12px;padding:12px 0;border-bottom:1px solid var(--rule)}.ocrow b{justify-self:start;height:fit-content}.ocrow h3{font:700 19px/1.3 var(--serif);margin:0}.ocrow h3 a{color:inherit}.ocrow .w{font:600 13px var(--sans);color:var(--muted);margin:2px 0}.ocrow p{margin:2px 0 0}.ocrow .src{color:var(--muted);font-size:14px}@media(max-width:520px){.ocrow{grid-template-columns:1fr;gap:4px}}.chw{display:block;margin:14px 0 20px;padding:14px 16px;border:1px solid var(--rule);border-left:4px solid var(--lake);background:var(--lake-soft);color:var(--ink);text-decoration:none}.chw h3{font:700 21px/1.25 var(--serif);margin:2px 0 4px}.chw p{margin:0;color:var(--muted)}.story .body ul{margin:0 0 14px;padding-left:22px}.story .body li{margin:0 0 6px}.gsec{margin:26px 0 0}.gsec>h2{font:800 22px var(--serif);margin:0 0 6px;padding-top:10px;border-top:4px solid var(--warm)}.gitem{padding:12px 0;border-bottom:1px solid var(--rule)}.gitem h3{font:700 19px/1.3 var(--serif);margin:0}.gitem h3 a{color:inherit}.gitem .gwhen{font:700 13px var(--sans);color:var(--warm);margin:3px 0}.gitem p{margin:2px 0 0}.gitem .meta{font:13px var(--sans);color:var(--muted);margin-top:4px}.gitem .meta a{color:var(--lake)}
.dateline .mk{width:26px;height:26px;display:block}.foot-brand{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:4px 10px;margin-bottom:8px;font:700 15px var(--sans);color:var(--ink)}.foot-brand img{width:28px;height:28px}.foot-brand em{font:italic 400 15px var(--serif);color:var(--muted)}
"""
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@900&family=Source+Sans+3:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,700;8..60,800&display=swap" rel="stylesheet">')




def ext_links(html):
    """External links open in a new tab; internal links stay in the same tab."""
    def fix(m):
        tag, url = m.group(0), m.group(1)
        if url.startswith(SITE) or "target=" in tag:
            return tag
        return tag[:-1].replace(' rel="noopener"', '') + ' target="_blank" rel="noopener">'
    return re.sub(r'<a\b[^>]*?href="(https?://[^"]+)"[^>]*>', fix, html)



TICKER = ""  # "Top news" strip shown under the menu on every page (built from the newest day)


def make_ticker(d):
    """Day's most important headlines in story order (top section first), spotlight excluded, each linking to its story."""
    items = []
    for key, sec in d["sections"].items():
        if key == "spotlight":
            continue
        for it in sec:
            if it.get("hold") or it.get("tag") == "Listings":
                continue
            items.append((it["title"], f"/story/{d['date']}-{slug(it['title'])}.html"))
    seen = set()
    items = [x for x in items if not (x[0] in seen or seen.add(x[0]))][:8]
    if len(items) < 3:  # Nov. 25 (Ben): hide the ticker on thin days instead of scrolling one headline
        return ""
    _set = "".join(f'<a href="{u}">{e(t)}</a>' for t, u in items)
    _dur = max(30, sum(len(t) for t, _ in items) // 5)
    return (f'<div class="wrap"><div class="ticker" aria-label="Today&rsquo;s top headlines"><b>Top news</b><div class="vp"><div class="track" style="--dur:{_dur}s">'
            f'<div class="set">{_set}</div><div class="set" aria-hidden="true">{_set}</div></div></div></div></div>')


def shell(title, body, d, active="Home", og=None, path="/", head=""):
    og = og or {}
    ogt, ogd = og.get("title", title), og.get("desc", "Bay View's morning paper: news, events and neighborhood talk for Milwaukee's Bay View, every morning by 6:30.")
    ogi = og.get("image") or SITE + "/og-default.png"
    meta = (f'<meta name="description" content="{e(ogd)}"><link rel="canonical" href="{SITE}{e(path)}">'
            f'<meta property="og:site_name" content="The Bay View Bulletin"><meta property="og:type" content="{og.get("type", "website")}">'
            f'<meta property="og:title" content="{e(ogt)}"><meta property="og:description" content="{e(ogd)}"><meta property="og:image" content="{e(ogi)}">'
            f'<meta property="og:url" content="{SITE}{e(path)}"><meta name="twitter:card" content="summary_large_image">'
            '<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="icon" href="/favicon-32.png" sizes="32x32"><link rel="apple-touch-icon" href="/apple-touch-icon.png"><link rel="manifest" href="/site.webmanifest">'
            '<meta name="theme-color" content="#1F4E79"><link rel="alternate" type="application/rss+xml" title="The Bay View Bulletin" href="/feed.xml">' + head)
    nav = "".join(f'<li><a href="{h}"{" class=on" if n == active else ""}>{n}</a></li>' for n, h in NAV)
    nav += f'<li class="find"><a href="/search.html" aria-label="Search" title="Search"{" class=on" if active == "Search" else ""}>{SEARCH_ICON}</a></li>'
    return ext_links(f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>{meta}{FONTS}<link rel="stylesheet" href="/assets/v2.css"><script data-goatcounter="https://bayviewbulletin.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script></head><body>
<header class="plate wrap"><div class="dateline"><span>{e(d['display_date'])}</span><a href="/" aria-label="The Bay View Bulletin home"><img class="mk" src="/mark.svg" alt="" width="26" height="26"></a><span>Bay View, Milwaukee</span></div>
<div class="rule"></div><h1><a href="/">The Bay View Bulletin</a></h1><p class="tag">Bay View's morning paper</p></header>
<nav class="sections" aria-label="Sections"><ul>{nav}</ul></nav>
{TICKER}<div class="wrap">{body}</div>
<footer><div class="wrap"><div class="foot-brand"><img src="/mark.svg" alt="" width="28" height="28"><span>The Bay View Bulletin</span><em>Bay View's morning paper</em></div>News, events and neighborhood talk, every morning by 6:30. No ads, no paywall.<br>Follow us: <a href="{IG_URL}">Instagram @bayviewbulletin</a> · <a href="{FB_URL}">Facebook</a><br>Covering Bay View from the harbor and Jones Island to Holt and Morgan avenues, I-43 to the lake.<br>
Every item links to the original reporting. Photos belong to their credited owners. <a href="{TIPS}">Send a tip</a> · <a href="/ask.html">Ask the Bulletin</a> · <a href="/explainers.html">Explainers</a> · <a href="/guides.html">Guides</a> · <a href="/real-estate.html">Real estate</a> · <a href="/openings.html">Opened &amp; closed</a> · <a href="/about.html">About</a> · <a href="/corrections.html">Corrections</a> · <a href="/schools.html">School days off</a> · <a href="/history.html">History</a> · <a href="/archive.html">Archive</a></div></footer>
<script>(function(){{var n=document.querySelector('nav.sections ul');if(!n)return;function f(){{n.classList.toggle('end',n.scrollLeft+n.clientWidth>=n.scrollWidth-4)}}n.addEventListener('scroll',f,{{passive:true}});f();var o=n.querySelector('a.on');if(o&&o.offsetLeft+o.offsetWidth>n.clientWidth)n.scrollLeft=o.offsetLeft-20}})();</script><script>document.addEventListener('click',function(ev){{var a=ev.target.closest&&ev.target.closest('a[href]');if(a&&a.host&&a.host!==location.host){{a.target='_blank';a.rel='noopener'}}}},true);</script></body></html>""")


ALL_STORIES = []
ALL_BUZZ = []  # tabloid items from every day, newest day last
BRIEFS = []  # older headlines (launch catch-up) that link straight to the source


def srcmeta(s):
    """Source line under a headline; citywide stories that affect Bay View get a Citywide label."""
    return ("Citywide · " if s.get("citywide") else "") + (s.get("source_name") or "")


SCHOOLS = json.loads((ROOT / "content/school_calendar.json").read_text())["schools"]


def school_off(sch, day):
    """Label if students at this school have no class on `day` (weekends excluded), else None."""
    iso = day.isoformat()
    for a, b, lab in sch["off"]:
        if a <= iso <= b:
            return lab
    if sch.get("last_day") and iso > sch["last_day"]:
        return "Summer break"
    if sch.get("first_day") and iso < sch["first_day"]:
        return "Summer break"
    return None


def next_off(sch, day):
    for a, b, lab in sorted(sch["off"]):
        if a > day.isoformat():
            return dt.date.fromisoformat(a), dt.date.fromisoformat(b), lab
    return None


def short_date(d0):
    return d0.strftime("%a. %b. ") + str(d0.day)


def schools_tile(day):
    mps = SCHOOLS[0]
    if day.weekday() >= 5:
        v = "No school (weekend)"
    else:
        lab = school_off(mps, day)
        v = f"No school: {lab}" if lab else "MPS in session"
    # other Bay View schools that differ from MPS today, else next MPS day off
    diff = [x["short"] for x in SCHOOLS[1:] if day.weekday() < 5 and bool(school_off(x, day)) != bool(school_off(mps, day))]
    nxt = day + dt.timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += dt.timedelta(days=1)
    tom = [x["short"] for x in SCHOOLS if school_off(x, nxt) and school_off(x, nxt) != "Summer break" and not (school_off(x, day) and day.weekday() < 5)]
    when = "Tomorrow" if (nxt - day).days == 1 else nxt.strftime("%A")
    if diff and not school_off(mps, day):
        s_ = "Off today: " + ", ".join(diff)
    elif tom:
        s_ = f"{when}, no school: " + ("all Bay View schools" if len(tom) == len(SCHOOLS) else ", ".join(tom))
    elif day.weekday() < 5 and school_off(mps, day) and school_off(mps, day) != "Summer break":
        back = day + dt.timedelta(days=1)
        while back.weekday() >= 5 or school_off(mps, back):
            back += dt.timedelta(days=1)
        s_ = f"Classes resume {short_date(back)}"
    else:
        n = next_off(mps, day)
        s_ = (f"Next day off: {short_date(n[0])}" + ("" if n[0] == n[1] else f"–{n[1].day}" if n[0].month == n[1].month else f" – {short_date(n[1])}")) if n else ""
    return v, s_


def schools_page(d):
    day = dt.date.fromisoformat(d["date"])
    rows = []
    for x in SCHOOLS:
        up = []
        for a, b, lab in sorted(x["off"]):
            if b < day.isoformat():
                continue
            A, B = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
            when = short_date(A) if A == B else f"{short_date(A)} – {short_date(B)}"
            up.append(f"<li><b>{e(when)}</b> · {e(lab)}</li>")
        today_lab = school_off(x, day) if day.weekday() < 5 else "Weekend"
        status = f"No school today ({e(today_lab)})" if today_lab else "In session today"
        addr = f' · {e(x["address"])}' if x.get("address") else ""
        note = f'<p class="pagedek">{e(x["note"])}</p>' if x.get("note") else ""
        last = f'<li><b>{e(short_date(dt.date.fromisoformat(x["last_day"])))}</b> · Last day of school</li>' if x.get("last_day") and x["last_day"] >= day.isoformat() else ""
        rows.append(f'<section class="school"><h2>{e(x["name"])}</h2><p class="kicker">{status}{addr}</p>{note}<ul>{"".join(up)}{last}</ul>'
                    f'<p class="src">Source: <a href="{e(x["source_url"])}" rel="noopener">{e(x["source_name"])}</a></p></section>')
    return (f'<h1 class="pagehead">School days off</h1><p class="pagedek">When Bay View kids are out of school this year. Snow days and emergency closures are posted on the front page the morning they happen. '
            f'Schools can change dates, so check with yours.</p>' + "".join(rows))



def buzz_card(b, big=False):
    stamp = '<span class="stamp">Unconfirmed</span>' if b.get("unconfirmed") else ""
    who = e(b.get("who") or "A neighbor") + ("" if (b.get("who") or "") == (b.get("where") or "") else f' in {e(b.get("where") or "the group")}')
    im = b.get("image")
    pic = (f'<figure class="bzimg"><img src="{e(im["src"])}" alt="{e(im.get("alt", ""))}" loading="lazy">'
           f'<figcaption>{cap_label(im)}<a href="{e(im.get("credit_url") or "#")}" rel="noopener">{e(im.get("credit", ""))}</a></figcaption></figure>') if im else ""
    return (f'<article class="bz{" hot" if b.get("tone") == "hot" else ""}">{stamp}{pic}<span class="bk">{e(b["kicker"])}</span>'
            f'<h3>{e(b["headline"])}</h3><p>{e(b["body"])}</p>'
            f'<a class="via" href="{e(b["source_url"])}" rel="noopener">— {who} · see the post →</a></article>')


BUZZ_NOTE = ("The Bay View Buzz rounds up what neighbors are posting about local businesses, events and oddities in public groups and on social media "
             "(Bay View Town Hall on Facebook, Reddit, Instagram). It's chatter, not reporting: items marked Unconfirmed haven't been verified. "
             "Want something corrected or removed? <a href=\"{TIPS}\">Tell us</a>.")


def feature_html(url, img, kicker, title, dk, meta, internal=True):
    """Big featured story at the top of a section page."""
    rel = "" if internal else ' rel="noopener"'
    pic = (f'<figure><img src="{e(img["src"])}" alt="{e(img.get("alt", ""))}"></figure>'
           f'<div class="cap">Photo: {e(img.get("credit", ""))}</div>') if img else ""
    return (f'<a class="lead feature" href="{e(url)}"{rel}>{pic}<span class="kicker">{e(kicker)}</span><h2>{e(title)}</h2>'
            + (f'<p>{e(dk)}</p>' if dk else "") + f'<div class="meta">{e(meta)}{"" if internal else " · Read the story →"}</div></a>')


def paras(text):
    out = []
    for p in (text or "").split("\n\n"):
        p = p.strip()
        if not p:
            continue
        lines = [l.strip() for l in p.split("\n") if l.strip()]
        if lines and all(l.startswith("- ") for l in lines):
            out.append("<ul>" + "".join(f"<li>{e(l[2:])}</li>" for l in lines) + "</ul>")
        else:
            out.append(f"<p>{e(p)}</p>")
    return "".join(out)


def gallery_html(s):
    g = s.get("gallery") or []
    if not g:
        return ""
    return ('<div class="gallery">' + "".join(
        f'<figure><a href="{e(i["src"])}"><img src="{e(i["src"])}" alt="{e(i.get("alt", ""))}" loading="lazy"></a>'
        f'<figcaption>{e(i.get("alt", ""))} · Photo: <a href="{e(i.get("credit_url") or "#")}" rel="noopener">{e(i.get("credit", ""))}</a></figcaption></figure>'
        for i in g) + "</div>")


def links_html(s):
    ls = s.get("links") or []
    if not ls:
        return ""
    name = s["title"].replace("Spotlight: ", "")
    return (f'<section class="morelinks"><h2>More about {e(name)}</h2><ul>'
            + "".join(f'<li><a href="{e(l["url"])}" rel="noopener">{e(l["label"])}</a></li>' for l in ls) + "</ul></section>")

ALL_HISTORY = []  # one Bay View history item per day (Ben, Nov. 13)


def history_title(h):
    if h.get("title"):
        return h["title"]
    t = h.get("text", "").split(". ")[0]
    return (t[:90] + "…") if len(t) > 90 else t


def history_page(d):
    """Write the day's history item to its own story page; return its URL."""
    h = d["history"]
    title = history_title(h)
    url = f"/history/{d['date']}-{slug(title)}.html"
    img = h.get("image") or {}
    fig = (f'<figure><img src="{e(img["src"])}" alt="{e(img.get("alt", ""))}"><div class="cap">Photo: <a href="{e(img.get("credit_url") or h.get("source_url") or "#")}">{e(img.get("credit", ""))}</a></div></figure>') if img else ""
    when = {"on this day": "On this day", "this week": "This week in history", "this month": "This month in history"}.get(h.get("match"), "Bay View history")
    now = h.get("now")
    nowh = f'<p class="pagedek" style="margin:14px 0"><strong>Now:</strong> <a href="{e(now["url"])}" style="color:var(--lake)">{e(now["name"])}</a></p>' if now else ""
    src = f'<a class="btn" href="{e(h["source_url"])}">Source: {e(h["source_name"])} →</a>' if h.get("source_url") else ""
    body = (f'<article class="story"><span class="kicker">Bay View history · {e(when)} · {e(h.get("year"))}</span><h1>{e(title)}</h1>{fig}'
            f'<div class="body">{paras(h.get("body") or h.get("text"))}</div>{nowh}{gallery_html(h)}{links_html(dict(h, title=title))}{src}'
            f'<p class="pagedek" style="margin-top:22px"><a href="/history.html" style="color:var(--lake)">More Bay View history →</a></p></article>')
    (OUT / "history").mkdir(exist_ok=True)
    (OUT / url.lstrip("/")).write_text(shell(title + " · Bay View history · The Bay View Bulletin", body, d, "", {"title": title, "desc": h.get("text", "")[:200], "image": abs_url(img.get("src")), "type": "article"}, url))
    ALL_HISTORY.append(dict(h, title=title, url=url, issue_date=d["date"], display_date=d["display_date"]))
    return url


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
    buzz = [b for b in d.get("buzz", []) if not b.get("hold")]
    ALL_BUZZ.append((d, buzz))
    for c in d.get("catching_up", []):
        if c.get("section"):
            BRIEFS.append(dict(c, label=SECTION_OF.get(c["section"], "Bay View")))
    # The daily business spotlight always gets its own block and is never the lead or a side headline.
    news = [s for s in stories if s["key"] != "spotlight"] or stories
    # Lead (Nov. 25, Ben): weather leads only when people must act (the day file marks that story "urgent": true, e.g. a
    # snow emergency or storm warning). On thin days with no Bay View news story to lead with, lead with the best Bay View
    # item of any kind: the day file's "lead" pick ({"kind": "buzz" | "spotlight" | "event" | "story", "title": ...}),
    # else the first photo Buzz item that is confirmed and not a stock photo, else the spotlight, else today's event with a flyer.
    def _story_ok(x):
        return x["key"] != "spotlight" and not (is_weather(x) and not x.get("urgent")) and not x.get("citywide")
    pick = d.get("lead") or {}
    lead = None
    if pick.get("kind") in ("story", "spotlight"):
        lead = next((x for x in stories if x["title"] == pick.get("title") or (pick["kind"] == "spotlight" and x["key"] == "spotlight")), None)
    if lead is None and not pick:
        cands = [x for x in stories if _story_ok(x)]
        lead = next((x for x in cands if x.get("image")), cands[0] if cands else None)
    lead_buzz = None
    if lead is None:
        _bz = [b for b in buzz if b.get("image") and not b.get("unconfirmed") and "stock photo" not in b["image"].get("alt", "").lower()]
        _ev = [ev for ev in d["events"] if ev["day"].startswith("Today") and ev.get("image")]
        _sp = next((x for x in stories if x["key"] == "spotlight"), None)
        if pick.get("kind") == "buzz":
            lead_buzz = next((b for b in buzz if b["headline"] == pick.get("title")), None)
        elif pick.get("kind") == "event":
            _ev = [ev for ev in d["events"] if ev["title"] == pick.get("title")] or _ev
        if lead_buzz is None and pick.get("kind") in (None, "buzz") and _bz:
            lead_buzz = _bz[0]
        if lead_buzz:
            _first = dek({"body": lead_buzz["body"].strip()})
            lead = {"key": "alt", "url": "/buzz.html", "section": "The Bay View Buzz · " + lead_buzz["kicker"], "title": lead_buzz["headline"],
                    "dek": _first, "image": lead_buzz["image"], "meta": (lead_buzz.get("who") or "A neighbor") + ("" if (lead_buzz.get("who") or "") == (lead_buzz.get("where") or "") else " in " + (lead_buzz.get("where") or "the group"))}
        elif _sp and pick.get("kind") in (None, "spotlight"):
            lead = _sp
        elif _ev:
            ev0 = _ev[0]
            lead = {"key": "alt", "url": ev0["link"], "section": "Today in Bay View · " + ev0["when"], "title": ev0["title"], "dek": ev0.get("desc", ""),
                    "image": {"src": venue_img(ev0), "alt": "Flyer: " + ev0["title"], "credit": ev0["where"].split(",")[0]}, "meta": ev0["where"]}
        else:
            lead = next((x for x in news if x.get("image")), news[0])
    rest = [s for s in stories if s is not lead]

    # story pages
    for s in stories:
        others = "".join(f'<a href="{o["url"]}"><span class="kicker">{e(o["section"])}</span><h3>{e(o["title"])}</h3><p>{e(dek(o))}</p></a>' for o in stories if o is not s)[:6000]
        img = (f'<figure><img src="{e(s["image"]["src"])}" alt="{e(s["image"]["alt"])}"><div class="cap">{cap_label(s["image"])}<a href="{e(s["image"]["credit_url"])}">{e(s["image"]["credit"])}</a></div></figure>') if s.get("image") else ""
        src = f'<a class="btn" href="{e(s["source_url"])}">Read the full story at {e(s["source_name"])} →</a>' if s.get("source_url") else ""
        _x = next((x for x in EXPLAINERS if x["slug"] == s.get("explainer")), None)
        _xbox = f'<a class="xbox" href="/explainer/{_x["slug"]}.html"><span class="kicker">Background · Explainer</span><b>{e(_x["title"])} →</b></a>' if _x else ""
        body = (f'<article class="story"><span class="kicker">{"Ask the Bulletin · " if s.get("ask") else ""}{e(s["section"])}{" · Citywide" if s.get("citywide") else ""} · {e(d["display_date"])}</span><h1>{e(s["title"])}</h1>{img}'
                f'<div class="body">{paras(s.get("body"))}</div>{_xbox}' + (f'<p class="corr"><strong>{"Update" if s.get("correction_type") == "update" else "Correction"}:</strong> {e(s["correction"])}</p>' if s.get("correction") else "") + f'{gallery_html(s)}{links_html(s)}{src}<section class="more side"><h2>More from Bay View today</h2>{others}</section></article>')
        (OUT / s["url"].lstrip("/")).write_text(shell(s["title"] + " · The Bay View Bulletin", body, d, "", {"title": s["title"], "desc": dek(s), "image": abs_url((s.get("image") or {}).get("src")), "type": "article"}, s["url"], story_ld(s, d)))

    # utilities
    rise, sset = sunrise_sunset(day)
    today_events = [ev for ev in d["events"] if ev["day"].startswith("Today")]
    days_to_winter = (dt.date(day.year, 12, 1) - day).days
    U = d.get("utilities", {})
    def ut(key, label, fallback_v, fallback_s, href=""):
        x = U.get(key) or {}
        return (label, x.get("v") or fallback_v, x.get("s") or fallback_s, x.get("class", ""), x.get("href") or href)
    # Nov. 17 (Ben): four tiles. "Today" was dropped (events are already on the page) and Parking folded into the street tile.
    winter = (f"Winter parking rules in {days_to_winter} days" if days_to_winter > 0 else "Winter parking rules in effect", "Dec. 1 to March 1")
    st = U.get("pickup") or {}
    utils = [
        ut("weather", "Weather", "Today's forecast →", "National Weather Service", "https://forecast.weather.gov/MapClick.php?lat=42.99&lon=-87.89"),
        ("Streets & parking", st.get("v") or winter[0], st.get("s") or winter[1], st.get("class", "warm" if 0 < days_to_winter <= 7 else ""), st.get("href") or "https://city.milwaukee.gov/mpw/parking/meter"),
        ut("schools", "Schools", *schools_tile(day), "/schools.html"),
        ("Sun over the lake", f"↑ {rise} · ↓ {sset}", "Bay View shoreline", "", ""),
    ]
    _w = list(utils[0])
    if re.match(r"^-?\d+°", str(_w[1])):
        _w[1] = "Now " + _w[1]
        if _w[2] and not str(_w[2]).lower().startswith(("today", "tonight")):
            _w[2] = "Today: " + _w[2][0].lower() + _w[2][1:]
    utils[0] = tuple(_w)
    util_html = "".join((f'<a class="util {c}" href="{e(h)}">' if h else f'<div class="util {c}">') + f'<span class="k">{k}</span><span class="v">{e(v)}</span><span class="s">{e(s_)}</span>' + ("</a>" if h else "</div>") for k, v, s_, c, h in utils)
    tick = [s for s in stories if s["key"] == "openings"] or []
    # Headline ticker: the day's most important news, in story order (top section first), each linking to its story.

    tops = [s for s in rest if s["key"] == "top"]; side_items = (tops + [s for s in rest if s["key"] not in ("top", "spotlight")])[:max(3, len(tops))]
    side = "".join(f'<a href="{s["url"]}"><span class="kicker">{e(s["section"])}</span><h3>{e(s["title"])}</h3><p>{e(dek(s))}</p></a>' for s in side_items)
    # Nov. 25 (Ben): on thin days the right column fills with a Buzz item and today's events instead of sitting empty.
    tease_buzz = next((b for b in buzz if b is not lead_buzz), None)
    _fill = 3 - len(side_items)
    if _fill > 0:
        for b in [b for b in buzz if b is not lead_buzz and b is not tease_buzz][:1]:
            side += f'<a href="/buzz.html"><span class="kicker">The Buzz · {e(b["kicker"])}</span><h3>{e(b["headline"])}</h3><p>{e(dek({"body": b["body"].strip()}))}</p></a>'
            _fill -= 1
        _eve = sorted([ev for ev in today_events if not (lead.get("key") == "alt" and ev["title"] == lead["title"])],
                      key=lambda ev: not re.search(r"\b([5-9]|1[01])(:\d\d)?(-\d+)?\s*(pm|p\.m\.)", ev["when"], re.I))
        for ev in _eve[:max(0, _fill)]:
            side += f'<a href="/events.html#today"><span class="kicker">Today · {e(ev["when"])}</span><h3>{e(ev["title"])}</h3><p>{e(ev["where"].split(",")[0])}' + (f' · {e(ev["desc"])}' if ev.get("desc") else "") + '</p></a>'
    lead_img = f'<figure><img src="{e(lead["image"]["src"])}" alt="{e(lead["image"]["alt"])}"><div class="cap">{cap_label(lead["image"])}{e(lead["image"]["credit"])}</div></figure>' if lead.get("image") else ""
    # Nov. 17: a crime or safety lead gets a smaller photo, so the front page doesn't open on a grim full-width image.
    lead_cls = "lead textlead" if (lead["key"] == "safety" or "safety" in (lead.get("also") or []) or lead.get("tag") == "Safety") else "lead"
    # "Bay View in 60 seconds": the day's "briefing" bullets, or an automatic version.
    brief_items = d.get("briefing") or []
    if not brief_items:
        w = (U.get("weather") or {})
        if w.get("v"):
            brief_items.append({"text": f'Weather: {w["v"]}' + (f', {w["s"]}' if w.get("s") else "") + "."})
        brief_items.append({"text": "Top story: " + lead["title"] + ".", "url": lead["url"]})
        eve = [ev for ev in today_events if re.search(r"\b([5-9]|1[01])(:\d\d)?\s*(pm|p\.m\.)", ev["when"], re.I)] or today_events
        if eve:
            _n = len(today_events)
            brief_items.append({"text": (f'Today: {_n} things to do, including {eve[0]["title"]} at {eve[0]["where"].split(",")[0]} ({eve[0]["when"]}).' if _n > 1
                                         else f'Today: {eve[0]["title"]} at {eve[0]["where"].split(",")[0]} ({eve[0]["when"]}).'), "url": "/events.html#today"})
        if buzz:
            brief_items.append({"text": "Buzz: " + buzz[0]["headline"] + ".", "url": "/buzz.html"})
        sp_ = next((x for x in stories if x["key"] == "spotlight"), None)
        if sp_:
            brief_items.append({"text": "Spotlight: " + sp_["title"].replace("Spotlight: ", "") + ". " + dek(sp_).rstrip(".") + ".", "url": "/spotlight.html"})
    brief_html = ('<section class="brief" aria-label="Bay View in 60 seconds"><h2>Bay View in 60 seconds</h2><ul>'
                  + "".join(f'<li>{("<a href=" + chr(34) + e(b["url"]) + chr(34) + ">" + e(b["text"]) + "</a>") if b.get("url") else e(b["text"])}</li>' for b in brief_items[:5]) + "</ul></section>") if brief_items else ""
    # This weekend: up to 6 weekend events (not today's), mixing types, photos first.
    wk = [ev for ev in d["events"] if "weekend" in ev_when_tags(ev_date(ev, day), day) and not ev["day"].startswith("Today")]
    pick, seen = [], set()
    for ev in sorted(wk, key=lambda x: (not x.get("image"),)):
        if ev["kind"] not in seen:
            pick.append(ev); seen.add(ev["kind"])
    for ev in wk:
        if len(pick) >= 6: break
        if ev not in pick: pick.append(ev)
    pick = sorted(pick[:6], key=lambda x: d["events"].index(x))
    wk_label = "This weekend in Bay View" if day.weekday() >= 4 else "Coming up this weekend"
    wk_chips = "".join(f'<a class="chip" href="/events.html#weekend">{ev_thumb(ev, day)}<span class="in"><span class="d">{e(ev["day"].replace("Today, ", ""))}</span><span class="t">{e(ev["when"])}</span><span class="n">{e(ev["title"])}</span><span class="w">{e(ev["where"].split(",")[0].split(" · ")[0])}</span></span></a>' for ev in pick)
    weekend_html = f'<section class="tonight weekend"><h2><span>{wk_label}</span><a href="/weekend.html">The weekend guide →</a></h2><div class="chips">{wk_chips}</div></section>' if pick else ""
    # Earlier this week: on thin days (fewer than 6 news stories), recent stories from the previous 3 days.
    earlier_html = ""
    if len(news) < 6:
        prev = [x for x in reversed(ALL_STORIES) if x["issue_date"] < d["date"] and x["issue_date"] >= (day - dt.timedelta(days=3)).isoformat() and x["key"] != "spotlight"]
        if prev:
            earlier_html = ('<section class="topic"><h2>Earlier this week<a href="/archive.html">Archive →</a></h2>'
                            + "".join(f'<a class="row noimg" href="{x["url"]}"><div><span class="kicker">{e(x["section"])} · {e(x["display_date"].split(",")[0])}</span><h3>{e(x["title"])}</h3><p>{e(dek(x))}</p></div></a>' for x in prev[:4]) + "</section>")
    chips = "".join(f'<a class="chip" href="/events.html#today">{ev_thumb(ev, day)}<span class="in"><span class="t">{e(ev["when"])}</span><span class="n">{e(ev["title"])}</span><span class="w">{e(ev["where"].split(",")[0].split(" · ")[0])}</span></span></a>' for ev in today_events)

    def row(s, kicker=True):
        img = f'<img src="{e(s["image"]["src"])}" alt="">' if s.get("image") else ""
        return f'<a class="row{"" if img else " noimg"}" href="{s["url"]}">{img}<div>{('<span class="kicker">' + e(s["section"]) + '</span>') if kicker else ""}<h3>{e(s["title"])}</h3><p>{e(dek(s))}</p><div class="meta">{e(srcmeta(s))}</div></div></a>'
    groups = {}
    for s_ in rest:
        if s_ in side_items:
            continue
        groups.setdefault(s_["section"], []).append(s_)
    if "Business spotlight" in groups:  # spotlight block comes first among the topic blocks
        groups = {"Business spotlight": groups.pop("Business spotlight"), **groups}
    topics = "".join(f'<section class="topic{" w" if sec in WARM else ""}"><h2>{e(sec)}<a href="{LABEL_PAGE.get(sec, "/section/" + slug(sec) + ".html")}">{"Read the spotlight →" if sec == "Business spotlight" else "More →"}</a></h2>{"".join(row(x, False) for x in xs[:3])}</section>' for sec, xs in groups.items())
    # Nov. 25: in-season guides get a tease under the lead; the openings tracker gets a strip of its latest entries.
    _in = [g for g in GUIDES if g.get("status") != "planned" and g.get("season") and g["season"]["start"] <= d["date"] <= g["season"]["end"]]
    guide_html = "".join(f'<a class="guidetease" href="/guide/{g["slug"]}.html"><span class="k">Guide</span><b>{e(g["title"])}</b><span class="go">{e(g.get("tease") or "Open the guide")} →</span></a>' for g in _in[:2])
    _oc = [o for o in sorted(OPENINGS, key=lambda o: o["date"], reverse=True) if o["date"] <= d["date"]][:3]
    _ocl = {"opened": "Opened", "closed": "Closed", "coming": "Coming", "seasonal": "Season over", "moved": "Moved", "renamed": "Renamed", "closing": "Closing"}
    oc_html = ('<section class="ocstrip"><h2><span>Opened &amp; closed</span><a href="/openings.html">The tracker →</a></h2><ul>'
               + "".join(f'<li><b class="{e(o["status"])}">{_ocl.get(o["status"], o["status"].title())}</b> {e(o["name"])}<span> · {e(o.get("note", ""))}</span></li>' for o in _oc)
               + '</ul></section>') if _oc else ""
    # Nov. 25: "On the market" homepage block: new listings (last 7 days), this week's open houses, then price cuts
    _items = LISTINGS.get("items", [])
    def _age(it):
        return (dt.date.fromisoformat(d["date"]) - dt.date.fromisoformat(it.get("first_seen", d["date"]))).days
    _wk = (dt.date.fromisoformat(d["date"]) + dt.timedelta(days=7)).isoformat()
    _oh = [it for it in _items if it.get("status") not in ("sold", "off_market") and any(d["date"] <= o.get("date", "") <= _wk for o in it.get("open_house") or [])]
    _new = [it for it in _items if it.get("status") in ("active", "new", "price_cut") and 0 <= _age(it) <= 7 and it not in _oh]
    _cut = [it for it in _items if it.get("status") == "price_cut" and it not in _oh + _new]
    _show = (sorted(_oh, key=lambda it: min(o["date"] for o in it["open_house"])) + sorted(_new, key=_age) + _cut)[:4]
    _n_active = sum(1 for it in _items if it.get("status") in ("active", "new", "price_cut") and it.get("kind") != "commercial")
    _n_comm = sum(1 for it in _items if it.get("status") in ("active", "new", "price_cut") and it.get("kind") == "commercial")
    re_html = (f'<section class="onmkt"><h2><span>On the market</span><a href="/real-estate.html">All Bay View listings →</a></h2>'
               f'<div class="rgrid">{"".join(re_card(it, d["date"], True) for it in _show)}</div>'
               f'<p class="rsum">{_n_active} home{"s" if _n_active != 1 else ""} for sale and {_n_comm} commercial space{"s" if _n_comm != 1 else ""} on our list. Listings link to the listing agent or broker. <a href="/submit-listing.html">Agents: submit a listing</a>.</p></section>') if _show else ""
    mke = d.get("milwaukee", [])
    h = d.get("history")
    hurl = history_page(d) if h else ""
    hist = (f'<section class="block"><h2>Bay View history<a href="/history.html" style="float:right;font:600 14px var(--sans);color:var(--lake)">All history →</a></h2><div class="hist"><div><a href="{hurl}"><img src="{e(h["image"]["src"])}" alt="{e(h["image"]["alt"])}"></a><div class="cap">{e(h["image"]["credit"])}</div></div>'
            f'<div><div class="yr">{e(h["year"])}</div>' + (f'<h3 style="font:700 21px/1.25 var(--serif);margin:2px 0 6px"><a href="{hurl}" style="color:inherit">{e(h["title"])}</a></h3>' if h.get("title") else "")
            + f'<p>{e(h["text"])}</p><a class="kicker" href="{hurl}">Read the story →</a></div></div></section>') if h else ""
    home = (f'<div class="utils">{util_html}</div>{brief_html}'
            f'<section class="front"><a class="{lead_cls}" href="{lead["url"]}">{lead_img}<span class="kicker">{e(lead["section"])}</span><h2>{e(lead["title"])}</h2><p>{e(dek(lead))}</p><div class="meta">{e(lead.get("meta") or srcmeta(lead))}</div></a>'
            f'<div class="side">{side}</div></section>'
            f'{guide_html}'
            f'<section class="tonight"><h2><span>Today in Bay View</span><a href="/events.html">All events →</a></h2><div class="chips">{chips}</div></section>'
            + (f'<a class="bztease" href="/buzz.html"><span class="bzlogo">The Bay View <span>Buzz</span></span>'
               f'<span class="bzk">{e(tease_buzz["kicker"])}</span><span class="bzh">{e(tease_buzz["headline"])}</span><span class="bzgo">Read the Buzz →</span></a>' if tease_buzz else "") +
            f'{weekend_html}{re_html}{oc_html}<div class="topics">{topics}{earlier_html}</div>'
            f'{hist}')
    (OUT / "issues").mkdir(exist_ok=True)
    (OUT / "issues" / f'{d["date"]}.html').write_text(shell("The Bay View Bulletin · " + d["display_date"], home, d))
    if not newest:
        return
    (OUT / "index.html").write_text(shell("The Bay View Bulletin · Bay View's morning paper", home, d, "Home", {"title": "The Bay View Bulletin · " + d["display_date"], "desc": lead["title"]}, "/"))

    # events
    cal, cur = [], None
    (OUT / "ics").mkdir(exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    all_vevents = []
    for ev in d["events"]:
        _id, _vev, _g = ev_ics(ev, day, stamp)
        all_vevents.append(_vev)
        (OUT / "ics" / f"{_id}.ics").write_text(ics_wrap(_vev, ev["title"]))
        ev = dict(ev, _ics=f"/ics/{_id}.ics", _g=_g)
        if ev["day"] != cur:
            cur = ev["day"]
            cal.append(f'<div class="cal-day" data-day="{e(cur)}">{e(cur)}</div>')
        _dd = ev_date(ev, day)
        cal.append(f'<div class="ev" data-day="{e(ev["day"])}" data-kind="{e(ev["kind"])}" data-when="{ev_when_tags(_dd, day)}" data-free="{1 if ev_free(ev) else 0}">{ev_thumb(ev, day)}<span class="t">{e(ev["when"])}</span><div><a href="{e(ev["link"])}" class="n">{e(ev["title"])}</a><div class="w">{e(ev["where"])}</div>{('<div class="d">' + e(ev["desc"]) + '</div>') if ev.get("desc") else ""}<div class="evcal">Add to calendar: <a href="{ev["_ics"]}" download>Apple / Outlook</a> · <a href="{e(ev["_g"])}">Google</a></div></div><span class="pill">{e(ev["kind"])}</span></div>')
    (OUT / "events.ics").write_text(ics_wrap("".join(all_vevents)))
    kinds = sorted({ev["kind"] for ev in d["events"]})
    whens = [("", "Any day"), ("today", "Today"), ("tomorrow", "Tomorrow"), ("weekend", "This weekend"), ("week", "Next 7 days")]
    filt = ('<div class="filters when" role="group" aria-label="Filter events by date">'
            + "".join(f'<button type="button" data-w="{w}"{" class=on" if not w else ""} aria-pressed="{"true" if not w else "false"}">{lab}</button>' for w, lab in whens)
            + '<button type="button" class="free" data-free="1" aria-pressed="false">Free only</button></div>'
            '<div class="filters kinds" role="group" aria-label="Filter events by type"><button type="button" class="on" data-k="" aria-pressed="true">All types</button>'
            + "".join(f'<button type="button" data-k="{e(k)}" aria-pressed="false">{e(k)}</button>' for k in kinds) + "</div>")
    filt_js = """<p class="pagedek" id="evnone" hidden>No events match. Try another day or type.</p><script>
(function(){var kb=[].slice.call(document.querySelectorAll('.filters.kinds button')),wb=[].slice.call(document.querySelectorAll('.filters.when button[data-w]')),fb=document.querySelector('.filters.when .free'),
evs=[].slice.call(document.querySelectorAll('.ev[data-kind]')),days=[].slice.call(document.querySelectorAll('.cal-day')),S={k:'',w:'',f:false};
function press(list,attr,val){list.forEach(function(b){var on=b.dataset[attr]===val;b.classList.toggle('on',on);b.setAttribute('aria-pressed',on)})}
function apply(){press(kb,'k',S.k);press(wb,'w',S.w);fb.classList.toggle('on',S.f);fb.setAttribute('aria-pressed',S.f);
var n=0;evs.forEach(function(x){var v=(!S.k||x.dataset.kind===S.k)&&(!S.w||(' '+x.dataset.when+' ').indexOf(' '+S.w+' ')>=0)&&(!S.f||x.dataset.free==='1');x.hidden=!v;if(v)n++});
days.forEach(function(h){h.hidden=!evs.some(function(x){return !x.hidden&&x.dataset.day===h.dataset.day})});
document.getElementById('evnone').hidden=n>0;
var parts=[];if(S.w)parts.push(S.w);if(S.k)parts.push(encodeURIComponent(S.k));if(S.f)parts.push('free');
try{history.replaceState(null,'',parts.length?'#'+parts.join('/'):location.pathname)}catch(e){}}
kb.forEach(function(b){b.addEventListener('click',function(){S.k=b.dataset.k;apply()})});
wb.forEach(function(b){b.addEventListener('click',function(){S.w=b.dataset.w;apply()})});
fb.addEventListener('click',function(){S.f=!S.f;apply()});
function fromHash(){S={k:'',w:'',f:false};decodeURIComponent(location.hash.slice(1)).split('/').forEach(function(p){if(!p)return;if(p==='free')S.f=true;else if(wb.some(function(b){return b.dataset.w===p}))S.w=p;else if(kb.some(function(b){return b.dataset.k===p}))S.k=p});apply()}
window.addEventListener('hashchange',fromHash);if(location.hash)fromHash();})();
</script>"""
    (OUT / "events.html").write_text(shell("Events · The Bay View Bulletin", f'<h1 class="pagehead">Events in Bay View</h1><p class="pagedek">Shows, family time, markets and meetings, today and ahead. <a href="/weekend.html" style="color:var(--lake);font-weight:600">This weekend&rsquo;s guide</a> · <a href="webcal://bayviewbulletin.com/events.ics" style="color:var(--lake);font-weight:600">Subscribe to this calendar</a> (or add <a href="/events.ics" style="color:var(--lake)">bayviewbulletin.com/events.ics</a> to Google Calendar under "From URL").</p>{filt}{"".join(cal)}{filt_js}', d, "Events", None, "/events.html", events_ld(d["events"], day)))

    # milwaukee
    # The Milwaukee section was retired Nov. 12, 2026 (citywide news that affects Bay View now runs in the topic blocks).
    (OUT / "milwaukee.html").write_text('<!DOCTYPE html><meta charset="utf-8"><title>The Bay View Bulletin</title><link rel="canonical" href="/"><meta http-equiv="refresh" content="0; url=/"><a href="/">The Bay View Bulletin</a>')


SECTION_PAGES = {"food": ("Food & Drink", {"Food & Drink", "Fish fry"}), "city": ("City Hall", {"City Hall", "Streets"}),
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
    xf = ROOT / "content/explainers.json"
    EXPLAINERS[:] = json.loads(xf.read_text()) if xf.exists() else []
    gf, of = ROOT / "content/guides.json", ROOT / "content/openings.json"
    GUIDES[:] = json.loads(gf.read_text()) if gf.exists() else []
    OPENINGS[:] = json.loads(of.read_text()) if of.exists() else []
    lf = ROOT / "content/listings.json"
    LISTINGS.clear()
    LISTINGS.update(json.loads(lf.read_text()) if lf.exists() else {})
    files = sorted((ROOT / "content/issues").glob("*.json"))
    issues = [json.loads(f.read_text()) for f in files]
    global TICKER
    TICKER = make_ticker(issues[-1])
    for i, d in enumerate(issues):
        build_one(d, i == len(issues) - 1)
    d = issues[-1]
    recent = [s for s in reversed(ALL_STORIES)][:400]

    def listing(items):
        return '<div class="list">' + "".join(f'<a href="{s["url"]}"><span class="kicker">{e(s["section"])} · {e(s["display_date"])}</span><h3>{e(s["title"])}</h3><p>{e(dek(s))}</p></a>' for s in items) + "</div>"
    labels = sorted({s["section"] for s in recent})
    for lab in labels:
        items = [s for s in recent if s["section"] == lab]
        if lab in LABEL_PAGE and LABEL_PAGE[lab] != f"/section/{slug(lab)}.html":
            (OUT / "section" / f"{slug(lab)}.html").write_text(redirect_page(LABEL_PAGE[lab]))  # Nov. 25: one page per menu section
            continue
        (OUT / "section" / f"{slug(lab)}.html").write_text(shell(lab + " · The Bay View Bulletin", f'<h1 class="pagehead">{e(lab)}</h1><p class="pagedek">Recent {e(lab.lower())} news from Bay View.</p>' + (listing(items) or "<p>Nothing yet.</p>"), d, LABEL_ACTIVE.get(lab, "More"), None, f"/section/{slug(lab)}.html"))
    # Nov. 25: "City Hall this week" (Mondays) is pinned at the top of the City Hall page until the next one.
    _chw = next((x for x in reversed(ALL_STORIES) if x.get("weekly") == "cityhall"), None)
    chw_box = (f'<a class="chw" href="{_chw["url"]}"><span class="kicker">City Hall this week · {e(_chw["display_date"])}</span><h3>{e(_chw["title"])}</h3><p>{e(dek(_chw))}</p></a>') if _chw else ""
    for key, (title, labs) in SECTION_PAGES.items():
        onpage = lambda s: labs is None or s["section"] in labs or key in (s.get("also") or [])
        items = [s for s in recent if onpage(s)]
        active = {"food": "Food & Drink", "city": "City Hall", "safety": "Safety", "more": "More"}[key]
        briefs = [b for b in BRIEFS if labs is None or b["label"] in labs]
        empty = f'<p class="pagedek">No new {e(title.lower())} news in the last day. New stories land here every morning.</p>'
        # Featured: the most important story from the newest day (story order = importance), preferring one with a photo;
        # if this section had no stories, the newest earlier headline.
        feat = None
        if labs is not None and items:
            newest = max(s["issue_date"] for s in items)
            day_items = [s for s in ALL_STORIES if s["issue_date"] == newest and onpage(s)]
            feat = next((s for s in day_items if s.get("image")), day_items[0] if day_items else None)
            if feat:
                items = [s for s in items if s["url"] != feat["url"]]
                body_feat = feature_html(feat["url"], feat.get("image"), f'{feat["section"]} · {feat["display_date"]}', feat["title"], dek(feat), srcmeta(feat), internal=True)
        elif labs is not None and briefs:
            feat = next((b for b in briefs if b.get("image")), briefs[0])
            briefs = [b for b in briefs if b is not feat]
            body_feat = feature_html(feat["source_url"], feat.get("image"), f'{feat["label"]} · {feat["date"]}', feat["title"], "", feat["source_name"], internal=False)
        body = f'<h1 class="pagehead">{e(title)}</h1>' + ('<p class="pagedek"><a href="/history.html" style="color:var(--lake);font-weight:600">Bay View history →</a> · <a href="/schools.html" style="color:var(--lake);font-weight:600">School days off →</a> · <a href="/directory.html" style="color:var(--lake);font-weight:600">Business directory →</a> · <a href="/explainers.html" style="color:var(--lake);font-weight:600">Explainers →</a> · <a href="/ask.html" style="color:var(--lake);font-weight:600">Ask the Bulletin →</a> · <a href="/weekend.html" style="color:var(--lake);font-weight:600">This weekend →</a> · <a href="/openings.html" style="color:var(--lake);font-weight:600">Opened &amp; closed →</a> · <a href="/guides.html" style="color:var(--lake);font-weight:600">Seasonal guides →</a></p>' if key == "more" else "") + ('<p class="pagedek"><a href="/explainers.html" style="color:var(--lake);font-weight:600">How City Hall works: explainers →</a> · <a href="/openings.html" style="color:var(--lake);font-weight:600">Opened &amp; closed →</a></p>' + chw_box if key == "city" else "") + (body_feat if feat else "") + (listing(items) if items else ("" if feat else empty))
        if feat and not [s for s in recent if onpage(s)]:
            body = body.replace(body_feat, f'<p class="pagedek">No new {e(title.lower())} news in the last day. Here&rsquo;s the latest:</p>' + body_feat)
        if briefs:
            body += '<h2 class="kicker" style="margin:32px 0 6px;font-size:13px;color:var(--muted)">Earlier this fall</h2><div class="list">' + "".join(
                f'<a href="{e(b["source_url"])}" rel="noopener"><span class="kicker">{e(b["label"])} · {e(b["date"])} · {e(b["source_name"])}</span><h3>{e(b["title"])}</h3></a>' for b in briefs) + "</div>"
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
    corr_items = [x for x in reversed(ALL_STORIES) if x.get("correction")]
    corr_list = "".join(f'<a href="{x["url"]}"><span class="kicker">{e(x["display_date"])}</span><h3>{e(x["title"])}</h3><p>{e(x["correction"])}</p></a>' for x in corr_items)
    (OUT / "corrections.html").write_text(shell("Corrections · The Bay View Bulletin",
        f'<h1 class="pagehead">Corrections</h1><p class="pagedek">When we get something wrong, we fix it on the story and note what changed. Every correction is listed here, newest first. Spot a mistake? <a href="{TIPS}" style="color:var(--lake)">Tell us</a>.</p>'
        + (f'<div class="list">{corr_list}</div>' if corr_list else '<p class="pagedek">No corrections so far.</p>'), d, "", None, "/corrections.html"))
    about = f"""<article class="story"><h1>Bay View's morning paper</h1><div class="body">
<p>The Bay View Bulletin is a free daily guide to what's happening in Milwaukee's Bay View neighborhood, updated every morning by 6:30. It's a neighborhood project, not a company: no ads, no paywall and no paid placements.</p>
<h2>Who's behind it</h2>
<p>The Bulletin is an independent project run by a Bay View resident who serves as its editor: setting what we cover and how, deciding anything sensitive, and answering for every mistake. The easiest way to reach the editor is the tip form below.</p>
<h2>How it's made</h2>
<p>We don't have reporters at meetings or crime scenes. Each morning's edition is put together with the help of AI tools, which follow the editor's written rules. They read local news outlets, city and school sources, elected officials' announcements, public records, and the public social media posts of Bay View businesses and neighbors. Then they summarize what's new in our own words, link every item to its original source and credit every photo. Anything sensitive, uncertain or that could hurt someone is held back for the editor to review before it runs. If something here matters to you, follow the link and read the original reporting, and please support the outlets that do that work.</p>
<h2>Where we cover</h2>
<p>Bay View as neighbors know it, from the harbor and Jones Island south to Holt and Morgan avenues, and from I-43 east to Lake Michigan. Citywide news runs only when it directly affects Bay View.</p>
<h2>Our standards</h2>
<p>We run news from the last 24 hours plus what's coming up, and we don't repeat stories. Safety coverage sticks to notable incidents, and we never name private individuals. Protests and rallies are listed neutrally, for any cause. Elected officials are covered for what they do for Bay View, never for campaigns. The daily business spotlight is never paid for and is limited to independent, locally owned businesses. The Bay View Buzz rounds up public posts and labels rumors as unconfirmed.</p>
<h2>Corrections</h2>
<p>If we get something wrong, we fix it on the story with a note saying what changed, and list it on our <a href="/corrections.html">corrections page</a>. Photos come from the original source or free-licensed collections, always credited. If you own a photo and want it removed, tell us and it comes down.</p>
<p>Follow the Bulletin on <a href="{IG_URL}">Instagram (@bayviewbulletin)</a> and <a href="{FB_URL}">Facebook</a> for the day's top stories every morning.</p>
<p><a class="btn" href="{TIPS}">Send a tip or a correction</a></p></div></article>"""
    # Nov. 17: the Buzz page shows the last 7 days; every day also gets its own archive page at /buzz/<date>.html.
    (OUT / "buzz").mkdir(exist_ok=True)
    bz_days = [(dd, items) for dd, items in reversed(ALL_BUZZ) if items]
    cutoff = (dt.date.fromisoformat(d["date"]) - dt.timedelta(days=6)).isoformat()
    def bz_section(dd, items):
        return f'<h2 class="bzday"><a href="/buzz/{dd["date"]}.html" style="color:inherit">{e(dd["display_date"])}</a></h2><div class="bzgrid">{"".join(buzz_card(b) for b in items)}</div>'
    def bz_page(inner, extra=""):
        return (f'<section class="buzz page"><header><h2>The Bay View <span>Buzz</span></h2><p>What the neighborhood is posting about</p></header>{inner}{extra}'
                f'<p class="bznote">{BUZZ_NOTE.replace("{TIPS}", TIPS)}</p></section>')
    older = [(dd, items) for dd, items in bz_days if dd["date"] < cutoff]
    arch_links = ('<div class="bzarch"><h3>Earlier Buzz</h3><p>' + " · ".join(f'<a href="/buzz/{dd["date"]}.html">{e(dd["display_date"].split(",", 1)[1].strip() if "," in dd["display_date"] else dd["display_date"])}</a>' for dd, _ in older) + "</p></div>") if older else ""
    bz_html = "".join(bz_section(dd, items) for dd, items in bz_days if dd["date"] >= cutoff)
    for k, (dd, items) in enumerate(bz_days):
        nav_ = []
        if k + 1 < len(bz_days): nav_.append(f'<a href="/buzz/{bz_days[k + 1][0]["date"]}.html">← {e(bz_days[k + 1][0]["display_date"])}</a>')
        nav_.append('<a href="/buzz.html">Latest Buzz</a>')
        if k > 0: nav_.append(f'<a href="/buzz/{bz_days[k - 1][0]["date"]}.html">{e(bz_days[k - 1][0]["display_date"])} →</a>')
        (OUT / "buzz" / f'{dd["date"]}.html').write_text(shell(f'The Bay View Buzz, {dd["display_date"]} · The Bay View Bulletin',
            bz_page(bz_section(dd, items), '<p class="bzarch">' + " · ".join(nav_) + "</p>"), d, "Buzz", {"title": "The Bay View Buzz · " + dd["display_date"], "desc": items[0]["headline"]}))
    (OUT / "buzz.html").write_text(shell("The Bay View Buzz · The Bay View Bulletin",
        bz_page(bz_html or "<p>Quiet out there. Check back tomorrow.</p>", arch_links), d, "Buzz"))
    spots = [x for x in reversed(ALL_STORIES) if x["key"] == "spotlight"]
    if spots:
        cur, past = spots[0], spots[1:]
        img = cur.get("image") or {}
        sp = (f'<h1 class="pagehead">Business spotlight</h1><p class="pagedek">Every day we feature one independent, locally owned Bay View business.</p>'
              f'<article class="story" style="margin-top:8px"><span class="kicker">{e(cur["display_date"])}</span><h1>{e(cur["title"].replace("Spotlight: ", ""))}</h1>'
              f'<p class="dek" style="font:20px/1.45 var(--serif);color:var(--muted);margin:0 0 12px">{e(cur.get("dek", ""))}</p>'
              + (f'<figure><img src="{e(img["src"])}" alt="{e(img.get("alt", ""))}"><div class="cap">Photo: <a href="{e(img.get("credit_url") or "#")}">{e(img.get("credit", ""))}</a></div></figure>' if img else "")
              + f'<div class="body">{paras(cur.get("body"))}</div>{gallery_html(cur)}{links_html(cur)}</article>')
        if past:
            sp += '<h2 class="kicker" style="margin:36px 0 12px">Past spotlights</h2><div class="spot-past">' + "".join(
                f'<a href="{x["url"]}">' + (f'<img src="{e(x["image"]["src"])}" alt="" loading="lazy">' if x.get("image") else "")
                + f'<span class="kicker">{e(x["display_date"])}</span><h3>{e(x["title"].replace("Spotlight: ", ""))}</h3></a>' for x in past) + "</div>"
    else:
        sp = '<h1 class="pagehead">Business spotlight</h1><p class="pagedek">The first spotlight lands tomorrow morning.</p>'
    (OUT / "spotlight.html").write_text(shell("Business spotlight · The Bay View Bulletin", sp, d, "Spotlight"))
    hist_items = "".join(f'<a href="{x["url"]}">' + (f'<img src="{e(x["image"]["src"])}" alt="" loading="lazy" style="float:right;width:120px;height:90px;object-fit:cover;margin:0 0 8px 14px">' if x.get("image") else "")
                         + f'<span class="kicker">{e(x.get("year"))} · Posted {e(x["display_date"])}</span><h3>{e(x["title"])}</h3><p>{e(x.get("text", ""))}</p><div style="clear:both"></div></a>' for x in reversed(ALL_HISTORY))
    (OUT / "history.html").write_text(shell("Bay View history · The Bay View Bulletin",
        f'<h1 class="pagehead">Bay View history</h1><p class="pagedek">One story from Bay View&rsquo;s past every day: the shops, taverns, factories, people and places that made the neighborhood. Newest first.</p><div class="list">{hist_items or "<p>The first history story lands tomorrow morning.</p>"}</div>', d, "History", None, "/history.html"))
    (OUT / "schools.html").write_text(shell("School days off · The Bay View Bulletin", schools_page(d), d, ""))
    (OUT / "about.html").write_text(shell("About · The Bay View Bulletin", about, d, ""))
    # search index + page
    idx = [{"t": s["title"], "d": dek(s), "u": s["url"], "k": s["section"], "dt": s["display_date"]} for s in recent]
    idx += [{"t": x["title"], "d": x.get("text", ""), "u": x["url"], "k": "History", "dt": str(x.get("year", ""))} for x in reversed(ALL_HISTORY)]
    idx += [{"t": x["title"], "d": x.get("dek", ""), "u": f'/explainer/{x["slug"]}.html', "k": "Explainer", "dt": x["updated"]} for x in EXPLAINERS]
    idx += [{"t": g["title"], "d": g.get("dek", ""), "u": f'/guide/{g["slug"]}.html', "k": "Guide", "dt": g["updated"]} for g in GUIDES if g.get("status") != "planned"]
    idx += [{"t": it["address"], "d": f'{listing_facts(it)}. {it.get("note", "")}', "u": "/real-estate.html", "k": "Real estate", "dt": it.get("first_seen", "")} for it in LISTINGS.get("items", []) if it.get("status") not in ("off_market",)]
    idx += [{"t": b["name"], "d": b["type"] + " · " + b["address"], "u": "/directory.html", "k": "Directory", "dt": ""} for b in dirs]
    idx += [{"t": ev["title"], "d": ev["when"] + " · " + ev["where"], "u": "/events.html", "k": "Event", "dt": ev["day"]} for ev in d["events"]]
    (OUT / "search.json").write_text(json.dumps(idx, ensure_ascii=False))
    search = f"""<h1 class="pagehead">Search</h1><p class="pagedek">Stories, events and Bay View businesses.</p>
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
    # Ben, Nov. 12: the map is no longer a feature of the site; old links go to the front page.
    (OUT / "map.html").write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=/"><link rel="canonical" href="/"><title>The Bay View Bulletin</title><a href="/">The Bay View Bulletin</a>')
    # Nov. 25: seasonal guides (content/guides.json) and the openings-and-closings tracker (content/openings.json).
    (OUT / "guide").mkdir(exist_ok=True)
    live_guides = [g for g in GUIDES if g.get("status") != "planned"]
    for g in live_guides:
        secs = ""
        for sec in g.get("sections", []):
            its = "".join(f'<div class="gitem"><h3>' + (f'<a href="{e(it["url"])}">{e(it["name"])}</a>' if it.get("url") else e(it["name"])) + '</h3>'
                          + (f'<div class="gwhen">{e(it["when"])}' + (f' · {e(it["where"])}' if it.get("where") else "") + '</div>' if it.get("when") or it.get("where") else "")
                          + f'<p>{e(it.get("text", ""))}</p>' + (f'<div class="meta">Source: <a href="{e(it["url"])}">{e(it["source"])}</a></div>' if it.get("source") and it.get("url") else "") + '</div>'
                          for it in sec.get("items", []))
            secs += f'<section class="gsec"><h2>{e(sec["heading"])}</h2>{("<p class=" + chr(34) + "pagedek" + chr(34) + ">" + e(sec["intro"]) + "</p>") if sec.get("intro") else ""}{its}</section>'
        img = g.get("image")
        pic = f'<figure><img src="{e(img["src"])}" alt="{e(img["alt"])}"><div class="cap">{cap_label(img)}<a href="{e(img.get("credit_url", "#"))}">{e(img["credit"])}</a></div></figure>' if img else ""
        gbody = (f'<article class="story guide"><span class="kicker">Guide · Updated {e(dt.date.fromisoformat(g["updated"]).strftime("%b. %-d, %Y"))}</span><h1>{e(g["title"])}</h1>{pic}'
                 f'<div class="body">{paras(g.get("intro"))}</div>{secs}<div class="body">{paras(g.get("outro"))}</div>'
                 f'<p class="pagedek" style="margin-top:22px">We update this guide as plans are announced. Know something we missed? <a href="{TIPS}" style="color:var(--lake)">Tell us</a>. <a href="/guides.html" style="color:var(--lake)">All guides →</a> · <a href="/events.html" style="color:var(--lake)">All events →</a></p></article>')
        (OUT / "guide" / f'{g["slug"]}.html').write_text(shell(g["title"] + " · The Bay View Bulletin", gbody, d, "", {"title": g["title"], "desc": g.get("dek", ""), "image": abs_url((img or {}).get("src"))}, f'/guide/{g["slug"]}.html'))
    gl = "".join(f'<a href="/guide/{g["slug"]}.html"><span class="kicker">{"In season · " if g.get("season") and g["season"]["start"] <= d["date"] <= g["season"]["end"] else ""}Updated {e(dt.date.fromisoformat(g["updated"]).strftime("%b. %-d, %Y"))}</span><h3>{e(g["title"])}</h3><p>{e(g.get("dek", ""))}</p></a>' for g in sorted(live_guides, key=lambda g: g["updated"], reverse=True))
    coming_g = [g for g in GUIDES if g.get("status") == "planned"]
    (OUT / "guides.html").write_text(shell("Seasonal guides · The Bay View Bulletin",
        '<h1 class="pagehead">Seasonal guides</h1><p class="pagedek">Where to go in Bay View this season, updated as plans are announced.</p>' + (f'<div class="list">{gl}</div>' if gl else "")
        + ('<p class="pagedek" style="margin-top:18px">Coming later: ' + " · ".join(f'{e(g["title"])} (by {e(dt.date.fromisoformat(g["publish_by"]).strftime("%B %-d"))})' for g in coming_g) + '</p>' if coming_g else ""), d, "", None, "/guides.html"))
    _ocl = {"opened": "Opened", "closed": "Closed", "coming": "Coming soon", "seasonal": "Closed for the season", "moved": "Moved", "renamed": "Renamed", "closing": "Closing soon"}
    def _ocrow(o):
        return (f'<div class="ocrow"><b class="{e(o["status"])}">{_ocl.get(o["status"], o["status"].title())}</b><div><h3>' + (f'<a href="{e(o["url"])}">{e(o["name"])}</a>' if o.get("url") else e(o["name"]))
                + f'</h3><div class="w">{e(o.get("address", ""))}' + (" · " if o.get("address") else "") + f'{e(dt.date.fromisoformat(o["date"]).strftime("%b. %-d, %Y"))}</div><p>{e(o.get("note", ""))}' + (f' <span class="src">({e(o["source"])})</span>' if o.get("source") else "") + '</p></div></div>')
    oc_sorted = sorted(OPENINGS, key=lambda o: o["date"], reverse=True)
    oc_groups = [("Coming soon", [o for o in oc_sorted if o["status"] in ("coming", "closing")]), ("Recently opened", [o for o in oc_sorted if o["status"] in ("opened", "moved", "renamed")]),
                 ("Recently closed", [o for o in oc_sorted if o["status"] in ("closed", "seasonal")])]
    ocbody = ('<h1 class="pagehead">Opened &amp; closed</h1><p class="pagedek">Bay View businesses that just opened, are on the way, or have closed, newest first. Every entry links to its source. '
              f'Spotted a new sign or an empty storefront? <a href="{TIPS}" style="color:var(--lake);font-weight:600">Send a tip</a>.</p>'
              + "".join(f'<h2 class="kicker" style="margin:26px 0 4px">{h}</h2>' + "".join(_ocrow(o) for o in xs) for h, xs in oc_groups if xs))
    (OUT / "openings.html").write_text(shell("Opened & closed · The Bay View Bulletin", ocbody, d, "", {"title": "Opened & closed in Bay View", "desc": "New Bay View businesses, what's coming soon, and what has closed."}, "/openings.html"))
    # Nov. 25: Real Estate page (menu item) from content/listings.json plus the "realestate" stories
    items = LISTINGS.get("items", [])
    live = [it for it in items if it.get("status") not in ("sold", "off_market")]
    today = d["date"]
    wk = (dt.date.fromisoformat(today) + dt.timedelta(days=7)).isoformat()
    ohs = sorted([it for it in live if any(today <= o.get("date", "") <= wk for o in it.get("open_house") or [])], key=lambda it: min(o["date"] for o in it["open_house"] if o.get("date", "") >= today))
    homes = sorted([it for it in live if it.get("kind") != "commercial"], key=lambda it: it.get("first_seen", ""), reverse=True)
    comm = sorted([it for it in live if it.get("kind") == "commercial"], key=lambda it: it.get("first_seen", ""), reverse=True)
    sold = sorted([it for it in items if it.get("status") == "sold"], key=lambda it: (it.get("sold") or {}).get("date", it.get("last_checked", "")), reverse=True)[:12]
    mk = LISTINGS.get("market")
    mk_html = (f'<div class="rmkt"><div><b>{e(mk["median_list"])}</b><span>median list price</span></div><div><b>{e(str(mk["homes_for_sale"]))}</b><span>homes for sale</span></div>'
               + (f'<div><b>{e(str(mk["median_days"]))}</b><span>median days on market</span></div>' if mk.get("median_days") else "")
               + f'<p>As of {e(mk["as_of"])}. Source: <a href="{e(mk["url"])}">{e(mk["source"])}</a></p></div>') if mk else ""
    re_stories = [x for x in reversed(ALL_STORIES) if x.get("section") == "Real estate"][:6]
    def grid(xs):
        return f'<div class="rgrid big">{"".join(re_card(it, today) for it in xs)}</div>'
    rebody = ('<h1 class="pagehead">Real estate</h1><p class="pagedek">Bay View homes and commercial spaces for sale and lease, open houses and notable sales. '
              'Each listing is in our own words and links to the listing agent or broker, who has the photos and details. '
              f'Agents and sellers: <a href="/submit-listing.html" style="color:var(--lake);font-weight:600">submit your Bay View listing</a>. Maps &copy; <a href="https://www.openstreetmap.org/copyright" style="color:var(--lake)">OpenStreetMap contributors</a>.</p>'
              + mk_html + re_bigmap(live)
              + (f'<h2 class="rsec">Open houses this week</h2>{grid(ohs)}' if ohs else "")
              + (f'<h2 class="rsec">Homes for sale <span>{len(homes)}</span></h2>{grid(homes)}' if homes else '<h2 class="rsec">Homes for sale</h2><p class="pagedek">New listings show up here as we confirm them.</p>')
              + (f'<h2 class="rsec">Commercial for sale and lease <span>{len(comm)}</span></h2>{grid(comm)}' if comm else "")
              + (f'<h2 class="rsec">Recently sold</h2><p class="pagedek">Notable sales from city property records: commercial buildings and properties with four or more units. Prices from records are estimates.</p>{grid(sold)}' if sold else "")
              + (f'<h2 class="rsec">Real estate news</h2>{listing(re_stories)}' if re_stories else ""))
    (OUT / "real-estate.html").write_text(shell("Real estate · The Bay View Bulletin", rebody, d, "Real Estate",
        {"title": "Bay View real estate", "desc": "Homes and commercial spaces for sale and lease in Bay View, open houses and notable sales."}, "/real-estate.html"))
    # Nov. 25: agents and sellers submit listings (photo rights granted on the form)
    sbody = ('<h1 class="pagehead">Submit your Bay View listing</h1><div class="askbox">'
             '<p>Listing a home, condo, duplex or commercial space in Bay View? Send it to us and we&rsquo;ll feature it on our <a href="/real-estate.html">Real Estate page</a>, on the homepage and in our Saturday &ldquo;On the market&rdquo; post on Facebook and Instagram. It&rsquo;s free.</p>'
             '<p><b>Include:</b> the address, price, beds and baths, square footage, open house dates and times, and a link to the listing. '
             'To include photos, attach them and choose the &ldquo;Yes&rdquo; photo option on the form: that confirms you own the photos or have the photographer&rsquo;s permission, and lets us use them with credit to you and your brokerage.</p>'
             '<p>We describe each listing in our own words, link to your listing page, and credit your brokerage. We check every submission against the listing before it runs, and we don&rsquo;t run listings outside Bay View (the harbor south to Holt and Morgan, I-43 east to the lake).</p>'
             f'<a class="btn" href="{LISTING}">Submit a listing</a></div>')
    (OUT / "submit-listing.html").write_text(shell("Submit your listing · The Bay View Bulletin", sbody, d, "Real Estate",
        {"title": "Submit your Bay View listing", "desc": "Agents and sellers: send The Bay View Bulletin your Bay View listing to be featured free."}, "/submit-listing.html"))
    # Nov. 17: evergreen explainers, the weekend guide and Ask the Bulletin.
    (OUT / "explainer").mkdir(exist_ok=True)
    for x in EXPLAINERS:
        img = x.get("image") or {}
        fig = (f'<figure><img src="{e(img["src"])}" alt="{e(img.get("alt", ""))}"><div class="cap">Photo: <a href="{e(img.get("credit_url") or "#")}">{e(img.get("credit", ""))}</a></div></figure>') if img else ""
        upd = dt.date.fromisoformat(x["updated"]).strftime("%B %-d, %Y")
        body = (f'<article class="story"><span class="kicker">Explainer · {e(x.get("topic", "Bay View"))} · Updated {e(upd)}</span><h1>{e(x["title"])}</h1>'
                f'<p class="dek" style="font:20px/1.45 var(--serif);color:var(--muted);margin:0 0 12px">{e(x.get("dek", ""))}</p>{fig}<div class="body">{paras(x["body"])}</div>{links_html(x)}'
                f'<p class="pagedek" style="margin-top:22px">Explainers are updated when the facts change. Something out of date? <a href="{TIPS}" style="color:var(--lake)">Tell us</a>. <a href="/explainers.html" style="color:var(--lake)">All explainers →</a></p></article>')
        xo = {"title": x["title"], "desc": x.get("dek", ""), "image": abs_url(img.get("src")) or SITE + "/og/city.png", "type": "article"}
        (OUT / "explainer" / f'{x["slug"]}.html').write_text(shell(x["title"] + " · Explainer · The Bay View Bulletin", body, d, "", xo, f'/explainer/{x["slug"]}.html'))
    xl = "".join(f'<a href="/explainer/{x["slug"]}.html"><span class="kicker">{e(x.get("topic", "Bay View"))} · Updated {e(dt.date.fromisoformat(x["updated"]).strftime("%b. %-d, %Y"))}</span><h3>{e(x["title"])}</h3><p>{e(x.get("dek", ""))}</p></a>' for x in sorted(EXPLAINERS, key=lambda x: x["updated"], reverse=True))
    (OUT / "explainers.html").write_text(shell("Explainers · The Bay View Bulletin",
        f'<h1 class="pagehead">Explainers</h1><p class="pagedek">How things work in Bay View and at City Hall, in plain language: the rules, who decides and how to weigh in. Kept up to date as things change.</p>'
        + (f'<div class="list">{xl}</div>' if xl else '<p class="pagedek">The first explainer is on its way.</p>'), d, "", None, "/explainers.html"))
    # weekend guide: this weekend's events by day, with the editor's picks when the day file has a "weekend" field
    today_ = dt.date.fromisoformat(d["date"])
    wk_ev = [ev for ev in d["events"] if "weekend" in ev_when_tags(ev_date(ev, today_), today_)]
    wk_meta = next((x.get("weekend") for x in reversed(issues) if x.get("weekend") and (today_ - dt.date.fromisoformat(x["date"])).days <= 3), None) or {}
    picks_html = ""
    for pk in wk_meta.get("picks", []):
        ev = next((v for v in wk_ev if v["title"].lower() == pk.get("title", "").lower()), None)
        if not ev:
            continue
        picks_html += (f'<a class="pick" href="{e(ev.get("link") or "/events.html")}">{ev_thumb(ev, today_)}<div><span class="t">{e(ev["day"].replace("Today, ", ""))} · {e(ev["when"])}</span>'
                       f'<h3>{e(ev["title"])}</h3><p><b>{e(ev["where"].split(" · ")[0])}.</b> {e(pk.get("why") or ev.get("desc", ""))}</p></div></a>')
    by_day, cur_ = [], None
    for ev in wk_ev:
        if ev["day"] != cur_:
            cur_ = ev["day"]; by_day.append(f'<div class="cal-day">{e(cur_)}</div>')
        by_day.append(f'<div class="ev" data-kind="{e(ev["kind"])}">{ev_thumb(ev, today_)}<span class="t">{e(ev["when"])}</span><div><a href="{e(ev.get("link") or "#")}" class="n">{e(ev["title"])}</a><div class="w">{e(ev["where"])}</div>{("<div class=" + chr(34) + "d" + chr(34) + ">" + e(ev["desc"]) + "</div>") if ev.get("desc") else ""}</div><span class="pill">{e(ev["kind"])}</span></div>')
    label = "This weekend in Bay View" if today_.weekday() >= 4 else "Coming up this weekend in Bay View"
    wbody = (f'<h1 class="pagehead">{label}</h1><p class="pagedek">{e(wk_meta.get("intro") or "Every show, market, class and gathering in Bay View from Friday through Sunday, in one place.")}</p>'
             + (f'<h2 class="kicker" style="margin:18px 0 0">Our picks</h2><div class="picks">{picks_html}</div>' if picks_html else "")
             + (f'<h2 class="kicker" style="margin:26px 0 0">Everything this weekend ({len(wk_ev)})</h2>' + "".join(by_day) if wk_ev else '<p class="pagedek">No weekend events listed yet.</p>')
             + '<p class="pagedek" style="margin-top:18px"><a href="/events.html" style="color:var(--lake)">All upcoming events →</a> · <a href="webcal://bayviewbulletin.com/events.ics" style="color:var(--lake)">Subscribe to the calendar</a></p>')
    (OUT / "weekend.html").write_text(shell(label + " · The Bay View Bulletin", wbody, d, "Events", {"title": label, "desc": wk_meta.get("intro") or "Every Bay View event this weekend, Friday through Sunday."}, "/weekend.html"))
    # Ask the Bulletin
    asked = [x for x in reversed(ALL_STORIES) if x.get("ask")]
    abody = (f'<h1 class="pagehead">Ask the Bulletin</h1><div class="askbox"><p>Wondering what&rsquo;s going up on that empty lot, why your street got new signs, or when a shop is opening? Ask us. We&rsquo;ll look into the questions that matter to the most neighbors and publish what we find here.</p>'
             f'<a class="btn" href="{ASK}">Ask a question</a></div>'
             + ('<h2 class="kicker" style="margin:20px 0 0">Questions we&rsquo;ve answered</h2><div class="list">' + "".join(f'<a href="{x["url"]}"><span class="kicker">{e(x["display_date"])}</span><h3>{e(x["title"])}</h3><p>{e(dek(x))}</p></a>' for x in asked) + "</div>" if asked
                else '<p class="pagedek">Answers will appear here. We don&rsquo;t publish your name or email.</p>'))
    (OUT / "ask.html").write_text(shell("Ask the Bulletin · The Bay View Bulletin", abody, d, "", {"title": "Ask the Bulletin", "desc": "Send The Bay View Bulletin your question about Bay View. We look into it and publish the answer."}, "/ask.html"))
    # Nov. 17: every page gets its own canonical URL and og:url, and section pages get their own link-preview image.
    og_for = {"/events.html": "events", "/weekend.html": "events", "/explainers.html": "city", "/buzz.html": "buzz", "/spotlight.html": "spotlight", "/history.html": "history", "/section/food.html": "food",
              "/section/food-drink.html": "food", "/section/fish-fry.html": "food", "/section/city.html": "city", "/section/city-hall.html": "city",
              "/section/streets.html": "city", "/section/safety.html": "safety", "/schools.html": "schools", "/section/schools.html": "schools",
              "/directory.html": "directory", "/section/business-spotlight.html": "spotlight", "/openings.html": "food", "/guides.html": "events", "/real-estate.html": "city"}
    for f in OUT.rglob("*.html"):
        rel = "/" + str(f.relative_to(OUT))
        if rel.endswith("/index.html"):
            rel = rel[:-len("index.html")]
        h = f.read_text()
        if 'rel="canonical"' not in h or "http-equiv=\"refresh\"" in h:
            continue
        if rel == "/404.html":
            h = re.sub(r'<link rel="canonical" href="[^"]*">', '<meta name="robots" content="noindex">', h, count=1)
        else:
            h = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{SITE}{rel}">', h, count=1)
            h = re.sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{SITE}{rel}">', h, count=1)
        ogk = og_for.get(rel) or ("buzz" if rel.startswith("/buzz/") else None)
        if ogk:
            h = h.replace(f'<meta property="og:image" content="{SITE}/og-default.png">', f'<meta property="og:image" content="{SITE}/og/{ogk}.png">', 1)
        f.write_text(h)
    (OUT / "site.webmanifest").write_text(json.dumps({"name": "The Bay View Bulletin", "short_name": "Bulletin", "description": "Bay View's morning paper",
        "start_url": "/", "display": "browser", "background_color": "#FFFFFF", "theme_color": "#1F4E79",
        "icons": [{"src": "/mark-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "/mark-512.png", "sizes": "512x512", "type": "image/png"}]}, indent=1))
    # Nov. 17: phone-sized copies of every photo (640 px) and srcset on <img> tags, so phones download far less.
    sm = OUT / "photos" / "sm"
    sm.mkdir(exist_ok=True)
    from PIL import Image as _Img
    have_sm = {}
    for f in (OUT / "photos").glob("*.jpg"):
        try:
            im = _Img.open(f)
            if im.width <= 700:
                continue
            w0 = im.width
            im = im.convert("RGB").resize((640, round(im.height * 640 / im.width)), _Img.LANCZOS)
            im.save(sm / f.name, "JPEG", quality=74, optimize=True, progressive=True)
            have_sm[f.name] = w0
        except Exception:
            pass
    def _srcset(m):
        tag, name = m.group(0), m.group(1)
        if name not in have_sm or "srcset=" in tag:
            return tag
        return tag[:-1] + f' srcset="/photos/sm/{name} 640w, /photos/{name} {have_sm[name]}w" sizes="(max-width: 700px) 100vw, 700px">'
    for f in OUT.rglob("*.html"):
        h = f.read_text()
        h2 = re.sub(r'<img\b[^>]*?src="/photos/([^"/]+\.jpg)"[^>]*>', _srcset, h)
        if h2 != h:
            f.write_text(h2)
    # site basics (Nov. 17): 404 page, RSS feed, sitemap, robots.txt
    nf = (f'<h1 class="pagehead">Page not found</h1><p class="pagedek">That page isn&rsquo;t here. It may have moved, or the link may be mistyped.</p>'
          '<form action="/search.html" style="margin:18px 0"><input name="q" type="search" placeholder="Search the Bulletin" style="width:100%;max-width:520px;font:400 18px var(--sans);padding:10px 12px;border:2px solid var(--ink);border-radius:4px;background:var(--paper);color:var(--ink)"></form>'
          '<p><a class="btn" href="/">Today&rsquo;s front page</a></p><p class="pagedek" style="margin-top:14px"><a href="/events.html" style="color:var(--lake)">Events</a> · <a href="/buzz.html" style="color:var(--lake)">Buzz</a> · <a href="/spotlight.html" style="color:var(--lake)">Spotlight</a> · <a href="/archive.html" style="color:var(--lake)">Archive</a></p>')
    (OUT / "404.html").write_text(re.sub(r'<link rel="canonical" href="[^"]*">', '<meta name="robots" content="noindex">', shell("Page not found · The Bay View Bulletin", nf, d, ""), count=1))
    from email.utils import format_datetime
    def rfc(dstr):
        return format_datetime(dt.datetime.fromisoformat(dstr + "T06:00:00" + ctoff(dstr)))
    feed_items = sorted(ALL_STORIES, key=lambda x: x["issue_date"], reverse=True)[:60]
    hist_feed = [dict(x, _hist=True) for x in ALL_HISTORY]
    rows_xml = []
    for x in feed_items:
        img = (x.get("image") or {}).get("src")
        rows_xml.append(f'<item><title>{e(x["title"])}</title><link>{SITE}{e(x["url"])}</link><guid isPermaLink="true">{SITE}{e(x["url"])}</guid>'
                        f'<pubDate>{rfc(x["issue_date"])}</pubDate><category>{e(x["section"])}</category><description>{e(dek(x))}</description>'
                        + (f'<enclosure url="{e(abs_url(img))}" type="image/jpeg" length="0"/>' if img else "") + '</item>')
    for x in hist_feed[-14:]:
        if x.get("url") and x.get("issue_date"):
            rows_xml.append(f'<item><title>History: {e(x["title"])}</title><link>{SITE}{e(x["url"])}</link><guid isPermaLink="true">{SITE}{e(x["url"])}</guid><pubDate>{rfc(x["issue_date"])}</pubDate><category>History</category><description>{e(x.get("text", ""))}</description></item>')
    feed = ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>The Bay View Bulletin</title>'
            f'<link>{SITE}/</link><description>Bay View&apos;s morning paper: daily news for Milwaukee&apos;s Bay View neighborhood.</description><language>en-us</language>'
            f'<atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/><lastBuildDate>{rfc(d["date"])}</lastBuildDate>' + "".join(rows_xml) + '</channel></rss>')
    (OUT / "feed.xml").write_text(feed)
    urls = []
    for f in sorted(OUT.rglob("*.html")):
        rel = "/" + str(f.relative_to(OUT)).replace("index.html", "")
        if rel in ("/404.html", "/map.html", "/milwaukee.html") or "http-equiv=\"refresh\"" in f.read_text()[:600]:
            continue
        urls.append(f"<url><loc>{SITE}{e(rel)}</loc></url>")
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(urls) + "</urlset>")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /map.html\nDisallow: /milwaukee.html\n\nSitemap: {SITE}/sitemap.xml\n")
    print("built", OUT, len(issues), "issue(s)")


if __name__ == "__main__":
    build()

