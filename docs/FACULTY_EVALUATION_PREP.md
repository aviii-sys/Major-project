# First faculty evaluation: audit, academic roadmap and presentation pack

**Written for:** the project team, to prepare the first evaluation. **Companion:** the Faculty Evaluation Dashboard (`dashboard/evaluation/index.html`, built from the saved result tables). Everything here is taken from the repository (tables, reports, registry, tests). Where something is not documented, it is marked **NOT DOCUMENTED** or **PROPOSAL**. Nothing below claims the hybrid model, any upstream-input result, warning logic or live operation, because none exists yet.

## 1. Audit: what actually exists

| Area | Evidence in the repository | Status |
|---|---|---|
| Data | 668,307 USGS 15-minute stage readings, 2007-10-02 to 2026-11-22, 99.55% of expected values present (`reports/phase0/phase0_results.json`); official NWS stages and a 20-event catalogue at 10 ft or more; Phase 0 report with a corrected-threshold finding | Complete |
| Preprocessing and evaluation framework | Causal features, storm clusters, blocked chronological folds with a 27 h 15 min embargo, per-fold scaling, paired storm-cluster bootstrap (`src/flashflood/`, 11 modules; protocols `docs/PHASE1A..1E_PROTOCOL.md`) | Complete |
| Models trained | Classical: persistence, damped trend, ridge, XGBoost. Deep: LSTM, GRU, Transformer; 66 neural trainings in total (18 in Phase 1C, 12 in Phase 1D, 36 in Phase 1E), each with a checkpoint, SHA-256 manifest and saved predictions | Complete |
| Experiments | Phase 1C (single split, 5 seeds), Phase 1D (six-fold cross-validation), Phase 1E (24 h versus 72 h, pre-registered rule), onset timing (post-hoc), upstream feasibility and protocol | Complete; upstream protocol is a draft awaiting the research guide |
| Software quality | 76 automated tests pass (`.venv/bin/python -m pytest -q`); 7 protocol documents; experiment registry with 20 entries and logged deviations | Complete |
| Dashboards | Historical-replay dashboard (`dashboard/replay/index.html`, offline, saved forecasts only) and the faculty dashboard | Complete |
| Hybrid Transformer-LSTM | design sketched only | **Not implemented** |
| Upstream-input experiments (A to D) | protocol only; nothing trained or run | **Not implemented** |
| Probability/detection head, warning categories, live data, discharge forecasting | not started | **Not implemented** |

**Honesty points the evidence forces:** every experimental number is *exploratory* (retrospective cross-validation on a record that has been inspected; the registry lists no confirmatory results); the project title says "real-time", but both rainfall sources used so far are retrospective and no real-time ingestion exists.

## 2. What can be shown at the first evaluation

**Completed and demonstrable:** data audit; leakage-safe framework with tests; classical and deep baselines; six-fold cross-validation; the 24 h versus 72 h experiment (decision: keep 24 h); onset-timing analysis; upstream feasibility study; the replay dashboard.

**Research findings and evidence (all exploratory):**
1. Simple models are hard to beat. Flood-window RMSE at 3 h (18 events, 27 bootstrap groups): ridge 3.960 ft, damped trend 4.017, XGBoost 4.066, LSTM 4.091, GRU 4.092, persistence 4.687 (`reports/phase1d/tables/D1_pooled_regression_metrics.csv`). Over all rows at 3 h the non-persistence models are within 0.01 ft of each other (0.2555 to 0.2650 ft; persistence 0.3078).
2. Neural networks show no reliable advantage. GRU minus ridge in flood windows: +0.037 ft [0.006, 0.071] at 15 min, +0.064 [0.003, 0.137] at 30 min, +0.099 [-0.010, 0.220] at 1 h, +0.132 [-0.019, 0.276] at 3 h (`D3_paired_model_differences.csv`). The earlier single-split result (GRU ahead of ridge, Phase 1C) did not replicate.
3. Sudden rises are hard to anticipate from stage alone. A 3 h forecast shows half of a rise a median of 2.25 h after the river reached it; in none of the 18 events did any model forecast half of a rise before it began (`reports/PHASE1E_ONSET_TIMING.md`).
4. Upstream gauges may contain earlier information. 6 of 18 events are upstream-led (best upstream lead 6.25 to 25.75 h), 6 local-or-downstream-led, 6 ambiguous (`reports/upstream_protocol_support/tables/S4_class_counts.csv`). This describes where information exists, not whether a model can use it.
5. 72 h of history was not adopted. 0 of 4 horizons improved consistently in flood windows; 72 h was 2.9 times slower to train (median 5.2 versus 1.8 min); all-row error was 1.2% to 1.6% worse at three horizons (`reports/phase1e/decision.json`, `E1b`, `E8`).

