# Phase 1B Report: Strengthened Classical Baselines, Probability Detection, Rainfall Products

Status: for review. **No LSTM, GRU, Transformer or hybrid has been trained.** Protocols: `docs/PHASE1B_PROTOCOL.md` (pre-registered before any Phase 1B model ran; deviations listed at its end) and `docs/PHASE1C_DL_PROTOCOL.md` (draft, not run). Full generated tables: `reports/phase1b/PHASE1B_TABLES.md`. Timestamps UTC, stage in feet.

## 0. How to read these results
- **Every test-period number (2022-01-01 onward) is exploratory.** The test period was already inspected in Phase 1A and during the deviation-3 defect (section 1), so it cannot confirm anything. All selections here (feature set, sample weights, damped-trend settings, probability thresholds) used validation data (2018-2021) only, but validation has very few events: stage >= 10 ft: 5; >= 15 ft: 2; rise >= 4 ft/3 h: 6; rise >= 8 ft/3 h: 1; none at official stages.
- Official categories remain descriptive (3 test events, 2 storms; one storm is USGS-provisional 2026 data). Experimental targets (stage >= 10/15 ft, rises >= 4/8 ft in 3 h) are not flood thresholds. **No claim of flood-warning capability or generalization is made.**
- Independent events behind each result (events / distinct storm clusters), test period: stage >= 10 ft 4/4; >= 15 ft 2/2; rise >= 4 ft/3 h 7/7; rise >= 8 ft/3 h 5/4; official action 3/2, minor 2/2, moderate 1/1. Blocked CV (non-causal): 20, 9, 27, 15 events and 6, 4, 1 official events.

## 1. Deviation 3 preserved and checked (your item 5)
- **Both versions are kept.** Original (strict rolling windows, events without eligible rows counted as misses): `reports/phase1a_original_strict/`, regenerated from the preserved code path (`run_phase1a.py --legacy`); every number printed during the first run was reproduced exactly. Corrected: `reports/phase1a/`. Side-by-side: `reports/DEVIATION3_COMPARISON.md`.
- **Disclosure:** the defect (one missing sample blanked 72 h of features and removed the largest test event from all models) was found after inspecting test output. The corrected test results are post-hoc corrected and exploratory, not an untouched confirmation. Corrected versus original: 12,879 / 4,261 / 6,159 more eligible 1 h rows in train / validation / test; **401 of 2,880** per-event statuses changed (255 miss to early, 49 miss to late, 60 miss to not evaluable, 18 late to early, 11 early to late, 7 early to miss, 1 late to miss).
- **Regression test kept** (`test_one_missing_sample_does_not_blank_the_next_72_hours`), plus new tests for robust missing-value handling and the gauge-availability cutoff (14 tests pass).
- **Are events only marked unevaluable when coverage makes evaluation impossible?** I checked (`reports/deviation3_unevaluable_diagnosis.csv`). In Phase 1A two events were flagged: the 2024-06-02 rise (a 21 h stage outage ended just before it, so the 6-24 h lag features were missing in all lead-window rows although the current stage was valid) and 2024-07-24 at 3 h (76% eligible against the arbitrary 80% cutoff). Neither was truly impossible to evaluate; the rule was too strict. Phase 1B therefore requires only current stage, 15/30/60 min changes and the target (models tolerate missing long-lag features) and flags an event only if fewer than 50% of its lead-credit issue times have those. **Result: no event in any protocol, horizon or definition is now marked not evaluable.** The Phase 1A numbers are not recomputed under this rule.

