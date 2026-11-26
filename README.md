> **Social posts, Nov. 26-27, 2026 (Ben, Nov. 25):** the Bulletin's first social post is an introduction carousel, already scheduled in Meta Business Suite for **Fri. Nov. 27 at 7:00 a.m.** on Facebook and Instagram (don't touch it). **Thu. Nov. 26 (Thanksgiving): no social posts**; the website publishes as usual. **Fri. Nov. 27:** post one carousel, the weekend picks (scripts/social_post.py picks it automatically), **no earlier than 7:10 a.m.**, after checking the intro is live. These come from `content/social_schedule.json`; social_post.py prints "DO NOT POST TODAY" or a "SCHEDULE NOTE" when one applies. Follow it.

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

## HISTORY BANK (Ben, Nov. 18, 2026; replaces the daily MPL archive step)
The daily run NO LONGER opens the MPL Journal/Sentinel archive (the CountyCat sign-in never lasted until 4:30 a.m.). Instead:
- **Weekly session (Sundays, about 10 a.m. Central, its own scheduled task "Bay View Bulletin: weekly history bank"):**
  - It runs while Ben is awake. He signs in to CountyCat when the session pings him.
  - It banks 10 complete history items in `content/history_bank.json`: 7 dated ones for the coming Monday through Sunday, matched "on this day" first, plus 3 undated spares.
  - It crops archive page photos into static/photos/ (labeled "(public domain)" for pre-1931 pages).
  - It fills `content/archive_research.json` with spotlight backstory, then-and-now pairs and an anniversaries calendar.
- **Daily run, history item, in this order:**
  1. The bank entry whose `run_on` is today.
  2. A spare whose subject fits (e.g. the same week or month).
  3. Free web sources: Bay View Compass back issues on Issuu (issuu.com/bayviewcompass), the Bay View Historical Society's Historian newsletter PDFs (bayviewhistoricalsociety.org/wp-content/uploads/...), Urban Milwaukee, OnMilwaukee and Milwaukee Record history pieces, Encyclopedia of Milwaukee (emke.uwm.edu), MPL's free digital photo collections (mpl.org/special_collections/images), the Wisconsin Historical Society property records, and Chronicling America.
- **Before using a banked item:** re-check its subject against content/history.json (no repeats within 365 days) and read its notes. Then move it from `dated`/`spares` to `used` with the date it ran, and append it to content/history.json as usual.
- **Spotlights:** check `archive_research.json` > `spotlight_backstory` for the day's business. For the history item's `now` line, check `then_and_now`.
- **Finish message:** say whether the history item came from the bank, a spare or the free fallback, and how many banked items are left. If fewer than 2 dated items remain for the coming days, say so.
- **Never:** type a library card number, barcode, PIN or password; use paid archives; use the library archive for current news.

## FACEBOOK PROFILE SWITCH (daily-run duty; Ben, Nov. 20, 2026)
If Facebook in Ben's Chrome is acting as a different profile or Page (on Nov. 20 it was acting as the "Milwaukee Marquee" Page, so Feeds > Pages came back empty), the daily run has Ben's permission to switch Facebook back to **Ben's own personal profile** with the Claude in Chrome tools, then read the feed as usual.
- How: open the profile menu (round profile picture, top right), choose "See all profiles", pick Ben's personal profile, then reload facebook.com/?filter=pages&sk=h_chr and check that page posts appear.
- Only switch back to Ben's personal profile. Don't switch to any other profile or Page, change settings, or post, react, follow or message.
- If the switch asks for a password, a code or any other sign-in step, stop, skip the feed and say so in the finish message. Never type credentials.
- In the finish message, say that the profile was switched and which profile or Page Facebook had been on.

## INSTAGRAM SWEEP NOTE (Nov. 21, 2026)
A handle that no longer exists makes Instagram reload the page, which kills the pushState loop. Mark each handle "tried" before visiting it, and when restarting treat a handle left at "tried" as failed (or retry it once), so the sweep moves past it. Nov. 21 fixes: Goodkind is now @goodkindbayview, McLaughlin & Hayes is @mhhatmilmke (new phone 414-210-3715); the old @bay_view_fitness and @gingerzmke accounts are gone and were removed from the directory.

