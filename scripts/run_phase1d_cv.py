"""Phase 1D (E14): six-fold blocked chronological cross-validation for GRU and LSTM (+ classical comparators), exactly as in docs/PHASE1D_PROTOCOL.md.
Expanding-window forward chaining; every fold fits only on data preceding its held-out block; preprocessing fitted per fold on training rows only.
Resumable; writes to reports/phase1d/ only.

IMPORTANT: PyTorch and XGBoost crash (segmentation fault, OpenMP clash) when both are used in ONE process on this machine, so the two stages run as
separate processes:   python scripts/run_phase1d_cv.py --stage dl    and    python scripts/run_phase1d_cv.py --stage classical     [--quick]
"""
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd

from flashflood import data, experiment, folds

OUT = Path("reports/phase1d")
RUNS = OUT / "runs"
HZ = experiment.HZ
ARCHS = ["gru", "lstm"]
HIDDEN, SEED = 64, 0
WINDOW = 96
TREND_W = {"15m": 1, "30m": 2, "1h": 4}
TREND_PHI = (0.25, 0.5, 0.75, 1.0)
CLASSICAL = ["persistence", "trend_v2", "ridge_H", "xgb_H"]


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def setup():
    RUNS.mkdir(parents=True, exist_ok=True)
    ctx = experiment.build_context()
    spec = folds.design_folds(ctx.s.index, ctx.clusters)
    spec.to_csv(OUT / "fold_specification.csv", index=False)
    (OUT / "fold_specification.json").write_text(spec.astype(str).to_json(orient="records", indent=2))
    mapping = folds.event_to_fold(ctx.ev_all, ctx.kind_of, spec, ctx.s.index, ctx.clusters, ctx.groups)
    mapping.to_csv(OUT / "event_to_fold_mapping.csv", index=False)
    any_elig = np.zeros(ctx.n, bool)
    for h in HZ:
        any_elig |= ctx.elig[h]
    return ctx, spec, any_elig


