"""Descriptive supporting tables for docs/UPSTREAM_INPUT_PROTOCOL.md (experiment id: documentation only, no model, no training, no evaluation).

Reads ONLY existing project files (event-to-fold mapping, Phase 1E per-event table, upstream feasibility tables, cached 15-min upstream gauge series,
daily gauge-rainfall product, series catalogue) plus a small cached public-archive availability probe (`mrms_archive_probe.csv`).
Every number in the outputs is either copied from those files or computed here by the arithmetic shown in the column name.

Usage (from the project root):
    .venv/bin/python scripts/build_upstream_protocol_support.py            # offline: uses the cached probe file
    .venv/bin/python scripts/build_upstream_protocol_support.py --probe    # ONE-TIME network probe of public directory listings (no personal data sent), then builds

Output: reports/upstream_protocol_support/tables/*.csv|md and README.md.
"""
import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("reports/upstream_protocol_support")
TAB = OUT / "tables"
IV = Path("data/raw/upstream/iv")
# same eight gauges, same order as scripts/assess_upstream_inputs.py (kept local to avoid importing a script with import-time side effects)
SITES = ["08165300", "08165500", "08166000", "08166140", "08166200", "08166250", "08167000", "08167200"]
SHORT = {"08165300": "N Fk Hunt", "08165500": "Hunt", "08166000": "Johnson Ck", "08166140": "Kerrville abv Bear", "08166200": "Kerrville", "08166250": "Center Point",
         "08167000": "Comfort", "08167200": "Bergheim"}
MRMS_BASE = "https://mtarchive.geol.iastate.edu"
LONG_LEAD_H, NONE_LEAD_H = 6.0, 1.0      # pre-specified class thresholds (docs/UPSTREAM_INPUT_PROTOCOL.md section 3.7); the same bands as upstream_anchored_v3.py
COV_MIN = 0.8                            # same coverage rule as rise_timing() in assess_upstream_inputs.py


# ------------------------------------------------------------------ pure functions (unit-tested)
def lead_band(x) -> str:
    """none: no consistent upstream response or best lead < 1 h; short: 1 h <= lead < 6 h; long: lead >= 6 h."""
    if x is None or (isinstance(x, float) and np.isnan(x)) or x < NONE_LEAD_H:
        return "none"
    return "short" if x < LONG_LEAD_H else "long"


def classify_event(v2_lead, v3_lead) -> tuple:
    """Pre-specified class from observed data only. Both timing rules (v2, v3) must agree for a firm class; anything else is 'ambiguous'."""
    b2, b3 = lead_band(v2_lead), lead_band(v3_lead)
    if b2 == "long" and b3 == "long":
        return "upstream-led", "both timing rules give a lead >= 6 h"
    if b2 == "none" and b3 == "none":
        return "local-or-downstream-led", "both timing rules give no consistent upstream response or a lead < 1 h"
    if b2 == b3:
        return "ambiguous", "short lead (1 h to < 6 h) under both timing rules"
    return "ambiguous", f"timing rules disagree (v2 {b2}, v3 {b3})"


def nws_stage_reached(peak_ft: float) -> str:
    """Highest NWS stage reached by the PEAK (project thresholds: action 25, minor 30, moderate 36, major 39 ft); below 25 ft it is NOT an official flood stage."""
    for thr, name in ((39, "major"), (36, "moderate"), (30, "minor"), (25, "action")):
        if peak_ft >= thr:
            return name
    return "below action stage (experimental >= 10 ft event only)"


def window_coverage(s: pd.Series, lo, hi) -> float:
    """Same definition as rise_timing(): non-missing samples in [lo, hi] divided by the number of 15-min intervals in the window."""
    w = s.loc[lo:hi]
    return float(w.notna().sum() / ((hi - lo) / pd.Timedelta("15min")))


