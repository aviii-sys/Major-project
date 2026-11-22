# Phase 1E Report: GRU input window 24 h versus 72 h

**Retrospective blocked chronological cross-validation, NOT untouched validation; every number is exploratory.** Protocol (fixed before any model was trained): `docs/PHASE1E_PROTOCOL.md` (experiment E16). Only Phase 1E was run: no hybrid, Transformer diagnostic, probability head, discharge forecasting or new inputs. All numbers below are copied from `reports/phase1e/tables/` (table names in brackets).

## 0. Headline
- **Pre-registered decision: 72 h is NOT adopted; the 24 h window stays the default.** Horizons with consistent improvement in flood windows: **0 of 4**. Three of four all-row differences (15 min, 30 min, 1 h) are significantly *worse* for 72 h, by 1.2% to 1.6% of the 24 h RMSE (`E3`).
- Regression: 72 h is not better and is slightly worse almost everywhere. Pooled 72 h minus 24 h RMSE is positive in all 16 subset x horizon cells (+0.9% to +1.9% of the 24 h error); the interval excludes zero (on the 72 h-worse side) in 3 of 4 all-row cells and in 5 of 12 flood-subset cells (`E1b`). The differences are small compared with the gap between the GRU and ridge, and with the spread between seeds.
- Detection and onset: no sign of improvement. Fixed-rule hits are equal or lower for 72 h (rapid rises at 3 h: 3.7 versus 5.3 of 25 on seed means, with ranges that overlap), and the 3 h peak-capture ratio of every official event is within 0.025 of the 24 h value (`E6b`, `E4`). Regression changes are not read as detection changes, and none is seen either way.
- What this means for the research question: stage history older than 24 h did not give this GRU extra usable information. This agrees with the upstream-input finding (`docs/UPSTREAM_INPUT_FEASIBILITY.md`): the missing information is about where rain fell, which a longer stage history cannot contain. It does not show that no longer-context model could help.

## 1. What was run
36 trainings (6 folds x 3 seeds x 2 windows), matched seeds 0-2, folds identical to Phase 1D (asserted in the runner), GRU hidden 64, same optimizer, features, targets, horizons and preprocessing. Training rows are identical for both windows (rows with at least 72 h of history). Evaluation rows are the Phase 1B/1D eligible held-out rows, identical for both windows.
- **Training diagnostics (`E8`):** epochs run 16.3 (24 h) versus 16.4 (72 h) on average; best epoch 9.3 versus 9.4; the 72 h model reached a lower best validation loss than the matching 24 h model in 7 of 18 fold-seed pairs. Median run time 1.8 min (24 h) versus 5.2 min (72 h), about 2.9 times; the 72 h mean in the table (12.1 min) is inflated by one run (fold 5, seed 1) whose clock includes about two hours of machine sleep (7,427 s); without it the 72 h mean is 5.5 min over 17 runs.
- **Reproducibility (`E7`):** the new 24 h seed-0 predictions equal the Phase 1D GRU seed-0 predictions exactly (RMSE of the difference 0 ft at all four horizons), although the two runs differ in training rows by the first two days of the record. So the training pipeline was reproducible on this machine for this seed; this does not say anything about run-to-run noise on other hardware.

## 2. Pooled results (`E1_pooled_metrics`)
Seed-mean RMSE in ft (sd across the three seeds is 0.0001-0.0027 for all rows and 0.003-0.12 for the flood subsets). Rows and storm-bootstrap groups: all rows 502,382 / 502,161 / 501,803 / 500,393 rows (837 groups; 835 at 3 h); flood windows of >= 10 ft events 1,552 rows (27 groups); rapid-rise windows 1,034 rows (39 groups); rising-water rows 947 rows (119 groups).

| Subset | Horizon | GRU 24 h | GRU 72 h | persistence | damped trend | ridge H | XGBoost H |
|---|---|---|---|---|---|---|---|
| all rows | 15 m | 0.0208 | 0.0210 | 0.0333 | 0.0208 | 0.0202 | 0.0209 |
| all rows | 30 m | 0.0386 | 0.0392 | 0.0629 | 0.0387 | 0.0373 | 0.0398 |
| all rows | 1 h | 0.0803 | 0.0815 | 0.1194 | 0.0826 | 0.0784 | 0.0832 |
| all rows | 3 h | 0.2572 | 0.2601 | 0.3078 | 0.2650 | 0.2555 | 0.2608 |
| flood windows >= 10 ft | 15 m | 0.2888 | 0.2921 | 0.4768 | 0.2538 | 0.2507 | 0.2772 |
| flood windows >= 10 ft | 30 m | 0.5629 | 0.5732 | 0.9202 | 0.4974 | 0.4975 | 0.5542 |
| flood windows >= 10 ft | 1 h | 1.1994 | 1.2191 | 1.7709 | 1.1567 | 1.1111 | 1.2019 |
| flood windows >= 10 ft | 3 h | 4.0746 | 4.1158 | 4.6873 | 4.0172 | 3.9601 | 4.0657 |

