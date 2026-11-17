# The Bay View Bulletin

Bay View's morning paper: bayviewbulletin.com

- `content/issues/YYYY-MM-DD.json`: one file per daily issue
- `content/directory.json`: Bay View business directory
- `build.py`: builds the static site into `docs/` (front-page layout v2; `--preview` writes to preview_v2/)
- `build_v1.py`: retired single-column layout
- `scripts/check_repeats.py`: flags stories, Buzz items and events that repeat earlier days (run before every publish)
- `content/x_sources.json`: Ben's private X list and the daily X searches (Nov. 17)
- `scripts/records.py`: public-records leads for Bay View (Legistar files, District 14 liquor licenses, property sales, building permits); run each morning, verify before publishing
- `scripts/traffic.py`: yesterday's GoatCounter traffic (needs GOATCOUNTER_TOKEN; never commit the token)
- `review/`: items held for editor review (never published)

Run `python3 build.py` after adding an issue, then commit and push.

Story fields (optional): `correction` (text shown as a Correction note on the story and listed on /corrections.html), `correction_type: "update"` to label it Update instead, `updated` (YYYY-MM-DD, used as dateModified).

Site basics written by build.py (Nov. 17): 404.html, feed.xml (RSS), sitemap.xml, robots.txt, NewsArticle structured data on story pages, Event structured data on events.html.

Day fields (optional, Nov. 17): `briefing` = 3-5 items [{text, url}] for the homepage "Bay View in 60 seconds" box (if omitted, build.py writes one from the weather, lead story, tonight's event, top Buzz item and spotlight). The homepage also shows "This weekend" events automatically, "Earlier this week" stories on thin days (fewer than 6 news stories), and a smaller photo when the lead story is a Safety story.

Events and Buzz (Nov. 17): build.py writes events.ics (a subscribable calendar of every listed event), one .ics file per event in /ics/ with Apple/Outlook and Google "Add to calendar" links, and dated tiles in the event type's color for events without a flyer (no more hotlinked stock venue photos). buzz.html shows the last 7 days; every day's Buzz also has its own page at /buzz/<date>.html, linked from "Earlier Buzz".

Content features (Nov. 17): `content/explainers.json` holds evergreen explainers (slug, title, dek, updated, topic, body, links, optional image), built at /explainer/<slug>.html and listed on /explainers.html; a story links one with `"explainer": "<slug>"`. /weekend.html lists every weekend event, plus the editor's picks from a day file's `weekend` field ({intro, picks: [{title, why}]}, titles matching event titles). /ask.html invites reader questions (the tip form prefilled with "Ask the Bulletin: "); stories with `"ask": true` are labeled Ask the Bulletin and listed there.
