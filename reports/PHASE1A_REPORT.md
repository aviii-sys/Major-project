# Phase 1A Report: Baselines for Stage Forecasting at USGS 08167500

Status: for review. **No LSTM, GRU, Transformer or hybrid has been built.** Everything below follows `docs/PHASE1A_PROTOCOL.md`, which was written before any model was scored. Full result tables (generated, not hand-copied): `reports/phase1a/PHASE1A_TABLES.md`. Timestamps UTC, stage in feet.

## 0. What can and cannot be claimed
- **Official NWS categories** (action 25, minor 30, moderate 36, major 39 ft) are used descriptively only. In the test period there are **3 action-stage events that form 2 distinct storms** (one is the double crest of July 2026), 2 minor-stage and 1 moderate-stage event. The July 2026 events are **USGS provisional** data. **No official flood-detection capability is claimed.**
- Stage >= 10 ft and >= 15 ft are **experimental development targets**, not flood thresholds. Rises of >= 4 ft and >= 8 ft in 3 h are **experimental rapid-rise indicators**, not warning thresholds.
- "Real time" is not claimed. Both rainfall sources are retrospective (section 3).

## 1. Decision 1: historical discharge record (1997 and 2002): DOES NOT PASS

Raw 15-min discharge for 1986-10-01 to 2007-10-01 is kept separate in `data/raw/usgs_iv_discharge_pre2007/` (22 yearly files) and is **not** merged into the 2007-onward stage dataset. No gage height is inferred from discharge.

Audit criteria were fixed before looking (script docstring): C1 >= 95% of intervals exactly 15 min; C2 >= 90% of the year's 15-min steps present; C3 no gap > 2 h within 24 h of any candidate event peak; C4 no negative values. Results (`reports/discharge_pre2007/yearly_audit.md`):
- 1986 to 1995 is **hourly** (median step 60 min), with only 4% to 25% of the year present; unsuitable for a 15-min task. 1996 is only 86% 15-min (70% complete). **1997 fails C2 (56% complete).** 1998 to 2007 pass C1 to C4 (90.6% to 98.6% complete).

**Yearly completeness hid a decisive problem, so I added C5 (disclosed as added after the first audit pass).** C5 uses the independent USGS *daily mean* discharge as the reference: every day with a daily mean >= 5,000 cfs must have >= 90% of its 96 samples and an IV maximum >= the daily mean. Candidate-event detection on the 15-min record alone cannot see a flood that has no 15-min data.
- **1997-06-22:** daily mean 69,400 cfs. The 15-min record has 24 samples that day (maximum 17,600 cfs, on the rising limb) and **none on 1997-06-23** (daily mean 41,800 cfs). Of 8 flood days in 1997, 7 fail.
- **2002-07-02 to 07-06:** daily means 25,000 (20 samples, max 11,800), then 52,000, 43,000, 60,000 and 40,000 cfs on 07-03 to 07-06 with **zero 15-min samples**. Of 12 flood days in 2002, 11 fail.
- Passing flood periods at 15 min: **2007-08-17 (56,400 cfs; 13 of 13 flood days in 2007 pass)**, 2001-11, and most of 2004 (one day, 2004-11-17, has 75% coverage). 1998 and 2000 lose 2 of 4 and 3 of 4 flood days.
- **Conclusion:** the 1997 and 2002 floods cannot be used as 15-min event records. The 1998 to 2007 discharge years can support a separate discharge task only for the C5-passing events, listed in `reports/discharge_pre2007/flood_day_check.md`. The 2007-08-17 flood predates the stage record, so it is available only as discharge.
- **Correction to Phase 0:** Phase 0 said 15-min discharge was verified for 1997 and 2002. That check inspected short samples chosen around the flood dates and only showed that the rows were 15-min spaced; I did not check whether the peaks were present. They are not. A smaller slip during this audit: one interim print labelled "daily mean" actually showed the daily *maximum* column for 2002; the C5 numbers above use the explicit `00060_Mean` column.
- Unresolved: the 2002 annual-peak file lists 94,400 cfs on 2002-07-05, but the daily maximum series places 94,400 cfs on 2002-07-03.

## 2. Decision 2: event protocol (fixed in advance)
Grouping, start/end, hysteresis, matching, false alarms and lead time are defined in `docs/PHASE1A_PROTOCOL.md` sections 4 and 5 and were not changed after results. In short: exceedance events merge within 24 h; alarms use a 1 h hold (hysteresis); an alarm episode matches an event if its target interval overlaps the event +/- 1 h; an **early hit** needs an alarm issued before the event starts, lead time = event start minus the first such issue time; late detections are counted separately from hits; false alarms are alarm episodes matching no event. Intervals are exact binomial (Clopper-Pearson); counts accompany every rate. Storm clusters (>= 5 ft or >= 1 ft/3 h, merged within 72 h) number 78 and are never split across datasets.