The rapid-rise and rising-water subsets show the same ordering (`E1`). The reference models are unchanged from Phase 1D: ridge H and the damped trend have a lower point-estimate RMSE than either GRU window at all four horizons in flood windows (the Phase 1D intervals showed this to be significant only at 15 and 30 min), so the Phase 1D conclusion stands whichever window is used.

## 3. Paired differences, 72 h minus 24 h (`E1b_paired_72_minus_24`)
Negative = 72 h better. Pooled difference with 95% storm-cluster bootstrap interval (2,000 resamples; conditional on the three trained seeds), then the three per-seed differences.

| Subset | Horizon | Pooled difference (ft) | 95% interval | Seeds 0 / 1 / 2 | Seeds where 72 h better | Folds where 72 h better |
|---|---|---|---|---|---|---|
| all rows | 15 m | +0.0003 | [+0.0000, +0.0005] | +0.0004 / +0.0004 / -0.0000 | 1 of 3 | 2 of 6 |
| all rows | 30 m | +0.0006 | [+0.0002, +0.0010] | +0.0009 / +0.0008 / +0.0002 | 0 of 3 | 1 of 6 |
| all rows | 1 h | +0.0011 | [+0.0001, +0.0024] | +0.0022 / +0.0012 / -0.0000 | 1 of 3 | 2 of 6 |
| all rows | 3 h | +0.0029 | [-0.0002, +0.0058] | +0.0050 / +0.0027 / +0.0008 | 0 of 3 | 2 of 6 |
| flood >= 10 ft | 15 m | +0.0033 | [-0.0011, +0.0089] | +0.0072 / +0.0073 / -0.0044 | 1 of 3 | 3 of 6 |
| flood >= 10 ft | 30 m | +0.0103 | [+0.0032, +0.0190] | +0.0198 / +0.0142 / -0.0027 | 1 of 3 | 0 of 6 |
| flood >= 10 ft | 1 h | +0.0198 | [-0.0006, +0.0483] | +0.0525 / +0.0243 / -0.0178 | 1 of 3 | 2 of 6 |
| flood >= 10 ft | 3 h | +0.0413 | [+0.0028, +0.0853] | +0.1064 / +0.0379 / -0.0213 | 1 of 3 | 2 of 6 |

Rapid-rise windows and rising-water rows give the same picture: positive pooled differences at every horizon, 1 of 3 seeds favouring 72 h at every horizon, and 72 h better in at most 4 of 6 folds (`E1b`). Seed 2 is the one seed that favours 72 h in the flood subsets; seeds 0 and 1 do not. The seed-to-seed range of the difference is larger than its pooled value in every flood-window cell, so a single seed can show either answer. **No configuration was selected by its best seed.** MAE differences are also tiny and mostly positive (`E1b`).

## 4. Per fold and per event (`E2_per_fold_paired`, `E4_per_event`, `E4b_per_event_summary`)
- **Folds, flood windows >= 10 ft, 3 h** (72 h minus 24 h, ft): fold 1 -0.011, fold 2 +0.002, fold 3 +0.016, fold 4 -0.010, fold 5 +0.042, fold 6 +0.137. The pooled +0.041 is driven mainly by fold 6 (the 2025-2026 events, 323 of 1,552 rows; its 1 h difference is +0.081 against -0.012 to +0.015 in the other five folds). The pooled disadvantage of 72 h in flood windows is therefore probably dominated by fold 6; I have not computed the pooled value without it because that would be a new post-hoc analysis, so this is a reading of the fold table only. Fold 6 includes provisional 2026 data.
- **Events (18 evaluated >= 10 ft events from 14 storm clusters), `E4b`:** events where the 72 h window RMSE is lower: 8 (15 min), 2 (30 min), 7 (1 h), 6 (3 h). The median per-event difference is positive at every horizon (72 h worse). At 1 h the largest worsenings are 2026-07-15 (+0.113 ft), 2025-07-05 (+0.076) and 2026-06-15 (+0.069); at 3 h 2026-07-15 (+0.160), 2025-07-05 (+0.138) and 2021-10-14 (+0.106); the largest improvements are small (3 h: 2018-10-17 -0.064, 2015-10-30 -0.031) (figure `fig2_per_event_differences.png`).
- **Peak capture for the official events** (3 h forecast issued before the peak, forecast divided by observed peak, 24 h / 72 h; descriptive): 2015-05-23 0.711 / 0.708; 2015-10-30 0.337 / 0.339; 2016-05-29 0.890 / 0.889; 2025-07-05 0.958 / 0.938; 2026-07-15 0.968 / 0.944 (provisional data). `E4` lists five rows because the >= 10 ft event catalogue merges the two official 2026 events (peaks 25.04 and 36.75 ft) into one. 72 h is slightly lower at the two most recent events and indistinguishable at the other three.
- Heterogeneity: the sign of the difference changes between seeds, folds and events. There is no fold or event where 72 h gives a large gain, and one fold (6) where it is clearly worse.

