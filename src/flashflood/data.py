"""Data loading and causal feature construction (Phase 1A).  All times UTC, stage in feet."""
from pathlib import Path

import numpy as np
import pandas as pd

FLOOR_FT = -1.2          # stage at/below this is a flat sensor-floor / dry-channel period (Phase 0) -> invalid
STEP = pd.Timedelta("15min")
HORIZONS = {"15m": 1, "30m": 2, "1h": 4, "3h": 12}          # forecast horizons in 15-min steps
LAGS = {"15m": 1, "30m": 2, "1h": 4, "2h": 8, "3h": 12, "6h": 24, "12h": 48, "24h": 96}
RAIN_WINDOWS_H = (3, 6, 12, 24, 72, 168)


def load_stage(raw_dir: str = "data/raw/usgs_iv") -> pd.DataFrame:
    """Regular 15-min grid with stage `s` (NaN when missing/invalid), `valid`, `provisional`."""
    frames = [pd.read_csv(f, index_col=0) for f in sorted(Path(raw_dir).glob("iv_*.csv"))]
    d = pd.concat(frames)
    d.index = pd.to_datetime(d.index, utc=True)
    d = d.sort_index()
    d = d[~d.index.duplicated()]
    d = d.rename(columns={"00065": "stage_ft", "00060": "q_cfs", "00065_cd": "stage_cd"})
    full = pd.date_range(d.index.min().ceil("15min"), d.index.max().floor("15min"), freq="15min")
    reg = d[["stage_ft", "q_cfs", "stage_cd"]].reindex(full)
    reg["stage_ft"] = pd.to_numeric(reg.stage_ft, errors="coerce")
    reg["valid"] = reg.stage_ft.notna() & (reg.stage_ft > FLOOR_FT)
    reg["s"] = reg.stage_ft.where(reg.valid)
    reg["provisional"] = reg.stage_cd.astype(str).str.startswith("P")
    return reg


def load_rain_hourly(raw_dir: str = "data/raw/era5_precip", cells_csv: str = "data/raw/meta/era5_cells.csv") -> pd.Series:
    """Area-weighted basin-mean ERA5 precipitation (mm), label = end of the hour (Open-Meteo 'preceding hour' sum)."""
    cells = pd.read_csv(cells_csv, dtype=str)
    ser = {}
    for r in cells.itertuples():
        files = sorted((Path(raw_dir) / f"{r.lat}_{r.lon}").glob("*.csv"))
        df = pd.concat([pd.read_csv(f) for f in files])
        df["time"] = pd.to_datetime(df.time, utc=True)
        ser[r.Index] = df.drop_duplicates("time").set_index("time").sort_index().precipitation
    w = cells.area_km2.astype(float).values
    wide = pd.DataFrame(ser)
    avail = wide.notna().mul(w, axis=1).sum(axis=1)
    p = wide.mul(w, axis=1).sum(axis=1, min_count=1) / avail.where(avail > 0)
    p[avail < 0.999 * w.sum()] = np.nan
    return p.asfreq("h")


def hydro_features(s: pd.Series, strict: bool = False) -> pd.DataFrame:
    """Stage-only predictors; every value at row t uses data with timestamp <= t.

    strict=True reproduces the ORIGINAL first-run behaviour (no gap bridging, rolling windows need 100% of samples) and is
    kept only so the original results can be regenerated for the deviation-3 comparison.
    """
    f = pd.DataFrame(index=s.index)
    f["s"] = s
    if strict:
        for name, k in LAGS.items():
            f[f"d_{name}"] = s - s.shift(k)
        f["max24h"] = s.rolling(96, min_periods=96).max()
        f["max72h"] = s.rolling(288, min_periods=288).max()
        return f
    s_ff = s.ffill(limit=4)      # causal fill of isolated gaps <= 1 h, used ONLY for the lagged reference value
    for name, k in LAGS.items():
        f[f"d_{name}"] = s - s_ff.shift(k)
    # rolling maxima over the available samples; need >= 50% of the window so one missing sample does not blank 72 h
    f["max24h"] = s.rolling(96, min_periods=48).max()
    f["max72h"] = s.rolling(288, min_periods=144).max()
    return f


