# Plan: hybrid Transformer-LSTM with a 30-minute warning-lead target

**Status (updated 2026-11-23): approved by the project owner ("whatever feels right but do build lstm+transformer"); H0 is done; H1 was started under `docs/HYBRID_H1_PROTOCOL.md` and then STOPPED at the owner's request after 10 of 24 stability runs, so no hybrid result exists. H2 (upstream inputs) and H3 (detection head, warnings) are NOT started and need separate approvals.** The text below is the original plan; defaults were adopted: definition B primary with A alongside, H0 first, stage-only H1 first, bounded stability protocol, false-alarm cap equal to the best baseline's at the same horizon. Written 2026-11-23. It follows the project's pre-registration practice (decisions, metrics and stopping rules are fixed before any run) and keeps the exploratory/retrospective framing: no result of this plan can be untouched validation. Every number quoted below comes from existing saved tables (Phase 1D `D5`/`D5b`, onset timing `O3c`, `S1`); none is a hybrid result.

## 1. What "30 minutes before the flash flood" can mean (this must be fixed first)
The same words describe three very different targets. The evidence already in the project says how hard each is.

| Definition of the flood "start" | Meaning of "30 min before" | What current saved models already achieve (fixed alarm rule, lead of at least 30 min; events; best single configuration) | Difficulty |
|---|---|---|---|
| **A. Stage reaches a level** (official NWS 25 ft action stage, or the experimental 10 ft) | Alarm at least 30 min before the stage first reaches the level | 25 ft (6 events, 5 storms) at the 1 h horizon: damped trend 6, ridge 5, GRU 4. 10 ft (18 events): ridge 16, damped trend 16, GRU 15 | Largely met by simple baselines |
| **B. A rapid rise begins** (rise of at least 4 ft in 3 h, experimental; 25 events, 22 clusters) | Alarm at least 30 min before the rise criterion is first met | 1 h horizon: XGBoost 18, ridge 17, damped trend 15, GRU 14 of 25 (confirmed by H0, `reports/hybrid_h0/`). 3 h horizon: damped trend 10, ridge 5, GRU 5. Best of three baselines and two horizons per event (optimistic): 21 of 25; four events have at most 15 min of lead from any baseline (2013-05-25, 2014-05-26, 2015-10-30, 2025-07-05; two are official floods) | **The real headroom** |
| **C. The river begins to rise** (rise onset) | Warning at least 30 min before the first rise | No model has done this: in none of the 18 evaluated events did any variant forecast half of a rise before the onset (`reports/PHASE1E_ONSET_TIMING.md`). Stage-only inputs cannot see rain that has not yet reached the gauge | Needs new information (upstream gauges, rainfall) |

**Recommendation (to confirm):** define the primary target as **B**, with **A** reported alongside (it is the official-stage reading) and **C** treated as the research frontier, not a promise. State it in the report as "alarm raised at least 30 min before the flood criterion is first met", never as "the model predicts floods 30 min ahead". A 30-minute forecast *horizon* already exists (one of the four heads); a 30-minute *lead* is a different, harder property and is what this plan measures.

**Reality check the guide and faculty should hear:** a hybrid trained on the same stage-only inputs is unlikely to deliver 30 minutes of lead for the sharp-onset events, because Phase 1D/1E show the limit is information, not model size (ridge matches the networks; 72 h of history changed nothing). The plan therefore has a cheap falsification stage first and puts the hard cases behind the upstream-input stage.

## 2. Who, why, alternatives, success (questions the project must be able to answer)
- **Who benefits (hypothetical):** a flood-forecasting or emergency-management user at Spring Branch who needs time to act. This project is a research prototype; no user study or operational deployment is planned.
- **Alternatives that must be beaten, not ignored:** persistence, damped trend (best 25 ft lead performance already), ridge H, XGBoost H, GRU/LSTM, and a rule using upstream gauge rises directly (no learning) once upstream data are built. A hybrid is justified only if it beats these on the pre-registered measures below.
- **Why a hybrid might help:** a Transformer branch can weigh the whole recent history (long window) while an LSTM branch tracks the latest dynamics; the combination may handle both slow multi-stage rises and sharp onsets. This is a hypothesis, not evidence; hybrids of this kind are not novel, so the contribution would be a fair, leakage-safe comparison on sparse flood events.
- **How success is measured:** Section 6, fixed before training. Technology (Transformer, LSTM) is not itself a success criterion.

