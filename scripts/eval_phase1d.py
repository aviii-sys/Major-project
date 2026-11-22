"""Evaluate the Phase 1D blocked chronological cross-validation (E14).  RETROSPECTIVE blocked CV: not untouched external validation.
Pools the six held-out blocks into one out-of-fold (OOF) prediction set per model.   Usage: python scripts/eval_phase1d.py
Outputs: reports/phase1d/{tables,figures}, oof_predictions.csv.gz
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from flashflood import data, experiment, folds, metrics, models  # noqa: E402

OUT = Path("reports/phase1d")
RUNS = OUT / "runs"
TAB, FIG = OUT / "tables", OUT / "figures"
for p in (TAB, FIG):
    p.mkdir(parents=True, exist_ok=True)
HZ = experiment.HZ
MODELS = ["persistence", "trend_v2", "ridge_H", "xgb_H", "gru", "lstm"]
DEEP = ["gru", "lstm"]
B = 2000
LABEL = "Retrospective blocked chronological cross-validation (not untouched validation)"
COL = {"persistence": "#52514e", "trend_v2": "#eda100", "ridge_H": "#1baf7a", "xgb_H": "#2a78d6", "gru": "#6250d6", "lstm": "#eb6834"}
C = dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#e6e5e1")
plt.rcParams.update({"figure.facecolor": C["surface"], "axes.facecolor": C["surface"], "savefig.facecolor": C["surface"], "axes.edgecolor": C["grid"], "axes.labelcolor": C["ink2"],
                     "text.color": C["ink"], "xtick.color": C["ink2"], "ytick.color": C["ink2"], "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 8, "axes.titleweight": "bold", "axes.titlelocation": "left"})


def md(df, name):
    df.to_csv(TAB / f"{name}.csv", index=False)
    (TAB / f"{name}.md").write_text(df.to_markdown(index=False, floatfmt=".6g"))


def main() -> None:
    ctx = experiment.build_context()
    n, idx = ctx.n, ctx.s.index
    spec = pd.read_csv(OUT / "fold_specification.csv", parse_dates=["train_start", "train_end", "val_start", "val_end", "test_start", "test_end"])
    mapping = pd.read_csv(OUT / "event_to_fold_mapping.csv", parse_dates=["event_start", "event_end"])
    # ---- assemble pooled OOF predictions
    P = {(m, h): np.full(n, np.nan) for m in MODELS for h in HZ}
    fold_of = np.zeros(n, int)
    for r in spec.itertuples():
        k = r.fold
        for m in MODELS:
            d = RUNS / (f"fold{k}_{m}_h64_s0" if m in DEEP else f"fold{k}_classical")
            z = np.load(d / "predictions.npz")
            arr = z["pred_test"] if m in DEEP else z[f"pred_{m}"]
            for hi, h in enumerate(HZ):
                P[(m, h)][z["test_idx"]] = arr[:, hi]
        fold_of[(idx >= r.test_start) & (idx <= r.test_end)] = k
    oof = fold_of > 0
    elig_all = {h: ctx.elig[h] & oof for h in HZ}
    for h in HZ:                                                  # every eligible held-out row predicted exactly once by every model
        for m in MODELS:
            P[(m, h)][~elig_all[h]] = np.nan                      # deep heads also output rows eligible only at other horizons: not evaluated
            assert np.isfinite(P[(m, h)][elig_all[h]]).all(), (m, h)
            assert not np.isfinite(P[(m, h)][~elig_all[h]]).any(), (m, h)
    first_test = spec.test_start.min()
    years = (idx[-1] - first_test).days / 365.25
    ev_eval = {d: ev[(fold_of[ev.i0.values] > 0)].reset_index(drop=True) if len(ev) else ev for d, ev in ctx.ev_all.items()}
    subsets = {"all": np.ones(n, bool),
               "event_windows_stage10ft": ctx.win_mask(ev_eval["experimental_stage_10ft"], "exceed"),
               "event_windows_rise4ft3h": ctx.win_mask(ev_eval["experimental_rise_4ft_3h"], "rapid")}

    # ---- D1 pooled regression metrics (+ paired bootstrap), D3 paired differences
    d1, d3 = [], []
    pairs = [("gru", "lstm"), ("gru", "trend_v2"), ("gru", "ridge_H"), ("gru", "xgb_H"), ("lstm", "trend_v2"), ("lstm", "ridge_H"), ("lstm", "xgb_H")]
    for sub, sm in subsets.items():
        for h in HZ:
            mk = elig_all[h] & sm
            y = ctx.tg[h][mk]
            gb = metrics.GroupBoot(ctx.groups[mk], b=B, seed=0)
            mse_p = gb.mse(-y)
            rep, pt = {}, {}
            for m in MODELS:
                e = P[(m, h)][mk] - y
                rep[m] = gb.mse(e)
                pt[m] = {"rmse": float(np.sqrt(np.mean(e ** 2))), "mae": float(np.mean(np.abs(e)))}
            mse_pp = float(np.mean(y ** 2))
            for m in MODELS:
                lo, hi = gb.ci(np.sqrt(rep[m])); slo, shi = gb.ci(1 - rep[m] / mse_p)
                d1.append({"subset": sub, "horizon": h, "model": m, "n_rows": int(mk.sum()), "n_storm_groups": int(len(gb.ug)), "rmse_ft": pt[m]["rmse"], "rmse_ci_lo": lo, "rmse_ci_hi": hi,
                           "mae_ft": pt[m]["mae"], "skill_vs_persistence": 1 - pt[m]["rmse"] ** 2 / mse_pp, "skill_ci_lo": slo, "skill_ci_hi": shi})
            for a, b_ in pairs:
                dd = np.sqrt(rep[a]) - np.sqrt(rep[b_]); lo, hi = gb.ci(dd)
                d3.append({"subset": sub, "horizon": h, "model": a, "reference": b_, "rmse_diff_ft": pt[a]["rmse"] - pt[b_]["rmse"], "ci_lo": lo, "ci_hi": hi, "interval_excludes_zero": bool(lo > 0 or hi < 0)})
    md(pd.DataFrame(d1), "D1_pooled_regression_metrics"); md(pd.DataFrame(d3), "D3_paired_model_differences")

    # ---- D2 per fold
    d2 = []
    for r in spec.itertuples():
        fm = fold_of == r.fold
        n10 = int(((mapping.definition == "experimental_stage_10ft") & (mapping.fold == r.fold)).sum())
        for sub in ("all", "event_windows_stage10ft"):
            for h in HZ:
                mk = elig_all[h] & fm & subsets[sub]
                if mk.sum() < 30:
                    continue
                y = ctx.tg[h][mk]
                for m in MODELS:
                    e = P[(m, h)][mk] - y
                    d2.append({"fold": r.fold, "test_block": f"{r.test_start:%Y-%m-%d} to {r.test_end:%Y-%m-%d}", "events_10ft_in_block": n10, "subset": sub, "horizon": h, "model": m, "n_rows": int(mk.sum()),
                               "rmse_ft": float(np.sqrt(np.mean(e ** 2))), "mae_ft": float(np.mean(np.abs(e))), "rmse_persistence_ft": float(np.sqrt(np.mean(y ** 2)))})
    d2 = pd.DataFrame(d2); md(d2, "D2_per_fold_regression")
    # consistency of GRU/LSTM versus references across folds (flood windows, 3 h and 1 h)
    cons = []
    for sub in ("all", "event_windows_stage10ft"):
        for h in HZ:
            for a in DEEP:
                for ref in ("trend_v2", "ridge_H", "xgb_H"):
                    x = d2[(d2["subset"] == sub) & (d2.horizon == h)].pivot(index="fold", columns="model", values="rmse_ft")
                    if a in x and ref in x:
                        cons.append({"subset": sub, "horizon": h, "model": a, "reference": ref, "folds_compared": int(x[[a, ref]].dropna().shape[0]), "folds_where_model_better": int((x[a] < x[ref]).sum())})
    md(pd.DataFrame(cons), "D2b_fold_consistency")

    # ---- D4 per event (evaluated events only)
    d4 = []
    for defn in ("experimental_stage_10ft", "official_action_25ft", "experimental_rise_4ft_3h"):
        evp = ev_eval[defn]
        for i in range(len(evp)):
            e = evp.iloc[i]
            wm = ctx.win_mask(evp.iloc[[i]], ctx.kind_of[defn])
            fo = int(fold_of[int(e.i0)])
            for h, k in data.HORIZONS.items():
                mk = wm & elig_all[h]
                pi = int(e.peak_i) - k
                for m in MODELS:
                    a = P[(m, h)]
                    mm = mk & np.isfinite(a)
                    if mm.sum() == 0:
                        continue
                    ph = ctx.sv[pi] + a[pi] if pi >= 0 and np.isfinite(a[pi]) else np.nan
                    d4.append({"definition": defn, "event_start": str(idx[int(e.i0)])[:16], "fold": fo, "storm_cluster": int(ctx.groups[int(e.i0)]), "peak_ft": float(e.peak_ft),
                               "provisional_data": bool(ctx.prov[int(e.i0):int(e.i1) + 1].any()), "horizon": h, "model": m, "window_rows": int(mm.sum()),
                               "window_rmse_ft": float(np.sqrt(np.mean((a[mm] - ctx.tg[h][mm]) ** 2))), "peak_forecast_ft": float(ph), "peak_ratio": float(ph / e.peak_ft)})
    d4 = pd.DataFrame(d4); md(d4, "D4_per_event")

    # ---- D5 fixed-rule detection on pooled OOF predictions
    d5, d5e = [], []
    for defn in ctx.ev_all:
        evp = ev_eval[defn]
        for h, k in data.HORIZONS.items():
            for m in MODELS:
                a = P[(m, h)]
                raw = experiment.fixed_rule_raw(ctx, np.where(np.isfinite(a), a, np.nan), k, ctx.kind_of[defn], ctx.thr_of[defn]) & np.isfinite(a)
                summ, pe = experiment.detect(ctx, raw, evp, k, elig_all[h], years)
                if summ:
                    d5.append({"definition": defn, "horizon": h, "model": m, **summ})
                if len(pe):
                    d5e.append(pe.assign(definition=defn, horizon=h, model=m, event_start=lambda x: x.t0)[["definition", "horizon", "model", "event_start", "peak_ft", "status", "lead_h"]])
    md(pd.DataFrame(d5), "D5_fixed_rule_detection_pooled_oof"); md(pd.concat(d5e), "D5b_fixed_rule_per_event")

    # ---- D6 event coverage and exclusions
    cov = mapping.groupby(["definition", "status"]).agg(events=("storm_cluster", "size"), storm_clusters=("storm_cluster", "nunique")).reset_index()
    md(cov, "D6_event_coverage_and_exclusions")
    md(mapping[mapping.status == "excluded"][["definition", "event_start", "peak_ft", "storm_cluster", "reason"]], "D6b_excluded_events")
    md(mapping[mapping.status == "evaluated"].groupby(["definition", "fold"]).agg(events=("storm_cluster", "size"), storm_clusters=("storm_cluster", "nunique")).reset_index(), "D6c_events_per_fold")

    # ---- D7 diagnostics
    diag = []
    for r in spec.itertuples():
        for a in DEEP:
            c = json.load(open(RUNS / f"fold{r.fold}_{a}_h64_s0" / "config.json"))
            diag.append({"fold": r.fold, "model": a, "seed": c["seed"], "rows_train": c["rows"]["train"], "rows_val": c["rows"]["val"], "rows_test": c["rows"]["test"], "epochs_run": c["epochs_run"],
                         "best_epoch": c["best_epoch"], "best_val_scaled_loss": c["best_val_scaled_loss"], "train_seconds": c["train_seconds"]})
    md(pd.DataFrame(diag), "D7_training_diagnostics")
    cl = []
    for r in spec.itertuples():
        c = json.load(open(RUNS / f"fold{r.fold}_classical" / "config.json"))
        cl.append({"fold": r.fold, "trend_selection_by": c["trend_selection_by"], "validation_events": c["validation_events_used_for_trend"],
                   **{f"{k_}": json.dumps(v) for k_, v in c.items() if k_.startswith(("trend_", "ridge_", "xgb_")) and isinstance(v, dict)}})
    md(pd.DataFrame(cl), "D7b_classical_selected_hyperparameters")

    # ---- OOF predictions file (machine readable)
    rows = np.where(oof & np.any([ctx.elig[h] for h in HZ], axis=0))[0]
    df = pd.DataFrame({"timestamp_utc": idx[rows].strftime("%Y-%m-%d %H:%M"), "fold": fold_of[rows], "stage_ft": np.round(ctx.sv[rows], 3),
                       "in_flood_window_10ft": subsets["event_windows_stage10ft"][rows], "in_flood_window_rise4": subsets["event_windows_rise4ft3h"][rows]})
    for h, k in data.HORIZONS.items():
        df[f"target_stage_{h}_ft"] = np.round(ctx.sv[rows] + np.where(ctx.elig[h][rows], ctx.tg[h][rows], np.nan), 3)
        for m in MODELS:
            df[f"pred_{m}_{h}_ft"] = np.round(ctx.sv[rows] + P[(m, h)][rows], 3)
    df.to_csv(OUT / "oof_predictions.csv.gz", index=False, compression="gzip")

    # ---- figures
    D1 = pd.DataFrame(d1)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    for ax, sub in zip(axes, ["all", "event_windows_stage10ft"]):
        d = D1[D1["subset"] == sub]
        for j, m in enumerate(MODELS):
            x = np.arange(len(HZ)) + (j - 2.5) * 0.13
            dm = d[d.model == m].set_index("horizon").reindex(HZ)
            ax.bar(x, dm.rmse_ft, width=0.12, color=COL[m], label=m)
            ax.errorbar(x, dm.rmse_ft, yerr=[dm.rmse_ft - dm.rmse_ci_lo, dm.rmse_ci_hi - dm.rmse_ft], fmt="none", ecolor=C["ink2"], lw=0.7, capsize=1.5)
        ax.set_xticks(range(len(HZ))); ax.set_xticklabels(HZ); ax.set_ylabel("RMSE (ft)"); ax.grid(axis="x", visible=False)
    axes[0].set_yscale("log"); axes[0].set_title("Pooled OOF, all rows (log scale)"); axes[1].set_title("Pooled OOF, flood windows of >=10 ft events")
    axes[0].legend(frameon=False, fontsize=7, ncol=2)
    fig.suptitle(LABEL, fontsize=8, color=C["ink2"], x=0.01, ha="left"); fig.tight_layout(); fig.savefig(FIG / "fig1_pooled_rmse.png", dpi=150); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4))
    for ax, h in zip(axes, ["1h", "3h"]):
        d = d2[(d2["subset"] == "event_windows_stage10ft") & (d2.horizon == h)]
        for m in MODELS[1:]:
            dm = d[d.model == m].set_index("fold")
            ax.plot(dm.index, dm.rmse_ft, "o-", color=COL[m], lw=1, ms=4, label=m)
        ax.set_xlabel("fold (held-out block)"); ax.set_ylabel("flood-window RMSE (ft)"); ax.set_title(f"Per-fold flood-window RMSE, {h}")
        nev = d.drop_duplicates("fold").set_index("fold").events_10ft_in_block
        ax.set_xticks(list(nev.index)); ax.set_xticklabels([f"{f}\n({nev[f]} ev)" for f in nev.index])
    axes[0].legend(frameon=False, fontsize=7)
    fig.suptitle(LABEL, fontsize=8, color=C["ink2"], x=0.01, ha="left"); fig.tight_layout(); fig.savefig(FIG / "fig2_per_fold_flood_window_rmse.png", dpi=150); plt.close(fig)

    ev10 = ev_eval["experimental_stage_10ft"]
    for h, k in (("3h", 12), ("1h", 4)):
        nrow, ncol = 6, 3
        fig, axes = plt.subplots(nrow, ncol, figsize=(13, 15))
        for ax in axes.ravel():
            ax.set_visible(False)
        for i in range(len(ev10)):
            ax = axes.ravel()[i]; ax.set_visible(True)
            e = ev10.iloc[i]
            a_, b_ = idx[int(e.i0)] - pd.Timedelta("20h"), idx[int(e.i1)] + pd.Timedelta("16h")
            ax.plot(ctx.s.loc[a_:b_].index, ctx.s.loc[a_:b_].values, color=C["ink"], lw=1.4, label="observed")
            for m in ("trend_v2", "gru", "lstm"):
                f = pd.Series(ctx.sv + P[(m, h)], index=idx).shift(k)
                ax.plot(f.loc[a_:b_].index, f.loc[a_:b_].values, color=COL[m], lw=0.9, label=f"{m} {h} ahead")
            off = " [official]" if ctx.sv[int(e.peak_i)] >= 25 else ""
            ax.set_title(f"{idx[int(e.i0)]:%Y-%m-%d}  peak {e.peak_ft:.1f} ft  fold {int(fold_of[int(e.i0)])}{off}", fontsize=8)
            ax.tick_params(axis="x", labelrotation=30, labelsize=6)
        axes.ravel()[0].legend(frameon=False, fontsize=6.5)
        fig.suptitle(f"Observed versus {h}-ahead forecasts at held-out >=10 ft events. {LABEL}", fontsize=9, x=0.01, ha="left"); fig.tight_layout(rect=(0, 0, 1, 0.98))
        fig.savefig(FIG / f"fig3_events_{h}.png", dpi=110); plt.close(fig)
    print("Phase 1D evaluation written; OOF rows:", len(df), "| pooled rows 1h:", int(elig_all["1h"].sum()))


if __name__ == "__main__":
    main()
