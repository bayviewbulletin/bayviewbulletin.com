"""Sunday "This week in Bay View" Reel (Ben, Nov. 27, 2026): a 9:16 slideshow video of the week's best social-safe photos.

    python3 scripts/social_reel.py 2026-11-29

Reads the last 7 day files (Mon-Sun ending on <date>) and takes each day's lead story, plus the week's spotlights and the
weekend picks' photos, using only photos allowed on social (social_post.photo_ok: the business's own, Wikimedia/public
domain, agencies or the Bulletin). Never held items, Safety stories or unconfirmed Buzz. Writes review/social/<date>-reel/
reel.mp4 (1080x1920, 30 fps, 15-30 s, silent audio track, kept under 3.7 MB for the upload), cover.jpg (the Reel cover) and caption.txt.
Post it as a Reel to Facebook at about 6 p.m. Sunday (schedule it in Business Suite's Create reel composer).
The video carries a silent track; music is added in the composer's Edit > Audio step from Meta's licensed library
(Ben, Nov. 27: an upbeat instrumental, no vocals). Instagram can't add music to a Reel after it's posted.
"""
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import social_post as sp  # noqa: E402
from social_post import ROOT, W, cover, cta, photo_ok, si, stories, story_frame, fb_link_line  # noqa: E402

SEC = 2.6   # seconds per photo
FADE = 0.5
# Claude in Chrome's file_upload takes at most 3.8 MB per call (found Nov. 27: a 16 s Reel at CRF 20 was 6.4 MB),
# so the bitrate is set from the length to land near VIDEO_BUDGET_MB.
VIDEO_BUDGET_MB = 3.2
MAX_MB = 3.7


def week_items(end):
    items = []
    for i in range(6, -1, -1):
        day = end - dt.timedelta(days=i)
        f = ROOT / f"content/issues/{day.isoformat()}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        label = day.strftime("%A").upper()
        news = [(k, s) for k, s in stories(d) if k != "spotlight" and photo_ok(si(s)) and not s.get("citywide")]
        if news:
            items.append((label, news[0][1]["title"], si(news[0][1])))
        spot = next((s for k, s in stories(d) if k == "spotlight"), None)
        if spot and day.weekday() == 2:
            pic = next((g for g in [spot.get("image")] + spot.get("gallery", []) if photo_ok(g)), None)
            if pic:
                items.append(("SPOTLIGHT", spot["title"].replace("Spotlight: ", ""), pic))
    seen, out = set(), []
    for it in items:
        if it[2]["src"] not in seen:
            seen.add(it[2]["src"])
            out.append(it)
    return out[:9]


def main():
    end = dt.date.fromisoformat(sys.argv[1])
    items = week_items(end)
    if len(items) < 4:
        sys.exit(f"Only {len(items)} social-safe photos this week; skip the Reel.")
    out = ROOT / "review/social" / f"{end.isoformat()}-reel"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*"):
        old.unlink()
    date_label = f"Week of {(end - dt.timedelta(days=6)).strftime('%b. ')}{(end - dt.timedelta(days=6)).day}"
    frames = []
    for n, (label, title, pic) in enumerate(items, 1):
        im = cover({"title": title, "image": pic, "footer": "bayviewbulletin.com"}, date_label, label)
        fr = story_frame(im, "THIS WEEK IN BAY VIEW", "Follow for Bay View news every morning")
        p = out / f"f{n:02d}.jpg"
        fr.save(p, quality=92)
        frames.append(p)
    end_card = story_frame(cta(["Bay View's morning paper", "Free every morning by 6:30"], len(items) + 1),
                           "THIS WEEK IN BAY VIEW", "bayviewbulletin.com")
    p = out / f"f{len(items) + 1:02d}.jpg"
    end_card.save(p, quality=92)
    frames.append(p)
    (out / "cover.jpg").write_bytes(frames[0].read_bytes())

    # ffmpeg: each still with a slow push-in, chained with crossfades, plus a silent stereo track
    args, filters = ["ffmpeg", "-y", "-loglevel", "error"], []
    for i, f in enumerate(frames):
        args += ["-loop", "1", "-t", str(SEC + FADE), "-i", str(f)]
        filters.append(f"[{i}:v]scale=1188:2112,zoompan=z='min(zoom+0.0006,1.06)':d={int((SEC + FADE) * 30)}:"
                       f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x1920:fps=30,setsar=1,format=yuv420p[v{i}]")
    last, off = "v0", 0.0
    for i in range(1, len(frames)):
        off += SEC
        filters.append(f"[{last}][v{i}]xfade=transition=fade:duration={FADE}:offset={off:.2f}[x{i}]")
        last = f"x{i}"
    total = SEC * len(frames) + FADE
    vbr = max(600, min(3000, int(VIDEO_BUDGET_MB * 8000 / total) - 70))  # kbit/s
    args += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
             "-filter_complex", ";".join(filters), "-map", f"[{last}]", "-map", f"{len(frames)}:a",
             "-c:v", "libx264", "-preset", "veryfast", "-b:v", f"{vbr}k", "-maxrate", f"{int(vbr * 1.2)}k",
             "-bufsize", f"{vbr * 2}k", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "64k", "-shortest",
             "-movflags", "+faststart", str(out / "reel.mp4")]
    subprocess.run(args, check=True)
    mb = (out / "reel.mp4").stat().st_size / 1e6
    if mb > MAX_MB:
        sys.exit(f"reel.mp4 is {mb:.1f} MB, over the {MAX_MB} MB upload limit; lower VIDEO_BUDGET_MB and rerun.")
    for f in frames:
        f.unlink()

    lines = "\n".join(f"→ {'Spotlight: ' if lb == 'SPOTLIGHT' else ''}{t}" for lb, t, _ in items)
    body = f"This week in Bay View, Milwaukee:\n{lines}"
    fb = body + "\n\n" + fb_link_line("The Bulletin is free every morning.")[0]
    (out / "caption.txt").write_text("=== FACEBOOK ===\n" + fb + "\n")  # Facebook only since Nov. 27
    print("\n".join(str(p) for p in [out / "reel.mp4", out / "cover.jpg", out / "caption.txt"]))


if __name__ == "__main__":
    main()
