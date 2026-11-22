"""Sequence inputs for the deep baselines (Phase 1C protocol section 2). Everything at row t uses data with timestamp <= t."""
import numpy as np
import torch

WINDOW = 96                    # 24 h of 15-min steps
C1_SCALE, C2_SCALE = 0.25, 0.05


class SeqData:
    """Holds the stage series on the device and builds windows for end-indices on the fly (no future data is ever gathered)."""

    def __init__(self, sv: np.ndarray, device: str, window: int = WINDOW):
        self.device = device
        self.window = window                                          # input history in 15-min steps (96 = 24 h, 288 = 72 h)
        self.S = torch.tensor(np.nan_to_num(sv, nan=0.0), dtype=torch.float32, device=device)
        self.M = torch.tensor(~np.isnan(sv), dtype=torch.float32, device=device)
        self.offs = torch.arange(-window, 1, device=device)           # window+1 positions: t-window ... t
        self.stats = None

    def raw_channels(self, idx: torch.Tensor):
        pos = idx[:, None] + self.offs[None, :]
        S, M = self.S[pos], self.M[pos]
        cur = S[:, -1]
        rel_mask = M[:, 1:]
        rel = torch.asinh((S[:, 1:] - cur[:, None]) / C1_SCALE) * rel_mask
        d_mask = M[:, 1:] * M[:, :-1]
        dlt = torch.asinh((S[:, 1:] - S[:, :-1]) / C2_SCALE) * d_mask
        return rel, dlt, rel_mask, d_mask, cur, 1.0 - rel_mask.mean(dim=1)

    def fit_stats(self, train_idx: np.ndarray, n_sample: int = 20000, seed: int = 0):
        """Normalisation statistics from TRAINING windows only."""
        rng = np.random.default_rng(seed)
        sel = torch.tensor(rng.choice(train_idx, size=min(n_sample, len(train_idx)), replace=False), device=self.device)
        rel, dlt, rm, dm, cur, _ = self.raw_channels(sel)
        def ms(x, m):
            v = x[m > 0]
            return float(v.mean()), float(v.std() + 1e-6)
        self.stats = {"c1": ms(rel, rm), "c2": ms(dlt, dm), "cur": (float(cur.mean()), float(cur.std() + 1e-6))}
        return self.stats

    def batch(self, idx: torch.Tensor):
        rel, dlt, rm, dm, cur, miss_frac = self.raw_channels(idx)
        st = self.stats
        c1 = ((rel - st["c1"][0]) / st["c1"][1]) * rm
        c2 = ((dlt - st["c2"][0]) / st["c2"][1]) * dm
        x = torch.stack([c1, c2, rm], dim=-1)
        static = torch.stack([(cur - st["cur"][0]) / st["cur"][1], miss_frac], dim=-1)
        return x, static
