"""Onset-timing diagnostics for saved forecasts (docs/PHASE1E_ONSET_PROTOCOL.md, experiment E18).

Pure array functions: they take the observed stage `sv` on the project's 15-min grid, a forecast series aligned at ISSUE time
(`Fiss[i]` = forecast, made at step i, of the stage at step i + k) and an event reference. Nothing here trains or alters a model.
Conventions: one step = 15 min; times are returned in hours; lag = (time the forecast shows a level) - (time the river reached it);
lead = horizon - lag = (time the river reached the level) - (issue time of the first forecast that shows it).
"""
from __future__ import annotations

import numpy as np

from . import events

STEP_H = 0.25
FRACS = (0.1, 0.5, 0.9)
PRE_STEPS = 24            # 6 h before the rise onset (same offset as the Phase 1D/1E flood window)
POST_STEPS = 8            # 2 h after (peak + horizon) when searching for the forecast maximum / arrival
ANTICIPATION_FT = 0.5     # the tolerance that already defines the rise onset
SENSITIVITY_FT = (0.25, 0.5, 1.0)


def target_aligned(fiss: np.ndarray, k: int) -> np.ndarray:
    """Forecast series indexed by TARGET time: out[j] = forecast issued at j - k."""
    out = np.full(len(fiss), np.nan)
    out[k:] = fiss[:-k] if k else fiss
    return out


def first_at_or_above(arr: np.ndarray, level: float, lo: int, hi: int):
    """Index of the first finite sample >= level in [lo, hi] (inclusive), else None."""
    lo, hi = max(0, int(lo)), min(len(arr) - 1, int(hi))
    if hi < lo:
        return None
    seg = arr[lo:hi + 1]
    ok = np.isfinite(seg) & (np.nan_to_num(seg, nan=-np.inf) >= level)
    w = np.flatnonzero(ok)
    return int(lo + w[0]) if len(w) else None


def event_reference(sv: np.ndarray, i0: int, peak_i: int, back_steps: int = 288) -> dict:
    """Rise onset, baseline and amplitude from the existing event definitions (events.rise_onset_index; baseline = minimum of the preceding 72 h)."""
    onset = events.rise_onset_index(sv, i0, back_steps)
    lo = max(0, i0 - back_steps)
    base = float(np.nanmin(sv[lo:i0 + 1]))
    peak = float(sv[peak_i])
    return {"i0": int(i0), "onset_i": int(onset), "peak_i": int(peak_i), "baseline_ft": base, "peak_ft": peak, "amplitude_ft": peak - base}


def level_timing(sv: np.ndarray, ftar: np.ndarray, ref: dict, k: int, fracs=FRACS) -> dict:
    """Arrival of the levels b + f*A in the observation and in the forecast series (target-time aligned). Not-reached forecasts give NaN, never an imputed value."""
    o, p, b, a = ref["onset_i"], ref["peak_i"], ref["baseline_ft"], ref["amplitude_ft"]
    h_hours = k * STEP_H
    out: dict = {}
    for f in fracs:
        level = b + f * a
        t_o = first_at_or_above(sv, level, o, p)
        t_f = first_at_or_above(ftar, level, o - PRE_STEPS, p + k + POST_STEPS)
        tag = f"f{int(round(f * 100)):02d}"
        out[f"level_{tag}_ft"] = level
        out[f"obs_arrival_{tag}_i"] = t_o
        out[f"fc_arrival_{tag}_i"] = t_f
        lag = (t_f - t_o) * STEP_H if (t_o is not None and t_f is not None) else np.nan
        out[f"lag_{tag}_h"] = lag
        out[f"lead_{tag}_h"] = h_hours - lag if np.isfinite(lag) else np.nan
        out[f"reached_{tag}"] = t_f is not None
        # issue time of the first forecast that shows the level, relative to the rise onset (negative = issued before the river began to rise)
        out[f"issue_vs_onset_{tag}_h"] = (t_f - k - o) * STEP_H if t_f is not None else np.nan
    lag10, lag90 = out.get("lag_f10_h", np.nan), out.get("lag_f90_h", np.nan)
    out["catch_up_h"] = lag10 - lag90 if (np.isfinite(lag10) and np.isfinite(lag90)) else np.nan
    return out


def peak_timing(sv: np.ndarray, ftar: np.ndarray, ref: dict, k: int) -> dict:
    o, p = ref["onset_i"], ref["peak_i"]
    lo, hi = max(0, o - PRE_STEPS), min(len(ftar) - 1, p + k + POST_STEPS)
    seg = ftar[lo:hi + 1]
    if not np.isfinite(seg).any():
        return {"fc_max_ft": np.nan, "fc_max_ratio": np.nan, "fc_peak_time_lag_h": np.nan}
    j = lo + int(np.nanargmax(seg))
    return {"fc_max_ft": float(ftar[j]), "fc_max_ratio": float(ftar[j] / ref["peak_ft"]), "fc_peak_time_lag_h": (j - p) * STEP_H}


