# H1 protocol: stage-only hybrid Transformer+LSTM (fixed BEFORE any real training)

Written 2026-11-23. Experiment ids **E22** (H0, warning-lead harness on the saved baselines, already run: no training) and **E23** (H1, this protocol). Output folders `reports/hybrid_h0/` and `reports/hybrid_h1/` (new). Follows `docs/HYBRID_PLAN_30MIN_LEAD.md`. No Phase 1C, 1D or 1E artifact is modified. **Out of scope here (separate approvals): upstream gauges or rainfall as inputs (H2), a probability/detection head, warning categories, live operation.**

## 0. Integrity
Retrospective blocked chronological cross-validation on the six Phase 1D folds; **not untouched validation; every number is exploratory.** Nothing is tuned on held-out blocks: the only choice made from data (one of four stability settings) uses the VALIDATION chunk of each fold. The alarm rule and event definitions are the existing Phase 1A/1B ones and are not changed or tuned. No configuration is selected by its best seed or best fold. Phase 1D/1E conclusions (ridge and damped trend competitive; 24 h kept) stand regardless of this result.

## 1. Questions
- **H1a (forecast error).** Does the hybrid reduce flood-window RMSE at 1 h and 3 h relative to ridge H and to the GRU 24 h?
- **H1b (30-minute warning lead, plan definitions A and B).** Does the hybrid raise early alarms at least 30 minutes before the event criterion for more events than the best baseline, at no more false-alarm episodes?
- **H1c (attribution, descriptive).** What does each branch contribute (Transformer-only and LSTM-only ablations)?
Rapid onset (definition C, forecasting before the river starts to rise) is not tested here: stage-only inputs cannot see it (`reports/PHASE1E_ONSET_TIMING.md`).

## 2. Design
- **Folds, rows, embargo:** exactly the Phase 1D folds (the runner asserts equality with `reports/phase1d/fold_specification.csv`), embargo 27 h 15 min, training rows with at least 72 h of history (identical to the Phase 1E GRU 24 h runs, so the matched deep baseline uses the same rows), evaluation rows = the Phase 1B/1D eligible held-out rows.
- **Inputs:** the Phase 1C-1E channels only (stage relative to the current stage, 15-min change, missing mask; side inputs current stage and missing fraction); normalisation fitted on each fold's training windows only.
- **Architecture:** Transformer encoder on the 24 h window (96 steps) and an LSTM (hidden 64) on the last 6 h (24 steps) of the same channels; summaries concatenated with the 16-unit static embedding; four horizon heads (15 min, 30 min, 1 h, 3 h) with per-horizon scaled MSE and equal weights; Adam, batch 512, 120,000 random rows per epoch, gradient clip 1.0, patience 6, at most 40 epochs, best-validation checkpoint (the Phase 1C-1E training protocol). `src/flashflood/hybrid.py`.
- **Matched references (read only):** GRU 24 h seeds 0-2 (Phase 1E), LSTM seed 0, ridge H, damped trend, XGBoost H, persistence (Phase 1D), all on identical evaluation rows.
- **Seeds 0, 1, 2.**

## 3. Stability protocol (bounded; the Phase 1C Transformer trained unstably)
Four settings, each run on all six folds with seed 0 (24 runs, `reports/hybrid_h1/stability/`):

| Setting | Transformer branch |
|---|---|
| S0 | post-LayerNorm, width 64, 2 layers, 4 heads, feed-forward 128, dropout 0.1, learning rate 1e-3, no warm-up (the Phase 1C configuration) |
| S1 | S0 with pre-LayerNorm (final norm) and 300-step linear warm-up |
| S2 | S1 with learning rate 3e-4 |
| S3 | S1 with width 32 |

**Selection rule (validation data only):** for each setting and fold, the best validation scaled loss; ratio to S0 in that fold; geometric mean of the six ratios; the setting with the lowest ratio is chosen **only if the ratio is at most 0.99** (at least 1% better than S0), otherwise S0 is kept. The chosen setting is fixed for the main runs and the ablations. No other tuning (width, depth, learning rate, windows, fusion, loss weights) is performed in this experiment.

## 4. Runs
Main: chosen setting x 6 folds x seeds 0-2 = 18 runs (`reports/hybrid_h1/runs/fold{k}_hybrid_{setting}_s{seed}`). Ablations (seed 0 only, to bound compute): Transformer-only and LSTM-only with the same setting x 6 folds = 12 runs. Each run saves configuration, history, checkpoint (SHA-256), held-out predictions; a manifest of hashes per folder.

