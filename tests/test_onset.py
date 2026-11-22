"""Onset-timing diagnostics (E18): synthetic forecasts with known behaviour, plus consistency checks against the saved Phase 1E outputs."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from flashflood import onset

K = 12                      # 3 h horizon in 15-min steps


def _river(n=400):
    """Quiet at 2 ft, then a clean ramp of 0.6 ft per step to a peak, then a recession."""
    sv = np.full(n, 2.0)
    up = 2.0 + 0.6 * np.arange(1, 41)                # 40 steps, peak 26 ft
    sv[100:140] = up
    sv[140:200] = np.linspace(up[-1], 2.0, 60)
    return sv


def _ref(sv):
    i0 = int(np.flatnonzero(sv >= 10)[0])
    peak_i = int(np.nanargmax(sv))
    return onset.event_reference(sv, i0, peak_i)


def _shifted_forecast(sv, k, d):
    """Forecast issued at i for i + k that shows the river as it was d steps before the target (d = k is persistence, d = 0 is perfect)."""
    f = np.full(len(sv), np.nan)
    for i in range(len(sv)):
        j = i + k - d
        if 0 <= j < len(sv):
            f[i] = sv[j]
    return f


def test_target_alignment():
    f = np.arange(10.0)
    t = onset.target_aligned(f, 3)
    assert np.isnan(t[:3]).all() and (t[3:] == f[:-3]).all()


def test_persistence_has_zero_lead_and_lag_equal_to_horizon():
    sv = _river(); ref = _ref(sv)
    r = onset.event_timing_row(sv, sv.copy(), ref, K)
    for tag in ("f10", "f50", "f90"):
        assert r[f"lead_{tag}_h"] == pytest.approx(0.0) and r[f"lag_{tag}_h"] == pytest.approx(K * 0.25)
    assert r["catch_up_h"] == pytest.approx(0.0)
    assert not r["anticipation_flag"]


def test_perfect_forecast_has_lead_equal_to_horizon():
    sv = _river(); ref = _ref(sv)
    r = onset.event_timing_row(sv, _shifted_forecast(sv, K, 0), ref, K)
    for tag in ("f10", "f50", "f90"):
        assert r[f"lead_{tag}_h"] == pytest.approx(K * 0.25) and r[f"lag_{tag}_h"] == pytest.approx(0.0)
    assert r["fc_max_ratio"] == pytest.approx(1.0) and r["fc_peak_time_lag_h"] == pytest.approx(0.0)
    assert r["anticipation_flag"] and r["first_flag_lead_vs_onset_h"] > 0     # a perfect forecaster does anticipate


@pytest.mark.parametrize("d", [2, 5, 9])
def test_forecast_late_by_d_steps(d):
    sv = _river(); ref = _ref(sv)
    r = onset.event_timing_row(sv, _shifted_forecast(sv, K, d), ref, K)
    for tag in ("f10", "f50", "f90"):
        assert r[f"lag_{tag}_h"] == pytest.approx(d * 0.25) and r[f"lead_{tag}_h"] == pytest.approx((K - d) * 0.25)


def test_catch_up_is_positive_when_the_forecast_closes_the_gap():
    sv = _river(); ref = _ref(sv)
    f = _shifted_forecast(sv, K, K)                        # persistence ...
    late = np.flatnonzero(sv >= ref["baseline_ft"] + 0.7 * ref["amplitude_ft"])[0]
    f[late - K:] = _shifted_forecast(sv, K, 0)[late - K:]  # ... that becomes exact from 70 % of the rise on
    r = onset.event_timing_row(sv, f, ref, K)
    assert r["lag_f10_h"] == pytest.approx(K * 0.25) and r["lag_f90_h"] == pytest.approx(0.0) and r["catch_up_h"] == pytest.approx(K * 0.25)


def test_level_not_reached_gives_nan_not_an_imputed_value():
    sv = _river(); ref = _ref(sv)
    f = np.full(len(sv), 2.0)                              # a forecast that never rises
    r = onset.event_timing_row(sv, f, ref, K)
    assert np.isnan(r["lag_f50_h"]) and np.isnan(r["lead_f50_h"]) and not r["reached_f50"]
    assert np.isnan(r["catch_up_h"])


def test_reactive_forecast_cannot_flag_before_the_river_moves():
    """A trend extrapolator responds only to a rise that has begun. With a sharp first step (0.6 ft > the 0.5 ft tolerance) the river has not moved at the onset sample,
    so nothing is flagged; with a gentle start it is flagged at the first sample that has moved, which is within the 0.5 ft tolerance, i.e. one step (0.25 h) before the onset sample, never earlier."""
    sv = _river(); ref = _ref(sv)
    f = sv + 4 * np.r_[0, np.diff(sv)]
    assert not onset.pre_onset(sv, f, ref, K)["anticipation_flag"]
    g = np.full(400, 2.0); g[100:] = 2.0 + 0.2 * np.minimum(np.arange(1, 301), 120)       # gentle start: 0.2 ft per step
    refg = onset.event_reference(g, int(np.flatnonzero(g >= 10)[0]), int(np.nanargmax(g)))
    fg = g + 4 * np.r_[0, np.diff(g)]
    r = onset.pre_onset(g, fg, refg, K)
    assert r["anticipation_flag"] and r["first_flag_issue_i"] == 100 and r["first_flag_lead_vs_onset_h"] == pytest.approx(0.25)


def test_genuine_anticipation_has_positive_lead_and_stage_condition_is_enforced():
    sv = _river(); ref = _ref(sv)
    f = sv.copy()
    f[ref["onset_i"] - 4] = sv[ref["onset_i"] - 4] + 1.0   # one forecast, issued 1 h before the onset, predicts +1 ft
    r = onset.pre_onset(sv, f, ref, K)
    assert r["anticipation_flag"] and r["first_flag_lead_vs_onset_h"] == pytest.approx(1.0) and r["flag_at_1ft"]
    assert not onset.pre_onset(sv, sv.copy(), ref, K)["anticipation_flag"]
    # after the onset the river has already risen: such issue times never qualify
    g = sv.copy(); g[ref["onset_i"] + 3] += 5.0
    assert not onset.pre_onset(sv, g, ref, K)["anticipation_flag"]


def test_pre_onset_sensitivity_flags_are_nested():
    sv = _river(); ref = _ref(sv)
    f = sv.copy(); f[ref["onset_i"] - 2] += 0.6
    r = onset.pre_onset(sv, f, ref, K)
    assert r["flag_at_0.25ft"] and r["flag_at_0.5ft"] and not r["flag_at_1ft"]


def test_background_rate_excludes_event_windows():
    sv = _river(); f = sv.copy(); f[50] += 1.0; f[300] += 1.0
    excl = np.zeros(len(sv), bool); excl[40:60] = True
    r = onset.background_rate(sv, f, excl)
    assert r["n_ge_thr"] == 1 and r["rows"] == len(sv) - 20


def test_reliability_flags_follow_the_pre_specified_rules():
    sv = _river(); ref = _ref(sv)
    ok = onset.reliability_flags(ref, {"forecast_coverage": 1.0, "obs_missing_share": 0.0}, False)
    assert not any(ok.values())
    bad = onset.reliability_flags({**ref, "amplitude_ft": 2.0, "peak_i": ref["onset_i"] + 100}, {"forecast_coverage": 0.5, "obs_missing_share": 0.1}, True)
    assert all(bad.values())


def test_coverage_counts_missing_forecasts_and_observations():
    sv = _river(); sv[110:114] = np.nan; ref = onset.event_reference(np.where(np.isnan(sv), 2.0, sv), 100 + 14, 139)
    f = _shifted_forecast(np.where(np.isnan(sv), 2.0, sv), K, 0); f[100:120] = np.nan
    c = onset.coverage(sv, onset.target_aligned(f, K), ref, K)
    assert c["forecast_coverage"] < 1.0 and c["obs_missing_share"] > 0.0


def test_saved_reproduction_check_matches_phase1e_detection_counts():
    p = Path("reports/phase1e_onset/tables/O7b_reproduction_check_vs_E6.csv")
    if not p.exists():
        pytest.skip("onset-timing outputs not present")
    chk = pd.read_csv(p)
    assert len(chk) == 48 and chk.match.all()
    assert json.loads(Path("reports/phase1e_onset/run_summary.json").read_text())["reproduction_all_match"] is True


def test_saved_onset_table_covers_the_same_18_events_as_phase1e():
    p, q = Path("reports/phase1e_onset/tables/O0_event_reference.csv"), Path("reports/phase1e/tables/E4_per_event.csv")
    if not (p.exists() and q.exists()):
        pytest.skip("outputs not present")
    a = set(pd.read_csv(p).event_start)
    b = set(pd.read_csv(q).event_start)
    assert a == b and len(a) == 18
