# Phase 1E onset-timing comparison: GRU 24 h versus 72 h (E18)

**Post-hoc diagnostic on SAVED out-of-fold predictions; retrospective blocked cross-validation, NOT untouched validation; exploratory; 18 events from 14 storm clusters.** Specification written before the analysis: `docs/PHASE1E_ONSET_PROTOCOL.md`. Nothing was retrained; no Phase 1C, 1D or 1E artifact was modified. The Phase 1E decision (keep 24 h) was made by the pre-registered rule and is not reopened here. All numbers are copied from `reports/phase1e_onset/tables/` (names in brackets).

## 0. Headline
- **No evidence that the 72 h window changes how the GRU responds to a rise.** Under the interpretation rule fixed in advance, neither criterion is met: at 10% and 50% of the rise, the 72 h forecast reaches the level earlier in at most 3 of 18 events and later in at most 6 (the rule needed the same sign in at least 12 of 18), and the number of events with a pre-onset anticipation flag is the same (13 of 18 flagged by all three seeds at 3 h for both windows; per-seed counts 14/14/15 versus 15/14/14).
- **Both windows respond to the rise, they do not anticipate it.** In none of the 18 events did any variant (GRU 24 h, GRU 72 h, damped trend, ridge, persistence) issue a forecast showing half of the eventual rise before the river had begun to rise (`O3c`). The first such forecast was issued a median of about 2 h after the rise onset at both 1 h and 3 h horizons.
- **The 3 h forecasts are late by about 2 to 2.5 hours, not a full 3 hours.** Median lag between the time the river reached a level and the time the 3 h forecast showed it: 2.5 h at 10% of the rise, 2.25 h at 50%, 2.0 h at 90% for GRU 24 h (2.5 / 2.4 / 2.25 h for 72 h), against 3.0 h for persistence (`O3b`, `O1`). This refines the "roughly three hours" wording used in earlier phases.
- **Pre-onset flags are mostly a reaction to the first uptick, and they do not separate the models.** At 3 h the GRU flags 13 of 18 events, but the damped trend (which cannot anticipate) flags 8 and ridge 5; 76 of 86 flagged GRU event-seed pairs fire within 1 h of the onset sample. The sharpest recent official event (2025-07-05, 22 ft rise over 3 h) got no pre-onset signal from either window (largest predicted change 0.06 ft).
- Peak-capture ratios are **not** used to support any conclusion here.

## 1. Definitions used (all existing, `docs/PHASE1E_ONSET_PROTOCOL.md`)
Events: the 18 evaluated >= 10 ft events (`O0`); rise onset `o` = `events.rise_onset_index` (last sample within 0.5 ft of the preceding-72 h minimum before the first exceedance); levels 10%, 50%, 90% of the rise from baseline to peak. A forecast issued at time `t` is a forecast of the stage at `t + h`; plotted at its target time unless stated. **Lag** = time the forecast shows a level minus time the river reached it; **lead** = `h` minus lag = time the river reached the level minus the issue time of the first forecast that shows it (0 = followed the river, as persistence does; `h` = exact). Variants: GRU 24 h and 72 h (3 seeds each, Phase 1E), persistence, damped trend, ridge H (Phase 1D). The time grid is 15 min, so differences below 0.25 h cannot be resolved and many paired differences are exactly zero.
Correctness checks: the saved stage matches the project series; the fixed-rule detection counts recomputed from these arrays equal Phase 1E `E6` in all 48 seed/horizon/definition cells (`O7b`); 16 unit tests on synthetic forecasts with known lead and lag (`tests/test_onset.py`).

## 2. Level-arrival timing (`O1`, `O2`, `O3`, `O3b`; figures `figO1_*`, `figO2_*`)
Median lead in hours (GRU values are medians over the 18 events x 3 seeds; maximum possible = horizon):

| Horizon | Level | GRU 24 h | GRU 72 h | damped trend | ridge H | persistence |
|---|---|---|---|---|---|---|
| 1 h | 10% | 0.25 | 0.25 | 0.25 | 0.25 | 0 |
| 1 h | 50% | 0.5 | 0.5 | 0.5 | 0.625 | 0 |
| 1 h | 90% | 0.75 | 0.75 | 0.75 | 0.75 | 0 |
| 3 h | 10% | 0.5 | 0.5 | 0.375 | 0.5 | 0 |
| 3 h | 50% | 0.75 | 0.625 | 1.0 | 1.0 | 0 |
| 3 h | 90% | 1.0 | 0.75 | 1.375 | 1.0 | 0 |

