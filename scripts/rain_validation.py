"""Validate ERA5 (Open-Meteo) rainfall against independent gauge observations.

Part A  timestamp semantics + hourly skill: USGS tipping-bucket rain gauges (param 00045) inside/near the
        basin vs the ERA5 0.25-degree cell containing each gauge. Lagged Pearson r on hourly totals; the lag
        with the highest r tells whether ERA5's hourly label is the END (lag 0) or START (lag +1/-1) of the hour.
Part B  the anomalous events (2015-05-24, 2016-05-30): NOAA/NCEI daily gauge totals (GHCN-D incl. CoCoRaHS)
        for stations inside the basin polygon vs ERA5, day by day.

Outputs: reports/rain_validation/*.csv|md.   Gauge data cached under data/raw/rain_gauges/.
Daily gauge totals have station-specific observation times (typically ~7 am local = ~12-13 UTC); both a 12 UTC
and a local-calendar-day ERA5 aggregation are shown so the reader can see that conclusions do not hinge on it.
"""
import io
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from shapely.geometry import Point, shape

warnings.filterwarnings("ignore")
import dataretrieval.nwis as nwis  # noqa: E402

RAW = Path("data/raw")
CACHE = RAW / "rain_gauges"
OUT = Path("reports/rain_validation")
for p in (CACHE, OUT):
    p.mkdir(parents=True, exist_ok=True)
BASIN = shape(json.load(open(RAW / "meta/basin.geojson"))["features"][0]["geometry"])


def era5_cell(lat: float, lon: float) -> pd.Series:
    la, lo = round(lat / 0.25) * 0.25, round(lon / 0.25) * 0.25
    d = RAW / "era5_precip" / f"{la:g}_{lo:g}".replace("_", "_")
    cand = [RAW / "era5_precip" / f"{la}_{lo}", RAW / "era5_precip" / f"{la:.2f}_{lo:.2f}".rstrip("0")]
    d = next((c for c in cand if c.exists()), None)
    if d is None:  # fall back to csv strings used when cells were fetched
        cells = pd.read_csv(RAW / "meta/era5_cells.csv", dtype=str)
        cells["dist"] = (cells.lat.astype(float) - lat) ** 2 + (cells.lon.astype(float) - lon) ** 2
        r = cells.sort_values("dist").iloc[0]
        d = RAW / "era5_precip" / f"{r.lat}_{r.lon}"
    df = pd.concat([pd.read_csv(f) for f in sorted(d.glob("*.csv"))])
    df["time"] = pd.to_datetime(df.time, utc=True)
    s = df.drop_duplicates("time").set_index("time").sort_index().precipitation
    s.attrs["cell"] = d.name
    return s


def basin_era5() -> pd.Series:
    cells = pd.read_csv(RAW / "meta/era5_cells.csv", dtype=str)
    ser = {}
    for r in cells.itertuples():
        df = pd.concat([pd.read_csv(f) for f in sorted((RAW / "era5_precip" / f"{r.lat}_{r.lon}").glob("*.csv"))])
        df["time"] = pd.to_datetime(df.time, utc=True)
        ser[r.Index] = df.drop_duplicates("time").set_index("time").precipitation
    w = cells.area_km2.astype(float).values
    wide = pd.DataFrame(ser)
    return (wide * w).sum(axis=1) / w.sum()


