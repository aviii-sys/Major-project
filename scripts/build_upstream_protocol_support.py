"""Descriptive supporting tables for docs/UPSTREAM_INPUT_PROTOCOL.md (documentation only: no model, no training, no forecasting evaluation).

Reads existing project files (event-to-fold mapping, Phase 1E per-event table, upstream feasibility tables, cached upstream gauge series, daily gauge-rainfall product,
series catalogue) plus two small cached public-service availability probes written by `--probe` (MRMS archive directory listings) and `--probe-nwis` (re-query of gauge-events
that have no cached file).  Nothing in the existing feasibility tables is modified: corrections are written as NEW tables in reports/upstream_protocol_support/.

Usage (from the project root, system python lacks pandas):
    .venv/bin/python scripts/build_upstream_protocol_support.py                          # offline: uses the cached probe files
    .venv/bin/python scripts/build_upstream_protocol_support.py --probe --probe-nwis     # one-time public-service probes (index pages / gauge series; no personal data sent)
"""
import argparse
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
OUT = Path("reports/upstream_protocol_support")
TAB = OUT / "tables"
IV = Path("data/raw/upstream/iv")
IV_REQ = Path("data/raw/upstream/iv_requery")        # NEW folder: series re-queried for gauge-events missing from the original cache (original cache untouched)
SITES = ["08165300", "08165500", "08166000", "08166140", "08166200", "08166250", "08167000", "08167200"]   # same order as scripts/assess_upstream_inputs.py
SHORT = {"08165300": "N Fk Hunt", "08165500": "Hunt", "08166000": "Johnson Ck", "08166140": "Kerrville abv Bear", "08166200": "Kerrville", "08166250": "Center Point",
         "08167000": "Comfort", "08167200": "Bergheim"}
MRMS_BASE = "https://mtarchive.geol.iastate.edu"
PRODUCTS = ("GaugeCorr_QPE_01H", "MultiSensor_QPE_01H_Pass2")   # earlier and later name of the hourly radar+gauge product in the archive (names read from directory listings)
LONG_LEAD_H, NONE_LEAD_H = 6.0, 1.0      # pre-specified class thresholds (docs/UPSTREAM_INPUT_PROTOCOL.md section 3.6); same bands as scripts/upstream_anchored_v3.py
COV_MIN = 0.8                            # same coverage rule as rise_timing() in scripts/assess_upstream_inputs.py


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


def to_15min_grid(s: pd.Series) -> pd.Series:
    """Keep only readings stamped exactly on a 15-min mark (:00 :15 :30 :45), one per stamp. Native 15-min series are unchanged; 5-min series lose two of every three readings.
    No averaging and no interpolation: a value is the instantaneous reading at that mark."""
    s = s[~s.index.duplicated(keep="first")]
    return s[(s.index.minute % 15 == 0) & (s.index.second == 0)]


def window_coverage(s: pd.Series, lo, hi) -> float:
    """Same definition as rise_timing(): non-missing samples in [lo, hi] divided by the number of 15-min intervals in the window (only meaningful on a 15-min grid)."""
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


def gauge_status(cov: float, source: str, record_started: bool) -> str:
    """not installed: the window ends before the gauge's stage record begins (series catalogue); no data: nothing in the cache or the re-query; dropout: < 80% of the window's 15-min marks."""
    if not record_started:
        return "not installed (record starts later)"
    if source == "none":
        return "no data (cache and re-query)"
    return "recorded" if cov >= COV_MIN else "dropout (<80% coverage)"


def lead_summary(leads_consistent: list) -> tuple:
    """(best lead in hours or NaN, index of the gauge giving it) from the leads of the gauges that respond consistently."""
    if not leads_consistent:
        return np.nan, -1
    i = int(np.argmax(leads_consistent))
    return float(leads_consistent[i]), i


