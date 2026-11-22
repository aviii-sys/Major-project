# Phase 1D Report: Six-Fold Blocked Chronological Cross-Validation for GRU and LSTM

Status: for review. **Retrospective blocked chronological cross-validation. It is NOT untouched external validation**; the whole 2007-2026 record has been inspected in earlier phases and every number here is exploratory. Protocol (fixed before training): `docs/PHASE1D_PROTOCOL.md`. Experiment id E14, all outputs in `reports/phase1d/` (no earlier artifact was modified). **Only Phase 1D was run: no 72 h ablation (1E), no Transformer diagnostic (1F), no hybrid.** Stage in feet, timestamps UTC.

## 0. Headline
The GRU/LSTM advantage seen in Phase 1C **does not replicate out-of-fold**. Over 18 held-out >= 10 ft events (14 storm clusters), ridge H and the damped trend are as good as or better than both deep models; inside flood windows at 15 and 30 minutes the deep models are significantly **worse** than ridge H and the damped trend; at 1 h and 3 h no difference can be established. Detection with the fixed alarm rule is not better for the deep models either. All models, deep ones included, lag the onset of sharp rises by about three hours at the 3 h horizon.

## 1. Verification before running (your instruction)
All 36 Phase 1C checkpoint and prediction files match `manifest.json` (0 mismatches); re-running the Phase 1C evaluation reproduces its documented tables exactly (168-row regression table and the detection summary; scratch copy in `reports/phase1d/verification/`); the existing tests passed (24, now 33 with Phase 1D). Nothing was recreated or overwritten.

## 2. Design as run
Six held-out blocks, expanding-window forward chaining, each fold `train | 27 h 15 min embargo | validation | embargo | held-out block`; embargo = 24 h window + 3 h horizon + one step, so no training or validation target shares a timestamp with a held-out input window. All boundaries lie in quiet periods (no storm cluster in the 96 h before; none of the six nominal dates had to move), so **no storm cluster is split**. Scalers, target scales and early stopping use each fold's own earlier data only.
| Fold | Held-out block | Training rows | Training ends | Validation chunk | >= 10 ft events (storm clusters) |
|---|---|---|---|---|---|
| 1 | 2012-01-01 to 2014-12-31 | 108,826 | 2010-12-06 | 2010-12-07 to 2011-12-30 | 2 (2) |
| 2 | 2015 | 187,495 | 2013-03-07 | 2013-03-08 to 2014-12-30 | 3 (2) |
| 3 | 2016-2017 | 215,926 | 2013-12-29 | 2013-12-30 to 2015-12-30 | 4 (1) |
| 4 | 2018-2019 | 286,096 | 2015-12-30 | 2015-12-31 to 2017-12-30 | 4 (4) |
| 5 | 2020-2024 | 356,053 | 2017-12-29 | 2017-12-30 to 2019-12-30 | 2 (2) |
| 6 | 2025-01-01 to 2026-11-22 | 526,033 | 2022-12-30 | 2022-12-31 to 2024-12-30 | 3 (3) |
GRU and LSTM use exactly the Phase 1C architecture and hyperparameters (24 h window, hidden 64, shared encoder with four heads, Adam 1e-3, patience 6, at most 40 epochs, hydrology-only input), **seed 0**, six trainings each, no search and no refit. Classical comparators (persistence, damped trend, ridge H, XGBoost H) were fitted on the same folds with hyperparameters chosen on each fold's validation chunk and **no refit**, so deep and classical models see identical data.
**Event coverage** (`event_to_fold_mapping.csv`, `tables/D6*`): >= 10 ft events 20 in the catalogue, **18 evaluated from 14 storm clusters**, 2 excluded (2010-04-17 and 2010-09-08: they lie in the initial training segment, so no earlier data exist to train a model evaluated on them). >= 15 ft: 8 of 9 evaluated; rise >= 4 ft/3 h: 25 of 27 (22 clusters); rise >= 8 ft/3 h: 13 of 15 (10 clusters); **all 6 official >= 25 ft events (5 storms), 4 minor and 1 moderate are evaluated**. No event was excluded for missing inputs.