def pre_onset(sv: np.ndarray, fiss: np.ndarray, ref: dict, k: int, thr: float = ANTICIPATION_FT, sens=SENSITIVITY_FT) -> dict:
    """Genuine anticipation: forecasts issued while the river has not yet risen (stage <= baseline + 0.5 ft, issue times from 6 h before the onset to the onset)
    that already predict a rise of at least `thr` over the horizon."""
    o, i0, b = ref["onset_i"], ref["i0"], ref["baseline_ft"]
    idx = np.arange(max(0, o - PRE_STEPS), o + 1)
    s_i, f_i = sv[idx], fiss[idx]
    ok = np.isfinite(s_i) & np.isfinite(f_i) & (s_i <= b + ANTICIPATION_FT)
    out: dict = {"n_qualifying_issue_times": int(ok.sum())}
    if not ok.any():
        out.update({"max_predicted_change_ft": np.nan, "realised_max_change_ft": np.nan, "anticipation_flag": False, "first_flag_issue_i": None,
                    "first_flag_lead_vs_onset_h": np.nan, "first_flag_lead_vs_i0_h": np.nan, "realised_change_at_first_flag_ft": np.nan})
        out.update({f"flag_at_{t:g}ft": False for t in sens})
        return out
    ii = idx[ok]
    dhat = fiss[ii] - sv[ii]
    tgt = ii + k
    real = np.where(tgt < len(sv), sv[np.minimum(tgt, len(sv) - 1)] - sv[ii], np.nan)
    out["max_predicted_change_ft"] = float(np.max(dhat))
    out["realised_max_change_ft"] = float(np.nanmax(real)) if np.isfinite(real).any() else np.nan
    hit = np.flatnonzero(dhat >= thr)
    out["anticipation_flag"] = bool(len(hit))
    if len(hit):
        i = int(ii[hit[0]])
        out.update({"first_flag_issue_i": i, "first_flag_lead_vs_onset_h": (o - i) * STEP_H, "first_flag_lead_vs_i0_h": (i0 - i) * STEP_H,
                    "realised_change_at_first_flag_ft": float(real[hit[0]]) if np.isfinite(real[hit[0]]) else np.nan})
    else:
        out.update({"first_flag_issue_i": None, "first_flag_lead_vs_onset_h": np.nan, "first_flag_lead_vs_i0_h": np.nan, "realised_change_at_first_flag_ft": np.nan})
    for t in sens:
        out[f"flag_at_{t:g}ft"] = bool((dhat >= t).any())
    return out


def background_rate(sv: np.ndarray, fiss: np.ndarray, exclude: np.ndarray, thr: float = ANTICIPATION_FT) -> dict:
    """Share of issue times OUTSIDE every flood/rapid-rise window with a predicted change >= thr: how often the anticipation flag fires for no event."""
    ok = np.isfinite(sv) & np.isfinite(fiss) & ~exclude
    d = fiss[ok] - sv[ok]
    return {"rows": int(ok.sum()), "share_ge_thr": float(np.mean(d >= thr)) if ok.any() else np.nan, "n_ge_thr": int((d >= thr).sum())}


def coverage(sv: np.ndarray, ftar: np.ndarray, ref: dict, k: int) -> dict:
    o, p = ref["onset_i"], ref["peak_i"]
    seg_f = ftar[o:min(len(ftar), p + k + 1)]
    seg_o = sv[max(0, o - PRE_STEPS):p + 1]
    return {"forecast_coverage": float(np.isfinite(seg_f).mean()) if len(seg_f) else 0.0, "obs_missing_share": float(np.isnan(seg_o).mean()) if len(seg_o) else 1.0}


def reliability_flags(ref: dict, cov: dict, provisional: bool) -> dict:
    """Pre-specified flags (protocol section 4)."""
    return {"R1_low_forecast_coverage": cov["forecast_coverage"] < 0.8, "R2_obs_missing_gt5pct": cov["obs_missing_share"] > 0.05,
            "R3_ambiguous_onset": (ref["peak_i"] - ref["onset_i"]) * STEP_H > 24.0, "R4_low_amplitude": ref["amplitude_ft"] < 3.0, "R5_provisional": bool(provisional)}


def event_timing_row(sv: np.ndarray, fiss: np.ndarray, ref: dict, k: int) -> dict:
    """Everything for one event / horizon / forecast variant, as a flat dict."""
    ftar = target_aligned(fiss, k)
    return {**level_timing(sv, ftar, ref, k), **peak_timing(sv, ftar, ref, k), **pre_onset(sv, fiss, ref, k), **coverage(sv, ftar, ref, k)}
