"""ALTERNATIVE anchoring (v3), added after visual inspection of the plotted events showed that v2 can anchor on a small earlier Spring Branch pulse (2024-07-24).
v3 anchors the Spring Branch timing to the catalogued event's own rise: window [t0-12h, t0+3h]; upstream window [t0-48h, t0+3h]; same 1 ft/3 h trigger, same
consistency rule.  v2 results are NOT replaced; both are reported.  Cached data only.  Output: tables/upstream_event_level_lead_v3.csv, v2_vs_v3_changes.csv"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from assess_upstream_inputs import SITES, RAW, rise_timing  # noqa: E402
from flashflood import experiment  # noqa: E402

OUT = Path("reports/upstream_feasibility/tables")
ctx = experiment.build_context(); idx = ctx.s.index
m = pd.read_csv("reports/phase1d/event_to_fold_mapping.csv"); m = m[m.definition == "experimental_stage_10ft"]
evaluated = set(m[m.status == "evaluated"].event_start.str[:16])
ev = ctx.ev_all["experimental_stage_10ft"]
rows = []
for e in ev.itertuples():
    t0, t1 = idx[int(e.i0)], idx[int(e.i1)]
    key = str(t0)[:16]
    if key not in evaluated:
        continue
    lo_v2, hi_v2 = t0 - pd.Timedelta("36h"), t1 + pd.Timedelta("18h")
    sb = rise_timing(ctx.s, t0 - pd.Timedelta("12h"), t0 + pd.Timedelta("3h"))
    best, bsite, n_resp, n_cov_bad = np.nan, "", 0, 0
    if sb["status"] == "responds":
        for site in SITES:
            f = RAW / f"{site}_{(lo_v2 - pd.Timedelta('24h')):%Y%m%d}_{(hi_v2 + pd.Timedelta('12h')):%Y%m%d}.csv"
            if not f.exists():
                continue
            d = pd.read_csv(f, index_col=0, parse_dates=True)
            up = rise_timing(d["00065"], t0 - pd.Timedelta("48h"), t0 + pd.Timedelta("3h"))
            if up["status"] == "insufficient coverage":
                n_cov_bad += 1
            if up["status"] != "responds":
                continue
            lf = (sb["t_first"] - up["t_first"]) / pd.Timedelta("1h"); ls = (sb["t_steep"] - up["t_steep"]) / pd.Timedelta("1h")
            if abs(lf - ls) <= 6:
                n_resp += 1
                if np.isnan(best) or lf > best:
                    best, bsite = lf, site
    rows.append({"event_start": key, "peak_ft": float(e.peak_ft), "v3_gauges_consistent": n_resp, "v3_best_first_rise_lead_h": best, "v3_best_gauge": bsite, "v3_gauges_with_insufficient_coverage": n_cov_bad})
v3 = pd.DataFrame(rows)
v2 = pd.read_csv(OUT / "upstream_event_level_lead.csv")[["event_start", "best_first_rise_lead_h", "best_gauge"]].rename(columns={"best_first_rise_lead_h": "v2_best_first_rise_lead_h", "best_gauge": "v2_best_gauge"})
c = v3.merge(v2, on="event_start"); c.to_csv(OUT / "upstream_event_level_lead_v3.csv", index=False)
cls = lambda x: np.where(x.isna() | (x < 1), "none (<1 h)", np.where(x < 6, "1-6 h", ">=6 h"))  # noqa: E731
c["v2_class"], c["v3_class"] = cls(c.v2_best_first_rise_lead_h), cls(c.v3_best_first_rise_lead_h)
c[c.v2_class != c.v3_class].to_csv(OUT / "upstream_v2_vs_v3_changes.csv", index=False)
print(c.round(1)[["event_start", "peak_ft", "v2_best_first_rise_lead_h", "v3_best_first_rise_lead_h", "v2_class", "v3_class", "v3_gauges_with_insufficient_coverage"]].to_string(index=False))
for nme in ("v2", "v3"):
    s = c[f"{nme}_best_first_rise_lead_h"]
    print(f"{nme}: consistent response {int(s.notna().sum())}/18 | >=3 h {int((s >= 3).sum())} | >=6 h {int((s >= 6).sum())} | none (<1 h or no response) {int(((s < 1) | s.isna()).sum())}")