def longest_gap_hours(s: pd.Series, lo, hi) -> float:
    """Longest run of missing 15-min samples inside [lo, hi] (hours), on the full 15-min grid."""
    grid = pd.date_range(lo, hi, freq="15min")
    miss = s.reindex(grid).isna().to_numpy().astype(int)
    best = cur = 0
    for m in miss:
        cur = cur + 1 if m else 0
        best = max(best, cur)
    return best * 0.25


def gauge_status(cov: float, has_any_record: bool) -> str:
    if not has_any_record or cov == 0:
        return "no data in window"
    return "recorded" if cov >= COV_MIN else "dropout (<80% coverage)"


# ------------------------------------------------------------------ availability probe of a public archive (directory listings only)
def probe_mrms(events: pd.DataFrame) -> None:
    import re

    import requests

    sess = requests.Session()
    sess.headers["User-Agent"] = "research-availability-check"
    rows = []

    def listing(url):
        r = sess.get(url, timeout=30)
        time.sleep(0.3)
        return r.status_code, (r.text if r.status_code == 200 else "")

    def has_product(day: pd.Timestamp) -> tuple:
        url = f"{MRMS_BASE}/{day:%Y/%m/%d}/mrms/ncep/GaugeCorr_QPE_01H/"
        code, txt = listing(url)
        return code, len(re.findall(r"GaugeCorr_QPE_01H_00\.00_\d{8}-\d{6}\.grib2", txt))

    # (1) first date of the hourly gauge-corrected product, bisection between the two monthly probes recorded in docs/UPSTREAM_INPUT_FEASIBILITY.md
    lo, hi = pd.Timestamp("2014-09-01"), pd.Timestamp("2014-12-01")
    while (hi - lo).days > 1:
        mid = lo + (hi - lo) // 2
        code, n = has_product(mid)
        rows.append({"kind": "bisection", "date": f"{mid:%Y-%m-%d}", "http": code, "gaugecorr_hourly_files": n, "toplevel_folders": ""})
        lo, hi = (mid, hi) if code != 200 or n == 0 else (lo, mid)
    for d in (lo, hi):
        code, n = has_product(d)
        rows.append({"kind": "bisection_final", "date": f"{d:%Y-%m-%d}", "http": code, "gaugecorr_hourly_files": n, "toplevel_folders": ""})
    # (2) every UTC date from the day before the event start (rain precedes the rise) to the event-end date, for each evaluated >= 10 ft event
    seen = set()
    for e in events.itertuples():
        t0, tp = pd.Timestamp(e.t0).tz_localize(None).normalize(), pd.Timestamp(e.t_end).tz_localize(None).normalize()
        for d in pd.date_range(t0 - pd.Timedelta("1D"), tp):
            if d in seen:
                continue
            seen.add(d)
            code, n = has_product(d)
            folders = ""
            if code != 200 or n == 0:
                c2, txt = listing(f"{MRMS_BASE}/{d:%Y/%m/%d}/")
                folders = " ".join(sorted(set(re.findall(r'href="([a-z0-9_]+)/"', txt)))) if c2 == 200 else f"listing http {c2}"
            rows.append({"kind": "event_date", "date": f"{d:%Y-%m-%d}", "http": code, "gaugecorr_hourly_files": n, "toplevel_folders": folders})
    pd.DataFrame(rows).to_csv(TAB / "mrms_archive_probe.csv", index=False)


