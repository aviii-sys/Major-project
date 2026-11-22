"""Expanding-window blocked chronological cross-validation (Phase 1D).

Fold k: train on data BEFORE a validation chunk, validate (early stopping / hyperparameter selection) on the chunk just before the
held-out block, test on the held-out block k.  Nothing after the end of the validation chunk is ever used for fitting, and no storm
cluster is split between train / validation / test.  An embargo of (input window 24 h + max horizon 3 h + 1 step) separates the chunks,
so no training or validation TARGET shares a timestamp with any test INPUT window.
"""
import numpy as np
import pandas as pd

WINDOW_H, HORIZON_H = 24, 3
EMBARGO = pd.Timedelta(hours=WINDOW_H + HORIZON_H) + pd.Timedelta("15min")      # 27 h 15 min
CLEAR = pd.Timedelta("96h")                                                   # a boundary must have no storm cluster in the 96 h before it
STEP = pd.Timedelta("15min")
BLOCK_STARTS = ["2012-01-01", "2015-01-01", "2016-01-01", "2018-01-01", "2020-01-01", "2025-01-01"]   # nominal; snapped forward to quiet periods


def snap_forward(t: pd.Timestamp, clusters: pd.DataFrame) -> pd.Timestamp:
    """Move t forward until no storm cluster intersects [t - CLEAR, t]."""
    moved = True
    while moved:
        moved = False
        for c in clusters.itertuples():
            if c.t0 <= t and c.t1 >= t - CLEAR:
                t = c.t1 + CLEAR
                moved = True
    return t


def design_folds(index: pd.DatetimeIndex, clusters: pd.DataFrame, block_starts=BLOCK_STARTS, val_frac: float = 0.25, val_min_months: float = 12,
                 val_max_months: float = 24) -> pd.DataFrame:
    """Return one row per fold with the exact boundaries (all UTC)."""
    rec0, rec1 = index[0], index[-1]
    starts = [snap_forward(pd.Timestamp(d, tz="UTC"), clusters) for d in block_starts]
    ends = starts[1:] + [rec1 + STEP]
    rows = []
    for k, (S, E) in enumerate(zip(starts, ends), start=1):
        prior = S - rec0
        val_len = min(max(prior * val_frac, pd.Timedelta(days=30.44 * val_min_months)), pd.Timedelta(days=30.44 * val_max_months))
        val_end = S - EMBARGO
        val_start = snap_forward(val_end - val_len, clusters)
        train_end = val_start - EMBARGO
        rows.append({"fold": k, "train_start": rec0, "train_end": train_end, "val_start": val_start, "val_end": val_end, "test_start": S, "test_end": E - STEP,
                     "nominal_test_start": pd.Timestamp(block_starts[k - 1], tz="UTC")})
    return pd.DataFrame(rows)


def fold_masks(index: pd.DatetimeIndex, spec_row) -> tuple:
    """Boolean arrays (train, val, test) over the full index for one fold; embargo rows belong to none of them."""
    train = (index >= spec_row.train_start) & (index <= spec_row.train_end)
    val = (index >= spec_row.val_start) & (index <= spec_row.val_end)
    test = (index >= spec_row.test_start) & (index <= spec_row.test_end)
    return np.asarray(train), np.asarray(val), np.asarray(test)


def event_to_fold(ev_all: dict, kind_of: dict, spec: pd.DataFrame, index: pd.DatetimeIndex, clusters: pd.DataFrame, groups: np.ndarray) -> pd.DataFrame:
    """Map every event of every definition to a held-out fold, or to a documented exclusion."""
    rows = []
    first_start = spec.test_start.min()
    for defn, ev in ev_all.items():
        for e in ev.itertuples():
            t0 = index[int(e.i0)]
            fold, reason = None, ""
            if t0 < first_start:
                reason = "excluded: lies in the initial training segment (no earlier data to train a model that is evaluated on it)"
            else:
                hit = spec[(spec.test_start <= t0) & (spec.test_end >= t0)]
                fold = int(hit.fold.iloc[0]) if len(hit) else None
                if fold is None:
                    reason = "excluded: falls in no held-out block"
                else:
                    t1 = index[int(e.i1)]
                    if t1 > hit.test_end.iloc[0]:
                        reason = "excluded: event end crosses the block end"
            rows.append({"definition": defn, "event_start": t0, "event_end": index[int(e.i1)], "peak_ft": getattr(e, "peak_ft", np.nan), "storm_cluster": int(groups[int(e.i0)]),
                         "fold": fold if not reason else None, "status": "evaluated" if not reason else "excluded", "reason": reason})
    return pd.DataFrame(rows)
