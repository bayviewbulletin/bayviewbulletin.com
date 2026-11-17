"""Weather tile for the daily issue, from the National Weather Service API (no key, works from the workspace shell).

Prints JSON for utilities.weather: {"v": "36° · Fair", "s": "Sunny, high near 55 · SW wind 10-15 mph", "href": ...}
plus any active alerts for the Bay View point (lakeshore flood, wind, winter storm...), which can become a news item.
Usage: python3 scripts/weather.py
"""
import json
import re
import urllib.request

LAT, LON = 42.99, -87.89
HREF = f"https://forecast.weather.gov/MapClick.php?lat={LAT}&lon={LON}"
UA = {"User-Agent": "BayViewBulletin/1.0 (bayviewbulletin.com)", "Accept": "application/geo+json"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    pt = get(f"https://api.weather.gov/points/{LAT},{LON}")["properties"]
    periods = get(pt["forecast"])["properties"]["periods"]
    now_v = None
    try:
        st = get(pt["observationStations"])["features"][0]["properties"]["stationIdentifier"]
        ob = get(f"https://api.weather.gov/stations/{st}/observations/latest")["properties"]
        c = ob["temperature"]["value"]
        if c is not None:
            now_v = f'{round(c * 9 / 5 + 32)}° · {ob.get("textDescription") or periods[0]["shortForecast"]}'
    except Exception:
        pass
    p0 = periods[0]
    if not now_v:
        now_v = f'{p0["temperature"]}° · {p0["shortForecast"]}'
    day = next((p for p in periods[:2] if p["isDaytime"]), p0)
    night = next((p for p in periods[:3] if not p["isDaytime"]), None)
    first = re.split(r"\. ", day["detailedForecast"])[0].rstrip(".")
    hi = f'high near {day["temperature"]}' if "high" not in first.lower() else ""
    s = first + (f", {hi}" if hi and day["isDaytime"] else "") + f' · {day["windDirection"]} wind {day["windSpeed"]}'
    out = {"v": now_v, "s": s.replace(" to ", "-").replace(" mph", " mph"), "href": HREF}
    alerts = get(f"https://api.weather.gov/alerts/active?point={LAT},{LON}")["features"]
    print(json.dumps({"weather": out, "tonight": night and night["detailedForecast"],
                      "alerts": [{"event": a["properties"]["event"], "headline": a["properties"]["headline"], "ends": a["properties"].get("ends")} for a in alerts]}, indent=1))


if __name__ == "__main__":
    main()
