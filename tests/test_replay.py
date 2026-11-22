"""Historical-replay dashboard (E19): every displayed number must trace to the saved out-of-fold predictions; alignment, gaps and metrics are checked here."""
import functools
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from flashflood import events, replay

ROOT = Path(".")
NEEDED = ["reports/phase1d/oof_predictions.csv.gz", "reports/phase1e/oof_predictions.csv.gz", "reports/phase1d/tables/D4_per_event.csv", "reports/phase1d/tables/D5b_fixed_rule_per_event.csv",
          "reports/phase1e/tables/E1_pooled_metrics.csv", "reports/phase1e/tables/E4_per_event.csv", "reports/phase1e_onset/tables/O7_fixed_rule_lead_per_event.csv"]
artifacts = pytest.mark.skipif(not all((ROOT / p).exists() for p in NEEDED), reason="saved prediction artifacts not present")
EXACT_DISCLAIMER = ("Exploratory retrospective historical replay using saved out-of-fold predictions. "
                    "This is not a live forecasting system or an operational flood-warning service.")


@functools.lru_cache(maxsize=1)
def _doc():
    from flashflood import experiment
    ctx = experiment.build_context()
    return ctx, replay.build_document(ctx, ROOT)


# ------------------------------------------------------------------ pure helpers
def test_disclaimer_is_the_required_text():
    assert replay.DISCLAIMER == EXACT_DISCLAIMER


def test_clean_keeps_gaps_as_none_and_never_fills():
    assert replay._clean(np.array([1.23456, np.nan, np.inf, -2.0])) == [1.235, None, None, -2.0]


def test_window_metrics_skip_missing_rows_and_count_them():
    pred = np.array([1.0, np.nan, 3.0, 5.0, 9.0]); target = np.array([1.5, 2.0, 2.0, np.nan, 9.0]); mask = np.array([True, True, True, True, False])
    m = replay.window_metrics(pred, target, mask)
    assert m["rows_in_window"] == 4 and m["rows_scored"] == 2 and m["rows_unavailable"] == 2          # row 1 has no forecast, row 3 has no observed target, row 4 is outside the window
    assert m["rmse"] == pytest.approx(np.sqrt((0.25 + 1.0) / 2)) and m["bias"] == pytest.approx((-0.5 + 1.0) / 2) and m["max_abs_err"] == pytest.approx(1.0)
    none = replay.window_metrics(np.full(3, np.nan), np.ones(3), np.ones(3, bool))
    assert none["rows_scored"] == 0 and none["rmse"] is None


def test_peak_metrics_use_the_forecast_issued_h_before_the_peak_and_the_target_time_of_the_maximum():
    n, k = 60, 4
    pred = np.full(n, 2.0); pred[40 - k] = 9.0           # forecast issued at 36 for the stage at 40 (the peak time)
    pred[44 - k] = 12.0                                    # a higher forecast, for target time 44 (peak + 1 h)
    m = replay.peak_metrics(pred, peak_i=40, peak_ft=10.0, onset_i=30, k=k)
    assert m["peak_forecast_ft"] == 9.0 and m["peak_ratio"] == pytest.approx(0.9)
    assert m["fc_max_ft"] == 12.0 and m["fc_max_time_minus_peak_h"] == pytest.approx(1.0)
    pred[36] = np.nan
    assert replay.peak_metrics(pred, 40, 10.0, 30, k)["peak_forecast_ft"] is None


def test_missing_runs_and_history_share():
    m = np.array([0, 1, 1, 0, 0, 1, 0], bool)
    assert replay.missing_runs(m) == [[1, 2], [5, 5]]
    s = replay.window_missing_share(m, 3)
    assert np.isnan(s[:2]).all() and s[2] == pytest.approx(2 / 3) and s[6] == pytest.approx(1 / 3)


# ------------------------------------------------------------------ the built document versus the saved files
@artifacts
def test_event_set_matches_phase1e_and_official_flags():
    _, doc = _doc()
    e4 = pd.read_csv("reports/phase1e/tables/E4_per_event.csv").drop_duplicates("event_start")
    assert {e["start"] for e in doc["events"]} == set(e4.event_start) and len(doc["events"]) == 18
    assert sum(e["official_ge_25ft"] for e in doc["events"]) == 5
    assert [e for e in doc["events"] if e["start"] == "2026-07-15 18:30"][0]["official_events_inside"].__len__() == 2


