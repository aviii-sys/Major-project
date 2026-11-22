# Phase 1A result tables (generated)

### Stage forecast error, chronological TEST, all rows

Rows scored: {'15m': 147089, '30m': 147033, '1h': 146949, '3h': 146540}. Brackets are 95% storm-cluster bootstrap intervals where computed.

| model       | RMSE ft 15m        | RMSE ft 30m        | RMSE ft 1h         | RMSE ft 3h         |
|:------------|:-------------------|:-------------------|:-------------------|:-------------------|
| persistence | 0.035 [0.01, 0.05] | 0.067 [0.03, 0.10] | 0.127 [0.06, 0.19] | 0.338 [0.15, 0.50] |
| trend       | 0.022 [0.01, 0.03] | 0.043 [0.03, 0.06] | 0.091 [0.06, 0.12] | 0.318 [0.19, 0.44] |
| ridge_H     | 0.018 [0.01, 0.03] | 0.036 [0.02, 0.05] | 0.078 [0.05, 0.11] | 0.258 [0.13, 0.38] |
| ridge_HR    | 0.018 [0.01, 0.03] | 0.036 [0.02, 0.05] | 0.078 [0.05, 0.11] | 0.256 [0.13, 0.38] |
| xgb_H       | 0.018 [0.01, 0.03] | 0.038 [0.02, 0.06] | 0.078 [0.05, 0.11] | 0.282 [0.13, 0.42] |
| xgb_HR      | 0.018 [0.01, 0.03] | 0.037 [0.02, 0.05] | 0.081 [0.05, 0.11] | 0.296 [0.14, 0.44] |

Skill versus persistence (1 - MSE/MSE_persistence; 0 = no better than persistence):

| model    | skill 15m         | skill 30m         | skill 1h           | skill 3h           |
|:---------|:------------------|:------------------|:-------------------|:-------------------|
| trend    | 0.61 [0.31, 0.76] | 0.58 [0.17, 0.76] | 0.49 [-0.02, 0.70] | 0.11 [-0.65, 0.35] |
| ridge_H  | 0.72 [0.50, 0.79] | 0.70 [0.38, 0.81] | 0.63 [0.19, 0.76]  | 0.42 [0.03, 0.59]  |
| ridge_HR | 0.72 [0.50, 0.79] | 0.70 [0.38, 0.81] | 0.63 [0.20, 0.77]  | 0.42 [0.04, 0.59]  |
| xgb_H    | 0.73 [0.62, 0.80] | 0.67 [0.45, 0.77] | 0.62 [0.24, 0.75]  | 0.30 [0.07, 0.41]  |
| xgb_HR   | 0.73 [0.62, 0.80] | 0.69 [0.44, 0.78] | 0.59 [0.23, 0.71]  | 0.24 [0.05, 0.31]  |

### Stage forecast error, chronological TEST, event windows of the experimental >=10 ft events

Rows scored: {'15m': 353, '30m': 353, '1h': 353, '3h': 353}. Brackets are 95% storm-cluster bootstrap intervals where computed.

| model       | RMSE ft 15m        | RMSE ft 30m        | RMSE ft 1h         | RMSE ft 3h         |
|:------------|:-------------------|:-------------------|:-------------------|:-------------------|
| persistence | 0.609 [0.31, 0.95] | 1.190 [0.75, 1.75] | 2.286 [1.65, 3.10] | 6.117 [4.31, 7.82] |
| trend       | 0.353 [0.19, 0.68] | 0.736 [0.42, 1.32] | 1.565 [0.97, 2.58] | 5.693 [4.22, 8.37] |
| ridge_H     | 0.290 [0.17, 0.54] | 0.619 [0.36, 1.05] | 1.357 [0.87, 2.23] | 4.753 [3.08, 7.25] |
| ridge_HR    | 0.290 [0.17, 0.54] | 0.618 [0.36, 1.05] | 1.354 [0.87, 2.22] | 4.724 [3.05, 7.17] |
| xgb_H       | 0.297 [0.15, 0.56] | 0.683 [0.42, 1.12] | 1.380 [0.90, 2.23] | 5.310 [3.59, 7.40] |
| xgb_HR      | 0.298 [0.16, 0.55] | 0.651 [0.40, 1.07] | 1.454 [0.98, 2.27] | 5.499 [3.79, 7.53] |

Skill versus persistence (1 - MSE/MSE_persistence; 0 = no better than persistence):

| model    | skill 15m         | skill 30m         | skill 1h          | skill 3h           |
|:---------|:------------------|:------------------|:------------------|:-------------------|
| trend    | 0.66 [0.45, 0.85] | 0.62 [0.26, 0.82] | 0.53 [0.11, 0.74] | 0.13 [-0.37, 0.36] |
| ridge_H  | 0.77 [0.62, 0.88] | 0.73 [0.35, 0.86] | 0.65 [0.18, 0.80] | 0.40 [0.06, 0.61]  |
| ridge_HR | 0.77 [0.62, 0.88] | 0.73 [0.36, 0.86] | 0.65 [0.19, 0.80] | 0.40 [0.08, 0.61]  |
| xgb_H    | 0.76 [0.64, 0.87] | 0.67 [0.38, 0.80] | 0.64 [0.18, 0.78] | 0.25 [0.05, 0.35]  |
| xgb_HR   | 0.76 [0.64, 0.86] | 0.70 [0.37, 0.82] | 0.60 [0.19, 0.72] | 0.19 [0.04, 0.27]  |

### Stage forecast error, chronological TEST, event windows of the experimental >=4 ft/3 h rapid rises

Rows scored: {'15m': 331, '30m': 331, '1h': 331, '3h': 331}. Brackets are 95% storm-cluster bootstrap intervals where computed.

| model       | RMSE ft 15m        | RMSE ft 30m        | RMSE ft 1h         | RMSE ft 3h         |
|:------------|:-------------------|:-------------------|:-------------------|:-------------------|
| persistence | 0.643 [0.38, 0.95] | 1.259 [0.84, 1.79] | 2.413 [1.70, 3.19] | 6.386 [4.16, 7.97] |
| trend       | 0.384 [0.21, 0.68] | 0.809 [0.49, 1.36] | 1.729 [1.15, 2.71] | 6.164 [4.76, 8.77] |
| ridge_H     | 0.308 [0.19, 0.54] | 0.667 [0.42, 1.08] | 1.473 [1.00, 2.32] | 5.046 [3.50, 7.21] |
| ridge_HR    | 0.308 [0.19, 0.54] | 0.666 [0.42, 1.08] | 1.469 [1.00, 2.31] | 5.015 [3.45, 7.14] |
| xgb_H       | 0.310 [0.18, 0.55] | 0.723 [0.46, 1.15] | 1.478 [1.01, 2.31] | 5.564 [3.67, 7.44] |
| xgb_HR      | 0.311 [0.18, 0.55] | 0.692 [0.45, 1.10] | 1.558 [1.11, 2.33] | 5.761 [3.73, 7.63] |

Skill versus persistence (1 - MSE/MSE_persistence; 0 = no better than persistence):

| model    | skill 15m         | skill 30m         | skill 1h           | skill 3h           |
|:---------|:------------------|:------------------|:-------------------|:-------------------|
| trend    | 0.64 [0.37, 0.84] | 0.59 [0.17, 0.80] | 0.49 [-0.02, 0.72] | 0.07 [-0.79, 0.33] |
| ridge_H  | 0.77 [0.61, 0.88] | 0.72 [0.39, 0.85] | 0.63 [0.18, 0.79]  | 0.38 [0.02, 0.55]  |
| ridge_HR | 0.77 [0.61, 0.88] | 0.72 [0.40, 0.85] | 0.63 [0.19, 0.79]  | 0.38 [0.04, 0.56]  |
| xgb_H    | 0.77 [0.65, 0.87] | 0.67 [0.44, 0.79] | 0.63 [0.22, 0.77]  | 0.24 [0.04, 0.34]  |
| xgb_HR   | 0.77 [0.66, 0.87] | 0.70 [0.44, 0.81] | 0.58 [0.21, 0.71]  | 0.19 [0.03, 0.26]  |

