# Deviation 3: original versus corrected Phase 1A results

ORIGINAL = first full run (strict rolling windows, events with no eligible rows counted as misses), regenerated bit-for-bit from the preserved code path (`run_phase1a.py --legacy`; every number printed during the first run was reproduced).
CORRECTED = gap-tolerant features plus the not-evaluable rule. The defect was discovered AFTER inspecting test-set output, so the corrected test results are **post-hoc corrected / exploratory**, not an untouched confirmation.

## 1. Eligible rows

| item                                               |   n_original |   n_corrected |   rows_recovered |
|:---------------------------------------------------|-------------:|--------------:|-----------------:|
| 15-min grid rows                                   |       671141 |        671141 |                0 |
| valid stage rows                                   |       651581 |        651581 |                0 |
| rows masked as sensor-floor (stage <= -1.2 ft)     |        16538 |         16538 |                0 |
| rows with complete hydrology features              |       618743 |        642558 |            23815 |
| rows with complete hydrology+rain features         |       617781 |        641452 |            23671 |
| storm clusters (>=5 ft or >=1 ft/3h, <72 h merged) |           78 |            78 |                0 |
| eligible rows h=15m train                          |       341806 |        354730 |            12924 |
| eligible rows h=15m val                            |       135054 |        139331 |             4277 |
| eligible rows h=15m test                           |       140822 |        147089 |             6267 |
| eligible rows h=30m train                          |       341777 |        354684 |            12907 |
| eligible rows h=30m val                            |       135048 |        139315 |             4267 |
| eligible rows h=30m test                           |       140811 |        147033 |             6222 |
| eligible rows h=1h train                           |       341725 |        354604 |            12879 |
| eligible rows h=1h val                             |       135039 |        139300 |             4261 |
| eligible rows h=1h test                            |       140790 |        146949 |             6159 |
| eligible rows h=3h train                           |       341638 |        354465 |            12827 |
| eligible rows h=3h val                             |       135015 |        139249 |             4234 |
| eligible rows h=3h test                            |       140741 |        146540 |             5799 |

## 2. Chronological-test RMSE (ft)

