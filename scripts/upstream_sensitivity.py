"""Sensitivity of the upstream lead-time findings to the rise trigger (0.5, 1, 2 ft per 3 h) and to the consistency tolerance. Uses cached IV data only.
Output: reports/upstream_feasibility/tables/sensitivity_*.csv"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from assess_upstream_inputs import SITES, RAW, fetch, rise_timing  # noqa: E402
from flashflood import experiment  # noqa: E402

OUT = Path("reports/upstream_feasibility/tables")
ctx = experiment.build_context(); idx = ctx.s.index
m = pd.read_csv("reports/phase1d/event_to_fold_mapping.csv"); m = m[m.definition == "experimental_stage_10ft"]
evaluated = set(m[m.status == "evaluated"].event_start.str[:16])
ev = ctx.ev_all["experimental_stage_10ft"]
rows = []
for trig in (0.5, 1.0, 2.0):
    for tol in (3, 6, 12):
        per_event = []
        for e in ev.itertuples():
            t0, t1 = idx[int(e.i0)], idx[int(e.i1)]
            if str(t0)[:16] not in evaluated:
                continue
            lo, hi = t0 - pd.Timedelta("36h"), t1 + pd.Timedelta("18h")
            sb = rise_timing(ctx.s, lo, hi, trig)
            best = np.nan
            if sb["status"] == "responds":
                for site in SITES:
                    f = RAW / f"{site}_{(lo - pd.Timedelta('24h')):%Y%m%d}_{(hi + pd.Timedelta('12h')):%Y%m%d}.csv"
                    if not f.exists():
                        continue
                    d = pd.read_csv(f, index_col=0, parse_dates=True)
                    up = rise_timing(d["00065"], lo, hi, trig)
                    if up["status"] != "responds":
                        continue
                    lf = (sb["t_first"] - up["t_first"]) / pd.Timedelta("1h"); ls = (sb["t_steep"] - up["t_steep"]) / pd.Timedelta("1h")
                    if abs(lf - ls) <= tol and (np.isnan(best) or lf > best):
                        best = lf
            per_event.append(best)
        b = pd.Series(per_event)
        rows.append({"trigger_ft_per_3h": trig, "consistency_tolerance_h": tol, "events": len(b), "events_with_consistent_upstream_response": int(b.notna().sum()),
                     "best_lead_ge_1h": int((b >= 1).sum()), "best_lead_ge_3h": int((b >= 3).sum()), "best_lead_ge_6h": int((b >= 6).sum()), "no_usable_warning": int(((b < 1) | b.isna()).sum())})
r = pd.DataFrame(rows); r.to_csv(OUT / "sensitivity_trigger_and_tolerance.csv", index=False)
(OUT / "sensitivity_trigger_and_tolerance.md").write_text(r.to_markdown(index=False))
print(r.to_string(index=False))
