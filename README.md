# The Bay View Bulletin

Bay View's morning paper: bayviewbulletin.com

- `content/issues/YYYY-MM-DD.json`: one file per daily issue
- `content/directory.json`: Bay View business directory
- `build.py`: builds the static site into `docs/` (front-page layout v2; `--preview` writes to preview_v2/)
- `build_v1.py`: retired single-column layout
- `scripts/post_check.py`: post-publish check of the live site (images that could be upgraded, dead links, rule slips, phone/desktop layout); run after every push, fix, re-push
- `scripts/check_repeats.py`: flags stories, Buzz items and events that repeat earlier days (run before every publish)
- `content/x_sources.json`: Ben's private X list and the daily X searches (Nov. 17)
- `scripts/records.py`: public-records leads for Bay View (Legistar files, District 14 liquor licenses, property sales, building permits); run each morning, verify before publishing
- `scripts/traffic.py`: yesterday's GoatCounter traffic (needs GOATCOUNTER_TOKEN; never commit the token)
- `review/`: items held for editor review (never published)

Run `python3 build.py` after adding an issue, then commit and push.

Story fields (optional): `correction` (text shown as a Correction note on the story and listed on /corrections.html), `correction_type: "update"` to label it Update instead, `updated` (YYYY-MM-DD, used as dateModified).

Site basics written by build.py (Nov. 17): 404.html, feed.xml (RSS), sitemap.xml, robots.txt, NewsArticle structured data on story pages, Event structured data on events.html.

Day fields (optional, Nov. 17): `briefing` = 3-5 items [{text, url}] for the homepage "Bay View in 60 seconds" box (if omitted, build.py writes one from the weather, lead story, tonight's event, top Buzz item and spotlight). The homepage also shows "This weekend" events automatically, "Earlier this week" stories on thin days (fewer than 6 news stories), and a smaller photo when the lead story is a Safety story.

Events and Buzz (Nov. 17): build.py writes events.ics (a subscribable calendar of every listed event), one .ics file per event in /ics/ with Apple/Outlook and Google "Add to calendar" links,. Events without a flyer show a venue photo (Ben, Nov. 17: no text tiles). buzz.html shows the last 7 days; every day's Buzz also has its own page at /buzz/<date>.html, linked from "Earlier Buzz".

Content features (Nov. 17): `content/explainers.json` holds evergreen explainers (slug, title, dek, updated, topic, body, links, optional image), built at /explainer/<slug>.html and listed on /explainers.html; a story links one with `"explainer": "<slug>"`. /weekend.html lists every weekend event, plus the editor's picks from a day file's `weekend` field ({intro, picks: [{title, why}]}, titles matching event titles). /ask.html invites reader questions (the tip form prefilled with "Ask the Bulletin: "); stories with `"ask": true` are labeled Ask the Bulletin and listed there.

Back end (Nov. 17): `scripts/weather.py` (NWS API weather tile + alerts), `scripts/site_check.py` (run after build; also runs in GitHub Actions on every push), `.github/workflows/uptime.yml` (hourly: site up, HTTPS valid for 14+ days, today's edition published after 7 a.m. Central). build.py writes 640 px phone copies of photos to /photos/sm/ with srcset. The private admin dashboard lives on claude.ai, not in this public repo.

## POST-PUBLISH CHECK (daily-run duty; Ben, Nov. 18, 2026)
This step is part of the daily task. It runs right after the push in BUILD & PUBLISH and before the finish message, and it overrides the older rules noted below.

1. **Wait for the deploy.** Poll https://bayviewbulletin.com/ until it shows today's date (GitHub Pages usually takes 1-2 minutes).
2. **Run the checker:** `python3 scripts/post_check.py <date> --shots <scratchpad>/post`. It reports four parts: LIVE (pages and images return 200), IMAGES (stock photos, Facebook Buzz posts, events on the venue fallback, with any og:image it finds on the event's link), LINKS AND RULES (dead source links, deks of 120+ characters, event descs and kinds, long quotes, Buzz credits), and LAYOUT (phone 390 px and desktop 1280 px screenshots, broken images, horizontal scroll). Look at the screenshots yourself.
3. **Re-read every published item against the standing rules**, not only what the script flags: no repeats, quotes under 15 words with at most one per source, no private names, Buzz credit format, freshness (the publish date is on the page), and facts (dates, times, addresses, names) checked against the source.
4. **Upgrade images, in this priority order.** First the lead story and the other top stories, then the Buzz, then the spotlight, then events (today's and the weekend's first).
   - **Events (every one on the venue fallback):** try the event link's og:image, then the organizer's and performers' Instagram posts, then the venue's own post about the event. Use what fits after a contact-sheet look.
   - **Film screenings (Ben, Nov. 18):** a screening may use the organizer's or venue's promo image even when it's a still from the movie, credited to that page. Example: the Nov. 18 Hanksgiving 'Burbs screening uses Milwaukee Record's image. Movie stills are still rejected for anything else.
   - **Facebook posts in public groups (Ben, Nov. 18; this overrides the old "Facebook photos can't be used" Buzz rule).** For a Buzz item from a public-group post, use the post's own photo when it shows no people or faces, no minors, no license plates and no house numbers.
     - Open the post in Chrome and click the photo to open the viewer.
     - Move the mouse off the image, then capture it with the computer tool's `zoom` and `save_to_disk`.
     - Convert it to JPEG in static/photos/.
     - Credit "<First name> <last initial>. via Bay View Town Hall (Facebook)" and set credit_url to the post.
     - Examples (Nov. 18): the Lime scooter in the Humboldt Park lagoon, and the Pup Stand on Oklahoma.
     - Don't use the Chrome tool to fetch the image URL itself; screenshots only.
   - Stock photos stay the last resort.
5. **Fix and re-push.** Fix anything clear-cut right away: a better photo, a broken link, a typo, a dek that's too long, a rule slip. For a fact that was wrong in a published story, use the corrections fields. Then re-run check_repeats.py, build.py and site_check.py, commit ("Bay View Bulletin: <date> post-publish fixes") and push.
6. **Time limit: 6:15 a.m. Central.** Work in the priority order above until 6:15. Anything left unchecked goes in the report.
7. **Report.**
   - **Finish message:** add a short "Post-publish check" section listing what was checked, what was fixed (e.g. "3 photos upgraded, 1 dead link removed") and what's left.
   - **Admin dashboard:** add these fields to today's runs.json row: `post_images_upgraded`, `post_links_fixed`, `post_rule_fixes`, `post_layout_issues`, `post_left` (the number of problems still open).
