# Phase 1C Deep Sequence Baselines: FINAL protocol (fixed BEFORE any deep model was trained)

Written 2026-11-22. Replaces the draft (archived at `docs/archive/PHASE1C_DL_PROTOCOL_draft.md`). Scope of THIS experiment: **LSTM, GRU and Transformer-encoder regression baselines only.** No probability head, no hybrid Transformer-LSTM, no discharge forecasting. Targets, horizons, masking, chronological storm-grouped splits, eligibility and evaluation code follow Phases 1A and 1B wherever possible.

## 0. Integrity statement
- The test period (2022-01-01 onward) was inspected in earlier phases, so **every test-period result here is exploratory**. Protocol deviation 3 (a feature-eligibility defect found after viewing test output) stays documented (`docs/PHASE1A_PROTOCOL.md`, `reports/DEVIATION3_COMPARISON.md`).
- **Nothing (hyperparameters, epochs, early stopping, architecture, comparison rules) is tuned or chosen using test results.** Test predictions are produced once, from the best-validation checkpoint.
- All earlier exploratory results are preserved (`experiments/REGISTRY.md`). Official categories remain descriptive; **no flood-warning capability or generalization is claimed.**

## 1. Primary configuration (what is compared)
- **Deep models:** LSTM, GRU, Transformer encoder, each with a **shared encoder and four horizon-specific output heads** (15 min, 30 min, 1 h, 3 h), regression output only.
- **Primary input window: 24 h = 96 steps** of 15 min, ending at the issue time t (causal). Windows may include data before the split boundary (inputs only; same as classical lookbacks); storm clusters are never split across splits, which is what prevents storm leakage.
- **Input is hydrology only** (no rain, gauge, H2 or weighting inputs): the Phase 1A feature family, whose lagged differences the sequence encoder can learn itself. H2 features and sample weighting did not improve under the evaluation rule and are archived, not used.
- **Classical comparators (primary configuration):** persistence, damped trend (v2), ridge (H features, lambda = 0) and XGBoost (H features, lambda = 0), from the frozen Phase 1B predictions on identical rows. ridge/XGBoost with H2 and weighting are archived and are **not** primary comparators.

## 2. Data representation
Per step j of the window (oldest to newest): (1) `asinh((s_j - s_t)/0.25)`, stage relative to the current stage; (2) `asinh((s_j - s_{j-1})/0.05)`, the 15-min change; (3) an observed-sample mask. Missing samples are set to 0 in channels 1 and 2 with mask 0 (never imputed as real values). Channels 1 and 2 are standardised with statistics from a sample of **training** windows only. Side inputs at t: current stage (standardised with training statistics) and the fraction of missing samples in the window.
Eligibility is exactly the Phase 1B rule (current stage, 15/30/60 min changes and the target valid; ERA5 rain features valid so every model is scored on the same rows). Training rows additionally need a full 96-step history (drops the first 24 h of the record, all in the training period). A row contributes to the loss of a horizon only if that horizon's target is valid.
Targets: stage **change** s(t+h) - s(t) in feet, divided by the training-set standard deviation of that horizon's change; loss = mean over horizons of the masked mean squared error of the scaled targets (equal horizon weights). Metrics are always computed in feet.

## 3. Models
- LSTM and GRU: 1 layer, hidden size H, last hidden state. Transformer: input projection to d_model = H, learned positional embedding (96 positions), 2 encoder layers, 4 heads, feed-forward width 2H, dropout 0.1, representation = concatenation of the final-position output and the mean over positions. Side inputs go through a 16-unit layer; each of the four heads is a 32-unit hidden layer with ReLU followed by one linear output. No other architecture changes will be tried in this experiment.

## 4. Training, selection and seeds
- Adam, learning rate 1e-3, batch 512, gradient-norm clip 1.0, an "epoch" = 120,000 training rows drawn at random without replacement, at most 40 epochs, early stopping with patience 6 epochs on the **validation all-row scaled loss**, best-validation checkpoint kept. Training runs on Apple MPS.
- **Hidden size H in {32, 64}, chosen per architecture on validation** using seed 0 only, by the lowest mean (over the four horizons) **validation event-window RMSE** (issue times from 6 h before rise onset to the peak, for validation events of >= 10 ft and of >= 4 ft/3 h rises; the Phase 1B definition). Nothing else is tuned.
- Then seeds 0, 1, 2, 3, 4 are trained with the chosen H. **Every seed is reported; no best-seed selection.** Results are reported per seed and as mean and standard deviation across seeds; "seed-mean" metrics use the mean of per-seed squared errors, not an averaged prediction (a seed-ensemble is a different model and is not reported as the headline).
- Deterministic seeding of Python, NumPy and PyTorch; MPS kernels are not guaranteed bit-reproducible, so seed-to-seed and rerun variation is expected and reported.

