"""Data layer of the historical-replay dashboard (E19): turns the SAVED out-of-fold predictions into a JSON document that the dashboard displays.

Exploratory retrospective historical replay using saved out-of-fold predictions. Nothing is retrained, interpolated or smoothed: a forecast that
does not exist is `null`; every curve in the dashboard is a saved forecast row, every metric is recomputed from those rows.
Conventions: one grid step = 15 min, times are UTC; the forecast stored at index i is the forecast MADE at step i (issue time) of the stage at step i + k
(target time = issue time + horizon). Metrics are on the Phase 1D/1E flood window of the event (6 h before the rise onset to the observed peak,
issue times) restricted to issue times that have an observed target.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from . import data, events

STEP_MS = 15 * 60 * 1000
HZ = list(data.HORIZONS)                                  # ['15m', '30m', '1h', '3h']
KSTEP = dict(data.HORIZONS)
DISCLAIMER = ("Exploratory retrospective historical replay using saved out-of-fold predictions. "
              "This is not a live forecasting system or an operational flood-warning service.")
PRE_WINDOW_STEPS = 48                                     # 12 h of context before the rise onset
POST_WINDOW_STEPS = 96                                    # 24 h after the later of the observed peak and the end of the >= 10 ft event
MODEL_SPECS = [
    {"id": "gru", "label": "GRU, 24 h input", "short": "GRU", "source": "phase1d", "col": "pred_gru_{h}_ft", "default": True,
     "note": "Phase 1D, one training seed (seed 0); identical to the Phase 1E 24 h seed 0 run"},
    {"id": "lstm", "label": "LSTM, 24 h input", "short": "LSTM", "source": "phase1d", "col": "pred_lstm_{h}_ft", "default": True, "note": "Phase 1D, one training seed (seed 0)"},
    {"id": "ridge_H", "label": "Ridge regression", "short": "Ridge", "source": "phase1d", "col": "pred_ridge_H_{h}_ft", "default": True, "note": "Phase 1D, engineered stage-history features"},
    {"id": "trend_v2", "label": "Damped trend", "short": "Damped trend", "source": "phase1d", "col": "pred_trend_v2_{h}_ft", "default": True, "note": "Phase 1D, two-parameter heuristic"},
    {"id": "persistence", "label": "Persistence (reference)", "short": "Persistence", "source": "phase1d", "col": "pred_persistence_{h}_ft", "default": False, "note": "the future equals the current stage"},
    {"id": "xgb_H", "label": "XGBoost", "short": "XGBoost", "source": "phase1d", "col": "pred_xgb_H_{h}_ft", "default": False, "note": "Phase 1D, engineered stage-history features"},
    {"id": "gru72_s0", "label": "GRU, 72 h input", "short": "GRU 72 h", "source": "phase1e", "col": "pred_gru72h_s0_{h}_ft", "default": False,
     "note": "Phase 1E, one training seed (seed 0); the pre-registered rule kept the 24 h window"},
]
DET_DEFINITIONS = {"experimental_stage_10ft": ("stage reaches 10 ft", "experimental"), "official_action_25ft": ("stage reaches 25 ft (NWS action stage)", "official"),
                   "experimental_rise_4ft_3h": ("rise of 4 ft within 3 h", "experimental")}
D5B_MODEL = {"gru": "gru", "lstm": "lstm", "ridge_H": "ridge_H", "trend_v2": "trend_v2", "persistence": "persistence", "xgb_H": "xgb_H"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm_ts(x) -> str:
    return str(pd.Timestamp(x))[:16].replace("T", " ")


def _clean(a, ndigits=3):
    """numpy array -> list with NaN as None (never filled or interpolated)."""
    out = np.round(np.asarray(a, dtype=float), ndigits)
    return [None if not np.isfinite(v) else float(v) for v in out]


def load_saved_predictions(ctx, root: Path = Path(".")) -> dict:
    """Saved Phase 1D / 1E out-of-fold predictions on the full project grid, aligned at ISSUE time."""
    n, idx = ctx.n, ctx.s.index
    p4, p5 = root / "reports/phase1d/oof_predictions.csv.gz", root / "reports/phase1e/oof_predictions.csv.gz"
    o4, o5 = pd.read_csv(p4), pd.read_csv(p5)
    srcs = {"phase1d": o4, "phase1e": o5}
    pos = {}
    for name, df in srcs.items():
        ts = pd.DatetimeIndex(pd.to_datetime(df.timestamp_utc)).tz_localize("UTC")
        p = idx.get_indexer(ts)
        if (p < 0).any() or len(np.unique(p)) != len(p):
            raise ValueError(f"{name}: timestamps not unique or not on the project grid")
        fin = np.isfinite(df.stage_ft.values) & np.isfinite(ctx.sv[p])
        if not np.allclose(df.stage_ft.values[fin], ctx.sv[p][fin], atol=1e-6):
            raise ValueError(f"{name}: stage in the saved predictions differs from the project series")
        pos[name] = p
    # fold membership comes from the fold specification (test block boundaries), NOT from which rows the saved files happen to contain
    # (the saved files omit rows whose stage is missing, which would otherwise look like 'outside the test block')
    spec = pd.read_csv(root / "reports/phase1d/fold_specification.csv", parse_dates=["test_start", "test_end"])
    fold_of = np.zeros(n, int)
    for r in spec.itertuples():
        fold_of[(idx >= r.test_start) & (idx <= r.test_end)] = int(r.fold)
    if not np.array_equal(fold_of[pos["phase1d"]], o4.fold.values):
        raise ValueError("fold specification disagrees with the fold column of the saved predictions")
    arrays, target = {}, {}
    for spec in MODEL_SPECS:
        df, p = srcs[spec["source"]], pos[spec["source"]]
        for h in HZ:
            a = np.full(n, np.nan)
            a[p] = df[spec["col"].format(h=h)].values
            arrays[(spec["id"], h)] = a
    for h in HZ:
        t = np.full(n, np.nan)
        t[pos["phase1d"]] = o4[f"target_stage_{h}_ft"].values
        target[h] = t
    band = {}
    for h in HZ:
        stack = []
        for s in (0, 1, 2):
            a = np.full(n, np.nan)
            a[pos["phase1e"]] = o5[f"pred_gru24h_s{s}_{h}_ft"].values
            stack.append(a)
        st = np.vstack(stack)
        with np.errstate(all="ignore"):
            band[h] = (np.nanmin(st, 0), np.nanmax(st, 0))
        both = np.isfinite(arrays[("gru", h)]) & np.isfinite(stack[0])
        if np.abs(arrays[("gru", h)][both] - stack[0][both]).max() > 0.0011:        # Phase 1D GRU == Phase 1E 24 h seed 0 (E7), up to the 3-decimal rounding of the files
            raise ValueError("Phase 1D GRU and Phase 1E 24 h seed 0 predictions disagree")
    flood10 = np.zeros(ctx.n, bool)
    flood10[pos["phase1d"]] = o4.in_flood_window_10ft.values.astype(bool)
    return {"arrays": arrays, "target": target, "band": band, "fold_of": fold_of, "flood10_flag": flood10,
            "sources": {"reports/phase1d/oof_predictions.csv.gz": sha256(p4), "reports/phase1e/oof_predictions.csv.gz": sha256(p5)}}


# ------------------------------------------------------------------ pure metric helpers (tested)
def window_metrics(pred: np.ndarray, target: np.ndarray, mask: np.ndarray) -> dict:
    """Forecast error over the scored issue times: rows with a forecast AND an observed target; nothing is imputed."""
    total = int(mask.sum())
    ok = mask & np.isfinite(pred) & np.isfinite(target)
    n = int(ok.sum())
    if n == 0:
        return {"rows_in_window": total, "rows_scored": 0, "rows_unavailable": total, "rmse": None, "mae": None, "bias": None, "max_abs_err": None}
    e = pred[ok] - target[ok]
    return {"rows_in_window": total, "rows_scored": n, "rows_unavailable": total - n, "rmse": float(np.sqrt(np.mean(e ** 2))), "mae": float(np.mean(np.abs(e))),
            "bias": float(np.mean(e)), "max_abs_err": float(np.max(np.abs(e)))}


def peak_metrics(pred_issue: np.ndarray, peak_i: int, peak_ft: float, onset_i: int, k: int) -> dict:
    """Predicted peak level two ways. (1) the forecast issued h before the observed peak for the peak time (Phase 1D/1E definition; peak ratio = that forecast / observed peak);
    (2) the maximum of the forecast series at target times from 6 h before the onset to 2 h after (peak time + h), with its time relative to the observed peak."""
    pi = peak_i - k
    pf = float(pred_issue[pi]) if 0 <= pi < len(pred_issue) and np.isfinite(pred_issue[pi]) else None
    lo, hi = max(0, onset_i - 24 - k), min(len(pred_issue) - 1, peak_i + 8)           # issue indices whose target times fall in [onset - 6 h, peak + h + 2 h]
    seg = pred_issue[lo:hi + 1]
    if np.isfinite(seg).any():
        j = lo + int(np.nanargmax(seg))
        fmax, tlag = float(pred_issue[j]), (j + k - peak_i) * 0.25
    else:
        fmax, tlag = None, None
    return {"peak_forecast_ft": pf, "peak_ratio": (pf / peak_ft if pf is not None else None), "fc_max_ft": fmax, "fc_max_ratio": (fmax / peak_ft if fmax is not None else None),
            "fc_max_time_minus_peak_h": tlag}


def missing_runs(isnan: np.ndarray) -> list:
    """[start, end] index pairs (inclusive) of runs of True."""
    st, en = events.runs_idx(isnan)
    return [[int(a), int(b)] for a, b in zip(st, en)]


def window_missing_share(isnan: np.ndarray, steps: int) -> np.ndarray:
    """Share of the `steps` samples ending at each index (inclusive) that are missing; NaN where the window is incomplete at the start of the record."""
    c = np.r_[0, np.cumsum(isnan.astype(float))]
    out = np.full(len(isnan), np.nan)
    out[steps - 1:] = (c[steps:] - c[:-steps]) / steps
    return out


# ------------------------------------------------------------------ assembly
def unavailable_reason_codes(ctx, saved: dict, idxs: np.ndarray, h: str) -> dict:
    """Why a forecast row does not exist (counts over issue indices `idxs`), using only the project's own eligibility ingredients."""
    k = KSTEP[h]
    fold = saved["fold_of"][idxs]
    sv = ctx.sv
    tgt_i = np.minimum(idxs + k, ctx.n - 1)
    req = ctx.H[data.REQUIRED_COLS].notna().all(axis=1).values[idxs]
    have = np.isfinite(saved["arrays"][("gru", h)][idxs])
    miss = ~have
    reasons = {
        "outside the out-of-fold test blocks (no out-of-fold forecast exists)": int((miss & (fold == 0)).sum()),
        "stage missing at the issue time": int((miss & (fold > 0) & np.isnan(sv[idxs])).sum()),
        "observed target missing": int((miss & (fold > 0) & np.isfinite(sv[idxs]) & np.isnan(sv[tgt_i])).sum()),
        "recent-history gap (15, 30 or 60 min change unavailable)": int((miss & (fold > 0) & np.isfinite(sv[idxs]) & np.isfinite(sv[tgt_i]) & ~req).sum()),
    }
    reasons["other (e.g. rainfall-input validity rule)"] = int(miss.sum()) - sum(reasons.values())
    return reasons


