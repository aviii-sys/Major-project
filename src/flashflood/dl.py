"""Deep regression baselines: LSTM, GRU, Transformer encoder with a shared encoder and four horizon heads (Phase 1C protocol)."""
import copy
import hashlib
import time

import numpy as np
import torch
from torch import nn

from .seq import WINDOW, SeqData

N_H = 4


class Net(nn.Module):
    def __init__(self, arch: str, hidden: int, dropout: float = 0.1):
        super().__init__()
        self.arch = arch
        if arch == "lstm":
            self.rnn = nn.LSTM(3, hidden, batch_first=True)
            z = hidden
        elif arch == "gru":
            self.rnn = nn.GRU(3, hidden, batch_first=True)
            z = hidden
        elif arch == "transformer":
            self.proj = nn.Linear(3, hidden)
            self.pos = nn.Parameter(torch.zeros(1, WINDOW, hidden))
            nn.init.normal_(self.pos, std=0.02)
            layer = nn.TransformerEncoderLayer(hidden, 4, 2 * hidden, dropout, batch_first=True)
            self.enc = nn.TransformerEncoder(layer, 2, enable_nested_tensor=False)
            self.pool = nn.Linear(2 * hidden, hidden)
            z = hidden
        else:
            raise ValueError(arch)
        self.static = nn.Sequential(nn.Linear(2, 16), nn.ReLU())
        self.heads = nn.ModuleList([nn.Sequential(nn.Linear(z + 16, 32), nn.ReLU(), nn.Linear(32, 1)) for _ in range(N_H)])

    def encode(self, x):
        if self.arch in ("lstm", "gru"):
            out, _ = self.rnn(x)
            return out[:, -1]
        h = self.enc(self.proj(x) + self.pos)
        return self.pool(torch.cat([h[:, -1], h.mean(dim=1)], dim=-1))

    def forward(self, x, static):
        z = torch.cat([self.encode(x), self.static(static)], dim=-1)
        return torch.cat([hd(z) for hd in self.heads], dim=-1)          # (B, 4) scaled changes


def masked_loss(pred, y, m):
    """Mean over horizons of the masked mean squared error of scaled targets (equal horizon weights)."""
    se = (pred - y) ** 2 * m
    per_h = se.sum(dim=0) / m.sum(dim=0).clamp(min=1.0)
    return per_h[m.sum(dim=0) > 0].mean()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@torch.no_grad()
def predict(net: Net, sd: SeqData, idx: np.ndarray, sigma: torch.Tensor, bs: int = 4096) -> np.ndarray:
    net.eval()
    out = []
    for i in range(0, len(idx), bs):
        b = torch.tensor(idx[i:i + bs], device=sd.device)
        x, st = sd.batch(b)
        out.append((net(x, st) * sigma).cpu().numpy())
    return np.concatenate(out) if out else np.zeros((0, N_H), np.float32)


def train_run(arch, hidden, seed, sd: SeqData, Y: torch.Tensor, M: torch.Tensor, sigma: torch.Tensor, train_idx, val_idx, *, max_epochs=40, patience=6,
              rows_per_epoch=120000, batch=512, lr=1e-3, log=print):
    """Train one model. Y, M: (n, 4) scaled targets and validity masks on the device. Returns (net_best, history)."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    rng = np.random.default_rng(seed)
    net = Net(arch, hidden).to(sd.device)
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    best, best_state, bad, hist = np.inf, None, 0, []
    val_t = torch.tensor(val_idx, device=sd.device)
    for ep in range(max_epochs):
        t0 = time.time()
        net.train()
        rows = rng.choice(train_idx, size=min(rows_per_epoch, len(train_idx)), replace=False)
        tl, nb = 0.0, 0
        for i in range(0, len(rows), batch):
            b = torch.tensor(rows[i:i + batch], device=sd.device)
            x, st = sd.batch(b)
            loss = masked_loss(net(x, st), Y[b], M[b])
            opt.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
            tl += float(loss.detach()); nb += 1
        net.eval()
        with torch.no_grad():
            vs, vn = 0.0, 0
            for i in range(0, len(val_t), 4096):
                b = val_t[i:i + 4096]
                x, st = sd.batch(b)
                vs += float(masked_loss(net(x, st), Y[b], M[b])) * len(b); vn += len(b)
        vl = vs / vn
        hist.append({"epoch": ep, "train_loss": tl / nb, "val_loss": vl, "seconds": round(time.time() - t0, 1)})
        log(f"  [{arch} h={hidden} s={seed}] epoch {ep:2d} train {tl / nb:.4f} val {vl:.4f} ({hist[-1]['seconds']}s)")
        if vl < best - 1e-6:
            best, best_state, bad = vl, copy.deepcopy(net.state_dict()), 0
        else:
            bad += 1
            if bad >= patience:
                break
    net.load_state_dict(best_state)
    return net, hist