# ------------------------------------------------------------------ table builders
def load_events() -> pd.DataFrame:
    m = pd.read_csv("reports/phase1d/event_to_fold_mapping.csv")
    m = m[(m.definition == "experimental_stage_10ft") & (m.status == "evaluated")].copy()
    m["t0"] = pd.to_datetime(m.event_start, utc=True)
    m["t1"] = pd.to_datetime(m.event_end, utc=True)
    m["key"] = m.t0.dt.strftime("%Y-%m-%d %H:%M")
    e4 = pd.read_csv("reports/phase1e/tables/E4_per_event.csv").drop_duplicates("event_start")[["event_start", "provisional_data", "official_stage_ge_25ft"]]
    m = m.merge(e4, left_on="key", right_on="event_start", how="left", suffixes=("", "_e4"))
    assert m.provisional_data.notna().all() and len(m) == 18
    v2 = pd.read_csv("reports/upstream_feasibility/tables/upstream_event_level_lead.csv", dtype={"best_gauge": str})
    v3 = pd.read_csv("reports/upstream_feasibility/tables/upstream_event_level_lead_v3.csv", dtype={"v3_best_gauge": str})
    m = m.merge(v2[["event_start", "gauges_usable", "gauges_with_consistent_response", "best_first_rise_lead_h", "best_gauge"]], left_on="key", right_on="event_start", how="left", suffixes=("", "_v2"))
    m = m.merge(v3[["event_start", "v3_gauges_consistent", "v3_best_first_rise_lead_h", "v3_best_gauge", "v3_gauges_with_insufficient_coverage"]], left_on="key", right_on="event_start", how="left", suffixes=("", "_v3"))
    assert m.v3_gauges_consistent.notna().all()
    # window end for the availability checks: the catalogue event end (the peak time is not stored in the mapping file)
    m["t_end"] = m.t1
    return m.sort_values("t0").reset_index(drop=True)


def gauge_coverage_long(ev: pd.DataFrame) -> pd.DataFrame:
    """Per event x gauge: coverage and longest gap in the v3 upstream window [t0-48 h, t0+3 h] from the cached 15-min series."""
    rows = []
    for e in ev.itertuples():
        lo_v2, hi_v2 = e.t0 - pd.Timedelta("36h"), e.t1 + pd.Timedelta("18h")
        lo, hi = e.t0 - pd.Timedelta("48h"), e.t0 + pd.Timedelta("3h")
        for site in SITES:
            f = IV / f"{site}_{(lo_v2 - pd.Timedelta('24h')):%Y%m%d}_{(hi_v2 + pd.Timedelta('12h')):%Y%m%d}.csv"
            if not f.exists():
                rows.append({"event_start": e.key, "site": site, "gauge": SHORT[site], "cached_file": False, "coverage": np.nan, "longest_gap_h": np.nan, "status": "no data in window"})
                continue
            d = pd.read_csv(f, index_col=0, parse_dates=True)
            s = d["00065"] if "00065" in d.columns else pd.Series(dtype=float)
            has = len(s.loc[lo:hi].dropna()) > 0
            cov = window_coverage(s, lo, hi) if len(s) else 0.0
            rows.append({"event_start": e.key, "site": site, "gauge": SHORT[site], "cached_file": True, "coverage": cov,
                         "longest_gap_h": longest_gap_hours(s, lo, hi) if len(s) else np.nan, "status": gauge_status(cov, has)})
    return pd.DataFrame(rows)