## 2. Rainfall (your item 2)
**Gauge-based basin product (done):** `data/processed/gauge_basin_daily.csv`, documentation `reports/gauge_rainfall/README.md`. 664 NOAA stations (187 inside the basin: 176 CoCoRaHS, 9 COOP, 2 airport), flagged data removed, morning-observation family (COOP 07-09 h; CoCoRaHS assigned to it and checked empirically: same-day correlation 0.95 against 0.28/0.25 at +/-1 day), inverse-distance weighting chosen by leave-one-station-out cross-validation (MAE 5.43 mm versus **8.76 mm for the simple mean** and 6.38 mm for the nearest station), station count growing from about 25 (2007) to about 59 (2025) inside the basin, 1 missing and 1 low-coverage day of 6,985. Product day D is usable only from 15:00 UTC on D, so it cannot supply storm-onset timing.
**ERA5 limitations (retained as comparison dataset):** on days with at least 10 mm of gauge basin rain, ERA5 averages 15.5 mm against 23.5 mm (correlation 0.50 versus 0.74 over all days). For the key days of the **2015-05-24 and 2016-05-29 floods ERA5 holds about 8% of the gauge basin rainfall (9.9 versus 119.4 mm; 5.0 versus 64.5 mm)**. ERA5-Land provides no precipitation in the Open-Meteo API; its soil moisture download (53 cells) is still incomplete and unused.
**Effect on forecasting (exploratory):** adding ERA5 rain (H2+R) did not help validation (event-window RMSE 1.066 versus 1.034 for H2), adding gauge features (H2+G) did not either (1.044), and the best richer set (H2+R+G, 1.016) improved on H2 by only 1.8%, below the pre-registered 5% bar. So rainfall features are not used in the final Phase 1B models. This reflects what daily antecedent gauge totals and ERA5 can add to 15-min to 3-h stage forecasts, not whether good sub-daily rainfall would help.
**NLDAS-2 (still blocked on you):** this machine has no Earthdata entry in `~/.netrc` (checked without printing contents). Steps are in `reports/PHASE1A_REPORT.md` section 3.1. Once credentials exist I will test access on a single granule and then compare NLDAS-2 against the same 92-station gauge comparison before preferring it.

## 3. Historical discharge dataset (your item 3)
`data/processed/discharge_1998_2007_15min.csv.gz`, kept separate, no gage height inferred (`reports/discharge_pre2007/README.md`). Each event is checked individually for gaps, against the independent daily mean, and for estimated values: **13 of 17** events >= 10,000 cfs are usable (8 of 10 at >= 20,000; 4 of 5 at >= 30,000). Unusable: 2000-10-25, 2000-11-03, 2002-07-01, 2004-11-17. The 1997 and 2002 floods remain excluded. The 2007-08-17 flood (56,400 cfs) is usable. No models have been run on this dataset.

## 4. Strengthened classical baselines (your item 4)
Pre-registered selection, validation only: **feature set H2** (one choice for all models; richer sets did not meet the 5% rule); **sample weighting**: lambda 0 for ridge, lambda 10 for XGBoost (chosen on a 1% validation difference); **damped trend** per horizon from 12 candidates: window 15 min with phi 1.0, 0.75, 0.75, 0.25 at 15 m, 30 m, 1 h, 3 h.

### 4.1 Stage forecast skill versus persistence, TEST (exploratory), skill [95% storm-cluster interval]
| Model | all rows 15 m | 1 h | 3 h | flood windows 15 m | 1 h | 3 h |
|---|---|---|---|---|---|---|
| damped trend (v2) | 0.70 [0.46, 0.74] | 0.61 [0.15, 0.76] | 0.30 [0.05, 0.45] | 0.81 [0.67, 0.89] | 0.67 [0.19, 0.83] | 0.31 [0.05, 0.55] |
| ridge H (Phase 1A features) | 0.71 [0.47, 0.78] | 0.61 [0.15, 0.75] | 0.41 [0.02, 0.58] | 0.77 [0.59, 0.87] | 0.64 [0.17, 0.80] | 0.39 [0.06, 0.59] |
| ridge H2 (final) | 0.71 [0.47, 0.78] | 0.61 [0.16, 0.76] | 0.42 [0.03, 0.59] | 0.76 [0.59, 0.87] | 0.64 [0.17, 0.80] | 0.39 [0.05, 0.59] |
| XGBoost H | 0.71 [0.59, 0.78] | 0.62 [0.22, 0.74] | 0.30 [0.07, 0.41] | 0.75 [0.63, 0.85] | 0.63 [0.19, 0.78] | 0.25 [0.05, 0.35] |
| XGBoost H2, lambda 10 (final) | 0.67 [0.41, 0.79] | 0.52 [0.09, 0.74] | 0.31 [0.04, 0.44] | 0.72 [0.55, 0.87] | 0.54 [0.16, 0.80] | 0.25 [0.01, 0.42] |
Flood windows = issue times from 6 h before rise onset to the peak of the >= 10 ft events (493 rows, 4 events); persistence RMSE there is 0.52, 1.95 and 5.20 ft at 15 m, 1 h and 3 h.
**Findings.** (1) A two-parameter damped trend is as good as or better than ridge and XGBoost inside flood windows up to 1 h and is close elsewhere; ridge is best at 3 h (the intervals overlap, so the ordering is not established). (2) **The event-weighted XGBoost chosen on validation is worse on test than the unweighted one** (1 h skill 0.52 versus 0.62), so the validation gain from weighting did not transfer; sample weighting has not been shown to help. (3) H2 features did not beat H on validation (mean event-window RMSE 1.034 versus 1.022). (4) No model is distinguishable from the others by these intervals. Blocked CV (non-causal, 20 events) shows a similar pattern: at 1 h or less the damped trend and ridge differ by only 0.003 to 0.015 ft inside flood windows (ridge marginally ahead at 15 min, trend at 30 min and 1 h), and at 3 h the flood-window RMSE is ridge 3.75, trend 3.92, XGBoost 3.99 ft.

