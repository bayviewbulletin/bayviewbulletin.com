"""Public-records leads for Bay View (Ben, Nov. 17, 2026).

Pulls recent items from free city sources and prints a Markdown report of leads for the daily run.
These are LEADS, not stories: verify each one (the Legistar file, the city record, the business's
own post or news coverage) before anything runs, and never publish private homeowners' names.

Sources (all reachable from the workspace shell, no keys):
  1. Common Council / committees: Legistar Web API (webapi.legistar.com/v1/milwaukee): files introduced
     recently whose titles mention the 14th Aldermanic District or Bay View streets and places.
  2. Liquor licenses (data.milwaukee.gov "liquorlicenses", updated daily): Aldermanic District 14 licenses
     with a recent effective date; trade names not in content/directory.json are flagged as new-business leads.
  3. Property sales (MPROP, data.milwaukee.gov "mprop", updated daily but conveyances lag a few weeks):
     District 14 commercial, industrial and 4+ unit parcels with a recent conveyance. The price is estimated
     from the Wisconsin transfer fee ($3 per $1,000). Owner names are shown only for companies.
  4. Building permits (data.milwaukee.gov "buildingpermits"): permits on District 14 addresses with a recent
     issue date and a cost of $50,000+ or a new-construction/raze/commercial type. This dataset can lag months.

Usage: python3 scripts/records.py [--days 14] [--out path.md] [--json path.json]
"""
import argparse
import datetime as dt
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "BayViewBulletin/1.0 (bayviewbulletin.com)"}
CKAN = "https://data.milwaukee.gov/api/3/action/"
MPROP = "0a2c7f31-cd15-4151-8222-09dd57d5f16d"
LIQUOR = "45c027b5-fa66-4de2-aa7e-d9314292093d"
PERMITS = "828e9630-d7cb-42e4-960e-964eae916397"
LEGISTAR = "https://webapi.legistar.com/v1/milwaukee/"

BAY_VIEW_TERMS = [
    r"14th Aldermanic", r"Bay View", r"Bayview", r"Kinnickinnic", r"\bKK\b", r"Humboldt Park", r"South Shore", r"Jones Island",
    r"Hoan", r"Howell Av", r"Delaware Av", r"Logan Av", r"Superior St", r"Clement Av", r"Wentworth", r"Lenox St", r"Chase Av",
    r"Graham St", r"Allis St", r"Kinnickinnic River", r"Beulah Brinton", r"Port Milwaukee", r"Fernwood", r"Tippecanoe",
    # east-west streets also run on the far West Side, so require "E."/"East"
    r"(?:\bE\.?|East)\s+(?:Lincoln|Bay|Russell|Oklahoma|Potter|Ward|Pryor|Ellen|Archer|Dover|Iron|Texas|Morgan|Holt|Euclid|Smith|Montana|Conway|Homer|Rosedale|Linus|Deer|Nock|Otjen|Manitoba|Clement|Ontario|Estes|Bennett|Lunham|Idaho|Wilbur|Herman|Fernwood)\b",
]
TERMS_RE = re.compile("|".join(BAY_VIEW_TERMS), re.I)


def get_json(url, tries=2):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:  # noqa: BLE001
            err = ex
    raise err


def sql(q):
    return get_json(CKAN + "datastore_search_sql?sql=" + urllib.parse.quote(q))["result"]["records"]


def legistar(since):
    url = LEGISTAR + "matters?$filter=" + urllib.parse.quote(f"MatterIntroDate ge datetime'{since.isoformat()}'") + "&$top=1000"
    out = []
    for m in get_json(url):
        title = m.get("MatterTitle") or ""
        if not TERMS_RE.search(title):
            continue
        intro = (m.get("MatterIntroDate") or "")[:10]
        if intro > (dt.date.today() + dt.timedelta(days=60)).isoformat():  # a few records carry typo dates
            continue
        out.append({"file": m.get("MatterFile"), "type": m.get("MatterTypeName"), "status": m.get("MatterStatusName"),
                    "body": m.get("MatterBodyName"), "intro": intro, "title": title,
                    "url": f"https://milwaukee.legistar.com/LegislationDetail.aspx?ID={m['MatterId']}&GUID={m['MatterGuid']}"})
    return sorted(out, key=lambda x: x["intro"], reverse=True)


