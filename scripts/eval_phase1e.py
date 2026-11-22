"""Evaluate Phase 1E (E16): GRU 24 h vs 72 h input window, six Phase 1D folds, matched seeds 0-2.  RETROSPECTIVE blocked CV, not untouched validation.
Implements docs/PHASE1E_PROTOCOL.md section 2-3 (paired differences, per seed / fold / event, missing-data strata, pre-registered decision rule).
Usage: python scripts/eval_phase1e.py        Output: reports/phase1e/{tables,figures}, oof_predictions.csv.gz
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from flashflood import data, experiment, metrics  # noqa: E402

OUT = Path("reports/phase1e")
RUNS = OUT / "runs"
D1RUNS = Path("reports/phase1d/runs")
TAB, FIG = OUT / "tables", OUT / "figures"
for p in (TAB, FIG):
    p.mkdir(parents=True, exist_ok=True)
HZ = experiment.HZ
WINS, SEEDS = (24, 72), (0, 1, 2)
REFS = ["persistence", "trend_v2", "ridge_H", "xgb_H"]
B = 2000
LABEL = "Retrospective blocked chronological cross-validation (not untouched validation)"
C = dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#e6e5e1", w24="#6250d6", w72="#eb6834")
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
    mapping = pd.read_csv("reports/phase1d/event_to_fold_mapping.csv", parse_dates=["event_start", "event_end"])
    # ---- assemble pooled out-of-fold predictions
    P = {(w, s, h): np.full(n, np.nan) for w in WINS for s in SEEDS for h in HZ}
    R = {(m, h): np.full(n, np.nan) for m in REFS for h in HZ}
    P1D = {h: np.full(n, np.nan) for h in HZ}
    fold_of = np.zeros(n, int)
    for r in spec.itertuples():
        k = r.fold
        for w in WINS:
            for s in SEEDS:
                z = np.load(RUNS / f"fold{k}_gru_w{w}h_h64_s{s}" / "predictions.npz")
                for hi, h in enumerate(HZ):
                    P[(w, s, h)][z["test_idx"]] = z["pred_test"][:, hi]
        zc = np.load(D1RUNS / f"fold{k}_classical" / "predictions.npz")
        for m in REFS:
            for hi, h in enumerate(HZ):
                R[(m, h)][zc["test_idx"]] = zc[f"pred_{m}"][:, hi]
        z1 = np.load(D1RUNS / f"fold{k}_gru_h64_s0" / "predictions.npz")
        for hi, h in enumerate(HZ):
            P1D[h][z1["test_idx"]] = z1["pred_test"][:, hi]
        fold_of[(idx >= r.test_start) & (idx <= r.test_end)] = k
    oof = fold_of > 0
    elig = {h: ctx.elig[h] & oof for h in HZ}
    for h in HZ:
        for key in [k_ for k_ in P if k_[2] == h] + [(m, h) for m in REFS]:
            a = P[key] if key in P else R[key]
            a[~elig[h]] = np.nan
            assert np.isfinite(a[elig[h]]).all(), key
        P1D[h][~elig[h]] = np.nan
    first_test = spec.test_start.min()
    years = (idx[-1] - first_test).days / 365.25
    ev_eval = {d: ev[(fold_of[ev.i0.values] > 0)].reset_index(drop=True) if len(ev) else ev for d, ev in ctx.ev_all.items()}
    d1h = ctx.H["d_1h"].values
    miss = ctx.s.isna().astype(float)
    frac72 = miss.rolling(288, min_periods=288).mean().values
    frac24 = miss.rolling(96, min_periods=96).mean().values
    subsets = {"all": np.ones(n, bool), "flood_windows_10ft": ctx.win_mask(ev_eval["experimental_stage_10ft"], "exceed"),
               "flood_windows_rise4": ctx.win_mask(ev_eval["experimental_rise_4ft_3h"], "rapid"), "rising_rows_d1h_ge_0.5ft": np.nan_to_num(d1h, nan=0.0) >= 0.5}
    # ---- E1 pooled metrics with paired differences (seed-averaged replicates), E2 per-seed and per-fold differences, E3 decision rule
    e1, e1b, e2s, e2f = [], [], [], []
    verdict_inputs = {}
    for sub, sm in subsets.items():
        for h in HZ:
            mk = elig[h] & sm
            if mk.sum() < 30:
                continue
            y = ctx.tg[h][mk]
            gb = metrics.GroupBoot(ctx.groups[mk], b=B, seed=0)
            rep, pt, mae = {}, {}, {}
            for w in WINS:
                reps = [gb.mse(P[(w, s, h)][mk] - y) for s in SEEDS]
                rep[w] = np.mean(reps, axis=0)
                pt[w] = float(np.sqrt(np.mean([np.mean((P[(w, s, h)][mk] - y) ** 2) for s in SEEDS])))
                mae[w] = float(np.mean([np.mean(np.abs(P[(w, s, h)][mk] - y)) for s in SEEDS]))
                ps = [float(np.sqrt(np.mean((P[(w, s, h)][mk] - y) ** 2))) for s in SEEDS]
                lo, hi = gb.ci(np.sqrt(rep[w]))
                e1.append({"subset": sub, "horizon": h, "window_h": w, "n_rows": int(mk.sum()), "n_storm_groups": int(len(gb.ug)), "rmse_ft_seed_mean": pt[w], "rmse_ci_lo": lo, "rmse_ci_hi": hi,
                           "rmse_sd_across_seeds": float(np.std(ps, ddof=1)), "mae_ft_seed_mean": mae[w], **{f"rmse_seed{s}": v for s, v in zip(SEEDS, ps)}})
            dd = np.sqrt(rep[72]) - np.sqrt(rep[24])
            lo, hi = gb.ci(dd)
            seed_diff = [float(np.sqrt(np.mean((P[(72, s, h)][mk] - y) ** 2)) - np.sqrt(np.mean((P[(24, s, h)][mk] - y) ** 2))) for s in SEEDS]
            fold_diff = {}
            for f in range(1, 7):
                mf = mk & (fold_of == f)
                if mf.sum() >= 30:
                    yf = ctx.tg[h][mf]
                    r72 = np.sqrt(np.mean([np.mean((P[(72, s, h)][mf] - yf) ** 2) for s in SEEDS])); r24 = np.sqrt(np.mean([np.mean((P[(24, s, h)][mf] - yf) ** 2) for s in SEEDS]))
                    fold_diff[f] = float(r72 - r24)
                    e2f.append({"subset": sub, "horizon": h, "fold": f, "n_rows": int(mf.sum()), "rmse_24h": float(r24), "rmse_72h": float(r72), "diff_72_minus_24": float(r72 - r24)})
            e1b.append({"subset": sub, "horizon": h, "diff_72_minus_24_ft": pt[72] - pt[24], "ci_lo": lo, "ci_hi": hi, "interval_excludes_zero": bool(lo > 0 or hi < 0),
                        "seed0_diff": seed_diff[0], "seed1_diff": seed_diff[1], "seed2_diff": seed_diff[2], "seeds_where_72h_better": int(sum(d < 0 for d in seed_diff)),
                        "folds_with_data": len(fold_diff), "folds_where_72h_better": int(sum(v < 0 for v in fold_diff.values())),
                        "mae_diff_72_minus_24_ft": mae[72] - mae[24]})
            verdict_inputs[(sub, h)] = e1b[-1]
            for m in REFS:
                e = R[(m, h)][mk] - y
                e1.append({"subset": sub, "horizon": h, "window_h": m, "n_rows": int(mk.sum()), "n_storm_groups": int(len(gb.ug)), "rmse_ft_seed_mean": float(np.sqrt(np.mean(e ** 2))),
                           "mae_ft_seed_mean": float(np.mean(np.abs(e)))})
    md(pd.DataFrame(e1), "E1_pooled_metrics"); md(pd.DataFrame(e1b), "E1b_paired_72_minus_24"); md(pd.DataFrame(e2f), "E2_per_fold_paired")
    # decision rule (pre-registered)
    rows, n_cons = [], 0
    for h in HZ:
        v = verdict_inputs[("flood_windows_10ft", h)]
        cons = bool(v["ci_hi"] < 0 and v["folds_where_72h_better"] >= 4 and v["seeds_where_72h_better"] == 3)
        n_cons += cons
        va = verdict_inputs[("all", h)]
        rows.append({"horizon": h, "flood10_pooled_diff": v["diff_72_minus_24_ft"], "flood10_ci": f"[{v['ci_lo']:+.3f}, {v['ci_hi']:+.3f}]", "(i) interval entirely below zero": bool(v["ci_hi"] < 0),
                     "(ii) folds 72h better (need >=4 of 6)": f"{v['folds_where_72h_better']}/{v['folds_with_data']}", "(iii) seeds 72h better (need 3 of 3)": f"{v['seeds_where_72h_better']}/3",
                     "CONSISTENT IMPROVEMENT": cons, "all_rows_pooled_diff": va["diff_72_minus_24_ft"], "all_rows_ci": f"[{va['ci_lo']:+.4f}, {va['ci_hi']:+.4f}]",
                     "all_rows_significantly_worse": bool(va["ci_lo"] > 0)})
    adopt = bool(n_cons >= 2 and not any(r_["all_rows_significantly_worse"] for r_ in rows))
    dec = pd.DataFrame(rows); dec["DECISION_72h_ADOPTED"] = adopt
    md(dec, "E3_decision_rule")
    (OUT / "decision.json").write_text(json.dumps({"horizons_with_consistent_improvement_in_flood_windows": int(n_cons), "adopt_72h": adopt,
                                                   "rule": "72 h adopted only if consistent improvement in flood-window RMSE at >= 2 of 4 horizons and no horizon significantly worse on all rows; otherwise retain 24 h"}, indent=2))

    # ---- E4 per-event differences and peak capture (18 evaluated >= 10 ft events)
    e4 = []
    evp = ev_eval["experimental_stage_10ft"]
    for i in range(len(evp)):
        e = evp.iloc[i]
        wm = ctx.win_mask(evp.iloc[[i]], "exceed")
        for h, k in data.HORIZONS.items():
            mk = wm & elig[h]
            pi = int(e.peak_i) - k
            rec = {"event_start": str(idx[int(e.i0)])[:16], "fold": int(fold_of[int(e.i0)]), "storm_cluster": int(ctx.groups[int(e.i0)]), "peak_ft": float(e.peak_ft), "official_stage_ge_25ft": bool(e.peak_ft >= 25),
                   "provisional_data": bool(ctx.prov[int(e.i0):int(e.i1) + 1].any()), "horizon": h, "window_rows": int(mk.sum())}
            for w in WINS:
                rec[f"window_rmse_{w}h"] = float(np.sqrt(np.mean([np.mean((P[(w, s, h)][mk] - ctx.tg[h][mk]) ** 2) for s in SEEDS])))
                pk = [ctx.sv[pi] + P[(w, s, h)][pi] for s in SEEDS]
                rec[f"peak_ratio_{w}h"] = float(np.mean(pk) / e.peak_ft)
            rec["window_rmse_diff_72_minus_24"] = rec["window_rmse_72h"] - rec["window_rmse_24h"]
            rec["peak_ratio_diff_72_minus_24"] = rec["peak_ratio_72h"] - rec["peak_ratio_24h"]
            e4.append(rec)
    e4 = pd.DataFrame(e4); md(e4, "E4_per_event")
    ratio_dev = e4.assign(dev24=(e4.peak_ratio_24h - 1).abs(), dev72=(e4.peak_ratio_72h - 1).abs())
    e4s = ratio_dev.groupby("horizon").apply(lambda g: pd.Series({"events": len(g), "storm_clusters": g.storm_cluster.nunique(), "events_72h_lower_window_rmse": int((g.window_rmse_diff_72_minus_24 < 0).sum()),
                                                                   "median_window_rmse_diff_72_minus_24": g.window_rmse_diff_72_minus_24.median(), "events_72h_peak_ratio_closer_to_1": int((g.dev72 < g.dev24).sum())})).reset_index()
    md(e4s, "E4b_per_event_summary")

    # ---- E5 missing-data sensitivity
    e5 = []
    for strat_name, frac in (("missing fraction of the 72 h window", frac72), ("missing fraction of the 24 h window", frac24)):
        bins = {"none": frac == 0, "up to 5%": (frac > 0) & (frac <= 0.05), "above 5%": frac > 0.05}
        for sub in ("all", "flood_windows_10ft"):
            for h in HZ:
                for bname, bm in bins.items():
                    mk = elig[h] & subsets[sub] & np.nan_to_num(bm, nan=False).astype(bool)
                    if mk.sum() < 30:
                        e5.append({"stratified_by": strat_name, "subset": sub, "horizon": h, "stratum": bname, "n_rows": int(mk.sum()), "note": "fewer than 30 rows: not evaluated"})
                        continue
                    y = ctx.tg[h][mk]
                    gb = metrics.GroupBoot(ctx.groups[mk], b=B, seed=0)
                    rr = {w: np.mean([gb.mse(P[(w, s, h)][mk] - y) for s in SEEDS], axis=0) for w in WINS}
                    pt = {w: float(np.sqrt(np.mean([np.mean((P[(w, s, h)][mk] - y) ** 2) for s in SEEDS]))) for w in WINS}
                    lo, hi = gb.ci(np.sqrt(rr[72]) - np.sqrt(rr[24]))
                    e5.append({"stratified_by": strat_name, "subset": sub, "horizon": h, "stratum": bname, "n_rows": int(mk.sum()), "n_storm_groups": int(len(gb.ug)), "rmse_24h": pt[24], "rmse_72h": pt[72],
                               "diff_72_minus_24": pt[72] - pt[24], "ci_lo": lo, "ci_hi": hi})
    e5 = pd.DataFrame(e5); md(e5, "E5_missing_data_sensitivity")
    share = []
    for set_name in ("all", "flood_windows_10ft"):
        sel = elig["1h"] & subsets[set_name]
        share.append({"rows_set": set_name, "rows": int(sel.sum()), "share_72h_window_any_missing": float(np.mean(frac72[sel] > 0)), "share_24h_window_any_missing": float(np.mean(frac24[sel] > 0)),
                      "share_72h_window_missing_above_5pct": float(np.mean(frac72[sel] > 0.05))})
    md(pd.DataFrame(share), "E5b_missing_share")

    # ---- E6 fixed-rule detection per seed
    e6 = []
    for defn in ("official_action_25ft", "experimental_stage_10ft", "experimental_rise_4ft_3h", "experimental_rise_8ft_3h"):
        evs = ev_eval[defn]
        for h, k in data.HORIZONS.items():
            for w in WINS:
                for s in SEEDS:
                    a = P[(w, s, h)]
                    raw = experiment.fixed_rule_raw(ctx, np.where(np.isfinite(a), a, np.nan), k, ctx.kind_of[defn], ctx.thr_of[defn]) & np.isfinite(a)
                    summ, _ = experiment.detect(ctx, raw, evs, k, elig[h], years)
                    if summ:
                        e6.append({"definition": defn, "horizon": h, "window_h": w, "seed": s, **summ})
    e6 = pd.DataFrame(e6); md(e6, "E6_fixed_rule_detection_per_seed")
    md(e6.groupby(["definition", "horizon", "window_h"]).agg(n_events=("n_events", "first"), storm_clusters=("storm_clusters", "first"), hits_mean=("early_hits", "mean"), hits_min=("early_hits", "min"),
                                                             hits_max=("early_hits", "max"), false_alarm_episodes_mean=("false_alarm_episodes", "mean"), alarm_episodes_mean=("alarm_episodes", "mean")).reset_index(), "E6b_detection_seed_summary")

    # ---- E7 reproducibility versus Phase 1D (24 h, seed 0) and E8 training diagnostics
    e7 = []
    for h in HZ:
        mk = elig[h]
        y = ctx.tg[h][mk]
        a, b_ = P[(24, 0, h)][mk], P1D[h][mk]
        e7.append({"horizon": h, "rows": int(mk.sum()), "rmse_phase1e_24h_seed0": float(np.sqrt(np.mean((a - y) ** 2))), "rmse_phase1d_gru_seed0": float(np.sqrt(np.mean((b_ - y) ** 2))),
                   "rmse_of_difference_between_the_two_prediction_sets_ft": float(np.sqrt(np.mean((a - b_) ** 2)))})
    md(pd.DataFrame(e7), "E7_reproducibility_vs_phase1d")
    diag = []
    for d in sorted(RUNS.glob("fold*")):
        if (d / "config.json").exists():
            c = json.load(open(d / "config.json"))
            diag.append({"fold": c["fold"], "window_h": c["window_hours"], "seed": c["seed"], "rows_train": c["rows"]["train"], "epochs_run": c["epochs_run"], "best_epoch": c["best_epoch"],
                         "best_val_scaled_loss": c["best_val_scaled_loss"], "train_seconds": c["train_seconds"]})
    md(pd.DataFrame(diag), "E8_training_diagnostics")

    # ---- OOF predictions file
    rows_ = np.where(oof & np.any([ctx.elig[h] for h in HZ], axis=0))[0]
    df = pd.DataFrame({"timestamp_utc": idx[rows_].strftime("%Y-%m-%d %H:%M"), "fold": fold_of[rows_], "stage_ft": np.round(ctx.sv[rows_], 3)})
    for h in HZ:
        df[f"target_stage_{h}_ft"] = np.round(ctx.sv[rows_] + np.where(ctx.elig[h][rows_], ctx.tg[h][rows_], np.nan), 3)
        for w in WINS:
            for s in SEEDS:
                df[f"pred_gru{w}h_s{s}_{h}_ft"] = np.round(ctx.sv[rows_] + P[(w, s, h)][rows_], 3)
    df.to_csv(OUT / "oof_predictions.csv.gz", index=False, compression="gzip")

    # ---- figures
    E1b = pd.DataFrame(e1b)
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    for ax, sub in zip(axes, ["all", "flood_windows_10ft", "flood_windows_rise4"]):
        d = E1b[E1b["subset"] == sub].set_index("horizon").reindex(HZ)
        x = np.arange(len(HZ))
        ax.axhline(0, color=C["ink2"], lw=0.8)
        ax.errorbar(x, d.diff_72_minus_24_ft, yerr=[d.diff_72_minus_24_ft - d.ci_lo, d.ci_hi - d.diff_72_minus_24_ft], fmt="o", color=C["w72"], capsize=3, label="pooled (95% CI)")
        for j, s in enumerate(SEEDS):
            ax.scatter(x + 0.12 * (j - 1), d[f"seed{s}_diff"], s=12, color=C["ink"], zorder=3, label="individual seeds" if j == 0 else None)
        ax.set_xticks(x); ax.set_xticklabels(HZ); ax.set_ylabel("RMSE(72 h) - RMSE(24 h)  (ft)"); ax.set_title(sub.replace("_", " ") + "  (below 0 = 72 h better)")
    axes[0].legend(frameon=False, fontsize=7)
    fig.suptitle(LABEL, fontsize=8, color=C["ink2"], x=0.01, ha="left"); fig.tight_layout(); fig.savefig(FIG / "fig1_paired_differences.png", dpi=150); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for ax, h in zip(axes, ["1h", "3h"]):
        d = e4[e4.horizon == h].sort_values("window_rmse_diff_72_minus_24")
        ax.barh(range(len(d)), d.window_rmse_diff_72_minus_24, color=[C["w72"] if v > 0 else C["w24"] for v in d.window_rmse_diff_72_minus_24])
        ax.set_yticks(range(len(d))); ax.set_yticklabels([f"{r.event_start[:10]} ({r.peak_ft:.0f} ft)" for r in d.itertuples()], fontsize=6.5); ax.axvline(0, color=C["ink2"], lw=0.8)
        ax.set_xlabel("window RMSE 72 h minus 24 h (ft); purple = 72 h better"); ax.set_title(f"Per-event difference, {h} (18 events)")
    fig.suptitle(LABEL, fontsize=8, color=C["ink2"], x=0.01, ha="left"); fig.tight_layout(); fig.savefig(FIG / "fig2_per_event_differences.png", dpi=150); plt.close(fig)
    print("Phase 1E evaluation written. Decision (pre-registered rule): adopt 72 h =", adopt, "| horizons consistent in flood windows:", n_cons)


if __name__ == "__main__":
    main()
