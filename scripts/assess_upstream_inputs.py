"""Feasibility assessment of additional predictive inputs (Decision 3): upstream gauge lead over the Spring Branch rise.
DESCRIPTIVE only: no model is trained.  For each >= 10 ft event (all 20 in the catalogue; this is not a forecasting evaluation) and each long-record upstream
stage gauge, fetch 15-min stage around the event and time (a) the first and (b) the steepest 3-hour rise of at least 1 ft, identically at the upstream
gauge and at 08167500.  Lead = time at 08167500 minus time at the upstream gauge (positive = upstream rises first).
Version 2: fixes (i) gauges whose stage column is named '00065_<sensor description>' were silently dropped as 'no data'; (ii) the baseline/amplitude 'arrival'
definition, which an earlier minor pulse could trigger, is replaced by baseline-free rise timings with a two-method consistency check.
Output: reports/upstream_feasibility/tables.   Usage: python scripts/assess_upstream_inputs.py
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
import dataretrieval.nwis as nwis  # noqa: E402

from flashflood import experiment  # noqa: E402

RAW = Path("data/raw/upstream/iv")
RAW.mkdir(parents=True, exist_ok=True)
OUT = Path("reports/upstream_feasibility/tables")
OUT.mkdir(parents=True, exist_ok=True)
SITES = ["08165300", "08165500", "08166000", "08166140", "08166200", "08166250", "08167000", "08167200"]
TRIGGER_FT = 1.0           # a "rise" = stage increase of at least this much within 3 hours


def fetch(site, a, b):
    f = RAW / f"{site}_{a:%Y%m%d}_{b:%Y%m%d}.csv"
    if f.exists():
        return pd.read_csv(f, index_col=0, parse_dates=True)
    try:
        d, _ = nwis.get_iv(sites=site, start=str(a.date()), end=str(b.date()), parameterCd="00065")
    except Exception:
        return pd.DataFrame()
    cols = [c for c in (d.columns if d is not None else []) if str(c).startswith("00065") and not str(c).endswith("_cd")]
    if d is None or len(d) == 0 or not cols:
        return pd.DataFrame()
    d = d[[cols[0]]].rename(columns={cols[0]: "00065"}).copy()
    d.index = pd.to_datetime(d.index, utc=True)
    d.to_csv(f)
    return d


def rise_timing(s: pd.Series, t_lo, t_hi, trigger_ft: float = TRIGGER_FT):
    """Timing of the first and of the steepest 3-hour rise (>= TRIGGER_FT) inside [t_lo, t_hi]; computed identically at every gauge.
    No baseline or amplitude is needed, so an earlier minor pulse cannot shift the result."""
    w = s.loc[t_lo:t_hi]
    cov = float(w.notna().sum() / ((t_hi - t_lo) / pd.Timedelta("15min")))
    if cov < 0.8:
        return {"coverage": cov, "status": "insufficient coverage"}
    inc3 = (w - w.shift(12)).dropna()
    if len(inc3) == 0 or inc3.max() < trigger_ft:
        return {"coverage": cov, "status": "no response", "max_3h_rise_ft": float(inc3.max()) if len(inc3) else np.nan}
    return {"coverage": cov, "status": "responds", "max_3h_rise_ft": float(inc3.max()), "t_first": inc3[inc3 >= trigger_ft].index[0], "t_steep": inc3.idxmax(), "t_peak": w.idxmax()}


def main() -> None:
    ctx = experiment.build_context()
    idx = ctx.s.index
    ev = ctx.ev_all["experimental_stage_10ft"]
    info = pd.read_csv("data/raw/upstream/upstream_site_info.csv", dtype={"site_no": str}).set_index("site_no")
    rows = []
    for e in ev.itertuples():
        t0, t1 = idx[int(e.i0)], idx[int(e.i1)]
        lo, hi = t0 - pd.Timedelta("36h"), t1 + pd.Timedelta("18h")
        sb = rise_timing(ctx.s, lo, hi)
        if sb["status"] != "responds":
            continue
        for site in SITES:
            d = fetch(site, lo - pd.Timedelta("24h"), hi + pd.Timedelta("12h"))
            rec = {"event_start": str(t0)[:16], "peak_ft_08167500": float(e.peak_ft), "site": site, "name": info.loc[site, "station_nm"], "drain_area_sqmi": info.loc[site, "drain_area_va"]}
            if len(d) == 0:
                rec["status"] = "no data"; rows.append(rec); continue
            up = rise_timing(d["00065"], lo, hi)
            rec.update({"status": up["status"], "coverage": up["coverage"], "upstream_max_3h_rise_ft": up.get("max_3h_rise_ft", np.nan)})
            if up["status"] == "responds":
                lf = (sb["t_first"] - up["t_first"]) / pd.Timedelta("1h")
                ls = (sb["t_steep"] - up["t_steep"]) / pd.Timedelta("1h")
                rec.update({"first_rise_lead_h": lf, "steepest_rise_lead_h": ls, "peak_lag_h": (sb["t_peak"] - up["t_peak"]) / pd.Timedelta("1h"), "two_timings_agree_within_6h": bool(abs(lf - ls) <= 6)})
            rows.append(rec)
        print("done event", str(t0)[:10], flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "upstream_event_timing.csv", index=False)
    summ = []
    for site, g in df.groupby("site"):
        r = g[g.status == "responds"]
        ok = r[r.two_timings_agree_within_6h]
        summ.append({"site": site, "name": g["name"].iloc[0], "drain_area_sqmi": g.drain_area_sqmi.iloc[0], "events_in_catalogue": len(g),
                     "events_with_usable_data": int((~g.status.isin(["no data", "insufficient coverage"])).sum()), "events_upstream_responds": len(r), "responds_and_two_timings_agree": len(ok),
                     "median_first_rise_lead_h": float(ok.first_rise_lead_h.median()) if len(ok) else np.nan, "min_first_rise_lead_h": float(ok.first_rise_lead_h.min()) if len(ok) else np.nan,
                     "max_first_rise_lead_h": float(ok.first_rise_lead_h.max()) if len(ok) else np.nan, "median_steepest_rise_lead_h": float(ok.steepest_rise_lead_h.median()) if len(ok) else np.nan,
                     "events_first_rise_lead_ge_1h": int((ok.first_rise_lead_h >= 1).sum()), "events_first_rise_lead_ge_3h": int((ok.first_rise_lead_h >= 3).sum()),
                     "events_first_rise_lead_negative": int((ok.first_rise_lead_h < 0).sum())})
    s = pd.DataFrame(summ).sort_values("drain_area_sqmi", ascending=False, key=lambda x: pd.to_numeric(x))
    s.to_csv(OUT / "upstream_gauge_lead_summary.csv", index=False)
    (OUT / "upstream_gauge_lead_summary.md").write_text(s.round(2).to_markdown(index=False))
    print(s.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
