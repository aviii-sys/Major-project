# Phase 1C Report: LSTM, GRU and Transformer Regression Baselines

Status: for review. Protocol (fixed before training): `docs/PHASE1C_DL_PROTOCOL.md`. **Only the three regression baselines were trained. No probability head, ablation, discharge experiment or hybrid has been implemented.** Result tables: `reports/phase1c/tables/`; figures: `reports/phase1c/figures/`; runs, configs, checkpoints, predictions and hashes: `reports/phase1c/runs/` (`manifest.json`). Stage in feet, timestamps UTC.

## 0. Read this first
- **Every test-period number (2022-01-01 onward) is exploratory.** The test period was inspected in earlier phases and during protocol deviation 3 (a feature-eligibility defect found after viewing test output, documented in `reports/DEVIATION3_COMPARISON.md`). Nothing here was tuned on test: hidden sizes were chosen on validation with seed 0 only, and test predictions come from best-validation checkpoints.
- Test events are few: the >= 10 ft flood windows contain 4 events (493 rows, **only 8 bootstrap groups**, so intervals there are fragile); the official >= 25 ft events are 3 events from 2 storms, two of them USGS-provisional 2026 data. **No claim of flood-warning capability or generalization is made.**
- Same rows, splits and evaluation code as Phase 1B: the classical rows reproduce the Phase 1B numbers exactly (max RMSE difference 6.5e-9; 176 detection rows with zero mismatches; verified before the final evaluation).

## 1. Configuration actually run
24 h input window (96 steps), hydrology-only channels (stage relative to current stage, 15-min change, missing mask) plus current stage and window-missing fraction; shared encoder (LSTM, GRU, Transformer encoder) with four horizon-specific heads; per-horizon scaled MSE with equal horizon weights; Adam 1e-3, batch 512, 120,000 random training rows per epoch, patience 6, at most 40 epochs, 5 seeds (0-4) per model, every seed reported. No H2 features, sample weighting, rain or gauge inputs.
**Hidden size** (seed 0, validation event-window RMSE, protocol rule): LSTM 64 (1.004 versus 1.015 for 32), GRU 64 (0.984 versus 0.999), Transformer 64 (0.980 versus 1.000). All three picked 64; differences are about 1-2%.
**Pre-registered best classical baseline** (lowest validation event-window RMSE, computed before any deep test evaluation): **XGBoost H** at 1.0219, with the damped trend at 1.0231 and ridge H at 1.0336. The margin is 0.001 ft, so this choice is nearly arbitrary; the report therefore also shows comparisons against the damped trend.
**Training:** LSTM about 1.5 min per run (best epoch 7-17), GRU 3.1 min (best epoch 11-32), Transformer 6.7 min (best epoch **1-15**). Best validation scaled loss across seeds: LSTM 0.287-0.309, GRU 0.276-0.301, **Transformer 0.319-0.363**. The Transformer trained unstably (seed 1 peaked at epoch 1 and never improved).

## 2. Stage forecast error, TEST (exploratory), RMSE in ft (deep models: seed-mean, sd across 5 seeds in brackets)
**All test rows (152,084 rows at 1 h, 275 bootstrap groups; mostly quiet river)**
| Model | 15 m | 30 m | 1 h | 3 h |
|---|---|---|---|---|
| persistence | 0.035 | 0.066 | 0.127 | 0.336 |
| damped trend | 0.019 | 0.037 | 0.079 | 0.281 |
| ridge H | 0.019 | 0.037 | 0.079 | 0.259 |
| XGBoost H | 0.019 | 0.037 | 0.079 | 0.280 |
| LSTM | 0.018 (0.001) | 0.036 (0.001) | 0.076 (0.001) | 0.252 (0.004) |
| GRU | **0.017** (0.001) | **0.034** (0.001) | **0.074** (0.001) | **0.247** (0.004) |
| Transformer | 0.022 (0.001) | 0.044 (0.002) | 0.090 (0.003) | 0.276 (0.005) |

