"""Download NOAA/NCEI GHCN-Daily PRCP (COOP, CoCoRaHS, others) for stations in and around the Guadalupe basin.

Step 1 inventory: NCEI search service, bbox = basin bounds +/- 0.3 deg, any PRCP between 2007-10-02 and 2026-11-15.
Step 2 data: NCEI data service in station chunks, metric units (mm), with attributes (MFLAG, QFLAG, SFLAG, OBS_TIME)
             and station name/location.  Raw CSV chunks are saved untouched under data/raw/ghcnd/.
Resumable.  Public data, no credentials.   Usage: python scripts/fetch_ghcnd.py
Flag meanings are in data/raw/meta/ghcnd_readme.txt (NCEI readme, fetched 2026-11-22).
"""
import json
import time
from pathlib import Path

import requests

BASE = "https://www.ncei.noaa.gov/access/services"
OUT = Path("data/raw/ghcnd")
OUT.mkdir(parents=True, exist_ok=True)
START, END = "2007-10-02", "2026-11-15"
BBOX = "30.56,-100.0,29.50,-98.07"        # north,west,south,east
CHUNK = 20
BUFFER_DEG = 0.25      # ~25 km


def inventory() -> list:
    f = OUT / "inventory.json"
    if f.exists():
        return json.load(open(f))
    res, off = [], 0
    while True:
        r = requests.get(f"{BASE}/search/v1/data", params=dict(dataset="daily-summaries", bbox=BBOX, startDate=START, endDate=END,
                                                                dataTypes="PRCP", limit=500, offset=off), timeout=180).json()
        part = r.get("results", [])
        res += [{"id": x["filePath"].split("/")[-1].replace(".csv", ""), "lon": x["boundingPoints"][0]["coordinates"][0],
                 "lat": x["boundingPoints"][0]["coordinates"][1], "start": x.get("startDate"), "end": x.get("endDate")} for x in part]
        off += len(part)
        if not part or off >= r.get("count", 0):
            break
    json.dump(res, open(OUT / "inventory_bbox_all.json", "w"))
    # keep stations inside the basin polygon or within BUFFER_DEG of it (inputs for interpolation near the edges)
    from shapely.geometry import Point, shape
    basin = shape(json.load(open("data/raw/meta/basin.geojson"))["features"][0]["geometry"])
    near = basin.buffer(BUFFER_DEG)
    for s in res:
        pt = Point(s["lon"], s["lat"])
        s["inside_basin"] = bool(basin.contains(pt))
        s["dist_deg_to_basin"] = 0.0 if s["inside_basin"] else float(basin.exterior.distance(pt) if hasattr(basin, "exterior") else basin.boundary.distance(pt))
    res = [s for s in res if near.contains(Point(s["lon"], s["lat"]))]
    json.dump(res, open(f, "w"))
    return res


def main() -> None:
    inv = inventory()
    print("stations in buffered bbox with PRCP:", len(inv))
    ids = [s["id"] for s in inv]
    for i in range(0, len(ids), CHUNK):
        f = OUT / f"prcp_chunk_{i // CHUNK:03d}.csv"
        if f.exists():
            continue
        for attempt in range(5):
            try:
                r = requests.get(f"{BASE}/data/v1", params=dict(dataset="daily-summaries", stations=",".join(ids[i:i + CHUNK]), startDate=START, endDate=END,
                                                              dataTypes="PRCP", units="metric", format="csv", includeAttributes="true",
                                                              includeStationName="true", includeStationLocation="true"), timeout=300)
                if r.status_code == 200:
                    f.write_text(r.text)
                    print(f.name, len(r.text.splitlines()) - 1, "rows", flush=True)
                    break
                print("HTTP", r.status_code, "retry", attempt)
            except Exception as ex:
                print("ERR", repr(ex)[:100], "retry", attempt)
            time.sleep(5 * (attempt + 1))
    print("done")


if __name__ == "__main__":
    main()
