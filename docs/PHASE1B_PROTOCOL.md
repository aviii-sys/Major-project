# Phase 1B (classical strengthening) Protocol: fixed BEFORE any Phase 1B model was trained

Written 2026-11-22. Extends `docs/PHASE1A_PROTOCOL.md` (targets, horizons, splits, masking, event/alarm/matching definitions are unchanged unless stated here).
No LSTM, GRU, Transformer or hybrid is trained in this phase.

## 0. Integrity statement (read first)
- The chronological **test period (2022-01-01 onward) has already been inspected** (Phase 1A, and the defect found in deviation 3). Every test-period number produced in Phase 1B is therefore labelled **exploratory**, not confirmatory.
- All model, feature-set and hyperparameter **selections use validation data only** (2018-2021). The test set is scored once per final configuration. The blocked cross-validation (non-causal) is supplementary and never used for selection.
- The original Phase 1A results (`reports/phase1a_original_strict/`) and the corrected ones (`reports/phase1a/`) are both preserved; `reports/DEVIATION3_COMPARISON.md` compares them.
- A genuinely untouched evaluation requires data that did not exist at freeze time. Final model configurations and prediction files are saved with hashes in `reports/phase1b/frozen/`; any flood events after 2026-11-22 can later serve as a prospective check. Until then, no confirmatory claim is made.
- Validation has very few independent events (stage >= 10 ft: 5; >= 15 ft: 2; rise >= 4 ft/3 h: 6; rise >= 8 ft/3 h: 1). Selection rules below are therefore deliberately low-dimensional (a handful of choices), and sensitivity tables are reported so that readers can see how fragile each choice is.

## 1. Eligibility v2 and evaluable events (replaces Phase 1A rule 80% / full feature set)
- A row is **eligible** if stage s(t), d_15m, d_30m, d_1h and the target s(t+h) are valid. Long-lag features may be missing: XGBoost uses native missing-value handling; ridge and logistic regression fill missing differences with 0, missing running maxima with s(t), and add an indicator `long_missing`. (Reason: Phase 1A deviation 3 diagnostics showed that a 21 h outage just before a 2024 event made the event unevaluable only because the feature set demanded 24 h history, not because forecasting was impossible.)
- To compare feature sets fairly, every model in a comparison is scored on the rows valid for all feature sets in that comparison (this only removes rows where rain or gauge inputs do not exist, i.e. the last days of the record).
- An event is **not evaluable** at horizon h only if fewer than 50% of the issue times that could earn lead credit (t0 - h - 1 h to t0) satisfy minimal-input eligibility, i.e. the current stage or the target is itself missing. Not-evaluable events are listed with the cause. The Phase 1A 80% rule is retired.

## 2. Feature sets
- **H**: Phase 1A hydrology features. **H2** = H + `accel_1h` (d_1h minus the 1 h change one hour earlier) + `max_step_1h` (largest 15-min rise in the last hour) + `rel_base7d` (stage minus its 7-day minimum, needs >= 25% of the window).
- **R**: ERA5 rain features (Phase 1A). **G**: gauge-product antecedent features: last completed observation-day basin rainfall (product day D available only from 15:00 UTC on D), and 3-, 7-, 30-day sums ending at that day; NaN if the day is missing or flagged low-coverage.
- Compared on validation (XGBoost, lambda = 0): H, H2, H2+R, H2+G, H2+R+G. **Adoption rule (one choice for all horizons and models):** the set with the lowest mean validation event-window RMSE over the four horizons, but a richer set replaces H2 only if it is at least 5% better; otherwise H2. Event windows: issue times from 6 h before rise onset to the peak, for validation events of >= 10 ft and of >= 4 ft/3 h rises.

## 3. Trend extrapolation v2
change = phi x h(hours) x rate, rate = (stage change over window w) / w; w in {15 min, 30 min, 1 h}, phi in {0.25, 0.5, 0.75, 1.0} (12 candidates). One candidate per horizon, chosen by validation event-window RMSE.

## 4. Event-aware (sample-weighted) objectives
Training weight of row i = 1 + lambda x elevated_i, elevated_i = [s(t) >= 5 ft or d_3h >= 1 ft] (known at issue time, so no target information enters the weights). lambda in {0, 10, 50}. Applied to ridge and XGBoost; **one lambda per model type**, chosen by the lowest mean validation event-window RMSE across the four horizons (ties: smaller lambda). All-row validation RMSE is reported next to it; if the chosen lambda worsens all-row validation RMSE by more than 10% relative to lambda = 0, lambda = 0 is kept.

