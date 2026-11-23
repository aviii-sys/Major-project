"""Warning-lead evaluation on top of the existing fixed alarm rule (Phase 1A/1B definitions; unchanged): how many events are warned EARLY by at least a given lead.
Lead = event start minus the first matched alarm (hours, 15-min resolution). Nothing here defines a new event or a new alarm rule."""
import numpy as np
import pandas as pd

from . import experiment

LEAD_HOURS = 0.5                    # the 30-minute target of docs/HYBRID_PLAN_30MIN_LEAD.md
DEFINITIONS = ("official_action_25ft", "experimental_stage_10ft", "experimental_rise_4ft_3h")
LABELS = {"official_action_25ft": "official NWS action stage (>= 25 ft)", "experimental_stage_10ft": "experimental: stage >= 10 ft", "experimental_rise_4ft_3h": "experimental: rise >= 4 ft in 3 h"}


def summarize(pe: pd.DataFrame, min_lead_h: float = LEAD_HOURS) -> dict:
    """Counts from the per-event table returned by `experiment.detect` (status early/late/miss/not_evaluable, lead_h)."""
    ev = pe[pe.status != "not_evaluable"]
    early = ev[ev.status == "early"]
    return {"events": int(len(ev)), "early_hits": int(len(early)), "late": int((ev.status == "late").sum()), "misses": int((ev.status == "miss").sum()),
            "hits_with_lead_ge_30min": int((early.lead_h >= min_lead_h - 1e-9).sum()), "hits_with_lead_ge_60min": int((early.lead_h >= 1.0 - 1e-9).sum()),
            "median_lead_h_of_early_hits": float(early.lead_h.median()) if len(early) else np.nan}


def detect_all(ctx, change_arrays: dict, ev_eval: dict, elig: dict, years: float, horizons, kstep: dict, definitions=DEFINITIONS) -> tuple:
    """change_arrays: horizon -> predicted stage change on the grid (NaN where no forecast). Returns (summary rows, per-event rows)."""
    summ_rows, ev_rows = [], []
    for defn in definitions:
        evs = ev_eval[defn]
        for h in horizons:
            k = kstep[h]
            a = np.where(elig[h], change_arrays[h], np.nan)
            raw = experiment.fixed_rule_raw(ctx, a, k, ctx.kind_of[defn], ctx.thr_of[defn]) & np.isfinite(a)
            summ, pe = experiment.detect(ctx, raw, evs, k, elig[h], years)
            if summ is None:
                continue
            extra = summarize(pe)
            summ_rows.append({"definition": defn, "horizon": h, **extra, "alarm_episodes": summ["alarm_episodes"], "false_alarm_episodes": summ["false_alarm_episodes"],
                              "false_alarms_per_year": summ["false_alarms_per_year"], "storm_clusters": summ["storm_clusters"]})
            for r in pe.itertuples():
                ev_rows.append({"definition": defn, "horizon": h, "event_start": str(ctx.s.index[int(r.i0)])[:16], "peak_ft": float(r.peak_ft), "status": r.status, "lead_h": r.lead_h})
    return summ_rows, ev_rows