### Stage forecast error, blocked CV (NON-CAUSAL), event windows of >=10 ft events

Rows scored: {'15m': 1609, '30m': 1609, '1h': 1609, '3h': 1609}. Brackets are 95% storm-cluster bootstrap intervals where computed.

| model       | RMSE ft 15m        | RMSE ft 30m        | RMSE ft 1h         | RMSE ft 3h         |
|:------------|:-------------------|:-------------------|:-------------------|:-------------------|
| persistence | 0.480 [0.36, 0.64] | 0.927 [0.71, 1.21] | 1.784 [1.37, 2.29] | 4.719 [3.67, 5.89] |
| trend       | 0.285 [0.20, 0.40] | 0.576 [0.43, 0.79] | 1.273 [0.98, 1.71] | 5.007 [3.91, 6.60] |
| ridge_H     | 0.249 [0.18, 0.36] | 0.491 [0.37, 0.68] | 1.093 [0.83, 1.48] | 3.903 [3.04, 5.03] |
| ridge_HR    | 0.249 [0.18, 0.36] | 0.491 [0.37, 0.68] | 1.092 [0.83, 1.48] | 3.886 [3.02, 5.00] |
| xgb_H       | 0.261 [0.19, 0.38] | 0.532 [0.40, 0.73] | 1.130 [0.85, 1.54] | 4.113 [3.18, 5.25] |
| xgb_HR      | 0.282 [0.19, 0.40] | 0.564 [0.42, 0.78] | 1.275 [0.98, 1.68] | 4.327 [3.38, 5.43] |

Skill versus persistence (1 - MSE/MSE_persistence; 0 = no better than persistence):

| model    | skill 15m         | skill 30m         | skill 1h          | skill 3h            |
|:---------|:------------------|:------------------|:------------------|:--------------------|
| trend    | 0.65 [0.53, 0.75] | 0.61 [0.47, 0.72] | 0.49 [0.31, 0.61] | -0.13 [-0.49, 0.12] |
| ridge_H  | 0.73 [0.64, 0.81] | 0.72 [0.61, 0.79] | 0.62 [0.48, 0.72] | 0.32 [0.17, 0.41]   |
| ridge_HR | 0.73 [0.64, 0.81] | 0.72 [0.62, 0.79] | 0.63 [0.48, 0.72] | 0.32 [0.18, 0.41]   |
| xgb_H    | 0.70 [0.60, 0.79] | 0.67 [0.57, 0.74] | 0.60 [0.45, 0.69] | 0.24 [0.13, 0.31]   |
| xgb_HR   | 0.66 [0.49, 0.77] | 0.63 [0.49, 0.72] | 0.49 [0.34, 0.59] | 0.16 [0.09, 0.21]   |

### Event detection, chronological TEST (2022-01-01 onward; 2026 data provisional)

