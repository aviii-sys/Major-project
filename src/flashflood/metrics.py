"""Regression metrics, cluster bootstrap and exact binomial intervals."""
import numpy as np
from scipy.stats import beta


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple:
    if n == 0:
        return (np.nan, np.nan)
    lo = 0.0 if k == 0 else beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - alpha / 2, k + 1, n - k)
    return float(lo), float(hi)


def reg_stats(err_m: np.ndarray, err_p: np.ndarray) -> dict:
    mse_m, mse_p = np.mean(err_m ** 2), np.mean(err_p ** 2)
    return {"n": int(len(err_m)), "rmse": float(np.sqrt(mse_m)), "mae": float(np.mean(np.abs(err_m))),
            "rmse_persistence": float(np.sqrt(mse_p)), "skill_vs_persistence": float(1 - mse_m / mse_p) if mse_p > 0 else np.nan}


def cluster_bootstrap(err_m: np.ndarray, err_p: np.ndarray, groups: np.ndarray, b: int = 2000, seed: int = 0) -> dict:
    """95% percentile intervals for RMSE, MAE and skill by resampling whole groups (storm clusters / weekly quiet blocks)."""
    ug, inv = np.unique(groups, return_inverse=True)
    stats = np.zeros((len(ug), 4))
    np.add.at(stats[:, 0], inv, 1.0)
    np.add.at(stats[:, 1], inv, err_m ** 2)
    np.add.at(stats[:, 2], inv, np.abs(err_m))
    np.add.at(stats[:, 3], inv, err_p ** 2)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(ug), size=(b, len(ug)))
    s = stats[idx].sum(axis=1)
    rmse = np.sqrt(s[:, 1] / s[:, 0])
    mae = s[:, 2] / s[:, 0]
    skill = 1 - s[:, 1] / s[:, 3]
    q = lambda x: (float(np.nanpercentile(x, 2.5)), float(np.nanpercentile(x, 97.5)))  # noqa: E731
    return {"rmse_ci": q(rmse), "mae_ci": q(mae), "skill_ci": q(skill), "n_groups": int(len(ug))}


class GroupBoot:
    """Shared storm-cluster bootstrap resamples so that several models are compared on IDENTICAL resamples (paired intervals)."""

    def __init__(self, groups: np.ndarray, b: int = 2000, seed: int = 0):
        self.ug, self.inv = np.unique(groups, return_inverse=True)
        rng = np.random.default_rng(seed)
        self.idx = rng.integers(0, len(self.ug), size=(b, len(self.ug)))
        cnt = np.zeros(len(self.ug))
        np.add.at(cnt, self.inv, 1.0)
        self.n_rep = cnt[self.idx].sum(axis=1)

    def mse(self, err: np.ndarray) -> np.ndarray:
        s = np.zeros(len(self.ug))
        np.add.at(s, self.inv, np.asarray(err, dtype=float) ** 2)
        return s[self.idx].sum(axis=1) / self.n_rep

    @staticmethod
    def ci(x: np.ndarray) -> tuple:
        return float(np.nanpercentile(x, 2.5)), float(np.nanpercentile(x, 97.5))
