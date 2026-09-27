"""Aggregate data/ships.csv into the JSON files the website reads (docs/data/)."""
import datetime as dt
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import parse

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data"

SOUTH_ASIA = {"India", "Bangladesh", "Pakistan"}
REGIONS = ["South Asia", "Turkey", "China", "Rest of world"]
CATEGORIES = ["Bulk carrier", "Tanker", "Container", "General cargo",
              "Offshore & drilling", "Passenger & Ro-Ro", "Fishing", "Other"]
GT_FROM = 2014  # gross tonnage is only reported from the 2014 list onwards

# Yard locations (lon, lat). Ships at places not listed here fall back to the
# destination country's centroid on the map.
PLACES = {
    "Alang": (72.17, 21.40), "Chattogram": (91.70, 22.45), "Aliağa": (26.93, 38.80),
    "Gadani": (66.73, 25.12), "Jiangyin": (120.27, 31.91), "Xinhui": (113.03, 22.46),
    "Zhangjiagang": (120.55, 31.88), "Mumbai": (72.84, 18.95), "Grenaa": (10.93, 56.41),
    "Zhoushan": (122.20, 29.99), "Brownsville": (-97.40, 25.95), "Ghent": (3.73, 51.10),
    "Busan": (129.04, 35.10), "Esbjerg": (8.45, 55.47), "Ningde": (119.53, 26.66),
    "Surabaya": (112.73, -7.20), "Stokksund": (10.05, 64.03), "Port Colborne": (-79.25, 42.88),
    "Dalian": (121.61, 38.91), "Jiangmen": (113.08, 22.58), "Kolkata": (88.33, 22.55),
    "Frederikshavn": (10.54, 57.44), "Shidao": (122.43, 36.88), "Xingang": (117.73, 38.97),
    "Klaipeda": (21.13, 55.71), "Bojonegara": (106.08, -5.97), "Guayaquil": (-79.88, -2.20),
    "Jingjiang": (120.27, 32.01), "Gijon": (-5.66, 43.54), "Hanoytangen": (5.14, 60.53),
    "Taizhou": (121.42, 28.66), "Shanghai": (121.49, 31.23), "Brest": (-4.49, 48.38),
    "Batam": (104.03, 1.08), "Jakarta": (106.85, -6.10), "Liepaja": (21.01, 56.51),
    "Lagos": (3.39, 6.44), "Leith": (-3.17, 55.98), "Le Havre": (0.11, 49.49),
    "Murmansk": (33.08, 68.97), "Feda": (6.80, 58.26), "Gaogang": (119.87, 32.32),
    "Sachana": (70.02, 22.58), "Gravendeel": (4.62, 51.78), "Colon": (-79.90, 9.36),
    "Ulsteinvik": (5.85, 62.34), "Bilbao": (-3.04, 43.33), "Chongming": (121.40, 31.62),
    "Wenzhou": (120.67, 27.99), "Mokpo": (126.39, 34.79), "Montevideo": (-56.21, -34.90),
}


def region(country):
    if country in SOUTH_ASIA:
        return "South Asia"
    if country in ("Turkey", "China"):
        return country
    return "Rest of world"


def quartiles(values):
    if len(values) < 4:
        return None
    q = statistics.quantiles(values, n=4)
    return [round(q[0], 1), round(statistics.median(values), 1), round(q[2], 1)]


def top(counter, n):
    return [k for k, _ in counter.most_common(n) if k]


