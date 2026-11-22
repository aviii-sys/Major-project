# Phase 1E Protocol: GRU input window 24 h versus 72 h (fixed BEFORE any Phase 1E model was trained)

Written 2026-11-22. Experiment id **E16**. Output folder `reports/phase1e/` (new). No Phase 1C or Phase 1D artifact is modified. Scope: GRU only; the single experimental variable is the length of the input window. No hybrid, Transformer diagnostic, probability head, discharge forecasting or new inputs.

## 0. Integrity
Retrospective blocked chronological cross-validation on the six Phase 1D folds, **not untouched external validation**; every number is exploratory. Phase 1D results (ridge H and the damped trend competitive or better than GRU/LSTM; deep models significantly worse in flood windows at 15 and 30 min; all models lag sharp onsets by about 3 h) stand unchanged and are part of the findings. Nothing is tuned on held-out blocks; no configuration is selected by its best seed.

## 1. Design
- **Folds:** exactly the six Phase 1D folds (same boundaries, embargo 27 h 15 min, validation chunks, event-to-fold mapping). The runner asserts that the fold specification equals the saved Phase 1D specification.
- **Configurations:** (A) GRU with 24 h input = 96 steps; (B) GRU with 72 h input = 288 steps. Everything else identical: hydrology-only channels (stage relative to the current stage, 15-min change, missing mask, current stage and window-missing fraction as side inputs), hidden size 64, shared encoder with four horizon-specific heads, per-horizon scaled MSE with equal weights, Adam 1e-3, batch 512, 120,000 random rows per epoch, gradient clip 1.0, patience 6, at most 40 epochs, best-validation checkpoint, normalisation statistics fitted on each fold's training windows only (separately for each window length, by the same procedure).
- **Matched seeds 0, 1, 2.** A GRU's parameter shapes do not depend on the window length, so a given seed yields the same initial weights, and the training rows and their sampling order are identical for A and B. The two configurations then differ only by window length (plus non-deterministic Apple MPS kernels).
- **Training rows:** to keep rows identical for A and B, both use only rows with at least 288 steps of history (this drops the first 3 days of the record, all in the training period of every fold; Phase 1D's 24 h runs used 96 steps, so the 24 h runs here are NEW runs, not the Phase 1D ones). Evaluation rows are the Phase 1B/1D eligible held-out rows, identical for A and B.
- **Runs:** 6 folds x 3 seeds x 2 windows = **36 trainings**, all new. A reproducibility check compares the new 24 h seed-0 runs with the Phase 1D 24 h seed-0 runs (which differ in training rows by the first 2 days and in MPS non-determinism).
- **Reference models** (read only, from `reports/phase1d/runs/fold*_classical`): persistence, damped trend, ridge H, XGBoost H.

## 2. Evaluation
Per-horizon (15 m, 30 m, 1 h, 3 h) RMSE and MAE pooled over the out-of-fold rows, for these subsets: **all rows**; **flood windows of the evaluated >= 10 ft events** (primary); flood windows of the >= 4 ft/3 h rapid rises; **rising-water rows** (rows with a 1-h rise of at least 0.5 ft at the issue time). Reported for A, B and the reference models: seed-mean RMSE with the spread over seeds; per fold; per event (window RMSE and peak capture for the 18 evaluated >= 10 ft events, the 6 official events flagged); event-level fixed alarm rule detection (Phase 1A definition) with events and storm clusters beside every count.
**Paired differences B minus A** (negative = 72 h better): pooled, with 95% storm-cluster bootstrap intervals (2,000 resamples, seed-averaged replicates; intervals are conditional on the three trained seeds); per seed (3 values); per fold (6 values); per event (18 values, counts of events where B is better). Variation across seeds and folds is reported, not hidden.
**Missing-data sensitivity:** evaluation rows are stratified by the fraction of missing or invalid stage samples in their 72 h window (none; up to 5%; above 5%) and, separately, in their 24 h window; paired differences and row counts are reported per stratum; the number of flood-window rows affected is reported.

## 3. Pre-registered decision rule (default = retain 24 h)
72 h "consistently improves" at horizon h on subset S if all three hold: (i) the pooled paired RMSE difference (72 h minus 24 h, seed-mean) is negative with the 95% interval excluding zero; (ii) the fold-level differences (seed-mean) are negative in at least 4 of the 6 folds; (iii) the seed-level pooled differences are negative for all 3 seeds. **72 h is adopted only if it consistently improves flood-window RMSE (>= 10 ft windows) at 2 or more of the 4 horizons AND no horizon shows a significantly worse all-row RMSE (interval entirely above zero).** Otherwise the 24 h configuration is retained. Improvements in regression error are not read as improvements in flood detection or early-warning lead time; detection and onset timing are reported separately.

## 4. Saved artifacts
Per run: configuration, seed, window, checkpoint (SHA-256), history, held-out predictions, under `reports/phase1e/runs/fold{k}_gru_w{24|72}h_h64_s{seed}`; a manifest of hashes; fold specification copy; metric tables (pooled, per seed, per fold, per event, missing-data strata, detection); pooled out-of-fold predictions for both configurations; figures; test file `tests/test_phase1e.py`; registry entry E16.

## 5. Known limitations (stated in advance)
Three seeds only; six folds with 14 evaluated storm clusters and about 27 flood-window bootstrap groups; the early folds train on few years (a 72 h window has more parameters to learn from the same rows); validation chunks have 0 to 8 events; single hidden size; hyperparameters inherited from Phase 1C; intervals do not include uncertainty from additional seeds.

## Deviations
1. A quick-mode smoke run of all 36 trainings (2 epochs, 20,000 rows per epoch) was executed to debug the runner; its outputs were deleted before the real run and nothing in this protocol was changed because of them.
2. (Logged 2026-11-22, after training.) The Mac went to sleep for about two hours while fold 5, seed 1, 72 h was training; the process was paused, not altered, and was then protected with `caffeinate -i -w <pid>`. No setting changed; the 7,427 s recorded for that run in `E8` is wall-clock time.
3. (Logged 2026-11-22.) Two table constructions in `scripts/eval_phase1e.py` (`E4b`, `E5b`) were simplified before the evaluation run recorded in `reports/phase1e/eval.log`; the decision rule, subsets and metrics were not changed.

## Outcome (added after evaluation; the protocol above is unchanged)
Decision under the rule in section 3: **72 h not adopted, 24 h retained** (0 of 4 horizons with consistent flood-window improvement; all-row RMSE significantly worse for 72 h at 15 min, 30 min and 1 h, by 1.2% to 1.6%). Full results, limitations and the three favourable missing-data strata (all in rows whose 24 h window is more than 5% incomplete) are in `reports/PHASE1E_REPORT.md`; tables in `reports/phase1e/tables/`; `reports/phase1e/decision.json`. No post-hoc analysis was added.