# ------------------------------------------------------------------ public-service probes
def probe_mrms(events: pd.DataFrame) -> None:
    """Directory-listing probe of a public archive: GET requests for index pages only (no personal data, generic client name)."""
    import re

    import requests

    sess = requests.Session()
    sess.headers["User-Agent"] = "research-availability-check"
    rows = []

    def listing(url):
        for attempt in range(3):
            try:
                r = sess.get(url, timeout=40)
                time.sleep(0.3)
                return r.status_code, (r.text if r.status_code == 200 else "")
            except requests.RequestException:
                time.sleep(2 * (attempt + 1))
        return -1, ""

    def hourly(day: pd.Timestamp) -> tuple:
        code = -1
        for prod in PRODUCTS:
            code, txt = listing(f"{MRMS_BASE}/{day:%Y/%m/%d}/mrms/ncep/{prod}/")
            if code == 200:
                names = set(re.findall(rf"{prod}_00\.00_\d{{8}}-\d{{6}}\.grib2", txt))
                if names:
                    return prod, len(names), code
        return "", 0, code

    # (1) first date of GaugeCorr_QPE_01H: bisection between 2015-04-01 (no product in a manual probe) and 2015-05-16 (product present); assumes it stays present once present (NOT verified)
    lo, hi = pd.Timestamp("2015-04-01"), pd.Timestamp("2015-05-16")
    assert hourly(lo)[1] == 0 and hourly(hi)[1] > 0
    while (hi - lo).days > 1:
        mid = lo + (hi - lo) // 2
        prod, n, code = hourly(mid)
        rows.append({"kind": "bisection", "date": f"{mid:%Y-%m-%d}", "http": code, "product": prod, "hourly_files": n, "toplevel_folders": ""})
        lo, hi = (mid, hi) if n == 0 else (lo, mid)
    for d in (lo, hi):
        prod, n, code = hourly(d)
        rows.append({"kind": "bisection_final", "date": f"{d:%Y-%m-%d}", "http": code, "product": prod, "hourly_files": n, "toplevel_folders": ""})
    # (2) every UTC date from the day before the event start (rain precedes the rise) to the event-end date, for each evaluated >= 10 ft event
    seen = set()
    for e in events.itertuples():
        t0, tp = pd.Timestamp(e.t0).tz_localize(None).normalize(), pd.Timestamp(e.t_end).tz_localize(None).normalize()
        for d in pd.date_range(t0 - pd.Timedelta("1D"), tp):
            if d in seen:
                continue
            seen.add(d)
            prod, n, code = hourly(d)
            folders = ""
            if n == 0:
                c2, txt = listing(f"{MRMS_BASE}/{d:%Y/%m/%d}/")
                folders = " ".join(sorted(set(re.findall(r'href="([a-z0-9_]+)/"', txt)))) if c2 == 200 else f"listing http {c2}"
            rows.append({"kind": "event_date", "date": f"{d:%Y-%m-%d}", "http": code, "product": prod, "hourly_files": n, "toplevel_folders": folders})
    pd.DataFrame(rows).to_csv(TAB / "mrms_archive_probe.csv", index=False)


def _requery_path(site: str, e) -> Path:
    lo_v2, hi_v2 = e.t0 - pd.Timedelta("36h"), e.t1 + pd.Timedelta("18h")
    return IV_REQ / f"{site}_{(lo_v2 - pd.Timedelta('24h')):%Y%m%d}_{(hi_v2 + pd.Timedelta('12h')):%Y%m%d}.csv"


