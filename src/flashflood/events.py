"""Event, storm-cluster, alarm and matching logic exactly as defined in docs/PHASE1A_PROTOCOL.md."""
import numpy as np
import pandas as pd

STEP_H = 0.25


def runs_idx(mask) -> tuple:
    m = np.asarray(mask).astype(int)
    d = np.diff(np.r_[0, m, 0])
    return np.where(d == 1)[0], np.where(d == -1)[0] - 1


def merge_runs(st, en, min_gap_steps: float) -> list:
    """Merge runs whose separation (in steps) is < min_gap_steps."""
    merged: list = []
    for a, b in zip(st, en):
        if merged and (a - merged[-1][1] - 1) < min_gap_steps:
            merged[-1][1] = int(b)
        else:
            merged.append([int(a), int(b)])
    return merged


def _events_from_mask(index, mask, merge_h: float) -> pd.DataFrame:
    st, en = runs_idx(mask)
    m = merge_runs(st, en, merge_h / STEP_H)
    return pd.DataFrame({"i0": [a for a, _ in m], "i1": [b for _, b in m],
                         "t0": [index[a] for a, _ in m], "t1": [index[b] for _, b in m]})


def exceedance_events(s: pd.Series, thr: float, merge_h: float = 24.0) -> pd.DataFrame:
    ev = _events_from_mask(s.index, np.nan_to_num(s.values, nan=-9e9) >= thr, merge_h)
    if len(ev):
        ev["peak_ft"] = [float(np.nanmax(s.values[a:b + 1])) for a, b in zip(ev.i0, ev.i1)]
        ev["peak_i"] = [a + int(np.nanargmax(s.values[a:b + 1])) for a, b in zip(ev.i0, ev.i1)]
    return ev


def rise_series(s: pd.Series, hours: int = 3) -> pd.Series:
    return s - s.shift(hours * 4)


def rapid_rise_events(s: pd.Series, rise_ft: float, merge_h: float = 24.0) -> pd.DataFrame:
    z = np.nan_to_num(rise_series(s).values, nan=-9e9) >= rise_ft
    ev = _events_from_mask(s.index, z, merge_h)
    if len(ev):
        ev["peak_ft"] = [float(np.nanmax(s.values[a:b + 1])) for a, b in zip(ev.i0, ev.i1)]
        ev["peak_i"] = [a + int(np.nanargmax(s.values[a:b + 1])) for a, b in zip(ev.i0, ev.i1)]
    return ev


def rise_onset_index(s_vals: np.ndarray, i0: int, back_steps: int = 288, tol_ft: float = 0.5) -> int:
    """Last time within tol_ft of the preceding-72 h minimum before the first exceedance."""
    lo = max(0, i0 - back_steps)
    pre = s_vals[lo:i0 + 1]
    if not np.isfinite(pre).any():
        return i0
    base = np.nanmin(pre)
    return lo + int(np.where(pre <= base + tol_ft)[0][-1])


def storm_clusters(s: pd.Series, elevated_ft: float = 5.0, rise_ft: float = 1.0, merge_h: float = 72.0) -> pd.DataFrame:
    """Elevated = stage >= elevated_ft or 3-h rise >= rise_ft; elevated samples < merge_h apart form one cluster."""
    elev = ((s >= elevated_ft) | (rise_series(s) >= rise_ft)).fillna(False).values
    ev = _events_from_mask(s.index, elev, merge_h)
    ev.insert(0, "cluster_id", range(1, len(ev) + 1))
    return ev


def alarm_state(raw: np.ndarray, off_steps: int = 4) -> np.ndarray:
    """Hysteresis: ON at first raw flag, OFF after `off_steps` consecutive steps without a raw flag."""
    raw = np.asarray(raw, dtype=bool)
    st, en = runs_idx(raw)
    on = np.zeros(len(raw), bool)
    for a, b in merge_runs(st, en, off_steps + 1):   # gap of <= off_steps unflagged steps keeps the alarm on
        end = min(len(raw) - 1, b + off_steps)       # stays ON through the hold period after the last raw flag
        on[a:end + 1] = True
    return on


def alarm_episodes(state: np.ndarray) -> tuple:
    return runs_idx(state)


def match(events: pd.DataFrame, a0: np.ndarray, a1: np.ndarray, h_steps: int, tol_steps: int = 4) -> tuple:
    """Return (per-event DataFrame with status/lead_h, n_alarm_episodes, n_false_alarm_episodes)."""
    ep_matched = np.zeros(len(a0), bool)
    rows = []
    for e in events.itertuples():
        lo, hi = e.i0 - tol_steps, e.i1 + tol_steps
        ov = (a0 + h_steps <= hi) & (a1 + h_steps >= lo)
        ep_matched |= ov
        if not ov.any():
            rows.append(("miss", np.nan))
            continue
        early = ov & (a0 < e.i0)
        if early.any():
            rows.append(("early", (e.i0 - a0[early].min()) * STEP_H))
        else:
            rows.append(("late", np.nan))
    out = events.copy()
    out["status"] = [r[0] for r in rows]
    out["lead_h"] = [r[1] for r in rows]
    return out, int(len(a0)), int((~ep_matched).sum())
