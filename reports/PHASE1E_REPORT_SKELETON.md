# Phase 1E Report: GRU Input Window 24 h versus 72 h  —  SKELETON (no results; every {{...}} is to be filled from `reports/phase1e/tables/` after evaluation)

Status line to keep: **Retrospective blocked chronological cross-validation, NOT untouched validation; every number is exploratory.** Protocol (fixed before training): `docs/PHASE1E_PROTOCOL.md` (experiment E16). Only Phase 1E was run: no hybrid, Transformer diagnostic, probability head or discharge forecasting.

## 0. Headline (write LAST, from E3_decision_rule and decision.json)
- Pre-registered decision: 72 h adopted? {{yes/no}}; horizons with consistent improvement in flood windows: {{n}} of 4; any significantly worse all-row horizon: {{yes/no}}.
- One sentence on regression: {{...}}. One sentence on detection/onset (from E6, E4 peak capture): {{...}}. Do not read regression changes as detection changes.

## 1. What was run
36 trainings (6 folds x 3 seeds x 2 windows), matched seeds 0-2, identical folds to Phase 1D (assertion in the runner), GRU hidden 64, same optimizer, features, targets, horizons and preprocessing. Training rows identical for both windows (rows with at least 72 h of history). Fill from `E8_training_diagnostics`: epochs and best epochs per window {{...}}, runtime {{...}}. Reproducibility versus Phase 1D (`E7`): RMSE of the difference between the new 24 h seed-0 predictions and Phase 1D's {{...}} ft by horizon.

## 2. Pooled results (`E1_pooled_metrics`)
Table per subset (all rows; flood windows of >= 10 ft events; rapid-rise windows; rising-water rows): RMSE and MAE for 24 h, 72 h (seed-mean, sd across seeds, 95% interval) and for persistence, damped trend, ridge H, XGBoost H. Rows and storm-bootstrap groups in every table header: {{n_rows, n_groups}}.

## 3. Paired differences 72 h minus 24 h (`E1b_paired_72_minus_24`)
Pooled difference with 95% interval, the three per-seed differences, folds where 72 h is better (x of 6), seeds where 72 h is better (x of 3), MAE difference, for each subset and horizon. Report the spread, not just the mean.

## 4. Per fold and per event (`E2_per_fold_paired`, `E4_per_event`, `E4b_per_event_summary`)
Fold-level differences {{...}}; events where 72 h has the lower window RMSE (of 18; storm clusters {{14}}); peak-capture ratios for the 6 official events (descriptive; two are provisional 2026 data) {{...}}. Look for heterogeneity (a pooled gain driven by one fold or one event must be called out).

## 5. Missing-data sensitivity (`E5_missing_data_sensitivity`, `E5b_missing_share`)
Share of evaluation rows (all rows; flood-window rows) with any missing sample in the 72 h window {{...}} and above 5% {{...}}; paired differences by stratum with row counts and groups. State whether any apparent 72 h effect is confined to windows with missing data.

## 6. Rising-water rows and event detection (`E1b` subset `rising_rows_d1h_ge_0.5ft`, `E6`, `E6b`)
Does longer history help when the water is already rising? {{...}}. Fixed-rule detection hits per seed (min-max) with events and storm clusters beside every count {{...}}. Onset-timing figure: does the 3 h forecast still trail sharp onsets by about 3 h at 72 h? {{...}} (this needs a plot of observed versus 24 h and 72 h forecasts for the sharp-onset events; add if the numbers suggest any change).

## 7. Decision under the pre-registered rule (`E3_decision_rule`)
Reproduce the table: for each horizon (i) interval below zero, (ii) folds 72 h better, (iii) seeds 72 h better, consistent improvement yes/no; all-row significantly-worse check; final decision and its consequence for the default configuration (keep 24 h unless adopted). Do not select by the best single seed.

## 8. Interpretation and limitations
Three seeds only; six folds, 14 storm clusters, ~27 flood-window bootstrap groups; interval conditional on three trained seeds; early folds with little training data; 72 h has more missing data; hidden size and hyperparameters inherited from Phase 1C; no multiplicity correction; exploratory. What this does and does not show for the research question: {{...}}. Link to the upstream-input finding (`docs/UPSTREAM_INPUT_FEASIBILITY.md`): longer stage history does not provide information from where the rain fell; {{state only what the results support}}.

## 9. Files and deviations
List runs, manifests, tables, figures, tests, registry entry E16, and every protocol deviation (smoke run deleted; machine sleep pause during training did not change any setting; caffeinate used). Reproduce: `python scripts/run_phase1e_window.py` then `python scripts/eval_phase1e.py`.
