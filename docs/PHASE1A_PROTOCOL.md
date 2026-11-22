# Phase 1A Evaluation Protocol (fixed BEFORE any model was trained or scored)

Written 2026-11-22, prior to running `scripts/run_phase1a.py`. Any later change must be recorded in the "Deviations" section at the bottom, with the reason.
Scope: persistence, naive trend, ridge (linear) and XGBoost baselines for **stage** at the USGS 08167500 gauge. No hybrid, LSTM, GRU or Transformer.

## 0. Labels and what may be claimed
- **Official** categories (NWS SRGT2): action 25 ft, minor 30 ft, moderate 36 ft, major 39 ft. Results at these levels are **descriptive only**; there are very few independent events (Phase 0). No official flood-detection capability is claimed.
- **Experimental development-stage exceedance targets**: stage >= 10 ft and >= 15 ft. These are NOT flood thresholds; they were chosen because enough events exist.
- **Experimental rapid-rise indicators**: rise >= 4 ft in 3 h and >= 8 ft in 3 h. These are NOT established warning thresholds.

## 1. Data and masking
- Hydrology: USGS IV 2007-10-02 to 2026-11-22, 15-min grid, UTC, stage in feet. Discharge is not used as a predictor in 1A (at one gauge it is a near-deterministic function of stage); it returns in 1B.
- A sample is **invalid** if stage is missing or stage <= -1.2 ft (flat sensor-floor / dry-channel periods, Phase 0). Invalid samples are never used as inputs, targets or event evidence.
- Provisional (P) data exist only from 2026-01-12. They are never used for training or tuning (they fall in the test period). Test results are reported both with and without them.
- Rainfall (secondary until NLDAS-2 is obtained): area-weighted ERA5 basin mean (Open-Meteo). Rain features use only hourly labels <= floor(issue time to the hour) (causal). Phase 0 showed ERA5 rainfall is unreliable for some floods, so rain is evaluated as an **ablation** (H = hydrology only, H+R = hydrology + rain), never assumed useful.

## 2. Forecast task
At issue time t (every 15 min), predict stage at t+h for h in {15 min, 30 min, 1 h, 3 h}. Models regress the change `s(t+h) - s(t)`; stage forecast = `s(t) + predicted change`. Rows need valid s(t), valid target s(t+h) and all features available (counts of dropped rows are reported).

Features (all computed from data with timestamp <= t): s(t); s(t) - s(t-k) for k = 15 min, 30 min, 1 h, 2 h, 3 h, 6 h, 12 h, 24 h; max stage over the previous 24 h and 72 h. H+R adds: latest hourly basin rain, minutes since that hour (0/15/30/45), and rain sums over the last 3, 6, 12, 24, 72 and 168 hourly labels.
Models: **persistence** (change = 0); **trend** (change = h x 1-hour rate of change; naive extrapolation, extra sanity baseline); **ridge** (standardised, alpha tuned on validation); **XGBoost** (squared error, depth tuned on validation, early stopping on validation).

## 3. Storm grouping and splits (chronological, storm-grouped)
- A sample is **elevated** if stage >= 5 ft or its 3-hour rise >= 1 ft. Elevated samples separated by < 72 h are merged into one **storm cluster** (interval from first to last elevated sample). A cluster is never divided between splits.
- Nominal boundaries: validation starts 2018-01-01, test starts 2022-01-01 (UTC). A boundary falling inside a cluster is moved to just after that cluster's end. Train = before validation; validation = tuning only; test = held out once.
- Targets must not cross a boundary: issue times within 3 h before a boundary are dropped from the earlier split. Input lookbacks may reach earlier data (causal, legitimate).
- Hyperparameters are tuned on validation using a train-only fit; the chosen settings are then refit on train + validation and scored once on test.
- **No random window splits are used anywhere.**
- Supplementary **blocked cross-validation** (6 contiguous time blocks, boundaries moved outside clusters, 3 h purge, models trained on the other blocks including FUTURE blocks) is reported only to obtain out-of-sample forecasts for every historical event. It is non-causal and is labelled as such; it is never mixed with the chronological test results.