**Flood windows of the >= 10 ft events (issue times from 6 h before rise onset to the peak)**
| Model | 15 m | 30 m | 1 h | 3 h |
|---|---|---|---|---|
| persistence | 0.522 | 1.017 | 1.949 | 5.202 |
| damped trend | **0.225** | **0.509** | 1.121 | 4.322 |
| ridge H | 0.252 | 0.537 | 1.171 | 4.059 |
| XGBoost H | 0.261 | 0.551 | 1.179 | 4.497 |
| LSTM | 0.265 (0.013) | 0.545 (0.020) | 1.164 (0.028) | 4.041 (0.084) |
| GRU | 0.246 (0.015) | 0.518 (0.022) | **1.114** (0.027) | **3.962** (0.099) |
| Transformer | 0.331 (0.023) | 0.670 (0.044) | 1.389 (0.074) | 4.443 (0.128) |
Skill versus persistence, all rows (95% interval): GRU 0.76 [0.64, 0.83] at 15 m, 0.66 [0.24, 0.80] at 1 h, 0.46 [0.07, 0.62] at 3 h; ridge 0.71, 0.61, 0.41 [0.02, 0.58]; XGBoost 0.71, 0.62, 0.30 [0.07, 0.41]; Transformer 0.58, 0.49, 0.32.

## 3. Paired comparisons (pre-registered rule: a deep model is called better or worse only if the paired storm-cluster interval of the RMSE difference excludes zero)
Differences in ft, deep seed-mean minus reference, negative = deep better; `*` = interval excludes zero. 36 intervals per reference were examined with no multiplicity correction.
| Comparison (TEST) | 15 m | 30 m | 1 h | 3 h |
|---|---|---|---|---|
| GRU minus XGBoost H, all rows | -0.001 * | -0.003 * | -0.005 * | -0.033 * |
| GRU minus XGBoost H, flood windows | -0.015 * | -0.033 * | -0.064 * | -0.535 * |
| GRU minus damped trend, all rows | -0.002 | -0.002 | -0.005 * | -0.033 * |
| GRU minus damped trend, flood windows | +0.022 | +0.010 | -0.006 | -0.360 * |
| LSTM minus XGBoost H, flood windows | +0.003 | -0.006 | -0.015 | -0.455 * |
| LSTM minus damped trend, flood windows | +0.040 | +0.037 | +0.043 | -0.280 |
| Transformer minus XGBoost H, all rows | +0.004 * | +0.007 * | +0.012 * | -0.004 |
| Transformer minus XGBoost H, flood windows | +0.070 * | +0.119 * | +0.210 * | -0.054 |
**Post-hoc, not pre-registered** (added because the pre-registered comparator, XGBoost H, is weaker than ridge H at 3 h on test; `tables/C2b_posthoc_vs_ridge_and_trend.csv`): GRU minus ridge H is -0.002 to -0.011 ft over all rows (all four intervals exclude zero), and in flood windows -0.018 to -0.077 ft at 30 min and 1 h (excluding zero) and at 3 h -0.097 [-0.176, +0.009] for the >= 10 ft windows (not excluding zero) and -0.145 [-0.243, -0.031] for the >= 4 ft/3 h rise windows (excluding zero). LSTM minus ridge H is mostly indistinguishable. The Transformer is not distinguishable from ridge H.

## 4. Detection with the fixed alarm rule applied to the regression forecasts (TEST; early hits / events, mean over seeds with the seed range)
| Target (events, storm clusters) | h | damped trend | ridge H | XGBoost H | LSTM | GRU | Transformer |
|---|---|---|---|---|---|---|---|
| official action 25 ft (3, 2) | 1 h | 3/3 | 3/3 | 3/3 | 3 (3-3) | 3 (3-3) | 2.4 (2-3) |
| | 3 h | 2/3 | 2/3 | 2/3 | 3 (3-3) | 2.8 (2-3) | 1.6 (1-2) |
| stage >= 10 ft (4, 4) | 3 h | 4/4 | 4/4 | 4/4 | 4 | 4 | 4 |
| rise >= 4 ft/3 h (7, 7) | 1 h | 7/7 | 6/7 | 6/7 | 5.4 (5-6) | 6.2 (6-7) | 6.2 (6-7) |
| | 3 h | 1/7 | 4/7 | 0/7 | 3.2 (2-5) | 3.6 (3-4) | 0.6 (0-3) |
| rise >= 8 ft/3 h (5, 4) | 3 h | 1/5 | 1/5 | 0/5 | 0 | 0.6 (0-2) | 0 |
There is no consistent detection advantage for the deep models: at 3 h the rapid-rise (>= 4 ft/3 h) hit counts of LSTM (3.2) and GRU (3.6) are similar to ridge H (4/7). False-alarm episodes per alarm episodes at 3 h are ridge 4/10, LSTM 1.8/7.0 and GRU 2.0/7.2 (seed means), and the Transformer largely fails there (0.6 of 7 hits). Counts are tiny (events and storm clusters above); the full table with false alarms and leads is `C3b_fixed_rule_detection_seed_summary.csv`.