## 5. Missing-data sensitivity (`E5_missing_data_sensitivity`, `E5b_missing_share`)
- Share of rows with any missing sample in the window: **72 h window 4.76% of all evaluation rows and 13.85% of flood-window rows; 24 h window 2.50% and 9.02%**. Rows with more than 5% of the 72 h window missing: 1.93% (all) and 10.95% (flood windows). Flood windows therefore carry more missing history than ordinary rows, and the longer window carries more of it.
- Stratifying by missing fraction (none / up to 5% / above 5%, by 72 h window and by 24 h window; 48 cells with row counts and groups in `E5`): 20 cells have the interval entirely on the "72 h worse" side, 25 include zero and **3 favour 72 h**. The 3 favourable cells are all in rows whose *24 h* window has more than 5% of samples missing: all rows at 3 h (-0.0057 ft [-0.0120, -0.0013]; 6,554 rows, 62 groups, about 1.3% of rows; relative -2.9%) and flood windows at 1 h and 3 h (88 rows from only 2 groups each, so the interval is not informative). 16 of the 48 cells rest on 2 or fewer storm groups and should not be interpreted.
- The 72 h penalty does not come from missing data: it is present in rows with complete windows (all rows with none missing, 15 min to 1 h: +0.0002, +0.0006, +0.0009 ft, intervals excluding zero; flood windows with none missing, 30 min and 3 h: +0.0093 and +0.0326 ft, intervals excluding zero).
- The one hint of a 72 h benefit, at the 3 h horizon when the preceding 24 h are substantially incomplete, is plausible (more intact earlier context) but is a small effect in 1.3% of rows, comes from a stratification with 48 cells and no multiplicity correction, and does not change any flood-window result or the decision.

## 6. Rising-water rows and event detection (`E1b`, `E6`, `E6b`)
- **Rising-water rows** (947 rows, 119 groups; 1-h rise of at least 0.5 ft at issue time): 72 h minus 24 h is +0.0048, +0.0133, +0.0255, +0.0591 ft at 15 min to 3 h (intervals: only 30 min excludes zero, [+0.0036, +0.0254]); 1 of 3 seeds favours 72 h at every horizon. A longer history did not help when the water was already rising.
- **Fixed alarm rule, hits per seed (seed mean [min-max], 24 h versus 72 h), events and storm clusters beside every count (`E6b`):**

| Definition | Horizon | Events (clusters) | 24 h hits | 72 h hits | 24 h false-alarm episodes | 72 h false-alarm episodes |
|---|---|---|---|---|---|---|
| rise >= 4 ft in 3 h | 1 h | 25 (22) | 22.7 [22-23] | 23.0 [23-23] | 7.0 | 6.7 |
| rise >= 4 ft in 3 h | 3 h | 25 (22) | 5.3 [3-7] | 3.7 [2-6] | 3.3 | 3.0 |
| rise >= 8 ft in 3 h | 1 h | 13 (10) | 11.0 [11-11] | 10.7 [10-11] | 1.0 | 1.0 |
| rise >= 8 ft in 3 h | 3 h | 13 (10) | 0 | 0 | 0 | 0 |
| stage >= 10 ft | 3 h | 18 (14) | 17 [17-17] | 17 [17-17] | 8.7 | 9.0 |
| official >= 25 ft | 1 h | 6 (5) | 5.0 [5-5] | 4.7 [4-5] | 0.7 | 0.3 |
| official >= 25 ft | 3 h | 6 (5) | 3.7 [3-4] | 3.3 [3-4] | 0.7 | 0.3 |

  Hit counts are early hits (alarm before the event began with the target overlapping the event); the counts are small and the seed ranges overlap, so 72 h is at best equal. The 3 h rapid-rise difference (5.3 versus 3.7) is about as large as the seed-to-seed range and I do not interpret it as a real loss. All experimental definitions are experimental; only the official 25 ft rows relate to NWS stages, and with 6 events (5 storms) no detection claim can be made.
