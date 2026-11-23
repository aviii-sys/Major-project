"""Hybrid Transformer + LSTM regression model (E23, docs/HYBRID_H1_PROTOCOL.md). Stage-only inputs (the Phase 1C-1E channels).
A Transformer encoder reads the full 24 h window (96 steps), an LSTM reads the LAST 6 h (24 steps) of the same channels; their summaries are concatenated with the static features and
fed to four horizon heads (15 min, 30 min, 1 h, 3 h) exactly as in the Phase 1C baselines. Ablations switch one branch off. Nothing here changes dl.py or seq.py."""
import copy
import time
from dataclasses import asdict, dataclass

import numpy as np
import torch
from torch import nn

from .dl import N_H, masked_loss
from .seq import WINDOW, SeqData


@dataclass(frozen=True)
class HybridCfg:
    name: str
    d_model: int = 64
    n_heads: int = 4
    n_layers: int = 2
    ff_mult: int = 2
    dropout: float = 0.1
    norm_first: bool = False          # False = post-LayerNorm (as the Phase 1C Transformer); True = pre-LayerNorm with a final norm
    lstm_hidden: int = 64
    short_steps: int = 24             # 6 h
    lr: float = 1e-3
    warmup_steps: int = 0             # linear learning-rate warm-up over this many optimizer steps (0 = none)

    def as_dict(self) -> dict:
        return asdict(self)


# The four stability settings of docs/HYBRID_H1_PROTOCOL.md section 3 (chosen on validation data only; S0 mirrors the Phase 1C Transformer configuration)
SETTINGS = {
    "S0": HybridCfg("S0"),
    "S1": HybridCfg("S1", norm_first=True, warmup_steps=300),
    "S2": HybridCfg("S2", norm_first=True, warmup_steps=300, lr=3e-4),
    "S3": HybridCfg("S3", norm_first=True, warmup_steps=300, d_model=32),
}


class HybridNet(nn.Module):
    def __init__(self, cfg: HybridCfg, use_t: bool = True, use_l: bool = True):
        super().__init__()
        if not (use_t or use_l):
            raise ValueError("at least one branch is required")
        self.cfg, self.use_t, self.use_l = cfg, use_t, use_l
        z = 0
        if use_t:
            d = cfg.d_model
            self.proj = nn.Linear(3, d)
            self.pos = nn.Parameter(torch.zeros(1, WINDOW, d))
            nn.init.normal_(self.pos, std=0.02)
            layer = nn.TransformerEncoderLayer(d, cfg.n_heads, cfg.ff_mult * d, cfg.dropout, batch_first=True, norm_first=cfg.norm_first)
            self.enc = nn.TransformerEncoder(layer, cfg.n_layers, norm=nn.LayerNorm(d) if cfg.norm_first else None, enable_nested_tensor=False)
            self.pool = nn.Linear(2 * d, d)
            z += d
        if use_l:
            self.rnn = nn.LSTM(3, cfg.lstm_hidden, batch_first=True)
            z += cfg.lstm_hidden
        self.static = nn.Sequential(nn.Linear(2, 16), nn.ReLU())
        self.heads = nn.ModuleList([nn.Sequential(nn.Linear(z + 16, 32), nn.ReLU(), nn.Linear(32, 1)) for _ in range(N_H)])

    def encode_transformer(self, x):
        h = self.enc(self.proj(x) + self.pos)
        return self.pool(torch.cat([h[:, -1], h.mean(dim=1)], dim=-1))

    def encode_lstm(self, x):
        out, _ = self.rnn(x[:, -self.cfg.short_steps:, :])          # the most recent 6 h of the same window
        return out[:, -1]

    def forward(self, x, static):
        parts = []
        if self.use_t:
            parts.append(self.encode_transformer(x))
        if self.use_l:
            parts.append(self.encode_lstm(x))
        parts.append(self.static(static))
        z = torch.cat(parts, dim=-1)
        return torch.cat([hd(z) for hd in self.heads], dim=-1)      # (B, 4) scaled changes

    def n_params(self) -> int:
        return sum(p.numel() for p in self.parameters())


def lr_factor(step: int, warmup_steps: int) -> float:
    """Linear warm-up from 1/warmup to 1 (no decay afterwards); 1.0 when warm-up is disabled."""
    return 1.0 if warmup_steps <= 0 else min(1.0, (step + 1) / warmup_steps)


def train_run_hybrid(cfg: HybridCfg, seed: int, sd: SeqData, Y: torch.Tensor, M: torch.Tensor, train_idx, val_idx, *, use_t=True, use_l=True, max_epochs=40, patience=6,
                     rows_per_epoch=120000, batch=512, log=print):
    """Same protocol as dl.train_run (Adam, batch 512, 120,000 random rows per epoch, gradient clip 1.0, patience 6, best-validation checkpoint), plus the optional warm-up of `cfg`."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    rng = np.random.default_rng(seed)
    net = HybridNet(cfg, use_t, use_l).to(sd.device)
    opt = torch.optim.Adam(net.parameters(), lr=cfg.lr)
    best, best_state, bad, hist, step = np.inf, None, 0, [], 0
    val_t = torch.tensor(val_idx, device=sd.device)
    for ep in range(max_epochs):
        t0 = time.time()
        net.train()
        rows = rng.choice(train_idx, size=min(rows_per_epoch, len(train_idx)), replace=False)
        tl, nb = 0.0, 0
        for i in range(0, len(rows), batch):
            for g in opt.param_groups:
                g["lr"] = cfg.lr * lr_factor(step, cfg.warmup_steps)
            b = torch.tensor(rows[i:i + batch], device=sd.device)
            x, st = sd.batch(b)
            loss = masked_loss(net(x, st), Y[b], M[b])
            opt.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
            tl += float(loss.detach()); nb += 1; step += 1
        net.eval()
        with torch.no_grad():
            vs, vn = 0.0, 0
            for i in range(0, len(val_t), 4096):
                b = val_t[i:i + 4096]
                x, st = sd.batch(b)
                vs += float(masked_loss(net(x, st), Y[b], M[b])) * len(b); vn += len(b)
        vl = vs / vn
        hist.append({"epoch": ep, "train_loss": tl / nb, "val_loss": vl, "seconds": round(time.time() - t0, 1)})
        log(f"  [{cfg.name} t={int(use_t)} l={int(use_l)} s={seed}] epoch {ep:2d} train {tl / nb:.4f} val {vl:.4f} ({hist[-1]['seconds']}s)")
        if vl < best - 1e-6:
            best, best_state, bad = vl, copy.deepcopy(net.state_dict()), 0
        else:
            bad += 1
            if bad >= patience:
                break
    net.load_state_dict(best_state)
    return net, hist