## 5. The three official test events at 3 h (descriptive; 3 events, 2 storms; the two July 2026 events are provisional)
Peak forecast issued 3 h ahead divided by the observed peak, seed-mean (seed range for deep models): LSTM 0.97 (0.95-0.99), 0.89 (0.86-0.93), 0.98 (0.96-1.00); GRU 0.97 (0.95-1.00), 0.89 (0.84-0.93), 0.99 (0.96-1.01); Transformer 0.97, 0.84, 0.95; ridge H 0.90, 0.85, 0.95; damped trend 0.96, 0.84, 0.97; XGBoost H 0.89, 0.76, 0.92; persistence 0.88, 0.71, 0.90 (events in the order 2025-07-05, 2026-07-15, 2026-07-17). The deep models are slightly closer to the observed peaks, but the figure `fig2_test_official_events_3h.png` shows why this is not early warning: **every 3-hour forecast, deep models included, trails the sharp rise by roughly three hours and only catches up near the peak.** The gains are in the peak, recession and slower rises, not in anticipating onset.

## 6. What the results support
- **Supported (exploratory):** the GRU, and to a lesser degree the LSTM, give small but consistent RMSE reductions over XGBoost, ridge and the damped trend over all rows at every horizon, and at 3 h inside flood windows (GRU: 3.96 ft against 4.32 for the damped trend, 4.06 for ridge and 4.50 for XGBoost). Seed spread (sd 0.004 ft all rows at 3 h; 0.08-0.10 ft in flood windows) is smaller than these gaps for XGBoost and damped trend, but comparable to the GRU-ridge gap in flood windows.
- **Supported:** in flood windows at 15 and 30 min the damped trend is as good as the GRU (differences +0.022 and +0.010 ft, intervals including zero), so a two-parameter heuristic is still competitive for very short lead times.
- **Supported for this configuration only:** the Transformer encoder is worse than all classical baselines at 1 h or less and unstable across seeds. I have not diagnosed why (candidates: learning rate or warm-up, positional encoding, data size, overfitting of 355k correlated windows). It would be wrong to conclude from this that Transformers are unsuitable; this was a single, untuned configuration, chosen in advance.
- **Not supported:** that any deep model improves detection with the fixed alarm rule, anticipates event onset, or works for official flood stages.

## 7. Limitations
Test period exposed; very few events (8 bootstrap groups in flood windows); one gauge; no blocked cross-validation for deep models (about 100 additional trainings, deferred); a tiny architecture search (hidden size 32 or 64); MPS training is not bit-reproducible, so reruns will differ slightly (seed spread shown); intervals are conditional on the five trained seeds; multiple comparisons uncorrected; the pre-registered comparator is a coin flip against the damped trend. Hydrology-only input means rainfall information is absent by design.

## 8. Protocol deviations and disclosures (also in the protocol file)
1. A 2-epoch smoke run was executed to debug training; its outputs were deleted. 2. Before the final evaluation I ran the evaluation script on the LSTM and GRU predictions as a debug pass; its outputs (which contained test metrics) were written to a scratch folder, **not read**, and deleted after programmatic checks that compared only classical rows against Phase 1B. 3. The post-hoc comparison against ridge H (section 3) was added after seeing results and is labelled as such. 4. One figure title was shortened and the evaluation rerun; the results were identical.

## 9. Proposed next steps, for your review (nothing started)
Per your plan, controlled ablations one factor at a time: (1) 24 h versus 72 h window (GRU first, as the best configuration; LSTM for confirmation); (2) shared heads versus independent per-horizon models; (3) the gauge-antecedent side input as a controlled rainfall comparison; (4) a false-alarm-constrained probability experiment, with its cap pre-registered separately. Questions: should the Transformer's instability be investigated (a separate, pre-registered stabilisation experiment, for example learning-rate warm-up) before the window ablation, or left as is? Should I add blocked cross-validation for GRU and LSTM (seed 0, 6 trainings each, one per fold) to get out-of-sample forecasts for all 20 historical >= 10 ft events? The hybrid model is not started.

## 10. Files
Protocol `docs/PHASE1C_DL_PROTOCOL.md`; registry `experiments/REGISTRY.md`; code `src/flashflood/{experiment,seq,dl}.py`, `scripts/run_phase1c_dl.py`, `scripts/eval_phase1c.py`, `scripts/posthoc_phase1c_vs_ridge.py`; tests `tests/test_phase1c.py` (24 tests pass in total with earlier phases). Reproduce: `python scripts/run_phase1c_dl.py` then `python scripts/eval_phase1c.py`.
