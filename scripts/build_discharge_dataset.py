"""Build the SEPARATE 1998-2007 discharge-only dataset with per-event continuity/quality checks.

NOT merged into the primary stage dataset; no gage height is inferred from discharge.
Years 1998-2007-10-01 passed the yearly criteria C1-C4 (reports/discharge_pre2007/yearly_audit.md).  Events are then checked individually.
Candidate events use EXPERIMENTAL discharge thresholds (no NWS flow equivalents exist for this gauge).
Per-event usability = ALL of:
  U1  no gap > 2 h in the 15-min record within +/-24 h of the event window [start, end]
  U2  every UTC day touching [start-24h, end+24h] whose independent USGS DAILY MEAN is >= 5,000 cfs has >= 90% of 96 samples and IV max >= daily mean
  U3  the event contains no samples qualified 'e' (estimated) for more than 5% of its samples
Outputs: data/processed/discharge_1998_2007_15min.csv.gz, reports/discharge_pre2007/event_catalogue_checked.{csv,md}
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
import dataretrieval.nwis as nwis  # noqa: E402

RAW = Path("data/raw/usgs_iv_discharge_pre2007")
OUT = Path("reports/discharge_pre2007")
THRESH = {"exp_Q_10000cfs": 10000.0, "exp_Q_20000cfs": 20000.0, "exp_Q_30000cfs": 30000.0}
START, END = pd.Timestamp("1998-01-01", tz="UTC"), pd.Timestamp("2007-10-01 23:45", tz="UTC")


def runs(mask):
    m = np.asarray(mask).astype(int)
    d = np.diff(np.r_[0, m, 0])
    return np.where(d == 1)[0], np.where(d == -1)[0] - 1


def main() -> None:
    d = pd.concat([pd.read_csv(f, index_col=0) for f in sorted(RAW.glob("iv_*.csv"))])
    d.index = pd.to_datetime(d.index, utc=True)
    d = d[~d.index.duplicated()].sort_index().loc[START:END]
    d = d.rename(columns={"00060": "q_cfs", "00060_cd": "q_cd"})
    d["q_cfs"] = pd.to_numeric(d.q_cfs, errors="coerce")
    grid = pd.date_range(START, END, freq="15min")
    reg = d[["q_cfs", "q_cd"]].reindex(grid)
    reg["observed"] = reg.q_cfs.notna()
    reg["estimated"] = reg.q_cd.astype(str).str.contains("e")
    dv, _ = nwis.get_dv(sites="08167500", start="1998-01-01", end="2007-10-01", parameterCd="00060")
    dm = pd.Series(pd.to_numeric(dv["00060_Mean"], errors="coerce").values, index=pd.to_datetime(dv.index, utc=True).floor("D"))
    day = reg.q_cfs.groupby(reg.index.floor("D")).agg(n_obs="count", iv_max="max")
    chk = pd.concat([dm.rename("daily_mean_cfs"), day], axis=1).loc[START.floor("D"):END.floor("D")]
    chk["n_obs"] = chk.n_obs.fillna(0)
    chk["day_ok"] = (chk.n_obs >= 0.9 * 96) & (chk.iv_max >= chk.daily_mean_cfs)
    flood_days = chk[chk.daily_mean_cfs >= 5000]

    rows = []
    for name, thr in THRESH.items():
        st, en = runs(np.nan_to_num(reg.q_cfs.values, nan=-1) >= thr)
        merged: list = []
        for a, b in zip(st, en):
            if merged and (b - a >= 0) and (a - merged[-1][1]) * 0.25 < 24:
                merged[-1][1] = b
            else:
                merged.append([a, b])
        # also catch floods that are ABSENT from the 15-min record but present in the daily record (cannot be seen above)
        for a, b in merged:
            t0, t1 = reg.index[a], reg.index[b]
            w = reg.loc[t0 - pd.Timedelta("24h"): t1 + pd.Timedelta("24h")]
            obs_t = w.index[w.observed]
            gaps = pd.Series(obs_t).diff().dt.total_seconds().div(3600)
            max_gap = float(gaps.max()) if len(gaps) > 1 else np.nan
            u1 = bool(max_gap <= 2.0) if not np.isnan(max_gap) else False
            fd = flood_days.loc[(flood_days.index >= (t0 - pd.Timedelta("24h")).floor("D")) & (flood_days.index <= (t1 + pd.Timedelta("24h")).floor("D"))]
            u2 = bool(fd.day_ok.all()) if len(fd) else True
            est = float(reg.loc[t0:t1, "estimated"].mean())
            u3 = est <= 0.05
            rows.append({"definition": name, "start_utc": t0, "end_utc": t1, "peak_cfs": float(reg.q_cfs.iloc[a:b + 1].max()), "hours_above": (b - a + 1) * 0.25,
                         "max_gap_h_pm24h": max_gap, "U1_no_gap_gt_2h": u1, "flood_days_in_window": len(fd), "flood_days_failing": int((~fd.day_ok).sum()) if len(fd) else 0,
                         "U2_daily_reference_ok": u2, "frac_estimated": est, "U3_not_estimated": u3, "USABLE": u1 and u2 and u3})
    ev = pd.DataFrame(rows)
    ev.to_csv(OUT / "event_catalogue_checked.csv", index=False)
    (OUT / "event_catalogue_checked.md").write_text(ev.round(2).to_markdown(index=False))
    # floods present in the daily record but with no usable 15-min data at all (cannot appear as candidate events above)
    missing = flood_days[~flood_days.day_ok & (flood_days.daily_mean_cfs >= 20000)].copy()
    missing.to_csv(OUT / "daily_flood_days_failing_15min.csv")
    # flag every 15-min row that belongs to a USABLE event window (+/-24 h) so downstream code never uses unusable events
    reg["in_usable_event_window"] = False
    for r in ev[ev.USABLE & (ev.definition == "exp_Q_10000cfs")].itertuples():
        reg.loc[r.start_utc - pd.Timedelta("24h"): r.end_utc + pd.Timedelta("24h"), "in_usable_event_window"] = True
    reg.to_csv("data/processed/discharge_1998_2007_15min.csv.gz")
    print(ev.groupby("definition").agg(events=("USABLE", "size"), usable=("USABLE", "sum")).to_string())
    print("\n>=10,000 cfs events NOT usable:")
    print(ev[(ev.definition == "exp_Q_10000cfs") & ~ev.USABLE][["start_utc", "peak_cfs", "max_gap_h_pm24h", "flood_days_failing", "frac_estimated"]].round(2).to_string(index=False))
    print("\nflood days (daily mean >= 20,000 cfs) with inadequate 15-min data:"); print(missing.round(0).to_string())
    print("rows:", len(reg), "| observed:", int(reg.observed.sum()), "| in usable event windows:", int(reg.in_usable_event_window.sum()))


if __name__ == "__main__":
    main()