| protocol    | subset                  | horizon   | model       |   n_orig |   rmse_orig |   n_corr |   rmse_corr |
|:------------|:------------------------|:----------|:------------|---------:|------------:|---------:|------------:|
| chrono_test | all                     | 15m       | persistence |   140822 |       0.03  |   147089 |       0.035 |
| chrono_test | all                     | 15m       | trend       |   140822 |       0.02  |   147089 |       0.022 |
| chrono_test | all                     | 15m       | ridge_H     |   140822 |       0.017 |   147089 |       0.018 |
| chrono_test | all                     | 15m       | xgb_H       |   140822 |       0.016 |   147089 |       0.018 |
| chrono_test | event_windows_stage10ft | 15m       | persistence |      278 |       0.567 |      353 |       0.609 |
| chrono_test | event_windows_stage10ft | 15m       | trend       |      278 |       0.361 |      353 |       0.353 |
| chrono_test | event_windows_stage10ft | 15m       | ridge_H     |      278 |       0.292 |      353 |       0.29  |
| chrono_test | event_windows_stage10ft | 15m       | xgb_H       |      278 |       0.301 |      353 |       0.297 |
| chrono_test | all                     | 30m       | persistence |   140811 |       0.057 |   147033 |       0.067 |
| chrono_test | all                     | 30m       | trend       |   140811 |       0.041 |   147033 |       0.043 |
| chrono_test | all                     | 30m       | ridge_H     |   140811 |       0.034 |   147033 |       0.036 |
| chrono_test | all                     | 30m       | xgb_H       |   140811 |       0.035 |   147033 |       0.038 |
| chrono_test | event_windows_stage10ft | 30m       | persistence |      278 |       1.104 |      353 |       1.19  |
| chrono_test | event_windows_stage10ft | 30m       | trend       |      278 |       0.752 |      353 |       0.736 |
| chrono_test | event_windows_stage10ft | 30m       | ridge_H     |      278 |       0.629 |      353 |       0.619 |
| chrono_test | event_windows_stage10ft | 30m       | xgb_H       |      278 |       0.679 |      353 |       0.683 |
| chrono_test | all                     | 1h        | persistence |   140790 |       0.108 |   146949 |       0.127 |
| chrono_test | all                     | 1h        | trend       |   140790 |       0.085 |   146949 |       0.091 |
| chrono_test | all                     | 1h        | ridge_H     |   140790 |       0.072 |   146949 |       0.078 |
| chrono_test | all                     | 1h        | xgb_H       |   140790 |       0.071 |   146949 |       0.078 |
| chrono_test | event_windows_stage10ft | 1h        | persistence |      278 |       2.1   |      353 |       2.286 |
| chrono_test | event_windows_stage10ft | 1h        | trend       |      278 |       1.561 |      353 |       1.565 |
| chrono_test | event_windows_stage10ft | 1h        | ridge_H     |      278 |       1.353 |      353 |       1.357 |
| chrono_test | event_windows_stage10ft | 1h        | xgb_H       |      278 |       1.362 |      353 |       1.38  |
| chrono_test | all                     | 3h        | persistence |   140741 |       0.278 |   146540 |       0.338 |
| chrono_test | all                     | 3h        | trend       |   140741 |       0.282 |   146540 |       0.318 |
| chrono_test | all                     | 3h        | ridge_H     |   140741 |       0.221 |   146540 |       0.258 |
| chrono_test | all                     | 3h        | xgb_H       |   140741 |       0.233 |   146540 |       0.282 |
| chrono_test | event_windows_stage10ft | 3h        | persistence |      278 |       5.532 |      353 |       6.117 |
| chrono_test | event_windows_stage10ft | 3h        | trend       |      278 |       5.337 |      353 |       5.693 |
| chrono_test | event_windows_stage10ft | 3h        | ridge_H     |      278 |       4.386 |      353 |       4.753 |
| chrono_test | event_windows_stage10ft | 3h        | xgb_H       |      278 |       4.741 |      353 |       5.31  |

## 3. Official >=25 ft test events: status originally vs corrected

