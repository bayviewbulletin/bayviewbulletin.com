"""One-off: the Bulletin's introduction carousel, its first post on Facebook and Instagram (Nov. 25, 2026).

    python3 scripts/social_intro.py   -> review/social/intro/01.jpg ... and caption.txt

Uses the same design system as scripts/social_post.py. Numbers are pulled from the repo at build time.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import social_post as sp  # noqa: E402
from social_post import font, mark, ROOT, W, H, M, INK, MUTED, RULE, LAKE, WARM, LAKE_SOFT, WARM_SOFT, BUZZ  # noqa: E402

DATE = "2026-11-25"
d = json.loads((ROOT / f"content/issues/{DATE}.json").read_text())
n_events = len(d["events"])
n_dir = len(json.loads((ROOT / "content/directory.json").read_text()))
LABEL = "BAY VIEW, MILWAUKEE"


def list_slide(title, sub, rows, n, total, tint=LAKE_SOFT, color=LAKE):
    im, dr = sp.new()
    sp.header(dr, im, LABEL)
    dr.rectangle((0, 146, W, 356), fill=tint)
    dr.text((M, 262), title, font=font("plate", 70), fill=color, anchor="ls")
    sp.tracked(dr, (M, 314), sub, font("sans_b", 22), MUTED, 2)
    y, lcol = 400, 230
    fl = font("sans_b", 32)
    sized = [sp.fit_block(dr, text, "serif_r", [36, 34, 32], W - 2 * M - lcol, 3) for _, text in rows]
    used = sum(s + (len(ls) - 1) * round(s * 1.25) + round(s * 0.32) + 56 for f, s, ls in sized)
    pad = max(0, min(30, ((H - 92 - 40 - y) - used) // (2 * len(rows))))
    for (label, text), (f, s, ls) in zip(rows, sized):
        y += pad
        dr.text((M, y + s), label, font=fl, fill=WARM, anchor="ls")  # label shares the first baseline with its text
        yy = sp.text_lines(dr, (M + lcol, y), ls, f, s, INK, 1.25)
        y = yy + 26 + pad
        dr.line([(M, y), (W - M, y)], fill=RULE, width=1)
        y += 30
    sp.footer(dr, f"{n} / {total}", sp.SITE)
    return im


def cta(total):
    im, dr = sp.new()
    dr.rectangle((0, 0, W, H), fill=LAKE)
    dr.rectangle([0, 0, W // 2, 12], fill="#8DBDE3")
    dr.rectangle([W // 2, 0, W, 12], fill=WARM)
    im.alpha_composite(mark(150), ((W - 150) // 2, 160))
    dr.text((W / 2, 420), "Follow along", font=font("plate", 76), fill="#FFFFFF", anchor="ms")
    dr.text((W / 2, 486), "for Bay View's morning rundown", font=font("serif_i", 40), fill="#DCE7F2", anchor="ms")
    dr.line([(M + 140, 548), (W - M - 140, 548)], fill="#5F86AC", width=2)
    rows = [("Every morning", "Bay View in 60 seconds"), ("Thursdays", "Our weekend picks"), ("Anytime", "The full Bulletin, free")]
    y = 620
    for a, b in rows:
        dr.text((W / 2 - 24, y), a, font=font("sans_b", 30), fill=BUZZ, anchor="rs")
        dr.text((W / 2 + 24, y), b, font=font("serif_r", 34), fill="#FFFFFF", anchor="ls")
        y += 64
    dr.text((W / 2, 880), sp.SITE, font=font("serif_b", 54), fill=BUZZ, anchor="ms")
    dr.text((W / 2, 940), "Link on our Facebook Page", font=font("sans_sb", 30), fill="#DCE7F2", anchor="ms")
    dr.text((W / 2, 1060), "Got a tip or a question? Tell us on the site.", font=font("serif_r", 32), fill="#FFFFFF", anchor="ms")
    dr.text((W / 2, H - 120), "Free every morning by 6:30. No ads, no paywall.", font=font("sans_sb", 26), fill="#DCE7F2", anchor="ms")
    dr.text((W / 2, H - 70), f"{total} / {total}", font=font("sans_sb", 22), fill="#8DBDE3", anchor="ms")
    return im


def main():
    out = ROOT / "review/social/intro"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.jpg"):
        old.unlink()
    total = 7
    slides = []
    slides.append(sp.cover({"title": "Meet The Bay View Bulletin, Bay View's free morning paper",
                            "image": {"src": "/photos/news-south-shore-warm.jpg", "credit": "Michael Barera / Wikimedia Commons (CC BY-SA 4.0)"}},
                           LABEL, "INTRODUCING"))
    slides.append(list_slide("Every morning", "NEW BY 6:30 A.M., SEVEN DAYS A WEEK", [
        ("News", "What happened in Bay View in the last day, in plain words, with every source linked."),
        ("Events", f"{n_events} things to do in the next two weeks, from shows to holiday markets."),
        ("The Buzz", "What neighbors are talking about online, with rumors labeled as rumors."),
        ("Spotlight", "One independent Bay View business, every day."),
        ("History", "A story from the neighborhood's past, every day."),
    ], 2, total))
    slides.append(sp.story({"title": "Made for the neighborhood", "image": {"src": "/photos/bz-kk-avenue.jpg", "credit": "Michael Barera, CC BY-SA 4.0, via Wikimedia Commons"},
                            "dek": f"From the harbor to Holt Avenue, and from I-43 to the lake. Our directory lists {n_dir} local businesses and places.",
                            "kicker": "OUR COVERAGE AREA", "label_big": "Bay View", "color": LAKE}, LABEL, 3, total))
    slides.append(sp.story({"title": "Holiday guide: markets, lights and Santa", "contain": True,
                            "image": {"src": "/photos/n-christmas-on-kk-2026.jpg", "credit": "Bay View Community Center (@bayviewcentermke) on Instagram"},
                            "dek": "Christmas on KK on Dec. 11, the Dec. 7 tree lighting with Santa, pop-up markets and ways to give.",
                            "kicker": "NOW ON THE SITE", "label_big": "Holidays", "color": WARM, "more": f"{sp.SITE}/guides"}, LABEL, 4, total))
    slides.append(sp.story({"title": "What's opening, what's coming, what's closed",
                            "dek": "Our Opened & closed tracker follows every Bay View storefront change, like Radish opening Dec. 15 on Delaware Avenue.",
                            "image": {"src": "/photos/radish-dining-room.jpg", "credit": "Radish (@radish_mke) on Instagram"},
                            "kicker": "OPENED & CLOSED", "label_big": "Opened & closed", "color": WARM, "tint": WARM_SOFT,
                            "more": f"{sp.SITE}/openings"}, LABEL, 5, total))
    slides.append(sp.story({"title": "Free. No ads. No paywall.",
                            "dek": "Every story is in our own words and links to where it came from. When we get something wrong, we fix it and say so on our corrections page.",
                            "image": {"src": "/photos/hist-humboldt-park-now-2.jpg", "credit": "Rorr404 / Wikimedia Commons (CC0)"},
                            "kicker": "HOW WE WORK", "label_big": "Our promise", "color": LAKE, "tint": LAKE_SOFT}, LABEL, 6, total))
    slides.append(cta(total))
    for i, im in enumerate(slides, 1):
        im.convert("RGB").save(out / f"{i:02d}.jpg", quality=92, subsampling=0, optimize=True)
    body = ("Hello, Bay View. Meet The Bay View Bulletin, a free morning paper for our corner of Milwaukee.\n\n"
            "Every day by 6:30 a.m.:\n"
            "→ The news from Bay View, in plain words, with every source linked\n"
            f"→ Things to do ({n_events} events on the calendar for the next two weeks)\n"
            "→ The Buzz: what neighbors are talking about\n"
            "→ A local business spotlight and a story from Bay View's past\n\n"
            "Our holiday guide is up now: Christmas on KK, the tree lighting with Santa, pop-up markets and ways to give.\n\n"
            "Follow along for a quick Bay View rundown each morning and our weekend picks on Thursdays. Free, with no ads and no paywall.")
    fb = body + f"\n\nRead today's Bulletin: https://{sp.SITE}/\nGot a tip or a question? https://{sp.SITE}/ask.html"
    ig = body + "\n\nRead today's Bulletin at bayviewbulletin.com. Got a tip? Send it through the site.\n\n#BayView #BayViewMKE #Milwaukee #MKE"
    (out / "caption.txt").write_text("=== FACEBOOK ===\n" + fb + "\n\n=== INSTAGRAM ===\n" + ig + "\n")
    print("\n".join(str(p) for p in sorted(out.glob("*"))))


if __name__ == "__main__":
    main()
