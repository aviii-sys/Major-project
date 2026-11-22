"""Onset-timing comparison of the saved GRU 24 h and 72 h out-of-fold predictions (E18; docs/PHASE1E_ONSET_PROTOCOL.md).
Post-hoc diagnostic on SAVED predictions: nothing is retrained and no earlier artifact is modified.
Usage (project root): PYTHONPATH=src python scripts/run_onset_timing.py        Output: reports/phase1e_onset/{tables,figures}
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from flashflood import data, experiment, onset  # noqa: E402

OUT = Path("reports/phase1e_onset")
TAB, FIG = OUT / "tables", OUT / "figures"
for p in (TAB, FIG):
    p.mkdir(parents=True, exist_ok=True)
HZ = experiment.HZ
KSTEP = data.HORIZONS
SEEDS = (0, 1, 2)
REFS = {"persistence": "persistence", "trend_v2": "damped trend", "ridge_H": "ridge H"}
LEVELS = ("f10", "f50", "f90")
LABEL = "Post-hoc diagnostic on saved out-of-fold predictions; retrospective blocked CV, exploratory"
C = dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#e6e5e1", w24="#6250d6", w72="#eb6834", ref="#8d8c88")
plt.rcParams.update({"figure.facecolor": C["surface"], "axes.facecolor": C["surface"], "savefig.facecolor": C["surface"], "axes.edgecolor": C["grid"], "axes.labelcolor": C["ink2"],
                     "text.color": C["ink"], "xtick.color": C["ink2"], "ytick.color": C["ink2"], "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 8, "axes.titleweight": "bold", "axes.titlelocation": "left"})


def md(df, name):
    df.to_csv(TAB / f"{name}.csv", index=False)
    (TAB / f"{name}.md").write_text(df.to_markdown(index=False, floatfmt=".4g"))


def load_arrays(ctx):
    """Saved predictions -> full-grid arrays aligned at ISSUE time (forecast of the stage k steps later)."""
    n, idx = ctx.n, ctx.s.index
    o5 = pd.read_csv("reports/phase1e/oof_predictions.csv.gz")
    o4 = pd.read_csv("reports/phase1d/oof_predictions.csv.gz")
    out = {}
    fold_of = np.zeros(n, int)
    flood10 = np.zeros(n, bool)
    rise4 = np.zeros(n, bool)
    for src, name in ((o5, "phase1e"), (o4, "phase1d")):
        ts = pd.DatetimeIndex(pd.to_datetime(src.timestamp_utc)).tz_localize("UTC")
        pos = idx.get_indexer(ts)
        assert (pos >= 0).all(), f"{name}: timestamps not on the project grid"
        assert len(np.unique(pos)) == len(pos), f"{name}: duplicate timestamps"
        sv_chk = src.stage_ft.values
        fin = np.isfinite(sv_chk) & np.isfinite(ctx.sv[pos])
        assert np.allclose(sv_chk[fin], ctx.sv[pos][fin], atol=1e-6), f"{name}: stage in the saved predictions differs from the project series"
        fold_of[pos] = src.fold.values
        src_pos = pos
        if name == "phase1e":
            for w in (24, 72):
                for s in SEEDS:
                    for h in HZ:
                        a = np.full(n, np.nan); a[src_pos] = src[f"pred_gru{w}h_s{s}_{h}_ft"].values
                        out[(f"gru{w}_s{s}", h)] = a
        else:
            flood10[src_pos] = src.in_flood_window_10ft.values.astype(bool)
            rise4[src_pos] = src.in_flood_window_rise4.values.astype(bool)
            for m in REFS:
                for h in HZ:
                    a = np.full(n, np.nan); a[src_pos] = src[f"pred_{m}_{h}_ft"].values
                    out[(m, h)] = a
    return out, fold_of, flood10, rise4


def seed_stats(df, col, group_cols, win):
    """Seed mean / min / max / number of seeds with a finite value for window `win` (24 or 72)."""
    g = df[df.variant.str.startswith(f"gru{win}_")].groupby(group_cols)[col]
    return pd.DataFrame({f"{col}_mean": g.mean(), f"{col}_min": g.min(), f"{col}_max": g.max(), f"{col}_n": g.count()}).reset_index()


def main() -> None:
    ctx = experiment.build_context()
    sv, idx, n = ctx.sv, ctx.s.index, ctx.n
    FISS, fold_of, flood10, rise4 = load_arrays(ctx)
    ev_all = ctx.ev_all["experimental_stage_10ft"]
    ev = ev_all[fold_of[ev_all.i0.values] > 0].reset_index(drop=True)
    assert len(ev) == 18, len(ev)
    variants = [f"gru{w}_s{s}" for w in (24, 72) for s in SEEDS] + list(REFS)

    # ---- per event / horizon / variant timing table
    meta, rows = [], []
    for e in ev.itertuples():
        ref = onset.event_reference(sv, e.i0, e.peak_i)
        prov = bool(ctx.prov[e.i0:e.i1 + 1].any())
        meta.append({"event_start": str(idx[e.i0])[:16], "fold": int(fold_of[e.i0]), "storm_cluster": int(ctx.groups[e.i0]), "peak_ft": ref["peak_ft"], "official_ge_25ft": bool(ref["peak_ft"] >= 25),
                     "provisional_data": prov, "rise_onset": str(idx[ref["onset_i"]])[:16], "peak_time": str(idx[ref["peak_i"]])[:16], "baseline_ft": ref["baseline_ft"], "amplitude_ft": ref["amplitude_ft"],
                     "onset_to_peak_h": (ref["peak_i"] - ref["onset_i"]) * 0.25})
        for h in HZ:
            k = KSTEP[h]
            for v in variants:
                r = onset.event_timing_row(sv, FISS[(v, h)], ref, k)
                flags = onset.reliability_flags(ref, {"forecast_coverage": r["forecast_coverage"], "obs_missing_share": r["obs_missing_share"]}, prov)
                rows.append({"event_start": meta[-1]["event_start"], "peak_ft": ref["peak_ft"], "horizon": h, "variant": v, **{k_: v_ for k_, v_ in r.items() if not k_.endswith("_i")}, **flags})
    O0 = pd.DataFrame(meta)
    O1 = pd.DataFrame(rows)
    O1["window"] = O1.variant.map(lambda v: int(v[3:5]) if v.startswith("gru") else 0)
    md(O0, "O0_event_reference")
    md(O1.drop(columns=["window"]), "O1_timing_per_event_horizon_variant")

    # ---- seed summaries and paired 72 h - 24 h comparison at the pre-specified levels
    key = ["event_start", "peak_ft", "horizon"]
    rel_cols = ["R1_low_forecast_coverage", "R2_obs_missing_gt5pct", "R3_ambiguous_onset", "R4_low_amplitude", "R5_provisional"]
    comp_rows = []
    for lv in LEVELS:
        for col in (f"lead_{lv}_h", f"lag_{lv}_h"):
            s24, s72 = seed_stats(O1, col, key, 24), seed_stats(O1, col, key, 72)
            m = s24.merge(s72, on=key, suffixes=("_24", "_72"))
            m["diff_72_minus_24"] = m[f"{col}_mean_72"] - m[f"{col}_mean_24"]
            m["seed_range_24"] = m[f"{col}_max_24"] - m[f"{col}_min_24"]
            m["beyond_24h_seed_range"] = m.diff_72_minus_24.abs() > m.seed_range_24
            m["metric"] = col
            comp_rows.append(m.rename(columns={f"{col}_mean_24": "mean_24", f"{col}_mean_72": "mean_72", f"{col}_n_24": "n_seeds_24", f"{col}_n_72": "n_seeds_72",
                                               f"{col}_min_24": "min_24", f"{col}_max_24": "max_24", f"{col}_min_72": "min_72", f"{col}_max_72": "max_72"}))
    O2 = pd.concat(comp_rows, ignore_index=True)
    flags_ev = O1[O1.variant == "gru24_s0"].groupby(key)[rel_cols].any().reset_index()
    O2 = O2.merge(flags_ev, on=key)
    md(O2, "O2_paired_level_timing_72_minus_24")

    summ = []
    for (metric, h), g in O2.groupby(["metric", "horizon"]):
        if not metric.startswith("lead"):
            continue
        for scope, gg in (("all 18 events", g), ("excluding events with any reliability flag R1-R4", g[~g[["R1_low_forecast_coverage", "R2_obs_missing_gt5pct", "R3_ambiguous_onset", "R4_low_amplitude"]].any(axis=1)])):
            ok = gg.dropna(subset=["diff_72_minus_24"])
            ok = ok[(ok.n_seeds_24 == 3) & (ok.n_seeds_72 == 3)]
            summ.append({"metric": metric, "horizon": h, "scope": scope, "events_with_all_seeds_reaching_level": len(ok), "events_72h_earlier_lead": int((ok.diff_72_minus_24 > 0).sum()),
                         "events_72h_later_lead": int((ok.diff_72_minus_24 < 0).sum()), "events_equal": int((ok.diff_72_minus_24 == 0).sum()),
                         "median_diff_72_minus_24_h": float(ok.diff_72_minus_24.median()) if len(ok) else np.nan,
                         "median_24h_seed_range_h": float(ok.seed_range_24.median()) if len(ok) else np.nan,
                         "events_beyond_24h_seed_range": int(ok.beyond_24h_seed_range.sum()), "median_lead_24h_h": float(ok.mean_24.median()) if len(ok) else np.nan,
                         "median_lead_72h_h": float(ok.mean_72.median()) if len(ok) else np.nan})
    O3 = pd.DataFrame(summ)
    md(O3, "O3_summary_level_leads")

    # reference variants: lead per level (event medians)
    refs = O1[O1.variant.isin(REFS)].groupby(["horizon", "variant"])[[f"lead_{lv}_h" for lv in LEVELS] + ["catch_up_h"]].median().reset_index()
    g24 = O1[O1.variant.str.startswith("gru24")].groupby("horizon")[[f"lead_{lv}_h" for lv in LEVELS] + ["catch_up_h"]].median().reset_index().assign(variant="GRU 24 h (all seeds)")
    g72 = O1[O1.variant.str.startswith("gru72")].groupby("horizon")[[f"lead_{lv}_h" for lv in LEVELS] + ["catch_up_h"]].median().reset_index().assign(variant="GRU 72 h (all seeds)")
    md(pd.concat([g24, g72, refs], ignore_index=True), "O3b_median_lead_by_variant")

    # ---- issue time of the first forecast that shows each level, relative to the rise onset (added after the first run, see protocol deviation 1)
    iss = []
    for h in HZ:
        for lv in LEVELS:
            col = f"issue_vs_onset_{lv}_h"
            for label, sel in (("GRU 24 h", O1.variant.str.startswith("gru24")), ("GRU 72 h", O1.variant.str.startswith("gru72")), ("damped trend", O1.variant == "trend_v2"),
                               ("ridge H", O1.variant == "ridge_H"), ("persistence", O1.variant == "persistence")):
                g = O1[sel & (O1.horizon == h)]
                per_ev = g.groupby("event_start")[col].agg(["median", "min", "count"])
                n_before_any = int((g.groupby("event_start")[col].min() < 0).sum())
                n_before_all = int((g.groupby("event_start")[col].max() < 0).sum()) if label.startswith("GRU") else n_before_any
                iss.append({"horizon": h, "level": f"{int(lv[1:])}% of the rise", "variant": label, "events_with_level_reached": int((per_ev["count"] > 0).sum()),
                            "median_issue_vs_onset_h": float(per_ev["median"].median()), "events_first_forecast_issued_before_onset_any_seed": n_before_any,
                            "events_first_forecast_issued_before_onset_all_seeds": n_before_all})
    O3c = pd.DataFrame(iss)
    md(O3c, "O3c_issue_time_of_first_forecast_vs_onset")

    # ---- official events: the five >= 25 ft rows, seed means
    offs = O0[O0.official_ge_25ft].event_start.tolist()
    orows = []
    for es in offs:
        for h in ("1h", "3h"):
            for label, sel in (("GRU 24 h", O1.variant.str.startswith("gru24")), ("GRU 72 h", O1.variant.str.startswith("gru72")), ("damped trend", O1.variant == "trend_v2"), ("ridge H", O1.variant == "ridge_H")):
                g = O1[sel & (O1.horizon == h) & (O1.event_start == es)]
                orows.append({"event_start": es, "peak_ft": float(g.peak_ft.iloc[0]), "horizon": h, "variant": label, "lead_10pct_h": g.lead_f10_h.mean(), "lead_50pct_h": g.lead_f50_h.mean(), "lead_90pct_h": g.lead_f90_h.mean(),
                              "first_issue_50pct_vs_onset_h": g.issue_vs_onset_f50_h.mean(), "max_predicted_change_before_onset_ft": g.max_predicted_change_ft.mean(),
                              "realised_max_change_ft": g.realised_max_change_ft.iloc[0], "fc_peak_time_lag_h": g.fc_peak_time_lag_h.mean(), "fc_max_ratio": g.fc_max_ratio.mean(),
                              "onset_ambiguous_R3": bool(g.R3_ambiguous_onset.iloc[0])})
    md(pd.DataFrame(orows), "O8_official_events_summary")

    # ---- pre-onset anticipation
    ant = O1.groupby(["event_start", "peak_ft", "horizon"]).apply(lambda g: pd.Series({
        **{f"gru{w}_seeds_flagged": int(g[g.variant.str.startswith(f"gru{w}")].anticipation_flag.sum()) for w in (24, 72)},
        **{f"gru{w}_max_pred_change_ft_mean": g[g.variant.str.startswith(f"gru{w}")].max_predicted_change_ft.mean() for w in (24, 72)},
        **{f"gru{w}_max_pred_change_ft_min": g[g.variant.str.startswith(f"gru{w}")].max_predicted_change_ft.min() for w in (24, 72)},
        **{f"gru{w}_max_pred_change_ft_max": g[g.variant.str.startswith(f"gru{w}")].max_predicted_change_ft.max() for w in (24, 72)},
        "trend_flag": bool(g[g.variant == "trend_v2"].anticipation_flag.iloc[0]), "ridge_flag": bool(g[g.variant == "ridge_H"].anticipation_flag.iloc[0]),
        "persistence_flag": bool(g[g.variant == "persistence"].anticipation_flag.iloc[0]),
        "realised_max_change_ft": g.realised_max_change_ft.iloc[0], "n_qualifying_issue_times": int(g.n_qualifying_issue_times.iloc[0]),
        "R3_ambiguous_onset": bool(g.R3_ambiguous_onset.iloc[0]), "any_R1_R2_R4": bool(g[["R1_low_forecast_coverage", "R2_obs_missing_gt5pct", "R4_low_amplitude"]].any().any())})).reset_index()
    md(ant, "O4_pre_onset_anticipation_per_event")
    asumm = []
    for h in HZ:
        a = ant[ant.horizon == h]
        for scope, aa in (("all 18 events", a), ("excluding R3 ambiguous-onset events", a[~a.R3_ambiguous_onset])):
            for w in (24, 72):
                col = f"gru{w}_seeds_flagged"
                asumm.append({"horizon": h, "scope": scope, "window_h": w, "events": len(aa), "events_flagged_by_all_3_seeds": int((aa[col] == 3).sum()), "events_flagged_by_>=1_seed": int((aa[col] >= 1).sum()),
                              "flagged_event_seed_pairs": int(aa[col].sum()), "possible_pairs": 3 * len(aa), "median_max_pred_change_ft": float(aa[f"gru{w}_max_pred_change_ft_mean"].median())})
            asumm.append({"horizon": h, "scope": scope, "window_h": "damped trend", "events": len(aa), "events_flagged_by_all_3_seeds": int(aa.trend_flag.sum()), "events_flagged_by_>=1_seed": int(aa.trend_flag.sum()),
                          "flagged_event_seed_pairs": int(aa.trend_flag.sum()), "possible_pairs": len(aa), "median_max_pred_change_ft": np.nan})
            asumm.append({"horizon": h, "scope": scope, "window_h": "ridge H", "events": len(aa), "events_flagged_by_all_3_seeds": int(aa.ridge_flag.sum()), "events_flagged_by_>=1_seed": int(aa.ridge_flag.sum()),
                          "flagged_event_seed_pairs": int(aa.ridge_flag.sum()), "possible_pairs": len(aa), "median_max_pred_change_ft": np.nan})
    O5 = pd.DataFrame(asumm)
    md(O5, "O5_anticipation_summary")
    sens = O1[O1.variant.str.startswith("gru")].groupby(["horizon", "window"])[["flag_at_0.25ft", "flag_at_0.5ft", "flag_at_1ft"]].sum().reset_index()
    md(sens, "O5b_anticipation_threshold_sensitivity_event_seed_pairs")
    bg = []
    excl = flood10 | rise4
    for h in HZ:
        for v in variants:
            r = onset.background_rate(sv, FISS[(v, h)], excl)
            bg.append({"horizon": h, "variant": v, **r})
    md(pd.DataFrame(bg), "O5c_background_rate_outside_flood_windows")

    # ---- peak timing summary
    pk = O1.groupby(["horizon", "window"]).agg(median_fc_max_ratio=("fc_max_ratio", "median"), median_peak_time_lag_h=("fc_peak_time_lag_h", "median")).reset_index()
    md(pk, "O6_peak_timing_median")

    # ---- fixed-rule alarm leads on the existing definitions + reproduction check against E6
    spec = pd.read_csv("reports/phase1e/fold_specification.csv", parse_dates=["test_start"])
    years = (idx[-1] - spec.test_start.min()).days / 365.25
    oof = fold_of > 0
    elig = {h: ctx.elig[h] & oof for h in HZ}
    e6 = pd.read_csv("reports/phase1e/tables/E6_fixed_rule_detection_per_seed.csv")
    det_rows, checks = [], []
    for defn in ("experimental_stage_10ft", "experimental_rise_4ft_3h"):
        evs_all = ctx.ev_all[defn]
        evs = evs_all[fold_of[evs_all.i0.values] > 0].reset_index(drop=True)
        for h in HZ:
            k = KSTEP[h]
            for w in (24, 72):
                for s in SEEDS:
                    a = FISS[(f"gru{w}_s{s}", h)] - sv
                    a = np.where(elig[h], a, np.nan)
                    raw = experiment.fixed_rule_raw(ctx, a, k, ctx.kind_of[defn], ctx.thr_of[defn]) & np.isfinite(a)
                    summ_, pe = experiment.detect(ctx, raw, evs, k, elig[h], years)
                    ref_hits = e6[(e6.definition == defn) & (e6.horizon == h) & (e6.window_h == w) & (e6.seed == s)]
                    if summ_ is not None:
                        checks.append({"definition": defn, "horizon": h, "window_h": w, "seed": s, "early_hits_here": summ_["early_hits"], "early_hits_E6": int(ref_hits.early_hits.iloc[0]) if len(ref_hits) else None,
                                       "late_here": summ_["late"], "late_E6": int(ref_hits.late.iloc[0]) if len(ref_hits) else None})
                    for r in pe.itertuples():
                        det_rows.append({"definition": defn, "horizon": h, "window_h": w, "seed": s, "event_start": str(idx[int(r.i0)])[:16], "peak_ft": r.peak_ft, "status": r.status, "lead_h": r.lead_h})
    chk = pd.DataFrame(checks)
    chk["match"] = (chk.early_hits_here == chk.early_hits_E6) & (chk.late_here == chk.late_E6)
    md(chk, "O7b_reproduction_check_vs_E6")
    if not chk.match.all():
        raise SystemExit("Reproduction of Phase 1E detection counts failed: " + chk[~chk.match].to_string())
    O7 = pd.DataFrame(det_rows)
    md(O7, "O7_fixed_rule_lead_per_event")
    d7 = O7[O7.definition == "experimental_stage_10ft"].pivot_table(index=["horizon", "event_start", "peak_ft"], columns=["window_h"], values="lead_h", aggfunc=["median", "min", "max"]).reset_index()
    d7.columns = ["_".join(str(x) for x in c if str(x) != "").strip("_") for c in d7.columns]
    md(d7, "O7c_stage10_lead_per_event_seed_median_min_max")
    d7d = []
    for (defn, h, w), g in O7.groupby(["definition", "horizon", "window_h"]):
        early = g[g.status == "early"]
        d7d.append({"definition": defn, "horizon": h, "window_h": w, "events": g.event_start.nunique(), "early_hits_seed_mean": len(early) / 3, "late_seed_mean": int((g.status == "late").sum()) / 3,
                    "misses_seed_mean": int((g.status == "miss").sum()) / 3, "not_evaluable_seed_mean": int((g.status == "not_evaluable").sum()) / 3,
                    "median_lead_of_early_hits_h": float(early.lead_h.median()) if len(early) else np.nan, "max_lead_of_early_hits_h": float(early.lead_h.max()) if len(early) else np.nan})
    md(pd.DataFrame(d7d), "O7d_fixed_rule_lead_summary")

    # ---- figures
    make_figures(ctx, FISS, ev, O0, O1, O2, ant, variants)

    (OUT / "run_summary.json").write_text(json.dumps({"events": len(ev), "reproduction_check_rows": int(len(chk)), "reproduction_all_match": bool(chk.match.all()),
                                                      "note": LABEL}, indent=2))
    print("onset-timing analysis written to", OUT, "| reproduction of E6 hit counts:", "OK" if chk.match.all() else "FAILED")


def make_figures(ctx, FISS, ev, O0, O1, O2, ant, variants):
    sv, idx = ctx.sv, ctx.s.index
    # Fig O1: per event, 3 h forecasts at target time
    for h, tag in (("3h", "3h"), ("1h", "1h")):
        k = KSTEP[h]
        fig, axes = plt.subplots(6, 3, figsize=(14, 17), constrained_layout=True)
        for ax, e, m in zip(axes.ravel(), ev.itertuples(), O0.itertuples()):
            ref = onset.event_reference(sv, e.i0, e.peak_i)
            lo, hi = max(0, ref["onset_i"] - 24), min(ctx.n - 1, ref["peak_i"] + 24)
            j = np.arange(lo, hi + 1)
            t = (idx[j] - idx[ref["onset_i"]]) / pd.Timedelta("1h")
            ax.plot(t, sv[j], color=C["ink"], lw=1.6, label="observed")
            for w, col in ((24, C["w24"]), (72, C["w72"])):
                fc = np.vstack([onset.target_aligned(FISS[(f"gru{w}_s{s}", h)], k)[j] for s in SEEDS])
                ax.fill_between(t, np.nanmin(fc, 0), np.nanmax(fc, 0), color=col, alpha=0.2, lw=0)
                ax.plot(t, np.nanmean(fc, 0), color=col, lw=1.1, label=f"GRU {w} h (3-seed mean, band = seed range)")
            pr = onset.target_aligned(FISS[("persistence", h)], k)[j]
            ax.plot(t, pr, color=C["ref"], lw=0.9, ls=":", label="persistence")
            for f in onset.FRACS:
                ax.axhline(ref["baseline_ft"] + f * ref["amplitude_ft"], color=C["grid"], lw=0.7, zorder=0)
            ax.axvline(0, color=C["ink2"], lw=0.8, ls="--")
            ax.set_title(f"{m.event_start[:10]}  peak {m.peak_ft:.1f} ft" + ("  (official)" if m.official_ge_25ft else "") + ("  [ambiguous onset]" if m.onset_to_peak_h > 24 else ""), fontsize=8)
            ax.set_xlabel("hours from rise onset (dashed)", fontsize=7)
            ax.set_ylabel("stage (ft)", fontsize=7)
        axes.ravel()[0].legend(fontsize=6, loc="upper left")
        fig.suptitle(f"{h} forecasts drawn at their TARGET time versus the observed stage; light lines = 10 / 50 / 90 % of the rise\n{LABEL}", fontsize=9, x=0.01, ha="left")
        fig.savefig(FIG / f"figO1_events_{tag}_forecast_vs_observed.png", dpi=130); plt.close(fig)

    # Fig O2: lead at the 10 % and 50 % levels per event, 24 h vs 72 h
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)
    order = O0.sort_values("peak_ft").event_start.tolist()
    for r_i, h in enumerate(("1h", "3h")):
        for c_i, lv in enumerate(("f10", "f50")):
            ax = axes[r_i, c_i]
            xl, xr = (-0.5, 2.0) if h == "1h" else (-1.0, 4.0)
            sub = O2[(O2.metric == f"lead_{lv}_h") & (O2.horizon == h)].set_index("event_start")
            pr = O1[(O1.variant == "persistence") & (O1.horizon == h)].set_index("event_start")[f"lead_{lv}_h"]
            tr = O1[(O1.variant == "trend_v2") & (O1.horizon == h)].set_index("event_start")[f"lead_{lv}_h"]
            for yi, es in enumerate(order):
                if es not in sub.index:
                    continue
                row = sub.loc[es]
                amb = bool(O0.set_index("event_start").loc[es, "onset_to_peak_h"] > 24)
                for w, col, dy in ((24, C["w24"], -0.12), (72, C["w72"], 0.12)):
                    mn, mx, mu = row[f"min_{w}"], row[f"max_{w}"], row[f"mean_{w}"]
                    if np.isfinite(mu):
                        ax.plot([max(mn, xl), min(mx, xr)], [yi + dy] * 2, color=col, lw=2, alpha=0.5)
                        if mu > xr:
                            ax.plot(xr, yi + dy, ">", color=col, ms=5, mfc="none" if amb else col); ax.text(xr, yi + dy + 0.3, f"{mu:.1f}", fontsize=5.5, ha="right", color=C["ink2"])
                        else:
                            ax.plot(mu, yi + dy, "o", color=col, ms=4.5, mfc=col if not amb else "none")
                if es in tr.index and np.isfinite(tr[es]):
                    ax.plot(min(tr[es], xr), yi, "|", color=C["ink2"], ms=8)
            ax.set_xlim(xl, xr)
            ax.axvline(0, color=C["ref"], lw=1, ls=":")
            ax.set_yticks(range(len(order))); ax.set_yticklabels([f"{es[:10]} ({O0.set_index('event_start').loc[es, 'peak_ft']:.0f} ft)" for es in order], fontsize=6.5)
            ax.set_xlabel(f"lead (h): observed arrival minus issue time of first forecast reaching the level (max {KSTEP[h] * 0.25:g} h)", fontsize=7)
            ax.set_title(f"{h} forecasts, {int(lv[1:])}% of the rise", fontsize=9)
    axes[0, 0].plot([], [], "o", color=C["w24"], label="GRU 24 h (seed mean; line = seed range)"); axes[0, 0].plot([], [], "o", color=C["w72"], label="GRU 72 h")
    axes[0, 0].plot([], [], "|", color=C["ink2"], label="damped trend"); axes[0, 0].plot([], [], "o", mfc="none", color=C["ink2"], label="hollow = ambiguous (slow/multi-stage) onset"); axes[0, 0].legend(fontsize=6.5, loc="lower right")
    fig.suptitle("Zero = the forecast only followed the river (persistence); positive = shown before the river reached the level. Values beyond the axis are drawn as triangles at the edge with their value.\n" + LABEL, fontsize=9, x=0.01, ha="left")
    fig.savefig(FIG / "figO2_level_arrival_lead_24h_vs_72h.png", dpi=140); plt.close(fig)

    # Fig O3: pre-onset anticipation (max predicted rise before the river has risen)
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.5), constrained_layout=True)
    for ax, h in zip(axes, ("1h", "3h")):
        a = ant[ant.horizon == h].set_index("event_start").loc[order]
        for yi, es in enumerate(order):
            row = a.loc[es]
            for w, col, dy in ((24, C["w24"], -0.12), (72, C["w72"], 0.12)):
                ax.plot([row[f"gru{w}_max_pred_change_ft_min"], row[f"gru{w}_max_pred_change_ft_max"]], [yi + dy] * 2, color=col, lw=2, alpha=0.5)
                ax.plot(row[f"gru{w}_max_pred_change_ft_mean"], yi + dy, "o", color=col, ms=4.5, mfc="none" if row.R3_ambiguous_onset else col)
            ax.plot(row.realised_max_change_ft, yi, "x", color=C["ink"], ms=5)
        ax.axvline(onset.ANTICIPATION_FT, color=C["ink2"], lw=0.9, ls="--")
        ax.set_yticks(range(len(order))); ax.set_yticklabels([f"{es[:10]} ({O0.set_index('event_start').loc[es, 'peak_ft']:.0f} ft)" for es in order], fontsize=6.5)
        ax.set_xlabel("largest predicted change (ft) at issue times before the river had risen", fontsize=7)
        ax.set_title(f"{h} forecasts", fontsize=9)
    axes[0].plot([], [], "o", color=C["w24"], label="GRU 24 h (mean, seed range)"); axes[0].plot([], [], "o", color=C["w72"], label="GRU 72 h"); axes[0].plot([], [], "x", color=C["ink"], label="rise that actually followed (largest over the same issue times)")
    axes[0].plot([], [], "--", color=C["ink2"], label="0.5 ft anticipation threshold"); axes[0].legend(fontsize=6.5, loc="lower right")
    fig.suptitle("Pre-onset anticipation: did any forecast issued BEFORE the river rose already predict a rise?\n" + LABEL, fontsize=9, x=0.01, ha="left")
    fig.savefig(FIG / "figO3_pre_onset_anticipation.png", dpi=140); plt.close(fig)

    # Fig O4: issue-time view for two official events: predicted change versus realised change
    pick = [m for m in O0.itertuples() if m.event_start in ("2025-07-05 03:45", "2015-05-23 23:15")]
    fig, axes = plt.subplots(len(pick), 2, figsize=(12, 3.6 * len(pick)), constrained_layout=True, squeeze=False)
    for r_i, m in enumerate(pick):
        e = ev[ev.i0 == idx.get_loc(pd.Timestamp(m.event_start, tz="UTC"))].iloc[0]
        ref = onset.event_reference(sv, int(e.i0), int(e.peak_i))
        for c_i, h in enumerate(("1h", "3h")):
            k = KSTEP[h]
            ax = axes[r_i, c_i]
            lo, hi = ref["onset_i"] - 24, min(ctx.n - 1 - k, ref["peak_i"])
            j = np.arange(lo, hi + 1)
            t = (idx[j] - idx[ref["onset_i"]]) / pd.Timedelta("1h")
            ax.plot(t, sv[j + k] - sv[j], color=C["ink"], lw=1.5, label=f"realised change over the next {h}")
            for w, col in ((24, C["w24"]), (72, C["w72"])):
                d = np.vstack([FISS[(f"gru{w}_s{s}", h)][j] - sv[j] for s in SEEDS])
                ax.fill_between(t, np.nanmin(d, 0), np.nanmax(d, 0), color=col, alpha=0.2, lw=0)
                ax.plot(t, np.nanmean(d, 0), color=col, lw=1.1, label=f"GRU {w} h predicted change (issue time)")
            ax.axvline(0, color=C["ink2"], lw=0.8, ls="--"); ax.axhline(0, color=C["grid"], lw=0.8)
            ax.set_title(f"{m.event_start[:10]} (peak {m.peak_ft:.1f} ft), {h}", fontsize=9)
            ax.set_xlabel("issue time, hours from rise onset (dashed)", fontsize=7); ax.set_ylabel("change in stage (ft)", fontsize=7)
        axes[r_i, 0].legend(fontsize=6.5, loc="upper left")
    fig.suptitle("Issue-time view: what each forecast, made at the time on the x axis, said would happen, against what happened\n" + LABEL, fontsize=9, x=0.01, ha="left")
    fig.savefig(FIG / "figO4_issue_time_view_official_events.png", dpi=140); plt.close(fig)


if __name__ == "__main__":
    main()