## 3. Decision 3: rainfall

### 3.1 NASA Earthdata / NLDAS-2: needs your action
I cannot create an Earthdata account or enter your credentials. This machine has no Earthdata entry in `~/.netrc` (checked without printing contents). NLDAS-2 file URLs redirect to Earthdata login (HTTP 302). One OPeNDAP URL pattern I tried returned HTTP 410 (gone), so **I have not yet confirmed a working subsetting route**; this will be tested once credentials exist. Steps for you: (1) register at urs.earthdata.nasa.gov; (2) approve the "NASA GESDISC DATA ARCHIVE" application in your profile; (3) put the login in `~/.netrc` yourself and `chmod 600` it. Do not paste the password in chat. Then tell me and I will test access on a single granule first.

### 3.2 Timestamp semantics (ERA5 via Open-Meteo)
Open-Meteo documents hourly precipitation as the "sum of the preceding hour". It does not state outright that the timestamp is the end of that window. Independent check with two USGS tipping-bucket gauges inside the basin (Guadalupe at Hunt, Johnson Creek near Ingram; 5-min data aggregated to hours ending at the label): in the 10 wettest episodes (gauge 24 h total >= 40 mm) the rain-centroid time of ERA5 minus the gauge has **median +0.4 h (IQR 0.0 to 2.4 h)**. So there is **no evidence of a multi-hour shift**, but 0 h versus 1 h cannot be resolved. Hourly lagged correlation against a single 25 km cell is weak (r 0.18 to 0.33, no clear peak) and is not informative (`reports/rain_validation/partA_*`).

### 3.3 The two events where ERA5 rain appears after the peak (2015-05-24, 2016-05-30)
92 NOAA/NCEI daily gauges (COOP plus CoCoRaHS) lie inside the basin; 48 to 70 report on each event day (`reports/rain_validation/partB_*`). Gauge means are simple averages of reporting gauges (not area-weighted); observation days end around 7 am local.
- **2015 flood:** gauge-mean **130 mm** (max 313 mm; 64 gauges >= 25 mm) for the day ending 2015-05-24, against **9.8 mm** ERA5 basin mean for the matching 24 h (ending 12 UTC). ERA5's heaviest day (20 mm) is 05-25/26, when gauges average 2.6 and 17 mm.
- **2016 flood:** gauge-mean 62 mm (max 255 mm) on 05-29 and 24 mm on 05-30, against ERA5 5.0 and 3.8 mm. ERA5's largest days (about 43 mm on 06-01, 28 mm on 05-31 local) come after the peak.
- **Conclusion:** this is not a time shift. ERA5 misses these storms by roughly an order of magnitude and places its rain on the wrong days. Part of any point-versus-cell gap is scale, but not this much. At Johnson Creek the 24 h gauge total of 204 mm (2025-07-05) is 73 mm in the ERA5 cell, and 318 mm (2026-07-17) is 16 mm.

### 3.4 Spatial averaging and latency
Basin rainfall is the area-weighted mean over the 13 ERA5 0.25-degree cells overlapping the NLDI basin polygon (1,316 sq mi). A gauge-based daily basin product (92 stations) is feasible but not built. ERA5 (Open-Meteo) has a documented 5-day delay; the newest NLDAS-2 granule seen was 4 days old.
**Conclusion for source choice:** ERA5 rainfall is not adequate for the flood-producing storms of this record. NLDAS-2 is still unevaluated and must be tested against the same gauge comparison before it is preferred. Open-Meteo ERA5 stays as the secondary comparison. Land variables (soil moisture, temperature, humidity) are still downloading (ERA5-Land, 0.1 degree); they are not used in Phase 1A.

