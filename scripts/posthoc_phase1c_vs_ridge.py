"""POST-HOC (not pre-registered) paired comparison of the deep models against ridge H and the damped trend on TEST (exploratory).
Added after seeing that the pre-registered comparator (XGBoost H, chosen on validation by a margin of 0.001 ft) is weaker than ridge H at 3 h on test.
Same paired storm-cluster bootstrap as eval_phase1c.py.  Output: reports/phase1c/tables/C2b_posthoc_vs_ridge_and_trend.csv"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from flashflood import experiment, metrics, models

OUT = Path("reports/phase1c")
ctx = experiment.build_context(); n = ctx.n
z = np.load("reports/phase1b/frozen/predictions.npz"); sel = json.load(open(OUT / "selection.json"))
pm = ctx.lab == "test"
subsets = {"all": np.ones(n, bool), "event_windows_stage10ft": ctx.win_mask(ctx.ev_all["experimental_stage_10ft"], "exceed"),
           "event_windows_rise4ft3h": ctx.win_mask(ctx.ev_all["experimental_rise_4ft_3h"], "rapid")}
dl = {}
for a in ["lstm", "gru", "transformer"]:
    for d in sorted((OUT / "runs").glob(f"{a}_h{sel[a]['chosen_hidden']}_s*")):
        zz = np.load(d / "predictions.npz")
        for hi, h in enumerate(experiment.HZ):
            p = np.full(n, np.nan); p[zz["test_idx"]] = zz["pred_test"][:, hi]; dl[(a, int(d.name.split("_s")[-1]), h)] = p
rows = []
for sub, sm in subsets.items():
    for h in experiment.HZ:
        cl = {m: z[f"reg|chrono_test|{m}|{h}"].astype(float) for m in ["ridge_H0", "trend_v2", "xgb_H0"]}
        mk = ctx.elig[h] & pm & sm
        for v in cl.values(): mk &= np.isfinite(v)
        y = ctx.tg[h][mk]; gb = metrics.GroupBoot(ctx.groups[mk], b=2000, seed=0)
        rep = {m: gb.mse(cl[m][mk] - y) for m in cl}
        for a in ["lstm", "gru", "transformer"]:
            seeds = [s for (aa, s, hh) in dl if aa == a and hh == h]
            r = np.mean([gb.mse(dl[(a, s, h)][mk] - y) for s in seeds], axis=0)
            pt = np.sqrt(np.mean([np.mean((dl[(a, s, h)][mk] - y) ** 2) for s in seeds]))
            for ref in ["ridge_H0", "trend_v2"]:
                d = np.sqrt(r) - np.sqrt(rep[ref]); lo, hi = gb.ci(d)
                rows.append({"subset": sub, "horizon": h, "model": a, "reference": ref, "rmse_diff_ft": float(pt - models.rmse(cl[ref][mk], y)), "ci_lo": lo, "ci_hi": hi,
                             "interval_excludes_zero": bool(lo > 0 or hi < 0), "status": "POST-HOC, exploratory"})
pd.DataFrame(rows).to_csv(OUT / "tables/C2b_posthoc_vs_ridge_and_trend.csv", index=False)
t = pd.DataFrame(rows); t = t[t.reference == "ridge_H0"]
t["diff [95% CI]"] = t.apply(lambda r: f"{r.rmse_diff_ft:+.3f} [{r.ci_lo:+.3f},{r.ci_hi:+.3f}]{' *' if r.interval_excludes_zero else ''}", axis=1)
print("POST-HOC vs ridge H, TEST (negative = deep better, * excludes zero)"); print(t.pivot_table(index=["subset", "model"], columns="horizon", values="diff [95% CI]", aggfunc="first")[experiment.HZ].to_string())
