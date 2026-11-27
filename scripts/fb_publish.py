"""Publish queued Facebook Page posts through Meta's official Pages API (Graph API).

Ben, Nov. 27, 2026: after the Bulletin's Instagram account was disabled, posting moves off browser automation
in Business Suite and onto Meta's sanctioned API, so no browser ever acts in Ben's personal Facebook account.

Runs in GitHub Actions (.github/workflows/facebook.yml) with two repository secrets:
  FB_PAGE_ID     the Bulletin Page's numeric id
  FB_PAGE_TOKEN  a long-lived Page access token (pages_manage_posts, pages_read_engagement)
Without them it prints a note and exits 0, so nothing breaks before setup.

Queue: content/social_queue.json, a list of entries the daily run appends:
  {"id": "2026-11-28", "kind": "feed" | "story", "publish_at": "2026-11-28T07:00:00-06:00",
   "images": ["https://bayviewbulletin.com/social/2026-11-28/01.jpg", ...], "caption": "...",
   "status": "queued"}
Images must already be live on the site (the daily run copies slides to docs/social/<id>/ and pushes first).

feed:  published now if publish_at is under 11 minutes away, otherwise scheduled with scheduled_publish_time
       (Meta allows 10 minutes to 30 days ahead). Photos are uploaded unpublished with temporary=true, then
       attached to one multi-photo post.
story: Meta can't schedule Stories, so a story is published by the first workflow run at or after publish_at
       (one image per story, via /photo_stories).
Each entry gets status "scheduled" / "published" / "error" plus post_id or error, written back to the queue.
Entries older than 14 days are dropped. Never posts the same entry twice.
"""
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUEUE = ROOT / "content/social_queue.json"
API = "https://graph.facebook.com/v25.0"


def call(path, **params):
    params["access_token"] = os.environ["FB_PAGE_TOKEN"]
    data = urllib.parse.urlencode(params).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{API}/{path}", data=data), timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()[:500]) from None


def upload_photo(page, url, scheduled):
    p = {"url": url, "published": "false"}
    if scheduled:
        p["temporary"] = "true"
    return call(f"{page}/photos", **p)["id"]


def live(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=20) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    page, token = os.environ.get("FB_PAGE_ID"), os.environ.get("FB_PAGE_TOKEN")
    if not (page and token):
        print("FB_PAGE_ID / FB_PAGE_TOKEN not set: Pages API publishing isn't set up yet. Nothing posted.")
        return 0
    q = json.loads(QUEUE.read_text()) if QUEUE.exists() else []
    now = dt.datetime.now(dt.timezone.utc)
    q = [x for x in q if dt.datetime.fromisoformat(x["publish_at"]) > now - dt.timedelta(days=14)]
    changed, failed = False, False
    for x in q:
        if x.get("status") != "queued":
            continue
        at = dt.datetime.fromisoformat(x["publish_at"])
        if not all(live(u) for u in x["images"]):
            print(f'{x["id"]} {x["kind"]}: images not live on the site yet; will try on the next run')
            continue
        try:
            if x["kind"] == "feed":
                sched = at - now > dt.timedelta(minutes=11)
                ids = [upload_photo(page, u, sched) for u in x["images"]]
                p = {"message": x["caption"]}
                for i, mid in enumerate(ids):
                    p[f"attached_media[{i}]"] = json.dumps({"media_fbid": mid})
                if sched:
                    p.update(published="false", scheduled_publish_time=str(int(at.timestamp())))
                x["post_id"] = call(f"{page}/feed", **p)["id"]
                x["status"] = "scheduled" if sched else "published"
            elif x["kind"] == "story":
                if at > now:
                    continue
                pid = upload_photo(page, x["images"][0], False)
                x["post_id"] = call(f"{page}/photo_stories", photo_id=pid).get("post_id", pid)
                x["status"] = "published"
            else:
                raise RuntimeError(f"unknown kind {x['kind']}")
        except Exception as e:  # report and keep going; never retry automatically
            x["status"], x["error"] = "error", str(e)
            failed = True
        x["done_at"] = now.isoformat(timespec="seconds")
        changed = True
        print(f'{x["id"]} {x["kind"]}: {x["status"]} {x.get("post_id", x.get("error", ""))}')
    if changed:
        QUEUE.write_text(json.dumps(q, indent=2, ensure_ascii=False) + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