## 3. Pooled out-of-fold regression error (RMSE in ft)
**All out-of-fold rows** (about 502,000 rows, 837 storm/week bootstrap groups)
| Model | 15 m | 30 m | 1 h | 3 h |
|---|---|---|---|---|
| persistence | 0.033 | 0.063 | 0.119 | 0.308 |
| damped trend | 0.021 | 0.039 | 0.083 | 0.265 |
| ridge H | **0.020** | **0.037** | **0.078** | **0.256** |
| XGBoost H | 0.021 | 0.040 | 0.083 | 0.261 |
| GRU | 0.021 | 0.039 | 0.081 | 0.258 |
| LSTM | 0.021 | 0.039 | 0.081 | 0.257 |
**Flood windows of the evaluated >= 10 ft events** (1,552 rows, **27 bootstrap groups**)
| Model | 15 m | 30 m | 1 h | 3 h |
|---|---|---|---|---|
| persistence | 0.477 | 0.920 | 1.771 | 4.687 |
| damped trend | 0.254 | 0.497 | 1.157 | 4.017 |
| ridge H | **0.251** | **0.497** | **1.111** | **3.960** |
| XGBoost H | 0.277 | 0.554 | 1.202 | 4.066 |
| GRU | 0.288 | 0.562 | 1.210 | 4.092 |
| LSTM | 0.290 | 0.566 | 1.198 | 4.091 |
Flood windows of the rise >= 4 ft/3 h events (1,034 rows, 39 groups) give the same ordering (3 h: ridge 5.013, damped trend 5.110, GRU 5.120, LSTM 5.124, XGBoost 5.138). Skill versus persistence at 3 h, all rows: GRU 0.30, LSTM 0.31, ridge 0.31, XGBoost 0.28, damped trend 0.26 (intervals in `D1`).

## 4. Paired comparisons (storm-cluster bootstrap, deep model minus reference, ft; negative = deep better; * = interval excludes zero)
| Comparison | 15 m | 30 m | 1 h | 3 h |
|---|---|---|---|---|
| GRU minus ridge H, all rows | +0.001 | +0.001 | +0.003 | +0.003 |
| GRU minus ridge H, flood windows | **+0.037 [+0.006, +0.071]** * | **+0.064 [+0.003, +0.137]** * | +0.099 [-0.010, +0.220] | +0.132 [-0.019, +0.276] |
| GRU minus damped trend, flood windows | **+0.034 [+0.005, +0.064]** * | **+0.064 [+0.004, +0.127]** * | +0.054 | +0.075 |
| LSTM minus ridge H, flood windows | **+0.040** * | **+0.068** * | +0.087 | +0.131 |
| LSTM minus damped trend, flood windows | **+0.036** * | **+0.069** * | +0.041 | +0.074 |
| GRU minus XGBoost H, flood windows | +0.011 | +0.008 | +0.008 | +0.026 |
| GRU minus LSTM, flood windows | -0.002 | -0.004 | +0.012 | +0.001 |
On all rows the only intervals excluding zero are GRU versus XGBoost at 30 m (-0.001) and LSTM versus XGBoost at 1 h (-0.003), differences of only 0.001 to 0.003 ft in RMSE. GRU and LSTM are indistinguishable from each other. Flood-window intervals rest on only 27 groups and are fragile.

## 5. Heterogeneity across folds (`D2`, `D2b`)
No deep model is consistently better. Flood-window RMSE, folds where the deep model beats the reference (of 6): GRU versus ridge H at 15 m, 30 m, 1 h, 3 h: 2, 1, 3, 2; GRU versus damped trend: 1, 1, 3, 3; LSTM versus ridge H: 2, 2, 2, 3; LSTM versus damped trend: 2, 2, 4, 3. Examples at 3 h in flood windows: fold 1 (smallest training set) GRU 4.35 versus ridge 4.91; fold 6 (largest training set, 526,033 rows) GRU 4.97, LSTM 5.21 versus ridge 4.80, XGBoost 4.90. More training data did not produce a deep-model advantage. Per event (18 >= 10 ft events, 3 h window RMSE): GRU beats ridge H in 6, the damped trend in 10; LSTM beats ridge in 9, the trend in 10; at 1 h GRU beats ridge in 8 and the trend in 8, LSTM beats ridge in 8 and the trend in 10.

## 6. Event-level detection with the fixed alarm rule (pooled out-of-fold; early hits / events; storm clusters in brackets)
| Target | h | persistence | damped trend | ridge H | XGBoost H | GRU | LSTM |
|---|---|---|---|---|---|---|---|
| official >= 25 ft, 6 (5) | 1 h | 0 | 6 | 5 | 5 | 5 | 5 |
| | 3 h | 0 | 5 | 4 | 4 | 4 | 4 |
| >= 10 ft, 18 (14) | 3 h | 0 | 17 | 17 | 16 | 17 | 16 |
| rise >= 4 ft/3 h, 25 (22) | 1 h | 4 | 23 | 23 | 24 | 23 | 19 |
| | 3 h | 0 | 10 | **12** | 7 | 7 | 4 |
| rise >= 8 ft/3 h, 13 (10) | 3 h | 0 | 5 | 1 | 0 | 0 | 0 |
At 3 h the deep models detect fewer rapid rises than ridge H and the damped trend (GRU 7/25, LSTM 4/25 against 12/25 and 10/25) and none of the 13 rapid 8 ft rises, although they issue fewer false alarms (GRU 3 of 13 alarm episodes, LSTM 2 of 8, ridge 12 of 28, damped trend 8 of 24). Lead times and every false-alarm count are in `D5`; the per-event statuses in `D5b`.

