"""Fetch station metadata used by Phase 0 (all public, no credentials):
  - USGS site info (expanded) and data-series catalogue
  - USGS NLDI upstream basin polygon (GeoJSON)
  - NWS NWPS gauge record (official flood categories, historic crests)
  - USGS annual peak streamflow record (peak date, discharge, gage height)
Saved untouched under data/raw/meta/.
"""
import warnings
from pathlib import Path

import requests

warnings.filterwarnings("ignore")
import dataretrieval.nwis as nwis  # noqa: E402

SITE = "08167500"
OUT = Path("data/raw/meta")

URLS = {
    "site_info.rdb": f"https://waterservices.usgs.gov/nwis/site/?format=rdb&sites={SITE}&siteOutput=expanded",
    "series_catalog.rdb": f"https://waterservices.usgs.gov/nwis/site/?format=rdb&sites={SITE}&seriesCatalogOutput=true",
    "basin.geojson": f"https://api.water.usgs.gov/nldi/linked-data/nwissite/USGS-{SITE}/basin",
    "nws_gauge.json": f"https://api.water.noaa.gov/nwps/v1/gauges/{SITE}",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, url in URLS.items():
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        (OUT / name).write_bytes(r.content)
        print(f"{name}: {len(r.content)} bytes")
    peaks, _ = nwis.get_discharge_peaks(sites=SITE)
    peaks.to_csv(OUT / "annual_peaks.csv")
    print("annual_peaks.csv:", len(peaks), "rows")


if __name__ == "__main__":
    main()
