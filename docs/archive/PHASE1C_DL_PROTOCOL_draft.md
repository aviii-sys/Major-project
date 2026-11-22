# Phase 1C Deep Sequence Baselines Protocol: DRAFT for review (nothing here has been run)

Scope: LSTM, GRU and Transformer-encoder baselines **only**. The hybrid Transformer-LSTM is explicitly excluded until these results and the strengthened classical baselines have been reviewed. Wherever possible everything matches Phase 1A/1B: targets, horizons (15 m, 30 m, 1 h, 3 h), masking, chronological storm-grouped splits, event/alarm definitions, metrics, bootstrap and exact intervals.

## 1. Data representation
- Input window: the last 96 steps (24 h) at 15-min spacing, ending at the issue time t (causal). Channels per step: stage, 15-min change, a missing-value mask for stage, and hourly ERA5 basin rain with its age (the same causal alignment as Phase 1A; missing = 0 with mask). Optional channel group chosen like the classical feature sets: hydrology only, + ERA5, + gauge antecedent features appended to the final step. Normalisation statistics are fitted on the training period only.
- A window is used only if the issue time is eligible under Phase 1B rule 1 (minimal inputs + target valid). Windows never cross a split boundary or a storm cluster boundary; the target purge (3 h) applies.
- Targets: change in stage at the four horizons (multi-output regression head). A second head or separate runs for probability detection (BCE loss) follow the Phase 1B section 5 definitions and are run only after the regression baselines are reviewed.

## 2. Models and training
- LSTM (1 layer), GRU (1 layer), Transformer encoder (2 layers, 4 heads, learned positional encoding, mean-pooled), each followed by a small MLP head. Hidden size {32, 64}, dropout 0.1; chosen on validation by lowest mean event-window RMSE (the Phase 1B section 2 definition), nothing else is tuned.
- Adam, learning rate 1e-3, batch 512, at most 60 epochs, early stopping with patience 8 on validation all-row MSE; loss MSE, with the Phase 1B event-aware weight (lambda chosen once on validation from {0, 10, 50}).
- **Seeds:** 5 seeds (0 to 4) per configuration; every seed is reported, plus mean and standard deviation; no best-seed selection. Deterministic settings and library versions recorded.
- Compute: CPU or Apple MPS; training time per run recorded.

## 3. What is saved (per model, seed, horizon)
Validated configuration (YAML), seed, library versions, best-epoch checkpoint (state dict) with SHA-256, training/validation curves, predictions for validation, test and blocked-CV rows (compressed arrays aligned to the master timestamp index), metrics tables, and per-event tables.

## 4. Evaluation
Identical to Phase 1B: all-row and event-window RMSE/MAE/skill versus persistence with storm-cluster bootstrap intervals; fixed alarm rule detection; probability-based detection as in Phase 1B section 5 once approved; per-event tables; blocked CV (non-causal, supplementary); independent-event counts always shown. **Paired** storm-cluster bootstrap on metric differences against the best classical baseline, so that a deep model is only said to differ when the interval excludes zero.

## 5. Claims and caveats
The test period is already exposed (see Phase 1B section 0), so test results stay exploratory. No claim of flood-warning capability or generalization. A deep model that does not beat the strengthened classical baselines is reported as such.

## 6. Open questions for the reviewer
1. Window length 24 h versus 72 h (the classical features include 72 h running maxima)?
2. Joint multi-horizon head versus separate models per horizon?
3. Should the probability-detection head be trained in the same pass or only after the regression results are reviewed?