## 4. Event definitions
**Observed exceedance events** for stage threshold T: runs of valid samples with stage >= T; runs separated by < 24 h (below T or missing) are merged. Start t0 = first sample >= T; end t1 = last sample >= T.
**Observed rapid-rise events** for R in {4, 8} ft: indicator z_R(tau) = s(tau) - s(tau - 3 h) >= R (both valid); runs merged if separated by < 24 h; t0 = first tau with z_R, t1 = last.
**Independent events:** merged events as above; for the official thresholds the report also states the number of distinct storm clusters.

## 5. Alarms, hysteresis, matching, false alarms, lead time (per model, per horizon h)
- **Raw flag** at issue time t: exceedance: `s_hat(t+h) >= T`; rapid rise: `s_hat(t+h) - s(t+h-3h) >= R` (the base stage is already observed at t because h <= 3 h). Missing or invalid forecasts count as "no flag".
- **Hysteresis:** the alarm turns ON at the first raw flag and turns OFF only after 4 consecutive issue times (1 h) without a raw flag.
- **Alarm episode:** a contiguous ON interval with issue times [a0, a1]. Its **target interval** is [a0 + h, a1 + h].
- **Matching tolerance** tau = 1 h. An episode is **matched** to an observed event if its target interval overlaps [t0 - tau, t1 + tau]; otherwise it is a **false alarm**.
- **Early hit:** an observed event is detected early if some matched episode has a0 < t0. **Lead time** = t0 - (earliest such a0). **Late detection:** matched only by episodes with a0 >= t0 (counted separately, not as a hit). **Miss:** no matched episode.
- Metrics: POD = early hits / events; late fraction; FAR = false-alarm episodes / all alarm episodes; CSI = hits / (hits + misses + false-alarm episodes); false alarms per year; median and range of lead time. Intervals: Clopper-Pearson (exact binomial, 95%) for POD and FAR; counts are always shown next to rates.

## 6. Regression metrics and uncertainty
- RMSE and MAE in feet and skill versus persistence (1 - MSE_model / MSE_persistence), per horizon, on (a) all test rows, (b) **event windows** (issue times from 6 h before the rise onset until the peak, for observed >= 10 ft events and for each official event).
- **Peak capture:** for each event and horizon h, the forecast of the peak stage issued h before the peak, as signed error and ratio to the observed peak.
- Uncertainty: cluster bootstrap (2,000 resamples) over storm clusters (quiet periods are weekly blocks) for RMSE, MAE and skill; exact binomial intervals for event rates; per-event tables for all events.
- The small number of independent official events is stated beside every official-threshold result.

## Deviations
1. 2026-11-22, before any test result was inspected: the ridge alpha grid was extended from {0.1, 1, 10, 100} to {0.1, 1, 10, 100, 1000, 10000} because a smoke run (80 trees, validation-only selection) chose the upper edge of the old grid. Decision based on validation only.
3. **Found AFTER inspecting first-run test results (disclosed deliberately).** The first full run used strict rolling windows (`max24h`, `max72h` needed 100% of samples). One missing sample at 2026-07-16 18:15 made every row of the 2026-07-17 event (36.75 ft) ineligible, so all models "missed" it for lack of a forecast. This is a data-handling defect, not a modelling result. Changes: (a) isolated gaps up to 1 h are bridged by a causal forward-fill for the lagged reference value only; (b) rolling maxima need >= 50% of the window; (c) an event is **not evaluable** at a horizon if < 80% of the issue times that could earn lead credit (from t0 - h - 1 h to t0) are eligible rows, and such events are excluded from POD denominators and listed separately instead of counted as misses; (d) regression test added. All models were re-run end to end; **none of the first-run numbers are used anywhere.** These changes address missing data, not metric values, but because they were made after seeing test output, readers should weigh that.
4. The sensor-floor mask in this protocol is stage <= -1.2 ft (16,538 rows). Phase 0 reported 2,355 rows within 0.02 ft of the minimum; the mask is deliberately broader.