def probe_nwis_gaps(ev: pd.DataFrame, cat_start: dict) -> None:
    """Re-query NWIS (public, no login) for gauge-events whose original cache holds no file although the gauge's record had begun; save into the NEW folder IV_REQ."""
    from dataretrieval import nwis

    IV_REQ.mkdir(parents=True, exist_ok=True)
    rows = []
    for e in ev.itertuples():
        lo_v2, hi_v2 = e.t0 - pd.Timedelta("36h"), e.t1 + pd.Timedelta("18h")
        for site in SITES:
            orig = IV / f"{site}_{(lo_v2 - pd.Timedelta('24h')):%Y%m%d}_{(hi_v2 + pd.Timedelta('12h')):%Y%m%d}.csv"
            if orig.exists() or (e.t0 + pd.Timedelta("3h")) < cat_start[site]:
                continue
            a, b = lo_v2 - pd.Timedelta("24h"), hi_v2 + pd.Timedelta("12h")
            rec = {"event_start": e.key, "site": site, "gauge": SHORT[site], "requested_from": f"{a:%Y-%m-%d}", "requested_to": f"{b:%Y-%m-%d}"}
            try:
                for attempt in range(4):   # the service timed out once in a first attempt; retry before recording an error
                    try:
                        d, _ = nwis.get_iv(sites=site, start=str(a.date()), end=str(b.date()), parameterCd="00065")
                        break
                    except Exception:   # noqa: BLE001
                        if attempt == 3:
                            raise
                        time.sleep(5 * (attempt + 1))
                cols = [c for c in d.columns if str(c).startswith("00065") and not str(c).endswith("_cd")]
                s = d[cols[0]].copy() if len(cols) else pd.Series(dtype=float)
                s.index = pd.to_datetime(s.index, utc=True)
                s.rename("00065").to_frame().to_csv(_requery_path(site, e))
                step = s.index.to_series().diff().dropna().median() if len(s) > 2 else pd.NaT
                rec.update({"error": "", "rows": len(s), "median_step": str(step), "first": str(s.index.min()), "last": str(s.index.max())})
            except Exception as ex:   # noqa: BLE001 - recorded, not hidden
                rec.update({"error": f"{type(ex).__name__}: {str(ex)[:120]}", "rows": 0})
            rows.append(rec)
    pd.DataFrame(rows).to_csv(TAB / "S6b_nwis_requery_of_missing_cache.csv", index=False)


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
    m = m.merge(v2[["event_start", "best_first_rise_lead_h", "best_gauge"]].rename(columns={"event_start": "k2"}), left_on="key", right_on="k2", how="left")
    m = m.merge(v3[["event_start", "v3_gauges_consistent", "v3_best_first_rise_lead_h", "v3_best_gauge", "v3_gauges_with_insufficient_coverage"]].rename(columns={"event_start": "k3"}), left_on="key", right_on="k3", how="left")
    assert m.v3_gauges_consistent.notna().all()
    m["t_end"] = m.t1      # window end for the availability checks: the catalogue event end (the peak time is not stored in the mapping file)
    return m.sort_values("t0").reset_index(drop=True)


def catalog_start() -> dict:
    cat = pd.read_csv("data/raw/upstream/upstream_series_catalog.csv", dtype={"site_no": str})
    st = cat[(cat.data_type_cd == "uv") & (cat.parm_cd == 65)].groupby("site_no").begin_date.min()
    return {k: pd.Timestamp(v, tz="UTC") for k, v in st.items()}


def load_gauge(site: str, e) -> tuple:
    """(series on the 15-min grid, source in {cache, requery, none}, native median step)."""
    lo_v2, hi_v2 = e.t0 - pd.Timedelta("36h"), e.t1 + pd.Timedelta("18h")
    f = IV / f"{site}_{(lo_v2 - pd.Timedelta('24h')):%Y%m%d}_{(hi_v2 + pd.Timedelta('12h')):%Y%m%d}.csv"
    src = "cache"
    if not f.exists():
        f, src = _requery_path(site, e), "requery"
        if not f.exists():
            return pd.Series(dtype=float), "none", pd.NaT
    d = pd.read_csv(f, index_col=0, parse_dates=True)
    if "00065" not in d.columns or len(d) == 0:
        return pd.Series(dtype=float), "none", pd.NaT
    s = d["00065"]
    s.index = pd.to_datetime(s.index, utc=True)
    step = s.index.to_series().diff().dropna().median() if len(s) > 2 else pd.NaT
    return to_15min_grid(s), src, step


