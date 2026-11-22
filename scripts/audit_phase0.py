"""Phase 0 audit for USGS 08167500: hydrology quality, rainfall/weather sources, temporal alignment,
flood-event catalogue and split suitability.  Read-only on data/raw; writes tables, figures and a
results JSON under reports/phase0/ and a draft aligned table under data/processed/.

Run after: fetch_meta.py, fetch_usgs.py, fetch_openmeteo.py --dataset precip / land
Usage:     python scripts/audit_phase0.py

No model is trained and no model metric is computed here.  Everything is descriptive statistics
of the observed record.  All timestamps are UTC.  Stage is feet, discharge ft3/s (USGS native).
"""
import csv
import json
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")

RAW = Path("data/raw")
OUT = Path("reports/phase0")
TAB, FIG = OUT / "tables", OUT / "figures"
for p in (TAB, FIG, Path("data/processed")):
    p.mkdir(parents=True, exist_ok=True)

# --- chart tokens (validated default palette, light mode; text never wears series colour) -------
C = dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#e6e5e1", s1="#2a78d6", s2="#eb6834", s3="#1baf7a")
plt.rcParams.update({
    "figure.facecolor": C["surface"], "axes.facecolor": C["surface"], "savefig.facecolor": C["surface"],
    "axes.edgecolor": C["grid"], "axes.labelcolor": C["ink2"], "text.color": C["ink"],
    "xtick.color": C["ink2"], "ytick.color": C["ink2"], "axes.grid": True, "grid.color": C["grid"],
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9,
    "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left",
})

RESULTS: dict = {}
STEP_H = 0.25  # 15 minutes in hours
FLOOD = json.load(open(RAW / "meta/nws_gauge.json"))["flood"]["categories"]
CATS = {k: float(FLOOD[k]["stage"]) for k in ("action", "minor", "moderate", "major")}
OFFICIAL_THR = sorted(CATS.values())
EXTRA_THR = [5, 8, 10, 15, 20]  # NOT official: sensitivity analysis only
SEP_H = 24.0  # default declustering separation (hours below threshold) for independent events


def md(df: pd.DataFrame, name: str, index: bool = False) -> None:
    df.to_csv(TAB / f"{name}.csv", index=index)
    (TAB / f"{name}.md").write_text(df.to_markdown(index=index, floatfmt=".3g"))


def runs_idx(mask) -> tuple:
    m = np.asarray(mask).astype(int)
    d = np.diff(np.r_[0, m, 0])
    return np.where(d == 1)[0], np.where(d == -1)[0] - 1


