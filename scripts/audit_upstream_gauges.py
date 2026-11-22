"""Quality audit of the upstream gauges using USGS daily values (one request per gauge): yearly completeness of daily stage, and shifts in daily-mean stage at
matched low discharge (a step change suggests a datum or channel-control change, which would corrupt a stage-based input).  Output: reports/upstream_feasibility/tables
Usage: python scripts/audit_upstream_gauges.py"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
import dataretrieval.nwis as nwis  # noqa: E402

OUT = Path("reports/upstream_feasibility/tables")
SITES = ["08165300", "08165500", "08166000", "08166140", "08166200", "08166250", "08167000"]
import time  # noqa: E402

CACHE = Path("data/raw/upstream"); CACHE.mkdir(parents=True, exist_ok=True)


def get_dv(s):
    f = CACHE / f"dv_{s}.csv"
    if f.exists():
        return pd.read_csv(f, index_col=0, parse_dates=True)
    for attempt in range(6):
        try:
            d, _ = nwis.get_dv(sites=s, start="2007-10-01", end="2026-11-21", parameterCd="00060,00065")
            d.to_csv(f)
            return d
        except Exception as ex:
            print("retry", s, attempt, repr(ex)[:60], flush=True); time.sleep(8 * (attempt + 1))
    raise RuntimeError(f"could not fetch {s}")


rows, shifts = [], []
for s in SITES:
    d = get_dv(s)
    d.index = pd.to_datetime(d.index, utc=True)
    st = [c for c in d.columns if c.startswith("00065") and "Mean" in c and not c.endswith("_cd")]
    q = [c for c in d.columns if c.startswith("00060") and "Mean" in c and not c.endswith("_cd")]
    stage = pd.to_numeric(d[st[0]], errors="coerce"); dis = pd.to_numeric(d[q[0]], errors="coerce")
    yr = stage.groupby(stage.index.year)
    comp = (yr.count() / yr.size()).rename("frac_days_with_stage")
    for y, v in comp.items():
        rows.append({"site": s, "year": int(y), "frac_days_with_daily_stage": float(v), "days": int(yr.size()[y])})
    # stage at matched low discharge: days whose discharge lies in the 10th-40th percentile of the whole record
    lo, hi = dis.quantile(0.10), dis.quantile(0.40)
    band = stage[(dis >= lo) & (dis <= hi)]
    med = band.groupby(band.index.year).agg(["median", "count"])
    med = med[med["count"] >= 20]
    for y, r in med.iterrows():
        shifts.append({"site": s, "year": int(y), "median_stage_ft_at_matched_low_discharge": float(r["median"]), "n_days": int(r["count"]), "discharge_band_cfs": f"{lo:.1f}-{hi:.1f}"})
a = pd.DataFrame(rows); b = pd.DataFrame(shifts)
b["change_from_previous_year_ft"] = b.groupby("site").median_stage_ft_at_matched_low_discharge.diff()
a.to_csv(OUT / "upstream_audit_completeness_by_year.csv", index=False); b.to_csv(OUT / "upstream_audit_stage_at_matched_discharge.csv", index=False)
summ = a.groupby("site").agg(years=("year", "size"), min_year_frac=("frac_days_with_daily_stage", "min"), mean_frac=("frac_days_with_daily_stage", "mean")).round(3)
summ["years_with_stage_step_gt_0.5ft"] = b[b.change_from_previous_year_ft.abs() > 0.5].groupby("site").size().reindex(summ.index).fillna(0).astype(int)
summ["largest_year_to_year_step_ft"] = b.groupby("site").change_from_previous_year_ft.apply(lambda x: x.abs().max()).round(2)
summ["total_drift_first_to_last_year_ft"] = b.groupby("site").median_stage_ft_at_matched_low_discharge.apply(lambda x: x.iloc[-1] - x.iloc[0]).round(2)
summ.reset_index().to_csv(OUT / "upstream_audit_summary.csv", index=False); (OUT / "upstream_audit_summary.md").write_text(summ.reset_index().to_markdown(index=False))
print(summ.to_string())
print("\nyears with a step > 0.5 ft:"); print(b[b.change_from_previous_year_ft.abs() > 0.5][["site", "year", "median_stage_ft_at_matched_low_discharge", "change_from_previous_year_ft"]].round(2).to_string(index=False))