# ------------------------------------------------------------------ Part A
def part_a() -> None:
    sites = {"08165500": "Guadalupe Rv at Hunt", "08166000": "Johnson Ck nr Ingram"}
    txt = requests.get(f"https://waterservices.usgs.gov/nwis/site/?format=rdb&sites={','.join(sites)}", timeout=60).text
    lines = [ln for ln in txt.splitlines() if ln and not ln.startswith("#")]
    info = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[2:])), sep="\t", dtype=str)   # drop the RDB width row
    rows, lagrows = [], []
    for _, s in info.iterrows():
        lat, lon = float(s.dec_lat_va), float(s.dec_long_va)
        f = CACHE / f"usgs_{s.site_no}_00045.csv"
        if not f.exists():
            start = "2023-11-21" if s.site_no == "08165500" else "2025-05-12"
            d, _ = nwis.get_iv(sites=s.site_no, start=start, end="2026-11-22", parameterCd="00045")
            d.to_csv(f)
        g = pd.read_csv(f, index_col=0)
        g.index = pd.to_datetime(g.index, utc=True)
        col = [c for c in g.columns if c.startswith("00045") and not c.endswith("_cd")][0]
        inc = pd.to_numeric(g[col], errors="coerce") * 25.4          # inches -> mm
        step = g.index.to_series().diff().dropna().mode().iloc[0]
        # hourly total labelled by END of hour: (H-1h, H]  -> label H
        hourly = inc.resample("1h", label="right", closed="right").sum(min_count=1)
        era = era5_cell(lat, lon)
        both = pd.concat([hourly.rename("gauge"), era.rename("era5")], axis=1).dropna()
        n_wet = int((both.gauge > 0.5).sum())
        for lag in range(-6, 7):
            e = era.shift(-lag)  # lag>0: ERA5 label is `lag` hours EARLIER than the gauge hour label
            b = pd.concat([hourly.rename("gauge"), e.rename("era5")], axis=1).dropna()
            lagrows.append(dict(site=s.site_no, name=sites[s.site_no], lag_h=lag, n=len(b), pearson_r=float(b.gauge.corr(b.era5))))
        dd = both.resample("D").sum()
        rows.append(dict(site=s.site_no, name=sites[s.site_no], lat=lat, lon=lon, era5_cell=era.attrs["cell"], gauge_step=str(step),
                         hours=len(both), wet_hours_gauge_gt0_5mm=n_wet, gauge_total_mm=float(both.gauge.sum()), era5_total_mm=float(both.era5.sum()),
                         daily_r=float(dd.gauge.corr(dd.era5)), inside_basin=bool(BASIN.contains(Point(lon, lat)))))
    pd.DataFrame(rows).to_csv(OUT / "partA_gauge_summary.csv", index=False)
    lg = pd.DataFrame(lagrows)
    lg.to_csv(OUT / "partA_lag_correlation.csv", index=False)
    (OUT / "partA_lag_correlation.md").write_text(lg.pivot(index="lag_h", columns="name", values="pearson_r").round(3).to_markdown())
    print(pd.DataFrame(rows).to_string(index=False))
    print(lg.pivot(index="lag_h", columns="name", values="pearson_r").round(3).to_string())


def part_a2() -> None:
    """Episode timing: centroid time of rainfall (gauge vs ERA5) inside each wet episode (gauge 24 h total >= 40 mm)."""
    rows = []
    for f, name in [(CACHE / "usgs_08165500_00045.csv", "Hunt"), (CACHE / "usgs_08166000_00045.csv", "Johnson Ck")]:
        g = pd.read_csv(f, index_col=0)
        g.index = pd.to_datetime(g.index, utc=True)
        col = [c for c in g.columns if c.startswith("00045") and not c.endswith("_cd")][0]
        hourly = (pd.to_numeric(g[col], errors="coerce") * 25.4).resample("1h", label="right", closed="right").sum(min_count=1)
        era = era5_cell(30.07, -99.30)
        r24 = hourly.rolling(24, min_periods=20).sum().dropna().sort_values(ascending=False)
        chosen = []
        for t, v in r24.items():
            if v < 40:
                break
            if all(abs((t - c).total_seconds()) > 72 * 3600 for c in chosen):
                chosen.append(t)
        for t in chosen:
            w = slice(t - pd.Timedelta("23h"), t)
            gw, ew = hourly.loc[w], era.reindex(hourly.loc[w].index)
            if gw.isna().mean() > 0.2 or ew.sum() < 5:
                rows.append(dict(gauge=name, end=t, gauge_24h_mm=float(gw.sum()), era5_24h_mm=float(ew.sum()), centroid_lag_h=np.nan))
                continue
            hrs = np.arange(len(gw))
            cg = float((gw.fillna(0).values * hrs).sum() / gw.fillna(0).sum())
            ce = float((ew.fillna(0).values * hrs).sum() / ew.fillna(0).sum())
            rows.append(dict(gauge=name, end=t, gauge_24h_mm=float(gw.sum()), era5_24h_mm=float(ew.sum()), centroid_lag_h=ce - cg))
    d = pd.DataFrame(rows)
    d.to_csv(OUT / "partA2_episode_timing.csv", index=False)
    print(d.round(1).to_string(index=False))
    v = d.centroid_lag_h.dropna()
    print(f"episodes with usable timing: {len(v)} | median lag ERA5-gauge (h): {v.median():.1f} | IQR: {v.quantile(.25):.1f} to {v.quantile(.75):.1f}")