So at 3 h the GRU shows a level only 0.5 to 1 h before the river reaches it, out of a possible 3 h, and its lag does not shrink much from the start of the rise to near the peak (median catch-up, lag at 10% minus lag at 90%: 0 h at 3 h, 0.25 h at 1 h; the damped trend 0.75 h at 3 h). Except at the 10% level at 3 h (0.5 h versus 0.375 h for the damped trend), the GRU is not earlier than the damped trend or ridge at any level.

**Paired comparison, 72 h minus 24 h, per event (seed-mean lead; all 18 events; `O3`)**

| Horizon | Level | 72 h earlier | 72 h later | equal | median difference (h) | events beyond the 24 h seed range |
|---|---|---|---|---|---|---|
| 1 h | 10% | 1 | 2 | 15 | 0 | 0 |
| 1 h | 50% | 3 | 6 | 9 | 0 | 2 |
| 1 h | 90% | 4 | 7 | 7 | 0 | 4 |
| 3 h | 10% | 3 | 3 | 12 | 0 | 1 |
| 3 h | 50% | 2 | 6 | 10 | 0 | 5 |
| 3 h | 90% | 2 | 9 | 7 | -0.04 | 1 |

At 3 h and 90% of the rise the 72 h forecasts reach the level later in 9 of 18 events and earlier in 2 (median lead 0.75 h versus 0.96 h for 24 h); this is descriptive only (it is not one of the pre-specified criteria, and only 1 event lies beyond the seed range). "Beyond the seed range" is a weak yardstick where the 24 h seeds agree exactly (range 0), because any 0.25 h step then counts. Excluding the four events with an ambiguous onset gives the same pattern (`O3`).

## 3. Pre-onset anticipation (`O4`, `O5`, `O5b`, `O5c`; figures `figO3_*`, `figO4_*`)
A forecast counts as anticipating if it is issued while the river has not yet risen (stage within 0.5 ft of the baseline, issue times from 6 h before the onset to the onset) and already predicts a rise of at least 0.5 ft over its horizon.

| Horizon | Events flagged by all 3 seeds, 24 h / 72 h | Flagged event-seed pairs (of 54), 24 h / 72 h | Per-seed flagged events (of 18), 24 h / 72 h | Damped trend / ridge flagged (of 18) |
|---|---|---|---|---|
| 15 min | 0 / 0 | 0 / 0 | 0,0,0 / 0,0,0 | 0 / 0 |
| 30 min | 0 / 0 | 3 / 1 | 1,0,2 / 0,0,1 | 0 / 0 |
| 1 h | 4 / 5 | 20 / 18 | 7,6,7 / 6,6,6 | 0 / 0 |
| 3 h | 13 / 13 | 43 / 43 | 14,14,15 / 15,14,14 | 8 / 5 |

- The two windows are indistinguishable (differences of 0 to 2 pairs, inside the seed-to-seed spread of 1 to 2 events).
- **The flag is a weak test of anticipation.** The damped trend, which extrapolates only a rise already in progress, flags 8 of 18 events at 3 h. The first GRU flag falls a median of 0.5 h before the onset sample (interquartile range 0.25 to 0.75 h for both windows), and 76 of the 86 flagged GRU event-seed pairs at 3 h are within 1 h; the exceptions are two events (2018-09-09, a slow multi-stage rise with an ambiguous onset, and the provisional 2026-06-15 event) where the first flag is 3.5 and 4.5 h before the onset sample, and the trend flags 2018-09-09 too. The onset sample is by definition the last sample within 0.5 ft of the baseline, so a forecast reacting to the first few hundredths to tenths of a foot of rise can lie slightly before it.
- **Size of the signal against what followed.** At 3 h, in the 11 events where a rise of at least 4 ft followed pre-onset issue times, the largest pre-onset predicted change averaged 0.06 to 2.1 ft for GRU 24 h (0.05 to 1.7 ft for 72 h), against realised rises of 4.2 to 22.2 ft. For 2025-07-05 the predicted change was 0.06 ft (24 h) and 0.05 ft (72 h) while 22.2 ft followed (figure `figO4`: both forecasts stay at zero until the river starts to rise, then jump).
- Background rate: outside every flood and rapid-rise window the same 0.5 ft flag fires at 0.14% to 0.19% of 3 h issue times for the GRU (damped trend 0.10%, ridge 0.08%) and 0.06% at 1 h, so the flags in the pre-onset windows (13 of 18 events) are far more frequent than chance, consistent with reaction to the early rise rather than noise.
- Sensitivity (`O5b`): at a 0.25 ft threshold the counts are 47 / 46 (3 h, 24 h / 72 h) and at 1.0 ft 20 / 15 event-seed pairs (72 h flags fewer large pre-onset predictions at 3 h; per-seed counts at that threshold were not examined, so I do not interpret the difference of 5 pairs).