## 4. Phase 1A method summary
- **Task:** stage at t+h for h = 15 min, 30 min, 1 h, 3 h, predicting the change from the current stage. Features (all causal): current stage, differences over 15 min to 24 h, 24 h and 72 h running maxima; H+R adds latest hourly ERA5 basin rain, its age, and rain sums over 3 h to 7 days.
- **Models:** persistence, naive trend extrapolation (extra sanity baseline), ridge, XGBoost, each with hydrology only (H) and with rain (HR; persistence and trend ignore rain).
- **Masking:** stage <= -1.2 ft treated as sensor floor (16,538 rows); isolated gaps <= 1 h bridged causally for lag features only; provisional data never used for training or tuning.
- **Splits (chronological, storm-grouped, with a 3 h target purge):** train 2007-10-02 to 2017-12-31; validation 2018-01-01 to 2021-12-31 (tuning only); test 2022-01-01 to 2026-11-22. No nominal boundary fell inside a storm cluster. Eligible rows at 1 h: 354,604 train, 139,300 validation, 146,949 test. Tuned on validation, refit on train + validation, scored once on test. Tuned settings: ridge alpha 1,000 to 10,000; XGBoost depth 3 to 5 with only 22 to 129 trees (early stopping chose short ensembles).
- **Supplementary blocked CV** (6 contiguous blocks, boundaries outside clusters, hyperparameters fixed from the chronological validation) gives out-of-sample forecasts for all historical events. It is **non-causal** (models trained on future blocks) and is never mixed with the test results.
- **Uncertainty:** 2,000-resample storm-cluster bootstrap for RMSE, MAE and skill; exact binomial intervals for event rates.

## 5. Results (chronological TEST unless stated)

### 5.1 Stage forecast error (all test rows; mostly quiet river)
| Model | RMSE ft 15 m | 30 m | 1 h | 3 h |
|---|---|---|---|---|
| persistence | 0.035 | 0.067 | 0.127 | 0.338 |
| trend | 0.022 | 0.043 | 0.091 | 0.318 |
| ridge (H) | 0.018 | 0.036 | 0.078 | 0.258 |
| XGBoost (H) | 0.018 | 0.038 | 0.078 | 0.282 |
| XGBoost (H+R) | 0.018 | 0.037 | 0.081 | 0.296 |

Skill versus persistence (95% storm-cluster CI): ridge (H) 0.72 [0.50, 0.79] at 15 min, 0.63 [0.19, 0.76] at 1 h, **0.42 [0.03, 0.59] at 3 h**; XGBoost (H) 0.73 [0.62, 0.80], 0.62 [0.24, 0.75], 0.30 [0.07, 0.41]. The models are not distinguishable from one another at these sample sizes (intervals overlap), and **adding ERA5 rain does not help** (ridge identical, XGBoost slightly worse at 1 h and 3 h).

### 5.2 During events (issue times from 6 h before rise onset to the peak; 353 rows, 4 events of >= 10 ft)
RMSE (ft) at 15 m / 30 m / 1 h / 3 h: persistence 0.61 / 1.19 / 2.29 / 6.12; ridge (H) 0.29 / 0.62 / 1.36 / 4.75; XGBoost (H) 0.30 / 0.68 / 1.38 / 5.31; trend 0.35 / 0.74 / 1.57 / 5.69. Skill at 3 h is 0.40 (ridge) and 0.25 (XGBoost): **during floods the 3 h error is still about 5 ft**.

### 5.3 Event detection (test, experimental and official targets; early hits / events)
| Target (events in test) | model | 1 h hits | 1 h false alarms / episodes | 1 h median lead | 3 h hits | 3 h false alarms / episodes | 3 h median lead |
|---|---|---|---|---|---|---|---|
| Official action 25 ft (3 events, 2 storms) | persistence | 0/3 | 0/3 | n/a | 0/3 | 1/3 | n/a |
| | trend | 3/3 | 0/3 | 1.75 h | 3/3 | 0/3 | 2.5 h |
| | ridge (H) | 3/3 | 0/3 | 0.5 h | 2/3 | 1/4 | 1.9 h |
| | XGBoost (H) | 3/3 | 0/3 | 0.5 h | 2/3 | 1/3 | 0.4 h |
| Experimental stage >= 10 ft (4 events) | ridge (H) | 4/4 | 0/5 | 0.75 h | 4/4 | 2/7 | 1.1 h |
| | XGBoost (H) | 4/4 | 0/5 | 0.6 h | 4/4 | 0/5 | 0.75 h |
| | trend | 4/4 | 2/7 | 0.75 h | 4/4 | 5/10 | 1.4 h |
| Experimental rise >= 4 ft/3 h (6 evaluable events at 1 h, 5 at 3 h) | ridge (H) | 5/6 | 1/8 | 0.75 h | 2/5 | 3/7 | 0.5 h |
| | XGBoost (H) | 5/6 | 1/8 | 0.75 h | **0/5** | 1/3 | n/a |
| | trend | 5/6 | 1/8 | 0.5 h | 2/5 | 10/14 | 0.9 h |
| Experimental rise >= 8 ft/3 h (5 events) | ridge (H) | 5/5 | 0/5 | 0.5 h | 1/5 | 0/1 | 0.25 h |
| | XGBoost (H) | 5/5 | 0/5 | 0.5 h | **0/5** | 0/0 | n/a |
| | trend | 5/5 | 1/6 | 0.75 h | 5/5 | 3/8 | 1.0 h |