def recompute_timing(ev: pd.DataFrame) -> tuple:
    """Re-run the v2 and v3 timing rules (same code, same triggers, same consistency rule) on the 15-min grid, adding the gauge-events recovered by the re-query.
    Returns (per gauge-event table, per event table)."""
    import sys

    sys.path.insert(0, "scripts")
    from assess_upstream_inputs import rise_timing   # the original function, unchanged
    from flashflood import experiment

    ctx = experiment.build_context()
    start = catalog_start()
    g_rows, e_rows = [], []
    for e in ev.itertuples():
        lo2, hi2 = e.t0 - pd.Timedelta("36h"), e.t1 + pd.Timedelta("18h")
        lo3, hi3 = e.t0 - pd.Timedelta("48h"), e.t0 + pd.Timedelta("3h")
        sb2 = rise_timing(ctx.s, lo2, hi2)
        sb3 = rise_timing(ctx.s, e.t0 - pd.Timedelta("12h"), e.t0 + pd.Timedelta("3h"))
        l2, l3, n2, n3, rec3, drop3, noi3, nodata3 = [], [], [], [], [], [], [], []
        for site in SITES:
            s, src, step = load_gauge(site, e)
            started = bool(hi3 >= start[site])
            cov3 = window_coverage(s, lo3, hi3) if len(s) else 0.0
            st = gauge_status(cov3, src, started)
            {"recorded": rec3, "not installed (record starts later)": noi3, "no data (cache and re-query)": nodata3}.get(st, drop3).append(SHORT[site])
            r2 = rise_timing(s, lo2, hi2) if len(s) else {"status": "no data"}
            r3 = rise_timing(s, lo3, hi3) if len(s) else {"status": "no data"}
            row = {"event_start": e.key, "site": site, "gauge": SHORT[site], "source": src, "native_median_step": str(step), "coverage_v3_window_15min_grid": cov3 if len(s) else np.nan,
                   "longest_gap_h_v3_window": longest_gap_hours(s, lo3, hi3) if len(s) else np.nan, "status_v3_window": st, "v2c_status": r2["status"], "v3c_status": r3["status"]}
            if sb2["status"] == "responds" and r2["status"] == "responds":
                lf, ls = (sb2["t_first"] - r2["t_first"]) / pd.Timedelta("1h"), (sb2["t_steep"] - r2["t_steep"]) / pd.Timedelta("1h")
                row.update({"v2c_first_lead_h": lf, "v2c_consistent": bool(abs(lf - ls) <= 6)})
                if abs(lf - ls) <= 6:
                    l2.append(lf); n2.append(site)
            if sb3["status"] == "responds" and r3["status"] == "responds":
                lf, ls = (sb3["t_first"] - r3["t_first"]) / pd.Timedelta("1h"), (sb3["t_steep"] - r3["t_steep"]) / pd.Timedelta("1h")
                row.update({"v3c_first_lead_h": lf, "v3c_consistent": bool(abs(lf - ls) <= 6)})
                if abs(lf - ls) <= 6:
                    l3.append(lf); n3.append(site)
            g_rows.append(row)
        b2, i2 = lead_summary(l2)
        b3, i3 = lead_summary(l3)
        e_rows.append({"event_start": e.key, "v2c_best_lead_h": b2, "v2c_best_gauge": n2[i2] if i2 >= 0 else "", "v2c_gauges_consistent": len(l2),
                       "v3c_best_lead_h": b3, "v3c_best_gauge": n3[i3] if i3 >= 0 else "", "v3c_gauges_consistent": len(l3),
                       "gauges_recorded": ", ".join(rec3), "gauges_dropout_lt80pct": ", ".join(drop3), "gauges_no_data": ", ".join(nodata3), "gauges_not_installed_yet": ", ".join(noi3)})
    return pd.DataFrame(g_rows), pd.DataFrame(e_rows)


