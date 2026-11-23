"""H0 (E22): warning-lead evaluation of the EXISTING saved baselines (docs/HYBRID_PLAN_30MIN_LEAD.md section 4). No training; reads saved predictions only.
Question: for how many events does each baseline raise an early alarm at least 30 minutes before the event criterion is first met, at which false-alarm cost?
Usage (project root): PYTHONPATH=src python scripts/run_h0_leadtime.py        Output: reports/hybrid_h0/{tables,baseline_leadtime.json}
"""
import hashlib
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from flashflood import data, experiment, leadtime, oof  # noqa: E402

OUT = Path("reports/hybrid_h0")
TAB = OUT / "tables"
TAB.mkdir(parents=True, exist_ok=True)
HZ = experiment.HZ
KSTEP = data.HORIZONS
SEEDS = (0, 1, 2)


def md(df, name):
    df.to_csv(TAB / f"{name}.csv", index=False)
    (TAB / f"{name}.md").write_text(df.to_markdown(index=False, floatfmt=".4g"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> None:
    ctx = experiment.build_context()
    idx, n = ctx.s.index, ctx.n
    spec = oof.fold_spec()
    fold_of = oof.fold_of_array(idx, spec)
    elig = {h: ctx.elig[h] & (fold_of > 0) for h in HZ}
    years = (idx[-1] - spec.test_start.min()).days / 365.25
    ev_eval = {d: ev[(fold_of[ev.i0.values] > 0)].reset_index(drop=True) for d, ev in ctx.ev_all.items()}

    # ---- assemble the saved baselines as predicted stage changes
    cls = oof.classical_changes(n)
    models = {m: {h: cls[(m, h)].copy() for h in HZ} for m in ("persistence", "trend_v2", "ridge_H", "xgb_H")}
    models["lstm_s0"] = oof.phase1d_deep(n, "lstm", 0)
    for s in SEEDS:
        models[f"gru24_s{s}"] = oof.phase1e_gru24(n, s)
    for name, arr in models.items():
        oof.mask_to_eligible(arr, elig)
        for h in HZ:
            assert np.isfinite(arr[h][elig[h]]).all(), (name, h)

    summ_all, ev_all = [], []
    for name, arr in models.items():
        s_rows, e_rows = leadtime.detect_all(ctx, arr, ev_eval, elig, years, HZ, KSTEP)
        summ_all += [{"model": name, **r} for r in s_rows]
        ev_all += [{"model": name, **r} for r in e_rows]
    S = pd.DataFrame(summ_all)
    E = pd.DataFrame(ev_all)
    md(S, "H0_1_leadtime_summary_per_model_and_seed")
    md(E, "H0_3_per_event_leads")

    # ---- reproduction check against the Phase 1D pooled detection table (same rule, same rows, same models)
    d5 = pd.read_csv("reports/phase1d/tables/D5_fixed_rule_detection_pooled_oof.csv")
    alias = {"gru": "gru24_s0", "lstm": "lstm_s0"}
    chk = []
    for r in d5.itertuples():
        if r.definition not in leadtime.DEFINITIONS:
            continue
        m = alias.get(r.model, r.model)
        q = S[(S.model == m) & (S.definition == r.definition) & (S.horizon == r.horizon)]
        if len(q) == 0:
            continue
        q = q.iloc[0]
        chk.append({"definition": r.definition, "horizon": r.horizon, "model": r.model, "early_D5": int(r.early_hits), "early_here": int(q.early_hits), "late_D5": int(r.late), "late_here": int(q.late),
                    "miss_D5": int(r.misses), "miss_here": int(q.misses), "fa_D5": int(r.false_alarm_episodes), "fa_here": int(q.false_alarm_episodes)})
    C = pd.DataFrame(chk)
    C["match"] = (C.early_D5 == C.early_here) & (C.late_D5 == C.late_here) & (C.miss_D5 == C.miss_here) & (C.fa_D5 == C.fa_here)
    md(C, "H0_2_reproduction_check_vs_D5")
    if not C.match.all():
        raise SystemExit("H0 harness does not reproduce Phase 1D D5:\n" + C[~C.match].to_string())

    # ---- GRU 24 h: seed mean [min-max] (the matched deep baseline for the hybrid)
    g = S[S.model.str.startswith("gru24_")].groupby(["definition", "horizon"]).agg(events=("events", "first"), storm_clusters=("storm_clusters", "first"), early_hits_mean=("early_hits", "mean"),
                                                                                  lead30_mean=("hits_with_lead_ge_30min", "mean"), lead30_min=("hits_with_lead_ge_30min", "min"), lead30_max=("hits_with_lead_ge_30min", "max"),
                                                                                  fa_mean=("false_alarm_episodes", "mean"), fa_per_year_mean=("false_alarms_per_year", "mean")).reset_index()
    md(g, "H0_1b_gru24_three_seed_summary")

    # ---- the headline table: events with a 30-minute lead, by single configuration (no oracle selection)
    head = S[S.model.isin(["persistence", "trend_v2", "ridge_H", "xgb_H", "lstm_s0", "gru24_s0"])][["definition", "horizon", "model", "events", "storm_clusters", "early_hits", "hits_with_lead_ge_30min", "hits_with_lead_ge_60min",
                                                                                                    "late", "misses", "false_alarm_episodes", "false_alarms_per_year", "median_lead_h_of_early_hits"]]
    md(head, "H0_4_headline_events_with_30min_lead")

    # ---- headroom: events where NO baseline configuration reaches 30 minutes (reported with and without the oracle caveat)
    base = E[E.model.isin(["trend_v2", "ridge_H", "xgb_H", "lstm_s0", "gru24_s0"]) & E.horizon.isin(["30m", "1h", "3h"])]
    base = base.assign(lead=np.where(base.status == "early", base.lead_h, 0.0))
    best = base.groupby(["definition", "event_start", "peak_ft"]).lead.max().reset_index().rename(columns={"lead": "best_lead_h_any_baseline_30m_1h_3h"})
    best["reaches_30min_with_some_configuration"] = best.best_lead_h_any_baseline_30m_1h_3h >= 0.5 - 1e-9
    md(best, "H0_5_headroom_events_best_baseline_lead")
    hard = best[~best.reaches_30min_with_some_configuration]
    md(hard, "H0_5b_events_no_baseline_reaches_30min")

    frozen = {"note": "Frozen baseline warning-lead numbers (fixed alarm rule; lead >= 30 min counted among early hits). Retrospective, exploratory. The hybrid (H1) must be compared with these.",
              "years_of_test_record": round(years, 3), "headline": head.round(4).to_dict(orient="records"), "gru24_three_seed": g.round(4).to_dict(orient="records"),
              "inputs_sha256": {p: sha(p) for p in ["reports/phase1d/tables/D5_fixed_rule_detection_pooled_oof.csv", "reports/phase1d/fold_specification.csv"]}}
    (OUT / "baseline_leadtime.json").write_text(json.dumps(frozen, indent=1))
    print("H0 written to", OUT, "| reproduction of Phase 1D D5 rows:", len(C), "all match:", bool(C.match.all()))


if __name__ == "__main__":
    main()
