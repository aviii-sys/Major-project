"""Loading SAVED out-of-fold predictions (Phase 1D/1E and the hybrid runs) onto the project grid, as predicted stage CHANGES (ft) aligned at issue time.
Everything is read-only: no model is retrained and no saved artifact is modified."""
from pathlib import Path

import numpy as np
import pandas as pd

from . import data, folds

HZ = list(data.HORIZONS)
D1 = Path("reports/phase1d/runs")
E1 = Path("reports/phase1e/runs")


def fold_spec(root: Path = Path(".")) -> pd.DataFrame:
    return pd.read_csv(root / "reports/phase1d/fold_specification.csv", parse_dates=["train_start", "train_end", "val_start", "val_end", "test_start", "test_end"])


def fold_of_array(idx: pd.DatetimeIndex, spec: pd.DataFrame) -> np.ndarray:
    """Fold number (1-6) of every grid time inside a test block, 0 elsewhere (from the fold specification, not from which rows a file contains)."""
    out = np.zeros(len(idx), int)
    for r in spec.itertuples():
        out[(idx >= r.test_start) & (idx <= r.test_end)] = int(r.fold)
    return out


def deep_changes(n: int, run_dirs: dict) -> dict:
    """run_dirs: fold -> directory containing predictions.npz (test_idx, pred_test with columns in HZ order). Returns horizon -> array of predicted stage change."""
    out = {h: np.full(n, np.nan) for h in HZ}
    for k, d in run_dirs.items():
        z = np.load(Path(d) / "predictions.npz")
        for hi, h in enumerate(HZ):
            out[h][z["test_idx"]] = z["pred_test"][:, hi]
    return out


def classical_changes(n: int, models=("persistence", "trend_v2", "ridge_H", "xgb_H"), folds_=range(1, 7), root: Path = D1) -> dict:
    """(model, horizon) -> array of predicted stage change from the frozen Phase 1D classical predictions."""
    out = {(m, h): np.full(n, np.nan) for m in models for h in HZ}
    for k in folds_:
        z = np.load(root / f"fold{k}_classical" / "predictions.npz")
        for m in models:
            for hi, h in enumerate(HZ):
                out[(m, h)][z["test_idx"]] = z[f"pred_{m}"][:, hi]
    return out


def phase1d_deep(n: int, arch: str, seed: int = 0) -> dict:
    return deep_changes(n, {k: D1 / f"fold{k}_{arch}_h64_s{seed}" for k in range(1, 7)})


def phase1e_gru24(n: int, seed: int) -> dict:
    return deep_changes(n, {k: E1 / f"fold{k}_gru_w24h_h64_s{seed}" for k in range(1, 7)})


def mask_to_eligible(arrays: dict, elig: dict) -> None:
    """Predictions exist only on eligible held-out rows (as in Phases 1D and 1E); everything else becomes NaN in place. `arrays`: horizon -> array."""
    for h in HZ:
        arrays[h][~elig[h]] = np.nan