**Work in progress:** none running. The upstream-input protocol is written and awaits the research guide's decisions (15 questions).

**Remaining:** everything listed for the second and third evaluations in section 3; most importantly the hybrid model and the test of whether extra inputs help.

**Limitations and challenges:** 18 events from 14 storm clusters (6 official events, 5 storms); rainfall data (ERA5 gave about 8% of the gauge estimate on 2015-05-24; sub-daily radar only from 2015, continuity unverified); upstream gauge dropouts and reporting changes; low statistical power (6 upstream-led events); no demonstrated early anticipation; no operational system; one catchment.

## 3. Academic phase mapping (PROPOSAL)

**No academic phase requirements are documented in the repository or in the project instructions (NOT DOCUMENTED).** The university's three-evaluation structure below is therefore a proposal. Do not confuse the internal experiment phases (Phase 0, 1A to 1E) with the university's evaluations.

**Confirm with the faculty:** dates and weighting of each evaluation; whether a working hybrid is expected at the second evaluation; required deliverables (report, code, demo, viva); whether a live or near-real-time component is expected given that no real-time rainfall source is identified; whether negative or null results count as acceptable progress.

| | First evaluation (this one) | Second evaluation (proposed) | Third evaluation (proposed) |
|---|---|---|---|
| Theme | Problem, data, evaluation framework, baseline evidence | Information experiment and hybrid | Early-warning evaluation, robustness, final report |
| Objectives | Leakage-safe framework; classical and deep baselines; identify what limits forecasting | Test whether upstream rainfall and gauges change a fixed model's forecasts; implement and cross-validate the hybrid | Detection with a false-alarm cap and lead time; robustness to missing data; final report |
| Deliverables | Data audit; framework and tests; baselines; cross-validation; window experiment; onset timing; upstream feasibility and draft protocol; replay and faculty dashboards | Guide decisions; validated upstream data; configurations A to D report; hybrid implementation, tests, comparison; updated dashboard | Probability or detection head; warning-category calibration study (research prototype); robustness tests; final report and integrated demo |
| Work completed | All listed | Prerequisites only (protocol draft, baselines, framework) | Prerequisites only (detection metrics, fixed-rule evaluation) |
| Evidence available | Reports, tables, registry, 76 tests, dashboards | None yet | None yet |
| Work remaining | Guide review of the protocol | Everything listed | Everything listed; a real-time claim would additionally need a real-time rainfall source |
| Expected demonstration | Dashboards and the evidence above | A-to-D comparison per flood class; hybrid against all baselines with intervals; failure analysis | End-to-end replay with detection results, robustness figures, limitations |

Progress is counted as deliverables with evidence on disk, not percentages; task completion is not research validation.

## 4. Recommended 10 to 15 minute structure (about 13 minutes)

| Min | Slide / action | Content | Evidence to point at |
|---|---|---|---|
| 0:00-1:00 | 1. Problem and objective | Flash floods at one gauge; forecast stage 15 min to 3 h; research question about a hybrid | Dashboard section A |
| 1:00-2:30 | 2. Data and why it was audited | 668,307 readings, 99.55% complete; first dataset had no flood; official versus experimental thresholds; few events | Phase 0 report; strip chart in section G |
| 2:30-4:30 | 3. How results are made trustworthy | Storm clusters, chronological folds, embargo, pre-registration, tests, disclosed defect (deviation 3) | Protocols, registry, `pytest` |
| 4:30-7:00 | 4. Model comparison | Persistence to GRU/LSTM/Transformer; ordinary versus flood windows; no reliable neural advantage | Dashboard section D (switch horizon, then flood windows) |
| 7:00-9:00 | 5. Why: information limit | 2025-07-05 example (lag), onset analysis, upstream leads, 24 h kept over 72 h | Dashboard section E |
| 9:00-11:00 | 6. Live demonstration | Replay dashboard: event, horizon, target versus issue time, data-quality panel | `dashboard/replay/index.html` |
| 11:00-12:30 | 7. Limitations and plan | Honest limits; proposed second and third evaluations; the hybrid as proposed future work; guide questions | Dashboard sections G and H |
| 12:30-13:00 | 8. Close | One-sentence summary; invite questions | |