## 3. Proposed model (hypothesis, to be specified exactly before the first training)
- **Inputs, stage-only version (H1):** the Phase 1E channels for the target gauge (stage relative to current stage, 15-min change, missing mask; side inputs current stage and missing fraction). **H2 adds** upstream gauge channels and/or hourly rainfall per the draft upstream protocol (`docs/UPSTREAM_INPUT_PROTOCOL.md`), only after the guide approves it and the rainfall product is validated.
- **Branches:** Transformer encoder on the 24 h window (96 steps; 72 h was not useful in Phase 1E); LSTM on the last 6 h (24 steps) of the same channels. Fusion: concatenate pooled branch outputs, then a dense layer; gated fusion only as a pre-specified ablation. Four horizon heads (15 min, 30 min, 1 h, 3 h) with per-horizon scaled MSE as in Phases 1C to 1E (regression first; no probability head in H1).
- **Transformer stability:** the Phase 1C Transformer trained unstably (best epoch 1 to 15). Before the hybrid is judged, a **bounded, pre-registered** set of at most four stability settings (for example learning-rate warm-up, pre-norm, smaller width, lower rate) is tried and chosen on validation data only, identical for all folds. This is the deferred "Phase 1F" in a minimal form and needs its own approval.
- **Parameter and compute budget:** a Phase 1E GRU run takes a median 1.8 min on this laptop; a hybrid run is expected at several minutes (not measured). 18 runs for the main comparison (6 folds x 3 seeds) plus ablations is a few hours of compute.

## 4. Staged plan with gates (each gate needs your explicit approval)
| Stage | Content | New training? | Gate / stopping rule |
|---|---|---|---|
| **H0** Lead-time harness | Add the 30-minute-lead evaluation (per-event lead, hits with lead of at least 30 min, false alarms per year, per-event tables with event and storm-cluster counts) and freeze baseline numbers for persistence, damped trend, ridge, XGBoost, GRU, LSTM from the saved predictions; tests for the metric on synthetic data | **No** (reads saved predictions) | The harness reproduces the existing Phase 1D `D5` counts exactly |
| **H1** Stage-only hybrid | Hybrid against GRU 24 h, ridge, damped trend on the six Phase 1D folds, seeds 0 to 2 (18 runs); ablations Transformer-only and LSTM-only branch (36 runs) | Yes | Pre-registered rule (Section 6). **If the hybrid shows no consistent gain, stop; do not tune further on the same inputs.** The information limit is then the finding |
| **H1-stab** Stability protocol | At most four settings, validation only (Section 3) | Yes (small) | Runs before H1; chosen settings fixed for all folds |
| **H2** Hybrid with upstream and rainfall inputs | Configurations A to D of the upstream protocol, run with the hybrid and the GRU; reported separately for upstream-led, local-or-downstream and ambiguous floods | Yes | Only after the guide answers the 15 protocol questions and the radar rainfall product is validated (stage 1 of that protocol). Rainfall configurations are limited to folds with radar training data (4 to 6) |
| **H3** Warning-lead prototype | Detection or probability head with a **false-alarm cap fixed in its own document before any threshold is chosen** (Phase 1C protocol section 7, item 4); lead-time results for the chosen alarm rule; replay dashboard extension. Research prototype, no operational warning categories | Yes | Separate approval of the cap and of any warning-category calibration |