## 5. Evaluation (identical code to Phase 1B where possible)
- Chronological validation and TEST (exploratory) only; blocked cross-validation is **not** run for deep models in this experiment (about 100 additional trainings; deferred, not discarded).
- Subsets: all rows; windows of >= 10 ft events; windows of >= 4 ft/3 h rises. Metrics: RMSE, MAE, skill versus persistence, with 95% storm-cluster bootstrap intervals (2,000 resamples).
- **Pre-registered comparison:** the "best classical baseline" is the one of {damped trend, ridge H, XGBoost H} with the lowest mean validation event-window RMSE (computed from frozen validation predictions before any deep-model test evaluation). For each architecture and horizon, the **paired** storm-cluster bootstrap interval of the RMSE difference (deep seed-mean minus best classical) is reported; a deep model is described as better or worse only if the interval excludes zero. Twelve to twenty-four intervals are examined without multiplicity correction, so even those are treated as exploratory.
- Secondary: the fixed alarm rule of Phase 1A applied to the regression forecasts (no probability head), per seed, for the experimental targets and (descriptively) the official thresholds; per-event window RMSE and peak-capture tables for the test events. Independent event counts are shown next to every event-level number.

## 6. Saved artifacts (per architecture, hidden size, seed)
Configuration (JSON), seed, library versions, best-epoch checkpoint with SHA-256, training/validation history, validation and test predictions (float32, with the row indices), metrics tables; all under `reports/phase1c/runs/`, with a manifest of hashes in `reports/phase1c/runs/manifest.json`.

## 7. Planned controlled experiments after review (NOT run in this experiment; one factor at a time)
1. 24 h versus 72 h input window. 2. Shared multi-horizon heads versus independent per-horizon models. 3. Gauge antecedent rainfall appended as side input (controlled comparison; NLDAS-2 stays a future extension). 4. A separate probability-detection experiment with a **false-alarm-constrained operating point**: the cap (alert episodes per week and FAR) and its justification will be pre-registered in its own document before any training or threshold selection; if no defensible cap exists, the full precision-recall and false-alarm trade-off is reported instead of an "optimal" point. The validation-F2 experiment of Phase 1B stays archived as exploratory. The 8 ft rapid-rise target remains exploratory (one validation event). 5. Discharge forecasting on the 1998-2007 dataset is deferred until the primary stage-forecasting deep baselines and the hybrid have been evaluated. 6. The hybrid Transformer-LSTM is not implemented until these baselines are reviewed.

## 8. Changes relative to the draft (made before any training)
Windows may include pre-boundary inputs (as classical features do) instead of "never crossing a boundary"; blocked CV deferred for deep models; the Transformer representation concatenates last-position and mean outputs; the loss uses per-horizon scaled targets with equal horizon weights; epoch definition, patience 6 and 40 maximum epochs fixed for compute; hidden sizes selected by seed-0 validation event-window RMSE.

## Deviations
1. A 2-epoch smoke run (20,000 rows per epoch, seed 0 only) was executed to debug the training script; its hidden-size 'selection' and metrics came from 2 epochs, were not used, and its outputs were deleted before the real run. No rule or setting in this protocol was changed because of it.
2. Before the final evaluation, the evaluation script was run on the LSTM and GRU predictions as a code-path debug pass. Its outputs (which contained test metrics) were written to a scratch folder, not read, and deleted after programmatic checks that compared only the classical rows against Phase 1B.
3. **Post-hoc analysis (after seeing results, not pre-registered):** paired comparisons of the deep models against ridge H and the damped trend (`scripts/posthoc_phase1c_vs_ridge.py`), added because the pre-registered best classical baseline (XGBoost H, chosen on validation by a margin of 0.001 ft) is weaker than ridge H at 3 h on test. Labelled post-hoc in the report.
4. Results of the experiment as run are in `reports/PHASE1C_REPORT.md`. The Transformer trained unstably (best epoch 1 to 15; validation loss 0.319 to 0.363); no setting was changed after seeing this.

