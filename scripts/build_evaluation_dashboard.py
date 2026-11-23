"""Build the Faculty Evaluation Dashboard (dashboard/evaluation/index.html) from the project's OWN saved result tables.

Every number shown on the page is read from a table or JSON file listed in `sources` (path + SHA-256 are embedded and displayed in the page's Evidence section).
Narrative numbers come from the `facts` dictionary, which records for each fact its value, source file and how it was derived.
The academic three-phase roadmap is a PROPOSAL: no university phase requirements are documented in the repository.

Usage (project root): PYTHONPATH=src python scripts/build_evaluation_dashboard.py        Output: dashboard/evaluation/index.html (self-contained, offline)
Open:  open dashboard/evaluation/index.html
"""
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from flashflood import folds

warnings.filterwarnings("ignore")
ROOT = Path(".")
DIR = ROOT / "dashboard/evaluation"
HZ = ["15m", "30m", "1h", "3h"]
SOURCES: dict = {}
FACTS: dict = {}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def rd(rel: str) -> pd.DataFrame:
    p = ROOT / rel
    SOURCES[rel] = sha(p)
    return pd.read_csv(p)


def rj(rel: str):
    p = ROOT / rel
    SOURCES[rel] = sha(p)
    return json.loads(p.read_text())


def fact(key, value, source, how=""):
    FACTS[key] = {"value": value, "source": source, "how": how}
    return value


def rows(df: pd.DataFrame, cols=None, nd=8) -> list:
    d = df[cols] if cols else df
    out = []
    for r in d.itertuples(index=False):
        rec = {}
        for c, v in zip(d.columns, r):
            if isinstance(v, (float, np.floating)):
                rec[c] = None if not np.isfinite(v) else round(float(v), nd)
            elif isinstance(v, (np.integer,)):
                rec[c] = int(v)
            elif isinstance(v, (np.bool_,)):
                rec[c] = bool(v)
            else:
                rec[c] = v if not (isinstance(v, float) and np.isnan(v)) else None
        out.append(rec)
    return out


def exists(rel: str) -> str:
    assert (ROOT / rel).exists(), f"missing evidence file {rel}"
    return rel


def lines_of_code(folder: str) -> int:
    return sum(len(p.read_text().splitlines()) for p in (ROOT / folder).rglob("*.py") if "__pycache__" not in str(p))


def run_tests() -> dict:
    """Run the existing test suite (excluding this dashboard's own test to avoid recursion) and record the outcome at build time."""
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--ignore=tests/test_evaluation_dashboard.py", "-p", "no:cacheprovider"], capture_output=True, text=True, cwd=ROOT)
    m = re.search(r"(\d+) passed", r.stdout)
    f = re.search(r"(\d+) failed", r.stdout)
    per_file = {}
    c = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "--ignore=tests/test_evaluation_dashboard.py", "-p", "no:cacheprovider"], capture_output=True, text=True, cwd=ROOT)
    for line in c.stdout.splitlines():
        if "::" in line:
            per_file[line.split("::")[0].replace("tests/", "")] = per_file.get(line.split("::")[0].replace("tests/", ""), 0) + 1
    return {"passed": int(m.group(1)) if m else 0, "failed": int(f.group(1)) if f else 0, "per_file": per_file, "ran_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M")}