def build_event_table(ev: pd.DataFrame, tm: pd.DataFrame) -> pd.DataFrame:
    cat = pd.read_csv("data/raw/upstream/upstream_series_catalog.csv", dtype={"site_no": str})
    rain15 = cat[(cat.data_type_cd == "uv") & (cat.parm_cd == 45)].groupby("site_no").begin_date.min()
    gd = pd.read_csv("data/processed/gauge_basin_daily.csv", parse_dates=["date"]).set_index("date")
    pe = pd.DataFrame()
    if (TAB / "mrms_archive_probe.csv").exists():
        p = pd.read_csv(TAB / "mrms_archive_probe.csv", parse_dates=["date"])
        pe = p[p.kind == "event_date"].drop_duplicates("date").set_index("date")
    rows = []
    for e in ev.itertuples():
        t = tm[tm.event_start == e.key].iloc[0]
        cls, why = classify_event(t.v2c_best_lead_h, t.v3c_best_lead_h)
        cls_stored, _ = classify_event(e.best_first_rise_lead_h, e.v3_best_first_rise_lead_h)
        days = pd.date_range(e.t0.tz_localize(None).normalize() - pd.Timedelta("1D"), e.t_end.tz_localize(None).normalize())
        g = gd.reindex(days)
        mx = g.basin_idw_mm.idxmax() if g.basin_idw_mm.notna().any() else None
        if len(pe):
            pr = pe.reindex(days)
            n_ok = int((pr.hourly_files.fillna(0) > 0).sum())
            prods = ", ".join(sorted(set(pr["product"].dropna().astype(str)) - {""}))
            mrms = f"{int(pr.hourly_files.fillna(0).sum())} hourly files on {n_ok} of {len(days)} probed UTC dates" + (f" [{prods}]" if prods else "")
            mrms_ok = bool(n_ok == len(days))
        else:
            mrms, mrms_ok = "probe not run", None
        n_rain15 = int((pd.to_datetime(rain15) <= e.t0.tz_localize(None)).sum())
        notes = []
        v2c, v3c = t.v2c_best_lead_h, t.v3c_best_lead_h
        if cls == "upstream-led":
            if t.v3c_gauges_consistent <= 1:
                notes.append("only 1 gauge with a consistent response (v3)")
            if min(v2c, v3c) < LONG_LEAD_H + 1:
                notes.append("lead within 1 h of the 6 h cut-off")
        if (not np.isnan(v2c) and not np.isnan(v3c)) and abs(v3c - v2c) > 6:
            notes.append("v2 and v3 leads differ by > 6 h (multi-pulse storm)")
        if v3c > 30:
            notes.append("v3 lead > 30 h is physically implausible (UPSTREAM_INPUT_FEASIBILITY.md 2c)")
        if cls != cls_stored:
            notes.append(f"class differs from the one implied by the stored tables ({cls_stored}): see S8")
        rows.append({"event_start_utc": e.key, "peak_ft": e.peak_ft, "nws_stage_reached_by_peak": nws_stage_reached(e.peak_ft), "fold": int(e.fold), "storm_cluster": int(e.storm_cluster),
                     "provisional_data": bool(e.provisional_data), "upstream_gauges_recorded_in_v3_window": len([x for x in t.gauges_recorded.split(", ") if x]), "gauges_recorded": t.gauges_recorded,
                     "gauges_dropout_lt80pct": t.gauges_dropout_lt80pct, "gauges_no_data": t.gauges_no_data, "gauges_not_installed_yet": t.gauges_not_installed_yet,
                     "v2_best_lead_h_stored_tables": e.best_first_rise_lead_h, "v3_best_lead_h_stored_tables": e.v3_best_first_rise_lead_h,
                     "v2_best_lead_h_15min_grid": v2c, "v2_best_gauge": t.v2c_best_gauge, "v3_best_lead_h_15min_grid": v3c, "v3_best_gauge": t.v3c_best_gauge, "v3_gauges_consistent": int(t.v3c_gauges_consistent),
                     "proposed_class": cls, "class_reason": why, "class_from_stored_tables": cls_stored, "robustness_notes": "; ".join(notes),
                     "mrms_hourly_qpe_archive": mrms, "mrms_every_probed_date_present": mrms_ok,
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
        parent = ev[(ev.t0 <= r.t0) & (ev.t1 >= r.t0)]
        assert len(parent) == 1, (r.event_start, len(parent))
        p = ev_tab[ev_tab.event_start_utc == parent.iloc[0].key].iloc[0]
        rows.append({"official_event_first_reaches_25ft_utc": f"{r.t0:%Y-%m-%d %H:%M}", "peak_ft": r.peak_ft, "nws_stage_reached_by_peak": nws_stage_reached(r.peak_ft), "fold": int(r.fold),
                     "storm_cluster": int(r.storm_cluster), "parent_ge10ft_event_start_utc": parent.iloc[0].key, "provisional_data": p.provisional_data,
                     "upstream_gauges_recorded_in_v3_window": p.upstream_gauges_recorded_in_v3_window, "gauges_dropout_lt80pct": p.gauges_dropout_lt80pct,
                     "parent_class": p.proposed_class, "parent_v2_lead_h": p.v2_best_lead_h_15min_grid, "parent_v3_lead_h": p.v3_best_lead_h_15min_grid, "mrms_hourly_qpe_archive": p.mrms_hourly_qpe_archive,
                     "gauge_daily_max_basin_idw_mm": p.gauge_daily_max_basin_idw_mm})
    return pd.DataFrame(rows)


def build_travel_table() -> pd.DataFrame:
    t = pd.read_csv("reports/upstream_feasibility/tables/upstream_gauge_lead_summary_with_river_distance.csv", dtype={"site": str})
    target_area = 1315.0   # USGS drainage area of 08167500 as listed in docs/UPSTREAM_INPUT_FEASIBILITY.md section 1
    out = pd.DataFrame({"site": t.site, "gauge": t.site.map(SHORT), "drainage_sqmi": t.drain_area_sqmi, "river_km_above_08167500": t.river_km_upstream_of_08167500,
                        "events_with_consistent_two_timings (stored v2, 20 events)": t.responds_and_two_timings_agree, "median_first_rise_lead_h": t.median_first_rise_lead_h,
                        "min_first_rise_lead_h": t.min_first_rise_lead_h, "max_first_rise_lead_h": t.max_first_rise_lead_h, "implied_speed_m_per_s_from_median": t.implied_wave_speed_m_per_s})
    out["drainage_share_of_target_pct (=area/1315)"] = (100 * out.drainage_sqmi / target_area).round(1)
    out["area_below_gauge_sqmi (=1315-area)"] = (target_area - out.drainage_sqmi).round(0)
    for v in (2.0, 3.0):   # illustrative arithmetic only: hours = km / (v m/s * 3.6); NOT an estimate for any storm
        out[f"travel_h_at_{v:.0f}_m_per_s (=km/({v:.0f}*3.6))"] = (out.river_km_above_08167500 / (v * 3.6)).round(1)
    return out


def build_fold_table(ev_tab: pd.DataFrame) -> pd.DataFrame:
    f = pd.read_csv("reports/phase1d/fold_specification.csv")
    first_mrms = None
    if (TAB / "mrms_archive_probe.csv").exists():
        p = pd.read_csv(TAB / "mrms_archive_probe.csv", parse_dates=["date"])
        fin = p[(p.kind == "bisection_final") & (p["product"] == "GaugeCorr_QPE_01H") & (p.hourly_files > 0)]
        first_mrms = fin.date.min() if len(fin) else None
    rows = []
    for r in f.itertuples():
        tr_end, va_start, va_end = pd.Timestamp(r.train_end).tz_convert(None), pd.Timestamp(r.val_start).tz_convert(None), pd.Timestamp(r.val_end).tz_convert(None)
        mr_train = max(0.0, (tr_end - first_mrms).days / 365.25) if first_mrms is not None else np.nan
        mr_val = max(0.0, (va_end - max(va_start, first_mrms)).days / 365.25) if first_mrms is not None else np.nan
        sub = ev_tab[ev_tab.fold == r.fold]
        rows.append({"fold": int(r.fold), "train_period_utc": f"{pd.Timestamp(r.train_start):%Y-%m-%d} to {pd.Timestamp(r.train_end):%Y-%m-%d}", "validation_period_utc": f"{va_start:%Y-%m-%d} to {va_end:%Y-%m-%d}",
                     "test_block_utc": f"{pd.Timestamp(r.test_start):%Y-%m-%d} to {pd.Timestamp(r.test_end):%Y-%m-%d}",
                     "years_of_hourly_QPE_in_training (=(train_end-first_date)/365.25, floor 0)": round(mr_train, 2), "years_of_hourly_QPE_in_validation": round(mr_val, 2),
                     "evaluated_ge10ft_events": len(sub), "upstream_led": int((sub.proposed_class == "upstream-led").sum()), "local_or_downstream_led": int((sub.proposed_class == "local-or-downstream-led").sum()),
                     "ambiguous": int((sub.proposed_class == "ambiguous").sum()), "storm_clusters": int(sub.storm_cluster.nunique())})
    return pd.DataFrame(rows)


def build_source_matrix(first_mrms_text: str) -> pd.DataFrame:
    cat = pd.read_csv("data/raw/upstream/upstream_series_catalog.csv", dtype={"site_no": str})
    uv = cat[cat.data_type_cd == "uv"]
    q, st, rn = (uv[uv.parm_cd == c].groupby("site_no").begin_date.min() for c in (60, 65, 45))
    seven = ["08165300", "08165500", "08166000", "08166140", "08166200", "08166250", "08167000"]
    f = lambda s, sites: "; ".join(f"{SHORT[x]} {s[x]}" for x in sites if x in s.index)  # noqa: E731
    return pd.DataFrame([
        ["USGS NWIS 15-min stage, target 08167500", "stage (ft)", "15 min", f"{st['08167500']} onward (series catalogue)", "not measured here", "public, no login", "IN USE (primary target and inputs); 2026 values provisional"],
        ["USGS NWIS stage, 7 long-record upstream gauges", "stage (ft)", "15 min until about 2018; 5-min stamps at 6 of 7 gauges in the cached 2019-2026 event files (see README, finding 1)", "from " + f(st, seven), "not measured here; archived record is post-processed, not as-received telemetry (not verified)", "public, no login",
         "event windows cached only (data/raw/upstream/iv); full-record download not done"],
        ["USGS NWIS stage, Bergheim 08167200", "stage (ft)", "15 min (5-min stamps in cached 2026 files)", f"from {st['08167200']}", "not measured here", "public, no login", "event windows cached; absent for events before 2016-10-26"],
        ["USGS NWIS discharge, 8 upstream gauges", "discharge (cfs)", "15 min", "from " + f(q, SITES), "not measured here", "public, no login", "listed in the catalogue; NOT downloaded; rating shifts and provisional status not checked"],
        ["USGS rain gauges inside the basin", "precipitation", "15 min", "from " + f(rn[rn <= "2025-12-31"], ["08165500", "08166000"]) + " (other sites 2026-07-25 on)", "not measured here", "public, no login", "too short: 2 to 4 of the 18 evaluated events; not downloaded"],
        ["NOAA GHCN-Daily gauge basin product (built here)", "daily rainfall (mm)", "daily (observation day ending about 12-14 UTC)", "2007-10-02 to 2026-11-15 (6,985 days)", "usable only from 15:00 UTC on the observation day (project causality rule)", "public",
         "BUILT (reports/gauge_rainfall); no sub-daily timing, so it is not a storm-onset signal"],
        ["ERA5 hourly via Open-Meteo", "hourly rainfall", "hourly, about 0.25 degree", "whole record", "retrospective (days)", "public, non-commercial free tier", "HAVE; about 8% of gauge basin rainfall on 2015-05-24 and 2016-05-29; not a reliable flood-rainfall input"],
        ["MRMS hourly radar+gauge QPE, Iowa State archive (GaugeCorr_QPE_01H, later MultiSensor_QPE_01H_Pass2)", "hourly QPE", "hourly (24 files per UTC day where present)", first_mrms_text, "retrospective; real-time latency of the gauge-corrected product not verified", "public, no login",
         "directory listings verified for the probed dates only; NOT downloaded; format, units, accuracy NOT validated; the product name changes between 2018 and 2021 (algorithm continuity not verified)"],
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
    ap.add_argument("--probe", action="store_true", help="one-time probe of public archive directory listings (MRMS)")
    ap.add_argument("--probe-nwis", action="store_true", help="re-query NWIS for gauge-events with no cached file (public service, no login)")
    args = ap.parse_args()
    TAB.mkdir(parents=True, exist_ok=True)
    ev = load_events()
    if args.probe:
        probe_mrms(ev)
    if args.probe_nwis:
        probe_nwis_gaps(ev, catalog_start())
    g, te = recompute_timing(ev)
    md(g, "S8b_timing_recomputed_per_gauge_event")
    stored = ev[["key", "best_first_rise_lead_h", "v3_best_first_rise_lead_h", "v3_gauges_with_insufficient_coverage"]].rename(columns={"key": "event_start", "best_first_rise_lead_h": "v2_best_lead_h_stored",
                                                                                                                              "v3_best_first_rise_lead_h": "v3_best_lead_h_stored"})
    cmp_ = te.merge(stored, on="event_start")
    cmp_["v2_changed"] = ~np.isclose(cmp_.v2c_best_lead_h.fillna(-999), cmp_.v2_best_lead_h_stored.fillna(-999))
    cmp_["v3_changed"] = ~np.isclose(cmp_.v3c_best_lead_h.fillna(-999), cmp_.v3_best_lead_h_stored.fillna(-999))
    cmp_["dropout_gauges_recomputed"] = cmp_.gauges_dropout_lt80pct.apply(lambda s: len([x for x in s.split(", ") if x]))
    md(cmp_, "S8_timing_recomputed_vs_stored")
    tab = build_event_table(ev, te)
    md(tab, "S1_event_availability_18")
    md(build_official_table(tab, ev), "S1b_official_events_6")
    first = "first date probed in mrms_archive_probe.csv (bisection); continuity after that NOT verified"
    if (TAB / "mrms_archive_probe.csv").exists():
        p = pd.read_csv(TAB / "mrms_archive_probe.csv")
        fin = p[p.kind == "bisection_final"]
        yes, no = fin[fin.hourly_files > 0], fin[fin.hourly_files == 0]
        if len(yes) and len(no):
            first = (f"GaugeCorr_QPE_01H: absent on {no.date.max()}, present on {yes.date.min()} ({int(yes.hourly_files.iloc[0])} hourly files that day; days between not individually probed); "
                     "continuity after that NOT verified; MultiSensor_QPE_01H_Pass2 present on the probed 2021-2026 event dates")
    md(build_source_matrix(first), "S2_data_source_matrix")
    md(build_travel_table(), "S3_travel_time")
    cls = tab.groupby("proposed_class").agg(events=("peak_ft", "size"), storm_clusters=("storm_cluster", "nunique"), peak_ge_25ft=("peak_ft", lambda x: int((x >= 25).sum())),
                                           provisional=("provisional_data", "sum")).reset_index()
    md(cls, "S4_class_counts")
    md(build_fold_table(tab), "S5_fold_data_availability")
    print(tab[["event_start_utc", "peak_ft", "fold", "proposed_class", "class_from_stored_tables", "v2_best_lead_h_15min_grid", "v3_best_lead_h_15min_grid", "gauges_dropout_lt80pct"]].to_string(index=False))
    print(cls.to_string(index=False))


if __name__ == "__main__":
    main()
