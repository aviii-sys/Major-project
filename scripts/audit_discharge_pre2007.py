"""Continuity/quality audit of the SEPARATE pre-2007 discharge-only record (USGS 08167500, param 00060).

Inclusion criteria (fixed before looking at results), evaluated per calendar year:
  C1  >= 95% of consecutive sample intervals are exactly 15 min
  C2  >= 90% of the year's expected 15-min steps are present
  C3  every candidate flood event (discharge >= EVENT_Q cfs) has no data gap > 2 h within +/- 24 h of its peak
  C4  no negative discharge
A year passes if C1-C4 all hold.  Candidate-event discharge thresholds are EXPERIMENTAL (not NWS), because the NWS
publishes no flow equivalents for this gauge and gage height must NOT be inferred from discharge here.
Outputs: reports/discharge_pre2007/*.csv|md
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
RAW = Path("data/raw/usgs_iv_discharge_pre2007")
OUT = Path("reports/discharge_pre2007")
OUT.mkdir(parents=True, exist_ok=True)
EVENT_Q = 10000.0          # experimental candidate-event discharge threshold (cfs)
THRESH = (5000, 10000, 20000, 30000, 50000)


def load() -> pd.DataFrame:
    d = pd.concat([pd.read_csv(f, index_col=0) for f in sorted(RAW.glob("iv_*.csv"))])
    d.index = pd.to_datetime(d.index, utc=True)
    d = d[~d.index.duplicated()].sort_index()
    d = d.rename(columns={"00060": "q_cfs", "00060_cd": "q_cd"})
    d["q_cfs"] = pd.to_numeric(d.q_cfs, errors="coerce")
    return d


def main() -> None:
    d = load()
    q = d.q_cfs
    steps = d.index.to_series().diff().dt.total_seconds().div(60)
    rows = []
    for y in range(d.index.min().year, d.index.max().year + 1):
        sel = d[d.index.year == y]
        if sel.empty:
            rows.append({"year": y, "rows": 0})
            continue
        st = steps[d.index.year == y].dropna()
        full = pd.date_range(f"{y}-01-01", f"{y}-12-31 23:45", freq="15min", tz="UTC")
        n_exp = len(full) if y != d.index.min().year else int(((full >= d.index.min())).sum())
        n_exp = n_exp if y != 2007 else int((full <= pd.Timestamp("2007-10-01 23:45", tz="UTC")).sum())
        on15 = float((st == 15).mean()) if len(st) else np.nan
        comp = len(sel[sel.index.isin(full)]) / n_exp
        rows.append({"year": y, "rows": len(sel), "median_step_min": float(st.median()), "pct_intervals_15min": 100 * on15,
                     "pct_expected_15min_steps_present": 100 * comp, "n_negative": int((sel.q_cfs < 0).sum()),
                     "n_zero": int((sel.q_cfs == 0).sum()), "max_q_cfs": float(sel.q_cfs.max()),
                     "pct_estimated_e": 100 * float(sel.q_cd.astype(str).str.contains("e").mean()),
                     "pct_provisional_P": 100 * float(sel.q_cd.astype(str).str.startswith("P").mean())})
    yr = pd.DataFrame(rows)

    # candidate events by discharge (24 h merge) and the C3 gap test around each peak
    ev_rows = []
    for thr in THRESH:
        above = (q >= thr).values
        t = q.index
        st_, en_ = np.where(np.diff(np.r_[0, above.astype(int), 0]) == 1)[0], np.where(np.diff(np.r_[0, above.astype(int), 0]) == -1)[0] - 1
        merged: list = []
        for a, b in zip(st_, en_):
            if merged and (t[a] - t[merged[-1][1]]) < pd.Timedelta("24h"):
                merged[-1][1] = b
            else:
                merged.append([a, b])
        for a, b in merged:
            seg = q.iloc[a:b + 1]
            pk = seg.idxmax()
            w = d.loc[pk - pd.Timedelta("24h"): pk + pd.Timedelta("24h")]
            gaps = w.index.to_series().diff().dt.total_seconds().div(3600)
            ev_rows.append({"threshold_cfs": thr, "start": t[a], "peak_time": pk, "peak_q_cfs": float(seg.max()),
                            "median_step_min_pm24h": float(w.index.to_series().diff().dt.total_seconds().div(60).median()),
                            "max_gap_h_pm24h": float(gaps.max()) if len(gaps) > 1 else np.nan, "n_obs_pm24h": len(w),
                            "pct_estimated_pm24h": 100 * float(w.q_cd.astype(str).str.contains("e").mean())})
    ev = pd.DataFrame(ev_rows)
    cand = ev[ev.threshold_cfs == EVENT_Q].copy()
    cand["C3_ok"] = (cand.max_gap_h_pm24h <= 2) & (cand.median_step_min_pm24h == 15)
    cand["year"] = cand.peak_time.dt.year
    c3 = cand.groupby("year").C3_ok.agg(lambda s: bool(s.all()) if len(s) else True)
    yr["C1"] = yr.pct_intervals_15min >= 95
    yr["C2"] = yr.pct_expected_15min_steps_present >= 90
    yr["C3"] = yr.year.map(c3).fillna(True)
    yr["C4"] = yr.n_negative == 0
    yr["PASS"] = yr[["C1", "C2", "C3", "C4"]].all(axis=1)
    yr.to_csv(OUT / "yearly_audit.csv", index=False)
    (OUT / "yearly_audit.md").write_text(yr.round(1).to_markdown(index=False))
    ev.to_csv(OUT / "candidate_events.csv", index=False)
    cand.to_csv(OUT / "candidate_events_10000cfs_with_gap_test.csv", index=False)
    (OUT / "candidate_events_10000cfs_with_gap_test.md").write_text(cand.round(1).to_markdown(index=False))
    print(yr.round(1).to_string(index=False))
    print("\nevents by threshold:", ev.groupby("threshold_cfs").size().to_dict())
    print(cand.round(1).to_string(index=False))
    # the two years named in the decision
    peaks = pd.read_csv("data/raw/meta/annual_peaks.csv")
    for pdt, label in (("1997-06-22", "1997 flood"), ("2002-07-05", "2002 flood")):
        t0 = pd.Timestamp(pdt, tz="UTC")
        w = d.loc[t0 - pd.Timedelta("3D"): t0 + pd.Timedelta("4D")]
        st = w.index.to_series().diff().dt.total_seconds().div(60)
        pk = peaks[peaks.peak_dt == pdt]
        print(f"\n{label}: obs in +/-(3,4)d window {len(w)} (15-min full = 672); step mode {st.mode().iloc[0]:.0f} min; max gap {st.max():.0f} min; "
              f"IV max {w.q_cfs.max():.0f} cfs at {w.q_cfs.idxmax()}; USGS peak file {pk.peak_va.values}")


def flood_day_check() -> None:
    """C5 (added after the yearly audit showed 1997/2002 passing C1-C4 while their flood peaks are absent):
    for every UTC day whose independent USGS DAILY MEAN discharge is >= 5,000 cfs, the 15-min record must hold
    >= 90% of that day's 96 samples and its maximum must be >= the daily mean.  Candidate-event detection on the
    15-min record alone cannot see floods that have no 15-min data, so the daily record is the independent reference."""
    import dataretrieval.nwis as nwis
    dv, _ = nwis.get_dv(sites="08167500", start="1996-01-01", end="2007-10-01", parameterCd="00060")
    col = "00060_Mean"      # explicit: for 2001+ the service also returns _Maximum/_Minimum columns (first-column pick was a bug)
    dm = pd.Series(pd.to_numeric(dv[col], errors="coerce").values, index=pd.to_datetime(dv.index, utc=True).floor("D"))
    d = load()
    day = d.q_cfs.groupby(d.index.floor("D")).agg(n_obs="count", iv_max="max")
    tab = pd.concat([dm.rename("daily_mean_cfs"), day], axis=1).loc["1996-01-01":"2007-10-01"]
    tab["n_obs"] = tab.n_obs.fillna(0)
    fl = tab[tab.daily_mean_cfs >= 5000].copy()
    fl["coverage_pct"] = 100 * fl.n_obs / 96
    fl["iv_max_ge_daily_mean"] = fl.iv_max >= fl.daily_mean_cfs
    fl["day_ok"] = (fl.coverage_pct >= 90) & fl.iv_max_ge_daily_mean
    fl.index.name = "day"
    fl.reset_index().to_csv(OUT / "flood_day_check.csv", index=False)
    (OUT / "flood_day_check.md").write_text(fl.reset_index().round(1).to_markdown(index=False))
    s = fl.groupby(fl.index.year).agg(flood_days_ge5000=("day_ok", "size"), days_ok=("day_ok", "sum"))
    s["days_failing"] = s.flood_days_ge5000 - s.days_ok
    s.to_csv(OUT / "flood_day_check_by_year.csv")
    print("\nC5 flood-day check (days with independent daily mean >= 5,000 cfs):")
    print(s.to_string())
    print("\nfailing days with daily mean >= 20,000 cfs:")
    print(fl[(~fl.day_ok) & (fl.daily_mean_cfs >= 20000)][["daily_mean_cfs", "n_obs", "iv_max"]].round(0).to_string())


if __name__ == "__main__":
    main()
    flood_day_check()