## 4. When was a forecast of half the rise first issued? (`O3c`)
Issue time of the first forecast that shows 50% of the eventual rise, relative to the rise onset (median over events, hours; positive = after the river had begun to rise): GRU 24 h 2.0, GRU 72 h 2.0, damped trend 1.6 (3 h) and 1.9 (1 h), ridge 1.6 (3 h) and 2.0 (1 h), persistence 2.5 at 3 h. **Events in which such a forecast was issued before the onset: 0 of 18 for every variant at every horizon.** At the 10% level (a small rise, 0.5 to 3.5 ft depending on the event) the GRU issued such a forecast before the onset in 7 of 18 events at 3 h (4 events for all seeds, identical for both windows; damped trend 2, ridge 2), mainly slow or multi-stage rises and tiny levels.

## 5. Peak timing (`O6`)
The maximum of the forecast series occurs a median 2.0 h after the observed peak at 3 h for both GRU windows (persistence 3.0 h, damped trend 2.1 h, ridge 1.9 h), 0.4 to 0.5 h at 1 h; the forecast maximum is about 3% above the observed peak in the median for both windows at 3 h (ratio 1.033 versus 1.029). Larger overshoot occurs in some events (figure `figO1`).

## 6. Fixed-rule alarm lead on the existing definitions (`O7`, `O7d`)
Applying the Phase 1A/1B alarm rule to the saved predictions (counts equal Phase 1E `E6`), median lead of early hits over events and seeds:

| Definition (events) | Horizon | Early hits, 24 h / 72 h (seed mean) | Median lead of early hits, 24 h / 72 h (h) |
|---|---|---|---|
| stage >= 10 ft (18) | 1 h | 18 / 18 | 0.5 / 0.5 |
| stage >= 10 ft (18) | 3 h | 17 / 17 | 0.75 / 0.75 |
| rise >= 4 ft in 3 h (25) | 1 h | 22.7 / 23.0 | 0.5 / 0.5 |
| rise >= 4 ft in 3 h (25) | 3 h | 5.3 / 3.7 | 0.625 / 0.25 |

Leads of early hits are below an hour for both windows. The experimental definitions are not official flood levels and nothing here is a warning-capability claim.

## 7. Events where onset timing cannot be calculated reliably (`O0`, `O1` flag columns)
- **Ambiguous onset (R3, onset-to-peak > 24 h; slow multi-stage rise, so "the onset" is not one event):** 2016-05-19 (38.5 h; the window starts at the preceding 2016-05-18 event), 2018-09-09 (49.8 h), 2024-07-24 (42.3 h), 2026-07-15 (47.5 h; contains the first 25 ft peak of the two official 2026 events). In these events the 10% level and the pre-onset test are not meaningful (values such as a 20 h lead at 10% in 2018-09-09 or 30 h at 50% in 2024-07-24 come from forecast spikes in a first slow pulse); the 50% and 90% levels remain defined but may be reached in an earlier pulse. They are drawn as hollow markers and summaries are given with and without them.
- Provisional data (R5; informational): 2026-06-15 and 2026-07-15.
- Missing observations (R2, more than 5% of observed samples missing in the window): 2024-07-24 only (10.8% missing; also an R3 event). No event failed the forecast-coverage (R1) or low-amplitude (R4) rules.
- Lag resolution is one step (15 min): for 15 min and 30 min forecasts differences cannot be resolved, so those horizons are in the tables but carry no interpretation.