def build_event_records(ctx, saved: dict, d5b: pd.DataFrame, o7: pd.DataFrame, fold_spec: pd.DataFrame) -> list:
    sv, idx, n = ctx.sv, ctx.s.index, ctx.n
    fold_of = saved["fold_of"]
    ev_all = ctx.ev_all["experimental_stage_10ft"]
    ev = ev_all[fold_of[ev_all.i0.values] > 0].reset_index(drop=True)
    isnan = np.isnan(sv)
    miss24, miss72 = window_missing_share(isnan, 96), window_missing_share(isnan, 288)
    off = ctx.ev_all["official_action_25ft"]
    clusters = pd.Series([int(ctx.groups[int(i)]) for i in ev.i0]).value_counts()
    det_models = {"gru": "gru", "lstm": "lstm", "ridge_H": "ridge_H", "trend_v2": "trend_v2", "persistence": "persistence", "xgb_H": "xgb_H"}
    d5 = d5b.assign(start=d5b.event_start.map(_norm_ts))
    o7s = o7[(o7.window_h == 72) & (o7.seed == 0)].assign(start=lambda d: d.event_start.map(_norm_ts))
    recs = []
    for r in ev.itertuples():
        i0, peak_i = int(r.i0), int(r.peak_i)
        onset_i = events.rise_onset_index(sv, i0)
        lo, hi = max(0, onset_i - PRE_WINDOW_STEPS), min(n - 1, max(peak_i, int(r.i1)) + POST_WINDOW_STEPS)
        sl = slice(lo, hi + 1)
        wm_full = ctx.win_mask(ev.iloc[[int(r.Index)]], "exceed")
        fw = np.flatnonzero(wm_full)
        fold = int(fold_of[i0])
        fs = fold_spec[fold_spec.fold == fold].iloc[0]
        idxs_w = np.arange(lo, hi + 1)
        fc, metrics, reasons = {}, {}, {}
        for spec in MODEL_SPECS:
            fc[spec["id"]], metrics[spec["id"]] = {}, {}
            for h in HZ:
                a = saved["arrays"][(spec["id"], h)]
                fc[spec["id"]][h] = _clean(a[sl])
                m = window_metrics(a, saved["target"][h], wm_full)
                m.update(peak_metrics(a, peak_i, float(r.peak_ft), onset_i, KSTEP[h]))
                metrics[spec["id"]][h] = m
        for h in HZ:
            reasons[h] = unavailable_reason_codes(ctx, saved, idxs_w, h)
        band = {h: {"lo": _clean(saved["band"][h][0][sl]), "hi": _clean(saved["band"][h][1][sl])} for h in HZ}
        # detection (fixed alarm rule): the evaluated event and the official / rapid-rise events inside the plotted window
        det = []
        for defn, (lab, kind) in DET_DEFINITIONS.items():
            evs = ctx.ev_all[defn]
            for e in evs[(evs.i0 >= lo) & (evs.i0 <= hi)].itertuples():
                key = _norm_ts(idx[int(e.i0)])
                if int(fold_of[int(e.i0)]) == 0:
                    continue
                res = {}
                for mid in list(det_models) + ["gru72_s0"]:
                    res[mid] = {}
                    for h in HZ:
                        if mid == "gru72_s0":
                            q = o7s[(o7s.definition == defn) & (o7s.horizon == h) & (o7s.start == key)]
                        else:
                            q = d5[(d5.definition == defn) & (d5.horizon == h) & (d5.model == mid) & (d5.start == key)]
                        if len(q) == 0:
                            res[mid][h] = None
                        else:
                            q0 = q.iloc[0]
                            res[mid][h] = {"status": str(q0.status), "lead_h": (None if pd.isna(q0.lead_h) else float(q0.lead_h))}
                det.append({"definition": defn, "label": lab, "kind": kind, "start_ms": int(idx[int(e.i0)].timestamp() * 1000), "start": key, "peak_ft": float(e.peak_ft), "is_primary": bool(defn == "experimental_stage_10ft" and int(e.i0) == i0), "results": res})
        det.sort(key=lambda d: (not d["is_primary"], d["start_ms"]))
        obs_runs = missing_runs(isnan[sl])
        longest = max([(b - a + 1) * 0.25 for a, b in obs_runs], default=0.0)
        prov = ctx.prov[sl].astype(bool)
        official_inside = [{"start": _norm_ts(idx[int(e.i0)]), "peak_ft": float(e.peak_ft)} for e in off[(off.i0 >= lo) & (off.i0 <= hi)].itertuples()]
        fw_rows = fw[fw < n]
        recs.append({
            "id": _norm_ts(idx[i0]).replace(" ", "T"), "start": _norm_ts(idx[i0]), "onset": _norm_ts(idx[onset_i]), "peak_time": _norm_ts(idx[peak_i]), "end": _norm_ts(idx[int(r.i1)]),
            "peak_ft": float(r.peak_ft), "official_ge_25ft": bool(r.peak_ft >= 25), "official_events_inside": official_inside, "provisional": bool(ctx.prov[i0:int(r.i1) + 1].any()),
            "fold": fold, "storm_cluster": int(ctx.groups[i0]), "events_in_cluster": int(clusters[int(ctx.groups[i0])]),
            "fold_train_end": _norm_ts(fs.train_end), "fold_test_start": _norm_ts(fs.test_start), "fold_test_end": _norm_ts(fs.test_end),
            "t0_ms": int(idx[lo].timestamp() * 1000), "step_ms": STEP_MS, "n": int(hi - lo + 1),
            "i0_rel": i0 - lo, "onset_rel": onset_i - lo, "peak_rel": peak_i - lo, "end_rel": int(r.i1) - lo,
            "window_rel": [int(fw_rows.min() - lo), int(fw_rows.max() - lo)],
            "obs": _clean(sv[sl]), "prov_runs": missing_runs(prov), "obs_missing_runs": obs_runs,
            "fc": fc, "band_gru24": band, "metrics": metrics, "detection": det,
            "quality": {"window_samples": int(hi - lo + 1), "obs_missing_samples": int(isnan[sl].sum()), "obs_missing_share": float(isnan[sl].mean()), "longest_obs_gap_h": float(longest),
                        "flood_window_issue_times": int(len(fw_rows)),
                        "history24_any_missing_share": float(np.nanmean(miss24[fw_rows] > 0)), "history72_any_missing_share": float(np.nanmean(miss72[fw_rows] > 0)),
                        "provisional_samples": int(prov.sum()), "unavailable_forecast_reasons": reasons}})
    return recs