def build_event_table(ev: pd.DataFrame, cov: pd.DataFrame) -> pd.DataFrame:
    cat = pd.read_csv("data/raw/upstream/upstream_series_catalog.csv", dtype={"site_no": str})
    rain15 = cat[(cat.data_type_cd == "uv") & (cat.parm_cd == 45)].groupby("site_no").begin_date.min()
    gd = pd.read_csv("data/processed/gauge_basin_daily.csv", parse_dates=["date"]).set_index("date")
    probe = pd.read_csv(TAB / "mrms_archive_probe.csv", parse_dates=["date"]) if (TAB / "mrms_archive_probe.csv").exists() else pd.DataFrame()
    pe = probe[probe.kind == "event_date"].set_index("date") if len(probe) else pd.DataFrame()
    rows = []
    for e in ev.itertuples():
        c = cov[cov.event_start == e.key].set_index("gauge")
        rec = [g for g in c.index if c.loc[g, "status"] == "recorded"]
        drop = [g for g in c.index if c.loc[g, "status"].startswith("dropout")]
        nod = [g for g in c.index if c.loc[g, "status"] == "no data in window"]
        cls, why = classify_event(e.best_first_rise_lead_h, e.v3_best_first_rise_lead_h)
        days = pd.date_range(e.t0.tz_localize(None).normalize() - pd.Timedelta("1D"), e.t_end.tz_localize(None).normalize())
        g = gd.reindex(days)
        mx = g.basin_idw_mm.idxmax() if g.basin_idw_mm.notna().any() else None
        if len(pe):
            pr = pe.reindex(days)
            mrms = f"{int(pr.gaugecorr_hourly_files.fillna(0).sum())} hourly files on {int((pr.gaugecorr_hourly_files.fillna(0) > 0).sum())} of {len(days)} probed UTC dates"
            mrms_ok = bool((pr.gaugecorr_hourly_files.fillna(0) > 0).all())
        else:
            mrms, mrms_ok = "probe not run", None
        n_rain15 = int((pd.to_datetime(rain15) <= e.t0.tz_localize(None)).sum())
        marg = []
        if cls == "upstream-led":
            if e.v3_gauges_consistent <= 1:
                marg.append("only 1 gauge with a consistent response (v3)")
            if min(e.best_first_rise_lead_h, e.v3_best_first_rise_lead_h) < LONG_LEAD_H + 1:
                marg.append("lead within 1 h of the 6 h cut-off")
            if abs(e.v3_best_first_rise_lead_h - e.best_first_rise_lead_h) > 6:
                marg.append("v2 and v3 leads differ by > 6 h (multi-pulse storm)")
        if e.v3_best_first_rise_lead_h > 30:
            marg.append("v3 lead > 30 h is physically implausible per UPSTREAM_INPUT_FEASIBILITY.md 2c")
        rows.append({"event_start_utc": e.key, "peak_ft": e.peak_ft, "nws_stage_reached_by_peak": nws_stage_reached(e.peak_ft), "fold": int(e.fold), "storm_cluster": int(e.storm_cluster),
                     "provisional_data": bool(e.provisional_data),
                     "upstream_gauges_recorded_in_v3_window": len(rec), "gauges_recorded": ", ".join(rec), "gauges_dropout_lt80pct": ", ".join(drop), "gauges_no_data": ", ".join(nod),
                     "v2_best_first_rise_lead_h": e.best_first_rise_lead_h, "v2_best_gauge": e.best_gauge, "v3_best_first_rise_lead_h": e.v3_best_first_rise_lead_h, "v3_best_gauge": e.v3_best_gauge,
                     "v3_gauges_consistent": int(e.v3_gauges_consistent), "proposed_class": cls, "class_reason": why, "robustness_notes": "; ".join(marg),
                     "mrms_gaugecorr_hourly_archive": mrms, "mrms_every_probed_date_present": mrms_ok,
                     "gauge_daily_max_basin_idw_mm": float(g.basin_idw_mm.max()) if mx is not None else np.nan, "gauge_daily_max_on": f"{mx:%Y-%m-%d}" if mx is not None else "",
                     "gauge_daily_n_stations_inside_that_day": int(g.loc[mx, "n_stations_inside"]) if mx is not None else np.nan,
                     "gauge_daily_quality_all_days": ", ".join(sorted(set(g.quality.dropna()))), "usgs_15min_rain_gauges_started_by_event": n_rain15})
    return pd.DataFrame(rows)