| protocol    | definition           | event_start      | horizon   | model       | status_orig   |   peak_forecast_ft_orig | status_corr   |   peak_forecast_ft_corr |
|:------------|:---------------------|:-----------------|:----------|:------------|:--------------|------------------------:|:--------------|------------------------:|
| chrono_test | official_action_25ft | 2025-07-05 06:15 | 1h        | persistence | late          |                   29.58 | late          |                   29.58 |
| chrono_test | official_action_25ft | 2026-07-15 23:00 | 1h        | persistence | late          |                   24.26 | late          |                   24.26 |
| chrono_test | official_action_25ft | 2026-07-17 00:30 | 1h        | persistence | miss          |                  nan    | late          |                   36.38 |
| chrono_test | official_action_25ft | 2025-07-05 06:15 | 1h        | trend       | early         |                   30.43 | early         |                   30.43 |
| chrono_test | official_action_25ft | 2026-07-15 23:00 | 1h        | trend       | early         |                   27    | early         |                   27    |
| chrono_test | official_action_25ft | 2026-07-17 00:30 | 1h        | trend       | miss          |                  nan    | early         |                   37.54 |
| chrono_test | official_action_25ft | 2025-07-05 06:15 | 1h        | ridge_H     | early         |                   29.35 | early         |                   29.35 |
| chrono_test | official_action_25ft | 2026-07-15 23:00 | 1h        | ridge_H     | early         |                   25.63 | early         |                   25.63 |
| chrono_test | official_action_25ft | 2026-07-17 00:30 | 1h        | ridge_H     | miss          |                  nan    | early         |                   36.66 |
| chrono_test | official_action_25ft | 2025-07-05 06:15 | 1h        | xgb_H       | early         |                   30.04 | early         |                   30.05 |
| chrono_test | official_action_25ft | 2026-07-15 23:00 | 1h        | xgb_H       | early         |                   25.68 | early         |                   25.76 |
| chrono_test | official_action_25ft | 2026-07-17 00:30 | 1h        | xgb_H       | miss          |                  nan    | early         |                   36.8  |
| chrono_test | official_action_25ft | 2025-07-05 06:15 | 3h        | persistence | late          |                   26.54 | late          |                   26.54 |
| chrono_test | official_action_25ft | 2026-07-15 23:00 | 3h        | persistence | miss          |                   17.73 | miss          |                   17.73 |
| chrono_test | official_action_25ft | 2026-07-17 00:30 | 3h        | persistence | miss          |                  nan    | late          |                   33.25 |
| chrono_test | official_action_25ft | 2025-07-05 06:15 | 3h        | trend       | early         |                   37.58 | early         |                   37.58 |
| chrono_test | official_action_25ft | 2026-07-15 23:00 | 3h        | trend       | early         |                   30    | early         |                   30    |
| chrono_test | official_action_25ft | 2026-07-17 00:30 | 3h        | trend       | miss          |                  nan    | early         |                   43.3  |
| chrono_test | official_action_25ft | 2025-07-05 06:15 | 3h        | ridge_H     | early         |                   27.15 | early         |                   27.14 |
| chrono_test | official_action_25ft | 2026-07-15 23:00 | 3h        | ridge_H     | miss          |                   21.33 | miss          |                   21.31 |
| chrono_test | official_action_25ft | 2026-07-17 00:30 | 3h        | ridge_H     | miss          |                  nan    | early         |                   34.97 |
| chrono_test | official_action_25ft | 2025-07-05 06:15 | 3h        | xgb_H       | early         |                   27.11 | early         |                   26.69 |
| chrono_test | official_action_25ft | 2026-07-15 23:00 | 3h        | xgb_H       | miss          |                   20.91 | miss          |                   19.15 |
| chrono_test | official_action_25ft | 2026-07-17 00:30 | 3h        | xgb_H       | miss          |                  nan    | early         |                   33.74 |

## 4. How many (protocol, definition, event, horizon, model) rows changed status

401 of 2880 rows. By original -> corrected status:

| status_orig   | status_corr   |   n |
|:--------------|:--------------|----:|
| early         | late          |  11 |
| early         | miss          |   7 |
| late          | early         |  18 |
| late          | miss          |   1 |
| miss          | early         | 255 |
| miss          | late          |  49 |
| miss          | not_evaluable |  60 |

## 5. Why events are 'not evaluable' (all protocols; events are flagged only when < 80% of the lead-credit issue times are eligible)

| definition               | event_start               | horizon   |   eligible_frac |   issue_times |   stage_missing_or_floor |   target_missing |   hydro_feature_missing |   rain_missing |   longest_stage_gap_h_in_prior_24h |
|:-------------------------|:--------------------------|:----------|----------------:|--------------:|-------------------------:|-----------------:|------------------------:|---------------:|-----------------------------------:|
| experimental_rise_4ft_3h | 2024-06-02 07:15:00+00:00 | 15m       |            0    |             6 |                        0 |                0 |                       6 |              0 |                                 21 |
| experimental_rise_4ft_3h | 2024-06-02 07:15:00+00:00 | 30m       |            0    |             7 |                        0 |                0 |                       7 |              0 |                                 21 |
| experimental_rise_4ft_3h | 2024-06-02 07:15:00+00:00 | 1h        |            0    |             9 |                        0 |                0 |                       9 |              0 |                                 21 |
| experimental_rise_4ft_3h | 2024-06-02 07:15:00+00:00 | 3h        |            0    |            17 |                        4 |                4 |                      17 |              0 |                                 21 |
| experimental_rise_4ft_3h | 2024-07-24 14:00:00+00:00 | 3h        |            0.76 |            17 |                        0 |                0 |                       4 |              0 |                                  0 |