| definition               | h   | model       | early hits / events [95% CI]   |   late |   missed | false alarms / episodes   |   false alarms per yr |   median lead h |   not evaluable |
|:-------------------------|:----|:------------|:-------------------------------|-------:|---------:|:--------------------------|----------------------:|----------------:|----------------:|
| official_action_25ft     | 15m | persistence | 0/3 [0.00, 0.71]               |      3 |        0 | 0/3                       |                  0    |                 |               0 |
| official_action_25ft     | 15m | trend       | 2/3 [0.09, 0.99]               |      1 |        0 | 0/3                       |                  0    |            0.38 |               0 |
| official_action_25ft     | 15m | ridge_H     | 0/3 [0.00, 0.71]               |      3 |        0 | 0/3                       |                  0    |                 |               0 |
| official_action_25ft     | 15m | xgb_H       | 1/3 [0.01, 0.91]               |      2 |        0 | 0/3                       |                  0    |            0.25 |               0 |
| official_action_25ft     | 15m | xgb_HR      | 1/3 [0.01, 0.91]               |      2 |        0 | 0/3                       |                  0    |            0.25 |               0 |
| official_action_25ft     | 30m | persistence | 0/3 [0.00, 0.71]               |      3 |        0 | 0/3                       |                  0    |                 |               0 |
| official_action_25ft     | 30m | trend       | 3/3 [0.29, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.5  |               0 |
| official_action_25ft     | 30m | ridge_H     | 3/3 [0.29, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.25 |               0 |
| official_action_25ft     | 30m | xgb_H       | 3/3 [0.29, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.25 |               0 |
| official_action_25ft     | 30m | xgb_HR      | 3/3 [0.29, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.25 |               0 |
| official_action_25ft     | 1h  | persistence | 0/3 [0.00, 0.71]               |      3 |        0 | 0/3                       |                  0    |                 |               0 |
| official_action_25ft     | 1h  | trend       | 3/3 [0.29, 1.00]               |      0 |        0 | 0/3                       |                  0    |            1.75 |               0 |
| official_action_25ft     | 1h  | ridge_H     | 3/3 [0.29, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.5  |               0 |
| official_action_25ft     | 1h  | xgb_H       | 3/3 [0.29, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.5  |               0 |
| official_action_25ft     | 1h  | xgb_HR      | 3/3 [0.29, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.5  |               0 |
| official_action_25ft     | 3h  | persistence | 0/3 [0.00, 0.71]               |      2 |        1 | 1/3                       |                  0.2  |                 |               0 |
| official_action_25ft     | 3h  | trend       | 3/3 [0.29, 1.00]               |      0 |        0 | 0/3                       |                  0    |            2.5  |               0 |
| official_action_25ft     | 3h  | ridge_H     | 2/3 [0.09, 0.99]               |      0 |        1 | 1/4                       |                  0.2  |            1.88 |               0 |
| official_action_25ft     | 3h  | xgb_H       | 2/3 [0.09, 0.99]               |      0 |        1 | 1/3                       |                  0.2  |            0.38 |               0 |
| official_action_25ft     | 3h  | xgb_HR      | 2/3 [0.09, 0.99]               |      0 |        1 | 1/3                       |                  0.2  |            0.25 |               0 |
| official_minor_30ft      | 15m | persistence | 0/2 [0.00, 0.84]               |      2 |        0 | 0/2                       |                  0    |                 |               0 |
| official_minor_30ft      | 15m | trend       | 2/2 [0.16, 1.00]               |      0 |        0 | 0/2                       |                  0    |            0.5  |               0 |
| official_minor_30ft      | 15m | ridge_H     | 2/2 [0.16, 1.00]               |      0 |        0 | 0/2                       |                  0    |            0.38 |               0 |
| official_minor_30ft      | 15m | xgb_H       | 2/2 [0.16, 1.00]               |      0 |        0 | 0/2                       |                  0    |            0.38 |               0 |
| official_minor_30ft      | 15m | xgb_HR      | 2/2 [0.16, 1.00]               |      0 |        0 | 0/2                       |                  0    |            0.38 |               0 |
| official_minor_30ft      | 30m | persistence | 0/2 [0.00, 0.84]               |      2 |        0 | 0/2                       |                  0    |                 |               0 |
| official_minor_30ft      | 30m | trend       | 2/2 [0.16, 1.00]               |      0 |        0 | 0/2                       |                  0    |            1.12 |               0 |
| official_minor_30ft      | 30m | ridge_H     | 2/2 [0.16, 1.00]               |      0 |        0 | 0/2                       |                  0    |            0.5  |               0 |
| official_minor_30ft      | 30m | xgb_H       | 2/2 [0.16, 1.00]               |      0 |        0 | 0/2                       |                  0    |            0.38 |               0 |
| official_minor_30ft      | 30m | xgb_HR      | 2/2 [0.16, 1.00]               |      0 |        0 | 0/2                       |                  0    |            0.38 |               0 |
| official_minor_30ft      | 1h  | persistence | 0/2 [0.00, 0.84]               |      2 |        0 | 0/2                       |                  0    |                 |               0 |
| official_minor_30ft      | 1h  | trend       | 2/2 [0.16, 1.00]               |      0 |        0 | 0/2                       |                  0    |            2.12 |               0 |
| official_minor_30ft      | 1h  | ridge_H     | 2/2 [0.16, 1.00]               |      0 |        0 | 0/2                       |                  0    |            0.75 |               0 |
| official_minor_30ft      | 1h  | xgb_H       | 2/2 [0.16, 1.00]               |      0 |        0 | 0/2                       |                  0    |            1.12 |               0 |
| official_minor_30ft      | 1h  | xgb_HR      | 2/2 [0.16, 1.00]               |      0 |        0 | 0/2                       |                  0    |            1.12 |               0 |
| official_minor_30ft      | 3h  | persistence | 0/2 [0.00, 0.84]               |      1 |        1 | 1/2                       |                  0.2  |                 |               0 |
| official_minor_30ft      | 3h  | trend       | 2/2 [0.16, 1.00]               |      0 |        0 | 1/3                       |                  0.2  |            4.38 |               0 |
| official_minor_30ft      | 3h  | ridge_H     | 1/2 [0.01, 0.99]               |      0 |        1 | 1/2                       |                  0.2  |            1.5  |               0 |
| official_minor_30ft      | 3h  | xgb_H       | 1/2 [0.01, 0.99]               |      0 |        1 | 1/2                       |                  0.2  |            0.75 |               0 |
| official_minor_30ft      | 3h  | xgb_HR      | 1/2 [0.01, 0.99]               |      0 |        1 | 1/2                       |                  0.2  |            0.5  |               0 |
| official_moderate_36ft   | 15m | persistence | 0/1 [0.00, 0.97]               |      1 |        0 | 0/1                       |                  0    |                 |               0 |
| official_moderate_36ft   | 15m | trend       | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 15m | ridge_H     | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 15m | xgb_H       | 0/1 [0.00, 0.97]               |      1 |        0 | 0/1                       |                  0    |                 |               0 |
| official_moderate_36ft   | 15m | xgb_HR      | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 30m | persistence | 0/1 [0.00, 0.97]               |      1 |        0 | 0/1                       |                  0    |                 |               0 |
| official_moderate_36ft   | 30m | trend       | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            1    |               0 |
| official_moderate_36ft   | 30m | ridge_H     | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 30m | xgb_H       | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 30m | xgb_HR      | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 1h  | persistence | 0/1 [0.00, 0.97]               |      1 |        0 | 0/1                       |                  0    |                 |               0 |
| official_moderate_36ft   | 1h  | trend       | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            2    |               0 |
| official_moderate_36ft   | 1h  | ridge_H     | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 1h  | xgb_H       | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            1    |               0 |
| official_moderate_36ft   | 1h  | xgb_HR      | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 3h  | persistence | 0/1 [0.00, 0.97]               |      0 |        1 | 1/1                       |                  0.2  |                 |               0 |
| official_moderate_36ft   | 3h  | trend       | 1/1 [0.03, 1.00]               |      0 |        0 | 1/2                       |                  0.2  |            4.75 |               0 |
| official_moderate_36ft   | 3h  | ridge_H     | 0/1 [0.00, 0.97]               |      0 |        1 | 1/1                       |                  0.2  |                 |               0 |
| official_moderate_36ft   | 3h  | xgb_H       | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            1    |               0 |
| official_moderate_36ft   | 3h  | xgb_HR      | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            1    |               0 |
| experimental_stage_10ft  | 15m | persistence | 0/4 [0.00, 0.60]               |      4 |        0 | 0/5                       |                  0    |                 |               0 |
| experimental_stage_10ft  | 15m | trend       | 3/4 [0.19, 0.99]               |      1 |        0 | 0/5                       |                  0    |            0.25 |               0 |
| experimental_stage_10ft  | 15m | ridge_H     | 3/4 [0.19, 0.99]               |      1 |        0 | 0/5                       |                  0    |            0.25 |               0 |
| experimental_stage_10ft  | 15m | xgb_H       | 3/4 [0.19, 0.99]               |      1 |        0 | 0/5                       |                  0    |            0.25 |               0 |
| experimental_stage_10ft  | 15m | xgb_HR      | 3/4 [0.19, 0.99]               |      1 |        0 | 0/5                       |                  0    |            0.25 |               0 |
| experimental_stage_10ft  | 30m | persistence | 0/4 [0.00, 0.60]               |      4 |        0 | 0/5                       |                  0    |                 |               0 |
| experimental_stage_10ft  | 30m | trend       | 3/4 [0.19, 0.99]               |      1 |        0 | 0/5                       |                  0    |            0.75 |               0 |
| experimental_stage_10ft  | 30m | ridge_H     | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.38 |               0 |
| experimental_stage_10ft  | 30m | xgb_H       | 3/4 [0.19, 0.99]               |      1 |        0 | 0/5                       |                  0    |            0.5  |               0 |
| experimental_stage_10ft  | 30m | xgb_HR      | 3/4 [0.19, 0.99]               |      1 |        0 | 0/5                       |                  0    |            0.5  |               0 |
| experimental_stage_10ft  | 1h  | persistence | 0/4 [0.00, 0.60]               |      4 |        0 | 0/5                       |                  0    |                 |               0 |
| experimental_stage_10ft  | 1h  | trend       | 4/4 [0.40, 1.00]               |      0 |        0 | 2/7                       |                  0.41 |            0.75 |               0 |
| experimental_stage_10ft  | 1h  | ridge_H     | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.75 |               0 |
| experimental_stage_10ft  | 1h  | xgb_H       | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.62 |               0 |
| experimental_stage_10ft  | 1h  | xgb_HR      | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.62 |               0 |
| experimental_stage_10ft  | 3h  | persistence | 0/4 [0.00, 0.60]               |      4 |        0 | 0/5                       |                  0    |                 |               0 |
| experimental_stage_10ft  | 3h  | trend       | 4/4 [0.40, 1.00]               |      0 |        0 | 5/10                      |                  1.02 |            1.38 |               0 |
| experimental_stage_10ft  | 3h  | ridge_H     | 4/4 [0.40, 1.00]               |      0 |        0 | 2/7                       |                  0.41 |            1.12 |               0 |
| experimental_stage_10ft  | 3h  | xgb_H       | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.75 |               0 |
| experimental_stage_10ft  | 3h  | xgb_HR      | 3/4 [0.19, 0.99]               |      1 |        0 | 0/5                       |                  0    |            0.75 |               0 |
| experimental_stage_15ft  | 15m | persistence | 0/2 [0.00, 0.84]               |      2 |        0 | 0/3                       |                  0    |                 |               0 |
| experimental_stage_15ft  | 15m | trend       | 2/2 [0.16, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.25 |               0 |
| experimental_stage_15ft  | 15m | ridge_H     | 2/2 [0.16, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.25 |               0 |
| experimental_stage_15ft  | 15m | xgb_H       | 2/2 [0.16, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.25 |               0 |
| experimental_stage_15ft  | 15m | xgb_HR      | 2/2 [0.16, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.25 |               0 |
| experimental_stage_15ft  | 30m | persistence | 0/2 [0.00, 0.84]               |      2 |        0 | 0/3                       |                  0    |                 |               0 |
| experimental_stage_15ft  | 30m | trend       | 2/2 [0.16, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.5  |               0 |
| experimental_stage_15ft  | 30m | ridge_H     | 2/2 [0.16, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.5  |               0 |
| experimental_stage_15ft  | 30m | xgb_H       | 2/2 [0.16, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.38 |               0 |
| experimental_stage_15ft  | 30m | xgb_HR      | 2/2 [0.16, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.38 |               0 |
| experimental_stage_15ft  | 1h  | persistence | 0/2 [0.00, 0.84]               |      2 |        0 | 0/3                       |                  0    |                 |               0 |
| experimental_stage_15ft  | 1h  | trend       | 2/2 [0.16, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.75 |               0 |
| experimental_stage_15ft  | 1h  | ridge_H     | 2/2 [0.16, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.75 |               0 |
| experimental_stage_15ft  | 1h  | xgb_H       | 2/2 [0.16, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.62 |               0 |
| experimental_stage_15ft  | 1h  | xgb_HR      | 2/2 [0.16, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.62 |               0 |
| experimental_stage_15ft  | 3h  | persistence | 0/2 [0.00, 0.84]               |      2 |        0 | 0/3                       |                  0    |                 |               0 |
| experimental_stage_15ft  | 3h  | trend       | 2/2 [0.16, 1.00]               |      0 |        0 | 4/7                       |                  0.82 |            1.25 |               0 |
| experimental_stage_15ft  | 3h  | ridge_H     | 2/2 [0.16, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.88 |               0 |
| experimental_stage_15ft  | 3h  | xgb_H       | 2/2 [0.16, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.75 |               0 |
| experimental_stage_15ft  | 3h  | xgb_HR      | 2/2 [0.16, 1.00]               |      0 |        0 | 0/3                       |                  0    |            0.38 |               0 |
| experimental_rise_4ft_3h | 15m | persistence | 0/6 [0.00, 0.46]               |      6 |        0 | 0/7                       |                  0    |                 |               1 |
| experimental_rise_4ft_3h | 15m | trend       | 5/6 [0.36, 1.00]               |      1 |        0 | 0/7                       |                  0    |            0.25 |               1 |
| experimental_rise_4ft_3h | 15m | ridge_H     | 5/6 [0.36, 1.00]               |      1 |        0 | 0/7                       |                  0    |            0.25 |               1 |
| experimental_rise_4ft_3h | 15m | xgb_H       | 5/6 [0.36, 1.00]               |      1 |        0 | 0/7                       |                  0    |            0.25 |               1 |
| experimental_rise_4ft_3h | 15m | xgb_HR      | 5/6 [0.36, 1.00]               |      1 |        0 | 0/7                       |                  0    |            0.25 |               1 |
| experimental_rise_4ft_3h | 30m | persistence | 1/6 [0.00, 0.64]               |      5 |        0 | 0/7                       |                  0    |            0.25 |               1 |
| experimental_rise_4ft_3h | 30m | trend       | 5/6 [0.36, 1.00]               |      1 |        0 | 1/8                       |                  0.2  |            0.5  |               1 |
| experimental_rise_4ft_3h | 30m | ridge_H     | 5/6 [0.36, 1.00]               |      1 |        0 | 1/8                       |                  0.2  |            0.5  |               1 |
| experimental_rise_4ft_3h | 30m | xgb_H       | 5/6 [0.36, 1.00]               |      1 |        0 | 0/7                       |                  0    |            0.5  |               1 |
| experimental_rise_4ft_3h | 30m | xgb_HR      | 5/6 [0.36, 1.00]               |      1 |        0 | 0/7                       |                  0    |            0.5  |               1 |
| experimental_rise_4ft_3h | 1h  | persistence | 1/6 [0.00, 0.64]               |      5 |        0 | 0/7                       |                  0    |            0.25 |               1 |
| experimental_rise_4ft_3h | 1h  | trend       | 5/6 [0.36, 1.00]               |      1 |        0 | 1/8                       |                  0.2  |            0.5  |               1 |
| experimental_rise_4ft_3h | 1h  | ridge_H     | 5/6 [0.36, 1.00]               |      1 |        0 | 1/8                       |                  0.2  |            0.75 |               1 |
| experimental_rise_4ft_3h | 1h  | xgb_H       | 5/6 [0.36, 1.00]               |      1 |        0 | 1/8                       |                  0.2  |            0.75 |               1 |
| experimental_rise_4ft_3h | 1h  | xgb_HR      | 6/6 [0.54, 1.00]               |      0 |        0 | 1/8                       |                  0.2  |            0.75 |               1 |
| experimental_rise_4ft_3h | 3h  | persistence | 0/5 [0.00, 0.52]               |      0 |        5 | 0/0                       |                  0    |                 |               2 |
| experimental_rise_4ft_3h | 3h  | trend       | 2/5 [0.05, 0.85]               |      1 |        2 | 10/14                     |                  2.05 |            0.88 |               2 |
| experimental_rise_4ft_3h | 3h  | ridge_H     | 2/5 [0.05, 0.85]               |      1 |        2 | 3/7                       |                  0.61 |            0.5  |               2 |
| experimental_rise_4ft_3h | 3h  | xgb_H       | 0/5 [0.00, 0.52]               |      2 |        3 | 1/3                       |                  0.2  |                 |               2 |
| experimental_rise_4ft_3h | 3h  | xgb_HR      | 0/5 [0.00, 0.52]               |      0 |        5 | 0/0                       |                  0    |                 |               2 |
| experimental_rise_8ft_3h | 15m | persistence | 1/5 [0.01, 0.72]               |      4 |        0 | 0/5                       |                  0    |            0.25 |               0 |
| experimental_rise_8ft_3h | 15m | trend       | 4/5 [0.28, 0.99]               |      1 |        0 | 0/5                       |                  0    |            0.25 |               0 |
| experimental_rise_8ft_3h | 15m | ridge_H     | 3/5 [0.15, 0.95]               |      2 |        0 | 0/5                       |                  0    |            0.25 |               0 |
| experimental_rise_8ft_3h | 15m | xgb_H       | 4/5 [0.28, 0.99]               |      1 |        0 | 0/5                       |                  0    |            0.25 |               0 |
| experimental_rise_8ft_3h | 15m | xgb_HR      | 4/5 [0.28, 0.99]               |      1 |        0 | 0/5                       |                  0    |            0.25 |               0 |
| experimental_rise_8ft_3h | 30m | persistence | 0/5 [0.00, 0.52]               |      3 |        2 | 0/3                       |                  0    |                 |               0 |
| experimental_rise_8ft_3h | 30m | trend       | 5/5 [0.48, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.5  |               0 |
| experimental_rise_8ft_3h | 30m | ridge_H     | 5/5 [0.48, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.25 |               0 |
| experimental_rise_8ft_3h | 30m | xgb_H       | 5/5 [0.48, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.25 |               0 |
| experimental_rise_8ft_3h | 30m | xgb_HR      | 5/5 [0.48, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.25 |               0 |
| experimental_rise_8ft_3h | 1h  | persistence | 0/5 [0.00, 0.52]               |      3 |        2 | 0/3                       |                  0    |                 |               0 |
| experimental_rise_8ft_3h | 1h  | trend       | 5/5 [0.48, 1.00]               |      0 |        0 | 1/6                       |                  0.2  |            0.75 |               0 |
| experimental_rise_8ft_3h | 1h  | ridge_H     | 5/5 [0.48, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.5  |               0 |
| experimental_rise_8ft_3h | 1h  | xgb_H       | 5/5 [0.48, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.5  |               0 |
| experimental_rise_8ft_3h | 1h  | xgb_HR      | 5/5 [0.48, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.5  |               0 |
| experimental_rise_8ft_3h | 3h  | persistence | 0/5 [0.00, 0.52]               |      0 |        5 | 0/0                       |                  0    |                 |               0 |
| experimental_rise_8ft_3h | 3h  | trend       | 5/5 [0.48, 1.00]               |      0 |        0 | 3/8                       |                  0.61 |            1    |               0 |
| experimental_rise_8ft_3h | 3h  | ridge_H     | 1/5 [0.01, 0.72]               |      0 |        4 | 0/1                       |                  0    |            0.25 |               0 |
| experimental_rise_8ft_3h | 3h  | xgb_H       | 0/5 [0.00, 0.52]               |      0 |        5 | 0/0                       |                  0    |                 |               0 |
| experimental_rise_8ft_3h | 3h  | xgb_HR      | 0/5 [0.00, 0.52]               |      0 |        5 | 0/0                       |                  0    |                 |               0 |

### Event detection, blocked CV, whole record (NON-CAUSAL: trained on future blocks)

| definition               | h   | model       | early hits / events [95% CI]   |   late |   missed | false alarms / episodes   |   false alarms per yr |   median lead h |   not evaluable |
|:-------------------------|:----|:------------|:-------------------------------|-------:|---------:|:--------------------------|----------------------:|----------------:|----------------:|
| official_action_25ft     | 15m | persistence | 0/6 [0.00, 0.46]               |      6 |        0 | 0/6                       |                  0    |                 |               0 |
| official_action_25ft     | 15m | trend       | 4/6 [0.22, 0.96]               |      2 |        0 | 0/6                       |                  0    |            0.25 |               0 |
| official_action_25ft     | 15m | ridge_H     | 2/6 [0.04, 0.78]               |      4 |        0 | 0/6                       |                  0    |            0.25 |               0 |
| official_action_25ft     | 15m | xgb_H       | 3/6 [0.12, 0.88]               |      3 |        0 | 0/6                       |                  0    |            0.25 |               0 |
| official_action_25ft     | 15m | xgb_HR      | 2/6 [0.04, 0.78]               |      4 |        0 | 0/6                       |                  0    |            0.25 |               0 |
| official_action_25ft     | 30m | persistence | 0/6 [0.00, 0.46]               |      6 |        0 | 0/6                       |                  0    |                 |               0 |
| official_action_25ft     | 30m | trend       | 6/6 [0.54, 1.00]               |      0 |        0 | 0/6                       |                  0    |            0.5  |               0 |
| official_action_25ft     | 30m | ridge_H     | 5/6 [0.36, 1.00]               |      1 |        0 | 0/6                       |                  0    |            0.5  |               0 |
| official_action_25ft     | 30m | xgb_H       | 5/6 [0.36, 1.00]               |      1 |        0 | 1/7                       |                  0.05 |            0.25 |               0 |
| official_action_25ft     | 30m | xgb_HR      | 5/6 [0.36, 1.00]               |      1 |        0 | 0/6                       |                  0    |            0.25 |               0 |
| official_action_25ft     | 1h  | persistence | 0/6 [0.00, 0.46]               |      6 |        0 | 0/6                       |                  0    |                 |               0 |
| official_action_25ft     | 1h  | trend       | 6/6 [0.54, 1.00]               |      0 |        0 | 0/6                       |                  0    |            1.25 |               0 |
| official_action_25ft     | 1h  | ridge_H     | 6/6 [0.54, 1.00]               |      0 |        0 | 0/6                       |                  0    |            0.62 |               0 |
| official_action_25ft     | 1h  | xgb_H       | 6/6 [0.54, 1.00]               |      0 |        0 | 1/7                       |                  0.05 |            0.62 |               0 |
| official_action_25ft     | 1h  | xgb_HR      | 5/6 [0.36, 1.00]               |      1 |        0 | 1/7                       |                  0.05 |            0.5  |               0 |
| official_action_25ft     | 3h  | persistence | 0/6 [0.00, 0.46]               |      5 |        1 | 1/6                       |                  0.05 |                 |               0 |
| official_action_25ft     | 3h  | trend       | 6/6 [0.54, 1.00]               |      0 |        0 | 5/11                      |                  0.26 |            2.12 |               0 |
| official_action_25ft     | 3h  | ridge_H     | 5/6 [0.36, 1.00]               |      0 |        1 | 1/7                       |                  0.05 |            1.25 |               0 |
| official_action_25ft     | 3h  | xgb_H       | 5/6 [0.36, 1.00]               |      0 |        1 | 3/8                       |                  0.16 |            0.5  |               0 |
| official_action_25ft     | 3h  | xgb_HR      | 4/6 [0.22, 0.96]               |      1 |        1 | 2/7                       |                  0.1  |            0.5  |               0 |
| official_minor_30ft      | 15m | persistence | 0/4 [0.00, 0.60]               |      4 |        0 | 0/5                       |                  0    |                 |               0 |
| official_minor_30ft      | 15m | trend       | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.5  |               0 |
| official_minor_30ft      | 15m | ridge_H     | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.25 |               0 |
| official_minor_30ft      | 15m | xgb_H       | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.25 |               0 |
| official_minor_30ft      | 15m | xgb_HR      | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.25 |               0 |
| official_minor_30ft      | 30m | persistence | 0/4 [0.00, 0.60]               |      4 |        0 | 0/5                       |                  0    |                 |               0 |
| official_minor_30ft      | 30m | trend       | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.75 |               0 |
| official_minor_30ft      | 30m | ridge_H     | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.5  |               0 |
| official_minor_30ft      | 30m | xgb_H       | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.38 |               0 |
| official_minor_30ft      | 30m | xgb_HR      | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.38 |               0 |
| official_minor_30ft      | 1h  | persistence | 0/4 [0.00, 0.60]               |      4 |        0 | 0/5                       |                  0    |                 |               0 |
| official_minor_30ft      | 1h  | trend       | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            1.25 |               0 |
| official_minor_30ft      | 1h  | ridge_H     | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.88 |               0 |
| official_minor_30ft      | 1h  | xgb_H       | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.88 |               0 |
| official_minor_30ft      | 1h  | xgb_HR      | 4/4 [0.40, 1.00]               |      0 |        0 | 0/5                       |                  0    |            0.62 |               0 |
| official_minor_30ft      | 3h  | persistence | 0/4 [0.00, 0.60]               |      2 |        2 | 2/5                       |                  0.1  |                 |               0 |
| official_minor_30ft      | 3h  | trend       | 4/4 [0.40, 1.00]               |      0 |        0 | 3/8                       |                  0.16 |            2.5  |               0 |
| official_minor_30ft      | 3h  | ridge_H     | 2/4 [0.07, 0.93]               |      0 |        2 | 2/5                       |                  0.1  |            1.5  |               0 |
| official_minor_30ft      | 3h  | xgb_H       | 2/4 [0.07, 0.93]               |      0 |        2 | 2/6                       |                  0.1  |            1.12 |               0 |
| official_minor_30ft      | 3h  | xgb_HR      | 2/4 [0.07, 0.93]               |      0 |        2 | 2/5                       |                  0.1  |            0.62 |               0 |
| official_moderate_36ft   | 15m | persistence | 0/1 [0.00, 0.97]               |      1 |        0 | 0/1                       |                  0    |                 |               0 |
| official_moderate_36ft   | 15m | trend       | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 15m | ridge_H     | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 15m | xgb_H       | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 15m | xgb_HR      | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 30m | persistence | 0/1 [0.00, 0.97]               |      1 |        0 | 0/1                       |                  0    |                 |               0 |
| official_moderate_36ft   | 30m | trend       | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            1    |               0 |
| official_moderate_36ft   | 30m | ridge_H     | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 30m | xgb_H       | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 30m | xgb_HR      | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 1h  | persistence | 0/1 [0.00, 0.97]               |      1 |        0 | 0/1                       |                  0    |                 |               0 |
| official_moderate_36ft   | 1h  | trend       | 1/1 [0.03, 1.00]               |      0 |        0 | 3/4                       |                  0.16 |            2    |               0 |
| official_moderate_36ft   | 1h  | ridge_H     | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 1h  | xgb_H       | 1/1 [0.03, 1.00]               |      0 |        0 | 1/2                       |                  0.05 |            0.25 |               0 |
| official_moderate_36ft   | 1h  | xgb_HR      | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            0.25 |               0 |
| official_moderate_36ft   | 3h  | persistence | 0/1 [0.00, 0.97]               |      0 |        1 | 1/1                       |                  0.05 |                 |               0 |
| official_moderate_36ft   | 3h  | trend       | 1/1 [0.03, 1.00]               |      0 |        0 | 3/4                       |                  0.16 |            4.75 |               0 |
| official_moderate_36ft   | 3h  | ridge_H     | 0/1 [0.00, 0.97]               |      0 |        1 | 3/3                       |                  0.16 |                 |               0 |
| official_moderate_36ft   | 3h  | xgb_H       | 1/1 [0.03, 1.00]               |      0 |        0 | 1/2                       |                  0.05 |            1    |               0 |
| official_moderate_36ft   | 3h  | xgb_HR      | 1/1 [0.03, 1.00]               |      0 |        0 | 0/1                       |                  0    |            1    |               0 |
| experimental_stage_10ft  | 15m | persistence | 0/20 [0.00, 0.17]              |     20 |        0 | 0/23                      |                  0    |                 |               0 |
| experimental_stage_10ft  | 15m | trend       | 18/20 [0.68, 0.99]             |      2 |        0 | 1/24                      |                  0.05 |            0.25 |               0 |
| experimental_stage_10ft  | 15m | ridge_H     | 18/20 [0.68, 0.99]             |      2 |        0 | 1/24                      |                  0.05 |            0.25 |               0 |
| experimental_stage_10ft  | 15m | xgb_H       | 19/20 [0.75, 1.00]             |      1 |        0 | 1/24                      |                  0.05 |            0.25 |               0 |
| experimental_stage_10ft  | 15m | xgb_HR      | 17/20 [0.62, 0.97]             |      3 |        0 | 0/23                      |                  0    |            0.25 |               0 |
| experimental_stage_10ft  | 30m | persistence | 0/20 [0.00, 0.17]              |     20 |        0 | 0/23                      |                  0    |                 |               0 |
| experimental_stage_10ft  | 30m | trend       | 19/20 [0.75, 1.00]             |      1 |        0 | 1/24                      |                  0.05 |            0.5  |               0 |
| experimental_stage_10ft  | 30m | ridge_H     | 20/20 [0.83, 1.00]             |      0 |        0 | 1/24                      |                  0.05 |            0.38 |               0 |
| experimental_stage_10ft  | 30m | xgb_H       | 19/20 [0.75, 1.00]             |      1 |        0 | 2/25                      |                  0.1  |            0.5  |               0 |
| experimental_stage_10ft  | 30m | xgb_HR      | 19/20 [0.75, 1.00]             |      1 |        0 | 1/24                      |                  0.05 |            0.5  |               0 |
| experimental_stage_10ft  | 1h  | persistence | 0/20 [0.00, 0.17]              |     20 |        0 | 0/23                      |                  0    |                 |               0 |
| experimental_stage_10ft  | 1h  | trend       | 20/20 [0.83, 1.00]             |      0 |        0 | 8/32                      |                  0.42 |            0.62 |               0 |
| experimental_stage_10ft  | 1h  | ridge_H     | 20/20 [0.83, 1.00]             |      0 |        0 | 2/26                      |                  0.1  |            0.5  |               0 |
| experimental_stage_10ft  | 1h  | xgb_H       | 20/20 [0.83, 1.00]             |      0 |        0 | 4/28                      |                  0.21 |            0.75 |               0 |
| experimental_stage_10ft  | 1h  | xgb_HR      | 20/20 [0.83, 1.00]             |      0 |        0 | 1/25                      |                  0.05 |            0.62 |               0 |
| experimental_stage_10ft  | 3h  | persistence | 0/20 [0.00, 0.17]              |     18 |        2 | 2/23                      |                  0.1  |                 |               0 |
| experimental_stage_10ft  | 3h  | trend       | 19/20 [0.75, 1.00]             |      0 |        1 | 32/57                     |                  1.67 |            1.25 |               0 |
| experimental_stage_10ft  | 3h  | ridge_H     | 19/20 [0.75, 1.00]             |      0 |        1 | 14/38                     |                  0.73 |            1    |               0 |
| experimental_stage_10ft  | 3h  | xgb_H       | 18/20 [0.68, 0.99]             |      1 |        1 | 11/34                     |                  0.57 |            0.75 |               0 |
| experimental_stage_10ft  | 3h  | xgb_HR      | 17/20 [0.62, 0.97]             |      1 |        2 | 5/27                      |                  0.26 |            0.5  |               0 |
| experimental_stage_15ft  | 15m | persistence | 0/9 [0.00, 0.34]               |      9 |        0 | 0/10                      |                  0    |                 |               0 |
| experimental_stage_15ft  | 15m | trend       | 9/9 [0.66, 1.00]               |      0 |        0 | 1/11                      |                  0.05 |            0.25 |               0 |
| experimental_stage_15ft  | 15m | ridge_H     | 9/9 [0.66, 1.00]               |      0 |        0 | 1/11                      |                  0.05 |            0.25 |               0 |
| experimental_stage_15ft  | 15m | xgb_H       | 9/9 [0.66, 1.00]               |      0 |        0 | 1/11                      |                  0.05 |            0.25 |               0 |
| experimental_stage_15ft  | 15m | xgb_HR      | 7/9 [0.40, 0.97]               |      2 |        0 | 1/11                      |                  0.05 |            0.25 |               0 |
| experimental_stage_15ft  | 30m | persistence | 0/9 [0.00, 0.34]               |      9 |        0 | 0/10                      |                  0    |                 |               0 |
| experimental_stage_15ft  | 30m | trend       | 9/9 [0.66, 1.00]               |      0 |        0 | 1/11                      |                  0.05 |            0.5  |               0 |
| experimental_stage_15ft  | 30m | ridge_H     | 9/9 [0.66, 1.00]               |      0 |        0 | 1/11                      |                  0.05 |            0.5  |               0 |
| experimental_stage_15ft  | 30m | xgb_H       | 9/9 [0.66, 1.00]               |      0 |        0 | 1/11                      |                  0.05 |            0.5  |               0 |
| experimental_stage_15ft  | 30m | xgb_HR      | 9/9 [0.66, 1.00]               |      0 |        0 | 1/11                      |                  0.05 |            0.25 |               0 |
| experimental_stage_15ft  | 1h  | persistence | 0/9 [0.00, 0.34]               |      9 |        0 | 0/10                      |                  0    |                 |               0 |
| experimental_stage_15ft  | 1h  | trend       | 9/9 [0.66, 1.00]               |      0 |        0 | 4/14                      |                  0.21 |            1    |               0 |
| experimental_stage_15ft  | 1h  | ridge_H     | 9/9 [0.66, 1.00]               |      0 |        0 | 2/12                      |                  0.1  |            0.75 |               0 |
| experimental_stage_15ft  | 1h  | xgb_H       | 9/9 [0.66, 1.00]               |      0 |        0 | 2/12                      |                  0.1  |            0.75 |               0 |
| experimental_stage_15ft  | 1h  | xgb_HR      | 8/9 [0.52, 1.00]               |      1 |        0 | 2/12                      |                  0.1  |            0.62 |               0 |
| experimental_stage_15ft  | 3h  | persistence | 0/9 [0.00, 0.34]               |      9 |        0 | 0/10                      |                  0    |                 |               0 |
| experimental_stage_15ft  | 3h  | trend       | 9/9 [0.66, 1.00]               |      0 |        0 | 20/30                     |                  1.04 |            1.75 |               0 |
| experimental_stage_15ft  | 3h  | ridge_H     | 9/9 [0.66, 1.00]               |      0 |        0 | 5/15                      |                  0.26 |            1.25 |               0 |
| experimental_stage_15ft  | 3h  | xgb_H       | 9/9 [0.66, 1.00]               |      0 |        0 | 4/15                      |                  0.21 |            1    |               0 |
| experimental_stage_15ft  | 3h  | xgb_HR      | 8/9 [0.52, 1.00]               |      1 |        0 | 2/12                      |                  0.1  |            0.5  |               0 |
| experimental_rise_4ft_3h | 15m | persistence | 1/26 [0.00, 0.20]              |     25 |        0 | 0/28                      |                  0    |            0.25 |               1 |
| experimental_rise_4ft_3h | 15m | trend       | 21/26 [0.61, 0.93]             |      5 |        0 | 4/32                      |                  0.21 |            0.25 |               1 |
| experimental_rise_4ft_3h | 15m | ridge_H     | 20/26 [0.56, 0.91]             |      6 |        0 | 2/30                      |                  0.1  |            0.25 |               1 |
| experimental_rise_4ft_3h | 15m | xgb_H       | 21/26 [0.61, 0.93]             |      5 |        0 | 4/32                      |                  0.21 |            0.25 |               1 |
| experimental_rise_4ft_3h | 15m | xgb_HR      | 18/26 [0.48, 0.86]             |      8 |        0 | 3/31                      |                  0.16 |            0.25 |               1 |
| experimental_rise_4ft_3h | 30m | persistence | 2/26 [0.01, 0.25]              |     24 |        0 | 0/29                      |                  0    |            0.25 |               1 |
| experimental_rise_4ft_3h | 30m | trend       | 24/26 [0.75, 0.99]             |      2 |        0 | 6/34                      |                  0.31 |            0.38 |               1 |
| experimental_rise_4ft_3h | 30m | ridge_H     | 25/26 [0.80, 1.00]             |      1 |        0 | 5/33                      |                  0.26 |            0.25 |               1 |
| experimental_rise_4ft_3h | 30m | xgb_H       | 23/26 [0.70, 0.98]             |      3 |        0 | 5/33                      |                  0.26 |            0.25 |               1 |
| experimental_rise_4ft_3h | 30m | xgb_HR      | 24/26 [0.75, 0.99]             |      2 |        0 | 4/32                      |                  0.21 |            0.25 |               1 |
| experimental_rise_4ft_3h | 1h  | persistence | 3/26 [0.02, 0.30]              |     21 |        2 | 0/26                      |                  0    |            0.25 |               1 |
| experimental_rise_4ft_3h | 1h  | trend       | 25/26 [0.80, 1.00]             |      1 |        0 | 10/38                     |                  0.52 |            0.5  |               1 |
| experimental_rise_4ft_3h | 1h  | ridge_H     | 25/26 [0.80, 1.00]             |      1 |        0 | 7/35                      |                  0.37 |            0.5  |               1 |
| experimental_rise_4ft_3h | 1h  | xgb_H       | 24/26 [0.75, 0.99]             |      2 |        0 | 8/36                      |                  0.42 |            0.5  |               1 |
| experimental_rise_4ft_3h | 1h  | xgb_HR      | 25/26 [0.80, 1.00]             |      1 |        0 | 10/39                     |                  0.52 |            0.5  |               1 |
| experimental_rise_4ft_3h | 3h  | persistence | 0/25 [0.00, 0.14]              |      0 |       25 | 0/0                       |                  0    |                 |               2 |
| experimental_rise_4ft_3h | 3h  | trend       | 18/25 [0.51, 0.88]             |      1 |        6 | 43/63                     |                  2.25 |            0.75 |               2 |
| experimental_rise_4ft_3h | 3h  | ridge_H     | 15/25 [0.39, 0.79]             |      2 |        8 | 13/31                     |                  0.68 |            0.5  |               2 |
| experimental_rise_4ft_3h | 3h  | xgb_H       | 7/25 [0.12, 0.49]              |      5 |       13 | 7/20                      |                  0.37 |            0.25 |               2 |
| experimental_rise_4ft_3h | 3h  | xgb_HR      | 2/25 [0.01, 0.26]              |      3 |       20 | 3/8                       |                  0.16 |            0.38 |               2 |
| experimental_rise_8ft_3h | 15m | persistence | 1/15 [0.00, 0.32]              |     12 |        2 | 0/13                      |                  0    |            0.25 |               0 |
| experimental_rise_8ft_3h | 15m | trend       | 13/15 [0.60, 0.98]             |      2 |        0 | 0/15                      |                  0    |            0.25 |               0 |
| experimental_rise_8ft_3h | 15m | ridge_H     | 12/15 [0.52, 0.96]             |      3 |        0 | 0/15                      |                  0    |            0.25 |               0 |
| experimental_rise_8ft_3h | 15m | xgb_H       | 13/15 [0.60, 0.98]             |      2 |        0 | 0/15                      |                  0    |            0.25 |               0 |
| experimental_rise_8ft_3h | 15m | xgb_HR      | 13/15 [0.60, 0.98]             |      2 |        0 | 0/15                      |                  0    |            0.25 |               0 |
| experimental_rise_8ft_3h | 30m | persistence | 0/15 [0.00, 0.22]              |     11 |        4 | 0/11                      |                  0    |                 |               0 |
| experimental_rise_8ft_3h | 30m | trend       | 15/15 [0.78, 1.00]             |      0 |        0 | 1/16                      |                  0.05 |            0.5  |               0 |
| experimental_rise_8ft_3h | 30m | ridge_H     | 15/15 [0.78, 1.00]             |      0 |        0 | 0/15                      |                  0    |            0.25 |               0 |
| experimental_rise_8ft_3h | 30m | xgb_H       | 14/15 [0.68, 1.00]             |      0 |        1 | 0/14                      |                  0    |            0.5  |               0 |
| experimental_rise_8ft_3h | 30m | xgb_HR      | 15/15 [0.78, 1.00]             |      0 |        0 | 0/15                      |                  0    |            0.5  |               0 |
| experimental_rise_8ft_3h | 1h  | persistence | 0/15 [0.00, 0.22]              |      9 |        6 | 0/9                       |                  0    |                 |               0 |
| experimental_rise_8ft_3h | 1h  | trend       | 15/15 [0.78, 1.00]             |      0 |        0 | 3/18                      |                  0.16 |            0.75 |               0 |
| experimental_rise_8ft_3h | 1h  | ridge_H     | 14/15 [0.68, 1.00]             |      0 |        1 | 2/16                      |                  0.1  |            0.75 |               0 |
| experimental_rise_8ft_3h | 1h  | xgb_H       | 14/15 [0.68, 1.00]             |      0 |        1 | 0/14                      |                  0    |            0.75 |               0 |
| experimental_rise_8ft_3h | 1h  | xgb_HR      | 14/15 [0.68, 1.00]             |      0 |        1 | 0/14                      |                  0    |            0.5  |               0 |
| experimental_rise_8ft_3h | 3h  | persistence | 0/15 [0.00, 0.22]              |      0 |       15 | 0/0                       |                  0    |                 |               0 |
| experimental_rise_8ft_3h | 3h  | trend       | 14/15 [0.68, 1.00]             |      0 |        1 | 13/27                     |                  0.68 |            1    |               0 |
| experimental_rise_8ft_3h | 3h  | ridge_H     | 6/15 [0.16, 0.68]              |      0 |        9 | 3/9                       |                  0.16 |            0.75 |               0 |
| experimental_rise_8ft_3h | 3h  | xgb_H       | 1/15 [0.00, 0.32]              |      0 |       14 | 1/2                       |                  0.05 |            2.75 |               0 |
| experimental_rise_8ft_3h | 3h  | xgb_HR      | 0/15 [0.00, 0.22]              |      0 |       15 | 0/0                       |                  0    |                 |               0 |

### Event counts by protocol (events vs distinct storm clusters)

| ('definition', '')       |   ('distinct_storm_clusters', 'blocked_cv_NONCAUSAL') |   ('distinct_storm_clusters', 'chrono_test') |   ('distinct_storm_clusters', 'chrono_val') |   ('events', 'blocked_cv_NONCAUSAL') |   ('events', 'chrono_test') |   ('events', 'chrono_val') |
|:-------------------------|------------------------------------------------------:|---------------------------------------------:|--------------------------------------------:|-------------------------------------:|----------------------------:|---------------------------:|
| experimental_rise_4ft_3h |                                                    24 |                                            7 |                                           6 |                                   27 |                           7 |                          6 |
| experimental_rise_8ft_3h |                                                    12 |                                            4 |                                           1 |                                   15 |                           5 |                          1 |
| experimental_stage_10ft  |                                                    16 |                                            4 |                                           5 |                                   20 |                           4 |                          5 |
| experimental_stage_15ft  |                                                     8 |                                            2 |                                           2 |                                    9 |                           2 |                          2 |
| official_action_25ft     |                                                     5 |                                            2 |                                           0 |                                    6 |                           3 |                          0 |
| official_minor_30ft      |                                                     4 |                                            2 |                                           0 |                                    4 |                           2 |                          0 |
| official_moderate_36ft   |                                                     1 |                                            1 |                                           0 |                                    1 |                           1 |                          0 |

### Official >=25 ft events inside the TEST period: per-event results (descriptive; n = 3 events, 2 storms)

peak_forecast_ft = forecast of the peak stage issued h before the peak; peak_ratio = forecast / observed peak. provisional_data = event lies in USGS provisional data (2026).

| event_start_utc   |   peak_ft | provisional_data   | horizon   | model       | status   |   lead_h |   peak_forecast_ft |   peak_ratio |   window_rmse_ft |   window_rmse_persistence_ft |
|:------------------|----------:|:-------------------|:----------|:------------|:---------|---------:|-------------------:|-------------:|-----------------:|-----------------------------:|
| 2025-07-05 06:15  |     30.03 | False              | 1h        | persistence | late     |   nan    |              29.58 |         0.99 |             3.87 |                         3.87 |
| 2026-07-15 23:00  |     25.04 | True               | 1h        | persistence | late     |   nan    |              24.26 |         0.97 |             1.71 |                         1.71 |
| 2026-07-17 00:30  |     36.75 | True               | 1h        | persistence | late     |   nan    |              36.38 |         0.99 |             1.99 |                         1.99 |
| 2025-07-05 06:15  |     30.03 | False              | 1h        | trend       | early    |     2.25 |              30.43 |         1.01 |             3.28 |                         3.87 |
| 2026-07-15 23:00  |     25.04 | True               | 1h        | trend       | early    |     1.75 |              27    |         1.08 |             0.78 |                         1.71 |
| 2026-07-17 00:30  |     36.75 | True               | 1h        | trend       | early    |     0.75 |              37.54 |         1.02 |             0.87 |                         1.99 |
| 2025-07-05 06:15  |     30.03 | False              | 1h        | ridge_H     | early    |     0.5  |              29.35 |         0.98 |             2.81 |                         3.87 |
| 2026-07-15 23:00  |     25.04 | True               | 1h        | ridge_H     | early    |     1    |              25.63 |         1.02 |             0.76 |                         1.71 |
| 2026-07-17 00:30  |     36.75 | True               | 1h        | ridge_H     | early    |     0.5  |              36.66 |         1    |             0.84 |                         1.99 |
| 2025-07-05 06:15  |     30.03 | False              | 1h        | xgb_H       | early    |     0.5  |              30.05 |         1    |             2.82 |                         3.87 |
| 2026-07-15 23:00  |     25.04 | True               | 1h        | xgb_H       | early    |     1    |              25.76 |         1.03 |             0.79 |                         1.71 |
| 2026-07-17 00:30  |     36.75 | True               | 1h        | xgb_H       | early    |     0.5  |              36.8  |         1    |             0.9  |                         1.99 |
| 2025-07-05 06:15  |     30.03 | False              | 3h        | persistence | late     |   nan    |              26.54 |         0.88 |             9.81 |                         9.81 |
| 2026-07-15 23:00  |     25.04 | True               | 3h        | persistence | miss     |   nan    |              17.73 |         0.71 |             4.83 |                         4.83 |
| 2026-07-17 00:30  |     36.75 | True               | 3h        | persistence | late     |   nan    |              33.25 |         0.9  |             5.65 |                         5.65 |
| 2025-07-05 06:15  |     30.03 | False              | 3h        | trend       | early    |     2.5  |              37.58 |         1.25 |            10.51 |                         9.81 |
| 2026-07-15 23:00  |     25.04 | True               | 3h        | trend       | early    |     3.75 |              30    |         1.2  |             3.75 |                         4.83 |
| 2026-07-17 00:30  |     36.75 | True               | 3h        | trend       | early    |     1.75 |              43.3  |         1.18 |             4.28 |                         5.65 |
| 2025-07-05 06:15  |     30.03 | False              | 3h        | ridge_H     | early    |     2.75 |              27.14 |         0.9  |             8.29 |                         9.81 |
| 2026-07-15 23:00  |     25.04 | True               | 3h        | ridge_H     | miss     |   nan    |              21.31 |         0.85 |             3.58 |                         4.83 |
| 2026-07-17 00:30  |     36.75 | True               | 3h        | ridge_H     | early    |     1    |              34.97 |         0.95 |             4.01 |                         5.65 |
| 2025-07-05 06:15  |     30.03 | False              | 3h        | xgb_H       | early    |     0.25 |              26.69 |         0.89 |             9    |                         9.81 |
| 2026-07-15 23:00  |     25.04 | True               | 3h        | xgb_H       | miss     |   nan    |              19.15 |         0.76 |             4.08 |                         4.83 |
| 2026-07-17 00:30  |     36.75 | True               | 3h        | xgb_H       | early    |     0.5  |              33.74 |         0.92 |             4.67 |                         5.65 |
