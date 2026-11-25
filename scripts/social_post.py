"""Make the day's Facebook + Instagram post: a branded 1080x1350 image and two captions.

    python3 scripts/social_post.py 2026-11-25            # morning roundup (every day)
    python3 scripts/social_post.py 2026-11-26 --weekend  # Thursday weekend-guide post

Writes review/social/<date>[-weekend].png plus review/social/<date>[-weekend].txt with the FB caption (with links)
and the IG caption (Instagram doesn't link captions, so it says "link in bio"). review/ is git-ignored.
Content comes only from the day file: the "briefing" bullets (or the lead story, Buzz and events), and for --weekend the
"weekend" picks. The image uses no third-party photos, so there's nothing to credit on the card.
Rules (Ben, Nov. 25): never include held items, Safety stories, unconfirmed Buzz or private people's names.
"""
import json
import re
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_og import font, mark, PAPER, INK, MUTED, RULE, LAKE, WARM, ROOT  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

SITE = "bayviewbulletin.com"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def safe_items(d):
    """The day's briefing bullets, minus anything the posting rules leave out."""
    held = {s["title"] for sec in d["sections"].values() for s in sec if s.get("hold")}
    safety = {s["title"] for k, sec in d["sections"].items() for s in sec if k == "safety" or s.get("tag") == "Safety"}
    unconf = {b["headline"] for b in d.get("buzz", []) if b.get("unconfirmed") or b.get("hold")}
    items = []
    for b in d.get("briefing") or []:
        t = b["text"]
        if any(x and x.lower()[:40] in t.lower() for x in held | safety | unconf):
            continue
        items.append(t)
    if not items:  # fallback: top stories, first confirmed Buzz, tonight's first event
        for k, sec in d["sections"].items():
            for s in sec:
                if s["title"] not in held | safety and k != "spotlight":
                    items.append(s["title"] + ".")
        bz = [b for b in d.get("buzz", []) if b["headline"] not in unconf]
        if bz:
            items.append("Buzz: " + bz[0]["headline"] + ".")
    return items[:5]


def weekend_items(d):
    w = d.get("weekend") or {}
    evs = {e["title"].lower(): e for e in d.get("events", [])}
    out = []
    for pk in w.get("picks", [])[:5]:
        ev = evs.get(pk["title"].lower())
        if ev:
            out.append(f'{ev["day"].replace("Today, ", "")}, {ev["when"]}: {ev["title"]} ({ev["where"].split(",")[0]})')
    return w.get("intro", ""), out


def card(title_kicker, date_line, items, out):
    W, H = 1080, 1350
    im = Image.new("RGBA", (W, H), PAPER)
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, W // 2, 16], fill=LAKE)
    dr.rectangle([W // 2, 0, W, 16], fill=WARM)
    im.alpha_composite(mark(84), (60, 60))
    dr.text((164, 78), "The Bay View Bulletin", font=font("plate", 50), fill=INK)
    dr.text((166, 134), "Bay View's morning paper", font=font("serif_i", 28), fill=MUTED)
    dr.line([(60, 190), (W - 60, 190)], fill=INK, width=3)
    dr.line([(60, 198), (W - 60, 198)], fill=INK, width=1)
    dr.text((60, 230), title_kicker.upper(), font=font("sans_b", 30), fill=LAKE)
    dr.text((60, 274), date_line, font=font("serif_b", 46), fill=INK)
    y, body = 360, font("serif_i", 1)  # placeholder
    body = font("serif_b", 36)
    size = 36
    # shrink the text until every bullet fits above the footer
    while True:
        body = font("serif_b", size)
        lines = []
        for it in items:
            wrapped = textwrap.wrap(it, width=int(1560 / size))
            lines.append(wrapped)
        need = sum(len(w) * int(size * 1.32) + int(size * 0.7) for w in lines)
        if need <= 820 or size <= 26:
            break
        size -= 2
    y = 370
    for wrapped in lines:
        dr.ellipse([62, y + size * 0.42 - 7, 76, y + size * 0.42 + 7], fill=WARM)
        for ln in wrapped:
            dr.text((100, y), ln, font=body, fill=INK)
            y += int(size * 1.32)
        y += int(size * 0.7)
    dr.rectangle([0, H - 150, W, H], fill=LAKE)
    dr.text((W / 2, H - 92), "Read it all at " + SITE, font=font("serif_b", 44), fill="#FFFFFF", anchor="ms")
    dr.text((W / 2, H - 46), "Free every morning by 6:30. No ads, no paywall.", font=font("sans_b", 26), fill="#DCE7F2", anchor="ms")
    im.convert("RGB").save(out, quality=90)


def main():
    date = sys.argv[1]
    weekend = "--weekend" in sys.argv
    d = json.loads((ROOT / f"content/issues/{date}.json").read_text())
    outdir = ROOT / "review/social"
    outdir.mkdir(parents=True, exist_ok=True)
    stem = date + ("-weekend" if weekend else "")
    if weekend:
        intro, items = weekend_items(d)
        if not items:
            sys.exit("No weekend picks in the day file; write the 'weekend' field first.")
        card("This weekend in Bay View", d["display_date"].split(",")[0] + "'s picks", items, outdir / f"{stem}.png")
        fb = (intro + "\n\n" if intro else "") + "\n".join("• " + x for x in items) + f"\n\nEvery event this weekend: https://{SITE}/weekend.html"
        ig = (intro + "\n\n" if intro else "") + "\n".join("• " + x for x in items) + "\n\nThe full weekend guide is at the link in our bio.\n\n#BayView #BayViewMKE #Milwaukee #MKE"
    else:
        items = safe_items(d)
        card("Bay View in 60 seconds", d["display_date"], items, outdir / f"{stem}.png")
        fb = f"Good morning, Bay View. Here's {d['display_date'].split(',')[0]} in 60 seconds:\n\n" + "\n".join("• " + x for x in items) + f"\n\nToday's full Bulletin: https://{SITE}/"
        ig = f"Good morning, Bay View. Here's {d['display_date'].split(',')[0]} in 60 seconds:\n\n" + "\n".join("• " + x for x in items) + "\n\nToday's full Bulletin is at the link in our bio.\n\n#BayView #BayViewMKE #Milwaukee #MKE"
    (outdir / f"{stem}.txt").write_text("=== FACEBOOK ===\n" + fb + "\n\n=== INSTAGRAM ===\n" + ig + "\n")
    print(outdir / f"{stem}.png")
    print(outdir / f"{stem}.txt")


if __name__ == "__main__":
    main()
