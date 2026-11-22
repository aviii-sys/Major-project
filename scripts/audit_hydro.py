"""Phase 0 audit of raw USGS 08167500 data. Read-only; prints a data card to stdout.

Gage height is reported by USGS in feet; thresholds in the progress report are in metres,
so we convert ft -> m (x0.3048) and report both.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

FT_TO_M = 0.3048
THRESH_M = {"high": 2.175, "extreme": 2.260}   # provisional, unverified
RISE_M_PER_H = 0.0075                           # provisional, unverified


def main(path: str) -> None:
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.sort_index()

    print("== basic ==")
    print("rows:", len(df), "| range:", df.index.min(), "->", df.index.max())
    print("duplicate timestamps:", int(df.index.duplicated().sum()))
    expected = pd.date_range(df.index.min(), df.index.max(), freq="15min")
    missing = expected.difference(df.index)
    print("expected 15-min steps:", len(expected), "| missing:", len(missing))
    if len(missing):
        gaps = pd.Series(missing).diff().ne(pd.Timedelta("15min")).cumsum()
        runs = pd.Series(missing).groupby(gaps.values).agg(["first", "size"])
        print("gap runs:", len(runs), "| longest run (steps):", int(runs["size"].max()))
        print(runs.sort_values("size", ascending=False).head(5).to_string())

    for col, name, unit in [("00065", "gage height", "ft"), ("00060", "discharge", "ft3/s")]:
        s = pd.to_numeric(df[col], errors="coerce")
        print(f"\n== {name} ({unit}) ==")
        print("nulls:", int(s.isna().sum()), "| min/median/max:", s.min(), s.median(), s.max())
        print("quantiles 50/90/99/99.9:", [round(s.quantile(q), 3) for q in (0.5, 0.9, 0.99, 0.999)])
    print("\nqualifier codes gage:", df["00065_cd"].value_counts().to_dict())

    h = pd.to_numeric(df["00065"], errors="coerce") * FT_TO_M
    print("\n== provisional thresholds (m) ==")
    for k, t in THRESH_M.items():
        above = h > t
        starts = (above & ~above.shift(fill_value=False)).sum()
        print(f"{k} {t} m: samples above={int(above.sum())} ({above.mean():.3%}), distinct crossings={int(starts)}")

    rate = h.diff() / 0.25   # m per hour (15-min step)
    print(f"rise rate > {RISE_M_PER_H} m/h: {(rate > RISE_M_PER_H).mean():.2%} of steps")
    print("rise rate quantiles 50/90/99/99.9 (m/h):", [round(rate.quantile(q), 4) for q in (0.5, 0.9, 0.99, 0.999)])
    print("max rise rate (m/h):", round(rate.max(), 3), "| max 1h rise (m):", round(h.diff(4).max(), 3))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/raw/usgs_08167500_iv_2022-01-01_2023-12-31.csv")