## 5. Why 30 minutes is plausible for some floods and not others (what the data allow)
- For **A** and part of **B**, models already raise alarms at 1 h and 3 h horizons far enough ahead; the hybrid's room for gain is in false alarms, in the harder rapid-rise events and in consistency across folds, not in basic feasibility.
- The **four sharpest rises** (two official floods) are where a lead of 30 minutes has not been reached by any baseline. Of the two official ones, 2025-07-05 is **upstream-led** (best upstream lead about 20 h, from the draft protocol's table), so an upstream-aware hybrid has a physical chance; 2015-10-30 is **local-or-downstream-led** (no upstream lead), so it would need rainfall information. The hourly radar archive lists files for that date, but its fold (fold 2) has no radar data in its training period, so rainfall configurations cannot be run on it under the Phase 1D folds without changing the folds. This pair is the natural test case for H2, with that limit stated.
- With only 6 upstream-led events (5 storms), no result can be statistically significant; the claim would be per-event, descriptive and labelled exploratory.

## 6. Evaluation and pre-registered decision rules (defaults; to be confirmed before H1)
- **Same folds, rows, embargo and event definitions** as Phases 1D and 1E; scalers and thresholds fitted on training or validation data only; test-fold data never used to pick an alarm threshold.
- **Primary forecast measure:** seed-mean flood-window RMSE at 1 h and 3 h, paired storm-cluster bootstrap against the best baseline (ridge H) and against the GRU. The hybrid "consistently improves" if the pooled difference is negative with the interval excluding zero, in at least 4 of 6 folds and for all 3 seeds (the Phase 1E rule). Margin and harm check as in the upstream protocol (5% benefit, 2% harm), to be confirmed.
- **Primary warning-lead measure (frozen after H0):** the number of events, of the 25 rapid rises and 18 evaluated 10 ft events, with an early alarm of at least 30 min **at a fixed false-alarm cap** set in advance (default proposal: no more than the baseline's false-alarm episodes per year at the same horizon, so the hybrid cannot win by alarming more). Report hits with at least 30 min, median lead, late detections, misses, false alarms per year, with event and storm-cluster counts beside every count, per seed (mean [min to max]).
- **Not accepted as evidence:** peak-capture ratios alone, a single seed, a single event, or a threshold chosen on the test folds.
- **Stop rules:** no consistent improvement in H1 means no further hybrid tuning on stage-only inputs; a hybrid that does not beat the damped trend and ridge at an equal false-alarm cap is reported as such.

## 7. Risks and what would change the plan
| Risk | Mitigation or change |
|---|---|
| The information limit: stage-only hybrid gains nothing | H1 is built as a cheap falsification; the result is the finding and motivates H2 |
| Very few hard events (4 sharp rises; 6 upstream-led) | Per-event reporting; no significance claims; the plan is effect-size oriented |
| Transformer instability | Bounded stability protocol; if unstable, report it rather than tune indefinitely |
| False alarms rise when alarming earlier (3 h alarms already give about 0.5 and 0.8 false alarms per year for the damped trend and ridge in the rapid-rise case) | Fixed false-alarm cap; report the whole trade-off curve |
| Real-time claim: all rainfall sources used so far are retrospective, and gauge data in use are archived, not as-received telemetry | Claims restricted to retrospective replay; real-time operation needs separate data work and approval |
| Provisional 2026 data (two evaluated events) | Reported with and without |
| Scope creep from "make it 30 minutes" into a promise | The target is an evaluated property with stated conditions, never a guarantee |

## 8. Mapping to the academic evaluations (proposal, pending faculty confirmation)
**Second evaluation:** H0, H1-stab, H1 (and H2 if the guide approves the upstream protocol in time). **Third evaluation:** H2 results, H3 warning-lead prototype, robustness to missing data, final report. If faculty expect a working hybrid at the second evaluation, H0 plus H1 is the achievable core; H2 depends on external approvals and data validation.

## 9. Decisions needed from you (recommended defaults)
1. Which definition is the primary "flash flood" for the 30-minute lead: A (stage level), **B (rapid rise; recommended)** or C (rise onset)? Which official/experimental thresholds?
2. Approve **H0** now (lead-time evaluation of the existing baselines, no training)? **Recommended: yes**, because it fixes the numbers any hybrid must beat.
3. Start with the stage-only hybrid (H1) as a falsification test, or wait for the upstream protocol to be approved and go to H2 directly? **Recommended: H1 first.**
4. May a bounded Transformer-stability protocol (at most four settings, validation only) be included? **Default: yes, as part of H1.**
5. False-alarm cap rule for the lead evaluation: equal to the best baseline's rate at the same horizon (default), or a fixed episodes-per-year number you choose.
6. Is the 30-minute lead a requirement from the faculty or guide, or your own target? If it is a requirement, please get the exact wording; it changes which definition is acceptable.