### 4.2 Fixed alarm rule (transparent baseline), TEST (exploratory), early hits / events and false-alarm episodes / alarm episodes
| Target (events, storm clusters) | model | 1 h | 3 h |
|---|---|---|---|
| stage >= 10 ft (4, 4) | damped trend | 4/4, FA 1/6 | 4/4, FA 1/6 |
| | ridge | 4/4, FA 0/5 | 4/4, FA 2/7 |
| | XGBoost | 3/4, FA 0/5 | 3/4, FA 1/6 |
| rise >= 4 ft/3 h (7, 7) | damped trend | 7/7, FA 2/10 | **1/7**, FA 1/4 |
| | ridge | 5/7, FA 2/9 | 2/7, FA 3/8 |
| | XGBoost | 5/7, FA 1/8 | 2/7, FA 2/6 |
| official action 25 ft (3, 2) | ridge / trend / XGBoost | 3/3 each | 2/3 each |
Median lead times are 0.25 to 1.9 h. Full tables including late detections, CSI and false alarms per year: `PHASE1B_TABLES.md`.

## 5. Probability-based event detection (your item 1)
Targets: stage >= 10 ft, >= 15 ft, rise >= 4 ft/3 h, rise >= 8 ft/3 h, at four horizons; logistic regression, XGBoost-plain, XGBoost-weighted on feature set H2. **Threshold chosen on validation only** (row-level F2, which favours recall). Official thresholds are not modelled (the training period holds only 3 action-stage events). **The rise >= 8 ft/3 h target has no selectable threshold** (one validation event, 11 positive rows, below the pre-registered 30-row minimum) and is therefore reported as not evaluated.

### 5.1 TEST (exploratory): early hits / events [95% CI], false-alarm episodes / alarm episodes, episode precision, median lead
| Target (events, clusters) | h | learner | theta (val) | hits | false alarms | precision | lead h |
|---|---|---|---|---|---|---|---|
| stage >= 10 ft (4, 4) | 1 h | logistic | 0.35 | 3/4 [0.19, 0.99] | 1/5 | 0.80 | 0.75 |
| | 1 h | XGB-plain | 0.50 | 3/4 | 2/6 | 0.67 | 0.50 |
| | 1 h | XGB-weighted | 0.90 | 4/4 [0.40, 1.00] | 1/5 | 0.80 | 0.88 |
| | 3 h | logistic | 0.35 | 4/4 | 2/8 | 0.75 | 0.88 |
| | 3 h | XGB-plain | 0.25 | 3/4 | 5/9 | 0.44 | 0.50 |
| | 3 h | XGB-weighted | 0.75 | 4/4 | 9/13 | 0.31 | 1.12 |
| rise >= 4 ft/3 h (7, 7) | 1 h | logistic | 0.05 | 6/7 [0.42, 1.00] | 7/14 | 0.50 | 0.75 |
| | 1 h | XGB-weighted | 0.80 | 6/7 | 7/14 | 0.50 | 0.62 |
| | 3 h | logistic | 0.02 | 5/7 [0.29, 0.96] | 10/16 | 0.38 | 0.75 |
| | 3 h | XGB-plain | 0.05 | 6/7 [0.42, 1.00] | 24/31 | 0.23 | 1.00 |
| | 3 h | XGB-weighted | 0.20 | 6/7 | 52/60 | 0.13 | 1.12 |
Stage >= 15 ft (2 events): all learners 2/2 at 1 h and 3 h; at 3 h false-alarm episodes 4/7 (logistic), 8/12 (XGB-plain), 18/22 (XGB-weighted). Late detections in the rows above: stage >= 10 ft has 1 late detection for logistic (1 h) and for XGB-plain (1 h and 3 h); none elsewhere.

