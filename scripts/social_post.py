"""Make the day's Facebook + Instagram post: a branded 4:5 carousel (1080x1350 slides) and two captions.

    python3 scripts/social_post.py 2026-11-25            # morning post (every day)
    python3 scripts/social_post.py 2026-11-26 --weekend  # Thursday weekend-guide post

Writes review/social/<stem>/01.jpg, 02.jpg, ... (upload them in order as one post) and review/social/<stem>/caption.txt
(FACEBOOK caption with the link; INSTAGRAM caption pointing to the link in bio). <stem> is the date, plus "-weekend".
review/ is git-ignored.

Design (Ben, Nov. 25 v2; see claude/bay-view-bulletin-brand.md):
- Slide 1 (cover): the lead story's photo full-bleed with the headline; it's what stops the scroll and is the grid thumbnail.
- Story slides: photo on top, section label, headline, one-line dek, credit. Events slide: a time/title/venue table.
- Last slide: where to read the rest (bayviewbulletin.com; "link in bio" on Instagram).
- 4:5 portrait; text stays 72 px in from the edges, inside Instagram's 3:4 grid crop.
Content rules (Ben, Nov. 25): post only what's on the site. Never held items, Safety stories, unconfirmed Buzz or private
people's names. Photos are used on social only when they come from the business/organizer itself (its Instagram or
website), Wikimedia Commons / public domain, or the Bulletin's own; news outlets' photos are left off social
(the slide gets a typographic panel instead), and every photo carries its credit.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_og  # noqa: E402
from make_og import font, mark, ROOT  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageOps  # noqa: E402

make_og.FONTS.setdefault("serif_r", "source-serif-4/files/source-serif-4-latin-400-normal")
make_og.FONTS.setdefault("sans_r", "source-sans-3/files/source-sans-3-latin-400-normal")
make_og.FONTS.setdefault("sans_sb", "source-sans-3/files/source-sans-3-latin-600-normal")

W, H, M = 1080, 1350, 72
PAPER, INK, MUTED, RULE, SOFT = "#FFFFFF", "#121212", "#5C6066", "#E3E1DC", "#F6F4EF"
LAKE, WARM, LAKE_SOFT, WARM_SOFT, BUZZ, HOT = "#1F4E79", "#C9541F", "#E8EFF6", "#FBEDE3", "#FFE14D", "#D7261E"
SITE = "bayviewbulletin.com"
OK_PHOTO = re.compile(r"instagram|website|wikimedia|commons|cc by|cc0|public domain|bay view bulletin", re.I)


# ---------- helpers ----------
def wrap(draw, text, fnt, maxw):
    """Wrap by measured pixel width; keeps 'Dec. 15'-style pairs together."""
    text = re.sub(r"\b([A-Z][a-z]{2,4}\.) (\d)", "\\1\u00a0\\2", text)
    lines, cur = [], ""
    for w in text.split(" "):
        t = (cur + " " + w).strip()
        if draw.textlength(t.replace("\u00a0", " "), font=fnt) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return [l.replace("\u00a0", " ") for l in lines]


def fit_block(draw, text, key, sizes, maxw, maxlines):
    for s in sizes:
        f = font(key, s)
        ls = wrap(draw, text, f, maxw)
        if len(ls) <= maxlines:
            return f, s, ls
    f = font(key, sizes[-1])
    ls = wrap(draw, text, f, maxw)[:maxlines]
    ls[-1] = ls[-1].rstrip(" ,;:") + "…"
    return f, sizes[-1], ls


def text_lines(draw, xy, lines, fnt, size, fill, lead=1.22):
    """Draw lines on a baseline grid; returns the y just below the block."""
    x, y = xy
    step = round(size * lead)
    for i, ln in enumerate(lines):
        draw.text((x, y + size + i * step), ln, font=fnt, fill=fill, anchor="ls")
    return y + size + (len(lines) - 1) * step + round(size * 0.32)


def tracked(draw, xy, text, fnt, fill, track=2, anchor="ls"):
    """Letter-spaced label."""
    x, y = xy
    if anchor == "rs":
        x -= sum(draw.textlength(c, font=fnt) + track for c in text) - track
    for c in text:
        draw.text((x, y), c, font=fnt, fill=fill, anchor="ls")
        x += draw.textlength(c, font=fnt) + track
    return x


def photo_ok(img):
    return bool(img and img.get("src") and OK_PHOTO.search(img.get("credit", "")))


def load_photo(src):
    for base in ("static", "docs"):
        p = ROOT / base / src.lstrip("/")
        if p.exists():
            return Image.open(p).convert("RGB")
    return None


def place_photo(im, src, box, contain=False):
    x0, y0, x1, y1 = box
    ph = load_photo(src)
    if ph is None:
        return False
    bw, bh = x1 - x0, y1 - y0
    if contain:  # flyers: show the whole flyer on a darkened, blurred bed of itself
        bed = ImageOps.fit(ph, (bw, bh)).filter(ImageFilter.GaussianBlur(28))
        bed = Image.blend(bed, Image.new("RGB", (bw, bh), "#000000"), 0.35)
        ph.thumbnail((bw - 40, bh - 40))
        bed.paste(ph, ((bw - ph.width) // 2, (bh - ph.height) // 2))
        im.paste(bed, (x0, y0))
    else:
        im.paste(ImageOps.fit(ph, (bw, bh), centering=(0.5, 0.45)), (x0, y0))
    return True


def credit_on_photo(im, draw, box, text):
    x0, y0, x1, y1 = box
    f = font("sans_r", 20)
    t = "Photo: " + text
    while draw.textlength(t, font=f) > (x1 - x0) - 2 * M and len(t) > 20:
        t = t[:-2].rstrip() + "…"
    grad = Image.linear_gradient("L").resize((x1 - x0, 90)).point(lambda v: int(v * 0.6))
    im.paste(Image.new("RGBA", (x1 - x0, 90), "#000000"), (x0, y1 - 90), grad)
    draw.text((x1 - M, y1 - 22), t, font=f, fill="#FFFFFF", anchor="rs")


def header(draw, im, date_label):
    draw.rectangle([0, 0, W // 2, 12], fill=LAKE)
    draw.rectangle([W // 2, 0, W, 12], fill=WARM)
    im.alpha_composite(mark(56), (M, 40))
    draw.text((M + 72, 82), "The Bay View Bulletin", font=font("plate", 38), fill=INK, anchor="ls")
    tracked(draw, (W - M, 80), date_label.upper(), font("sans_b", 20), MUTED, 2, anchor="rs")
    draw.line([(M, 116), (W - M, 116)], fill=INK, width=2)
    draw.line([(M, 122), (W - M, 122)], fill=INK, width=1)


def footer(draw, left, right, arrow=False):
    draw.line([(M, H - 92), (W - M, H - 92)], fill=RULE, width=2)
    draw.text((M, H - 48), left, font=font("sans_sb", 24), fill=MUTED, anchor="ls")
    x = W - M
    if arrow:  # a drawn arrow: the brand fonts have no arrow glyph
        y = H - 56
        draw.line([(x - 30, y), (x - 2, y)], fill=LAKE, width=4)
        draw.polygon([(x, y), (x - 12, y - 9), (x - 12, y + 9)], fill=LAKE)
        x -= 44
    draw.text((x, H - 48), right, font=font("sans_b", 24), fill=LAKE, anchor="rs")


def text_height(draw, item, key, sizes, maxlines, dek_lines=3):
    """Height of the kicker + headline (+ dek) block, used to size the photo above it."""
    f, s, ls = fit_block(draw, item["title"], key, sizes, W - 2 * M, maxlines)
    h = 22 + s + (len(ls) - 1) * round(s * 1.16) + round(s * 0.32)
    if item.get("dek"):
        f2, s2, l2 = fit_block(draw, item["dek"], "serif_r", [34, 32, 30], W - 2 * M, dek_lines)
        h += 6 + s2 + (len(l2) - 1) * round(s2 * 1.3) + round(s2 * 0.32)
    return h


def kicker(draw, xy, label, color, chip=None):
    f = font("sans_b", 24)
    x, y = xy
    if chip:  # Buzz: red label on yellow, as on the site
        w = sum(draw.textlength(c, font=f) + 2 for c in label) + 22
        draw.rectangle([x, y - 27, x + w, y + 9], fill=chip)
        tracked(draw, (x + 12, y), label, f, color, 2)
        return
    draw.rectangle([x, y - 19, x + 8, y + 1], fill=color)
    tracked(draw, (x + 20, y), label, f, color, 2)


def new():
    im = Image.new("RGBA", (W, H), PAPER)
    return im, ImageDraw.Draw(im)


# ---------- slides ----------
def cover(item, date_label, kick):
    im, dr = new()
    header(dr, im, date_label)
    th = text_height(dr, item, "serif_b", [62, 58, 54, 50, 46], 4, 0)
    bottom = max(700, min(940, H - 92 - 56 - th - 66))
    box = (0, 146, W, bottom)
    if photo_ok(item.get("image")) and place_photo(im, item["image"]["src"], box, item.get("contain")):
        credit_on_photo(im, dr, box, item["image"]["credit"])
    else:  # typographic cover
        dr.rectangle(box, fill=LAKE)
        dr.text((M, 430), "Bay View", font=font("plate", 104), fill="#FFFFFF", anchor="ls")
        dr.text((M, 540), "in 60 seconds", font=font("serif_i", 78), fill="#DCE7F2", anchor="ls")
        tracked(dr, (M, 640), date_label.upper(), font("sans_b", 30), BUZZ, 3)
    y = bottom + 64
    kicker(dr, (M, y), kick, WARM)
    f, s, ls = fit_block(dr, item["title"], "serif_b", [62, 58, 54, 50, 46], W - 2 * M, 4)
    text_lines(dr, (M, y + 22), ls, f, s, INK, 1.16)
    footer(dr, "Bay View's morning paper", "Swipe for more", arrow=True)
    return im


def story(item, date_label, n, total):
    im, dr = new()
    header(dr, im, date_label)
    th = text_height(dr, item, "serif_b", [56, 52, 48, 44], 3)
    bottom = max(660, min(900, H - 92 - 56 - th - 66))
    box = (0, 146, W, bottom)
    has = photo_ok(item.get("image")) and place_photo(im, item["image"]["src"], box, item.get("contain"))
    if has:
        credit_on_photo(im, dr, box, item["image"]["credit"])
        y = bottom + 64
    else:  # no usable photo: a tinted panel with the section name set large, and bigger type below it
        bottom = 560
        dr.rectangle((0, 146, W, bottom), fill=item.get("tint", LAKE_SOFT))
        col = item.get("color", LAKE)
        f0, s0, l0 = fit_block(dr, item["label_big"], "plate", [110, 96, 84], W - 2 * M, 1)
        dr.text((M, bottom - 64), l0[0], font=f0, fill=col, anchor="ls")
        dr.line([(M, bottom - 34), (M + 120, bottom - 34)], fill=col, width=6)
        im.alpha_composite(mark(96), (W - M - 96, 146 + 48))
        y = bottom + 70
    kicker(dr, (M, y), item["kicker"], item.get("color", LAKE), item.get("chip"))
    hs, ds = ([56, 52, 48, 44], [34, 32, 30]) if has else ([68, 62, 56, 50], [40, 38, 36, 34])
    f, s, ls = fit_block(dr, item["title"], "serif_b", hs, W - 2 * M, 3 if has else 4)
    y = text_lines(dr, (M, y + 22), ls, f, s, INK, 1.16)
    if item.get("dek"):
        f2, s2, l2 = fit_block(dr, item["dek"], "serif_r", ds, W - 2 * M, 3 if has else 6)
        text_lines(dr, (M, y + 10), l2, f2, s2, MUTED, 1.32)
    footer(dr, f"{n} / {total}", item.get("more", SITE))
    return im


def events_slide(evs, date_label, n, total):
    im, dr = new()
    header(dr, im, date_label)
    dr.rectangle((0, 146, W, 346), fill=WARM_SOFT)
    dr.text((M, 262), "Today in Bay View", font=font("plate", 70), fill=WARM, anchor="ls")
    tracked(dr, (M, 312), f"{len(evs['all'])} THINGS TO DO · HIGHLIGHTS", font("sans_b", 22), MUTED, 2)
    y, tcol = 392, 210
    fw = font("sans_b", 28)
    # first pass: measure rows, then spread the spare height between them
    heights = []
    for ev in evs["rows"]:
        wl = wrap(dr, ev["when"], fw, tcol - 28)[:2]
        ft, st, lt = fit_block(dr, ev["title"], "serif_b", [36, 34, 32], W - 2 * M - tcol, 2)
        heights.append(max(st + (len(lt) - 1) * round(st * 1.15) + round(st * 0.32) + 40, st + (len(wl) - 1) * 32 + 12) + 48)
    spare = (H - 92 - 40 - y) - sum(heights)
    pad = max(0, min(36, spare // max(1, 2 * len(heights))))
    for ev in evs["rows"]:
        y += pad
        wl = wrap(dr, ev["when"], fw, tcol - 28)[:2]
        ft, st, lt = fit_block(dr, ev["title"], "serif_b", [36, 34, 32], W - 2 * M - tcol, 2)
        # time and title share the first baseline, so every row lines up
        base = y + st
        for i, l in enumerate(wl):
            dr.text((M, base + i * 32), l, font=fw, fill=WARM, anchor="ls")
        yy = text_lines(dr, (M + tcol, y), lt, ft, st, INK, 1.15)
        dr.text((M + tcol, yy + 24), ev["where"].split(",")[0], font=font("sans_r", 26), fill=MUTED, anchor="ls")
        y = max(yy + 40, base + (len(wl) - 1) * 32 + 12) + 22 + pad
        dr.line([(M, y), (W - M, y)], fill=RULE, width=1)
        y += 26
        if y > H - 300:
            break
    footer(dr, f"{n} / {total}", f"Every event: {SITE}/events")
    return im


def cta(inside, total):
    im, dr = new()
    dr.rectangle((0, 0, W, H), fill=LAKE)
    dr.rectangle([0, 0, W // 2, 12], fill="#8DBDE3")
    dr.rectangle([W // 2, 0, W, 12], fill=WARM)
    im.alpha_composite(mark(150), ((W - 150) // 2, 170))
    dr.text((W / 2, 440), "Read the full Bulletin", font=font("plate", 70), fill="#FFFFFF", anchor="ms")
    dr.text((W / 2, 520), SITE, font=font("serif_b", 50), fill=BUZZ, anchor="ms")
    dr.text((W / 2, 578), "Link in our bio", font=font("sans_sb", 30), fill="#DCE7F2", anchor="ms")
    dr.line([(M + 140, 648), (W - M - 140, 648)], fill="#5F86AC", width=2)
    lab, f = "INSIDE TODAY", font("sans_b", 24)
    tracked(dr, (W / 2 - (sum(dr.textlength(c, font=f) + 3 for c in lab) - 3) / 2, 712), lab, f, "#DCE7F2", 3)
    y = 760
    for line in inside[:5]:
        dr.text((W / 2, y + 34), line, font=font("serif_r", 34), fill="#FFFFFF", anchor="ms")
        y += 58
    dr.text((W / 2, H - 120), "Free every morning by 6:30. No ads, no paywall.", font=font("sans_sb", 26), fill="#DCE7F2", anchor="ms")
    dr.text((W / 2, H - 70), f"{total} / {total}", font=font("sans_sb", 22), fill="#8DBDE3", anchor="ms")
    return im


# ---------- content ----------
SEC_LABEL = {"top": ("NEWS", "News", LAKE, LAKE_SOFT), "openings": ("FOOD & DRINK", "Food & Drink", WARM, WARM_SOFT),
             "development": ("CITY HALL", "City Hall", LAKE, LAKE_SOFT), "streets": ("STREETS", "Streets", LAKE, LAKE_SOFT),
             "schools": ("SCHOOLS", "Schools", LAKE, LAKE_SOFT), "parks": ("PARKS", "Parks", WARM, WARM_SOFT),
             "help": ("WAYS TO HELP", "Ways to help", WARM, WARM_SOFT), "realestate": ("REAL ESTATE", "Real estate", LAKE, LAKE_SOFT),
             "fishfry": ("FISH FRY", "Fish fry", WARM, WARM_SOFT), "pets": ("PETS", "Pets", WARM, WARM_SOFT),
             "sports": ("SPORTS", "Sports", LAKE, LAKE_SOFT), "remembrances": ("REMEMBRANCE", "Remembrance", MUTED, SOFT),
             "protests": ("COMMUNITY", "Community", LAKE, LAKE_SOFT)}


def stories(d):
    return [(k, s) for k, sec in d["sections"].items() for s in sec
            if not s.get("hold") and k != "safety" and s.get("tag") != "Safety"]


def ev_hour(e):
    m = re.search(r"(\d{1,2})(?::(\d\d))?\s*(am|pm)", e["when"], re.I)
    if not m:
        return 99
    return int(m.group(1)) % 12 + (12 if m.group(3).lower() == "pm" else 0) + int(m.group(2) or 0) / 60


def daily(d):
    st = stories(d)
    news = [(k, s) for k, s in st if k != "spotlight"]
    spot = next((s for k, s in st if k == "spotlight"), None)
    lead = next(((k, s) for k, s in news if photo_ok(s.get("image")) and not s.get("citywide")), news[0] if news else None)
    slides = []
    if lead:
        kick = "TODAY'S TOP STORY" if lead[0] == "top" else SEC_LABEL.get(lead[0], SEC_LABEL["top"])[0]
        slides.append(("cover", {"title": lead[1]["title"], "image": lead[1].get("image")}, kick))
    for k, s in [x for x in news if not lead or x[1] is not lead[1]][:2]:
        kk, big, col, tint = SEC_LABEL.get(k, SEC_LABEL["top"])
        slides.append(("story", {"title": s["title"], "dek": s.get("dek"), "image": s.get("image"),
                                 "kicker": ("CITYWIDE · " if s.get("citywide") else "") + kk, "label_big": big, "color": col, "tint": tint}))
    if spot:
        img = next((g for g in [spot.get("image")] + spot.get("gallery", []) if photo_ok(g)), spot.get("image"))
        slides.append(("story", {"title": spot["title"].replace("Spotlight: ", ""), "dek": spot.get("dek"), "image": img,
                                 "kicker": "BUSINESS SPOTLIGHT", "label_big": "Spotlight", "color": WARM, "tint": WARM_SOFT, "more": f"{SITE}/spotlight"}))
    today = [e for e in d.get("events", []) if e["day"].startswith("Today")]
    if today:
        timed = sorted([e for e in today if ev_hour(e) < 99], key=ev_hour)
        slides.append(("events", {"rows": (timed or today)[:5], "all": today}))
    bz = next((b for b in d.get("buzz", []) if not b.get("unconfirmed") and not b.get("hold")), None)
    if bz:
        slides.append(("story", {"title": bz["headline"], "dek": None, "image": bz.get("image"), "kicker": "THE BAY VIEW BUZZ",
                                 "label_big": "The Buzz", "color": HOT, "chip": BUZZ, "tint": "#FFF6C2", "more": f"{SITE}/buzz"}))
    h = d.get("history")
    if h and len(slides) < 7:
        slides.append(("story", {"title": h["title"], "dek": h.get("text") or f'From {h.get("year", "the archives")}.',
                                 "image": h.get("image"), "kicker": "BAY VIEW HISTORY", "label_big": "History", "color": LAKE,
                                 "tint": LAKE_SOFT, "more": f"{SITE}/history"}))
    n = len(news)
    inside = [f"{n} news stor{'y' if n == 1 else 'ies'}" + (f" · {len(today)} things to do today" if today else ""),
              f"Spotlight: {spot['title'].replace('Spotlight: ', '')}" if spot else "",
              "The Bay View Buzz · Bay View history"]
    return slides[:7], [x for x in inside if x]


def weekend(d):
    w = d.get("weekend") or {}
    evs = {e["title"].lower(): e for e in d.get("events", [])}
    picks = [(pk, evs.get(pk["title"].lower())) for pk in w.get("picks", [])]
    picks = [(pk, e) for pk, e in picks if e][:5]
    if not picks:
        sys.exit("No weekend picks in the day file; write the 'weekend' field first.")

    def img(e):
        return {"src": e["image"], "credit": e["where"].split(",")[0] + " (organizer's flyer)"} if e.get("image") else None
    first = picks[0][1]
    cov = {"title": f"{len(picks)} picks for the weekend in Bay View",
           "image": {**img(first), "credit": img(first)["credit"] + " on Instagram"} if first.get("image") else None, "contain": True}
    slides = [("cover", cov, "WEEKEND PICKS")]
    for pk, e in picks:
        im = img(e)
        if im:
            im["credit"] += " on Instagram"
        slides.append(("story", {"title": e["title"], "dek": f'{e["day"].replace("Today, ", "")} · {e["when"]} · {e["where"].split(",")[0]}. {pk.get("why", "")}'.strip(),
                                 "image": im, "contain": True, "kicker": e.get("kind", "Event").upper(), "label_big": e.get("kind", "Event"),
                                 "color": WARM, "tint": WARM_SOFT, "more": f"{SITE}/weekend"}))
    return slides[:7], ["Every event this weekend", f"{SITE}/weekend"]


def captions(d, weekend_mode):
    if weekend_mode:
        w = d.get("weekend") or {}
        evs = {e["title"].lower(): e for e in d.get("events", [])}
        lines = [f'{e["day"].replace("Today, ", "")}, {e["when"]}: {e["title"]} ({e["where"].split(",")[0]})'
                 for pk in w.get("picks", [])[:5] if (e := evs.get(pk["title"].lower()))]
        body = (w.get("intro") or "Our picks for the weekend in Bay View.").strip() + "\n\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(lines, 1))
        return (body + f"\n\nEvery event this weekend: https://{SITE}/weekend.html",
                body + "\n\nEvery event this weekend is at the link in our bio.\n\n#BayView #BayViewMKE #MilwaukeeEvents #MKE")
    held = {s["title"] for sec in d["sections"].values() for s in sec if s.get("hold")}
    safety = {s["title"] for k, sec in d["sections"].items() for s in sec if k == "safety" or s.get("tag") == "Safety"}
    unconf = {b["headline"] for b in d.get("buzz", []) if b.get("unconfirmed") or b.get("hold")}
    items = [b["text"] for b in d.get("briefing") or [] if not any(x and x.lower()[:40] in b["text"].lower() for x in held | safety | unconf)]
    lead = next((s["title"] for k, s in stories(d) if k != "spotlight"), None)
    body = ((lead + "\n\n") if lead else "") + f"Bay View in 60 seconds, {d['display_date'].split(',')[0]}:\n" + "\n".join(f"→ {x}" for x in items[:5])
    return (body + f"\n\nThe full Bulletin, free every morning: https://{SITE}/",
            body + "\n\nSwipe for the details. The full Bulletin is free every morning at the link in our bio.\n\n#BayView #BayViewMKE #Milwaukee #MKE")


def main():
    date = sys.argv[1]
    weekend_mode = "--weekend" in sys.argv
    # One-off overrides (content/social_schedule.json): skip days and swapped posts
    sched_f = ROOT / "content/social_schedule.json"
    sched = json.loads(sched_f.read_text()) if sched_f.exists() else {}
    if date in sched.get("skip", {}):
        print(f"DO NOT POST TODAY ({date}). {sched['skip'][date]}")
        return
    ov = sched.get("override", {}).get(date)
    d = json.loads((ROOT / f"content/issues/{date}.json").read_text())
    if ov:
        if weekend_mode:
            print(f"DO NOT POST a second weekend carousel today ({date}): {ov.get('note', '')}")
            return
        if ov.get("mode") == "weekend" and (d.get("weekend") or {}).get("picks"):
            weekend_mode = True
        print(f"SCHEDULE NOTE for {date}: post no earlier than {ov.get('not_before', 'the usual time')} Central. {ov.get('note', '')}")
    out = ROOT / "review/social" / (date + ("-weekend" if "--weekend" in sys.argv else ""))  # an override still writes to the day's usual folder
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob("*.png")) + list(out.glob("*.jpg")):
        old.unlink()
    day = dt.date.fromisoformat(date)
    date_label = day.strftime("%a., %b. ") + str(day.day)
    slides, inside = weekend(d) if weekend_mode else daily(d)
    total = len(slides) + 1
    paths = []
    for i, sl in enumerate(slides, 1):
        im = cover(sl[1], date_label, sl[2]) if sl[0] == "cover" else events_slide(sl[1], date_label, i, total) if sl[0] == "events" else story(sl[1], date_label, i, total)
        paths.append(out / f"{i:02d}.jpg")
        im.convert("RGB").save(paths[-1], quality=92, subsampling=0, optimize=True)
    paths.append(out / f"{total:02d}.jpg")
    cta(inside, total).convert("RGB").save(paths[-1], quality=92, subsampling=0, optimize=True)
    fb, ig = captions(d, weekend_mode)
    (out / "caption.txt").write_text("=== FACEBOOK ===\n" + fb + "\n\n=== INSTAGRAM ===\n" + ig + "\n")
    print("\n".join(str(p) for p in paths + [out / "caption.txt"]))


if __name__ == "__main__":
    main()
