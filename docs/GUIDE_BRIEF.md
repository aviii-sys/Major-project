# Brief for the research guide: where the project stands and one decision needed

Project: Hybrid Transformer-LSTM for multi-horizon river-stage forecasting and early warning, USGS 08167500 (Guadalupe River near Spring Branch, Texas). Status date: 2026-11-22.

## What has been established (all test-period numbers are exploratory; the 2007-2026 record has been inspected, so nothing is untouched validation)
1. **Data:** 15-min stage 2007-10 to 2026-11 (99.55% complete). Official NWS stages are action 25, minor 30, moderate 36, major 39 ft. There are 20 events at >= 10 ft (an experimental target, not a flood stage) from 16 distinct storms, and 6 official-stage events from 5 storms. The earlier 2022-2023 data held no flood.
2. **Strong simple baselines:** ridge regression and a two-parameter damped trend are very hard to beat. Under six-fold blocked chronological cross-validation (18 evaluated events, 14 storm clusters), GRU and LSTM show **no robust advantage**; in flood windows at 15 and 30 minutes they are significantly worse than ridge and the damped trend; at 1 h and 3 h no difference can be established. An earlier GRU advantage on a single split did not replicate.
3. **The central limitation:** every model, deep or classical, trails the onset of sharp rises by about 3 hours at the 3 h horizon. Event detection with a fixed alarm rule is not better for the deep models (rapid rises of at least 4 ft in 3 h, 3 h horizon: ridge detects 12 of 25, damped trend 10, GRU 7, LSTM 4).
4. **Rainfall inputs so far:** ERA5 captures only about 8% of the gauge-measured basin rainfall on the 2015-05 and 2016-05 flood days; a gauge-based daily rainfall product exists but is daily, so it cannot signal storm onset.

## New finding (descriptive, no model trained): upstream gauges
Seven upstream gauges have 15-min stage for the whole 2007-2026 period (an eighth, Bergheim, since 2016). Over the 18 cross-validated events, 13 show a consistent upstream rise, and for **6 to 8 of 18** (depending on how the rise is timed; multi-pulse storms are ambiguous) the upstream gauge rose **6 to 26 hours** before Spring Branch (including 3 of the 5 official storms: 2016-05, 2025-07, 2026-07). For **6 to 8 of 18** the rain fell downstream of, or level with, the upstream gauges, so no upstream warning exists (including the official 2015-05 and 2015-10 floods). Upstream gauges also dropped out during two of the largest floods (2018-10, 2025-07), and one key gauge (Comfort) has a +2.9 ft datum shift in 2011. Details and the data inventory: `docs/UPSTREAM_INPUT_FEASIBILITY.md`.

## Interpretation
The data support the hypothesis that part of the limitation is missing upstream information, not insufficient model complexity: for about a third of events the information needed to anticipate the rise exists hours earlier upstream. They do **not** show that upstream gauges would solve early warning generally, and they do not show that a model can exploit that information; that needs a cross-validated experiment. For storms that fall below the upstream gauges, only rainfall information at the right place and time would help, and hourly radar rainfall (MRMS gauge-corrected QPE, Iowa State archive) appears to exist by date for 16 of the 18 events (from late 2014), but it has not been downloaded or validated yet.

## Decisions requested
1. May the central claim be reframed from "a hybrid architecture improves forecasting" to "a hybrid that also sees upstream context improves forecasting of upstream-driven floods, and its limits are reported for the others"?
2. Is it acceptable to scope the early-warning claim to events with an upstream signal and to state explicitly that stage-based models cannot warn for the rest?
3. Should MRMS radar rainfall be validated first against the 92-station gauge product on the 2015 and 2016 floods, where ERA5 failed?
4. Which upstream gauge first (Comfort has the best coverage, 13 h median lead in 9 consistent events)?
5. Should the hybrid be built before or after the upstream-input experiment (our recommendation: after, so the comparison starts from the best available inputs)?