- **Onset timing:** I did not produce an observed-versus-forecast onset plot for 72 h. The numbers give no sign of a change: the 3 h peak-capture ratio of the official events moves by at most 0.025 and no rapid-rise subset improves. The Phase 1D observation that 3 h forecasts trail sharp onsets by about 3 h is therefore not contradicted, but it is also not re-demonstrated for the 72 h model. A quick plot is cheap if you want it.

## 7. Decision under the pre-registered rule (`E3_decision_rule`)
Flood windows >= 10 ft; "consistent improvement" needs (i) pooled interval entirely below zero, (ii) 72 h better in at least 4 of 6 folds, (iii) 72 h better in 3 of 3 seeds.

| Horizon | Pooled difference [interval] | (i) | (ii) folds | (iii) seeds | Consistent | All rows significantly worse? |
|---|---|---|---|---|---|---|
| 15 min | +0.0033 [-0.001, +0.009] | no | 3 / 6 | 1 / 3 | no | yes |
| 30 min | +0.0103 [+0.003, +0.019] | no | 0 / 6 | 1 / 3 | no | yes |
| 1 h | +0.0198 [-0.001, +0.048] | no | 2 / 6 | 1 / 3 | no | yes |
| 3 h | +0.0413 [+0.003, +0.085] | no | 2 / 6 | 1 / 3 | no | no |

**0 of 4 horizons consistently improve; three horizons are significantly worse on all rows; 72 h is not adopted; the default stays 24 h** (`decision.json`). No criterion is close to being met, so the conclusion does not depend on the choice of interval method.

## 8. Interpretation and limitations
- **What the results support:** under this protocol, lengthening the GRU input from 24 h to 72 h gave no benefit in overall error, flood-window error, rising-water error or fixed-rule detection, and cost about three times the training time. The decision is made on the rule fixed beforehand.
- **What they do not show:** that longer context cannot help any model or any input set. Possible reasons for the absence of a gain are untested here: no new information in days 2 and 3 of stage history for rain-driven rises (consistent with the upstream-input finding); a longer sequence being harder to optimise with the inherited hyperparameters (hidden size 64, patience 6, 120,000 rows per epoch); more missing data in longer windows; and the same number of training rows having to support learning from three times as many input steps. I did not test any of these, and the 24 h versus 72 h comparison does not separate them.
- **Limitations:** three seeds only; six folds, 14 storm clusters evaluated, about 27 flood-window bootstrap groups, so intervals are wide and conditional on the three trained seeds; early folds train on little data; a single hidden size; hyperparameters inherited from Phase 1C; no multiplicity correction across the many cells in `E1b`, `E2`, `E5`; fold 6 and the two newest events include provisional 2026 data; the whole record has been inspected before, so everything is exploratory.
- **Consequences for the next step:** nothing here argues for building a 72 h context into a later model; the open question for the research guide remains whether to add upstream-gauge inputs (and, if so, what the central claim becomes). The Transformer diagnostic, hybrid, probability head, discharge forecasting and dashboard have not been started and are not approved yet.

## 9. Files and deviations
- Runs: `reports/phase1e/runs/fold{k}_gru_w{24|72}h_h64_s{seed}` (36 directories with configuration, history, checkpoint, predictions, SHA-256 manifest); tables `reports/phase1e/tables/E1..E8*` (csv and md); figures `reports/phase1e/figures/fig1_paired_differences.png`, `fig2_per_event_differences.png`; `reports/phase1e/oof_predictions.csv.gz`, `decision.json`, `fold_specification.csv`, `train.log`, `eval.log`; tests `tests/test_phase1e.py`; registry entry E16 (`experiments/REGISTRY.md`).
- Deviations (also in `docs/PHASE1E_PROTOCOL.md`): (1) a 2-epoch smoke run of all 36 trainings was used to debug the runner and its outputs were deleted before the real run (protocol deviation 1); (2) the Mac slept for about two hours during fold 5, seed 1, 72 h; training was paused, not altered, and was then protected with `caffeinate`, so no setting changed (the 7,427 s in `E8` is wall-clock time); (3) the tables come from the evaluation run recorded in `eval.log`, executed after all 36 trainings had finished; two table constructions in the script (`E4b`, `E5b`) were simplified before that run and the decision rule was not changed; (4) no post-hoc analysis beyond the pre-specified tables was added, and the one reading of the fold table without a new computation (the fold 6 contribution) is labelled as such.
- Reproduce: `python scripts/run_phase1e_window.py` then `python scripts/eval_phase1e.py` (resumable; the 36 runs took about 2 hours of compute on this Apple MPS laptop, excluding the sleep pause; evaluation takes about 35 s).