## 5. Demonstrations to perform (in order)
1. Faculty dashboard: roadmap (note the "proposal" banner), then model comparison (switch horizon; flood windows; evidence set to Phase 1C to show the Transformer).
2. Findings 2 and 3: the Phase 1C versus Phase 1D reversal, and the 2025-07-05 lag chart.
3. Replay dashboard, event 2025-07-05, 3 h: forecasts rise about 2.75 h after the river; hover for issue and target times; toggle "issue time".
4. Replay dashboard, event 2024-07-24: grey bands (missing observations) and the hatched "no forecast" strip: data quality shown, not hidden.
5. Terminal: `.venv/bin/python -m pytest -q` (about 10 s, 76 passed).
6. `experiments/REGISTRY.md` and one protocol with its "Deviations" section.
Do not demonstrate anything that implies live forecasting.

## 6. The 60-second summary
"We built the evidence base for a flash-flood forecasting study on one river gauge: audited 19 years of data, designed a leakage-safe evaluation, trained classical and neural baselines, and cross-validated them on 18 held-out floods. The honest result is that neural networks and a Transformer do not yet beat simple methods, and that every model reacts to a flood rather than anticipating it, because the gauge's own history does not contain the rain. Upstream gauges rose hours earlier in about a third of events, so the next stage tests whether adding upstream information helps, and then builds and compares the hybrid model. The hybrid itself is not built yet; the baselines and the upstream study are what let us judge it fairly."

## 7. Likely faculty questions and suggested answers

