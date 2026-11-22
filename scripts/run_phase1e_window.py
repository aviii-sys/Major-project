"""Phase 1E (E16): GRU 24 h vs 72 h input window on the six Phase 1D folds with matched seeds 0, 1, 2 (36 trainings), per docs/PHASE1E_PROTOCOL.md.
The input-window length is the only experimental variable. Resumable; writes to reports/phase1e/ only.
Usage: python scripts/run_phase1e_window.py [--quick]
"""
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from flashflood import dl, experiment, folds
from flashflood.seq import SeqData

OUT = Path("reports/phase1e")
RUNS = OUT / "runs"
HZ = experiment.HZ
HIDDEN = 64
SEEDS = (0, 1, 2)
WINDOWS = {24: 96, 72: 288}
MIN_HISTORY = 288                      # training rows need 72 h of history for BOTH configurations, so training rows are identical


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(quick: bool) -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    ctx = experiment.build_context()
    idx, pos = ctx.s.index, np.arange(ctx.n)
    spec = folds.design_folds(idx, ctx.clusters)
    saved = pd.read_csv("reports/phase1d/fold_specification.csv", parse_dates=["train_start", "train_end", "val_start", "val_end", "test_start", "test_end"])
    for c in ("train_end", "val_start", "val_end", "test_start", "test_end"):
        assert (pd.to_datetime(spec[c], utc=True).values == pd.to_datetime(saved[c], utc=True).values).all(), f"fold specification differs from Phase 1D in {c}"
    spec.to_csv(OUT / "fold_specification.csv", index=False)
    log("fold specification identical to Phase 1D")
    any_elig = np.zeros(ctx.n, bool)
    for h in HZ:
        any_elig |= ctx.elig[h]
    kw = dict(max_epochs=2, rows_per_epoch=20000) if quick else dict(max_epochs=40, patience=6, rows_per_epoch=120000)
    env = {"python": platform.python_version(), "torch": torch.__version__, "device": device, "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__}
    for r in spec.itertuples():
        k = r.fold
        tr, va, te = folds.fold_masks(idx, r)
        train_idx = np.where(any_elig & tr & (pos >= MIN_HISTORY))[0]
        val_idx = np.where(any_elig & va)[0]
        test_idx = np.where(any_elig & te)[0]
        log(f"=== fold {k}: train {len(train_idx)} / val {len(val_idx)} / test {len(test_idx)} rows")
        sigma = np.array([np.nanstd(ctx.tg[h][ctx.elig[h] & tr]) for h in HZ], dtype=np.float32)
        Y = np.stack([np.nan_to_num(ctx.tg[h], nan=0.0) for h in HZ], axis=1).astype(np.float32) / sigma
        Mk = np.stack([ctx.elig[h] for h in HZ], axis=1).astype(np.float32)
        Yt, Mt, sig_t = torch.tensor(Y, device=device), torch.tensor(Mk, device=device), torch.tensor(sigma, device=device)
        for wh, wsteps in WINDOWS.items():
            sd = SeqData(ctx.sv, device, window=wsteps)
            sd.fit_stats(train_idx)                                       # per fold, per window length, training windows only
            for seed in SEEDS:
                d = RUNS / f"fold{k}_gru_w{wh}h_h{HIDDEN}_s{seed}"
                if (d / "predictions.npz").exists():
                    continue
                d.mkdir(parents=True, exist_ok=True)
                t0 = time.time()
                net, hist = dl.train_run("gru", HIDDEN, seed, sd, Yt, Mt, sig_t, train_idx, val_idx, log=lambda *_: None, **kw)
                pt = dl.predict(net, sd, test_idx, sig_t)
                torch.save(net.state_dict(), d / "checkpoint.pt")
                np.savez_compressed(d / "predictions.npz", test_idx=test_idx, pred_test=pt.astype(np.float32))
                best = min(hist, key=lambda x: x["val_loss"])
                cfg = {"experiment": "E16 phase1e", "fold": k, "arch": "gru", "window_hours": wh, "window_steps": wsteps, "hidden": HIDDEN, "seed": seed, "optimizer": "adam", "lr": 1e-3,
                       "batch": 512, "grad_clip": 1.0, "max_epochs": kw["max_epochs"], "patience": kw.get("patience"), "rows_per_epoch": kw["rows_per_epoch"], "epochs_run": len(hist),
                       "best_epoch": best["epoch"], "best_val_scaled_loss": best["val_loss"], "train_seconds": round(time.time() - t0, 1), "min_history_steps_for_training_rows": MIN_HISTORY,
                       "norm_stats_fit_on_fold_train_only": sd.stats, "sigma_ft": dict(zip(HZ, map(float, sigma))), "rows": {"train": len(train_idx), "val": len(val_idx), "test": len(test_idx)},
                       "boundaries": {c: str(getattr(r, c)) for c in ("train_start", "train_end", "val_start", "val_end", "test_start", "test_end")}, "environment": env,
                       "checkpoint_sha256": sha256_file(d / "checkpoint.pt"), "predictions_sha256": sha256_file(d / "predictions.npz"), "quick": quick}
                (d / "config.json").write_text(json.dumps(cfg, indent=2))
                (d / "history.json").write_text(json.dumps(hist, indent=2))
                log(f"saved {d.name}: best epoch {best['epoch']} val {best['val_loss']:.4f} in {cfg['train_seconds']}s")
    manifest = {}
    for d in sorted(RUNS.glob("fold*")):
        if (d / "config.json").exists():
            c = json.load(open(d / "config.json"))
            manifest[d.name] = {k_: c[k_] for k_ in ("checkpoint_sha256", "predictions_sha256", "best_epoch", "train_seconds")}
    (RUNS / "manifest.json").write_text(json.dumps(manifest, indent=2))
    log("all runs done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true")
    main(ap.parse_args().quick)