def stage_dl(quick: bool) -> None:
    import torch
    from flashflood import dl
    from flashflood.seq import SeqData
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    ctx, spec, any_elig = setup()
    idx, pos = ctx.s.index, np.arange(ctx.n)
    kw = dict(max_epochs=2, rows_per_epoch=20000) if quick else dict(max_epochs=40, patience=6, rows_per_epoch=120000)
    env = {"python": platform.python_version(), "torch": torch.__version__, "device": device, "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__}
    for r in spec.itertuples():
        k = r.fold
        tr, va, te = folds.fold_masks(idx, r)
        train_idx = np.where(any_elig & tr & (pos >= WINDOW))[0]
        val_idx = np.where(any_elig & va)[0]
        test_idx = np.where(any_elig & te)[0]
        log(f"=== fold {k}: train {len(train_idx)} / val {len(val_idx)} / test {len(test_idx)} rows; test block {r.test_start:%Y-%m-%d} -> {r.test_end:%Y-%m-%d}")
        sd = SeqData(ctx.sv, device)
        sd.fit_stats(train_idx)                                           # normalisation from THIS fold's training windows only
        sigma = np.array([np.nanstd(ctx.tg[h][ctx.elig[h] & tr]) for h in HZ], dtype=np.float32)
        Y = np.stack([np.nan_to_num(ctx.tg[h], nan=0.0) for h in HZ], axis=1).astype(np.float32) / sigma
        Mk = np.stack([ctx.elig[h] for h in HZ], axis=1).astype(np.float32)
        Yt, Mt, sig_t = torch.tensor(Y, device=device), torch.tensor(Mk, device=device), torch.tensor(sigma, device=device)
        for arch in ARCHS:
            d = RUNS / f"fold{k}_{arch}_h{HIDDEN}_s{SEED}"
            if (d / "predictions.npz").exists():
                continue
            d.mkdir(parents=True, exist_ok=True)
            t0 = time.time()
            net, hist = dl.train_run(arch, HIDDEN, SEED, sd, Yt, Mt, sig_t, train_idx, val_idx, log=log, **kw)
            pt = dl.predict(net, sd, test_idx, sig_t)
            torch.save(net.state_dict(), d / "checkpoint.pt")
            np.savez_compressed(d / "predictions.npz", test_idx=test_idx, pred_test=pt.astype(np.float32))
            best = min(hist, key=lambda x: x["val_loss"])
            cfg = {"experiment": "E14 phase1d", "fold": k, "arch": arch, "hidden": HIDDEN, "seed": SEED, "window_steps": WINDOW, "optimizer": "adam", "lr": 1e-3, "batch": 512,
                   "grad_clip": 1.0, "max_epochs": kw["max_epochs"], "patience": kw.get("patience"), "rows_per_epoch": kw["rows_per_epoch"], "epochs_run": len(hist),
                   "best_epoch": best["epoch"], "best_val_scaled_loss": best["val_loss"], "train_seconds": round(time.time() - t0, 1), "norm_stats_fit_on_fold_train_only": sd.stats,
                   "sigma_ft": dict(zip(HZ, map(float, sigma))), "rows": {"train": len(train_idx), "val": len(val_idx), "test": len(test_idx)},
                   "boundaries": {c: str(getattr(r, c)) for c in ("train_start", "train_end", "val_start", "val_end", "test_start", "test_end")},
                   "environment": env, "checkpoint_sha256": sha256_file(d / "checkpoint.pt"), "predictions_sha256": sha256_file(d / "predictions.npz"), "quick": quick}
            (d / "config.json").write_text(json.dumps(cfg, indent=2))
            (d / "history.json").write_text(json.dumps(hist, indent=2))
            log(f"saved {d.name}: best epoch {best['epoch']} val {best['val_loss']:.4f} in {cfg['train_seconds']}s")
    log("deep stage done")


def stage_classical(quick: bool) -> None:
    from flashflood import models
    ctx, spec, any_elig = setup()
    idx, n = ctx.s.index, ctx.n
    Hfeat = ctx.H
    Hcols = list(Hfeat.columns)
    Xraw = Hfeat[Hcols].values.astype(np.float32)
    Xlin = data.prep_linear(Hfeat, Hcols).astype(np.float32)
    env = {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__}
    for r in spec.itertuples():
        k = r.fold
        tr, va, te = folds.fold_masks(idx, r)
        test_idx = np.where(any_elig & te)[0]
        cdir = RUNS / f"fold{k}_classical"
        if (cdir / "predictions.npz").exists():
            continue
        cdir.mkdir(parents=True, exist_ok=True)
        val_win = np.zeros(n, bool)
        n_val_ev = 0
        for dname in ("experimental_stage_10ft", "experimental_rise_4ft_3h"):
            e = ctx.events_in(dname, va)
            n_val_ev += len(e)
            if len(e):
                val_win |= ctx.win_mask(e, ctx.kind_of[dname])
        use_event_window = n_val_ev >= 2
        preds = {m: np.full((len(test_idx), 4), np.nan, np.float32) for m in CLASSICAL}
        chosen = {"validation_events_used_for_trend": n_val_ev, "trend_selection_by": "event-window RMSE" if use_event_window else "all-row RMSE"}
        for hi, (h, kstep) in enumerate(data.HORIZONS.items()):
            y = ctx.tg[h]
            trh, vah, teh = ctx.elig[h] & tr, ctx.elig[h] & va, ctx.elig[h] & te
            tpos = np.searchsorted(test_idx, np.where(teh)[0])
            preds["persistence"][tpos, hi] = 0.0
            best_t = None
            for wn, ws in TREND_W.items():
                dcol = Hfeat[f"d_{wn}"].values
                for phi in TREND_PHI:
                    ch = models.trend_change_v2(dcol, ws, kstep, phi)
                    m = vah & ~np.isnan(ch)
                    mm = (m & val_win) if use_event_window else m
                    if mm.sum() == 0:
                        continue
                    e_ = models.rmse(ch[mm], y[mm])
                    if best_t is None or e_ < best_t[0]:
                        best_t = (e_, wn, ws, phi)
            _, wn, ws, phi = best_t
            ch = models.trend_change_v2(Hfeat[f"d_{wn}"].values, ws, kstep, phi)
            preds["trend_v2"][tpos, hi] = ch[teh]
            chosen[f"trend_{h}"] = {"window": wn, "phi": phi}
            best_r = None
            for a in models.RIDGE_ALPHAS:
                m_ = models.fit_ridge(Xlin[trh], y[trh], a)
                e_ = models.rmse(m_.predict(Xlin[vah]), y[vah])
                if best_r is None or e_ < best_r[0]:
                    best_r = (e_, a, m_)
            preds["ridge_H"][tpos, hi] = best_r[2].predict(Xlin[teh])
            chosen[f"ridge_{h}"] = {"alpha": best_r[1]}
            best_x = None
            for dep in models.XGB_DEPTHS:
                m_, bi = models.fit_xgb(Xraw[trh], y[trh], dep, Xraw[vah], y[vah], n_estimators=80 if quick else 600)
                e_ = models.rmse(m_.predict(Xraw[vah]), y[vah])
                if best_x is None or e_ < best_x[0]:
                    best_x = (e_, dep, bi, m_)
            preds["xgb_H"][tpos, hi] = best_x[3].predict(Xraw[teh])
            chosen[f"xgb_{h}"] = {"depth": best_x[1], "trees": best_x[2]}
        np.savez_compressed(cdir / "predictions.npz", test_idx=test_idx, **{f"pred_{m}": v for m, v in preds.items()})
        chosen.update({"fold": k, "seed": SEED, "environment": env, "predictions_sha256": sha256_file(cdir / "predictions.npz"), "quick": quick})
        (cdir / "config.json").write_text(json.dumps(chosen, indent=2))
        log(f"classical comparators fold {k} done ({chosen['trend_selection_by']}, {n_val_ev} validation events)")
    log("classical stage done")


def write_manifest() -> None:
    manifest = {}
    for d in sorted(RUNS.glob("fold*")):
        if (d / "config.json").exists():
            c = json.load(open(d / "config.json"))
            manifest[d.name] = {k_: c[k_] for k_ in ("checkpoint_sha256", "predictions_sha256", "best_epoch", "train_seconds") if k_ in c}
    (RUNS / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["dl", "classical", "manifest"], required=True)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    {"dl": stage_dl, "classical": stage_classical}.get(a.stage, lambda q: write_manifest())(a.quick)
    if a.stage != "manifest":
        write_manifest()
