"""Leakage, protocol and metric tests for Phase 1A."""
import numpy as np
import pandas as pd
import pytest

from flashflood import data, events, metrics, splits

IDX = pd.date_range("2020-01-01", periods=2000, freq="15min", tz="UTC")


def _stage(seed=0):
    rng = np.random.default_rng(seed)
    return pd.Series(2 + np.cumsum(rng.normal(0, 0.05, len(IDX))).clip(-1, 8), index=IDX)


def test_hydro_features_are_causal():
    s = _stage()
    full = data.hydro_features(s)
    for i in (400, 777, 1500):
        trunc = data.hydro_features(s.iloc[: i + 1])
        pd.testing.assert_series_equal(full.iloc[i], trunc.iloc[i], check_names=False)


def test_one_missing_sample_does_not_blank_the_next_72_hours():
    """Regression test for a defect found in the first Phase 1A run: strict rolling windows turned one missing
    15-min sample into 72 h of ineligible rows (it removed a whole flood event from evaluation)."""
    s = _stage().copy()
    s.iloc[500] = np.nan
    f = data.hydro_features(s)
    after = f.iloc[502:1500]
    assert after[["max24h", "max72h"]].notna().all().all()
    assert after.drop(columns=[]).iloc[10:].notna().all().all()      # lag features recover once past the gap
    assert f.iloc[501][["d_15m", "d_30m"]].notna().all()              # <= 1 h gap bridged causally


def test_rain_features_use_only_completed_hours():
    hours = pd.date_range("2019-12-20", "2020-01-10", freq="h", tz="UTC")
    p = pd.Series(np.random.default_rng(1).gamma(0.3, 2, len(hours)), index=hours)
    idx = IDX[500:700]
    full = data.rain_features(p, idx)
    for t in (idx[3], idx[77], idx[150]):
        cut = p.loc[: t.floor("h")]                     # nothing after the latest completed hour label
        trunc = data.rain_features(cut, pd.DatetimeIndex([t]))
        pd.testing.assert_series_equal(full.loc[t], trunc.iloc[0], check_names=False)
    assert set(full.rain_age_min.unique()) <= {0.0, 15.0, 30.0, 45.0}


def test_targets_are_future_change():
    s = _stage()
    t = data.targets(s)
    assert t["1h"].iloc[100] == pytest.approx(s.iloc[104] - s.iloc[100])
    assert np.isnan(t["3h"].iloc[-1])


def test_exceedance_events_merge_within_24h_and_split_beyond():
    s = pd.Series(1.0, index=pd.date_range("2020-01-01", periods=1000, freq="15min", tz="UTC"))
    s.iloc[100:104] = 12   # event A
    s.iloc[150:154] = 12   # 11 h later -> merged
    s.iloc[400:404] = 12   # 62 h later -> separate
    ev = events.exceedance_events(s, 10)
    assert len(ev) == 2 and ev.i0.tolist() == [100, 400] and ev.i1.tolist() == [153, 403]


def test_alarm_hysteresis_holds_one_hour():
    raw = np.zeros(40, bool)
    raw[[3, 4, 10]] = True
    st = events.alarm_state(raw, off_steps=4)
    on = np.where(st)[0]
    assert on.min() == 3 and set(range(3, 9)) <= set(on) and 9 not in on and 10 in on and on.max() == 14


def test_matching_early_late_miss_and_false_alarm():
    ev = pd.DataFrame({"i0": [100, 300, 500], "i1": [110, 310, 510]})
    a0 = np.array([96, 305, 700]); a1 = np.array([100, 308, 704])   # early for ev0, late for ev1, none for ev2; ep2 is false
    out, n_ep, n_fa = events.match(ev, a0, a1, h_steps=4)
    assert out.status.tolist() == ["early", "late", "miss"]
    assert out.lead_h.iloc[0] == pytest.approx(1.0)
    assert (n_ep, n_fa) == (3, 1)


def test_clopper_pearson_three_of_three():
    lo, hi = metrics.clopper_pearson(3, 3)
    assert lo == pytest.approx(0.025 ** (1 / 3), abs=1e-3) and hi == 1.0


def test_bootstrap_ci_contains_point_estimate():
    rng = np.random.default_rng(0)
    e = rng.normal(0, 1, 5000); p = rng.normal(0, 2, 5000); g = np.repeat(np.arange(100), 50)
    ci = metrics.cluster_bootstrap(e, p, g, b=300)
    pt = metrics.reg_stats(e, p)
    assert ci["rmse_ci"][0] <= pt["rmse"] <= ci["rmse_ci"][1]


def test_splits_never_split_a_storm_cluster_and_purge_targets():
    idx = pd.date_range("2017-12-20", "2018-01-10", freq="15min", tz="UTC")
    s = pd.Series(2.0, index=idx)
    s.loc["2017-12-31 12:00":"2018-01-02 06:00"] = 12      # storm straddles the nominal 2018-01-01 boundary
    clusters = events.storm_clusters(s)
    lab, vs, ts = splits.chronological_split(idx, clusters, val_start="2018-01-01", test_start="2018-01-08")
    for c in clusters.itertuples():
        assert lab.iloc[c.i0:c.i1 + 1][lab.iloc[c.i0:c.i1 + 1] != "purge"].nunique() <= 1
    assert vs > pd.Timestamp("2018-01-02 06:00", tz="UTC")
    last_train = lab[lab == "train"].index.max()
    assert last_train + pd.Timedelta("3h") <= vs     # no training target crosses into validation


def test_blocked_folds_purge_and_no_cluster_crossing():
    idx = pd.date_range("2020-01-01", periods=6000, freq="15min", tz="UTC")
    s = pd.Series(2.0, index=idx)
    s.iloc[990:1010] = 12; s.iloc[2490:2510] = 12
    clusters = events.storm_clusters(s)
    fold, bounds = splits.blocked_folds(idx, clusters, n_blocks=4)
    for c in clusters.itertuples():
        assert fold.iloc[c.i0:c.i1 + 1].dropna().nunique() <= 1
    for b in bounds:
        assert fold[(idx >= b - pd.Timedelta("3h")) & (idx < b)].isna().all()
