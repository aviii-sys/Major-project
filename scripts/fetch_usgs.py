"""Fetch USGS instantaneous values (IV) for station 08167500 in yearly chunks.

Saves each chunk untouched (values + qualifier codes) to data/raw/usgs_iv/ so the run is
resumable and reproducible. Existing chunks are skipped unless --force.

Usage: python scripts/fetch_usgs.py --start 2007-10-02 [--end YYYY-MM-DD]
"""
import argparse
import warnings
from datetime import date
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
import dataretrieval.nwis as nwis  # noqa: E402

SITE = "08167500"
PARAMS = ["00065", "00060"]  # gage height (ft), discharge (ft3/s)


def chunks(start: date, end: date):
    s = start
    while s <= end:
        e = min(date(s.year, 12, 31), end)
        yield s, e
        s = date(s.year + 1, 1, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2007-10-02")
    ap.add_argument("--end", default=str(date.today()))
    ap.add_argument("--out", default="data/raw/usgs_iv")
    ap.add_argument("--params", default=",".join(PARAMS), help="comma-separated USGS parameter codes")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    params = args.params.split(",")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for s, e in chunks(date.fromisoformat(args.start), date.fromisoformat(args.end)):
        path = out / f"iv_{SITE}_{s}_{e}.csv"
        # re-fetch the current (incomplete) year every time
        if path.exists() and not args.force and e < date.today():
            print("skip", path.name)
            continue
        try:
            df, _ = nwis.get_iv(sites=SITE, start=str(s), end=str(e), parameterCd=params)
        except Exception as ex:  # keep going, record failure
            print("FAILED", s, e, repr(ex)[:200])
            continue
        df.to_csv(path)
        print(f"{path.name}: {len(df)} rows", "" if len(df) == 0 else f"({df.index.min()} -> {df.index.max()})")


if __name__ == "__main__":
    main()