def outside(addr):
    """Rough check for District 14 addresses west of I-43 (outside the Bulletin's coverage area)."""
    a = addr.upper()
    m = re.search(r"\bS\s+(\d+)(?:ST|ND|RD|TH)\s+(?:ST|PL)\b", a)
    if m and int(m.group(1)) >= 6:
        return True
    m = re.match(r"(\d+)(?:-\d+)?\s+W\s+", a)
    return bool(m and int(m.group(1)) >= 600)


def tag(addr):
    return " (likely outside coverage: west of I-43)" if outside(addr) else ""


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def liquor(since, directory_names):
    rows = sql(f'SELECT * FROM "{LIQUOR}" WHERE "ALDERMANIC_DISTRICT"=\'14\' AND "EFF_DATE" >= \'{since.isoformat()}\' ORDER BY "EFF_DATE" DESC')
    out = []
    for r in rows:
        name = (r.get("TRADE_NAME") or r.get("CORP_NAME") or "").strip()
        known = any(norm(name)[:8] and (norm(name)[:8] in dn or dn[:8] in norm(name)) for dn in directory_names)
        addr = " ".join(x for x in [r.get("HOUSE_NR"), r.get("SDIR"), r.get("STREET"), r.get("STTYPE")] if x)
        out.append({"name": name.title(), "corp": (r.get("CORP_NAME") or "").title(), "address": addr.title(), "type": r.get("License Type Full Name") or r.get("LIC_TYPE"),
                    "effective": r.get("EFF_DATE"), "in_directory": known})
    return out


def sales(since):
    q = (f'SELECT "TAXKEY","HOUSE_NR_LO","HOUSE_NR_HI","SDIR","STREET","STTYPE","CONVEY_DATE","CONVEY_TYPE","CONVEY_FEE","C_A_CLASS","NR_UNITS","LAND_USE_GP","OWNER_NAME_1","C_A_TOTAL" '
         f'FROM "{MPROP}" WHERE "GEO_ALDER"=\'14\' AND "CONVEY_DATE" >= \'{since.isoformat()}\' ORDER BY "CONVEY_DATE" DESC')
    out = []
    for r in sql(q):
        units = int(float(r.get("NR_UNITS") or 0))
        cls = (r.get("C_A_CLASS") or "").strip()
        fee = float(r.get("CONVEY_FEE") or 0)
        owner = (r.get("OWNER_NAME_1") or "").strip()
        company = bool(re.search(r"\b(LLC|INC|CORP|CO|COMPANY|LP|LLP|PARTNERS|PROPERTIES|HOLDINGS|INVESTMENTS|DEVELOPMENT|GROUP|CHURCH|CITY OF|COUNTY|AUTHORITY|ASSOCIATION|FOUNDATION)\b\.?", owner))
        if not (cls in ("2", "3") or units >= 4 or company):  # skip ordinary homes bought by private owners
            continue
        hi =r.get("HOUSE_NR_HI")
        num = r.get("HOUSE_NR_LO") + (f"-{hi}" if hi and hi != r.get("HOUSE_NR_LO") else "")
        out.append({"address": " ".join(x for x in [num, r.get("SDIR"), r.get("STREET"), r.get("STTYPE")] if x).title(),
                    "date": (r.get("CONVEY_DATE") or "")[:10], "deed": r.get("CONVEY_TYPE"), "est_price": round(fee / 0.003) if fee else None,
                    "assessed": int(float(r.get("C_A_TOTAL") or 0)), "units": units, "class": {"1": "residential", "2": "commercial", "3": "manufacturing"}.get(cls, "class " + (cls or "?")),
                    "buyer": owner.title() if company else "(private owner, not shown)", "taxkey": r.get("TAXKEY")})
    return out


def d14_addresses():
    rows = sql(f'SELECT "HOUSE_NR_LO","HOUSE_NR_HI","SDIR","STREET" FROM "{MPROP}" WHERE "GEO_ALDER"=\'14\'')
    keys = set()
    for r in rows:
        try:
            lo, hi = int(r["HOUSE_NR_LO"]), int(r.get("HOUSE_NR_HI") or r["HOUSE_NR_LO"])
        except (TypeError, ValueError):
            continue
        for n in range(lo, min(hi, lo + 40) + 1):
            keys.add(f'{n} {r.get("SDIR") or ""} {r.get("STREET") or ""}'.upper())
    return keys