def pooled_flood_window(ctx, saved: dict) -> dict:
    """Pooled RMSE over the union of the 18 evaluated flood windows (equals the Phase 1D/1E 'flood windows >= 10 ft' subset), recomputed from the saved rows."""
    sv, fold_of = ctx.sv, saved["fold_of"]
    ev_all = ctx.ev_all["experimental_stage_10ft"]
    ev = ev_all[fold_of[ev_all.i0.values] > 0].reset_index(drop=True)
    mask = ctx.win_mask(ev, "exceed")
    out = {}
    for spec in MODEL_SPECS:
        out[spec["id"]] = {h: window_metrics(saved["arrays"][(spec["id"], h)], saved["target"][h], mask) for h in HZ}
    return out


def build_document(ctx, root: Path = Path(".")) -> dict:
    saved = load_saved_predictions(ctx, root)
    fold_spec = pd.read_csv(root / "reports/phase1d/fold_specification.csv")
    d5b = pd.read_csv(root / "reports/phase1d/tables/D5b_fixed_rule_per_event.csv")
    o7_path = root / "reports/phase1e_onset/tables/O7_fixed_rule_lead_per_event.csv"
    o7 = pd.read_csv(o7_path)
    recs = build_event_records(ctx, saved, d5b, o7, fold_spec)
    sources = dict(saved["sources"])
    for rel in ("reports/phase1d/tables/D5b_fixed_rule_per_event.csv", "reports/phase1e_onset/tables/O7_fixed_rule_lead_per_event.csv", "reports/phase1d/fold_specification.csv"):
        sources[rel] = sha256(root / rel)
    return {"meta": {"title": "Guadalupe River at Spring Branch, TX (USGS 08167500): historical replay of out-of-fold forecasts", "disclaimer": DISCLAIMER,
                     "horizons": HZ, "step_minutes": 15, "timezone": "UTC", "models": MODEL_SPECS, "sources": sources, "n_events": len(recs),
                     "generated_from": "scripts/build_replay_dashboard.py", "definitions": {k: v[0] for k, v in DET_DEFINITIONS.items()}},
            "pooled_flood_window": pooled_flood_window(ctx, saved), "events": recs}