## NOV. 25, 2026 UPDATES (Ben)
- **Lead and thin days:** weather leads only when a story has `"urgent": true` (snow emergency, storm warning). Non-urgent weather and `"citywide"` stories never lead. A day file can set `"lead": {"kind": "buzz" | "spotlight" | "event" | "story", "title": "..."}`; without it, on days with no leadable story, build.py leads with the first confirmed Buzz item with a real (non-stock) photo, then the spotlight, then today's event with a flyer. The right column fills with a Buzz item and today's events when there are fewer than 3 side headlines, and the "Top news" ticker hides with fewer than 3 different headlines.
- **Opened & closed tracker:** `content/openings.json` → /openings.html (More page, footer, homepage strip of the 3 newest). Entry: `{date, status: opened|coming|closing|closed|seasonal|moved|renamed, name, address, note, url, source}`.
- **City Hall this week (Mondays):** a "development" story with `"weekly": "cityhall"` is pinned at the top of the City Hall page. Story bodies can now hold bullet lists: a paragraph whose lines all start with "- ".
- **Seasonal guides:** `content/guides.json` → /guide/<slug>.html and /guides.html. Fields: slug, title, dek, tease, updated, season {start, end} (homepage tease while in season), image, intro, sections [{heading, intro, items [{name, when, where, text, url, source}]}], outro. `"status": "planned"` + `publish_by` keeps a guide off the site (listed as "coming later"). Planned: fish fry (by Feb. 10, 2027), patios and beer gardens (by May 1, 2027).
- **Event photos (Ben, Nov. 26):** an event without its own flyer shows a photo of the business itself: directory entries carry `"photo": {src, alt, credit, credit_url}` (the business's own Instagram/website photo of its space, saved as /photos/vn-<slug>.jpg; no logos, no customers' faces), matched to events by address or name in build.py (`dir_photo`) and social_post.py (`venue_photo`). Add one whenever an event venue lacks it. Seeded Nov. 26 for 17 businesses.
- **Social photos (Nov. 26):** weekend carousels use the organizer's flyer (/photos/ev-* or /photos/event-*), else the venue's directory photo when it's the business's own or Wikimedia (news outlets' photos stay off social), else a typographic panel. The weekend cover is a collage of the picks' photos (3+ needed; otherwise the first pick's photo). A venue's own promo that uses a still from the movie its event is themed on (Lost Whale's Elf pop-up) is fine; set `"social_image": false` on an event to keep its image off social. make_og.py installs `brotli` if it's missing (fresh containers lack it, and fonts won't load without it).
- **Always source photos (Ben, Nov. 26):** every social slide gets a real photo. social_post.py prints `NEEDS PHOTO` for any slide that would fall back to a text panel; fix each by adding `"social_image": {src, credit, credit_url}` to that story, Buzz item, history item or event (the business's or agency's own photo, its directory photo, Wikimedia, or the Bulletin's own), then rerun. Agencies' own graphics (WisDOT, City of Milwaukee, Milwaukee County) count as first-hand. The closing card has a large logo, an "Inside today" panel (up to 4 lines, including the in-season guide), and a follow/tip line.
- **Social posts (v2, Nov. 25 evening):** `python3 scripts/social_post.py <date> [--weekend]` writes a 4:5 carousel, review/social/<date>[-weekend]/01.jpg ... NN.jpg (cover with the lead photo and headline, story slides, a Today in Bay View events table, the Buzz, history, and a closing "read the full Bulletin" slide), plus caption.txt (FB and IG captions). Photos go on social only when they come from the business itself, Wikimedia/public domain or the Bulletin; news outlets' photos get a typographic panel instead. Posting steps are in the daily task (BUILD & PUBLISH step 5). `scripts/make_social.py` makes the profile picture and Facebook cover in static/social/.
- **Homepage spotlight (Nov. 26):** the spotlight block shows a large photo, the dek, the article's opening paragraph (up to 60 words) and three gallery photos, so it fills its column.
- **Small fixes:** weather tile reads "Now …" / "Today: …"; stock photos are captioned "Stock photo:"; event flyers have alt text; venue fallback photos are served from /photos/venues/ instead of Wikimedia; section label pages that duplicate a menu page (food-drink, city-hall, business-spotlight) redirect to it, and label pages underline the right menu item.

## REAL ESTATE (Nov. 25, 2026)

Ben's decisions: track new Bay View listings and feature them; residential and commercial; sources are agents' and brokers' own public posts and listing pages (never Zillow, Redfin, Realtor.com or Homes.com); photos only with the listing agent's OK (agents in realestate_sources.json photo_permission).

- `content/listings.json`: one entry per property. Fields: id, kind (home|condo|multi|land|commercial), deal (sale|lease|sale or lease), status (active|price_cut|pending|sold|off_market), address, price, price_num, beds, baths, sqft, note (our own words, 1-2 sentences), url (agent/broker post or listing page), listed_by (brokerage or agent), source, first_seen, last_checked, optional open_house [{date, time}], sold {date, price}, image {src, alt, credit} (credit like "Jane Doe, Shorewest, on Instagram"). Optional top-level "market": {median_list, homes_for_sale, median_days, as_of, source, url}. Update entries instead of duplicating; mark pending/sold when a listing changes; drop off_market items after 30 days.
- `content/realestate_sources.json`: where to look (brokerage pages, agents' social accounts to add as found, commercial brokers, public records).
- Site: `/real-estate.html` (menu item "Real Estate"), homepage "On the market" block (open houses this week, listings first seen in the last 7 days, price cuts; hidden when empty, and since Nov. 26 hidden until at least one home is for sale, so commercial-only lists don't show), search index. Notable sales: commercial and 4+ unit sales from scripts/records.py go in as status "sold"; never name private homeowners or buyers.
- Daily stories about real estate still go in sections.realestate (tag "Listings" keeps them off the ticker).
### Real estate tracking routine (Ben, Nov. 25: best practices)
- Daily: diff the M3 Realty Bay View listing reports (Metro MLS, refreshed nightly; homes, condos, single-family, multi-family) against content/listings.json to catch new listings, price changes, pending and back-on-market. **Lead list only (Ben, Nov. 26):** IDX data is for consumers' personal, non-commercial use, so publish a listing or change only after the listing agent or brokerage shows it on its own page or social post (or it comes through Submit your listing), and link that page, never the IDX page. If it can't be confirmed, skip it; then agents' and brokerages' Facebook/Instagram posts for open houses and "just listed" announcements.
- Weekly (Mondays): commercial brokers' pages; Wisconsin DOR property sales search (recorded sales in 53207, last 7 days); BizTimes real estate sales tracker; Urban Milwaukee's Plats and Parcels (Sundays); agent pages that post rarely (e.g. Andrew's Realty).
- Monthly: GMAR's housing report for the Milwaukee County context line.
- Dedupe by address + unit (use the MLS number as id when known). "Sold" only when the sale is recorded or the agent posts it.
- Fair housing: describe the property, never who should live there ("perfect for families", "ideal for singles", "walk to church" and similar are out).
- Photos: only from agents listed in realestate_sources.json "photo_permission" (Ben asks them); otherwise the price tile.
- Locator maps (Nov. 25): listing cards without a permitted photo show a small OpenStreetMap map with a pin (build.py `re_map`, `RE_MAPS = True` to turn on/off). Needs lat/lon: run `python3 scripts/geocode_listings.py` after adding listings (U.S. Census geocoder). Tiles load from tile.openstreetmap.org in the reader's browser, credited on each card and on the page.
- Interactive map (Ben, Nov. 26): the top of /real-estate.html has a Leaflet map of every live listing with lat/lon (build.py `re_bigmap`; blue = homes and condos, orange = commercial; pins at the same address are grouped into one popup). Ben is fine with maps on real estate; he only didn't want one for events.
- Submissions (Nov. 25): /submit-listing.html sends agents and sellers to the tip form prefilled with "Listing submission: ". Tip-sheet rows starting with that phrase are listing submissions: verify against the listing page or the M3 report, add to listings.json, and use attached photos only when the submitter chose the "Yes" photo option (that is the photo permission; credit "<agent>, <brokerage>" and add the agent to realestate_sources.json photo_permission).
- Social: Saturdays, `python3 scripts/social_post.py <date> --realestate` builds the "on the market" carousel (review/social/<date>-realestate/). Post it as a second post after the daily one, not before 9 a.m. If it exits with "No new listings…", skip it.
