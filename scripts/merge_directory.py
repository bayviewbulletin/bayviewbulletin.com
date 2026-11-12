import json, re, time, urllib.parse, urllib.request
known = json.loads(open('scripts/geo_cache.json').read())
new = [b for b in json.load(open('scripts/new_businesses.json')) if b["address"]]
dirs = json.load(open('content/directory.json'))
def key(a): return re.sub(r'\.', '', a).replace('S ', 'S ').strip()
def census(a):
    q = urllib.parse.quote(a + ", Milwaukee, WI 53207")
    u = f"https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address={q}&benchmark=Public_AR_Current&format=json"
    for _ in range(4):
        try:
            m = json.load(urllib.request.urlopen(u, timeout=30))["result"]["addressMatches"]; break
        except Exception: time.sleep(2)
    else: return None
    return [round(m[0]["coordinates"]["y"], 5), round(m[0]["coordinates"]["x"], 5)] if m else None
have = {b["name"].lower() for b in dirs}
added = 0
for b in new:
    if b["name"].lower() in have: continue
    k = key(b["address"])
    ll = known.get(k)
    if not isinstance(ll, list):
        ll = census(k); time.sleep(0.3)
    if ll: b["lat"], b["lon"] = ll
    dirs.append(b); added += 1
for b in dirs:
    if b["name"].startswith("Avalon"): b["address"] = "2473 S. Kinnickinnic Ave."; b.pop("verify", None)
    if b["name"].startswith("Catrina"): b["verify"] = True   # 2352 S. KK is Odd Duck's address
    if not b.get("lat"):
        try:
            ll = census(key(b["address"]))
            if ll: b["lat"], b["lon"] = ll
        except Exception: pass
dirs.sort(key=lambda b: b["name"].lower().removeprefix("the "))
json.dump(dirs, open('content/directory.json', 'w'), indent=1, ensure_ascii=False)
print("added", added, "total", len(dirs), "geocoded", sum(1 for b in dirs if b.get("lat")))
print("no coords:", [b["name"] for b in dirs if not b.get("lat")])
