"""Storm-grouped chronological splits and blocked-CV folds (no random window splits)."""
import numpy as np
import pandas as pd

PURGE = pd.Timedelta("3h")   # targets must not cross a boundary (max horizon 3 h)


def adjust_boundary(boundary: pd.Timestamp, clusters: pd.DataFrame) -> pd.Timestamp:
    """If the boundary falls inside a storm cluster, move it to just after the cluster ends."""
    for c in clusters.itertuples():
        if c.t0 < boundary <= c.t1:
            return c.t1 + pd.Timedelta("15min")
    return boundary


def chronological_split(index: pd.DatetimeIndex, clusters: pd.DataFrame, val_start: str = "2018-01-01", test_start: str = "2022-01-01"):
    vs = adjust_boundary(pd.Timestamp(val_start, tz="UTC"), clusters)
    ts = adjust_boundary(pd.Timestamp(test_start, tz="UTC"), clusters)
    lab = np.full(len(index), "purge", dtype=object)
    lab[index < vs - PURGE] = "train"
    lab[(index >= vs) & (index < ts - PURGE)] = "val"
    lab[index >= ts] = "test"
    return pd.Series(lab, index=index), vs, ts


def blocked_folds(index: pd.DatetimeIndex, clusters: pd.DataFrame, n_blocks: int = 6):
    """Contiguous time blocks with boundaries moved outside clusters; rows within PURGE before a boundary are dropped."""
    qs = [index[int(len(index) * k / n_blocks)] for k in range(1, n_blocks)]
    bounds = [adjust_boundary(q, clusters) for q in qs]
    b_naive = pd.DatetimeIndex(bounds).tz_convert(None).values.astype("datetime64[ns]")
    fold = np.searchsorted(b_naive, index.tz_convert(None).values.astype("datetime64[ns]"), side="right")
    fold = pd.Series(fold, index=index).astype(float)
    for b in bounds:
        fold[(index >= b - PURGE) & (index < b)] = np.nan
    return fold, bounds


def group_ids(index: pd.DatetimeIndex, clusters: pd.DataFrame) -> np.ndarray:
    """Bootstrap groups: storm-cluster id inside clusters, ISO-week block outside."""
    g = (index.isocalendar().year.values.astype(int) * 100 + index.isocalendar().week.values.astype(int)) + 1_000_000
    g = g.astype(np.int64)
    for c in clusters.itertuples():
        g[c.i0:c.i1 + 1] = c.cluster_id
    return g