With only 1 to 7 events per row, every rate is very uncertain (for example 3/3 has a 95% interval of 0.29 to 1.00). The blocked-CV version with 15 to 27 events (full tables in `PHASE1A_TABLES.md`) shows the same pattern: for the 4 ft/3 h indicator at 3 h, XGBoost (H) detects 7/25, ridge 15/25, trend 18/25 (with 43 false-alarm episodes in 63).

### 5.4 Per-event view of the three official test events (`PHASE1A_TABLES.md`, last table)
At 1 h every learned model issues an early alert for all three, but leads are **0.5 to 1.0 h** and the forecasts of the peak are within 3% of observed. At 3 h, XGBoost detects 2 of 3 (leads 0.25 and 0.5 h) and misses the 25.04 ft crest of 2026-07-15; peak forecasts issued 3 h ahead are 0.76 to 0.92 of the observed peak (persistence 0.71 to 0.90; trend over-forecasts at 1.18 to 1.25). Figure `reports/phase1a/figures/fig2_test_events_forecasts.png` shows the 3 h forecast trailing the sharp onset by several hours.

## 6. Interpretation (with confidence labels)
1. **Supported by the data:** learned linear and tree models cut RMSE well below persistence at every horizon, over all rows and inside event windows; the gain shrinks with horizon, and at 3 h the all-row intervals for ridge reach almost zero.
2. **Supported, small samples:** better RMSE does **not** mean better early warning. The naive trend extrapolation matches or beats the learned models at hitting rapid rises at 3 h, at the cost of many false alarms, while learned models are conservative. This is the squared-error behaviour (shrinkage toward the mean) that Phase 0 anticipated.
3. **Supported:** lead times are short (mostly under one hour for learned models). The models mainly react once a rise has started; none of them anticipates onset from stage history alone.
4. **Not supported either way:** whether rainfall helps. ERA5 rain adds nothing, but Section 3.3 shows ERA5 misses the flood-producing storms, so this is a test of ERA5, not of the value of rain.
5. **Not established:** any claim about official flood detection; any difference between ridge and XGBoost; generalization beyond one gauge and a handful of storms.

## 7. Disclosure of a defect found after seeing test output
The first full run used strict rolling windows, and one missing sample at 2026-07-16 18:15 made every row of the 2026-07-17 event (36.75 ft, the largest test event) ineligible. All models were therefore scored as "missed" on it. I found this while inspecting per-event output, fixed the data handling (short causal gap bridging, tolerant rolling windows), added an "evaluable event" rule so that events lacking eligible issue times are reported rather than counted as misses, added a regression test (11 tests pass), and re-ran everything. **No first-run numbers appear in this report.** Because the fix was made after seeing test output, treat it as a deviation (`docs/PHASE1A_PROTOCOL.md`, deviation 3). Two 4 ft/3 h rapid-rise events are still not evaluable at 3 h.

## 8. Limitations
Single gauge. Test period contains only 2 official-stage storms, one of them provisional. Rain inputs are unreliable for the key storms. Chronological test period is hydroclimatically different from training (2022 and 2023 had no events above 5 ft; 2025 and 2026 hold half of the action-stage events). Hyperparameter search is small. No imbalance-aware training objective, probabilistic output, or alarm-threshold tuning has been tried; the alarm rule is the fixed protocol rule (forecast >= threshold).

## 9. For your review before any LSTM, GRU or Transformer work
1. Is the protocol's alarm rule acceptable, or should detection use probabilities and a tuned operating point (a Phase 1B decision)?
2. Rainfall: provide Earthdata access for NLDAS-2, or approve a gauge-based daily basin-rainfall product (92 stations) as the independent check and possible input.
3. Should the 1998 to 2007 C5-passing discharge events become a separate discharge-forecasting dataset, and with which events?
4. Should Phase 1B first add event-aware objectives (for example asymmetric or quantile loss) to the linear/XGBoost baselines, so the later deep models are compared against a fair, strengthened baseline?

## 10. Files and reproduction
`python scripts/run_phase1a.py` then `python scripts/make_phase1a_tables.py`. Supporting: `scripts/audit_discharge_pre2007.py`, `scripts/rain_validation.py`, `docs/PHASE1A_PROTOCOL.md`, `src/flashflood/` (library), `tests/test_phase1a.py` (11 tests). Outputs: `reports/phase1a/` (tables, figures, `results.json`), `reports/discharge_pre2007/`, `reports/rain_validation/`.