## 8. The official events (`O8`; 3 h forecasts, seed means; 24 h / 72 h / damped trend / ridge)
| Event (peak) | Lead at 50% of the rise (h) | First forecast of half the rise, issued after onset by (h) | Forecast peak time minus observed peak (h) |
|---|---|---|---|
| 2015-05-23 (34.5 ft) | 0.25 / 0.33 / 0.75 / 0.75 | 4.0 / 3.9 / 3.5 / 3.5 | 3.0 / 3.0 / 3.0 / 3.0 |
| 2015-10-30 (30.1 ft) | 0.25 / 0.17 / 0.5 / 0.5 | 2.0 / 2.1 / 1.75 / 1.75 | 3.0 / 3.0 / 2.25 / 2.25 |
| 2016-05-29 (26.1 ft) | 0.75 / 0.75 / 1.75 / 1.0 | 2.0 / 2.0 / 1.0 / 1.75 | 1.5 / 1.5 / -1.5 / 1.5 |
| 2025-07-05 (30.0 ft) | 0.75 / 0.75 / 1.0 / 1.0 | 0.75 / 0.75 / 0.5 / 0.5 | 1.8 / 2.5 / 3.0 / -3.0 |
| 2026-07-15 (36.8 ft, provisional, ambiguous onset) | 0.83 / 0.67 / 0.5 / 1.0 | 13.9 / 14.1 / 14.3 / 13.8 | 1.9 / 2.0 / 3.0 / 3.0 |
Peak-time values of one hour or more in magnitude for single events are sensitive to forecast noise near a flat peak and are not interpreted individually. In every official event the first 3 h forecast of half the rise came after the river had started rising; the largest 24 h versus 72 h difference in these three columns is 0.67 h (forecast peak time, 2025-07-05) and the others are 0.17 h or less.

## 9. Does a longer history change response behaviour? (pre-specified rule, protocol section 5)
**No evidence that it does.** Criterion (a) (same-sign lead difference in at least 12 of 18 events at 10% and 50%, with the median above the 24 h seed range): not met at either horizon (maximum 6 events with the same sign at those levels; the median difference is zero). Criterion (b) (number of pre-onset anticipation flags differing by more than the seed spread): not met (equal at 3 h; differences of 2 pairs at 1 h within the seed spread). The descriptive 90% level at 3 h, where 72 h tends to be later (9 of 18 events), points if anything the other way from an improvement.
**Genuine anticipation versus catching up:** neither window anticipates the rise (no forecast of half the rise before the river started to rise, in any event), and neither shows strong catching up (median lag falls only from 2.5 h at 10% to 2.0 h (24 h) or 2.25 h (72 h) at 90%, and the forecast peak is about 2 h after the observed peak). The pattern is that of a model reacting to a rise already in progress and extrapolating it, as the damped trend does.

## 10. Limitations
18 events from 14 storm clusters, four with ambiguous onset; three seeds per window; 15-min resolution; leads and lags are first-crossing times and therefore sensitive to forecast noise near a level (spikes can produce early or very large leads in slow events); level fractions are chosen conventions (10/50/90%); the 0.5 ft flag reuses the onset tolerance and is not discriminating (above); the analysis is post-hoc, descriptive, no p-values, no pooling across horizons; two events include provisional 2026 data; the hydrology-only GRU has no information about rain or upstream stages, so the absence of anticipation is expected and says nothing about models with such inputs; retrospective blocked cross-validation, not untouched validation.

## 11. Files, deviations, reproduction
- Report inputs: `reports/phase1e/oof_predictions.csv.gz`, `reports/phase1d/oof_predictions.csv.gz`, `reports/phase1e/tables/E6_fixed_rule_detection_per_seed.csv`. Outputs: `reports/phase1e_onset/tables/O0..O8*` (csv, md), `figures/figO1_events_3h_forecast_vs_observed.png`, `figO1_events_1h_forecast_vs_observed.png`, `figO2_level_arrival_lead_24h_vs_72h.png`, `figO3_pre_onset_anticipation.png`, `figO4_issue_time_view_official_events.png`, `run_summary.json`. Code: `src/flashflood/onset.py`, `scripts/run_onset_timing.py`; tests `tests/test_onset.py`; registry E18.
- Deviation (also in the protocol): after the first run, the issue-time-relative-to-onset columns, `O3c` and `O8`, and `O7d` were added because the pre-specified 0.5 ft anticipation flag proved non-discriminating (the damped trend flags 8 of 18 events). No pre-specified definition, flag or threshold was changed; figure axes were clipped for readability and the two-line titles added.
- Reproduce: `PYTHONPATH=src python scripts/run_onset_timing.py` (about 5 s).
