"""Tests for Phase 1B: robust missing-value handling, H2 causality and the gauge-rainfall availability cutoff."""
import numpy as np
import pandas as pd

from flashflood import data

IDX = pd.date_range("2020-01-01", periods=1500, freq="15min", tz="UTC")


def _stage(seed=1):
    rng = np.random.default_rng(seed)
    return pd.Series(2 + np.cumsum(rng.normal(0, 0.05, len(IDX))).clip(-1, 8), index=IDX)


def test_h2_extra_is_causal():
    s = _stage()
    full = data.h2_extra(s)
    for i in (700, 1100, 1400):
        trunc = data.h2_extra(s.iloc[: i + 1])
        pd.testing.assert_series_equal(full.iloc[i], trunc.iloc[i], check_names=False)


def test_long_lag_features_may_be_missing_without_losing_the_row():
    """Eligibility v2: only s, d_15m, d_30m, d_1h are required; a 21 h outage ending just before t must not make the row unusable."""
    s = _stage().copy()
    s.iloc[400:484] = np.nan                       # 21 h outage
    f = pd.concat([data.hydro_features(s), data.h2_extra(s)], axis=1)
    t = 490
    assert f.iloc[t][data.REQUIRED_COLS].notna().all()
    assert f.iloc[t][["d_6h", "d_12h", "d_24h"]].isna().any()
    z = data.prep_linear(f, list(f.columns))
    assert np.isfinite(z[t]).all() and z[t, -1] == 1.0           # imputed, and the long_missing indicator is set


def test_gauge_day_not_available_before_15utc_and_gaps_are_nan():
    days = pd.date_range("2020-03-01", periods=40, freq="D")
    prod = pd.DataFrame({"date": days, "basin_idw_mm": np.arange(40, dtype=float), "quality": "ok"})
    prod.loc[10, "quality"] = "missing"
    idx = pd.DatetimeIndex([pd.Timestamp("2020-03-20 14:45", tz="UTC"), pd.Timestamp("2020-03-20 15:00", tz="UTC"), pd.Timestamp("2020-03-12 14:00", tz="UTC")])
    g = data.gauge_features(prod, idx)
    assert g.g_1d.iloc[0] == 18.0          # 14:45 UTC on 03-20: product day 03-20 not yet available -> day 03-19 (value 18)
    assert g.g_1d.iloc[1] == 19.0          # 15:00 UTC: day 03-20 (value 19) becomes available
    assert np.isnan(g.g_1d.iloc[2])        # at 14:00 UTC on 03-12 the last available day is 03-11, flagged missing -> NaN, never zero