def build_official_table(ev_tab: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    m = pd.read_csv("reports/phase1d/event_to_fold_mapping.csv")
    o = m[(m.definition == "official_action_25ft") & (m.status == "evaluated")].copy()
    o["t0"] = pd.to_datetime(o.event_start, utc=True)
    rows = []
    for r in o.itertuples():
        parent = ev[(ev.t0 <= r.t0) & (ev.t1 >= pd.to_datetime(r.event_end, utc=True)) | ((ev.t0 <= r.t0) & (ev.t1 >= r.t0))]
        assert len(parent) == 1, (r.event_start, len(parent))
        p = ev_tab[ev_tab.event_start_utc == parent.iloc[0].key].iloc[0]
        rows.append({"official_event_first_reaches_25ft_utc": f"{r.t0:%Y-%m-%d %H:%M}", "peak_ft": r.peak_ft, "nws_stage_reached_by_peak": nws_stage_reached(r.peak_ft), "fold": int(r.fold),
                     "storm_cluster": int(r.storm_cluster), "parent_ge10ft_event_start_utc": parent.iloc[0].key, "provisional_data": p.provisional_data,
                     "upstream_gauges_recorded_in_v3_window": p.upstream_gauges_recorded_in_v3_window, "gauges_dropout_lt80pct": p.gauges_dropout_lt80pct,
                     "parent_class": p.proposed_class, "parent_v2_lead_h": p.v2_best_first_rise_lead_h, "parent_v3_lead_h": p.v3_best_first_rise_lead_h, "mrms_gaugecorr_hourly_archive": p.mrms_gaugecorr_hourly_archive,
                     "gauge_daily_max_basin_idw_mm": p.gauge_daily_max_basin_idw_mm})
    return pd.DataFrame(rows)


def build_travel_table() -> pd.DataFrame:
    t = pd.read_csv("reports/upstream_feasibility/tables/upstream_gauge_lead_summary_with_river_distance.csv", dtype={"site": str})
    target_area = 1315.0   # USGS drainage area of 08167500 as listed in docs/UPSTREAM_INPUT_FEASIBILITY.md section 1
    out = pd.DataFrame({"site": t.site, "gauge": t.site.map(SHORT), "drainage_sqmi": t.drain_area_sqmi, "river_km_above_08167500": t.river_km_upstream_of_08167500,
                        "events_with_consistent_two_timings": t.responds_and_two_timings_agree, "median_first_rise_lead_h": t.median_first_rise_lead_h, "min_first_rise_lead_h": t.min_first_rise_lead_h,
                        "max_first_rise_lead_h": t.max_first_rise_lead_h, "implied_speed_m_per_s_from_median": t.implied_wave_speed_m_per_s})
    out["drainage_share_of_target_pct (=area/1315)"] = (100 * out.drainage_sqmi / target_area).round(1)
    out["area_below_gauge_sqmi (=1315-area)"] = (target_area - out.drainage_sqmi).round(0)
    for v in (2.0, 3.0):   # illustrative arithmetic only: hours = km / (v m/s * 3.6); NOT an estimate for any storm
        out[f"travel_h_at_{v:.0f}_m_per_s (=km/({v:.0f}*3.6))"] = (out.river_km_above_08167500 / (v * 3.6)).round(1)
    return out


def build_fold_table(ev_tab: pd.DataFrame) -> pd.DataFrame:
    f = pd.read_csv("reports/phase1d/fold_specification.csv")
    first_mrms = None
    pr = TAB / "mrms_archive_probe.csv"
    if pr.exists():
        p = pd.read_csv(pr, parse_dates=["date"])
        fin = p[(p.kind == "bisection_final") & (p.gaugecorr_hourly_files > 0)]
        first_mrms = fin.date.min() if len(fin) else None
    rows = []
    for r in f.itertuples():
        tr_end, va_end = pd.Timestamp(r.train_end).tz_convert(None), pd.Timestamp(r.val_end).tz_convert(None)
        va_start = pd.Timestamp(r.val_start).tz_convert(None)
        mr_train = max(0.0, (tr_end - first_mrms).days / 365.25) if first_mrms is not None else np.nan
        mr_val = max(0.0, (va_end - max(va_start, first_mrms)).days / 365.25) if first_mrms is not None else np.nan
        sub = ev_tab[ev_tab.fold == r.fold]
        rows.append({"fold": int(r.fold), "train_period_utc": f"{pd.Timestamp(r.train_start):%Y-%m-%d} to {pd.Timestamp(r.train_end):%Y-%m-%d}", "validation_period_utc": f"{va_start:%Y-%m-%d} to {va_end:%Y-%m-%d}",
                     "test_block_utc": f"{pd.Timestamp(r.test_start):%Y-%m-%d} to {pd.Timestamp(r.test_end):%Y-%m-%d}",
                     "years_of_hourly_mrms_in_training (=(train_end-first_date)/365.25)": round(mr_train, 2), "years_of_hourly_mrms_in_validation": round(mr_val, 2),
                     "evaluated_ge10ft_events": len(sub), "upstream_led": int((sub.proposed_class == "upstream-led").sum()), "local_or_downstream_led": int((sub.proposed_class == "local-or-downstream-led").sum()),
                     "ambiguous": int((sub.proposed_class == "ambiguous").sum()), "storm_clusters": int(sub.storm_cluster.nunique())})
    return pd.DataFrame(rows)


def build_source_matrix() -> pd.DataFrame:
    cat = pd.read_csv("data/raw/upstream/upstream_series_catalog.csv", dtype={"site_no": str})
    uv = cat[cat.data_type_cd == "uv"]
    q = uv[uv.parm_cd == 60].groupby("site_no").begin_date.min()
    st = uv[uv.parm_cd == 65].groupby("site_no").begin_date.min()
    rn = uv[uv.parm_cd == 45].groupby("site_no").begin_date.min()
    seven = ["08165300", "08165500", "08166000", "08166140", "08166200", "08166250", "08167000"]
    f = lambda s, sites: "; ".join(f"{SHORT[x]} {s[x]}" for x in sites if x in s.index)  # noqa: E731
    return pd.DataFrame([
        ["USGS NWIS 15-min stage, target 08167500", "stage (ft)", "15 min", f"{st['08167500']} onward (series catalogue)", "not measured here", "public, no login", "IN USE (primary target and inputs); 2026 values provisional"],
        ["USGS NWIS 15-min stage, 7 long-record upstream gauges", "stage (ft)", "15 min", "from " + f(st, seven), "not measured here; archived record is post-processed, not as-received telemetry (not verified)", "public, no login",
         "event windows cached only (data/raw/upstream/iv); full-record download not done"],
        ["USGS NWIS 15-min stage, Bergheim 08167200", "stage (ft)", "15 min", f"from {st['08167200']}", "not measured here", "public, no login", "event windows cached only; absent for events before 2016-10-26"],
        ["USGS NWIS 15-min discharge, 8 upstream gauges", "discharge (cfs)", "15 min", "from " + f(q, SITES), "not measured here", "public, no login", "listed in the catalogue; NOT downloaded; rating shifts and provisional status not checked"],
        ["USGS 15-min rain gauges inside the basin", "precipitation", "15 min", "from " + f(rn[rn <= '2025-12-31'], ["08165500", "08166000"]) + " (other sites 2026-07-25 on)", "not measured here", "public, no login", "too short: 2 to 4 of the 18 evaluated events; not downloaded"],
        ["NOAA GHCN-Daily gauge basin product (built here)", "daily rainfall (mm)", "daily (observation day ending about 12-14 UTC)", "2007-10-02 to 2026-11-15 (6,985 days)", "usable only from 15:00 UTC on the observation day (project causality rule)", "public",
         "BUILT (reports/gauge_rainfall); no sub-daily timing, so it is not a storm-onset signal"],
        ["ERA5 hourly via Open-Meteo", "hourly rainfall", "hourly, about 0.25 degree", "whole record", "retrospective (days)", "public, non-commercial free tier", "HAVE; about 8% of gauge basin rainfall on 2015-05-24 and 2016-05-29; not a reliable flood-rainfall input"],
        ["MRMS GaugeCorr_QPE_01H (hourly), Iowa State archive", "hourly radar+gauge QPE", "hourly (24 files per UTC day where present)", "first date probed in mrms_archive_probe.csv (bisection); continuity after that NOT verified", "retrospective; real-time latency of the gauge-corrected product not verified", "public, no login",
         "listing verified for the probed dates; NOT downloaded; file format, units and accuracy NOT validated"],
        ["MRMS on AWS (noaa-mrms-pds)", "radar QPE", "2-min / hourly", "listing starts 2020-10-14 (docs/UPSTREAM_INPUT_FEASIBILITY.md section 3)", "not measured", "public", "5 of 18 events only; not downloaded"],
        ["HRRR on AWS (noaa-hrrr-bdp-pds)", "model analysis/forecast rainfall", "hourly", "starts 2014-07-30 (feasibility doc)", "not measured", "public", "model product, not observation; skill for these storms unassessed; not downloaded"],
        ["NLDAS-2 hourly forcing (NASA GES DISC)", "hourly forcing incl. precipitation", "hourly, 1/8 degree", "catalogue to 2026 per feasibility doc; precipitation provenance NOT verified", "retrospective", "needs an Earthdata login the USER places in ~/.netrc (credentials are never requested in chat)", "NOT configured; not downloaded"],
        ["Stage IV radar+gauge QPE", "hourly QPE", "hourly", "NOT verified", "not verified", "not verified", "UNVERIFIED in feasibility doc; verify before any use"],
        ["Hourly ASOS/airport stations (NCEI global-hourly)", "hourly precipitation", "hourly", "8 stations in or near the area for 2015 (feasibility doc)", "not measured", "public", "sparse; precipitation quality untested; not downloaded"],
        ["NLDI flowlines and site navigation", "river geometry, upstream sites", "n/a", "cached 2026-11-22 (data/raw/upstream/nldi_*.json)", "n/a", "public", "IN USE for river distances (main stem); sub-basin polygons NOT fetched"],
    ], columns=["source", "variable", "resolution", "period (as verified)", "latency", "access", "status in this project"])


def md(df: pd.DataFrame, name: str) -> None:
    df.to_csv(TAB / f"{name}.csv", index=False)
    (TAB / f"{name}.md").write_text(df.to_markdown(index=False, floatfmt=".2f") + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="run the one-time network probe of public archive directory listings")
    args = ap.parse_args()
    TAB.mkdir(parents=True, exist_ok=True)
    ev = load_events()
    if args.probe:
        probe_mrms(ev)
    cov = gauge_coverage_long(ev)
    md(cov, "S6_gauge_coverage_per_event_long")
    tab = build_event_table(ev, cov)
    md(tab, "S1_event_availability_18")
    md(build_official_table(tab, ev), "S1b_official_events_6")
    md(build_source_matrix(), "S2_data_source_matrix")
    md(build_travel_table(), "S3_travel_time")
    cls = tab.groupby("proposed_class").agg(events=("peak_ft", "size"), storm_clusters=("storm_cluster", "nunique"), official_peak_ge25ft=("peak_ft", lambda x: int((x >= 25).sum())),
                                           provisional=("provisional_data", "sum")).reset_index()
    md(cls, "S4_class_counts")
    md(build_fold_table(tab), "S5_fold_data_availability")
    # consistency check against the existing v3 table: events with at least one dropout/no-data gauge versus its stored count
    chk = tab.merge(pd.read_csv("reports/upstream_feasibility/tables/upstream_event_level_lead_v3.csv")[["event_start", "v3_gauges_with_insufficient_coverage"]], left_on="event_start_utc", right_on="event_start")
    n_dropout = chk.gauges_dropout_lt80pct.apply(lambda s: len([x for x in s.split(", ") if x]))
    md(pd.DataFrame({"event_start_utc": chk.event_start_utc, "dropout_gauges_recomputed": n_dropout, "v3_gauges_with_insufficient_coverage_stored": chk.v3_gauges_with_insufficient_coverage}), "S7_consistency_check_vs_v3")
    print(tab[["event_start_utc", "peak_ft", "fold", "proposed_class", "upstream_gauges_recorded_in_v3_window", "gauges_dropout_lt80pct"]].to_string(index=False))
    print(cls.to_string(index=False))


if __name__ == "__main__":
    main()
