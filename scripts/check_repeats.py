#!/usr/bin/env python3
"""Flag stories, Buzz items and events in an issue that repeat earlier days.

Usage: python3 scripts/check_repeats.py [YYYY-MM-DD]   (default: newest issue)

Checks the issue against every earlier issue for:
  - stories and Buzz items with the same source_url or a similar title/body
  - duplicate events inside the issue (same day and similar title or same link)
Exits 1 when anything is found, so the daily run can fix it before publishing.
Spotlights are skipped (they are checked against content/spotlights.json).
"""
import glob
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
files = sorted(glob.glob(str(ROOT / "content/issues/*.json")))
target = next((f for f in files if sys.argv[1:] and sys.argv[1] in f), files[-1])
earlier = [f for f in files if f < target]


def items(d):
    out = []
    for b in d.get("buzz", []):
        out.append(("buzz", b["headline"], b.get("source_url", ""), b.get("body", "")))
    for s, its in d.get("sections", {}).items():
        if s == "spotlight":
            continue
        for i in its:
            out.append((s, i["title"], i.get("source_url", ""), i.get("body", "")))
    return out


def words(t):
    return set(re.findall(r"[a-z]{5,}", t.lower()))


today = json.load(open(target))
mine = items(today)
problems = []
for f in earlier:
    for k, t, u, b in items(json.load(open(f))):
        for k2, t2, u2, b2 in mine:
            same_url = bool(u) and u == u2
            ratio = SequenceMatcher(None, t.lower(), t2.lower()).ratio()
            overlap = len(words(b) & words(b2)) / max(1, min(len(words(b)), len(words(b2))))
            if same_url or ratio > 0.6 or overlap > 0.45:
                problems.append(f"REPEAT {k2}: '{t2}'\n    ran {Path(f).stem} ({k}): '{t}'"
                                f"  [same link: {same_url}, title {ratio:.2f}, body overlap {overlap:.2f}]")

ev = today.get("events", [])
for i, a in enumerate(ev):
    for b in ev[i + 1:]:
        if a["day"].replace("Today, ", "") != b["day"].replace("Today, ", ""):
            continue
        same_place = a.get("where", "").split(",")[0] == b.get("where", "").split(",")[0]
        if a.get("link") and a.get("link") == b.get("link") or \
                same_place and SequenceMatcher(None, a["title"].lower(), b["title"].lower()).ratio() > 0.6:
            problems.append(f"DUPLICATE EVENT {a['day']}: '{a['title']}' / '{b['title']}'")

print(f"Checked {Path(target).stem} against {len(earlier)} earlier issue(s).")
print("\n".join(problems) if problems else "No repeats found.")
sys.exit(1 if problems else 0)
