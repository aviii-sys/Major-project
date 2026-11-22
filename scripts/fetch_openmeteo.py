"""Fetch hourly ERA5-Land (via Open-Meteo archive API) for every 0.1-degree cell that overlaps the
upstream basin of USGS 08167500 (cells + area weights in data/raw/meta/era5land_cells.csv,
built from the USGS NLDI basin polygon).

Raw, per-cell, per-year CSVs go to data/raw/era5land/. Nothing is averaged here; basin-average
is computed later from the saved cells using the area weights. Resumable: existing files skipped.
Stops cleanly if Open-Meteo reports a rate/quota limit so it can be re-run later.

Attribution: Open-Meteo.com (CC BY 4.0); contains modified Copernicus Climate Change Service
information (ERA5-Land). Free API is for non-commercial use.

Usage: python scripts/fetch_openmeteo.py --dataset {precip,land} --start 2007-10-02 --end 2026-11-15
"""
import argparse
import csv
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

URL = "https://archive-api.open-meteo.com/v1/archive"
# Open-Meteo's era5_land model returns NO precipitation (verified: 100% null), so rainfall comes
# from the plain ERA5 model (native ~0.25 deg) and land-surface variables from ERA5-Land (0.1 deg).
DATASETS = {
    "land": dict(model="era5_land", cells="data/raw/meta/era5land_cells.csv", out="data/raw/era5land",
                 vars=["temperature_2m", "relative_humidity_2m", "soil_moisture_0_to_7cm",
                       "soil_moisture_7_to_28cm", "soil_moisture_28_to_100cm"]),
    "precip": dict(model="era5", cells="data/raw/meta/era5_cells.csv", out="data/raw/era5_precip",
                   vars=["precipitation"]),
}


class QuotaExceeded(Exception):
    pass


def fetch(lat, lon, start, end, cfg):
    params = dict(latitude=lat, longitude=lon, start_date=start, end_date=end,
                  hourly=",".join(cfg["vars"]), models=cfg["model"], timezone="UTC")
    for attempt in range(6):
        r = requests.get(URL, params=params, timeout=120)
        if r.status_code == 200:
            h = r.json()["hourly"]
            return pd.DataFrame(h)
        reason = ""
        try:
            reason = r.json().get("reason", "")
        except Exception:
            pass
        if r.status_code == 429 or "limit" in reason.lower():
            if "daily" in reason.lower():
                raise QuotaExceeded(reason)
            wait = 70 if "minute" in reason.lower() else 600
            print(f"  rate limited ({reason[:80]}); sleeping {wait}s", flush=True)
            time.sleep(wait)
            continue
        raise RuntimeError(f"HTTP {r.status_code}: {reason or r.text[:200]}")
    raise RuntimeError("too many retries")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2007-10-02")
    ap.add_argument("--end", default=str(date.today()))
    ap.add_argument("--dataset", choices=list(DATASETS), required=True)
    ap.add_argument("--max-cells", type=int, default=None)
    args = ap.parse_args()

    cfg = DATASETS[args.dataset]
    cells = list(csv.DictReader(open(cfg["cells"])))[: args.max_cells]
    s, e = date.fromisoformat(args.start), date.fromisoformat(args.end)
    out = Path(cfg["out"])
    n_new = 0
    for c in cells:
        d = out / f"{c['lat']}_{c['lon']}"
        d.mkdir(parents=True, exist_ok=True)
        for y in range(s.year, e.year + 1):
            ys, ye = max(s, date(y, 1, 1)), min(e, date(y, 12, 31))
            path = d / f"{y}.csv"
            if path.exists():
                continue
            try:
                df = fetch(c["lat"], c["lon"], str(ys), str(ye), cfg)
            except QuotaExceeded as ex:
                print("QUOTA EXCEEDED:", ex, "- re-run later to resume.")
                return
            df.to_csv(path, index=False)
            n_new += 1
            time.sleep(0.2)
        print(f"cell {c['lat']},{c['lon']} done", flush=True)
    print("new files:", n_new)


if __name__ == "__main__":
    main()