1. **Where is the hybrid model?** Not implemented. It is proposed for the second evaluation. What exists is the complete evaluation framework and the baselines it must beat.
2. **Why build baselines and an upstream study before the hybrid?** Because the baselines show the limit is probably information, not model size: ridge matches the networks, and no model forecast half of a rise before it began. A hybrid on the same stage-only inputs would likely hit the same limit; without strong, leakage-safe baselines any hybrid gain could not be judged. The upstream study tests the information hypothesis first.
3. **Isn't "neural networks do not beat ridge" a failed project?** No. It is a result obtained under a stricter protocol than the single split that first suggested otherwise. It sharpens the question: what information does a model need? The conclusion is limited to hydrology-only inputs, one architecture family and untuned settings.
4. **How do you know there is no data leakage?** Whole storms are kept together; folds are chronological with a 27 h 15 min embargo (24 h window + 3 h horizon + one step); scalers and target scales are fitted on training rows only; tests check these properties. A data-handling defect was found by us, fixed, and disclosed (deviation 3).
5. **Only 18 events: is that enough?** It limits certainty, which is why every result is labelled exploratory, intervals use storm-cluster bootstrap, and event counts and cluster counts are shown beside every event metric. Six upstream-led events cannot give statistical significance (smallest p-value 0.031), so that stage is framed as effect-size estimation.
6. **Why not a random train/test split?** Adjacent 15-minute samples are near-copies from the same storm; a random split inflates results.
7. **Is the system real-time?** No. Both rainfall sources used so far are retrospective. The replay dashboard replays saved forecasts. Real-time use would need a real-time rainfall source that has not been identified.
8. **What is the contribution if the hybrid is not novel?** The hybrid architecture itself is not claimed as novel. The contribution is a rigorous, reproducible evaluation for sparse flood events, evidence about where forecasts lag and why, and a controlled test of upstream information, with the hybrid compared fairly against strong baselines.
9. **Why did the Transformer do badly?** We cannot say why. It trained unstably (best epoch 1 to 15; validation loss 0.319 to 0.363 versus 0.276 to 0.309 for GRU/LSTM) in one untuned configuration. This is not evidence against Transformers; a bounded diagnostic is proposed only if approved.
10. **Why keep the 24 h window?** A pre-registered rule: adopt 72 h only if it consistently improved flood-window error at two or more horizons. It improved at none, was 2.9 times slower, and showed no better detection or onset timing.
11. **Do upstream gauges prove a better model is possible?** No. They show that earlier information exists in about a third of events (6 to 8 of 18 depending on the timing rule). Whether a model can use it is the experiment not yet run.
12. **Which results are most reliable?** The cross-validated comparisons (Phase 1D) and the pre-registered window decision (Phase 1E), still exploratory. The Phase 1C single-split result is the least reliable (4 flood events).
13. **What went wrong along the way?** A rolling-feature defect blanked 72 hours after one missing sample and hid the largest test flood; a first upstream-timing analysis dropped gauges silently; the protocol support analysis later found failed downloads and 5-minute reporting. Each was found, documented and corrected; the registry and protocols record them.
14. **Why is the 2025-07-05 example important?** It is an official-stage flood (peak 30.03 ft) in which the stage rose about 28.6 ft in 6.75 h from onset to peak; the 3 h forecasts stayed flat until the river started moving, then showed 10 ft 2.75 h after the river did.
15. **What if upstream inputs do not help?** The protocol is designed so a null result is informative (per-event effects, controls, a harm check); the hybrid question would then be reframed with the guide.
16. **How will you measure success later?** Pre-registered rules: paired storm-cluster bootstrap, per-seed and per-fold consistency, flood-window RMSE at 1 h and 3 h as primary, event detection with counts, separate reporting for upstream-led and local floods.
17. **What are the main risks?** Radar rainfall availability and continuity; few upstream-led events; the guide's decisions on the protocol; compute for multi-seed hybrid runs; possible faculty expectation of a live component.
18. **Is the data reliable?** 99.55% complete at the target gauge; 2026 values are provisional; upstream gauges have dropouts, one datum step, mixed reporting intervals; ERA5 rainfall was unreliable for flood timing.
19. **Why RMSE and event metrics?** About 500,000 held-out rows are mostly quiet river, so overall RMSE hides flood behaviour; flood-window RMSE and event-level detection are reported separately.
20. **What does "exploratory" mean here?** The whole record, including the later test years, has been inspected, so no result is untouched validation. We report that rather than hide it.

**Questions about the missing hybrid, short form:** (a) "Is the second evaluation realistic for a working hybrid?" Possibly, if the guide approves the plan quickly; confirm the expectation with faculty. (b) "Could you have built it now?" Yes technically, but a hybrid on stage-only inputs would answer a less informative question. (c) "What will it contain?" A Transformer branch on a long window, an LSTM branch on a short window, fusion, and four horizon heads, compared with every baseline on the same folds.

## 8. Missing evidence and unresolved questions
- The university's three-evaluation requirements (dates, weights, deliverables): **NOT DOCUMENTED**.
- The research guide has not reviewed the upstream-input protocol; its 15 questions are open.
- No confirmatory (untouched-test) result exists; none is possible on the current record without a new data period.
- The hourly radar rainfall product has not been downloaded or validated; folds 1 to 3 have no radar data in training.
- Real-time data availability for any live component has not been investigated.
- A second catchment is optional and not started.
- The Phase 1D report still describes onset lag as "roughly three hours"; the measured median is 2.0 to 2.5 h at the 3 h horizon (use the measured value when speaking).

## 9. Launch commands and files
```
open dashboard/evaluation/index.html          # faculty dashboard (offline)
open dashboard/replay/index.html              # historical-replay demonstration
.venv/bin/python -m pytest -q                 # test suite
PYTHONPATH=src .venv/bin/python scripts/build_evaluation_dashboard.py   # rebuild the faculty dashboard from the tables
```
The faculty dashboard has a "Projector mode" button (larger text), a light/dark theme button, and print styles; every number in its text comes from a listed fact (Evidence section).
