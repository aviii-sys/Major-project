"""Deviation 3 audit: original (strict features, no evaluability rule) vs corrected results, and a check that events are
marked 'not evaluable' only when input/target coverage really makes evaluation impossible.
Writes reports/DEVIATION3_COMPARISON.md and reports/deviation3_unevaluable_diagnosis.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

from flashflood import data, events

ORIG, CORR = Path("reports/phase1a_original_strict/tables"), Path("reports/phase1a/tables")
MODELS = ["persistence", "trend", "ridge_H", "xgb_H"]
out = ["# Deviation 3: original versus corrected Phase 1A results\n",
       "ORIGINAL = first full run (strict rolling windows, events with no eligible rows counted as misses), regenerated bit-for-bit from the "
       "preserved code path (`run_phase1a.py --legacy`; every number printed during the first run was reproduced).",
       "CORRECTED = gap-tolerant features plus the not-evaluable rule. The defect was discovered AFTER inspecting test-set output, so the corrected "
       "test results are **post-hoc corrected / exploratory**, not an untouched confirmation.\n"]

# 1 rows
co, cc = pd.read_csv(ORIG / "data_prep_counts.csv"), pd.read_csv(CORR / "data_prep_counts.csv")
m = co.merge(cc, on="item", suffixes=("_original", "_corrected"))
m["rows_recovered"] = m.n_corrected - m.n_original
out += ["## 1. Eligible rows\n", m.to_markdown(index=False), ""]

# 2 regression
ro, rc = pd.read_csv(ORIG / "regression_metrics.csv"), pd.read_csv(CORR / "regression_metrics.csv")
k = ["protocol", "subset", "horizon", "model"]
mm = ro[k + ["n", "rmse"]].merge(rc[k + ["n", "rmse"]], on=k, suffixes=("_orig", "_corr"))
sel = mm[(mm.protocol == "chrono_test") & (mm.subset.isin(["all", "event_windows_stage10ft"])) & mm.model.isin(MODELS)]
out += ["## 2. Chronological-test RMSE (ft)\n", sel.round(3).to_markdown(index=False), ""]

# 3 official events status
po, pc = pd.read_csv(ORIG / "per_event_results.csv"), pd.read_csv(CORR / "per_event_results.csv")
kk = ["protocol", "definition", "event_start", "horizon", "model"]
pe = po[kk + ["status", "peak_forecast_ft"]].merge(pc[kk + ["status", "peak_forecast_ft"]], on=kk, suffixes=("_orig", "_corr"))
off = pe[(pe.protocol == "chrono_test") & (pe.definition == "official_action_25ft") & pe.model.isin(MODELS) & pe.horizon.isin(["1h", "3h"])].copy()
off["event_start"] = off.event_start.str[:16]
out += ["## 3. Official >=25 ft test events: status originally vs corrected\n", off.round(2).to_markdown(index=False), ""]
chg = pe[pe.status_orig != pe.status_corr]
out += ["## 4. How many (protocol, definition, event, horizon, model) rows changed status\n",
        f"{len(chg)} of {len(pe)} rows. By original -> corrected status:\n",
        chg.groupby(["status_orig", "status_corr"]).size().rename("n").reset_index().to_markdown(index=False), ""]

# 5 diagnosis of not-evaluable events
reg = data.load_stage(); s = reg.s
p = data.load_rain_hourly(); H = data.hydro_features(s); R = data.rain_features(p, s.index); tg = data.targets(s)
X = pd.concat([H, R], axis=1)
defs = {"official_action_25ft": ("exceed", 25.0), "official_minor_30ft": ("exceed", 30.0), "official_moderate_36ft": ("exceed", 36.0),
        "experimental_stage_10ft": ("exceed", 10.0), "experimental_stage_15ft": ("exceed", 15.0),
        "experimental_rise_4ft_3h": ("rapid", 4.0), "experimental_rise_8ft_3h": ("rapid", 8.0)}
rows = []
for name, (kind, thr) in defs.items():
    ev = events.exceedance_events(s, thr) if kind == "exceed" else events.rapid_rise_events(s, thr)
    for h, kst in data.HORIZONS.items():
        elig = (X.notna().all(axis=1) & tg[h].notna() & s.notna()).values
        for e in ev.itertuples():
            lo = max(0, e.i0 - kst - 4)
            w = slice(lo, e.i0 + 1)
            frac = elig[w].mean()
            if frac < 0.8:
                idx = np.arange(lo, e.i0 + 1)
                rows.append({"definition": name, "event_start": e.t0, "horizon": h, "eligible_frac": round(float(frac), 2), "issue_times": len(idx),
                             "stage_missing_or_floor": int(s.iloc[idx].isna().sum()), "target_missing": int(tg[h].iloc[idx].isna().sum()),
                             "hydro_feature_missing": int(H.iloc[idx].isna().any(axis=1).sum()), "rain_missing": int(R.iloc[idx].isna().any(axis=1).sum()),
                             "longest_stage_gap_h_in_prior_24h": float(s.iloc[max(0, e.i0 - 96):e.i0 + 1].isna().astype(int).groupby(
                                 s.iloc[max(0, e.i0 - 96):e.i0 + 1].notna().cumsum()).sum().max() * 0.25)})
dg = pd.DataFrame(rows)
dg.to_csv("reports/deviation3_unevaluable_diagnosis.csv", index=False)
out += ["## 5. Why events are 'not evaluable' (all protocols; events are flagged only when < 80% of the lead-credit issue times are eligible)\n",
        dg.to_markdown(index=False) if len(dg) else "none", ""]
Path("reports/DEVIATION3_COMPARISON.md").write_text("\n".join(out))
print("\n".join(out)[:200]); print("not-evaluable diagnoses:", len(dg))
print(dg.to_string(index=False) if len(dg) else "none")