## 5. Probability-based event detection (separate experiment)
- **Targets:** experimental stage >= 10 ft, stage >= 15 ft, rise >= 4 ft/3 h, rise >= 8 ft/3 h; horizons 15 m, 30 m, 1 h, 3 h. Labels: exceedance y(t,h) = [s(t+h) >= T]; rapid rise y(t,h) = [s(t+h) - s(t+h-3 h) >= R] (both ends valid). **Official thresholds are not modelled**: the training period holds only 3 action-stage events (E01-E03) and 2 minor-stage events, too few to fit or validate a probability model. They remain descriptive (fixed alarm rule).
- **Learners:** logistic regression (C = 0.1, standardised); XGBoost-plain (depth 3, scale_pos_weight 1); XGBoost-weighted (depth 3, scale_pos_weight = clip(sqrt(negatives/positives), 1, 30)). Up to 400 trees, learning rate 0.05, early stopping on validation log-loss. Features: the adopted set (section 2).
- **Operating threshold, validation only:** theta chosen per (learner, target, horizon) as the value in {0.02, 0.05, 0.10, ..., 0.90} that maximises row-level F2 (beta = 2, favouring recall) on validation rows; ties pick the higher theta. A target/horizon needs >= 30 positive validation rows, otherwise it is reported as "no threshold selectable". The number of independent validation events behind each theta is reported beside it. **Theta is never adjusted using test results.**
- **Alarm:** p >= theta triggers a raw flag; same 1 h hold hysteresis, event matching, early/late/miss, false-alarm episode and lead-time definitions as Phase 1A. The fixed regression-derived alarm rule stays as the transparent baseline on the same rows.
- **Reported per cell:** event-level confusion counts (early hits, late detections, misses, false-alarm episodes), POD (recall), precision (1 - FAR, episode level), FAR, CSI, median and range of lead time, false alarms per year, exact binomial 95% intervals, and the numbers of **independent events and distinct storm clusters** behind them; row-level precision/recall at theta; Brier score, log-loss and a 10-bin calibration table on test; a descriptive threshold sweep on test (never used for selection).
- **Blocked CV (non-causal):** probabilities from out-of-fold models with the theta from the chronological validation applied unchanged (an approximation, flagged), plus threshold-free average precision.

## 6. Regression experiment outputs
Persistence, trend v2, ridge and XGBoost (adopted features, chosen lambda), compared with the Phase 1A models on validation, test (exploratory) and blocked CV; same metrics, bootstrap intervals and per-event tables as Phase 1A.

## 7. Claims
No statement about flood-warning capability, generalization, or operational use is made. Statements about official categories remain descriptive (3 test events, 2 storms).

## 8. Next phase
Deep sequence baselines are specified, not run, in `docs/PHASE1C_DL_PROTOCOL.md` (draft, awaiting review).

## Deviations and clarifications (recorded after the full run; none changed a selection rule)
1. **Smoke run seen first.** A quick-mode run (80-tree cap, no gauge features) was executed before the full run to debug the code. Its outputs were inspected (selected feature set, lambda, the "no threshold selectable" outcome for the rise >= 8 ft target). No rule, grid or threshold in this protocol was changed because of it, and the full run reproduced the same adopted feature set (H2) and lambdas (ridge 0, XGBoost 10).
2. **Probability models are not refit on train + validation.** Section 5 did not say; test and blocked-CV probabilities come from the train-only fit (blocked-CV from fold-specific fits), so that theta, selected on validation predictions of that same model, stays on the same probability scale.
3. **False-alarm accounting:** alarm episodes are matched against ALL events (including any not evaluable) while POD, CSI etc. use evaluable events. Phase 1A matched against evaluable events only. In Phase 1B no event is marked not evaluable, so this has no effect on the reported numbers.
4. **Gauge product construction fix (before any model used it).** My first build of the gauge product wrongly excluded almost all CoCoRaHS stations (their attributes carry no observation time); the rule was corrected and checked empirically (see `reports/gauge_rainfall/README.md`) before any Phase 1B feature or model was built from the product.
5. **Rule applied literally even where it looks fragile.** The adopted feature set is H2 although H scored slightly better than H2 on validation; the 5% rule only governs sets richer than H2. Lambda 10 was chosen for XGBoost on a 1% validation difference and did not help on test (reported as such).