# ================================================================ 1. hydrology
def load_hydro() -> tuple:
    frames = [pd.read_csv(f, index_col=0) for f in sorted((RAW / "usgs_iv").glob("iv_*.csv"))]
    raw = pd.concat(frames)
    raw.index = pd.to_datetime(raw.index, utc=True)
    raw = raw.sort_index()
    n_dup = int(raw.index.duplicated().sum())
    raw = raw[~raw.index.duplicated(keep="first")]
    raw = raw.rename(columns={"00065": "stage_ft", "00060": "q_cfs", "00065_cd": "stage_cd", "00060_cd": "q_cd"})
    for c in ("stage_ft", "q_cfs"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    full = pd.date_range(raw.index.min().ceil("15min"), raw.index.max().floor("15min"), freq="15min")
    reg = raw.reindex(full)
    return raw, reg, n_dup


def audit_hydro(raw, reg, n_dup) -> None:
    res = {"rows_raw": len(raw), "duplicates_dropped": n_dup, "first": str(raw.index.min()), "last": str(raw.index.max()),
           "expected_15min_steps": len(reg), "stage_missing": int(reg.stage_ft.isna().sum()),
           "discharge_missing": int(reg.q_cfs.isna().sum())}
    off_grid = int((raw.index != raw.index.round("15min")).sum())
    steps = raw.index.to_series().diff().dropna().value_counts().head(8)
    res["off_15min_grid_timestamps"] = off_grid
    res["step_distribution_top"] = {str(k): int(v) for k, v in steps.items()}
    yr = reg.index.year
    cov = pd.DataFrame({"expected": pd.Series(1, index=reg.index).groupby(yr).sum(),
                        "stage_obs": reg.stage_ft.notna().groupby(yr).sum(),
                        "q_obs": reg.q_cfs.notna().groupby(yr).sum()})
    cov["stage_complete_%"] = 100 * cov.stage_obs / cov.expected
    cov["q_complete_%"] = 100 * cov.q_obs / cov.expected
    md(cov.reset_index().rename(columns={"index": "year"}), "hydro_coverage_by_year")

    st, en = runs_idx(reg.stage_ft.isna())
    gaps = pd.DataFrame({"start": reg.index[st], "end": reg.index[en], "steps": en - st + 1})
    gaps["hours"] = gaps.steps * STEP_H
    res["gap_runs"] = len(gaps)
    res["gap_longest_h"] = float(gaps.hours.max()) if len(gaps) else 0
    res["gaps_ge_1h"] = int((gaps.hours >= 1).sum())
    res["gaps_ge_6h"] = int((gaps.hours >= 6).sum())
    res["gaps_ge_24h"] = int((gaps.hours >= 24).sum())
    res["gap_missing_steps_in_gaps_ge_24h"] = int(gaps.loc[gaps.hours >= 24, "steps"].sum())
    md(gaps.sort_values("hours", ascending=False).head(25), "hydro_longest_gaps")

    qual = {}
    for col in ("stage_cd", "q_cd"):
        vc = raw[col].fillna("NA").value_counts()
        qual[col] = {k: int(v) for k, v in vc.items()}
    res["qualifier_codes"] = qual
    piv = (raw.assign(year=raw.index.year, code=raw.stage_cd.fillna("NA")).groupby(["year", "code"]).size().unstack(fill_value=0))
    md(piv.reset_index(), "hydro_stage_qualifiers_by_year")

    s, q = reg.stage_ft, reg.q_cfs
    res["stage_ft"] = {"min": float(s.min()), "median": float(s.median()), "p99": float(s.quantile(.99)), "max": float(s.max()),
                       "n_negative": int((s < 0).sum()), "n_zero": int((s == 0).sum())}
    res["q_cfs"] = {"min": float(q.min()), "median": float(q.median()), "p99": float(q.quantile(.99)), "max": float(q.max()),
                    "n_negative": int((q < 0).sum()), "n_zero": int((q == 0).sum())}
    # rating drift: median Q inside a fixed stage band, per year
    band = float(s.quantile(.75))
    sel = reg[(s > band - .25) & (s < band + .25)]
    drift = sel.groupby(sel.index.year).q_cfs.agg(["count", "median"]).query("count >= 50")
    drift.insert(0, "stage_band_ft", f"{band - .25:.2f}-{band + .25:.2f}")
    md(drift.reset_index().rename(columns={"index": "year", "median": "median_q_cfs"}), "hydro_rating_drift_check")
    # largest 15-minute jumps (candidate sensor errors OR genuine flash rises; not judged here)
    d15 = s.diff()
    res["jumps_gt_1ft_per_15min"] = int((d15.abs() > 1).sum())
    res["jumps_gt_3ft_per_15min"] = int((d15.abs() > 3).sum())
    top = d15.abs().sort_values(ascending=False).head(10)
    md(pd.DataFrame({"time_utc": top.index, "abs_dstage_ft_15min": top.values,
                     "stage_ft": s.reindex(top.index).values, "q_cfs": q.reindex(top.index).values}), "hydro_largest_15min_jumps")
    RESULTS["hydro"] = res


# ================================================================ 2. events
def find_events(stage: pd.Series, q: pd.Series, thr: float, sep_h: float = SEP_H) -> pd.DataFrame:
    s, qv = stage.values, q.values
    above = np.nan_to_num(s, nan=-9e9) >= thr
    st, en = runs_idx(above)
    merged: list = []
    for a, b in zip(st, en):
        if merged and (a - merged[-1][1] - 1) * STEP_H < sep_h:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    nan_mask = np.isnan(s)
    rows = []
    for a, b in merged:
        seg = s[a:b + 1]
        pk = a + int(np.nanargmax(seg))
        lo = max(0, a - 288)
        pre = s[lo:a + 1]
        if np.isfinite(pre).any():
            base = float(np.nanmin(pre))
            on = lo + int(np.where(pre <= base + 0.5)[0][-1])
        else:
            base, on = np.nan, a

        def mr(k):
            if pk - on < k:
                return np.nan
            d = s[on + k:pk + 1] - s[on:pk + 1 - k]
            return float(np.nanmax(d)) if np.isfinite(d).any() else np.nan
        r15, r1, r3 = mr(1), mr(4), mr(12)
        row = dict(first_cross=stage.index[a], last_above=stage.index[b], peak_time=stage.index[pk],
                   peak_stage_ft=float(s[pk]), peak_q_cfs=float(np.nanmax(qv[a:b + 1])) if np.isfinite(qv[a:b + 1]).any() else np.nan,
                   hours_above=(b - a + 1) * STEP_H, baseline_stage_ft=base, rise_onset=stage.index[on],
                   onset_to_peak_h=(pk - on) * STEP_H, cross_to_peak_h=(pk - a) * STEP_H,
                   max_rise_15min_ft_per_h=r15 * 4 if np.isfinite(r15) else np.nan,
                   max_rise_1h_ft=r1, max_rise_3h_ft=r3,
                   data_gap_within_6h=bool(nan_mask[max(0, a - 24):b + 25].any()))
        for cat, val in CATS.items():
            idx = np.where(seg >= val)[0]
            row[f"t_{cat}"] = stage.index[a + idx[0]] if len(idx) else pd.NaT
        rows.append(row)
    df = pd.DataFrame(rows)
    for col in [c for c in df.columns if c.startswith("t_") or c in ("first_cross", "last_above", "peak_time", "rise_onset")]:
        df[col] = pd.to_datetime(df[col], utc=True)
    return df


def rapid_rise_episodes(stage: pd.Series, rise_ft: float, hours: int = 3, sep_h: float = SEP_H) -> pd.DataFrame:
    d = stage.diff(hours * 4)
    st, en = runs_idx((d >= rise_ft).fillna(False))
    merged: list = []
    for a, b in zip(st, en):
        if merged and (a - merged[-1][1] - 1) * STEP_H < sep_h:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    rows = []
    for a, b in merged:
        seg = d.values[a:b + 1]
        k = a + int(np.nanargmax(seg))
        rows.append(dict(time=stage.index[k], max_rise_ft=float(d.values[k]), stage_at_time=float(stage.values[k])))
    return pd.DataFrame(rows)


def audit_events(reg: pd.DataFrame) -> dict:
    s, q = reg.stage_ft, reg.q_cfs
    res: dict = {"official_categories_ft": CATS, "source": "NWS NWPS gauge SRGT2 (api.water.noaa.gov/nwps/v1/gauges/08167500)"}
    master = find_events(s, q, CATS["action"])
    master.insert(0, "event_id", [f"E{i + 1:02d}" for i in range(len(master))])
    for a, b in (("action", "minor"), ("minor", "moderate"), ("moderate", "major")):
        master[f"lead_{a}_to_{b}_h"] = (master[f"t_{b}"] - master[f"t_{a}"]).dt.total_seconds() / 3600
    md(master, "event_catalogue_action_stage")
    res["n_events_action"] = len(master)

    # counts by threshold and by declustering separation
    rows = []
    for thr in sorted(set(EXTRA_THR + OFFICIAL_THR)):
        row = {"threshold_ft": thr, "kind": next((k for k, v in CATS.items() if v == thr), "NOT official (sensitivity)")}
        for sep in (12, 24, 48, 72):
            row[f"events_sep{sep}h"] = len(find_events(s, q, thr, sep))
        ev = find_events(s, q, thr)
        row["median_peak_ft"] = float(ev.peak_stage_ft.median()) if len(ev) else np.nan
        row["max_peak_ft"] = float(ev.peak_stage_ft.max()) if len(ev) else np.nan
        rows.append(row)
    cnt = pd.DataFrame(rows)
    md(cnt, "event_counts_by_threshold")

    rr_rows, rr_eps = [], {}
    for r in (1, 2, 4, 8):
        e = rapid_rise_episodes(s, r)
        rr_eps[r] = e
        rr_rows.append({"rise_ft_in_3h": r, "independent_episodes_sep24h": len(e)})
    md(pd.DataFrame(rr_rows), "event_counts_rapid_rise")

    # annual peaks vs continuous record (never assume peaks have 15-min data)
    pk = pd.read_csv(RAW / "meta/annual_peaks.csv")
    pk["peak_date"] = pd.to_datetime(pk.peak_dt, errors="coerce", utc=True)
    pk = pk[pk.peak_date >= pd.Timestamp("2007-01-01", tz="UTC")].copy()
    t0 = reg.index.min()
    out = []
    for _, r in pk.iterrows():
        d0 = r.peak_date
        covered = d0 >= t0
        w = reg.loc[d0 - pd.Timedelta("1D"): d0 + pd.Timedelta("2D")] if covered else reg.iloc[0:0]
        out.append(dict(peak_date=d0.date(), peak_gage_ht_ft=r.gage_ht, peak_q_cfs=r.peak_va,
                        in_iv_record=bool(covered),
                        iv_obs_fraction_pm1_2d=float(w.stage_ft.notna().mean()) if len(w) else np.nan,
                        iv_max_stage_ft=float(w.stage_ft.max()) if len(w) else np.nan,
                        iv_max_q_cfs=float(w.q_cfs.max()) if len(w) else np.nan))
    md(pd.DataFrame(out), "annual_peaks_vs_iv_record")

    # per-year event counts (for split design) by event first-crossing date
    ev_by_thr = {thr: find_events(s, q, thr) for thr in sorted(set(EXTRA_THR + OFFICIAL_THR))}
    years = list(range(reg.index.min().year, reg.index.max().year + 1))
    mat = pd.DataFrame({f">={t:g} ft": pd.Series([(e.first_cross.dt.year == y).sum() if len(e) else 0 for y in years], index=years)
                        for t, e in ev_by_thr.items()})
    for r, e in rr_eps.items():
        mat[f"rapid rise >={r} ft/3h"] = pd.Series([(e.time.dt.year == y).sum() if len(e) else 0 for y in years], index=years)
    md(mat.reset_index().rename(columns={"index": "year"}), "event_counts_by_year")

    splits = {"A: <=2017 | 2018-2021 | 2022+": ("2018-01-01", "2022-01-01"),
              "B: <=2019 | 2020-2022 | 2023+": ("2020-01-01", "2023-01-01"),
              "C: <=2016 | 2017-2020 | 2021+": ("2017-01-01", "2021-01-01")}
    srows = []
    for name, (v0, t1) in splits.items():
        v0, t1 = pd.Timestamp(v0, tz="UTC"), pd.Timestamp(t1, tz="UTC")
        for label, ev in [(f">={t:g} ft", e) for t, e in ev_by_thr.items()] + [(f"rapid >={r} ft/3h", e.rename(columns={"time": "first_cross"})) for r, e in rr_eps.items()]:
            fc = ev.first_cross if len(ev) else pd.Series([], dtype="datetime64[ns, UTC]")
            srows.append({"split": name, "event_def": label, "train": int((fc < v0).sum()), "val": int(((fc >= v0) & (fc < t1)).sum()), "test": int((fc >= t1).sum())})
    md(pd.DataFrame(srows), "split_event_counts")
    RESULTS["events"] = res
    return {"master": master, "rr": rr_eps}


# ================================================================ 3. weather
def load_cells(folder: str, cellfile: str) -> tuple:
    cells = list(csv.DictReader(open(RAW / "meta" / cellfile)))
    series, weights = {}, {}
    for c in cells:
        d = RAW / folder / f"{c['lat']}_{c['lon']}"
        files = sorted(d.glob("*.csv")) if d.exists() else []
        if not files:
            continue
        df = pd.concat([pd.read_csv(f) for f in files])
        df["time"] = pd.to_datetime(df["time"], utc=True)
        series[(c["lat"], c["lon"])] = df.drop_duplicates("time").set_index("time").sort_index()
        weights[(c["lat"], c["lon"])] = float(c["area_km2"])
    return series, pd.Series(weights), len(cells)


def basin_mean(series: dict, weights: pd.Series, col: str) -> tuple:
    wide = pd.DataFrame({k: v[col] for k, v in series.items()})
    w = weights.reindex(wide.columns)
    avail = wide.notna().mul(w, axis=1).sum(axis=1)
    avg = wide.mul(w, axis=1).sum(axis=1, min_count=1) / avail.where(avail > 0)
    return avg, avail / w.sum(), wide


def audit_weather(reg: pd.DataFrame, master: pd.DataFrame) -> dict:
    res: dict = {}
    p_series, p_w, p_total = load_cells("era5_precip", "era5_cells.csv")
    l_series, l_w, l_total = load_cells("era5land", "era5land_cells.csv")
    res["precip_cells_downloaded"] = f"{len(p_series)}/{p_total}"
    res["land_cells_downloaded"] = f"{len(l_series)}/{l_total}"
    out = {"precip": None, "land": {}}
    if p_series:
        p, p_cov, p_wide = basin_mean(p_series, p_w, "precipitation")
        p[p_cov < 0.999] = np.nan  # only accept full-basin coverage
        out["precip"] = (p, p_wide)
        hours = pd.date_range(p.index.min(), p.index.max(), freq="h")
        res["precip"] = {"first": str(p.index.min()), "last_valid": str(p.dropna().index.max()), "hours_expected": len(hours),
                         "null_hours": int(p.reindex(hours).isna().sum()), "min_mm": float(p.min()), "max_hourly_mm": float(p.max()),
                         "frac_hours_gt_0.1mm": float((p > 0.1).mean()), "native_grid": "ERA5 0.25 deg (~25 km), via Open-Meteo model=era5"}
        yr = p.groupby(p.index.year).sum().rename("basin_mean_rain_mm")
        n = p.groupby(p.index.year).count().rename("hours")
        md(pd.concat([yr, n], axis=1).reset_index().rename(columns={"index": "year", "time": "year"}), "rain_annual_totals")
        cell_mean = (p_wide.groupby(p_wide.index.year).sum().T)
        cell_mean.index = [f"{a},{b}" for a, b in cell_mean.index]
        md(cell_mean.loc[:, cell_mean.columns.isin([2008, 2012, 2015, 2019, 2023])].reset_index().rename(columns={"index": "cell"}), "rain_spatial_by_cell_selected_years")
    for var, col in [("soil_moisture_0_7cm", "soil_moisture_0_to_7cm"), ("soil_moisture_7_28cm", "soil_moisture_7_to_28cm"),
                     ("soil_moisture_28_100cm", "soil_moisture_28_to_100cm"), ("temperature_2m", "temperature_2m"),
                     ("relative_humidity_2m", "relative_humidity_2m")]:
        if l_series:
            v, v_cov, _ = basin_mean(l_series, l_w, col)
            out["land"][var] = v
            res[var] = {"first": str(v.index.min()), "last_valid": str(v.dropna().index.max()), "null_frac": float(v.isna().mean()),
                        "min": float(v.min()), "max": float(v.max()), "cells_used": f"{len(l_series)}/{l_total}"}
    RESULTS["weather"] = res
    return out


def val_at(series, t, tol: str = "2h") -> float:
    """Value of an hourly series at time t, NaN if no sample within tol (never a stale value)."""
    if series is None:
        return np.nan
    i = series.index.get_indexer([t], method="nearest", tolerance=pd.Timedelta(tol))[0]
    return float(series.iloc[i]) if i >= 0 else np.nan


def rain_vs_events(wx: dict, reg: pd.DataFrame, master: pd.DataFrame) -> None:
    if wx["precip"] is None:
        return
    p, p_wide = wx["precip"]
    sm = wx["land"].get("soil_moisture_0_7cm")
    rows = []
    for _, e in master.iterrows():
        pk = e.peak_time
        win = p.loc[pk - pd.Timedelta("72h"):pk]
        wide72 = p_wide.loc[pk - pd.Timedelta("72h"):pk].sum()
        h = win.idxmax() if win.notna().any() else pd.NaT
        rows.append(dict(event_id=e.event_id, peak_time=pk, peak_stage_ft=e.peak_stage_ft,
                         basin_rain_24h_mm=float(p.loc[pk - pd.Timedelta("24h"):pk].sum()),
                         basin_rain_72h_mm=float(win.sum()), max_cell_rain_72h_mm=float(wide72.max()),
                         max_hourly_rain_mm=float(win.max()) if win.notna().any() else np.nan,
                         hr_of_max_rain=h, lag_maxrain_to_first_cross_h=(e.first_cross - h).total_seconds() / 3600 if pd.notna(h) else np.nan,
                         lag_maxrain_to_peak_h=(pk - h).total_seconds() / 3600 if pd.notna(h) else np.nan,
                         soil_moist_0_7cm_72h_before=val_at(sm, pk - pd.Timedelta("72h"))))
    md(pd.DataFrame(rows), "events_vs_rainfall")

    # largest 24 h basin-rain episodes and what the river did afterwards (base rate of 'rain without flood')
    r24 = p.rolling(24, min_periods=24).sum().dropna().sort_values(ascending=False)
    chosen = []
    for t, v in r24.items():
        if all(abs((t - c).total_seconds()) > 48 * 3600 for c, _ in chosen):
            chosen.append((t, v))
        if len(chosen) == 25:
            break
    srows = []
    for t, v in chosen:
        w = reg.loc[t:t + pd.Timedelta("72h")]
        srows.append(dict(rain_end=t, basin_rain_24h_mm=v,
                          stage_at_rain_end_ft=float(reg.stage_ft.asof(t)) if t >= reg.index.min() else np.nan,
                          max_stage_next_72h_ft=float(w.stage_ft.max()) if len(w) else np.nan,
                          reached_action_25ft=bool(w.stage_ft.max() >= CATS["action"]) if len(w) else False,
                          soil_moist_0_7cm=val_at(sm, t)))
    md(pd.DataFrame(srows), "top_rain_episodes_vs_river_response")


# ================================================================ 4. alignment
def align(reg: pd.DataFrame, wx: dict) -> None:
    t = reg.index
    hh = t.floor("h")
    al = reg[["stage_ft", "q_cfs", "stage_cd", "q_cd"]].copy()
    al["stage_observed"] = reg.stage_ft.notna()
    al["wx_hour_utc"] = hh                      # latest COMPLETED hourly weather label <= t (causal)
    al["rain_age_min"] = ((t - hh) / pd.Timedelta("1min")).astype(int)   # 0/15/30/45
    stats: dict = {"rain_age_min_distribution": al.rain_age_min.value_counts(normalize=True).sort_index().round(3).to_dict()}
    if wx["precip"] is not None:
        al["precip_mm_1h"] = wx["precip"][0].reindex(hh).values
        al["precip_observed"] = al.precip_mm_1h.notna()
        stats["rows_without_rain"] = int((~al.precip_observed).sum())
        stats["first_row_without_rain_after_start"] = str(al.index[~al.precip_observed][-1]) if (~al.precip_observed).any() else None
    for var, v in wx["land"].items():
        al[var] = v.reindex(hh).values
    al.to_csv("data/processed/aligned_15min_DRAFT.csv.gz")
    stats["rows"] = len(al)
    stats["note"] = ("Hourly weather is NOT interpolated or repeated as independent values: each 15-min row carries the latest "
                     "completed hourly value plus rain_age_min. Draft only: no scaling, no windows, no splits.")
    RESULTS["alignment"] = stats


# ================================================================ 5. figures
def figures(reg: pd.DataFrame, master: pd.DataFrame, wx: dict) -> None:
    s = reg.stage_ft
    # fig1 monthly completeness heatmap
    m = s.notna().groupby([s.index.year, s.index.month]).mean().unstack().reindex(columns=range(1, 13))
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("c", [C["surface"], C["s1"]])
    im = ax.imshow(m.values * 100, aspect="auto", cmap=cmap, vmin=0, vmax=100)
    ax.set_yticks(range(len(m))); ax.set_yticklabels(m.index); ax.set_xticks(range(12)); ax.set_xticklabels(list("JFMAMJJASOND"))
    ax.grid(False); cb = fig.colorbar(im, ax=ax); cb.set_label("% of 15-min steps with stage")
    ax.set_title("Stage data completeness by month (USGS 08167500)")
    fig.tight_layout(); fig.savefig(FIG / "fig1_coverage.png", dpi=150); plt.close(fig)

    # fig2 hydrograph with official flood categories
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(s.index, s.values, color=C["s1"], lw=0.5)
    for name, v in CATS.items():
        ax.axhline(v, color=C["ink2"], lw=0.8, ls="--")
        ax.text(s.index[0], v + 0.4, f"{name} {v:g} ft (NWS)", color=C["ink2"], fontsize=7.5)
    for _, e in master.iterrows():
        ax.plot(e.peak_time, e.peak_stage_ft, "o", ms=5, color=C["s2"], mec=C["surface"], mew=1.5)
    ax.set_ylabel("stage (ft)"); ax.set_title("Stage, 15-min record, with NWS flood categories (orange = events at/above action stage)")
    fig.tight_layout(); fig.savefig(FIG / "fig2_hydrograph.png", dpi=150); plt.close(fig)

    # fig3 annual maximum stage
    am = s.groupby(s.index.year).max()
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    ax.bar(am.index, am.values, color=C["s1"], width=0.6)
    ax.grid(axis="x", visible=False)
    for name, v in CATS.items():
        ax.axhline(v, color=C["ink2"], lw=0.8, ls="--"); ax.text(am.index.min() - 0.4, v + 0.4, name, color=C["ink2"], fontsize=7.5)
    ax.set_ylabel("annual max stage (ft)"); ax.set_title("Annual maximum stage vs NWS flood categories (partial first/last year)")
    fig.tight_layout(); fig.savefig(FIG / "fig3_annual_max.png", dpi=150); plt.close(fig)

    # fig4 event counts
    cnt = pd.read_csv(TAB / "event_counts_by_threshold.csv")
    fig, ax = plt.subplots(figsize=(7, 3.4))
    lab = [f"{t:g}" for t in cnt.threshold_ft]
    ax.bar(lab, cnt.events_sep24h, color=[C["s2"] if k != "NOT official (sensitivity)" else C["s1"] for k in cnt.kind], width=0.6)
    ax.grid(axis="x", visible=False)
    for i, v in enumerate(cnt.events_sep24h):
        ax.text(i, v + 0.3, str(v), ha="center", fontsize=8, color=C["ink"])
    ax.set_xlabel("stage threshold (ft); orange = official NWS category, blue = sensitivity only"); ax.set_ylabel("independent events (24 h separation)")
    ax.set_title("Independent events available per stage threshold, 2007-10 to present")
    fig.tight_layout(); fig.savefig(FIG / "fig4_event_counts.png", dpi=150); plt.close(fig)

    # fig5 event panels: stage over basin rain
    if len(master) and wx["precip"] is not None:
        p = wx["precip"][0]
        ev = master.sort_values("peak_stage_ft", ascending=False).head(6).sort_values("peak_time")
        n = len(ev)
        fig, axes = plt.subplots(2, n, figsize=(2.6 * n, 4.2), sharex="col", gridspec_kw={"height_ratios": [2, 1]}, squeeze=False)
        for j, (_, e) in enumerate(ev.iterrows()):
            a, b = e.peak_time - pd.Timedelta("4D"), e.peak_time + pd.Timedelta("3D")
            axes[0, j].plot(s.loc[a:b].index, s.loc[a:b].values, color=C["s1"], lw=1)
            axes[0, j].set_title(f"{e.event_id}  {e.peak_time:%Y-%m-%d}\npeak {e.peak_stage_ft:.1f} ft", fontsize=8)
            axes[1, j].bar(p.loc[a:b].index, p.loc[a:b].values, width=1 / 24, color=C["s3"])
            axes[1, j].tick_params(axis="x", labelrotation=45, labelsize=7)
        axes[0, 0].set_ylabel("stage (ft)"); axes[1, 0].set_ylabel("basin rain (mm/h)")
        fig.tight_layout(); fig.savefig(FIG / "fig5_event_panels.png", dpi=150); plt.close(fig)


def main() -> None:
    raw, reg, n_dup = load_hydro()
    audit_hydro(raw, reg, n_dup)
    ev = audit_events(reg)
    wx = audit_weather(reg, ev["master"])
    rain_vs_events(wx, reg, ev["master"])
    align(reg, wx)
    figures(reg, ev["master"], wx)
    (OUT / "phase0_results.json").write_text(json.dumps(RESULTS, indent=2, default=str))
    print(json.dumps(RESULTS, indent=2, default=str)[:6000])


if __name__ == "__main__":
    main()