def permits(since, addrs):
    rows = sql(f'SELECT * FROM "{PERMITS}" WHERE "Date Issued" >= \'{since.isoformat()}\' ORDER BY "Date Issued" DESC')
    out = []
    for r in rows:
        a = (r.get("Address") or "").split(",")[0].upper()
        m = re.match(r"(\d+)\s+([NSEW])\s+(\S+(?:\s\S+)*?)\s+(?:AV|AVE|ST|PL|CT|DR|BL|BLVD|WY|LA|LN|RD|TR|TER|PK|PKWY|CR|SQ)\b", a)
        if not m or f"{m.group(1)} {m.group(2)} {m.group(3)}" not in addrs:
            continue
        cost = float(r.get("Construction Total Cost") or 0)
        ptype = r.get("Permit Type") or ""
        if cost < 50000 and not re.search(r"New|Raze|Wreck|Commercial", ptype, re.I):
            continue
        out.append({"address": a.title(), "type": ptype, "status": r.get("Status"), "issued": (r.get("Date Issued") or "")[:10],
                    "cost": cost, "use": r.get("Use of Building"), "units": r.get("Dwelling units impact"), "record": r.get("Record ID")})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--out")
    ap.add_argument("--json")
    a = ap.parse_args()
    today = dt.date.today()
    since = today - dt.timedelta(days=a.days)
    names = [norm(b["name"]) for b in json.loads((ROOT / "content/directory.json").read_text())]
    report, data, errors = [], {}, []

    def section(key, fn, *args):
        try:
            data[key] = fn(*args)
        except Exception as ex:  # noqa: BLE001
            data[key] = []
            errors.append(f"{key}: {ex}")

    section("legistar", legistar, since)
    section("liquor", liquor, today - dt.timedelta(days=max(a.days, 30)), names)
    section("sales", sales, today - dt.timedelta(days=max(a.days, 60)))
    try:
        addrs = d14_addresses()
        section("permits", permits, today - dt.timedelta(days=max(a.days, 60)), addrs)
    except Exception as ex:  # noqa: BLE001
        data["permits"] = []
        errors.append(f"permits: {ex}")

    report.append(f"# Bay View public-records leads ({today.isoformat()})\n")
    report.append("Leads only: verify before running. Don't publish private homeowners' names.\n")
    report.append(f"## Common Council and committees: files introduced since {since} ({len(data['legistar'])})")
    for m in data["legistar"]:
        report.append(f"- **{m['file']}** ({m['type']}, {m['status']}, {m['body']}, introduced {m['intro']}): {m['title'][:300]}  \n  {m['url']}")
    report.append(f"\n## Liquor licenses in District 14 effective in the last {max(a.days, 30)} days ({len(data['liquor'])})")
    for x in data["liquor"]:
        flag = "" if x["in_directory"] else " **[not in directory: possible new business]**"
        report.append(f"- {x['name']} ({x['corp']}), {x['address']}{tag(x['address'])}: {x['type']}, effective {x['effective']}{'' if outside(x['address']) else flag}")
    report.append(f"\n## Property sales in District 14, commercial or 4+ units, last {max(a.days, 60)} days ({len(data['sales'])})")
    report.append("MPROP conveyances lag a few weeks behind the actual sale. Price is estimated from the transfer fee.")
    for x in data["sales"]:
        price = f"about ${x['est_price']:,}" if x["est_price"] else "no transfer fee (non-sale deed)"
        report.append(f"- {x['address']}{tag(x['address'])} ({x['class']}, {x['units']} units, assessed ${x['assessed']:,}): {x['deed']} {x['date']}, {price}; buyer: {x['buyer']}")
    report.append(f"\n## Building permits on District 14 addresses, last {max(a.days, 60)} days ({len(data['permits'])})")
    report.append("This dataset can lag months; treat it as background.")
    for x in data["permits"]:
        report.append(f"- {x['address']}{tag(x['address'])}: {x['type']} ({x['status']}, issued {x['issued']}), ${x['cost']:,.0f}, use {x['use'] or '?'} {('· units ' + x['units']) if x['units'] else ''} [{x['record']}]")
    if errors:
        report.append("\n## Errors\n" + "\n".join("- " + e for e in errors))
    text = "\n".join(report) + "\n"
    if a.out:
        Path(a.out).write_text(text)
    if a.json:
        Path(a.json).write_text(json.dumps(data, indent=1, ensure_ascii=False))
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
