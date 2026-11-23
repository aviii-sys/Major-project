"""Evaluate H1 (E23): stage-only hybrid Transformer+LSTM versus the matched baselines, per docs/HYBRID_H1_PROTOCOL.md sections 5-6.
RETROSPECTIVE blocked chronological cross-validation, NOT untouched validation. Reads saved predictions only.
Usage (project root): PYTHONPATH=src python scripts/eval_hybrid_h1.py        Output: reports/hybrid_h1/{tables,figures,decision.json,oof_predictions.csv.gz}
"""
import json
import os
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from flashflood import data, experiment, leadtime, metrics, oof  # noqa: E402

OUT = Path(os.environ.get("H1_OUT", "reports/hybrid_h1"))
RUNS = OUT / "runs"
TAB, FIG = OUT / "tables", OUT / "figures"
for p in (TAB, FIG):
    p.mkdir(parents=True, exist_ok=True)
HZ = experiment.HZ
KSTEP = data.HORIZONS
SEEDS = (0, 1, 2)
REFS = ["persistence", "trend_v2", "ridge_H", "xgb_H"]
B = 2000
LABEL = "Retrospective blocked chronological cross-validation (not untouched validation)"
C = dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#e6e5e1", hybrid="#6250d6", gru="#2a78d6", ridge="#1baf7a", trend="#eda100", xgb="#e87ba4", lstm="#eb6834", ref="#8d8c88")
plt.rcParams.update({"figure.facecolor": C["surface"], "axes.facecolor": C["surface"], "savefig.facecolor": C["surface"], "axes.edgecolor": C["grid"], "axes.labelcolor": C["ink2"], "text.color": C["ink"],
                     "xtick.color": C["ink2"], "ytick.color": C["ink2"], "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 8, "axes.titleweight": "bold", "axes.titlelocation": "left"})


def md(df, name):
    df.to_csv(TAB / f"{name}.csv", index=False)
    (TAB / f"{name}.md").write_text(df.to_markdown(index=False, floatfmt=".5g"))


def main() -> None:
    sel = json.load(open(OUT / "stability_selection.json"))["chosen_setting"]
    ctx = experiment.build_context()
    idx, n = ctx.s.index, ctx.n
    spec = oof.fold_spec()
    fold_of = oof.fold_of_array(idx, spec)
    elig = {h: ctx.elig[h] & (fold_of > 0) for h in HZ}
    years = (idx[-1] - spec.test_start.min()).days / 365.25
    ev_eval = {d: ev[(fold_of[ev.i0.values] > 0)].reset_index(drop=True) for d, ev in ctx.ev_all.items()}

    # ---- assemble predicted stage changes
    P = {}                                                                         # (name, h) -> array
    for s in SEEDS:
        a = oof.deep_changes(n, {k: RUNS / f"fold{k}_hybrid_{sel}_s{s}" for k in range(1, 7)})
        b = oof.phase1e_gru24(n, s)
        for h in HZ:
            P[(f"hybrid_s{s}", h)], P[(f"gru24_s{s}", h)] = a[h], b[h]
    abl_ok = all((RUNS / f"fold{k}_{kind}_{sel}_s0" / "predictions.npz").exists() for k in range(1, 7) for kind in ("tonly", "lonly"))
    if abl_ok:
        for kind in ("tonly", "lonly"):
            a = oof.deep_changes(n, {k: RUNS / f"fold{k}_{kind}_{sel}_s0" for k in range(1, 7)})
            for h in HZ:
                P[(f"{kind}_s0", h)] = a[h]
    cls = oof.classical_changes(n)
    lstm = oof.phase1d_deep(n, "lstm", 0)
    for h in HZ:
        for m in REFS:
            P[(m, h)] = cls[(m, h)]
        P[("lstm_s0", h)] = lstm[h]
    for (name, h), arr in P.items():
        arr[~elig[h]] = np.nan
        assert np.isfinite(arr[elig[h]]).all(), (name, h)

    d1h = ctx.H["d_1h"].values
    subsets = {"all": np.ones(n, bool), "flood_windows_10ft": ctx.win_mask(ev_eval["experimental_stage_10ft"], "exceed"), "flood_windows_rise4": ctx.win_mask(ev_eval["experimental_rise_4ft_3h"], "rapid"),
               "rising_rows_d1h_ge_0.5ft": np.nan_to_num(d1h, nan=0.0) >= 0.5}
    COMP = {"gru24": "matched GRU 24 h (Phase 1E, same seed index)", "ridge_H": "ridge H", "trend_v2": "damped trend", "xgb_H": "XGBoost H", "lstm_s0": "LSTM 24 h (Phase 1D, seed 0)"}

    def rm(name_fn, mk, y, h):
        return [np.sqrt(np.mean((P[(name_fn(s), h)][mk] - y) ** 2)) for s in SEEDS]

    # ---- H1_1 pooled metrics, H1_2 paired differences, H1_4 per fold
    t1, t2, t4 = [], [], []
    for sub, sm in subsets.items():
        for h in HZ:
            mk = elig[h] & sm
            if mk.sum() < 30:
                continue
            y = ctx.tg[h][mk]
            gb = metrics.GroupBoot(ctx.groups[mk], b=B, seed=0)
            def reps(name_fn):
                return np.mean([gb.mse(P[(name_fn(s), h)][mk] - y) for s in SEEDS], axis=0)
            hyb_rep = reps(lambda s: f"hybrid_s{s}")
            hyb_pt = float(np.sqrt(np.mean([np.mean((P[(f"hybrid_s{s}", h)][mk] - y) ** 2) for s in SEEDS])))
            lo, hi = gb.ci(np.sqrt(hyb_rep))
            ps = rm(lambda s: f"hybrid_s{s}", mk, y, h)
            t1.append({"subset": sub, "horizon": h, "model": "hybrid (3 seeds)", "n_rows": int(mk.sum()), "n_storm_groups": int(len(gb.ug)), "rmse_ft": hyb_pt, "rmse_ci_lo": lo, "rmse_ci_hi": hi,
                       "rmse_sd_across_seeds": float(np.std(ps, ddof=1)), "mae_ft": float(np.mean([np.mean(np.abs(P[(f'hybrid_s{s}', h)][mk] - y)) for s in SEEDS]))})
            comp_pt, comp_rep, comp_seed = {}, {}, {}
            for c in COMP:
                if c == "gru24":
                    comp_rep[c] = reps(lambda s: f"gru24_s{s}")
                    comp_seed[c] = rm(lambda s: f"gru24_s{s}", mk, y, h)
                    comp_pt[c] = float(np.sqrt(np.mean([np.mean((P[(f"gru24_s{s}", h)][mk] - y) ** 2) for s in SEEDS])))
                    mae_c = float(np.mean([np.mean(np.abs(P[(f'gru24_s{s}', h)][mk] - y)) for s in SEEDS]))
                    lo_c, hi_c = gb.ci(np.sqrt(comp_rep[c]))
                    t1.append({"subset": sub, "horizon": h, "model": "GRU 24 h (3 seeds, Phase 1E)", "n_rows": int(mk.sum()), "n_storm_groups": int(len(gb.ug)), "rmse_ft": comp_pt[c], "rmse_ci_lo": lo_c, "rmse_ci_hi": hi_c,
                               "rmse_sd_across_seeds": float(np.std(comp_seed[c], ddof=1)), "mae_ft": mae_c})
                else:
                    e = P[(c, h)][mk] - y
                    comp_rep[c] = gb.mse(e)
                    comp_pt[c] = float(np.sqrt(np.mean(e ** 2)))
                    comp_seed[c] = [comp_pt[c]] * 3
                    t1.append({"subset": sub, "horizon": h, "model": COMP[c], "n_rows": int(mk.sum()), "n_storm_groups": int(len(gb.ug)), "rmse_ft": comp_pt[c], "mae_ft": float(np.mean(np.abs(e)))})
            for c in COMP:
                dd = np.sqrt(hyb_rep) - np.sqrt(comp_rep[c])
                lo, hi = gb.ci(dd)
                sdiff = [float(a - b) for a, b in zip(ps, comp_seed[c])]
                fd = {}
                for f in range(1, 7):
                    mf = mk & (fold_of == f)
                    if mf.sum() >= 30:
                        yf = ctx.tg[h][mf]
                        rh = np.sqrt(np.mean([np.mean((P[(f"hybrid_s{s}", h)][mf] - yf) ** 2) for s in SEEDS]))
                        if c == "gru24":
                            rc = np.sqrt(np.mean([np.mean((P[(f"gru24_s{s}", h)][mf] - yf) ** 2) for s in SEEDS]))
                        else:
                            rc = np.sqrt(np.mean((P[(c, h)][mf] - yf) ** 2))
                        fd[f] = float(rh - rc)
                        t4.append({"subset": sub, "horizon": h, "comparator": COMP[c], "fold": f, "n_rows": int(mf.sum()), "rmse_hybrid": float(rh), "rmse_comparator": float(rc), "diff_hybrid_minus_comparator": float(rh - rc)})
                t2.append({"subset": sub, "horizon": h, "comparator": c, "comparator_label": COMP[c], "diff_ft": hyb_pt - comp_pt[c], "diff_pct_of_comparator": 100 * (hyb_pt - comp_pt[c]) / comp_pt[c], "ci_lo": lo, "ci_hi": hi,
                           "interval_excludes_zero": bool(lo > 0 or hi < 0), "ci_hi_pct_of_comparator": 100 * hi / comp_pt[c], "seed0_diff": sdiff[0], "seed1_diff": sdiff[1], "seed2_diff": sdiff[2],
                           "seeds_where_hybrid_better": int(sum(d < 0 for d in sdiff)), "folds_with_data": len(fd), "folds_where_hybrid_better": int(sum(v < 0 for v in fd.values()))})
    T1, T2, T4 = pd.DataFrame(t1), pd.DataFrame(t2), pd.DataFrame(t4)
    md(T1, "H1_1_pooled_rmse"); md(T2, "H1_2_paired_hybrid_minus_comparator"); md(T4, "H1_4_per_fold_paired")

    # ---- H1_3 pre-registered decision rule (flood windows >= 10 ft; ridge H and matched GRU 24 h; 1 h and 3 h)
    rows, all_ok = [], True
    for c in ("ridge_H", "gru24"):
        harm = bool(((T2[(T2.subset == "all") & (T2.comparator == c)].ci_hi_pct_of_comparator) > 2.0).any())
        for h in ("1h", "3h"):
            r = T2[(T2.subset == "flood_windows_10ft") & (T2.horizon == h) & (T2.comparator == c)].iloc[0]
            i_ = bool(r.ci_hi < 0)
            ii_ = bool(r.folds_where_hybrid_better >= 4)
            iii_ = bool(r.seeds_where_hybrid_better == 3)
            cons = i_ and ii_ and iii_
            mat = bool(cons and r.diff_pct_of_comparator <= -5.0)
            all_ok &= cons and not harm
            rows.append({"comparator": COMP[c], "horizon": h, "pooled_diff_ft": r.diff_ft, "pct_of_comparator": r.diff_pct_of_comparator, "interval": f"[{r.ci_lo:+.3f}, {r.ci_hi:+.3f}]", "(i) interval below zero": i_,
                         "(ii) folds hybrid better (need >=4 of 6)": f"{int(r.folds_where_hybrid_better)}/{int(r.folds_with_data)}", "(iii) seeds hybrid better (need 3 of 3)": f"{int(r.seeds_where_hybrid_better)}/3",
                         "CONSISTENT": cons, "MATERIAL (>=5%)": mat, "harm flag (all-row upper bound > +2%)": harm})
    T3 = pd.DataFrame(rows)
    md(T3, "H1_3_decision_rule_H1a")

    # ---- H1_5 warning lead (fixed alarm rule), H1b rule, H1_6 hard events
    names = [f"hybrid_s{s}" for s in SEEDS] + [f"gru24_s{s}" for s in SEEDS] + REFS + ["lstm_s0"] + ([f"{k}_s0" for k in ("tonly", "lonly")] if abl_ok else [])
    srows, erows = [], []
    for nm in names:
        arr = {h: P[(nm, h)] for h in HZ}
        s_r, e_r = leadtime.detect_all(ctx, arr, ev_eval, elig, years, HZ, KSTEP)
        srows += [{"model": nm, **r} for r in s_r]
        erows += [{"model": nm, **r} for r in e_r]
    S, E = pd.DataFrame(srows), pd.DataFrame(erows)
    md(S, "H1_5_leadtime_per_model_and_seed"); md(E, "H1_6_per_event_leads_all_models")
    t7, h1b_ok = [], {}
    for defn in leadtime.DEFINITIONS:
        for h in HZ:
            q = S[(S.definition == defn) & (S.horizon == h)]
            hy = q[q.model.str.startswith("hybrid_")]
            if len(hy) != 3:
                continue
            cand = {}
            for c in ("ridge_H", "trend_v2", "xgb_H", "lstm_s0"):
                r = q[q.model == c].iloc[0]
                cand[COMP[c]] = (float(r.hits_with_lead_ge_30min), float(r.false_alarm_episodes))
            gq = q[q.model.str.startswith("gru24_")]
            cand[COMP["gru24"]] = (float(gq.hits_with_lead_ge_30min.mean()), float(gq.false_alarm_episodes.mean()))
            best = max(cand.items(), key=lambda kv: (kv[1][0], -kv[1][1]))
            hm, hf = float(hy.hits_with_lead_ge_30min.mean()), float(hy.false_alarm_episodes.mean())
            improves = bool(hm >= best[1][0] + 2 and hf <= best[1][1])
            t7.append({"definition": defn, "horizon": h, "events": int(hy.events.iloc[0]), "storm_clusters": int(hy.storm_clusters.iloc[0]), "hybrid_lead30_mean": hm, "hybrid_lead30_min": int(hy.hits_with_lead_ge_30min.min()),
                       "hybrid_lead30_max": int(hy.hits_with_lead_ge_30min.max()), "hybrid_false_alarm_episodes_mean": hf, "hybrid_early_hits_mean": float(hy.early_hits.mean()),
                       "best_baseline": best[0], "best_baseline_lead30": best[1][0], "best_baseline_false_alarm_episodes": best[1][1], "hybrid_minus_best_lead30": hm - best[1][0],
                       "IMPROVES_30MIN_LEAD (>= +2 events at no more false alarms)": improves, "descriptive_only_official": defn == "official_action_25ft"})
            if h in ("1h", "3h") and defn != "official_action_25ft":
                h1b_ok[(defn, h)] = improves
    T7 = pd.DataFrame(t7)
    md(T7, "H1_7_H1b_lead30_vs_best_baseline")
    hard = pd.read_csv("reports/hybrid_h0/tables/H0_5b_events_no_baseline_reaches_30min.csv")
    hr = []
    for r in hard.itertuples():
        for h in ("30m", "1h", "3h"):
            e = E[(E.definition == r.definition) & (E.event_start == r.event_start) & (E.horizon == h) & E.model.str.startswith("hybrid_")]
            for q in e.itertuples():
                hr.append({"definition": r.definition, "event_start": r.event_start, "peak_ft": r.peak_ft, "horizon": h, "model": q.model, "status": q.status, "lead_h": q.lead_h})
    md(pd.DataFrame(hr), "H1_8_hard_events_hybrid_leads")

    # ---- H1_9 ablations (seed 0)
    if abl_ok:
        ab = []
        for sub, sm in subsets.items():
            for h in HZ:
                mk = elig[h] & sm
                if mk.sum() < 30:
                    continue
                y = ctx.tg[h][mk]
                rec = {"subset": sub, "horizon": h, "n_rows": int(mk.sum())}
                for nm in ("hybrid_s0", "tonly_s0", "lonly_s0", "gru24_s0"):
                    rec[f"rmse_{nm}"] = float(np.sqrt(np.mean((P[(nm, h)][mk] - y) ** 2)))
                ab.append(rec)
        md(pd.DataFrame(ab), "H1_9_ablations_seed0_rmse")

    # ---- H1_10 training diagnostics and stability
    diag = []
    for d in sorted(RUNS.glob("fold*")):
        if (d / "config.json").exists():
            c = json.load(open(d / "config.json"))
            diag.append({"run": d.name, "fold": c["fold"], "kind": c["kind"], "seed": c["seed"], "setting": c["setting"]["name"], "n_params": c["n_params"], "epochs_run": c["epochs_run"], "best_epoch": c["best_epoch"],
                         "best_val_scaled_loss": c["best_val_scaled_loss"], "train_seconds": c["train_seconds"]})
    DG = pd.DataFrame(diag)
    md(DG, "H1_10_training_diagnostics")
    shutil_copy = ["stability_summary.csv", "stability_per_run.csv"]
    for fn in shutil_copy:
        if (OUT / fn).exists():
            pd.read_csv(OUT / fn).to_csv(TAB / f"H1_11_{fn}", index=False)

    # ---- pooled out-of-fold predictions (stage levels) for the dashboards
    sel_rows = np.where((fold_of > 0))[0]
    cols = {"timestamp_utc": [str(t)[:16] for t in idx[sel_rows]], "fold": fold_of[sel_rows], "stage_ft": np.round(ctx.sv[sel_rows], 3)}
    for h in HZ:
        cols[f"target_stage_{h}_ft"] = np.round(ctx.sv[sel_rows] + np.nan_to_num(ctx.tg[h][sel_rows], nan=np.nan), 3)
        for nm in [f"hybrid_s{s}" for s in SEEDS]:
            cols[f"pred_{nm}_{h}_ft"] = np.round(ctx.sv[sel_rows] + P[(nm, h)][sel_rows], 3)
    pd.DataFrame(cols).to_csv(OUT / "oof_predictions.csv.gz", index=False)

    # ---- decision and figures
    primary = bool(all_ok)
    dec = {"setting_selected_on_validation": sel, "H1a_primary_claim_met": primary, "H1a_rule": "consistent improvement vs ridge H AND matched GRU 24 h at BOTH 1 h and 3 h in flood windows, no harm flag",
           "H1a_consistent_cells": f"{int(T3['CONSISTENT'].sum())} of {len(T3)}", "H1b_improves_lead30_cells_rise4_and_stage10_at_1h_3h": {f"{k[0]}|{k[1]}": v for k, v in h1b_ok.items()},
           "H1b_any": bool(any(h1b_ok.values())), "stop_rule": "if neither H1a nor H1b is met: no further hybrid tuning on stage-only inputs"}
    (OUT / "decision.json").write_text(json.dumps(dec, indent=2))
    fig, axes = plt.subplots(1, 4, figsize=(15, 3.6), constrained_layout=True)
    for ax, h in zip(axes, HZ):
        for j, (c, col) in enumerate((("gru24", C["gru"]), ("ridge_H", C["ridge"]), ("trend_v2", C["trend"]), ("xgb_H", C["xgb"]))):
            r = T2[(T2.subset == "flood_windows_10ft") & (T2.horizon == h) & (T2.comparator == c)].iloc[0]
            ax.errorbar(r.diff_ft, j, xerr=[[r.diff_ft - r.ci_lo], [r.ci_hi - r.diff_ft]], fmt="o", color=col, capsize=3)
            ax.plot([r.seed0_diff, r.seed1_diff, r.seed2_diff], [j] * 3, "|", color=C["ink"], ms=8)
        ax.axvline(0, color=C["ink2"], lw=1)
        ax.set_yticks(range(4)); ax.set_yticklabels(["vs GRU 24 h", "vs ridge H", "vs damped trend", "vs XGBoost H"]); ax.set_title(f"{h}: hybrid minus comparator, flood windows (ft)")
    fig.suptitle("Left of 0 = hybrid better; ticks = the three seeds. " + LABEL, fontsize=8, x=0.01, ha="left")
    fig.savefig(FIG / "fig1_paired_differences_flood_windows.png", dpi=140); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), constrained_layout=True)
    for ax, defn in zip(axes, ("experimental_rise_4ft_3h", "experimental_stage_10ft")):
        sub = T7[(T7.definition == defn) & T7.horizon.isin(["30m", "1h", "3h"])]
        xs = np.arange(len(sub))
        ax.bar(xs - 0.2, sub.hybrid_lead30_mean, 0.38, color=C["hybrid"], label="hybrid (seed mean; line = range)")
        ax.vlines(xs - 0.2, sub.hybrid_lead30_min, sub.hybrid_lead30_max, color=C["ink"])
        ax.bar(xs + 0.2, sub.best_baseline_lead30, 0.38, color=C["ref"], label="best single baseline")
        ax.set_xticks(xs); ax.set_xticklabels(sub.horizon); ax.set_title(f"{defn.replace('experimental_', '')}: events with an early alarm of at least 30 min (of {int(sub.events.iloc[0])})")
        ax.legend(fontsize=7)
    fig.suptitle(LABEL, fontsize=8, x=0.01, ha="left")
    fig.savefig(FIG / "fig2_events_with_30min_lead.png", dpi=140); plt.close(fig)
    print("H1 evaluation written. H1a primary claim met:", primary, "| H1b any:", dec["H1b_any"], "| setting", sel)


if __name__ == "__main__":
    main()