## 5. Evaluation and decision rules
- **Subsets:** all rows; flood windows of the evaluated >= 10 ft events (primary); rapid-rise windows; rising-water rows (Phase 1E definitions). RMSE and MAE per horizon with storm-cluster bootstrap (2,000 resamples, seed-averaged replicates, paired); per seed, per fold, per event; event and storm-cluster counts beside every event count.
- **H1a rule.** The hybrid *consistently improves* on comparator C at horizon h (flood windows) if (i) the pooled paired RMSE difference (hybrid minus C, seed mean) is negative with the 95% interval excluding zero, (ii) it is negative in at least 4 of 6 folds, (iii) it is negative for each of the 3 seeds (against the GRU seed with the same index; against ridge H each hybrid seed). It is *material* if the difference is at most -5% of C's RMSE. **Harm check:** the upper 95% bound of the all-row difference must not exceed +2% of C's RMSE at any horizon, otherwise a harm flag is raised. **Primary claim "the hybrid improves flood-window forecasting" requires consistent improvement on BOTH ridge H and GRU 24 h at BOTH 1 h and 3 h with no harm flag.** Anything less is reported as "not demonstrated", with the sub-claims that hold.
- **H1b rule.** For each definition (official 25 ft: 6 events; stage >= 10 ft: 18; rise >= 4 ft in 3 h: 25) and horizon 1 h and 3 h: events with an early alarm of at least 30 minutes, seed mean [min-max], with false-alarm episodes, versus the best single baseline configuration (ridge H, damped trend, XGBoost H, LSTM seed 0 or the GRU 24 h seed mean, whichever has the most such events; frozen in `reports/hybrid_h0/baseline_leadtime.json`). The hybrid *improves the 30-minute lead* if its seed-mean count is at least 2 events above that baseline **and** its mean false-alarm episodes are not above the baseline's. The 6 official events are descriptive only (no claim). The five events at which no baseline reaches 30 minutes (`reports/hybrid_h0/tables/H0_5b_events_no_baseline_reaches_30min.csv`) are reported individually.
- **Not accepted as evidence:** peak-capture ratios alone, a single seed, a single event, any threshold or alarm setting chosen on held-out data. The Phase 1A alarm rule (hysteresis 1 h, tolerance 1 h) is used unchanged.

## 6. Stop rules
If neither H1a nor H1b is met, **no further hybrid tuning on stage-only inputs**: the finding is that architecture alone does not help, which motivates H2 (upstream inputs) and goes to the guide. If the stability stage leaves every setting unstable (median best epoch of 2 or less in all four), that is reported as such and the main stage still runs with S0.

## 7. Limitations (stated in advance)
Three seeds; six folds; 14 storm clusters; five hard events; early folds train on little data; one hybrid design; stability settings are a small set, not a search; hyperparameters otherwise inherited from Phase 1C; ablations use one seed; intervals are conditional on the trained seeds; no multiplicity correction; exploratory.

## Deviations
1. A 2-epoch smoke run of the stability stage (fold 1, four settings, 20,000 rows per epoch) was used to debug the runner and to time it (about 30 to 35 s per full epoch is expected). Its validation losses were seen but have no role in any selection (the rule above uses only the full runs); the smoke outputs (`reports/hybrid_h1_smoke/`) were deleted before the real run.
2. A second, complete 2-epoch dry run of ALL stages (stability, select, main, ablate; every fold; 20,000 rows per epoch) plus the evaluation script was executed in a scratch folder (`reports/hybrid_h1_smoke2/`) to debug the pipeline while the real stability stage was training. It confirmed that the evaluation reproduces the Phase 1E/1D comparator numbers exactly (GRU 24 h, ridge, damped trend, XGBoost flood-window RMSE and all 96 H0 lead-time rows). Its hybrid results come from 2-epoch toy models and were not interpreted; its outputs were deleted. It slowed the real run by sharing the GPU for about 30 minutes.
3. (Logged 2026-11-23.) The real run was STOPPED at the project owner's request after 10 of the 24 stability runs (folds 1 and 2 complete; fold 3 settings S0 and S1 complete; S2 interrupted and its empty folder removed). No setting has been selected, no main run or ablation has been trained, and nothing has been evaluated; the 10 finished runs are preserved with a hash manifest and the stage is resumable because the runner skips runs that have predictions. Nothing in this protocol was changed.