def build(ships):
    years = sorted({s["year"] for s in ships})
    by_year = defaultdict(list)
    for s in ships:
        s["region"] = region(s["country"])
        by_year[s["year"]].append(s)

    # --- the headline index + per-year breakdowns -------------------------
    annual = []
    for y in years:
        ys = by_year[y]
        reg = Counter(s["region"] for s in ys)
        cat = Counter(s["category"] for s in ys)
        ages = [s["age"] for s in ys if s["age"] != ""]
        gts = [(s["gt"], s["region"]) for s in ys if s["gt"] != ""]
        foc = [s for s in ys if s["flag"] and s["owner_country"]]
        row = {
            "year": y,
            "ships": len(ys),
            "regions": {r: reg[r] for r in REGIONS},
            "categories": {c: cat[c] for c in CATEGORIES},
            "age": quartiles(ages),
            "flag_mismatch": round(sum(s["flag"] != s["owner_country"] for s in foc) / len(foc), 3),
            "gt": None, "gt_regions": None,
        }
        if y >= GT_FROM:
            row["gt"] = sum(g for g, _ in gts)
            row["gt_regions"] = {r: sum(g for g, rr in gts if rr == r) for r in REGIONS}
        annual.append(row)

    # --- where ships go ---------------------------------------------------
    place_tot = Counter()
    unplaced = Counter()
    for s in ships:
        if s["place"] in PLACES:
            place_tot[(s["place"], s["country"])] += 1
        elif s["country"]:
            unplaced[s["country"]] += 1
    yards = [{"name": p, "country": c, "ships": n, "lon": PLACES[p][0], "lat": PLACES[p][1]}
             for (p, c), n in place_tot.most_common()]
    countries_other = [{"country": c, "ships": n} for c, n in unplaced.most_common()]

    dest = Counter(s["country"] for s in ships if s["country"])
    dest_top = top(dest, 8)
    destinations = [{"country": c, "ships": dest[c],
                     "by_year": [sum(1 for s in by_year[y] if s["country"] == c) for y in years]}
                    for c in dest_top]

    # --- who sends them: owner country x destination region --------------
    owners = Counter(s["owner_country"] for s in ships if s["owner_country"])
    owner_rows = []
    for o in top(owners, 15):
        os_ = [s for s in ships if s["owner_country"] == o]
        reg = Counter(s["region"] for s in os_)
        owner_rows.append({"country": o, "ships": len(os_), "regions": {r: reg[r] for r in REGIONS}})

    # --- flags of the final voyage ----------------------------------------
    flags = Counter(s["flag"] for s in ships if s["flag"])
    flag_rows = []
    for f in top(flags, 12):
        fs = [s for s in ships if s["flag"] == f]
        own = sum(1 for s in fs if s["owner_country"] == f)
        flag_rows.append({"flag": f, "ships": len(fs), "south_asia": sum(s["region"] == "South Asia" for s in fs),
                          "home_owned": own})

    # --- age by category --------------------------------------------------
    cat_age = []
    for c in CATEGORIES:
        ages = [s["age"] for s in ships if s["category"] == c and s["age"] != ""]
        cat_age.append({"category": c, "ships": len(ages), "age": quartiles(ages)})

    # --- records ----------------------------------------------------------
    aged = [s for s in ships if s["age"] != ""]
    with_gt = [s for s in ships if s["gt"] != ""]

    def card(s):
        return {k: s[k] for k in ("name", "imo", "type_raw", "year", "built", "age", "gt", "flag",
                                  "owner_country", "place", "country")}

    latest = years[-1]
    ly = by_year[latest]
    records = {
        "oldest": card(max(aged, key=lambda s: s["age"])),
        "youngest": card(min(aged, key=lambda s: (s["age"], -int(s["gt"] or 0)))),
        "largest": card(max(with_gt, key=lambda s: s["gt"])),
    }

    total_sa = sum(s["region"] == "South Asia" for s in ships)
    stats = {
        "generated": data_date(),
        "years": [years[0], latest],
        "gt_from": GT_FROM,
        "regions": REGIONS,
        "categories": CATEGORIES,
        "totals": {
            "ships": len(ships),
            "south_asia": total_sa,
            "south_asia_share": round(total_sa / len(ships), 3),
            "median_age": statistics.median(s["age"] for s in aged),
            "gt": sum(s["gt"] for s in with_gt),
            "owner_countries": len(owners),
            "flags": len(flags),
            "destinations": len(dest),
        },
        "latest": {
            "year": latest,
            "ships": len(ly),
            "south_asia_share": round(sum(s["region"] == "South Asia" for s in ly) / len(ly), 3),
            "top_owner": Counter(s["owner_country"] for s in ly if s["owner_country"]).most_common(1)[0],
            "top_yard": Counter(s["place"] for s in ly if s["place"]).most_common(1)[0],
            "top_flag": Counter(s["flag"] for s in ly if s["flag"]).most_common(1)[0],
        },
        "annual": annual,
        "yards": yards,
        "countries_other": countries_other,
        "destinations": destinations,
        "owners": owner_rows,
        "flags": flag_rows,
        "category_age": cat_age,
        "records": records,
    }

    # Compact ship register for the searchable logbook.
    cols = ["year", "imo", "name", "category", "type_raw", "gt", "built", "flag", "owner_country", "place", "country"]
    register = {"columns": cols, "rows": [[s[c] for c in cols] for s in
                                          sorted(ships, key=lambda s: (-s["year"], s["name"]))]}
    return stats, register


def sanity_check(ships):
    """Refuse to publish if a list looks truncated or mis-parsed."""
    per_year = Counter(s["year"] for s in ships)
    for year, n in sorted(per_year.items()):
        if n < 100:
            raise SystemExit(f"build: only {n} ships parsed for {year}; refusing to publish")
    for field in ("imo", "country", "built"):
        share = sum(1 for s in ships if s[field] != "") / len(ships)
        if share < 0.9:
            raise SystemExit(f"build: field '{field}' filled for only {share:.0%} of ships; refusing to publish")


def data_date():
    """Date the newest list was downloaded (so an unchanged dataset builds identically)."""
    manifest = ROOT / "data" / "sources.json"
    if manifest.exists():
        return max(v["fetched"] for v in json.loads(manifest.read_text()).values())
    return dt.date.today().isoformat()


def main():
    ships = parse.main()
    sanity_check(ships)
    stats, register = build(ships)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "ships.json").write_text(json.dumps(register, ensure_ascii=False, separators=(",", ":")),
                                    encoding="utf-8")
    print(f"build: {stats['totals']['ships']} ships, {stats['years'][0]}-{stats['years'][1]} -> docs/data/")


if __name__ == "__main__":
    main()