# ------------------------------------------------------------------ Part B
def part_b() -> None:
    base = "https://www.ncei.noaa.gov/access/services"
    ids = set()
    windows = {"E01_2015-05": ("2015-05-19", "2015-05-27"), "E03_2016-05": ("2016-05-26", "2016-06-03")}
    for a, b in windows.values():
        r = requests.get(f"{base}/search/v1/data", params=dict(dataset="daily-summaries", bbox="30.40,-99.85,29.70,-98.25", startDate=a,
                                                                endDate=b, dataTypes="PRCP", limit=500), timeout=120).json()
        for x in r.get("results", []):
            c = x["boundingPoints"][0]["coordinates"]
            if BASIN.contains(Point(c[0], c[1])):
                ids.add((x["filePath"].split("/")[-1].replace(".csv", ""), c[1], c[0]))
    st = pd.DataFrame(sorted(ids), columns=["station", "lat", "lon"])
    st.to_csv(OUT / "partB_stations_in_basin.csv", index=False)
    print("stations inside basin with PRCP in event windows:", len(st))
    era_b = basin_era5()
    out = []
    for label, (a, b) in windows.items():
        f = CACHE / f"ncei_{label}.csv"
        if not f.exists():
            r = requests.get(f"{base}/data/v1", params=dict(dataset="daily-summaries", stations=",".join(st.station), startDate=a, endDate=b,
                                                          dataTypes="PRCP", units="metric", format="csv"), timeout=180)
            f.write_text(r.text)
        d = pd.read_csv(f)
        d["DATE"] = pd.to_datetime(d.DATE)
        d = d.merge(st, left_on="STATION", right_on="station")
        day = d.groupby("DATE").PRCP.agg(n_gauges="count", gauge_mean_mm="mean", gauge_max_mm="max", n_ge25mm=lambda x: int((x >= 25).sum()))
        tab = day.copy()
        for D in tab.index:
            end12 = pd.Timestamp(D, tz="UTC") + pd.Timedelta("12h")
            tab.loc[D, "era5_basin_mm_24h_end12UTC"] = era_b.loc[end12 - pd.Timedelta("23h"):end12].sum()
            loc0 = pd.Timestamp(D, tz="UTC") + pd.Timedelta("6h")     # local calendar day CST (UTC-6)
            tab.loc[D, "era5_basin_mm_localday_CST"] = era_b.loc[loc0:loc0 + pd.Timedelta("23h")].sum()
        tab.insert(0, "event", label)
        out.append(tab.reset_index())
        print(label); print(tab.round(1).to_string())
    pd.concat(out).to_csv(OUT / "partB_daily_gauges_vs_era5.csv", index=False)
    (OUT / "partB_daily_gauges_vs_era5.md").write_text(pd.concat(out).round(1).to_markdown(index=False))


if __name__ == "__main__":
    part_a()
    part_b()
