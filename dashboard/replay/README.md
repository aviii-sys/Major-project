# Historical-replay dashboard (Stage 1, experiment E19)

> **Exploratory retrospective historical replay using saved out-of-fold predictions. This is not a live forecasting system or an operational flood-warning service.**

A single self-contained web page (`index.html`, 1.4 MB, no server, no internet, no external libraries) that replays 18 historical flood events at USGS 08167500 (Guadalupe River near Spring Branch, TX) and compares the **saved** out-of-fold forecasts of several models with what the river did. Nothing is retrained, smoothed or interpolated; where a forecast or observation does not exist the line is left broken and the gap is shown. There are no warning categories, alerts, live data or real-time functionality.

## Launch
```
open dashboard/replay/index.html                                   # macOS; or double-click the file in any modern browser
python -m http.server --directory dashboard/replay 8000            # optional: then browse to http://localhost:8000
```
Rebuild after any change to the template or the saved predictions (about 4 s):
```
PYTHONPATH=src .venv/bin/python scripts/build_replay_dashboard.py
```
The page state (event, horizon, models, zoom, tab) is kept in the URL hash, so a view can be bookmarked or shared as `index.html#e=2025-07-05T03%3A45&h=3h`.

## What it shows
- **Event replay tab:** pick any of the 18 evaluated >= 10 ft events (official >= 25 ft events are labelled; two events include provisional USGS data) and a horizon (15 min, 30 min, 1 h, 3 h). Observed stage versus the saved forecasts of GRU, LSTM, ridge regression and the damped trend (default), plus persistence, XGBoost and the 72 h-input GRU (optional). A shaded band shows the range of three GRU 24 h seeds. Models are drawn with fixed colours and dash patterns so the comparison is the same for every event and horizon.
- **Issue time versus target time:** a forecast made at `t` for horizon `h` is a forecast of the stage at `t + h`. The default view draws it at `t + h` beside the observed line; the alternative draws it at `t`, with a dotted line for the stage that actually followed. The tooltip always states both times.
- **Forecast error** panel (forecast minus the stage observed at the target time), synchronised crosshair and tooltip, drag-to-zoom, zoom presets, light and dark themes, a keyboard-accessible data table of the plotted series.
- **Actual and predicted peak levels:** the observed peak; the forecast issued `h` before the peak (Phase 1D/1E definition) and the highest forecast value with its time relative to the observed peak, per model.
- **Forecast errors and event-level metrics:** flood-window RMSE, MAE, bias, largest error and rows scored per model; an RMSE matrix by horizon; the event-level results of the fixed alarm rule used in Phase 1A to 1E (early hit, late, miss, lead time) for the evaluated >= 10 ft event and for the official (25 ft) and rapid-rise (4 ft in 3 h) events inside the window. These are evaluation results with experimental thresholds, not warnings.
- **Data-quality information:** observed samples missing and the longest gap (grey bands), provisional USGS samples (orange strip), history completeness before each issue time (24 h and 72 h), and a hatched strip with a reason breakdown for issue times that have no forecast.
- **All events tab:** the same metric for all 18 events and every model at one horizon (RMSE, MAE or peak ratio), median over events, and the pooled value over all 18 windows (which reproduces the Phase 1D/1E "flood windows of the 10 ft events" subset). Click a row to open the event.
- **About and data tab:** definitions, limitations and the SHA-256 of every saved file the page was built from.

## Data sources and prediction coverage
| Content | Source (all saved, none regenerated) |
|---|---|
| Observed stage, missing runs, provisional flags | `data/` project stage series (via `flashflood.experiment.build_context`), cross-checked against the `stage_ft` column of the saved predictions |
| GRU 24 h, LSTM, ridge H, damped trend, persistence, XGBoost H | `reports/phase1d/oof_predictions.csv.gz` (Phase 1D, one training seed for GRU and LSTM) |
| GRU 72 h (seed 0), GRU 24 h three-seed range | `reports/phase1e/oof_predictions.csv.gz` (Phase 1E) |
| Fixed-rule event results | `reports/phase1d/tables/D5b_fixed_rule_per_event.csv`; GRU 72 h from `reports/phase1e_onset/tables/O7_fixed_rule_lead_per_event.csv` (two experimental definitions only; the official 25 ft definition is not computed for GRU 72 h and is shown as n/a) |
| Fold boundaries | `reports/phase1d/fold_specification.csv` |

Coverage: 18 events; 4,757 plotted issue times (12 h before the rise onset to 24 h after the event end); a forecast exists for 98.9% of them at every horizon. The 50 issue times without a forecast are 48 in the 2024-07-24 event (45 with the observed stage itself missing, an 11 h gap, plus 3 with a gap in the recent history) and 2 in the 2026-07-15 event (1 stage missing, 1 observed target missing). In the scored flood windows 1,552 of 1,578 issue times are scored; 24 of the 26 unscored ones are in the 2024-07-24 event, whose observed stage is missing for 13.8% of the plotted window. Forecasts exist only inside the out-of-fold test blocks; none of the 18 plotted windows starts before its block.

## Verification
- `tests/test_replay.py` (15 tests): disclaimer text; gaps stay `null` and are never filled; metric helpers on synthetic data; every plotted forecast equals the saved row at the same timestamp (all models, horizons, events); the issue-to-target alignment (15 min = 1 step, 3 h = 12 steps) against the saved target column and the persistence property; observed series and gap runs equal the project series; per-event RMSE, peak forecast and peak ratio reproduce Phase 1D `D4` (tolerance 0.002 ft, the 3-decimal rounding of the saved files); pooled flood-window RMSE reproduces Phase 1E `E1` for all seven models and four horizons; detection statuses equal `D5b`; unavailable-forecast counts add up and the reason codes use the fold boundaries (not row presence); the built HTML embeds the same document, contains the disclaimer, and has no external resources or network calls.
- Browser check during development (headless Chromium 131 through Playwright, installed in a scratch directory, not part of the project): all 288 combinations of 18 events x 4 horizons x 2 time axes x 2 zoom modes rendered with no JavaScript errors and no `NaN`/`undefined` text; screenshots in `screenshots/`. The browser run is not part of the automated test suite.

## Assumptions, limitations, deviations
- A static single-file page was chosen over Streamlit/Plotly because no dashboard library was installed or approved, the data is a fixed set of saved predictions, and the file works offline and can be shared as is. It cannot take new data without a rebuild.
- Metrics are recomputed from the saved 0.001 ft-rounded files, so they can differ from the report tables in the last digit.
- GRU, LSTM and GRU 72 h are single training seeds; seed-to-seed differences can be as large as many of the gaps between models (see `reports/PHASE1E_REPORT.md`). Differences visible for one event are not evidence of a better model.
- One gauge, 18 events from 14 storm clusters, all results retrospective and exploratory; peak ratios say nothing about when a rise was first anticipated (see `reports/PHASE1E_ONSET_TIMING.md`).
- The reason breakdown for missing forecasts uses only the project's own eligibility ingredients; "other" includes the rainfall-input validity rule.
- No warning categories, alerts, live feeds or deployment functionality were implemented (explicitly deferred).

## Screenshots (`screenshots/`)
`01_event_replay_overview.png` (2025-07-05, 3 h), `02_hover_tooltip_target_time.png`, `03_issue_time_view.png` (2015-05-23, 1 h), `04_missing_observations_and_unavailable_forecasts.png` (2024-07-24), `05_all_events_table.png`, `06_dark_mode_mobile.png`.
