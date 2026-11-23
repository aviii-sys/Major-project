"""H1 (E23): stage-only hybrid Transformer+LSTM on the six Phase 1D folds, per docs/HYBRID_H1_PROTOCOL.md. Resumable; writes only under --out (default reports/hybrid_h1).
Stages: stability (4 settings x 6 folds, seed 0; selection on VALIDATION loss only) -> select -> main (selected setting, 6 folds x seeds 0-2) -> ablate (single-branch ablations, seed 0).
Usage (project root): PYTHONPATH=src python scripts/run_hybrid_h1.py --stage stability|select|main|ablate [--quick --folds 1,2 --out reports/hybrid_h1_smoke]
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

from flashflood import experiment, folds, hybrid
from flashflood.seq import SeqData

HZ = experiment.HZ
SEEDS = (0, 1, 2)
MIN_HISTORY = 288                 # identical training rows to the Phase 1E GRU 24 h runs (rows with at least 72 h of history)
SWITCH_MARGIN = 0.99              # a setting replaces S0 only if its geometric-mean validation-loss ratio is <= 0.99 (protocol section 3)


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Setup:
    def __init__(self, out: Path, quick: bool, fold_list):
        self.out, self.quick = out, quick
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.ctx = experiment.build_context()
        self.idx, self.pos = self.ctx.s.index, np.arange(self.ctx.n)
        self.spec = folds.design_folds(self.idx, self.ctx.clusters)
        saved = pd.read_csv("reports/phase1d/fold_specification.csv", parse_dates=["train_start", "train_end", "val_start", "val_end", "test_start", "test_end"])
        for c in ("train_end", "val_start", "val_end", "test_start", "test_end"):
            assert (pd.to_datetime(self.spec[c], utc=True).values == pd.to_datetime(saved[c], utc=True).values).all(), f"fold specification differs from Phase 1D in {c}"
        out.mkdir(parents=True, exist_ok=True)
        self.spec.to_csv(out / "fold_specification.csv", index=False)
        self.fold_list = fold_list or list(range(1, 7))
        self.any_elig = np.zeros(self.ctx.n, bool)
        for h in HZ:
            self.any_elig |= self.ctx.elig[h]
        self.kw = dict(max_epochs=2, rows_per_epoch=20000) if quick else dict(max_epochs=40, patience=6, rows_per_epoch=120000)
        self.env = {"python": platform.python_version(), "torch": torch.__version__, "device": self.device, "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__}
        self._cache = {}

    def fold(self, r):
        k = r.fold
        if k in self._cache:
            return self._cache[k]
        tr, va, te = folds.fold_masks(self.idx, r)
        train_idx = np.where(self.any_elig & tr & (self.pos >= MIN_HISTORY))[0]
        val_idx = np.where(self.any_elig & va)[0]
        test_idx = np.where(self.any_elig & te)[0]
        sigma = np.array([np.nanstd(self.ctx.tg[h][self.ctx.elig[h] & tr]) for h in HZ], dtype=np.float32)
        Y = np.stack([np.nan_to_num(self.ctx.tg[h], nan=0.0) for h in HZ], axis=1).astype(np.float32) / sigma
        Mk = np.stack([self.ctx.elig[h] for h in HZ], axis=1).astype(np.float32)
        sd = SeqData(self.ctx.sv, self.device, window=96)
        sd.fit_stats(train_idx)                                       # per fold, training windows only (same as Phase 1E)
        d = {"train_idx": train_idx, "val_idx": val_idx, "test_idx": test_idx, "sigma": sigma, "sd": sd, "Y": torch.tensor(Y, device=self.device), "M": torch.tensor(Mk, device=self.device),
             "sig_t": torch.tensor(sigma, device=self.device)}
        self._cache = {k: d}                                          # keep one fold in memory
        return d


def run_one(S: Setup, r, directory: Path, cfg: hybrid.HybridCfg, seed: int, kind: str, experiment_id: str) -> None:
    if (directory / "predictions.npz").exists():
        return
    from flashflood import dl
    directory.mkdir(parents=True, exist_ok=True)
    fd = S.fold(r)
    use_t, use_l = kind in ("hybrid", "tonly"), kind in ("hybrid", "lonly")
    t0 = time.time()
    net, hist = hybrid.train_run_hybrid(cfg, seed, fd["sd"], fd["Y"], fd["M"], fd["train_idx"], fd["val_idx"], use_t=use_t, use_l=use_l, log=lambda *_: None, **S.kw)
    pt = dl.predict(net, fd["sd"], fd["test_idx"], fd["sig_t"])
    torch.save(net.state_dict(), directory / "checkpoint.pt")
    np.savez_compressed(directory / "predictions.npz", test_idx=fd["test_idx"], pred_test=pt.astype(np.float32))
    best = min(hist, key=lambda x: x["val_loss"])
    c = {"experiment": experiment_id, "fold": r.fold, "kind": kind, "setting": cfg.as_dict(), "seed": seed, "n_params": net.n_params(), "optimizer": "adam", "batch": 512, "grad_clip": 1.0,
         "max_epochs": S.kw["max_epochs"], "patience": S.kw.get("patience"), "rows_per_epoch": S.kw["rows_per_epoch"], "epochs_run": len(hist), "best_epoch": best["epoch"], "best_val_scaled_loss": best["val_loss"],
         "final_val_loss": hist[-1]["val_loss"], "train_seconds": round(time.time() - t0, 1), "min_history_steps_for_training_rows": MIN_HISTORY, "norm_stats_fit_on_fold_train_only": fd["sd"].stats,
         "sigma_ft": dict(zip(HZ, map(float, fd["sigma"]))), "rows": {"train": len(fd["train_idx"]), "val": len(fd["val_idx"]), "test": len(fd["test_idx"])},
         "boundaries": {k_: str(getattr(r, k_)) for k_ in ("train_start", "train_end", "val_start", "val_end", "test_start", "test_end")}, "environment": S.env,
         "checkpoint_sha256": sha256_file(directory / "checkpoint.pt"), "predictions_sha256": sha256_file(directory / "predictions.npz"), "quick": S.quick}
    (directory / "config.json").write_text(json.dumps(c, indent=2))
    (directory / "history.json").write_text(json.dumps(hist, indent=2))
    log(f"saved {directory.name}: best epoch {best['epoch']} val {best['val_loss']:.4f} in {c['train_seconds']}s ({c['epochs_run']} epochs, {c['n_params']} params)")


def write_manifest(folder: Path) -> None:
    man = {}
    for d in sorted(folder.glob("fold*")):
        if (d / "config.json").exists():
            c = json.load(open(d / "config.json"))
            man[d.name] = {k: c[k] for k in ("checkpoint_sha256", "predictions_sha256", "best_epoch", "train_seconds")}
    (folder / "manifest.json").write_text(json.dumps(man, indent=2))


def select(out: Path) -> dict:
    """Protocol section 3: choose the setting with the lowest geometric-mean ratio of best validation loss to S0 across folds; keep S0 unless the ratio is <= 0.99."""
    rows = []
    for d in sorted((out / "stability").glob("fold*")):
        c = json.load(open(d / "config.json"))
        rows.append({"fold": c["fold"], "setting": c["setting"]["name"], "best_val_loss": c["best_val_scaled_loss"], "best_epoch": c["best_epoch"], "epochs_run": c["epochs_run"], "seconds": c["train_seconds"]})
    df = pd.DataFrame(rows)
    ref = df[df.setting == "S0"].set_index("fold").best_val_loss
    df["ratio_to_S0"] = [r.best_val_loss / ref[r.fold] for r in df.itertuples()]
    summ = df.groupby("setting").agg(folds=("fold", "nunique"), geo_mean_ratio_to_S0=("ratio_to_S0", lambda x: float(np.exp(np.mean(np.log(x))))), median_best_epoch=("best_epoch", "median"), min_best_epoch=("best_epoch", "min"),
                                     mean_seconds=("seconds", "mean")).reset_index()
    assert (summ.folds == 6).all(), "stability stage incomplete"
    cand = summ[summ.setting != "S0"].sort_values("geo_mean_ratio_to_S0").iloc[0]
    chosen = cand.setting if cand.geo_mean_ratio_to_S0 <= SWITCH_MARGIN else "S0"
    df.to_csv(out / "stability_per_run.csv", index=False)
    summ.to_csv(out / "stability_summary.csv", index=False)
    (out / "stability_summary.md").write_text(summ.to_markdown(index=False, floatfmt=".4f"))
    res = {"chosen_setting": chosen, "rule": f"lowest geometric-mean ratio of best validation scaled loss to S0 over 6 folds (seed 0); S0 kept unless ratio <= {SWITCH_MARGIN}", "summary": summ.round(5).to_dict(orient="records")}
    (out / "stability_selection.json").write_text(json.dumps(res, indent=2))
    log(f"selected setting: {chosen}")
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["stability", "select", "main", "ablate"])
    ap.add_argument("--out", default="reports/hybrid_h1")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--folds", default="")
    a = ap.parse_args()
    out = Path(a.out)
    if a.stage == "select":
        select(out)
        return
    S = Setup(out, a.quick, [int(x) for x in a.folds.split(",")] if a.folds else None)
    if a.stage == "stability":
        for r in S.spec.itertuples():
            if r.fold not in S.fold_list:
                continue
            log(f"=== stability, fold {r.fold}")
            for name, cfg in hybrid.SETTINGS.items():
                run_one(S, r, out / "stability" / f"fold{r.fold}_{name}_s0", cfg, 0, "hybrid", "E23 H1 stability")
        write_manifest(out / "stability")
    else:
        sel = json.load(open(out / "stability_selection.json"))["chosen_setting"]
        cfg = hybrid.SETTINGS[sel]
        log(f"selected setting {sel}: {cfg.as_dict()}")
        plan = [("hybrid", s) for s in SEEDS] if a.stage == "main" else [("tonly", 0), ("lonly", 0)]
        for r in S.spec.itertuples():
            if r.fold not in S.fold_list:
                continue
            log(f"=== {a.stage}, fold {r.fold}")
            for kind, seed in plan:
                run_one(S, r, out / "runs" / f"fold{r.fold}_{kind}_{sel}_s{seed}", cfg, seed, kind, "E23 H1")
        write_manifest(out / "runs")
    log("stage done")


if __name__ == "__main__":
    main()
