#!/usr/bin/env python3
"""Print yesterday's bayviewbulletin.com traffic from GoatCounter.

Usage: GOATCOUNTER_TOKEN=... python3 scripts/traffic.py [YYYY-MM-DD]
The token is read-only (Read statistics). Never commit it to the repo.
With no date, reports yesterday (Central time). On Mondays it also prints
the past 7 days, day by day.
"""
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

BASE = "https://bayviewbulletin.goatcounter.com/api/v0"
TOKEN = os.environ.get("GOATCOUNTER_TOKEN", "")


def get(path, **params):
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}",
                                               "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def total(day):
    d = day.isoformat()
    return get("/stats/total", start=d, end=d).get("total", 0)


def main():
    if not TOKEN:
        sys.exit("GOATCOUNTER_TOKEN is not set")
    today = dt.datetime.now(ZoneInfo("America/Chicago")).date()
    day = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else today - dt.timedelta(days=1)
    d = day.isoformat()

    print(f"Traffic for {day:%a. %b. %-d, %Y}: {total(day)} visitors")

    hits = get("/stats/hits", start=d, end=d, limit=5).get("hits", [])
    pages = [h for h in hits if not h.get("event")]
    if pages:
        print("Top pages:")
        for h in pages[:5]:
            print(f"  {h.get('count', 0):>4}  {h.get('title') or h.get('path')}  ({h.get('path')})")

    refs = get("/stats/toprefs", start=d, end=d, limit=5).get("stats", [])
    if refs:
        print("Where they came from:")
        for r in refs[:5]:
            print(f"  {r.get('count', 0):>4}  {r.get('name') or '(direct / unknown)'}")

    if day.weekday() == 6:  # report for Sunday = Monday morning's run
        print("Past 7 days:")
        week = []
        for i in range(6, -1, -1):
            x = day - dt.timedelta(days=i)
            n = total(x)
            week.append(n)
            print(f"  {x:%a %b %-d}: {n}")
        print(f"  Week total: {sum(week)}")


if __name__ == "__main__":
    main()