@artifacts
def test_forecasts_are_the_saved_rows_at_the_right_issue_time():
    ctx, doc = _doc()
    o4 = pd.read_csv("reports/phase1d/oof_predictions.csv.gz").assign(ts=lambda d: pd.to_datetime(d.timestamp_utc))
    o4 = o4.set_index("ts")
    o5 = pd.read_csv("reports/phase1e/oof_predictions.csv.gz").assign(ts=lambda d: pd.to_datetime(d.timestamp_utc)).set_index("ts")
    checked = 0
    for e in doc["events"]:
        times = pd.to_datetime(e["t0_ms"] + np.arange(e["n"]) * e["step_ms"], unit="ms")
        for spec in replay.MODEL_SPECS:
            src = o4 if spec["source"] == "phase1d" else o5
            for h in replay.HZ:
                col = spec["col"].format(h=h)
                saved = src[col].reindex(times).values
                got = np.array([np.nan if v is None else v for v in e["fc"][spec["id"]][h]])
                assert np.array_equal(np.isnan(saved), np.isnan(got)), (e["id"], spec["id"], h)       # a missing forecast stays missing: nothing is created or filled
                fin = np.isfinite(saved)
                assert np.allclose(saved[fin], got[fin], atol=5e-4)
                checked += int(fin.sum())
    assert checked > 100000


@artifacts
def test_horizon_steps_align_forecast_rows_with_the_observed_target():
    """The target stage saved with each forecast row equals the observed stage k steps later, for every horizon: this fixes the issue-time -> target-time mapping."""
    ctx, doc = _doc()
    o4 = pd.read_csv("reports/phase1d/oof_predictions.csv.gz").assign(ts=lambda d: pd.to_datetime(d.timestamp_utc)).set_index("ts")
    K = {"15m": 1, "30m": 2, "1h": 4, "3h": 12}
    for e in doc["events"]:
        times = pd.to_datetime(e["t0_ms"] + np.arange(e["n"]) * e["step_ms"], unit="ms")
        obs = np.array([np.nan if v is None else v for v in e["obs"]])
        for h, k in K.items():
            tgt = o4[f"target_stage_{h}_ft"].reindex(times).values[: e["n"] - k]
            ob = obs[k:]
            ok = np.isfinite(tgt) & np.isfinite(ob)
            assert ok.sum() > 0 and np.allclose(tgt[ok], ob[ok], atol=1e-3), (e["id"], h)
            per = np.array([np.nan if v is None else v for v in e["fc"]["persistence"][h]])
            ok2 = np.isfinite(per) & np.isfinite(obs)
            assert np.allclose(per[ok2], obs[ok2], atol=1e-3)                    # persistence forecast issued at t equals the stage observed at t


@artifacts
def test_observed_series_is_the_project_stage_series_with_gaps_kept():
    ctx, doc = _doc()
    for e in doc["events"]:
        lo = int(ctx.s.index.get_loc(pd.Timestamp(e["t0_ms"], unit="ms", tz="UTC")))
        ref = np.round(ctx.sv[lo:lo + e["n"]], 3)
        got = np.array([np.nan if v is None else v for v in e["obs"]])
        assert np.array_equal(np.isnan(ref), np.isnan(got)) and np.allclose(ref[np.isfinite(ref)], got[np.isfinite(got)])
        assert e["quality"]["obs_missing_samples"] == int(np.isnan(ref).sum())
        assert all(np.isnan(ref[a:b + 1]).all() for a, b in e["obs_missing_runs"])


@artifacts
def test_event_metrics_reproduce_the_phase1d_table_up_to_file_rounding():
    _, doc = _doc()
    d4 = pd.read_csv("reports/phase1d/tables/D4_per_event.csv")
    d4 = d4[d4.definition == "experimental_stage_10ft"]
    n = 0
    for e in doc["events"]:
        for h in replay.HZ:
            for mid in ("gru", "lstm", "ridge_H", "trend_v2", "persistence", "xgb_H"):
                r = d4[(d4.event_start == e["start"]) & (d4.horizon == h) & (d4.model == mid)]
                assert len(r) == 1
                m = e["metrics"][mid][h]
                assert m["rmse"] == pytest.approx(float(r.window_rmse_ft.iloc[0]), abs=2e-3), (e["start"], h, mid)
                assert m["rows_scored"] == int(r.window_rows.iloc[0])
                assert m["peak_forecast_ft"] == pytest.approx(float(r.peak_forecast_ft.iloc[0]), abs=2e-3)
                assert m["peak_ratio"] == pytest.approx(float(r.peak_ratio.iloc[0]), abs=2e-3)
                n += 1
    assert n == 18 * 4 * 6


