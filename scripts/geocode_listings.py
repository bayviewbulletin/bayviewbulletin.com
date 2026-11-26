"""Add lat/lon to content/listings.json entries that lack them (U.S. Census geocoder, no key).
Run by the daily run after adding listings: python3 scripts/geocode_listings.py"""
import json, re, time, urllib.parse, urllib.request
from pathlib import Path
P = Path(__file__).resolve().parents[1] / "content/listings.json"
d = json.loads(P.read_text())
n = 0
for it in d.get("items", []):
    if it.get("lat"):
        continue
    a = re.sub(r"\s*\(.*?\)", "", it["address"])
    a = re.split(r"\s*[-–]\s*\d", a)[0] if re.match(r"^\d+\s*[-–]\s*\d+", a) is None else re.sub(r"^(\d+)\s*[-–]\s*\d+", r"\1", a)
    a = a.replace("S. ", "S ").replace("E. ", "E ").replace("W. ", "W ").replace("N. ", "N ").replace("Ave.", "Ave").replace("St.", "St").replace("Dr.", "Dr")
    q = urllib.parse.quote(f"{a}, Milwaukee, WI 53207")
    url = f"https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address={q}&benchmark=Public_AR_Current&format=json"
    for _ in range(2):
        try:
            m = json.load(urllib.request.urlopen(url, timeout=20))["result"]["addressMatches"]
            if m:
                it["lat"], it["lon"] = round(m[0]["coordinates"]["y"], 6), round(m[0]["coordinates"]["x"], 6)
                n += 1
            break
        except Exception:
            time.sleep(2)
P.write_text(json.dumps(d, indent=1, ensure_ascii=False))
print("geocoded", n, "missing", sum(1 for it in d["items"] if not it.get("lat")))