def rain_features(p_hourly: pd.Series, idx: pd.DatetimeIndex) -> pd.DataFrame:
    """Rain predictors at 15-min issue times using only hourly labels <= floor(t, 1h) (causal)."""
    p = p_hourly.asfreq("h")
    hh = idx.floor("h")
    out = pd.DataFrame(index=idx)
    out["rain_1h"] = p.reindex(hh).values
    out["rain_age_min"] = ((idx - hh) / pd.Timedelta("1min")).values
    for k in RAIN_WINDOWS_H:
        out[f"rain_sum_{k}h"] = p.rolling(k, min_periods=k).sum().reindex(hh).values
    return out


def targets(s: pd.Series) -> dict:
    """Change targets: s(t+h) - s(t) for each horizon (NaN if either end invalid)."""
    return {h: s.shift(-k) - s for h, k in HORIZONS.items()}


# ---------------------------------------------------------------- Phase 1B additions
REQUIRED_COLS = ["s", "d_15m", "d_30m", "d_1h"]        # minimal inputs for eligibility (Phase 1B protocol section 1)
MAX_COLS = ["max24h", "max72h"]


def h2_extra(s: pd.Series) -> pd.DataFrame:
    """H2 additions (causal): 1-h acceleration, largest 15-min rise in the last hour, stage above its 7-day minimum."""
    s_ff = s.ffill(limit=4)
    f = pd.DataFrame(index=s.index)
    f["accel_1h"] = (s - s_ff.shift(4)) - (s_ff.shift(4) - s_ff.shift(8))
    f["max_step_1h"] = (s - s_ff.shift(1)).rolling(4, min_periods=3).max()
    f["rel_base7d"] = s - s.rolling(672, min_periods=168).min()
    return f


def gauge_features(daily: pd.DataFrame, idx: pd.DatetimeIndex, cutoff_hour_utc: int = 15) -> pd.DataFrame:
    """Antecedent rainfall from the gauge product. Product day D (24 h ending ~7-8 am local) is usable only from
    D + cutoff_hour_utc (15:00 UTC), so a feature at issue time t uses the last day whose cutoff is <= t. Days with quality != 'ok' are NaN."""
    v = daily.set_index(pd.to_datetime(daily.date)).basin_idw_mm.where(daily.set_index(pd.to_datetime(daily.date)).quality.values == "ok")
    f = pd.DataFrame({"g_1d": v, "g_3d": v.rolling(3, min_periods=3).sum(), "g_7d": v.rolling(7, min_periods=6).sum(),
                      "g_30d": v.rolling(30, min_periods=24).sum()})
    f.index = (f.index + pd.Timedelta(hours=cutoff_hour_utc)).tz_localize("UTC")
    return f.reindex(idx, method="ffill")


def prep_linear(x: pd.DataFrame, cols: list) -> np.ndarray:
    """Imputation for ridge/logistic: missing differences -> 0, missing running maxima -> current stage, missing gauge features -> 0,
    plus indicators long_missing / g_missing so missingness is explicit, never silent."""
    z = x[cols].copy()
    long_missing = z.drop(columns=[c for c in REQUIRED_COLS if c in z], errors="ignore").isna().any(axis=1).astype(float)
    g_cols = [c for c in z if c.startswith("g_")]
    g_missing = z[g_cols].isna().any(axis=1).astype(float) if g_cols else None
    for c in MAX_COLS:
        if c in z:
            z[c] = z[c].fillna(z["s"])
    z = z.fillna(0.0)
    z["long_missing"] = long_missing
    if g_missing is not None:
        z["g_missing"] = g_missing
    return z.values
