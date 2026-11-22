"""Evaluate the Phase 1C deep regression baselines against persistence, damped trend, ridge H and XGBoost H (frozen Phase 1B predictions,
identical rows).  Implements docs/PHASE1C_DL_PROTOCOL.md section 5.  Validation and TEST (exploratory) only.
Outputs: reports/phase1c/tables, figures.   Usage: python scripts/eval_phase1c.py
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from flashflood import data, experiment, metrics, models  # noqa: E402

OUT = Path("reports/phase1c")
TAB, FIG = OUT / "tables", OUT / "figures"
for p in (TAB, FIG):
    p.mkdir(parents=True, exist_ok=True)
FROZEN = Path("reports/phase1b/frozen/predictions.npz")
HZ = experiment.HZ
CLASSICAL = ["persistence", "trend_v2", "ridge_H0", "xgb_H0"]
ARCHS = ["lstm", "gru", "transformer"]
B = 2000
C = dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#e6e5e1", s1="#2a78d6", s2="#eb6834", s3="#1baf7a", s4="#6250d6", s5="#eda100")
plt.rcParams.update({"figure.facecolor": C["surface"], "axes.facecolor": C["surface"], "savefig.facecolor": C["surface"], "axes.edgecolor": C["grid"], "axes.labelcolor": C["ink2"],
                     "text.color": C["ink"], "xtick.color": C["ink2"], "ytick.color": C["ink2"], "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 9, "axes.titleweight": "bold", "axes.titlelocation": "left"})


def md(df, name):
    df.to_csv(TAB / f"{name}.csv", index=False)
    (TAB / f"{name}.md").write_text(df.to_markdown(index=False, floatfmt=".6g"))


def main() -> None:
    ctx = experiment.build_context()
    n = ctx.n
    z = np.load(FROZEN)
    sel = json.load(open(OUT / "selection.json"))
    protos = {"chrono_val": ctx.lab == "val", "chrono_test": ctx.lab == "test"}
    cl = {(p, m, h): z[f"reg|{p}|{m}|{h}"].astype(float) for p in protos for m in CLASSICAL for h in HZ}
    # ---- deep predictions per architecture and seed (chosen hidden size only)
    seeds_of, dl = {}, {}
    for arch in ARCHS:
        hid = sel[arch]["chosen_hidden"]
        dirs = sorted((OUT / "runs").glob(f"{arch}_h{hid}_s*"))
        seeds_of[arch] = [int(d.name.split("_s")[-1]) for d in dirs]
        for d, sd_ in zip(dirs, seeds_of[arch]):
            zz = np.load(d / "predictions.npz")
            for p, (ik, pk) in {"chrono_val": ("val_idx", "pred_val"), "chrono_test": ("test_idx", "pred_test")}.items():
                for hi, h in enumerate(HZ):
                    a = np.full(n, np.nan); a[zz[ik]] = zz[pk][:, hi]
                    dl[(p, arch, sd_, h)] = a
    # ---- pre-registered best classical baseline: lowest mean VALIDATION event-window RMSE
    val_win = ctx.val_windows()
    sc = {}
    for m in ["trend_v2", "ridge_H0", "xgb_H0"]:
        r = []
        for h in HZ:
            mk = ctx.elig[h] & (ctx.lab == "val") & val_win & np.isfinite(cl[("chrono_val", m, h)])
            r.append(models.rmse(cl[("chrono_val", m, h)][mk], ctx.tg[h][mk]))
        sc[m] = float(np.mean(r))
    best_cl = min(sc, key=sc.get)
    (TAB.parent / "best_classical_baseline.json").write_text(json.dumps({"validation_mean_event_window_rmse": sc, "best_classical": best_cl, "rule": "lowest mean validation event-window RMSE among damped trend, ridge H, XGBoost H, computed before any deep-model test evaluation"}, indent=2))
    print("best classical baseline (validation rule):", best_cl, {k: round(v, 4) for k, v in sc.items()})

    subsets = {"all": np.ones(n, bool), "event_windows_stage10ft": ctx.win_mask(ctx.ev_all["experimental_stage_10ft"], "exceed"),
               "event_windows_rise4ft3h": ctx.win_mask(ctx.ev_all["experimental_rise_4ft_3h"], "rapid")}
    # ---- regression metrics with paired storm-cluster bootstrap
    rows, cmp_rows, seed_rows = [], [], []
    for pname, pm in protos.items():
        for sub, smask in subsets.items():
            for h in HZ:
                mk = ctx.elig[h] & pm & smask
                for m in CLASSICAL:
                    mk &= np.isfinite(cl[(pname, m, h)])
                for a in ARCHS:
                    for s_ in seeds_of[a]:
                        mk &= np.isfinite(dl[(pname, a, s_, h)])
                if mk.sum() < 30:
                    continue
                y = ctx.tg[h][mk]
                gb = metrics.GroupBoot(ctx.groups[mk], b=B, seed=0)
                err_p = -y
                mse_p = gb.mse(err_p)
                reps, pts = {}, {}
                for m in CLASSICAL:
                    e = cl[(pname, m, h)][mk] - y
                    reps[m] = gb.mse(e); pts[m] = {"rmse": models.rmse(cl[(pname, m, h)][mk], y), "mae": float(np.mean(np.abs(e))), "sd": np.nan}
                for a in ARCHS:
                    per_seed = []
                    r_acc = np.zeros(B)
                    for s_ in seeds_of[a]:
                        e = dl[(pname, a, s_, h)][mk] - y
                        per_seed.append({"rmse": models.rmse(dl[(pname, a, s_, h)][mk], y), "mae": float(np.mean(np.abs(e)))})
                        r_acc += gb.mse(e)
                        seed_rows.append({"protocol": pname, "subset": sub, "horizon": h, "model": a, "seed": s_, "n": int(mk.sum()), **per_seed[-1]})
                    reps[a] = r_acc / len(seeds_of[a])
                    mse_seedmean = np.mean([p_["rmse"] ** 2 for p_ in per_seed])
                    pts[a] = {"rmse": float(np.sqrt(mse_seedmean)), "mae": float(np.mean([p_["mae"] for p_ in per_seed])), "sd": float(np.std([p_["rmse"] for p_ in per_seed], ddof=1)) if len(per_seed) > 1 else np.nan}
                mse_p_pt = float(np.mean(err_p ** 2))
                for m, rep in reps.items():
                    lo, hi = gb.ci(np.sqrt(rep))
                    slo, shi = gb.ci(1 - rep / mse_p)
                    rows.append({"protocol": pname, "subset": sub, "horizon": h, "model": m, "n_rows": int(mk.sum()), "n_groups": int(len(gb.ug)), "rmse_ft": pts[m]["rmse"],
                                 "rmse_sd_across_seeds": pts[m]["sd"], "rmse_ci_lo": lo, "rmse_ci_hi": hi, "mae_ft": pts[m]["mae"],
                                 "skill_vs_persistence": 1 - pts[m]["rmse"] ** 2 / mse_p_pt, "skill_ci_lo": slo, "skill_ci_hi": shi})
                for a in ARCHS:
                    d = np.sqrt(reps[a]) - np.sqrt(reps[best_cl])
                    lo, hi = gb.ci(d)
                    d2 = np.sqrt(reps[a]) - np.sqrt(reps["persistence"]); dt = np.sqrt(reps[a]) - np.sqrt(reps["trend_v2"])
                    cmp_rows.append({"protocol": pname, "subset": sub, "horizon": h, "model": a, "best_classical": best_cl,
                                     "rmse_diff_vs_best_classical_ft": pts[a]["rmse"] - pts[best_cl]["rmse"], "ci_lo": lo, "ci_hi": hi, "interval_excludes_zero": bool(lo > 0 or hi < 0),
                                     "rmse_diff_vs_damped_trend_ft": pts[a]["rmse"] - pts["trend_v2"]["rmse"], "trend_ci_lo": gb.ci(dt)[0], "trend_ci_hi": gb.ci(dt)[1],
                                     "rmse_diff_vs_persistence_ft": pts[a]["rmse"] - pts["persistence"]["rmse"], "persist_ci_lo": gb.ci(d2)[0], "persist_ci_hi": gb.ci(d2)[1]})
    md(pd.DataFrame(rows), "C1_regression_metrics"); md(pd.DataFrame(cmp_rows), "C2_comparison_vs_best_classical"); md(pd.DataFrame(seed_rows), "C1b_per_seed_regression")

    # ---- fixed alarm rule applied to the regression forecasts (no probability head); per seed
    years = {"chrono_test": (ctx.s.index[-1] - ctx.ts).days / 365.25, "chrono_val": (ctx.ts - ctx.vs).days / 365.25}
    drows = []
    for pname, pm in protos.items():
        for defn in ctx.ev_all:
            evp = ctx.events_in(defn, pm)
            for h, k in data.HORIZONS.items():
                members = [(m, 0, cl[(pname, m, h)]) for m in CLASSICAL] + [(a, s_, dl[(pname, a, s_, h)]) for a in ARCHS for s_ in seeds_of[a]]
                for m, s_, a in members:
                    raw = experiment.fixed_rule_raw(ctx, np.where(np.isfinite(a), a, np.nan), k, ctx.kind_of[defn], ctx.thr_of[defn]) & np.isfinite(a)
                    summ, _ = experiment.detect(ctx, raw, evp, k, ctx.elig[h] & pm, years[pname])
                    if summ:
                        drows.append({"protocol": pname, "definition": defn, "horizon": h, "model": m, "seed": s_ if m in ARCHS else "", **summ})
    dd = pd.DataFrame(drows)
    md(dd, "C3_fixed_rule_detection_per_seed")
    agg = dd.groupby(["protocol", "definition", "horizon", "model"]).agg(n_events=("n_events", "first"), storm_clusters=("storm_clusters", "first"), hits_mean=("early_hits", "mean"),
                                                                         hits_min=("early_hits", "min"), hits_max=("early_hits", "max"), late_mean=("late", "mean"),
                                                                         false_alarm_episodes_mean=("false_alarm_episodes", "mean"), alarm_episodes_mean=("alarm_episodes", "mean"),
                                                                         median_lead_h_mean=("median_lead_h", "mean"), n_seeds=("early_hits", "size")).reset_index()
    md(agg, "C3b_fixed_rule_detection_seed_summary")

    # ---- per-event view (test): window RMSE and peak capture, seed-mean for deep models
    pe_rows = []
    pm = protos["chrono_test"]
    kinds = {d: ctx.kind_of[d] for d in ctx.ev_all}
    for defn in ["official_action_25ft", "experimental_stage_10ft", "experimental_rise_4ft_3h"]:
        evp = ctx.events_in(defn, pm)
        for i in range(len(evp)):
            wm = ctx.win_mask(evp.iloc[[i]], kinds[defn])
            e = evp.iloc[i]
            for h, k in data.HORIZONS.items():
                base = wm & ctx.elig[h] & pm
                pi = int(e.peak_i) - k
                for m in CLASSICAL + ARCHS:
                    if m in ARCHS:
                        ar = [dl[("chrono_test", m, s_, h)] for s_ in seeds_of[m]]
                    else:
                        ar = [cl[("chrono_test", m, h)]]
                    mk = base & np.all([np.isfinite(a) for a in ar], axis=0)
                    if mk.sum() == 0:
                        continue
                    wr = float(np.sqrt(np.mean([np.mean((a[mk] - ctx.tg[h][mk]) ** 2) for a in ar])))
                    pk = [ctx.sv[pi] + a[pi] for a in ar if pi >= 0 and np.isfinite(a[pi])]
                    pe_rows.append({"definition": defn, "event_start": str(ctx.s.index[int(e.i0)])[:16], "peak_ft": float(e.peak_ft), "provisional_data": bool(ctx.prov[int(e.i0):int(e.i1) + 1].any()),
                                    "horizon": h, "model": m, "window_rmse_ft": wr, "peak_forecast_ft_seed_mean": float(np.mean(pk)) if pk else np.nan,
                                    "peak_ratio": float(np.mean(pk) / e.peak_ft) if pk else np.nan, "peak_ratio_min_seed": float(np.min(pk) / e.peak_ft) if pk else np.nan,
                                    "peak_ratio_max_seed": float(np.max(pk) / e.peak_ft) if pk else np.nan})
    md(pd.DataFrame(pe_rows), "C4_per_event_test")

    # ---- training diagnostics
    dg = []
    for d in sorted((OUT / "runs").glob("*_s*")):
        if (d / "config.json").exists() and json.load(open(d / "config.json"))["arch"] in sel:
            c = json.load(open(d / "config.json"))
            dg.append({"run": d.name, "arch": c["arch"], "hidden": c["hidden"], "seed": c["seed"], "epochs_run": c["epochs_run"], "best_epoch": c["best_epoch"],
                       "best_val_scaled_loss": c["best_val_scaled_loss"], "train_seconds": c["train_seconds"], "chosen_for_primary": c["hidden"] == sel[c["arch"]]["chosen_hidden"]})
    md(pd.DataFrame(dg), "C5_training_diagnostics")
    md(pd.DataFrame([{"arch": a, "hidden_32_val_event_window_rmse": v["validation_event_window_rmse_seed0"].get("32"), "hidden_64_val_event_window_rmse": v["validation_event_window_rmse_seed0"].get("64"),
                      "chosen_hidden": v["chosen_hidden"]} for a, v in sel.items()]), "C0_hidden_size_selection_validation")

    # ---- figures
    R = pd.DataFrame(rows)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    cols = {"persistence": C["ink2"], "trend_v2": C["s5"], "ridge_H0": C["s3"], "xgb_H0": C["s1"], "lstm": C["s2"], "gru": C["s4"], "transformer": "#d55181"}
    for ax, sub in zip(axes, ["all", "event_windows_stage10ft"]):
        d = R[(R.protocol == "chrono_test") & (R["subset"] == sub)]
        for j, m in enumerate(cols):
            x = np.arange(len(HZ)) + (j - 3) * 0.12
            dm = d[d.model == m].set_index("horizon").reindex(HZ)
            ax.bar(x, dm.rmse_ft, width=0.11, color=cols[m], label=m)
            if m in ARCHS:
                for s_ in seeds_of[m]:
                    sr = [r for r in seed_rows if r["protocol"] == "chrono_test" and r["subset"] == sub and r["model"] == m and r["seed"] == s_]
                    ax.scatter([x[i] for i in range(len(HZ))], [next(r["rmse"] for r in sr if r["horizon"] == h) for h in HZ], s=6, color=C["ink"], zorder=3)
        ax.set_xticks(range(len(HZ))); ax.set_xticklabels(HZ); ax.set_ylabel("RMSE (ft)"); ax.grid(axis="x", visible=False)
        ax.set_yscale("log" if sub == "all" else "linear")
    axes[0].set_title("TEST (exploratory), all rows (log scale)"); axes[1].set_title("TEST, flood windows (>=10 ft); dots = seeds")
    axes[0].legend(frameon=False, fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(FIG / "fig1_test_rmse_by_model.png", dpi=150); plt.close(fig)
    ev = ctx.events_in("official_action_25ft", pm)
    if len(ev):
        starts = [ev.iloc[0], ev.iloc[-1]]
        fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
        for ax, e in zip(axes, starts):
            a_, b_ = ctx.s.index[int(e.i0)] - pd.Timedelta("18h"), ctx.s.index[int(e.i1)] + pd.Timedelta("18h")
            ax.plot(ctx.s.loc[a_:b_].index, ctx.s.loc[a_:b_].values, color=C["ink"], lw=1.5, label="observed")
            k = data.HORIZONS["3h"]
            for m, col in (("trend_v2", C["s5"]), ("ridge_H0", C["s3"])):
                f = pd.Series(ctx.sv + cl[("chrono_test", m, "3h")], index=ctx.s.index).shift(k)
                ax.plot(f.loc[a_:b_].index, f.loc[a_:b_].values, color=col, lw=1, label=f"{m} 3 h ahead")
            for a, col in [(x, cols[x]) for x in ARCHS]:
                f = pd.Series(ctx.sv + dl[("chrono_test", a, seeds_of[a][0], "3h")], index=ctx.s.index).shift(k)
                ax.plot(f.loc[a_:b_].index, f.loc[a_:b_].values, color=col, lw=1, label=f"{a} (seed {seeds_of[a][0]}) 3 h ahead")
            ax.set_title(f"{ctx.s.index[int(e.i0)]:%Y-%m-%d}  peak {e.peak_ft:.1f} ft", fontsize=9); ax.set_ylabel("stage (ft)"); ax.tick_params(axis="x", labelrotation=30, labelsize=7)
        axes[0].legend(frameon=False, fontsize=6.5)
        fig.tight_layout(); fig.savefig(FIG / "fig2_test_official_events_3h.png", dpi=150); plt.close(fig)
    print("evaluation written")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--archs", default="lstm,gru,transformer")
    ap.add_argument("--out", default="reports/phase1c", help="where tables/figures are written (runs are always read from reports/phase1c)")
    ap.add_argument("--debug", action="store_true", help="code-path check only: prints no test metrics")
    a = ap.parse_args()
    ARCHS = a.archs.split(",")
    TAB, FIG = Path(a.out) / "tables", Path(a.out) / "figures"
    for _p in (TAB, FIG):
        _p.mkdir(parents=True, exist_ok=True)
    main()
