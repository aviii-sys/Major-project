"""Phase 1C: train the LSTM / GRU / Transformer regression baselines exactly as in docs/PHASE1C_DL_PROTOCOL.md.

Hidden size (32 or 64) is chosen per architecture on VALIDATION event-window RMSE using seed 0 only (written to selection.json before the
other seeds are trained); then seeds 0-4 are trained.  Test predictions are produced from the best-validation checkpoint and are never used
for any selection.  Resumable: finished runs are skipped.   Usage: python scripts/run_phase1c_dl.py [--quick]
"""
import argparse
import json
import platform
import time
from pathlib import Path

import numpy as np
import torch

from flashflood import dl, experiment, models
from flashflood.seq import WINDOW, SeqData

OUT = Path("reports/phase1c")
RUNS = OUT / "runs"
ARCHS = ["lstm", "gru", "transformer"]
HIDDEN = (32, 64)
SEEDS = (0, 1, 2, 3, 4)


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main(quick: bool) -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    ctx = experiment.build_context()
    sd = SeqData(ctx.sv, device)
    any_elig = np.zeros(ctx.n, bool)
    for h in experiment.HZ:
        any_elig |= ctx.elig[h]
    pos = np.arange(ctx.n)
    train_idx = np.where(any_elig & (ctx.lab == "train") & (pos >= WINDOW))[0]
    val_idx = np.where(any_elig & (ctx.lab == "val"))[0]
    test_idx = np.where(any_elig & (ctx.lab == "test"))[0]
    sd.fit_stats(train_idx)
    # per-horizon scale of the stage change from TRAINING rows only
    sigma = np.array([np.nanstd(ctx.tg[h][ctx.elig[h] & (ctx.lab == "train")]) for h in experiment.HZ], dtype=np.float32)
    Y = np.stack([np.nan_to_num(ctx.tg[h], nan=0.0) for h in experiment.HZ], axis=1).astype(np.float32) / sigma
    Mk = np.stack([ctx.elig[h] for h in experiment.HZ], axis=1).astype(np.float32)
    Yt, Mt, sig_t = torch.tensor(Y, device=device), torch.tensor(Mk, device=device), torch.tensor(sigma, device=device)
    val_win = ctx.val_windows()
    log(f"device {device}; rows train/val/test = {len(train_idx)}/{len(val_idx)}/{len(test_idx)}; sigma(ft) = {dict(zip(experiment.HZ, sigma.round(4)))}")
    kw = dict(max_epochs=2, rows_per_epoch=20000) if quick else dict(max_epochs=40, patience=6, rows_per_epoch=120000)
    seeds = (0,) if quick else SEEDS

    def run_one(arch, hidden, seed):
        d = RUNS / f"{arch}_h{hidden}_s{seed}"
        if (d / "predictions.npz").exists():
            return d
        d.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        net, hist = dl.train_run(arch, hidden, seed, sd, Yt, Mt, sig_t, train_idx, val_idx, log=log, **kw)
        pv, pt = dl.predict(net, sd, val_idx, sig_t), dl.predict(net, sd, test_idx, sig_t)
        torch.save(net.state_dict(), d / "checkpoint.pt")
        np.savez_compressed(d / "predictions.npz", val_idx=val_idx, pred_val=pv.astype(np.float32), test_idx=test_idx, pred_test=pt.astype(np.float32))
        best = min(hist, key=lambda r: r["val_loss"])
        cfg = {"arch": arch, "hidden": hidden, "seed": seed, "window_steps": WINDOW, "dropout": 0.1, "optimizer": "adam", "lr": 1e-3, "batch": 512, "grad_clip": 1.0,
               "max_epochs": kw["max_epochs"], "patience": kw.get("patience"), "rows_per_epoch": kw["rows_per_epoch"], "epochs_run": len(hist), "best_epoch": best["epoch"],
               "best_val_scaled_loss": best["val_loss"], "train_seconds": round(time.time() - t0, 1), "device": device, "torch": torch.__version__, "python": platform.python_version(),
               "norm_stats": sd.stats, "sigma_ft": dict(zip(experiment.HZ, map(float, sigma))), "rows": {"train": len(train_idx), "val": len(val_idx), "test": len(test_idx)},
               "checkpoint_sha256": dl.sha256_file(d / "checkpoint.pt"), "predictions_sha256": dl.sha256_file(d / "predictions.npz"), "quick": quick,
               "note": "Test predictions saved from the best-validation checkpoint; never used for selection. MPS kernels are not guaranteed bit-reproducible."}
        (d / "config.json").write_text(json.dumps(cfg, indent=2))
        (d / "history.json").write_text(json.dumps(hist, indent=2))
        log(f"saved {d.name}: best epoch {best['epoch']} val {best['val_loss']:.4f} in {cfg['train_seconds']}s")
        return d

    def val_event_window_rmse(d) -> float:
        z = np.load(d / "predictions.npz")
        vals = []
        for hi, h in enumerate(experiment.HZ):
            p = np.full(ctx.n, np.nan); p[z["val_idx"]] = z["pred_val"][:, hi]
            m = ctx.elig[h] & (ctx.lab == "val") & val_win & ~np.isnan(p)
            vals.append(models.rmse(p[m], ctx.tg[h][m]))
        return float(np.mean(vals))

    sel_path = OUT / "selection.json"
    selection = json.load(open(sel_path)) if sel_path.exists() else {}
    for arch in ARCHS:
        if arch not in selection:
            scores = {}
            for hidden in HIDDEN:
                scores[hidden] = val_event_window_rmse(run_one(arch, hidden, 0))
            chosen = min(scores, key=scores.get)
            selection[arch] = {"validation_event_window_rmse_seed0": {str(k): v for k, v in scores.items()}, "chosen_hidden": chosen,
                               "rule": "lowest mean validation event-window RMSE over the 4 horizons, seed 0 only"}
            sel_path.write_text(json.dumps(selection, indent=2))
            log(f"{arch}: validation event-window RMSE by hidden size {scores} -> chosen {chosen}")
        for seed in seeds:
            run_one(arch, selection[arch]["chosen_hidden"], seed)
    manifest = {}
    for d in sorted(RUNS.glob("*_s*")):
        if (d / "config.json").exists():
            c = json.load(open(d / "config.json"))
            manifest[d.name] = {"checkpoint_sha256": c["checkpoint_sha256"], "predictions_sha256": c["predictions_sha256"], "best_epoch": c["best_epoch"], "seconds": c["train_seconds"]}
    (RUNS / "manifest.json").write_text(json.dumps(manifest, indent=2))
    log("all runs done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true")
    main(ap.parse_args().quick)
