"""Small tests for the descriptive support script of docs/UPSTREAM_INPUT_PROTOCOL.md (no model involved)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_upstream_protocol_support as sup  # noqa: E402

S1 = Path("reports/upstream_protocol_support/tables/S1_event_availability_18.csv")


def test_lead_band_and_classification_rule():
    assert sup.lead_band(np.nan) == "none" and sup.lead_band(0.99) == "none" and sup.lead_band(-3.0) == "none"
    assert sup.lead_band(1.0) == "short" and sup.lead_band(5.99) == "short" and sup.lead_band(6.0) == "long"
    assert sup.classify_event(16.0, 16.3)[0] == "upstream-led"
    assert sup.classify_event(np.nan, np.nan)[0] == "local-or-downstream-led"
    assert sup.classify_event(-1.5, 0.0)[0] == "local-or-downstream-led"
    assert sup.classify_event(2.5, 2.5)[0] == "ambiguous"                 # short lead under both rules
    assert sup.classify_event(0.0, 35.0)[0] == "ambiguous"                # the two timing rules disagree
    assert sup.classify_event(np.nan, 24.0)[0] == "ambiguous"


def test_nws_stage_labels_never_call_experimental_events_official():
    assert sup.nws_stage_reached(24.99).startswith("below action")
    assert sup.nws_stage_reached(25.0) == "action" and sup.nws_stage_reached(30.06) == "minor"
    assert sup.nws_stage_reached(36.75) == "moderate" and sup.nws_stage_reached(39.0) == "major"


def test_grid_keeps_only_15_minute_marks_and_coverage_is_not_inflated_by_5min_stamps():
    idx5 = pd.date_range("2025-07-01 00:00", "2025-07-01 12:00", freq="5min", tz="UTC")
    s5 = pd.Series(1.0, index=idx5)
    g = sup.to_15min_grid(s5)
    assert len(g) == 49 and (g.index.minute % 15 == 0).all()
    lo, hi = idx5[0], idx5[-1]
    assert sup.window_coverage(s5, lo, hi) > 2.9                      # the original definition over-counts 5-min series (about 3x)
    assert sup.window_coverage(g, lo, hi) == pytest.approx(49 / 48)    # on the 15-min grid it is a proper fraction (inclusive end point)
    s5.iloc[20:120] = np.nan                                           # a gap of 100 five-minute samples (about 8 h) is visible after gridding
    gg = sup.to_15min_grid(s5)
    assert sup.window_coverage(gg, lo, hi) < sup.window_coverage(s5, lo, hi) / 2
    assert sup.longest_gap_hours(gg, lo, hi) > 7


def test_gauge_status_distinguishes_not_installed_from_dropout_and_missing():
    assert sup.gauge_status(0.0, "none", False).startswith("not installed")
    assert sup.gauge_status(np.nan, "none", True).startswith("no data")
    assert sup.gauge_status(0.79, "cache", True).startswith("dropout") and sup.gauge_status(0.80, "cache", True) == "recorded"


def test_lead_summary_takes_the_best_consistent_gauge():
    assert sup.lead_summary([3.0, 16.25, 2.0]) == (16.25, 1)
    b, i = sup.lead_summary([])
    assert np.isnan(b) and i == -1


@pytest.mark.skipif(not S1.exists(), reason="support tables not built")
def test_built_event_table_is_complete_and_consistent_with_the_rule():
    t = pd.read_csv(S1)
    assert len(t) == 18 and t.event_start_utc.is_unique
    assert set(t.proposed_class) <= {"upstream-led", "local-or-downstream-led", "ambiguous"}
    for r in t.itertuples():
        assert sup.classify_event(r.v2_best_lead_h_15min_grid, r.v3_best_lead_h_15min_grid)[0] == r.proposed_class
    assert (t.peak_ft >= 25).sum() == 5 and set(t[t.peak_ft >= 25].nws_stage_reached_by_peak) <= {"action", "minor", "moderate", "major"}
    assert not t[t.peak_ft < 25].nws_stage_reached_by_peak.isin(["action", "minor", "moderate", "major"]).any()
    ev = pd.read_csv("reports/phase1d/event_to_fold_mapping.csv")
    ev = ev[(ev.definition == "experimental_stage_10ft") & (ev.status == "evaluated")]
    assert sorted(t.fold) == sorted(ev.fold.astype(int))
