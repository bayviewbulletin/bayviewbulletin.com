"""Queue a Facebook post for the Pages API publisher (scripts/fb_publish.py, run by GitHub Actions).

Usage:
  python3 scripts/social_queue.py <slides dir> <publish_at> [--stories]
    <slides dir>  a folder written by social_post.py or social_intro.py, e.g. review/social/2026-11-28
    <publish_at>  Central local time, e.g. 2026-11-28T07:00
    --stories     also queue story-01.jpg / story-02.jpg (if present) as Facebook Stories at the same time

It copies the numbered slides (01.jpg, 02.jpg, ...) and story frames into static/fb/<folder name>/ so build.py
publishes them at https://bayviewbulletin.com/fb/<folder name>/, and appends entries to content/social_queue.json
with the FACEBOOK caption from caption.txt. Then run build.py and push as usual; the workflow posts after the
site deploys. Folders older than 14 days are deleted from static/fb/. Re-queuing the same folder replaces its
entries only while they are still "queued".
"""
import datetime as dt
import json
import pathlib
import re
import shutil
import sys
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUEUE = ROOT / "content/social_queue.json"
SITE = "https://bayviewbulletin.com"


def main():
    src = pathlib.Path(sys.argv[1])
    at = dt.datetime.fromisoformat(sys.argv[2]).replace(tzinfo=ZoneInfo("America/Chicago"))
    name = src.name
    slides = sorted(p for p in src.glob("*.jpg") if re.fullmatch(r"\d\d\.jpg", p.name))
    if not slides:
        sys.exit(f"No numbered slides in {src}")
    cap = (src / "caption.txt").read_text()
    m = re.search(r"=== FACEBOOK ===\n(.*?)(?:\n=== [A-Z]+ ===|\Z)", cap, re.S)
    caption = (m.group(1) if m else cap).strip()
    dest = ROOT / "static/fb" / name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for p in slides:
        shutil.copy(p, dest / p.name)
    entries = [{"id": name, "kind": "feed", "publish_at": at.isoformat(),
                "images": [f"{SITE}/fb/{name}/{p.name}" for p in slides], "caption": caption, "status": "queued"}]
    if "--stories" in sys.argv:
        for s in ("story-01.jpg", "story-02.jpg"):
            if (src / s).exists():
                shutil.copy(src / s, dest / s)
                entries.append({"id": f"{name}-{s[:-4]}", "kind": "story", "publish_at": at.isoformat(),
                                "images": [f"{SITE}/fb/{name}/{s}"], "caption": "", "status": "queued"})
    q = json.loads(QUEUE.read_text()) if QUEUE.exists() else []
    ids = {e["id"] for e in entries}
    for x in q:
        if x["id"] in ids and x.get("status") != "queued":
            sys.exit(f"{x['id']} was already {x['status']}; not queuing it again.")
    q = [x for x in q if x["id"] not in ids] + entries
    QUEUE.write_text(json.dumps(q, indent=2, ensure_ascii=False) + "\n")
    cutoff = dt.date.today() - dt.timedelta(days=14)
    for d in (ROOT / "static/fb").iterdir():
        m = re.match(r"(\d{4}-\d\d-\d\d)", d.name)
        if d.is_dir() and m and dt.date.fromisoformat(m.group(1)) < cutoff:
            shutil.rmtree(d)
    for e in entries:
        print(f'queued {e["kind"]} {e["id"]} for {at:%a %b %d %I:%M %p} Central ({len(e["images"])} image(s))')


if __name__ == "__main__":
    main()
