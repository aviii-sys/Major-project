"""Faculty evaluation dashboard: every embedded number must equal the saved project tables, every link must resolve, and nothing unimplemented may be shown as done.
The page embeds a JSON document; these tests re-derive the values from the CSV/JSON sources by an independent route (key lookups, not the builder's code)."""
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import pytest

PAGE = Path("dashboard/evaluation/index.html")
pytestmark = pytest.mark.skipif(not PAGE.exists(), reason="dashboard not built (run scripts/build_evaluation_dashboard.py)")


def _doc() -> dict:
    html = PAGE.read_text()
    m = re.search(r'<script id="eval-data" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1).replace("<\\/", "</"))


@pytest.fixture(scope="module")
def doc():
    return _doc()


def test_embedded_source_hashes_match_current_files(doc):
    stale = [k for k, v in doc["sources"].items() if not Path(k).exists() or hashlib.sha256(Path(k).read_bytes()).hexdigest() != v]
    assert not stale, f"dashboard is stale, rebuild it: {stale}"


def test_model_comparison_matches_phase1d_table(doc):
    d1 = pd.read_csv("reports/phase1d/tables/D1_pooled_regression_metrics.csv").set_index(["subset", "horizon", "model"])
    assert len(doc["model_cv"]) == len(d1) == 72
    for r in doc["model_cv"]:
        s = d1.loc[(r["subset"], r["horizon"], r["model"])]
        assert r["rmse_ft"] == pytest.approx(s.rmse_ft, abs=5e-7) and r["rmse_ci_lo"] == pytest.approx(s.rmse_ci_lo, abs=5e-7) and r["rmse_ci_hi"] == pytest.approx(s.rmse_ci_hi, abs=5e-7)
        assert r["skill_vs_persistence"] == pytest.approx(s.skill_vs_persistence, abs=5e-7) and r["n_rows"] == s.n_rows and r["n_storm_groups"] == s.n_storm_groups


def test_single_split_matches_phase1c_table_and_includes_the_transformer(doc):
    c1 = pd.read_csv("reports/phase1c/tables/C1_regression_metrics.csv")
    c1 = c1[c1.protocol == "chrono_test"].set_index(["subset", "horizon", "model"])
    assert len(doc["single_split"]) == len(c1) == 84
    assert {r["model"] for r in doc["single_split"]} >= {"transformer", "gru", "lstm", "ridge_H0", "xgb_H0", "trend_v2", "persistence"}
    for r in doc["single_split"]:
        s = c1.loc[(r["subset"], r["horizon"], r["model"])]
        assert r["rmse_ft"] == pytest.approx(s.rmse_ft, abs=5e-7) and r["n_rows"] == s.n_rows


def test_paired_differences_and_detection_match_tables(doc):
    d3 = pd.read_csv("reports/phase1d/tables/D3_paired_model_differences.csv").set_index(["subset", "horizon", "model", "reference"])
    for r in doc["paired_cv"]:
        s = d3.loc[(r["subset"], r["horizon"], r["model"], r["reference"])]
        assert r["rmse_diff_ft"] == pytest.approx(s.rmse_diff_ft, abs=5e-7) and r["ci_lo"] == pytest.approx(s.ci_lo, abs=5e-7) and r["interval_excludes_zero"] == bool(s.interval_excludes_zero)
    c2 = pd.read_csv("reports/phase1c/tables/C2b_posthoc_vs_ridge_and_trend.csv").set_index(["subset", "horizon", "model", "reference"])
    for r in doc["paired_1c"]:
        assert r["rmse_diff_ft"] == pytest.approx(c2.loc[(r["subset"], r["horizon"], r["model"], r["reference"])].rmse_diff_ft, abs=5e-7)
    d5 = pd.read_csv("reports/phase1d/tables/D5_fixed_rule_detection_pooled_oof.csv").set_index(["definition", "horizon", "model"])
    for r in doc["detection"]:
        s = d5.loc[(r["definition"], r["horizon"], r["model"])]
        assert r["early_hits"] == s.early_hits and r["n_events"] == s.n_events and r["storm_clusters"] == s.storm_clusters


def test_window_and_onset_tables_match(doc):
    e1b = pd.read_csv("reports/phase1e/tables/E1b_paired_72_minus_24.csv").set_index(["subset", "horizon"])
    for r in doc["window"]["paired"]:
        s = e1b.loc[(r["subset"], r["horizon"])]
        assert r["diff_72_minus_24_ft"] == pytest.approx(s.diff_72_minus_24_ft, abs=5e-7) and r["interval_excludes_zero"] == bool(s.interval_excludes_zero)
    e3 = pd.read_csv("reports/phase1e/tables/E3_decision_rule.csv").set_index("horizon")
    for r in doc["window"]["decision"]:
        assert r["CONSISTENT IMPROVEMENT"] == bool(e3.loc[r["horizon"], "CONSISTENT IMPROVEMENT"])
    assert json.loads(Path("reports/phase1e/decision.json").read_text())["adopt_72h"] is False and not any(r["CONSISTENT IMPROVEMENT"] for r in doc["window"]["decision"])
    o3b = pd.read_csv("reports/phase1e_onset/tables/O3b_median_lead_by_variant.csv").set_index(["variant", "horizon"])
    for r in doc["onset"]["lead_by_variant"]:
        s = o3b.loc[(r["variant"], r["horizon"])]
        assert r["lead_f50_h"] == pytest.approx(s.lead_f50_h, abs=5e-7)


def test_upstream_rows_and_class_counts_match(doc):
    s1 = pd.read_csv("reports/upstream_protocol_support/tables/S1_event_availability_18.csv")
    assert len(doc["upstream"]) == len(s1) == 18
    got = pd.Series([r["proposed_class"] for r in doc["upstream"]]).value_counts().to_dict()
    assert got == s1.proposed_class.value_counts().to_dict() == {"upstream-led": 6, "local-or-downstream-led": 6, "ambiguous": 6}
    f = doc["facts"]
    assert (f["up.class_up"]["value"], f["up.class_local"]["value"], f["up.class_amb"]["value"]) == (6, 6, 6)


def test_key_facts_recomputed_independently(doc):
    f = {k: v["value"] for k, v in doc["facts"].items()}
    p0 = json.loads(Path("reports/phase0/phase0_results.json").read_text())["hydro"]
    assert f["p0.rows"] == p0["rows_raw"] and f["p0.completeness_pct"] == pytest.approx(100 * (1 - p0["stage_missing"] / p0["expected_15min_steps"]), abs=0.005)
    e8 = pd.read_csv("reports/phase1e/tables/E8_training_diagnostics.csv")
    m24, m72 = e8[e8.window_h == 24].train_seconds.median(), e8[e8.window_h == 72].train_seconds.median()
    assert f["p1e.slowdown"] == pytest.approx(m72 / m24, abs=0.05) and f["p1e.runs"] == len(e8) == 36
    d6 = pd.read_csv("reports/phase1d/tables/D6_event_coverage_and_exclusions.csv")
    r = d6[(d6.definition == "experimental_stage_10ft") & (d6.status == "evaluated")].iloc[0]
    assert (f["p1d.events_evaluated"], f["p1d.clusters_evaluated"]) == (r.events, r.storm_clusters) == (18, 14)
    o3b = pd.read_csv("reports/phase1e_onset/tables/O3b_median_lead_by_variant.csv")
    g = o3b[(o3b.variant == "GRU 24 h (all seeds)") & (o3b.horizon == "3h")].iloc[0]
    assert f["onset.lag_f50_3h"] == pytest.approx(3 - g.lead_f50_h, abs=0.005)
    assert f["eng.registry_entries"] == len(json.loads(Path("experiments/registry.json").read_text())["entries"])
    assert f["eng.tests_failed"] == 0 and f["eng.tests_passed"] >= 76
    assert f["p1d.rise4_3h_hits.ridge_H"] == 12 and f["p1d.rise4_3h_hits.gru"] == 7 and f["p1d.rise4_3h_hits.lstm"] == 4 and f["p1d.rise4_3h_hits.trend_v2"] == 10
    assert f["onset.half_rise_before_onset_events_max"] == 0 and f["p1e.consistent_horizons"] == 0 and f["p1e.adopt_72h"] is False


def test_example_event_series_equals_the_saved_predictions(doc):
    ex = doc["example"]
    o = pd.read_csv("reports/phase1d/oof_predictions.csv.gz", usecols=["timestamp_utc", "stage_ft", "pred_gru_3h_ft"])
    o = o.set_index("timestamp_utc")
    t0 = pd.Timestamp(ex["t0"])
    for i in (0, 20, 40, 60, ex["n"] - 1):
        ts = (t0 + pd.Timedelta(minutes=15 * i)).strftime("%Y-%m-%d %H:%M")
        assert ex["obs"][i] == pytest.approx(o.loc[ts, "stage_ft"], abs=1e-3)
        g = o.loc[ts, "pred_gru_3h_ft"]
        assert (ex["pred_gru_3h"][i] is None and pd.isna(g)) or ex["pred_gru_3h"][i] == pytest.approx(g, abs=1e-3)


def _local_paths(doc) -> set:
    paths = set()
    for m in doc["milestones"]:
        paths.update(m["evidence"])
    for p in doc["roadmap"]:
        paths.update(d["e"] for d in p["deliverables"] if d["e"])
    paths.update(item["e"] for item in doc["limitations"])
    paths.update(doc["demo"]["screenshots"])
    return paths


def test_every_link_target_exists(doc):
    missing = [p for p in _local_paths(doc) if not Path(p).exists()]
    assert not missing, missing
    html = PAGE.read_text()
    assert (PAGE.parent / "../replay/index.html").resolve().exists() and 'href="../replay/index.html"' in html          # the existing replay dashboard is linked and present
    for anchor in re.findall(r'<a href="#([a-z]+)">', html):
        assert f'id="{anchor}"' in html, anchor


def test_self_contained_and_no_network_calls():
    html = PAGE.read_text()
    assert not re.search(r'(src|href)\s*=\s*["\']https?://', html) and "@import" not in html and "fetch(" not in html and "XMLHttpRequest" not in html


def test_roadmap_is_labelled_a_proposal_and_the_hybrid_is_not_shown_as_done(doc):
    html = PAGE.read_text().lower()
    assert "this three-stage structure is a proposal" in html and "not documented anywhere in the project" in html
    ev = {p["id"]: p for p in doc["roadmap"]}
    assert ev["ev1"]["status"] == "Current" and ev["ev2"]["status"] == "Proposed" and ev["ev3"]["status"] == "Proposed"
    assert not any(d["done"] for p in (ev["ev2"], ev["ev3"]) for d in p["deliverables"])
    assert all(d["done"] and d["e"] and Path(d["e"]).exists() for d in ev["ev1"]["deliverables"])
    ni = " ".join(doc["demo"]["not_implemented"]).lower()
    for item in ("hybrid", "upstream-input experiments", "warning categories", "real-time", "discharge"):
        assert item in ni
    for m in doc["milestones"]:
        assert "hybrid" not in m["title"].lower()
    assert "proposed future development" in html and "proposed, not yet implemented" in html
    assert not re.search(r"\b\d{1,3}\s?%\s+(complete|done|finished)", html)                    # no invented completion percentages


def test_exploratory_status_is_stated_and_no_warning_capability_is_claimed():
    html = PAGE.read_text().lower()
    assert "exploratory" in html and "confirmatory" in html
    for banned in ("operational warning system is", "live forecast of", "real-time forecasting system is", "warning capability is"):
        assert banned not in html


def test_page_script_has_valid_javascript_syntax(tmp_path):
    """Catches template slips such as an unescaped quote inside a string (a syntax error silently blanks the whole page). Skipped when node is not installed."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    html = PAGE.read_text()
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    assert len(scripts) == 1
    f = tmp_path / "page.js"
    f.write_text(scripts[0])
    r = subprocess.run([node, "--check", str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:500]