**Findings.** (1) For stage exceedance (>= 10 ft) the probability models are **not better** than the fixed rule on the same events (fixed ridge: 4/4 hits with 0 or 2 false alarms). (2) For the rapid-rise indicator at 3 h the probability models detect 5 to 6 of 7 events, against 1 to 2 of 7 for the fixed rule, but only by raising many false alarms: episode precision 0.13 to 0.38. The validation-chosen thresholds are very low (0.02 to 0.20) because F2 rewards recall and validation holds only 6 such events; **a recall-weighted threshold selected on a handful of events does not transfer cleanly**. (3) A descriptive threshold sweep on test (never used for selection) shows no threshold giving both good recall and precision at 3 h for this target: logistic theta 0.1 gives 3/7 hits with 3 false alarms in 8 episodes; XGBoost-plain theta 0.3 gives 3/7 with 2/7; XGBoost-weighted theta 0.9 still gives 4/7 with 10/15. (4) Row-level at the chosen thresholds, the 3 h rise target has precision 0.23 to 0.45, recall 0.51 to 0.56 and average precision 0.46 to 0.50 (112 positive rows). Logistic regression is as good as or better than XGBoost throughout, which again suggests the available information (stage history only) is the limit, not model capacity.
**Blocked CV (non-causal; 27 rise events, theta from the chronological validation applied unchanged, an approximation):** rise >= 4 ft/3 h at 3 h detects 21/27 (logistic), 24/27 (XGB-plain), 25/27 (XGB-weighted) with false-alarm episodes 44/67, 110/137 and 416/445 (precision 0.34, 0.20, 0.07). Stage >= 10 ft at 3 h: 18/20 to 19/20 hits with precision 0.63 (logistic), 0.42 (XGB-plain), 0.39 (XGB-weighted).

## 6. Deep-learning sequence (your item 6)
Per your sequencing I have **not** trained LSTM, GRU or Transformer models. The draft protocol (`docs/PHASE1C_DL_PROTOCOL.md`) keeps the same targets, horizons, splits, masking, event rules and metrics; uses 24 h input windows; fixes 5 seeds per model, reports every seed, saves configs, seeds, predictions, checkpoints (SHA-256) and per-event tables; and compares deep models with paired storm-cluster bootstrap intervals against the best classical baseline. The hybrid is excluded. The frozen classical predictions and configuration hashes are in `reports/phase1b/frozen/`.

## 7. What this does and does not show
- **Shown (exploratory):** stage-history-only baselines reduce error versus persistence at all horizons; a simple damped trend is hard to beat inside floods at 1 h or less; learned models did not clearly beat it; event weighting did not help; rain features (ERA5 or daily gauges) did not help under the pre-registered rule; probability detection recovers more 3 h rapid rises than the fixed rule, at a large false-alarm cost.
- **Not shown:** that any of this works for official flood stages, in real time, at another gauge, or on an untouched period. Interval widths mostly span from near zero to about 0.8 in skill at 1 h and 3 h, and event rates rest on 2 to 7 independent events.
- **Caveats on my own choices:** F2 on validation is a recall-heavy criterion fixed in advance; it yields many false alarms. Whether that trade-off is acceptable is an operational question I cannot settle from this data.

## 8. Decisions for your review
1. Approve starting the LSTM/GRU/Transformer baselines under `PHASE1C_DL_PROTOCOL.md`? Open items: 24 h versus 72 h windows, joint versus per-horizon heads, probability head now or later.
2. Probability thresholds: keep the validation-F2 rule, or pre-register an alternative for a second experiment (for example the lowest false-alarm rate achieving a stated recall on validation, or a false-alarm-per-year cap)? Either must again be fixed before it is run.
3. Earthdata credentials for NLDAS-2 (you must create and place them).
4. Whether to drop sample-weighting and the H2 additions from further work, since neither helped.
5. Whether to run a first discharge-forecasting experiment on the separate 1998-2007 dataset.
6. Untouched evaluation: frozen predictions and hashes exist; any flood events after 2026-11-22 could serve as a prospective check.

## 9. Files and reproduction
`python scripts/run_phase1b.py` then `python scripts/make_phase1b_tables.py`. Supporting: `scripts/fetch_ghcnd.py`, `scripts/build_gauge_rain.py`, `scripts/build_discharge_dataset.py`, `scripts/compare_deviation3.py`, `scripts/run_phase1a.py --legacy --out ...`. Outputs: `reports/phase1b/` (tables, frozen artifacts, `results.json`), `reports/gauge_rainfall/`, `reports/discharge_pre2007/`, `reports/DEVIATION3_COMPARISON.md`, `reports/phase1a_original_strict/`.