def main() -> None:
    # ------------------------------------------------------------------ Phase 0 (data audit)
    p0 = rj("reports/phase0/phase0_results.json")
    fact("p0.rows", p0["hydro"]["rows_raw"], "reports/phase0/phase0_results.json", "hydro.rows_raw")
    fact("p0.first", p0["hydro"]["first"][:10], "reports/phase0/phase0_results.json", "hydro.first")
    fact("p0.last", p0["hydro"]["last"][:10], "reports/phase0/phase0_results.json", "hydro.last")
    fact("p0.completeness_pct", round(100 * (1 - p0["hydro"]["stage_missing"] / p0["hydro"]["expected_15min_steps"]), 2), "reports/phase0/phase0_results.json", "100 x (1 - stage_missing / expected_15min_steps)")
    fact("p0.max_stage_ft", p0["hydro"]["stage_ft"]["max"], "reports/phase0/phase0_results.json", "hydro.stage_ft.max")
    fact("p0.official_events", p0["events"]["n_events_action"], "reports/phase0/phase0_results.json", "events.n_events_action (stage >= 25 ft)")
    thr = rd("reports/phase0/tables/event_counts_by_threshold.csv")
    fact("p0.official_storms", int(thr[thr.threshold_ft == 25].events_sep72h.iloc[0]), "reports/phase0/tables/event_counts_by_threshold.csv", "threshold 25 ft, events merged within 72 h")
    fact("p0.events_ge10_24h", int(thr[thr.threshold_ft == 10].events_sep24h.iloc[0]), "reports/phase0/tables/event_counts_by_threshold.csv", "threshold 10 ft, events merged within 24 h")
    fact("p0.old_threshold_above_pct", 50.9, "reports/phase0/PHASE0_REPORT.md", "headline finding 3: the earlier 2.175 ft threshold is exceeded in 50.9% of rows")

    # ------------------------------------------------------------------ Phase 1D (cross-validated comparison, primary evidence)
    d1 = rd("reports/phase1d/tables/D1_pooled_regression_metrics.csv")
    d3 = rd("reports/phase1d/tables/D3_paired_model_differences.csv")
    d5 = rd("reports/phase1d/tables/D5_fixed_rule_detection_pooled_oof.csv")
    d6 = rd("reports/phase1d/tables/D6_event_coverage_and_exclusions.csv")
    mapping = rd("reports/phase1d/event_to_fold_mapping.csv")
    spec = rd("reports/phase1d/fold_specification.csv")
    fl = d1[d1.subset == "event_windows_stage10ft"]
    fact("p1d.flood_rows", int(fl.n_rows.iloc[0]), "reports/phase1d/tables/D1_pooled_regression_metrics.csv", "n_rows of subset event_windows_stage10ft")
    fact("p1d.flood_groups", int(fl.n_storm_groups.iloc[0]), "reports/phase1d/tables/D1_pooled_regression_metrics.csv", "n_storm_groups of subset event_windows_stage10ft")
    fact("p1d.all_rows_1h", int(d1[(d1.subset == "all") & (d1.horizon == "1h")].n_rows.iloc[0]), "reports/phase1d/tables/D1_pooled_regression_metrics.csv", "n_rows, subset all, 1 h")
    ev10 = d6[(d6.definition == "experimental_stage_10ft")]
    fact("p1d.events_evaluated", int(ev10[ev10.status == "evaluated"].events.iloc[0]), "reports/phase1d/tables/D6_event_coverage_and_exclusions.csv", "experimental_stage_10ft evaluated")
    fact("p1d.clusters_evaluated", int(ev10[ev10.status == "evaluated"].storm_clusters.iloc[0]), "reports/phase1d/tables/D6_event_coverage_and_exclusions.csv", "experimental_stage_10ft evaluated storm clusters")
    fact("p1d.events_excluded", int(ev10[ev10.status == "excluded"].events.iloc[0]), "reports/phase1d/tables/D6_event_coverage_and_exclusions.csv", "experimental_stage_10ft excluded (initial training segment)")
    off = d6[d6.definition == "official_action_25ft"]
    fact("p1d.official_evaluated", int(off.events.iloc[0]), "reports/phase1d/tables/D6_event_coverage_and_exclusions.csv", "official_action_25ft evaluated")
    fact("p1d.official_clusters", int(off.storm_clusters.iloc[0]), "reports/phase1d/tables/D6_event_coverage_and_exclusions.csv", "official_action_25ft storm clusters")
    fact("p1d.folds", int(len(spec)), "reports/phase1d/fold_specification.csv", "number of folds")
    mins = int(folds.EMBARGO / pd.Timedelta("1min"))
    fact("p1d.embargo_text", f"{mins // 60} h {mins % 60} min", "src/flashflood/folds.py", "EMBARGO = window + largest horizon + one 15-minute step")
    gru_r3 = d3[(d3.subset == "event_windows_stage10ft") & (d3.model == "gru") & (d3.reference == "ridge_H")].set_index("horizon")
    fact("p1d.gru_minus_ridge_15m_ft", round(float(gru_r3.loc["15m", "rmse_diff_ft"]), 3), "reports/phase1d/tables/D3_paired_model_differences.csv", "flood windows, gru minus ridge_H, 15 m (positive = GRU worse)")
    fact("p1d.gru_minus_ridge_15m_sig", bool(gru_r3.loc["15m", "interval_excludes_zero"]), "reports/phase1d/tables/D3_paired_model_differences.csv", "interval excludes zero")
    det = d5[(d5.definition == "experimental_rise_4ft_3h") & (d5.horizon == "3h")].set_index("model")
    for m in ("ridge_H", "trend_v2", "gru", "lstm", "xgb_H", "persistence"):
        fact(f"p1d.rise4_3h_hits.{m}", int(det.loc[m, "early_hits"]), "reports/phase1d/tables/D5_fixed_rule_detection_pooled_oof.csv", f"early_hits, rise >= 4 ft in 3 h, 3 h horizon, {m}")
    fact("p1d.rise4_events", int(det.loc["gru", "n_events"]), "reports/phase1d/tables/D5_fixed_rule_detection_pooled_oof.csv", "n_events of the rise >= 4 ft in 3 h definition")
    fact("p1d.rise4_clusters", int(det.loc["gru", "storm_clusters"]), "reports/phase1d/tables/D5_fixed_rule_detection_pooled_oof.csv", "storm_clusters of the rise >= 4 ft in 3 h definition")

    # ------------------------------------------------------------------ Phase 1C (single split, includes the Transformer)
    c1 = rd("reports/phase1c/tables/C1_regression_metrics.csv")
    c1 = c1[c1.protocol == "chrono_test"]
    c5 = rd("reports/phase1c/tables/C5_training_diagnostics.csv")
    c2b = rd("reports/phase1c/tables/C2b_posthoc_vs_ridge_and_trend.csv")
    tr = c5[(c5.arch == "transformer") & (c5.chosen_for_primary)]
    fact("p1c.transformer_best_epoch_min", int(tr.best_epoch.min()), "reports/phase1c/tables/C5_training_diagnostics.csv", "transformer hidden 64 runs, best_epoch min")
    fact("p1c.transformer_best_epoch_max", int(tr.best_epoch.max()), "reports/phase1c/tables/C5_training_diagnostics.csv", "transformer hidden 64 runs, best_epoch max")
    fact("p1c.transformer_val_loss_min", round(float(tr.best_val_scaled_loss.min()), 3), "reports/phase1c/tables/C5_training_diagnostics.csv", "transformer best_val_scaled_loss min")
    fact("p1c.transformer_val_loss_max", round(float(tr.best_val_scaled_loss.max()), 3), "reports/phase1c/tables/C5_training_diagnostics.csv", "transformer best_val_scaled_loss max")
    gl = c5[(c5.arch.isin(["gru", "lstm"])) & (c5.chosen_for_primary)]
    fact("p1c.gru_lstm_val_loss_min", round(float(gl.best_val_scaled_loss.min()), 3), "reports/phase1c/tables/C5_training_diagnostics.csv", "GRU/LSTM hidden 64 best_val_scaled_loss min")
    fact("p1c.gru_lstm_val_loss_max", round(float(gl.best_val_scaled_loss.max()), 3), "reports/phase1c/tables/C5_training_diagnostics.csv", "GRU/LSTM hidden 64 best_val_scaled_loss max")
    fact("p1c.seeds", int(c5[c5.arch == "gru"].seed.nunique()), "reports/phase1c/tables/C5_training_diagnostics.csv", "distinct seeds per architecture")
    ftest = c1[c1.subset == "event_windows_stage10ft"]
    c4 = rd("reports/phase1c/tables/C4_per_event_test.csv")
    fact("p1c.test_events", int(c4[c4.definition == "experimental_stage_10ft"].event_start.nunique()), "reports/phase1c/tables/C4_per_event_test.csv", "distinct events of the 10 ft definition in the Phase 1C test period")
    fact("p1c.flood_rows", int(ftest.n_rows.iloc[0]), "reports/phase1c/tables/C1_regression_metrics.csv", "test protocol, flood windows rows")
    fact("p1c.flood_groups", int(ftest.n_groups.iloc[0]), "reports/phase1c/tables/C1_regression_metrics.csv", "test protocol, flood windows bootstrap groups")

    # ------------------------------------------------------------------ Phase 1E (24 h versus 72 h)
    e1b = rd("reports/phase1e/tables/E1b_paired_72_minus_24.csv")
    e3 = rd("reports/phase1e/tables/E3_decision_rule.csv")
    e8 = rd("reports/phase1e/tables/E8_training_diagnostics.csv")
    dec = rj("reports/phase1e/decision.json")
    fact("p1e.adopt_72h", bool(dec["adopt_72h"]), "reports/phase1e/decision.json", "adopt_72h")
    fact("p1e.consistent_horizons", int(dec["horizons_with_consistent_improvement_in_flood_windows"]), "reports/phase1e/decision.json", "horizons_with_consistent_improvement_in_flood_windows")
    med = e8.groupby("window_h").train_seconds.median()
    fact("p1e.median_min_24", round(float(med[24] / 60), 1), "reports/phase1e/tables/E8_training_diagnostics.csv", "median train_seconds / 60, 24 h window")
    fact("p1e.median_min_72", round(float(med[72] / 60), 1), "reports/phase1e/tables/E8_training_diagnostics.csv", "median train_seconds / 60, 72 h window")
    fact("p1e.slowdown", round(float(med[72] / med[24]), 1), "reports/phase1e/tables/E8_training_diagnostics.csv", "ratio of median run times (a 2 h sleep pause inflates the 72 h MEAN, not the median)")
    fact("p1e.seeds", int(e8.seed.nunique()), "reports/phase1e/tables/E8_training_diagnostics.csv", "distinct seeds")
    fact("p1e.runs", int(len(e8)), "reports/phase1e/tables/E8_training_diagnostics.csv", "number of trained models (6 folds x 3 seeds x 2 windows)")
    e1b_all = e1b[e1b.subset == "all"].set_index("horizon")
    e1 = rd("reports/phase1e/tables/E1_pooled_metrics.csv")
    base24 = e1[(e1.subset == "all") & (e1.window_h == "24")].set_index("horizon").rmse_ft_seed_mean
    rel = (e1b_all.diff_72_minus_24_ft / base24.reindex(e1b_all.index) * 100)[e1b_all.interval_excludes_zero]
    fact("p1e.all_rows_worse_pct_min", round(float(rel.min()), 1), "reports/phase1e/tables/E1b_paired_72_minus_24.csv", "min of (72 h minus 24 h) / 24 h RMSE in % over all-row horizons whose interval excludes zero (E1 supplies the 24 h RMSE)")
    fact("p1e.all_rows_worse_pct_max", round(float(rel.max()), 1), "reports/phase1e/tables/E1b_paired_72_minus_24.csv", "max of the same quantity")
    fact("p1e.all_rows_worse_horizons", int(e1b_all.interval_excludes_zero.sum()), "reports/phase1e/tables/E1b_paired_72_minus_24.csv", "horizons where the all-row 72 h minus 24 h interval excludes zero (72 h worse)")

    # ------------------------------------------------------------------ onset timing (E18)
    o3b = rd("reports/phase1e_onset/tables/O3b_median_lead_by_variant.csv")
    o3c = rd("reports/phase1e_onset/tables/O3c_issue_time_of_first_forecast_vs_onset.csv")
    o5 = rd("reports/phase1e_onset/tables/O5_anticipation_summary.csv")
    o3 = rd("reports/phase1e_onset/tables/O3_summary_level_leads.csv")
    g24 = o3b[(o3b.variant == "GRU 24 h (all seeds)") & (o3b.horizon == "3h")].iloc[0]
    fact("onset.lag_f10_3h", round(3 - float(g24.lead_f10_h), 2), "reports/phase1e_onset/tables/O3b_median_lead_by_variant.csv", "3 h minus median lead at 10% of the rise, GRU 24 h")
    fact("onset.lag_f50_3h", round(3 - float(g24.lead_f50_h), 2), "reports/phase1e_onset/tables/O3b_median_lead_by_variant.csv", "3 h minus median lead at 50% of the rise, GRU 24 h")
    fact("onset.lag_f90_3h", round(3 - float(g24.lead_f90_h), 2), "reports/phase1e_onset/tables/O3b_median_lead_by_variant.csv", "3 h minus median lead at 90% of the rise, GRU 24 h")
    half = o3c[(o3c.level == "50% of the rise")]
    fact("onset.half_rise_before_onset_events_max", int(half.events_first_forecast_issued_before_onset_any_seed.max()), "reports/phase1e_onset/tables/O3c_issue_time_of_first_forecast_vs_onset.csv", "max over all variants and horizons of events (of 18) with a forecast of half the rise issued before the onset")
    fact("onset.half_rise_issue_median_h_gru24_3h", float(half[(half.variant == "GRU 24 h") & (half.horizon == "3h")].median_issue_vs_onset_h.iloc[0]), "reports/phase1e_onset/tables/O3c_issue_time_of_first_forecast_vs_onset.csv", "median issue time of the first forecast of half the rise, relative to onset (h)")
    a3 = o5[(o5.horizon == "3h") & (o5.scope == "all 18 events")].set_index("window_h")
    fact("onset.flag_gru24_3h", int(a3.loc["24", "events_flagged_by_all_3_seeds"]), "reports/phase1e_onset/tables/O5_anticipation_summary.csv", "events flagged by all 3 seeds, GRU 24 h, 3 h")
    fact("onset.flag_gru72_3h", int(a3.loc["72", "events_flagged_by_all_3_seeds"]), "reports/phase1e_onset/tables/O5_anticipation_summary.csv", "events flagged by all 3 seeds, GRU 72 h, 3 h")
    fact("onset.flag_trend_3h", int(a3.loc["damped trend", "events_flagged_by_all_3_seeds"]), "reports/phase1e_onset/tables/O5_anticipation_summary.csv", "events flagged, damped trend, 3 h")
    o0 = rd("reports/phase1e_onset/tables/O0_event_reference.csv")
    fact("onset.ambiguous_events", int((o0.onset_to_peak_h > 24).sum()), "reports/phase1e_onset/tables/O0_event_reference.csv", "events whose rise onset to peak exceeds 24 h (slow multi-stage rise, onset ambiguous)")
    od = o3[(o3.metric.isin(["lead_f10_h", "lead_f50_h"])) & (o3.scope == "all 18 events") & (o3.horizon.isin(["1h", "3h"]))]
    fact("onset.max_same_sign_events", int(max(od.events_72h_earlier_lead.max(), od.events_72h_later_lead.max())), "reports/phase1e_onset/tables/O3_summary_level_leads.csv", "max number of events (of 18) with a 72 h lead difference of the same sign at the 10% and 50% levels, 1 h and 3 h")

    # ------------------------------------------------------------------ upstream feasibility and protocol (E17, E20)
    s1 = rd("reports/upstream_protocol_support/tables/S1_event_availability_18.csv")
    s4 = rd("reports/upstream_protocol_support/tables/S4_class_counts.csv").set_index("proposed_class")
    for cls, key in (("upstream-led", "up"), ("local-or-downstream-led", "local"), ("ambiguous", "amb")):
        fact(f"up.class_{key}", int(s4.loc[cls, "events"]), "reports/upstream_protocol_support/tables/S4_class_counts.csv", f"events in class {cls}")
        fact(f"up.clusters_{key}", int(s4.loc[cls, "storm_clusters"]), "reports/upstream_protocol_support/tables/S4_class_counts.csv", f"storm clusters in class {cls}")
    fact("up.upstream_led_ge25", int(s4.loc["upstream-led", "peak_ge_25ft"]), "reports/upstream_protocol_support/tables/S4_class_counts.csv", "upstream-led events with a peak of at least 25 ft")
    lead = s1[["event_start_utc", "peak_ft", "fold", "storm_cluster", "provisional_data", "v2_best_lead_h_15min_grid", "v3_best_lead_h_15min_grid", "proposed_class"]]
    up_leads = lead[lead.proposed_class == "upstream-led"].v2_best_lead_h_15min_grid
    fact("up.lead_min_h", round(float(up_leads.min()), 2), "reports/upstream_protocol_support/tables/S1_event_availability_18.csv", "min v2 best lead (15-min grid) among upstream-led events")
    fact("up.lead_max_h", round(float(up_leads.max()), 2), "reports/upstream_protocol_support/tables/S1_event_availability_18.csv", "max v2 best lead (15-min grid) among upstream-led events")
    s5 = rd("reports/upstream_protocol_support/tables/S5_fold_data_availability.csv")
    s8b = rd("reports/upstream_protocol_support/tables/S8b_timing_recomputed_per_gauge_event.csv")
    fact("up.five_min_series", int((s8b.native_median_step == "0 days 00:05:00").sum()), "reports/upstream_protocol_support/tables/S8b_timing_recomputed_per_gauge_event.csv", "gauge-event series whose median reporting step is 5 minutes")
    s6 = rd("reports/upstream_protocol_support/tables/S6b_nwis_requery_of_missing_cache.csv")
    fact("up.requeried_gauge_events", int(s6.error.isna().sum()), "reports/upstream_protocol_support/tables/S6b_nwis_requery_of_missing_cache.csv", "gauge-events absent from the first cache (failed downloads) recovered by a public NWIS re-query")
    has_drop = s1.gauges_dropout_lt80pct.notna()
    fact("up.events_with_dropout", int(has_drop.sum()), "reports/upstream_protocol_support/tables/S1_event_availability_18.csv", "evaluated events in which at least one upstream gauge had under 80% coverage in the pre-event window")
    r25 = s1[s1.event_start_utc.str.startswith("2025-07-05")].iloc[0]
    n_drop = len(str(r25.gauges_dropout_lt80pct).split(", "))
    fact("up.dropout_2025_gauges", n_drop, "reports/upstream_protocol_support/tables/S1_event_availability_18.csv", "gauges below 80% coverage before the 2025-07-05 flood")
    fact("up.dropout_2025_total", int(r25.upstream_gauges_recorded_in_v3_window) + n_drop, "reports/upstream_protocol_support/tables/S1_event_availability_18.csv", "upstream gauges installed before the 2025-07-05 flood (recorded + dropout)")
    aud = rd("reports/upstream_feasibility/tables/upstream_audit_summary.csv")
    fact("up.datum_step_ft", float(aud[aud.site == 8167000].largest_year_to_year_step_ft.iloc[0]), "reports/upstream_feasibility/tables/upstream_audit_summary.csv", "largest year-to-year stage step at the Comfort gauge (08167000)")
    fact("up.min_sign_test_p", round(2 * 0.5 ** FACTS["up.class_up"]["value"], 3), "arithmetic", "2 x 0.5^n for n upstream-led events (smallest attainable two-sided exact sign-test p-value)")
    ptxt = (ROOT / "docs/UPSTREAM_INPUT_PROTOCOL.md").read_text()
    SOURCES["docs/UPSTREAM_INPUT_PROTOCOL.md"] = sha(ROOT / "docs/UPSTREAM_INPUT_PROTOCOL.md")
    sec6 = ptxt.split("## 6.")[1].split("## 7.")[0]
    fact("up.guide_questions", len(re.findall(r"^\d+\. ", sec6, flags=re.M)), "docs/UPSTREAM_INPUT_PROTOCOL.md", "numbered questions in section 6")
    rtxt = (ROOT / "reports/gauge_rainfall/README.md").read_text()
    SOURCES["reports/gauge_rainfall/README.md"] = sha(ROOT / "reports/gauge_rainfall/README.md")
    mrow = re.search(r"\| 2015-05-24 [^|]*\| ([0-9.]+) \| [0-9.]+ \| ([0-9.]+) \|", rtxt)
    fact("rain.era5_pct_2015_05_24", round(100 * float(mrow.group(2)) / float(mrow.group(1)), 1), "reports/gauge_rainfall/README.md", "ERA5 basin rainfall / gauge IDW basin rainfall on 2015-05-24 (table row)")
    qcol = [c for c in s5.columns if c.startswith("years_of_hourly_QPE_in_training")][0]
    fact("up.qpe_folds_with_training_data", int((s5[qcol] > 0).sum()), "reports/upstream_protocol_support/tables/S5_fold_data_availability.csv", "folds whose training period contains hourly radar rainfall")

    # ------------------------------------------------------------------ engineering facts
    reg = rj("experiments/registry.json")
    fact("eng.registry_entries", int(len(reg["entries"])), "experiments/registry.json", "number of registered experiments / work items")
    fact("eng.protocols", int(len(list((ROOT / "docs").glob("PHASE*_PROTOCOL.md"))) + 1), "docs/", "PHASE*_PROTOCOL.md files plus UPSTREAM_INPUT_PROTOCOL.md")
    fact("eng.loc_src", lines_of_code("src"), "src/", "lines of Python in src/")
    fact("eng.loc_scripts", lines_of_code("scripts"), "scripts/", "lines of Python in scripts/")
    fact("eng.loc_tests", lines_of_code("tests"), "tests/", "lines of Python in tests/")
    tests = run_tests()
    fact("eng.tests_passed", tests["passed"], "pytest run at build time", "pytest -q (this dashboard's own test excluded)")
    fact("eng.tests_failed", tests["failed"], "pytest run at build time", "pytest -q")
    fact("eng.scripts", int(len(list((ROOT / "scripts").glob("*.py")))), "scripts/", "number of Python scripts")
    fact("eng.modules", int(len([p for p in (ROOT / "src/flashflood").glob("*.py") if p.name != "__init__.py"])), "src/flashflood/", "library modules")

    # ------------------------------------------------------------------ model comparison data
    model_cv = rows(d1, ["subset", "horizon", "model", "n_rows", "n_storm_groups", "rmse_ft", "rmse_ci_lo", "rmse_ci_hi", "mae_ft", "skill_vs_persistence", "skill_ci_lo", "skill_ci_hi"])
    single = rows(c1, ["subset", "horizon", "model", "n_rows", "n_groups", "rmse_ft", "rmse_sd_across_seeds", "rmse_ci_lo", "rmse_ci_hi", "skill_vs_persistence"])
    paired_cv = rows(d3[d3.reference.isin(["ridge_H", "trend_v2", "xgb_H"])], ["subset", "horizon", "model", "reference", "rmse_diff_ft", "ci_lo", "ci_hi", "interval_excludes_zero"])
    paired_1c = rows(c2b, ["subset", "horizon", "model", "reference", "rmse_diff_ft", "ci_lo", "ci_hi", "interval_excludes_zero", "status"])
    detection = rows(d5[d5.definition.isin(["experimental_rise_4ft_3h", "experimental_stage_10ft", "official_action_25ft"])], ["definition", "horizon", "model", "n_events", "early_hits", "late", "misses", "POD", "false_alarm_episodes", "storm_clusters", "median_lead_h"])
    window = {"paired": rows(e1b, ["subset", "horizon", "diff_72_minus_24_ft", "ci_lo", "ci_hi", "interval_excludes_zero", "seeds_where_72h_better", "folds_where_72h_better"]),
              "decision": rows(e3, ["horizon", "flood10_pooled_diff", "flood10_ci", "(ii) folds 72h better (need >=4 of 6)", "(iii) seeds 72h better (need 3 of 3)", "CONSISTENT IMPROVEMENT", "all_rows_significantly_worse"]),
              "train_minutes_median": {"24": FACTS["p1e.median_min_24"]["value"], "72": FACTS["p1e.median_min_72"]["value"]}}
    onset = {"lead_by_variant": rows(o3b), "issue_vs_onset_50": rows(half[half.horizon.isin(["1h", "3h"])]), "pre_onset": rows(o5[(o5.scope == "all 18 events") & o5.horizon.isin(["1h", "3h"])])}

    # example series (saved Phase 1D out-of-fold predictions) for the "sudden rises" figure
    oof = pd.read_csv(ROOT / "reports/phase1d/oof_predictions.csv.gz", usecols=["timestamp_utc", "stage_ft", "pred_gru_3h_ft", "pred_ridge_H_3h_ft", "pred_persistence_3h_ft", "pred_gru_1h_ft", "pred_ridge_H_1h_ft"])
    SOURCES["reports/phase1d/oof_predictions.csv.gz"] = sha(ROOT / "reports/phase1d/oof_predictions.csv.gz")
    ex = oof[(oof.timestamp_utc >= "2025-07-04 21:00") & (oof.timestamp_utc <= "2025-07-05 21:00")].reset_index(drop=True)
    example = {"event": f"2025-07-05 (official NWS action stage reached; peak {float(np.nanmax(ex.stage_ft)):.2f} ft in the saved 15-minute data)", "t0": ex.timestamp_utc.iloc[0], "step_min": 15, "n": len(ex),
               "obs": [None if not np.isfinite(v) else round(float(v), 3) for v in ex.stage_ft], "pred_gru_3h": [None if not np.isfinite(v) else round(float(v), 3) for v in ex.pred_gru_3h_ft],
               "pred_ridge_3h": [None if not np.isfinite(v) else round(float(v), 3) for v in ex.pred_ridge_H_3h_ft], "pred_persistence_3h": [None if not np.isfinite(v) else round(float(v), 3) for v in ex.pred_persistence_3h_ft],
               "source": "reports/phase1d/oof_predictions.csv.gz (forecast issued at the row time for 3 h later)"}

    # event strip (all 20 events at or above 10 ft in the catalogue)
    m10 = mapping[mapping.definition == "experimental_stage_10ft"]
    strip = rows(m10[["event_start", "peak_ft", "status", "fold", "storm_cluster"]])
    upstream_rows = rows(lead)

    # ------------------------------------------------------------------ milestones, roadmap, limitations, next steps (curated text; numbers via facts)
    F = lambda k: FACTS[k]["value"]  # noqa: E731
    milestones = [
        {"id": "m1", "title": "Data acquisition and audit", "internal": "Phase 0 (E0)", "task": "Complete", "evidence_strength": "Descriptive statistics of observed data",
         "text": f"USGS 15-minute stage for {F('p0.first')} to {F('p0.last')}: {F('p0.rows'):,} rows, {F('p0.completeness_pct')}% of expected values present. The first working dataset (2022-2023) contained no flood and its thresholds were near the median stage ({F('p0.old_threshold_above_pct')}% of rows above them), so the record was extended and official NWS flood stages adopted. Only {F('p0.official_events')} events ({F('p0.official_storms')} storms) reach the 25 ft action stage; ERA5 rainfall was found unreliable for flood timing.",
         "evidence": [exists("reports/phase0/PHASE0_REPORT.md")]},
        {"id": "m2", "title": "Preprocessing and leakage-safe evaluation framework", "internal": "Phase 1A (E1, E2)", "task": "Complete", "evidence_strength": "Engineering and protocol; one defect found and disclosed",
         "text": "Causal features, eligibility rules, storm-cluster grouping and chronological splits written down before the experiments. A data-handling defect (one missing sample blanked 72 hours of features and hid the largest test flood) was found, fixed, logged as deviation 3, and the original results are kept reproducible.",
         "evidence": [exists("docs/PHASE1A_PROTOCOL.md"), exists("reports/PHASE1A_REPORT.md"), exists("reports/DEVIATION3_COMPARISON.md")]},
        {"id": "m3", "title": "Classical forecasting baselines", "internal": "Phase 1B (E3-E8)", "task": "Complete", "evidence_strength": "Exploratory (test period already inspected)",
         "text": "Persistence, damped trend, ridge regression and XGBoost at four horizons. Extra features, sample weighting and rainfall inputs were tested and archived because they did not improve results under the pre-set rule.",
         "evidence": [exists("docs/PHASE1B_PROTOCOL.md"), exists("reports/PHASE1B_REPORT.md")]},
        {"id": "m4", "title": "LSTM, GRU and Transformer baselines", "internal": "Phase 1C (E11, E12)", "task": "Complete", "evidence_strength": "Exploratory; single chronological split",
         "text": f"Three deep encoders with a shared design, {F('p1c.seeds')} seeds each. On one split the GRU looked best, but that split has only {F('p1c.test_events')} flood events. The Transformer trained unstably (best epoch {F('p1c.transformer_best_epoch_min')} to {F('p1c.transformer_best_epoch_max')}; validation loss {F('p1c.transformer_val_loss_min')} to {F('p1c.transformer_val_loss_max')} against {F('p1c.gru_lstm_val_loss_min')} to {F('p1c.gru_lstm_val_loss_max')} for GRU/LSTM); this is one untuned configuration, not evidence against Transformers.",
         "evidence": [exists("docs/PHASE1C_DL_PROTOCOL.md"), exists("reports/PHASE1C_REPORT.md")]},
        {"id": "m5", "title": "Chronological cross-validation", "internal": "Phase 1D (E14)", "task": "Complete", "evidence_strength": "Exploratory; retrospective blocked CV, not untouched validation",
         "text": f"{F('p1d.folds')} expanding-window folds with a {F('p1d.embargo_text')} embargo; {F('p1d.events_evaluated')} flood events from {F('p1d.clusters_evaluated')} storm clusters evaluated out of fold. GRU and LSTM show no robust advantage over ridge or the damped trend, and are significantly worse in flood windows at 15 and 30 minutes. The earlier GRU advantage did not replicate.",
         "evidence": [exists("docs/PHASE1D_PROTOCOL.md"), exists("reports/PHASE1D_REPORT.md")]},
        {"id": "m6", "title": "Input-window comparison (24 h versus 72 h)", "internal": "Phase 1E (E16)", "task": "Complete; reviewed and approved", "evidence_strength": "Exploratory; decision rule pre-registered",
         "text": f"{F('p1e.runs')} matched trainings. The pre-registered rule keeps the 24 h GRU: {F('p1e.consistent_horizons')} of 4 horizons improved consistently in flood windows, 72 h was {F('p1e.slowdown')} times slower to train, and detection was not better.",
         "evidence": [exists("docs/PHASE1E_PROTOCOL.md"), exists("reports/PHASE1E_REPORT.md")]},
        {"id": "m7", "title": "Upstream gauge feasibility and research protocol", "internal": "E17, E20", "task": "Feasibility complete; protocol written, awaiting the research guide's decisions", "evidence_strength": "Descriptive; no upstream-input model has been trained",
         "text": f"Of the {F('p1d.events_evaluated')} evaluated events, {F('up.class_up')} are upstream-led ({F('up.clusters_up')} storms), {F('up.class_local')} local-or-downstream-led and {F('up.class_amb')} ambiguous; leads in upstream-led events are {F('up.lead_min_h')} to {F('up.lead_max_h')} h. A controlled four-configuration protocol is drafted; nothing has been run.",
         "evidence": [exists("docs/UPSTREAM_INPUT_FEASIBILITY.md"), exists("docs/UPSTREAM_INPUT_PROTOCOL.md"), exists("reports/upstream_protocol_support/README.md")]},
        {"id": "m8", "title": "Onset-timing analysis", "internal": "E18", "task": "Complete", "evidence_strength": "Post-hoc descriptive diagnostic on saved predictions",
         "text": f"A 3 h forecast shows a level a median of {F('onset.lag_f50_3h')} h after the river reached it at half of the rise ({F('onset.lag_f10_3h')} to {F('onset.lag_f90_3h')} h across 10% to 90%). In none of the {F('p1d.events_evaluated')} events did any model forecast half of the rise before the rise began. The 72 h window does not change this.",
         "evidence": [exists("docs/PHASE1E_ONSET_PROTOCOL.md"), exists("reports/PHASE1E_ONSET_TIMING.md")]},
        {"id": "m9", "title": "Historical-replay dashboard", "internal": "E19", "task": "Complete", "evidence_strength": "Engineering; every curve and metric traceable to saved predictions",
         "text": "Offline viewer of the saved out-of-fold forecasts for 18 events: observed versus predicted stage, four horizons, issue versus target time, peak levels, error metrics, data-quality information. A retrospective replay, not a live system.",
         "evidence": [exists("dashboard/replay/index.html"), exists("dashboard/replay/README.md")]},
    ]
    roadmap = [
        {"id": "ev1", "name": "First evaluation", "status": "Current", "theme": "Problem, data, evaluation framework and baseline evidence",
         "objectives": ["Define the problem, data and a leakage-safe evaluation framework", "Establish classical and deep baselines under chronological cross-validation", "Identify what limits forecasting and what to test next"],
         "deliverables": [{"t": "Data audit and event catalogue", "done": True, "e": "reports/phase0/PHASE0_REPORT.md"}, {"t": "Leakage-safe preprocessing and evaluation framework with tests", "done": True, "e": "docs/PHASE1A_PROTOCOL.md"},
                          {"t": "Classical baselines", "done": True, "e": "reports/PHASE1B_REPORT.md"}, {"t": "LSTM, GRU and Transformer baselines", "done": True, "e": "reports/PHASE1C_REPORT.md"},
                          {"t": "Chronological cross-validation and model comparison", "done": True, "e": "reports/PHASE1D_REPORT.md"}, {"t": "24 h versus 72 h input-window experiment (reviewed, approved)", "done": True, "e": "reports/PHASE1E_REPORT.md"},
                          {"t": "Upstream gauge feasibility and onset-timing analysis", "done": True, "e": "reports/PHASE1E_ONSET_TIMING.md"}, {"t": "Upstream-input research protocol (draft for the guide)", "done": True, "e": "docs/UPSTREAM_INPUT_PROTOCOL.md"},
                          {"t": "Historical-replay dashboard", "done": True, "e": "dashboard/replay/index.html"}, {"t": "Faculty evaluation dashboard (this page) and presentation pack", "done": True, "e": "docs/FACULTY_EVALUATION_PREP.md"}],
         "completed": "All items listed as deliverables exist on disk with their evidence files.", "remaining": "The research guide has not yet reviewed the upstream-input protocol; no hybrid model, warning logic or live component exists.",
         "demo": "This dashboard, then the replay dashboard on the 2025-07-05 flood, then the model-comparison and onset-timing evidence."},
        {"id": "ev2", "name": "Second evaluation", "status": "Proposed", "theme": "Test whether extra information helps, then build and test the hybrid",
         "objectives": ["Run the upstream-input comparison (A to D) if the guide approves the protocol", "Specify and implement the hybrid Transformer-LSTM and compare it with every baseline under the same folds", "Optionally run a bounded Transformer-instability diagnostic"],
         "deliverables": [{"t": "Guide decisions on the " + str(FACTS["up.guide_questions"]["value"]) + " protocol questions", "done": False, "e": None}, {"t": "Validated upstream data (full-record gauge stage; hourly radar rainfall validated against gauges)", "done": False, "e": None},
                          {"t": "Upstream-input experiment report (configurations A to D, same folds, pre-registered rule)", "done": False, "e": None}, {"t": "Hybrid Transformer-LSTM implementation, tests and cross-validated comparison", "done": False, "e": None},
                          {"t": "Updated dashboard with the new results", "done": False, "e": None}],
         "completed": "Prerequisites only: the protocol draft, the baselines and the evaluation framework.", "remaining": "Everything listed; none of it has started.",
         "demo": "Planned: A-to-D comparison per flood class, hybrid against baselines with intervals, failure analysis."},
        {"id": "ev3", "name": "Third evaluation", "status": "Proposed", "theme": "Early-warning evaluation, robustness and final report",
         "objectives": ["Evaluate event detection and lead time with a false-alarm constraint (research prototype, not operational)", "Test robustness to missing data and report failure cases", "Complete the final report and an integrated replay demonstration"],
         "deliverables": [{"t": "Probability or detection head with false-alarm-capped thresholds", "done": False, "e": None}, {"t": "Warning-category calibration study (research prototype)", "done": False, "e": None},
                          {"t": "Robustness and missing-data tests; explanation of selected events", "done": False, "e": None}, {"t": "Final report, reproducibility package and integrated dashboard", "done": False, "e": None}],
         "completed": "Prerequisites only: event-detection metrics and fixed-rule evaluation exist.", "remaining": "Everything listed; any real-time claim additionally needs a real-time rainfall source that is not yet identified.",
         "demo": "Planned: end-to-end replay with detection results, robustness figures and limitations."},
    ]
    limitations = [
        {"t": "Few independent flood events", "d": f"{F('p1d.events_evaluated')} evaluated events come from {F('p1d.clusters_evaluated')} storm clusters; only {F('p1d.official_evaluated')} reach the official 25 ft stage, from {F('p1d.official_clusters')} storms. Flood-window statistics rest on {F('p1d.flood_groups')} bootstrap groups, so intervals are wide.", "e": "reports/phase1d/tables/D6_event_coverage_and_exclusions.csv"},
        {"t": "Rainfall data limitations", "d": "ERA5 reanalysis missed convective flood rainfall (about " + str(F('rain.era5_pct_2015_05_24')) + "% of the gauge estimate on 2015-05-24). The gauge rainfall product is daily. A sub-daily radar product exists only from 2015 and its continuity is unverified; folds 1 to 3 have no radar data in training.", "e": "reports/phase0/PHASE0_REPORT.md"},
        {"t": "Missing and inconsistent upstream observations", "d": f"Upstream gauges fell below 80% coverage before {F('up.events_with_dropout')} of the {F('p1d.events_evaluated')} events, including {F('up.dropout_2025_gauges')} of {F('up.dropout_2025_total')} gauges before the 2025-07-05 official-stage flood; the Comfort gauge has a {F('up.datum_step_ft')} ft datum step (2011); {F('up.five_min_series')} gauge-event series report at 5-minute rather than 15-minute stamps; and {F('up.requeried_gauge_events')} gauge-events were missing from the first cache because of failed downloads (since recovered).", "e": "reports/upstream_protocol_support/README.md"},
        {"t": "Limited statistical power", "d": f"{F('up.class_up')} upstream-led events from {F('up.clusters_up')} storms cannot give a significant result (smallest two-sided exact sign-test p-value {F('up.min_sign_test_p')}); the upstream-input plan is therefore an effect-size study. Deep-model comparisons use one seed per fold in the cross-validation.", "e": "docs/UPSTREAM_INPUT_PROTOCOL.md"},
        {"t": "No demonstrated early anticipation", "d": f"With stage-only inputs no model forecast half of a rise before it began in any of the {F('p1d.events_evaluated')} events; a 3 h forecast lags the river by a median {F('onset.lag_f50_3h')} h at half of the rise.", "e": "reports/PHASE1E_ONSET_TIMING.md"},
        {"t": "No operational warning system", "d": "There are no warning categories, alerts or live data feed. Both rainfall sources used so far are retrospective, so the project title's 'real-time' goal is not yet supported by the data pipeline. Every result is retrospective cross-validation on a record that has been inspected, i.e. exploratory.", "e": "README.md"},
        {"t": "One catchment, one gauge", "d": "No claim of transfer to other rivers; a second catchment is an optional extension.", "e": "README.md"},
    ]
    next_steps = [
        {"phase": "Before the second evaluation (needs the research guide)", "items": ["Review the upstream-input protocol and answer its " + str(F('up.guide_questions')) + " questions (reframing the central claim; gauge set; rainfall source; decision margins)", "Confirm faculty expectations for the three evaluations (deadlines, deliverable format, whether a working hybrid is expected at the second evaluation)"]},
        {"phase": "Proposed for the second evaluation", "items": ["Upstream-input experiments A to D under the same folds and metrics, reported separately for upstream-led and local floods", "Hybrid Transformer-LSTM: Transformer branch (long window) plus LSTM branch (short window), fusion, four horizon heads; compared with GRU, LSTM, ridge, damped trend, XGBoost", "Bounded Transformer diagnostic only if approved"]},
        {"phase": "Proposed for the third evaluation", "items": ["Detection head with a false-alarm cap and lead-time evaluation (research prototype)", "Robustness to missing data; failure analysis; final report; integrated replay demonstration"]},
    ]
    demo = {"replay": "../replay/index.html", "screenshots": [exists(f"dashboard/replay/screenshots/{n}") for n in ("01_event_replay_overview.png", "03_issue_time_view.png", "04_missing_observations_and_unavailable_forecasts.png")],
            "components": [
                {"t": "Data pipeline and audit", "d": f"{F('eng.scripts')} scripts and {F('eng.modules')} library modules ({F('eng.loc_src') + F('eng.loc_scripts'):,} lines of Python in src and scripts)", "cmd": "PYTHONPATH=src python scripts/audit_phase0.py"},
                {"t": "Leakage-safe evaluation framework", "d": "storm clusters, blocked chronological folds with embargo, per-fold scaling, paired storm-cluster bootstrap", "cmd": ".venv/bin/python -m pytest -q"},
                {"t": "Automated tests", "d": f"{F('eng.tests_passed')} tests passed, {F('eng.tests_failed')} failed at build time ({F('eng.loc_tests'):,} lines)", "cmd": ".venv/bin/python -m pytest -q"},
                {"t": "Pre-registered protocols and experiment registry", "d": f"{F('eng.protocols')} protocols, {F('eng.registry_entries')} registry entries with status and deviations", "cmd": "open experiments/REGISTRY.md"},
                {"t": "Historical-replay dashboard", "d": "saved out-of-fold forecasts, 18 events, offline", "cmd": "open dashboard/replay/index.html"}],
            "not_implemented": ["Hybrid Transformer-LSTM model", "Upstream-input experiments", "Probability / detection head and warning categories", "Real-time data ingestion, live forecasting or alerting", "Discharge forecasting"]}
    doc = {"meta": {"title": "Hybrid Transformer-LSTM for Real-Time Flash-Flood Forecasting and Early Warning: first evaluation progress review",
                    "station": "USGS 08167500, Guadalupe River near Spring Branch, Texas (NWS id SRGT2)", "horizons": HZ, "built": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "notice": "Research progress dashboard built from the project's saved result tables. All experimental results are exploratory (retrospective, test period already inspected). The hybrid model has not been implemented. The academic roadmap is a proposal pending faculty confirmation."},
           "facts": FACTS, "model_cv": model_cv, "single_split": single, "paired_cv": paired_cv, "paired_1c": paired_1c, "detection": detection, "window": window, "onset": onset,
           "example": example, "strip": strip, "upstream": upstream_rows, "milestones": milestones, "roadmap": roadmap, "limitations": limitations, "next_steps": next_steps, "demo": demo,
           "tests": tests, "sources": SOURCES}
    payload = json.dumps(doc, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    html = (DIR / "template.html").read_text()
    assert "__EVAL_DATA__" in html
    out = DIR / "index.html"
    out.write_text(html.replace("__EVAL_DATA__", payload))
    print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB; {len(FACTS)} facts; {len(SOURCES)} source files; tests passed {tests['passed']}, failed {tests['failed']})")


if __name__ == "__main__":
    DIR.mkdir(parents=True, exist_ok=True)
    main()
