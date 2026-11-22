"""Build a NOAA gauge-based DAILY basin rainfall product for the USGS 08167500 upstream basin.

Input : data/raw/ghcnd/prcp_chunk_*.csv   (GHCN-Daily PRCP in mm, attributes MFLAG,QFLAG,SFLAG,OBS_TIME)
Output: data/processed/gauge_basin_daily.csv, reports/gauge_rainfall/{tables,figures}

Quality screening (flag meanings: data/raw/meta/ghcnd_readme.txt)
  * value dropped if missing/negative, if QFLAG is non-blank (any failed NCEI quality check, incl. 'L' multi-day length),
    or if MFLAG is 'P' (missing presumed zero) or 'I' (no precipitation data reported). MFLAG 'T' (trace) and 'H' are kept as 0 mm and counted.
  * Observation-time families: the PRIMARY product uses only stations whose OBS_TIME is 0600-0900 local (daily total = 24 h ending
    ~7-8 am local). Stations with other or unknown OBS_TIME (e.g. midnight airport stations) are excluded from the primary product and counted.
Spatial method: inverse-distance weighting onto a 0.05-degree grid of the basin, chosen (power p, neighbours k; radius 60 km) by
  LEAVE-ONE-STATION-OUT cross-validation on wet station-days (>= 5 mm), compared with the simple mean of reporting stations and nearest-station.
Temporal alignment: product day D = 24 h ending ~7-8 am local on D. It is NOT available before 15:00 UTC on day D (conservative cutoff for 9 am CST).
Units: mm.  All dates are observation dates (local), stored as dates.
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from shapely.geometry import Point, shape

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAW = Path("data/raw")
OUT = Path("reports/gauge_rainfall")
TAB, FIG = OUT / "tables", OUT / "figures"
for p in (TAB, FIG, Path("data/processed")):
    p.mkdir(parents=True, exist_ok=True)
RMAX_KM, WET_MM = 60.0, 5.0
GRID_P, GRID_K = (1, 2, 3), (4, 8, 12)
BASIN = shape(json.load(open(RAW / "meta/basin.geojson"))["features"][0]["geometry"])
C = dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#e6e5e1", s1="#2a78d6", s2="#eb6834")
plt.rcParams.update({"figure.facecolor": C["surface"], "axes.facecolor": C["surface"], "savefig.facecolor": C["surface"], "axes.edgecolor": C["grid"],
                     "axes.labelcolor": C["ink2"], "text.color": C["ink"], "xtick.color": C["ink2"], "ytick.color": C["ink2"], "axes.grid": True,
                     "grid.color": C["grid"], "axes.spines.top": False, "axes.spines.right": False, "font.size": 9, "axes.titleweight": "bold",
                     "axes.titlelocation": "left"})
NOTES: dict = {}


def md(df, name, index=False):
    df.to_csv(TAB / f"{name}.csv", index=index)
    (TAB / f"{name}.md").write_text(df.to_markdown(index=index, floatfmt=".3g"))


def load() -> pd.DataFrame:
    d = pd.concat([pd.read_csv(f) for f in sorted((RAW / "ghcnd").glob("prcp_chunk_*.csv"))])
    d["DATE"] = pd.to_datetime(d.DATE)
    a = d.PRCP_ATTRIBUTES.fillna(",,,").astype(str).str.split(",", expand=True).reindex(columns=range(4))
    for i, c in enumerate(["MFLAG", "QFLAG", "SFLAG", "OBS"]):
        d[c] = a[i].fillna("").str.strip()
    return d


def xy_km(lat, lon, lat0=30.0, lon0=-99.0):
    return np.c_[(np.asarray(lon) - lon0) * np.cos(np.radians(lat0)) * 111.32, (np.asarray(lat) - lat0) * 110.57]


def idw_loo(P, stations_xy, targets, p, k, rmax=RMAX_KM, wet=WET_MM):
    """Leave-one-station-out IDW predictions for wet station-days of the `targets` columns. Returns obs, pred, naive-mean arrays."""
    obs, pred, mean_all = [], [], []
    for j in targets:
        dj = np.hypot(*(stations_xy - stations_xy[j]).T)
        cand = np.where((dj <= rmax) & (np.arange(len(dj)) != j))[0]
        cand = cand[np.argsort(dj[cand])]
        days = np.where(~np.isnan(P[:, j]) & (P[:, j] >= wet))[0]
        if len(days) == 0 or len(cand) == 0:
            continue
        M = P[np.ix_(days, cand)]
        v = ~np.isnan(M)
        sel = v & (np.cumsum(v, axis=1) <= k)
        w = np.where(sel, 1.0 / np.maximum(dj[cand], 1.0) ** p, 0.0)
        s = w.sum(axis=1)
        ok = s > 0
        pr = np.where(ok, (np.nan_to_num(M) * w).sum(axis=1) / np.where(ok, s, 1), np.nan)
        nm = np.where(v.sum(axis=1) > 0, np.nanmean(np.where(v, M, np.nan), axis=1), np.nan)
        obs.append(P[days, j][ok]); pred.append(pr[ok]); mean_all.append(nm[ok])
    return np.concatenate(obs), np.concatenate(pred), np.concatenate(mean_all)


def main() -> None:
    d = load()
    d["valid"] = d.PRCP.notna() & (d.PRCP >= 0) & (d.QFLAG == "") & ~d.MFLAG.isin(["P", "I"])
    d["trace_or_H"] = d.MFLAG.isin(["T", "H"])
    obs_i = pd.to_numeric(d.OBS, errors="coerce")
    d["std_obs"] = obs_i.between(600, 900)
    NOTES["rows"] = len(d)
    NOTES["rows_qflag_failed"] = int((d.QFLAG != "").sum())
    NOTES["rows_mflag_PI_dropped"] = int(d.MFLAG.isin(["P", "I"]).sum())
    NOTES["rows_trace_or_H_kept_as_zero"] = int((d.trace_or_H & d.valid).sum())
    st = d.groupby("STATION").agg(name=("NAME", "first"), lat=("LATITUDE", "first"), lon=("LONGITUDE", "first"), first=("DATE", "min"), last=("DATE", "max"),
                                  rows=("DATE", "size"), valid_days=("valid", "sum"), qflag_fail=("QFLAG", lambda s: int((s != "").sum())),
                                  frac_std_obs=("std_obs", "mean"), frac_blank_obs=("OBS", lambda s: float((s == "").mean())))
    st["inside_basin"] = [BASIN.contains(Point(lo, la)) for la, lo in zip(st.lat, st.lon)]
    st["network"] = np.where(st.index.str.startswith("US1"), "CoCoRaHS", np.where(st.index.str.startswith("USC"), "COOP", np.where(st.index.str.startswith("USW"), "WBAN/airport", "other")))
    # primary family = daily total of the 24 h ending ~7-8 am local: stations with OBS_TIME 0600-0900, plus CoCoRaHS stations whose
    # attributes carry no OBS_TIME at all (100% blank in this download; CoCoRaHS protocol is a 7 am observation: see the empirical
    # family check in tables/obs_time_family_check, which compares COOP-only and CoCoRaHS-only basin means on the event days)
    st["primary_family"] = (st.frac_std_obs >= 0.5) | ((st.network == "CoCoRaHS") & (st.frac_blank_obs >= 0.9))
    span = (st["last"] - st["first"]).dt.days + 1
    st["pct_valid_in_span"] = 100 * st.valid_days / span.clip(lower=1)
    md(st.reset_index().sort_values(["inside_basin", "valid_days"], ascending=[False, False]), "station_table")
    NOTES["stations_downloaded"] = len(st)
    NOTES["stations_inside_basin"] = int(st.inside_basin.sum())
    NOTES["stations_inside_primary_family"] = int((st.inside_basin & st.primary_family).sum())
    NOTES["stations_total_primary_family"] = int(st.primary_family.sum())
    NOTES["by_network_inside"] = st[st.inside_basin].network.value_counts().to_dict()

    # day x station matrices (primary family only)
    prim = st[st.primary_family].index.tolist()
    days = pd.date_range("2007-10-02", "2026-11-15", freq="D")
    dd = d[d.valid & d.STATION.isin(prim)]
    dd = dd[dd.std_obs | dd.OBS.eq("")]       # drop individual days with a non-standard observation time
    P = dd.pivot_table(index="DATE", columns="STATION", values="PRCP", aggfunc="first").reindex(days)[prim].values
    sxy = xy_km(st.loc[prim, "lat"].values, st.loc[prim, "lon"].values)
    inside_idx = [i for i, s in enumerate(prim) if st.loc[s, "inside_basin"]]

    # --- observation-time family check: do COOP (explicit 7-8 am OBS_TIME) and CoCoRaHS (blank OBS_TIME) put rain on the same days?
    coop_cols = [i for i, s_ in enumerate(prim) if st.loc[s_, "network"] == "COOP" and st.loc[s_, "inside_basin"]]
    coco_cols = [i for i, s_ in enumerate(prim) if st.loc[s_, "network"] == "CoCoRaHS" and st.loc[s_, "inside_basin"]]
    fam = pd.DataFrame({"date": days, "coop_mean_mm": np.nanmean(P[:, coop_cols], axis=1), "cocorahs_mean_mm": np.nanmean(P[:, coco_cols], axis=1),
                        "n_coop": (~np.isnan(P[:, coop_cols])).sum(axis=1), "n_cocorahs": (~np.isnan(P[:, coco_cols])).sum(axis=1)})
    fam_days = pd.to_datetime(["2015-05-22", "2015-05-23", "2015-05-24", "2015-05-25", "2016-05-28", "2016-05-29", "2016-05-30", "2016-05-31", "2025-07-03",
                               "2025-07-04", "2025-07-05", "2025-07-06", "2026-07-13", "2026-07-14", "2026-07-15", "2026-07-16", "2026-07-17"])
    md(fam[fam.date.isin(fam_days)], "obs_time_family_check")
    both_ok = fam.dropna(subset=["coop_mean_mm", "cocorahs_mean_mm"])
    wetd = both_ok[(both_ok.coop_mean_mm >= 10) | (both_ok.cocorahs_mean_mm >= 10)]
    lagc = {l: float(both_ok.set_index("date").coop_mean_mm.corr(both_ok.set_index("date").cocorahs_mean_mm.shift(l))) for l in (-1, 0, 1)}
    NOTES["coop_vs_cocorahs_daily_corr_by_lag_days"] = lagc
    NOTES["coop_vs_cocorahs_days_both_ge10mm"] = int(((both_ok.coop_mean_mm >= 10) & (both_ok.cocorahs_mean_mm >= 10)).sum())

    # --- LOO cross-validation of the spatial estimator (wet station-days)
    rows = []
    for p in GRID_P:
        for k in GRID_K:
            o, pr, nm = idw_loo(P, sxy, inside_idx, p, k)
            rows.append({"method": f"IDW p={p} k={k} R<=60km", "n_station_days": len(o), "MAE_mm": float(np.mean(np.abs(pr - o))),
                         "RMSE_mm": float(np.sqrt(np.mean((pr - o) ** 2))), "bias_mm": float(np.mean(pr - o))})
    o, pr, nm = idw_loo(P, sxy, inside_idx, 2, 8)
    ok = ~np.isnan(nm)
    rows.append({"method": "simple mean of all other reporting stations R<=60km", "n_station_days": int(ok.sum()), "MAE_mm": float(np.mean(np.abs(nm[ok] - o[ok]))),
                 "RMSE_mm": float(np.sqrt(np.mean((nm[ok] - o[ok]) ** 2))), "bias_mm": float(np.mean(nm[ok] - o[ok]))})
    o1, pr1, _ = idw_loo(P, sxy, inside_idx, 2, 1)
    rows.append({"method": "nearest station only", "n_station_days": len(o1), "MAE_mm": float(np.mean(np.abs(pr1 - o1))),
                 "RMSE_mm": float(np.sqrt(np.mean((pr1 - o1) ** 2))), "bias_mm": float(np.mean(pr1 - o1))})
    cv = pd.DataFrame(rows)
    md(cv, "loo_cv_spatial_methods")
    idw_rows = cv[cv.method.str.startswith("IDW")]
    best = idw_rows.sort_values("MAE_mm").iloc[0]
    bp, bk = int(best.method.split("p=")[1].split()[0]), int(best.method.split("k=")[1].split()[0])
    NOTES["selected_idw"] = {"p": bp, "k": bk, "rmax_km": RMAX_KM, "criterion": "lowest LOO MAE on wet station-days (>=5 mm)"}

    # --- basin grid and daily product
    gx = np.arange(BASIN.bounds[0], BASIN.bounds[2], 0.05) + 0.025
    gy = np.arange(BASIN.bounds[1], BASIN.bounds[3], 0.05) + 0.025
    cells = np.array([(x, y) for x in gx for y in gy if BASIN.contains(Point(x, y))])
    cxy = xy_km(cells[:, 1], cells[:, 0])
    dist = np.hypot(cxy[:, None, 0] - sxy[None, :, 0], cxy[:, None, 1] - sxy[None, :, 1])
    order = np.argsort(dist, axis=1)
    dsort = np.take_along_axis(dist, order, axis=1)
    NOTES["grid_cells"] = len(cells)
    basin, n_in, n_all, cov25, smean, smax = [], [], [], [], [], []
    inside_mask = np.zeros(len(prim), bool); inside_mask[inside_idx] = True
    for i in range(len(days)):
        row = P[i]
        v = ~np.isnan(row)
        n_all.append(int(v.sum())); n_in.append(int((v & inside_mask).sum()))
        smean.append(float(row[v & inside_mask].mean()) if (v & inside_mask).any() else np.nan)
        smax.append(float(row[v].max()) if v.any() else np.nan)
        if v.sum() < 3:
            basin.append(np.nan); cov25.append(0.0); continue
        vs = v[order] & (dsort <= RMAX_KM)
        sel = vs & (np.cumsum(vs, axis=1) <= bk)
        w = np.where(sel, 1.0 / np.maximum(dsort, 1.0) ** bp, 0.0)
        vals = np.nan_to_num(row[order])
        sw = w.sum(axis=1)
        cell = np.where(sw > 0, (vals * w).sum(axis=1) / np.where(sw > 0, sw, 1), np.nan)
        near = ((v[order] & (dsort <= 25.0)).sum(axis=1) >= 2)
        cov25.append(float(near.mean()))
        basin.append(float(np.nanmean(cell)) if np.isfinite(cell).sum() >= 0.5 * len(cell) else np.nan)
    prod = pd.DataFrame({"date": days, "basin_idw_mm": basin, "simple_mean_inside_mm": smean, "max_station_mm": smax,
                         "n_stations_inside": n_in, "n_stations_total": n_all, "coverage_frac_25km_2stations": cov25})
    prod["quality"] = np.where(prod.basin_idw_mm.isna(), "missing", np.where((prod.coverage_frac_25km_2stations < 0.8) | (prod.n_stations_inside < 3), "low_coverage", "ok"))
    prod.to_csv("data/processed/gauge_basin_daily.csv", index=False)
    NOTES["days"] = len(prod); NOTES["days_missing"] = int((prod.quality == "missing").sum()); NOTES["days_low_coverage"] = int((prod.quality == "low_coverage").sum())
    yr = prod.groupby(prod.date.dt.year).agg(days=("date", "size"), missing=("quality", lambda s: int((s == "missing").sum())),
                                              low_cov=("quality", lambda s: int((s == "low_coverage").sum())), median_stations_inside=("n_stations_inside", "median"),
                                              median_stations_total=("n_stations_total", "median"), mean_coverage=("coverage_frac_25km_2stations", "mean"),
                                              annual_mean_idw_mm_per_day=("basin_idw_mm", "mean"))
    yr["annual_total_mm_if_complete"] = yr.annual_mean_idw_mm_per_day * 365
    md(yr.reset_index().rename(columns={"date": "year"}), "coverage_by_year")

    # --- comparison with ERA5 (24 h ending 13 UTC) and event days
    from flashflood import data as fdata
    era = fdata.load_rain_hourly()
    e24 = era.rolling(24, min_periods=24).sum()
    prod["era5_24h_end13utc_mm"] = [float(e24.get(pd.Timestamp(dt, tz="UTC") + pd.Timedelta("13h"), np.nan)) for dt in prod.date]
    both = prod.dropna(subset=["basin_idw_mm", "era5_24h_end13utc_mm"])
    both = both[both.quality == "ok"]
    wet = both[both.basin_idw_mm >= 10]
    cmp_ = pd.DataFrame([
        {"subset": "all good days", "n": len(both), "pearson": both.basin_idw_mm.corr(both.era5_24h_end13utc_mm), "spearman": both.basin_idw_mm.corr(both.era5_24h_end13utc_mm, method="spearman"),
         "mean_gauge_mm": both.basin_idw_mm.mean(), "mean_era5_mm": both.era5_24h_end13utc_mm.mean()},
        {"subset": "gauge basin rain >= 10 mm", "n": len(wet), "pearson": wet.basin_idw_mm.corr(wet.era5_24h_end13utc_mm), "spearman": wet.basin_idw_mm.corr(wet.era5_24h_end13utc_mm, method="spearman"),
         "mean_gauge_mm": wet.basin_idw_mm.mean(), "mean_era5_mm": wet.era5_24h_end13utc_mm.mean()}])
    md(cmp_, "gauge_vs_era5_daily")
    top = both.sort_values("basin_idw_mm", ascending=False).head(25)[["date", "basin_idw_mm", "simple_mean_inside_mm", "era5_24h_end13utc_mm", "max_station_mm", "n_stations_inside"]]
    md(top, "top25_gauge_days_vs_era5")
    ev_days = ["2015-05-23", "2015-05-24", "2015-05-25", "2015-10-29", "2015-10-30", "2016-05-29", "2016-05-30", "2016-05-31", "2025-07-04", "2025-07-05", "2026-07-14", "2026-07-15", "2026-07-16", "2026-07-17"]
    md(prod[prod.date.isin(pd.to_datetime(ev_days))][["date", "basin_idw_mm", "simple_mean_inside_mm", "era5_24h_end13utc_mm", "max_station_mm", "n_stations_inside", "coverage_frac_25km_2stations", "quality"]],
       "event_days_gauge_vs_era5")

    fig, ax = plt.subplots(figsize=(7.5, 3.3))
    ax.bar(yr.index, yr.median_stations_inside, color=C["s1"], width=0.6); ax.grid(axis="x", visible=False)
    ax.set_ylabel("median stations/day inside basin"); ax.set_title("Gauge network size changes through time (primary obs-time family)")
    fig.tight_layout(); fig.savefig(FIG / "fig1_station_counts_by_year.png", dpi=150); plt.close(fig)
    fig, ax = plt.subplots(figsize=(4.8, 4.4))
    ax.scatter(both.basin_idw_mm, both.era5_24h_end13utc_mm, s=3, color=C["s1"], alpha=0.35, edgecolors="none")
    lim = max(both.basin_idw_mm.max(), both.era5_24h_end13utc_mm.max()); ax.plot([0, lim], [0, lim], color=C["ink2"], lw=0.8, ls="--")
    ax.set_xlabel("gauge IDW basin rain, 24 h (mm)"); ax.set_ylabel("ERA5 basin rain, 24 h ending 13 UTC (mm)"); ax.set_title("Daily basin rain: ERA5 vs gauges")
    fig.tight_layout(); fig.savefig(FIG / "fig2_era5_vs_gauges.png", dpi=150); plt.close(fig)
    (OUT / "build_notes.json").write_text(json.dumps(NOTES, indent=2, default=str))
    print(json.dumps(NOTES, indent=2, default=str)); print(cv.round(2).to_string(index=False)); print(cmp_.round(2).to_string(index=False))
    print(prod[prod.date.isin(pd.to_datetime(ev_days))].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
