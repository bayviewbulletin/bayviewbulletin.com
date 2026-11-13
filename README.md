# The Bay View Bulletin

Bay View's morning paper: bayviewbulletin.com

- `content/issues/YYYY-MM-DD.json`: one file per daily issue
- `content/directory.json`: Bay View business directory
- `build.py`: builds the static site into `docs/` (front-page layout v2; `--preview` writes to preview_v2/)
- `build_v1.py`: retired single-column layout
- `scripts/traffic.py`: yesterday's GoatCounter traffic (needs GOATCOUNTER_TOKEN; never commit the token)
- `review/`: items held for editor review (never published)

Run `python3 build.py` after adding an issue, then commit and push.