@artifacts
def test_pooled_flood_window_reproduces_phase1e_e1():
    _, doc = _doc()
    e1 = pd.read_csv("reports/phase1e/tables/E1_pooled_metrics.csv")
    e1 = e1[e1.subset == "flood_windows_10ft"]
    for h in replay.HZ:
        pooled = doc["pooled_flood_window"]
        assert pooled["gru"][h]["rows_scored"] == int(e1[(e1.horizon == h) & (e1.window_h == "24")].n_rows.iloc[0])
        g24 = e1[(e1.horizon == h) & (e1.window_h == "24")].rmse_seed0.iloc[0]
        g72 = e1[(e1.horizon == h) & (e1.window_h == "72")].rmse_seed0.iloc[0]
        assert pooled["gru"][h]["rmse"] == pytest.approx(g24, abs=2e-3) and pooled["gru72_s0"][h]["rmse"] == pytest.approx(g72, abs=2e-3)
        for mid in ("persistence", "trend_v2", "ridge_H", "xgb_H"):
            ref = e1[(e1.horizon == h) & (e1.window_h == mid)].rmse_ft_seed_mean.iloc[0]
            assert pooled[mid][h]["rmse"] == pytest.approx(ref, abs=2e-3)


@artifacts
def test_detection_statuses_equal_the_saved_tables():
    _, doc = _doc()
    d5 = pd.read_csv("reports/phase1d/tables/D5b_fixed_rule_per_event.csv").assign(start=lambda d: d.event_start.map(replay._norm_ts))
    n = 0
    for e in doc["events"]:
        for d in e["detection"]:
            for mid in ("gru", "lstm", "ridge_H", "trend_v2", "persistence", "xgb_H"):
                for h in replay.HZ:
                    q = d5[(d5.definition == d["definition"]) & (d5.start == d["start"]) & (d5.model == mid) & (d5.horizon == h)]
                    got = d["results"][mid][h]
                    if len(q) == 0:
                        assert got is None
                    else:
                        assert got["status"] == q.status.iloc[0]
                        assert (got["lead_h"] is None) == bool(pd.isna(q.lead_h.iloc[0]))
                        n += 1
    assert n > 200
    # the evaluated >= 10 ft event is always the first (primary) detection row
    assert all(e["detection"][0]["is_primary"] and e["detection"][0]["start"] == e["start"] for e in doc["events"])


@artifacts
def test_unavailable_forecast_counts_are_consistent():
    ctx, doc = _doc()
    for e in doc["events"]:
        for h in replay.HZ:
            n_none = sum(v is None for v in e["fc"]["gru"][h])
            assert sum(e["quality"]["unavailable_forecast_reasons"][h].values()) == n_none
            m = e["metrics"]["gru"][h]
            assert m["rows_scored"] + m["rows_unavailable"] == m["rows_in_window"]


@artifacts
def test_html_embeds_the_document_shows_the_disclaimer_and_is_self_contained():
    html_path = Path("dashboard/replay/index.html")
    if not html_path.exists():
        pytest.skip("dashboard not built")
    html = html_path.read_text()
    assert html.count(EXACT_DISCLAIMER) >= 3                                            # banner, footer, about page (the latter rendered from the data)
    payload = re.search(r'<script id="replay-data" type="application/json">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</")
    emb = json.loads(payload)
    _, doc = _doc()
    assert emb["meta"]["disclaimer"] == EXACT_DISCLAIMER
    assert [e["id"] for e in emb["events"]] == [e["id"] for e in doc["events"]]
    assert emb["events"][5]["metrics"]["gru"]["3h"]["rmse"] == pytest.approx(doc["events"][5]["metrics"]["gru"]["3h"]["rmse"])
    assert not re.search(r'(src|href)\s*=\s*["\']https?://', html) and "@import" not in html          # no external resources: works offline
    assert "fetch(" not in html and "XMLHttpRequest" not in html                           # no network calls: replay of saved data only
    for banned in ("warning level", "alert level", "send alert", "live feed"):
        assert banned not in html.lower()


@artifacts
def test_reason_codes_use_fold_boundaries_not_row_presence():
    """'Outside the test block' must mean outside [test_start, test_end] of the event's fold; rows missing because the stage is missing are a different reason."""
    ctx, doc = _doc()
    for e in doc["events"]:
        t0, st = e["t0_ms"], e["step_ms"]
        lo = pd.Timestamp(e["fold_test_start"], tz="UTC").value // 10 ** 6
        hi = pd.Timestamp(e["fold_test_end"], tz="UTC").value // 10 ** 6
        times = t0 + np.arange(e["n"]) * st
        expected_outside = int(((times < lo) | (times > hi)).sum())
        for h in replay.HZ:
            r = e["quality"]["unavailable_forecast_reasons"][h]
            assert r["outside the out-of-fold test blocks (no out-of-fold forecast exists)"] == expected_outside, (e["id"], h)
    e = [x for x in doc["events"] if x["start"] == "2024-07-24 14:45"][0]
    r3 = e["quality"]["unavailable_forecast_reasons"]["3h"]
    assert r3["stage missing at the issue time"] > 0 and r3["outside the out-of-fold test blocks (no out-of-fold forecast exists)"] == 0