## 7. Peak capture and timing for the held-out events (3 h)
Peak forecast issued 3 h ahead divided by the observed peak, median (minimum) over the 18 >= 10 ft events: persistence 0.80 (0.21), damped trend 0.94 (0.22), ridge H 0.87 (0.22), XGBoost H 0.88 (0.22), GRU 0.87 (0.22), LSTM 0.90 (0.22). For the six official events (persistence, damped trend, ridge, XGBoost, GRU, LSTM): 2015-05-24: 0.66, 0.84, 0.83, 0.72, 0.69, 0.70; 2015-10-30: 0.25, 0.42, 0.44, 0.33, 0.33, 0.32; 2016-05-30: 0.87, 1.07, 0.88, 0.93, 0.87, 0.96; 2025-07-05: 0.88, 0.96, 0.91, 0.92, 0.97, 0.91; 2026-07-15 (provisional): 0.71, 0.84, 0.85, 0.85, 0.88, 0.82; 2026-07-17 (provisional): 0.90, 0.97, 0.95, 0.94, 0.98, 0.93. The figures `figures/fig3_events_3h.png` and `fig3_events_1h.png` plot observed versus predicted stage for each of the 18 events: in every event the 3 h forecasts, deep and classical alike, trail the sharp rise by roughly three hours and the deep models are nearly indistinguishable from the damped trend.

## 8. Relation to Phase 1C, and why I do not read the contrast as "deep models are worse"
Phase 1C (4 test events, models trained on 2007-2017) found the GRU slightly ahead of ridge H on all rows (-0.011 ft at 3 h, interval excluding zero) and, in flood windows, by -0.097 [-0.176, +0.009] ft. Out-of-fold, GRU minus ridge H is +0.003 [-0.008, +0.014] on all rows and +0.132 [-0.019, +0.276] in flood windows at 3 h. The cleanest reading is that the Phase 1C margin was small and not robust. Candidate explanations I have not tested: it was specific to the 2022+ events or to seed noise (Phase 1C seed sd at 3 h in flood windows was 0.08-0.10 ft, comparable to many of these differences); the classical models here are tuned on each fold's validation chunk, whereas Phase 1C compared against classical models refitted on train plus validation; single seeds here.

## 9. Limitations
1. **One seed per fold**, so seed variation is not quantified in this experiment (Phase 1C showed 3 h flood-window seed sd of about 0.1 ft, as large as some of these gaps). 2. The deep hyperparameters (hidden size 64, learning rate, patience) come from Phase 1C, where hidden size was chosen on a 2018-2021 validation chunk that **postdates the test blocks of folds 1 to 3**, a mild look-ahead; the classical grids come from Phase 1B. 3. Early folds train on few years (fold 1: 3.2 years, two small floods) and validation chunks hold 0 to 8 events, so early stopping mostly follows quiet-period loss (the fold 3 LSTM ran the full 40 epochs, best epoch 35, and may not have converged). 4. Only 14 evaluated storm clusters and 27 flood-window bootstrap groups; fold 5 spans five years but holds two events; fold 6 contains provisional 2026 data. 5. Block boundaries were chosen from the event timeline, and event definitions and thresholds were fixed with whole-record knowledge. 6. Not a prospective test. 7. The project folder is not under version control. 8. No multiplicity correction for the many intervals examined. 9. Deep models were run on Apple MPS, which is not bit-reproducible.

## 10. Implications and what I suggest, for your review (nothing started)
- **For the research question:** a hybrid will have to beat a strong, simple baseline set (ridge H, damped trend) and a GRU/LSTM that currently shows no robust advantage over them. Every model fails to anticipate sharp onsets with stage history alone, so a hybrid using the same inputs is unlikely to fix early warning by itself; upstream or rainfall information (gauge product, NLDAS-2) is the more plausible lever and deserves discussion with your guide.
- **Phase 1E (24 h versus 72 h GRU):** I recommend running it on these six folds with at least three seeds, not only on the single Phase 1C split, because a single-seed, four-event comparison cannot separate a 72 h effect from noise. This needs your approval since it adds seeds beyond the earlier recommendation.
- **Optional before 1E:** seeds 1 and 2 for the Phase 1D GRU/LSTM (24 more trainings, about 1.5 hours) to quantify seed variation in cross-validation.
- **Phase 1F** (Transformer diagnostic) and the hybrid remain deferred as instructed.

## 11. Files
Protocol `docs/PHASE1D_PROTOCOL.md` (deviations: smoke run deleted; machine-specific PyTorch/XGBoost segmentation fault handled by running the stages as separate processes; fold 1 validation chunk has no events so its trend selection used the all-row fallback); `reports/phase1d/{fold_specification.csv,event_to_fold_mapping.csv,oof_predictions.csv.gz,runs/(configs, checkpoints, histories, predictions, manifest.json),tables/D1-D7*,figures/}`; code `src/flashflood/folds.py`, `scripts/run_phase1d_cv.py` (`--stage dl`, then `--stage classical`), `scripts/eval_phase1d.py`; tests `tests/test_phase1d.py` (33 tests pass in total); registry entry E14 in `experiments/REGISTRY.md`. Reproduce: run the two stages, then `python scripts/eval_phase1d.py`.
