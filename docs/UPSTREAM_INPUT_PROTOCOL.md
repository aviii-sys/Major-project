# Upstream-input research protocol: hydrology-only versus upstream rainfall and upstream river gauges

**Status: DRAFT FOR RESEARCH-GUIDE REVIEW. NOT APPROVED.** Written 2026-11-22. **No upstream-input experiment has been run, trained or evaluated**, and none will be until the guide has decided the questions in section 6. Everything in this document is exploratory and retrospective in the same sense as Phases 1C to 1E: the whole 2007-2026 record has been inspected, so no result of this plan can be untouched validation. Supporting descriptive tables: `reports/upstream_protocol_support/` (built by `scripts/build_upstream_protocol_support.py`; table names `S1`-`S8` below). Earlier feasibility work: `docs/UPSTREAM_INPUT_FEASIBILITY.md`, `docs/GUIDE_BRIEF.md`. Literature review: to be added by the student or guide; no external publication is cited here because none was re-verified for this draft.

## 0. Purpose, scope and what is NOT being done
**Purpose.** Phase 1D showed that GRU/LSTM trained on the gauge's own history have no robust advantage over ridge regression or a damped trend, and that every model trails sharp rises (measured after the fact: a 3 h forecast shows a level a median of 2.0 to 2.5 h after the river reached it, and no model forecast half of a rise before it began; `reports/PHASE1E_ONSET_TIMING.md`). Phase 1E showed that a longer own-history window (72 h) does not help. The feasibility study found that, for part of the events, the rise appears at gauges upstream hours before Spring Branch (leads of 6 to 26 h in 6 of 18 events under the main timing rule), and for others the rain fell below or level with the upstream gauges. This protocol defines a controlled way to find out **whether and for which floods extra information changes a fixed model's forecasts**. It does not assume that it will.

**Not being done here (all need separate approval):** no training, evaluation or tuning of any upstream-input model; no hybrid Transformer-LSTM; no Phase 1F Transformer diagnostic; no probability head; no operational warning categories, live alerts or real-time operation; no discharge *forecasting* (discharge may appear only as a candidate *input*, question 5); no change to any Phase 1C-1E artifact. The supporting scripts read cached data and, once, public index pages and gauge series (section 3.1).

## 1. Research questions and a-priori hypotheses
- **RQ1.** Does adding upstream river-gauge observations (configuration C) change a fixed GRU's forecast error and event timing relative to hydrology-only inputs (A)? Primary evidence: flood windows of the events classified *upstream-led* (section 3.6).
- **RQ2.** Does adding temporally resolved basin rainfall (B) do so, in particular for events the upstream gauges cannot anticipate?
- **RQ3.** Does using both (D) add anything beyond the better of B and C?
- **RQ4 (diagnostic).** For which events does added information help, hurt or make no difference, and does that agree with the pre-specified classification?

Hypotheses are written before any run and each can fail:
- **H1.** C reduces flood-window RMSE at 1 h and 3 h relative to A for upstream-led events (mechanism: the upstream rise precedes the Spring Branch rise by hours, far longer than the 15 min to 3 h horizons).
- **H2.** C neither helps nor hurts (within a margin) for local-or-downstream-led events: upstream gauges contain no information about rain that fell below them. A clear benefit there would be suspicious (section 3.11).
- **H3.** B can help local-or-downstream-led events only if the rainfall product sees the storm at the right place and time. No direction or size is assumed; it may add noise, particularly because its training record is short (section 3.8).
- **H4.** D is not worse than the better of B and C by more than a margin. It is not expected to be better by construction (more inputs per training event).
- **H5.** None of B, C, D worsens all-row error by more than a margin.
- **Explicit non-claims:** upstream information improves every flood; any configuration improves early warning; any result transfers to other basins.

## 2. The four controlled configurations
All four use the **same model**: the Phase 1E GRU (hidden size 64, shared encoder, four horizon-specific heads, per-horizon scaled MSE, Adam 1e-3, batch 512, 120,000 rows per epoch, gradient clip 1.0, patience 6, at most 40 epochs, best-validation checkpoint) with the **24 h (96-step) window**, the default after Phase 1E.

| Block of inputs | A hydrology-only | B + upstream rainfall | C + upstream river gauges | D + both |
|---|---|---|---|---|
| Target gauge 08167500: stage relative to current stage, 15-min change, missing mask (per step); current stage and missing fraction (side) | yes | yes | yes | yes |
| Rainfall zones, hourly accumulation held from the end of each hour, plus a missing mask (per step) | - | yes | - | yes |
| Upstream gauges (7 long-record gauges, section 3.2): per gauge the same three per-step channels as the target (relative stage, 15-min change, mask) and two side inputs (stage above the gauge's own causal 7-day minimum, missing fraction) | - | - | yes | yes |

**Single factor that changes:** the information available to the model (extra input channels); the architecture changes only in input width. **Identical across A-D:** the six Phase 1D folds and their 27 h 15 min embargo; targets (stage change at 15 min, 30 min, 1 h, 3 h); horizons; hidden size, optimiser, schedule and early stopping; preprocessing and scaling rules (fitted on each fold's training rows only); training rows (Phase 1D rows with a full 96-step history; added inputs that are missing are masked, not dropped); evaluation rows (the Phase 1B/1D eligible held-out rows); event definitions and catalogue; metrics, bootstrap and seeds 0, 1, 2. Two honest qualifications: (i) matched seeds do not give identical initial weights across configurations because the input weight matrix has a different shape, so pairing is by data order and seed index only and seed noise stays in the comparison (Phase 1E found seed-level differences as large as the pooled effect); (ii) B and D are defined only in folds that have rainfall training data (section 3.8).

A **control that is cheap and informative** (optional, needs approval, question 10): rerun C with the upstream series replaced by series from unrelated dates (same hour of year, different year). If it keeps the benefit, the benefit is not about upstream information.
A **secondary variant** (needs approval, question 8): rainfall as daily gauge accumulations only (antecedent wetness, the planned item 3 of Phase 1C section 7); it carries no storm-onset timing.

## 3. The twelve required topics

### 3.1 Data sources and availability (`S2_data_source_matrix`)
| Source | Resolution and period (as verified) | Status in this project |
|---|---|---|
| USGS stage, target 08167500 | 15 min, 2007-10-02 on | in use; 2026 values provisional |
| USGS stage, 7 long-record upstream gauges | stamps 15 min until about 2018 and 5 min at several gauges in recent files (section 3.3); records start 2007-10-01 (Center Point 2007-10-06) | event windows cached (`data/raw/upstream/iv`); full record not downloaded |
| USGS stage, Bergheim 08167200 | since 2016-10-26 | event windows cached; absent before that date |
| USGS discharge, upstream gauges | 15 min; start dates 1987 to 2019 (Bergheim 2019-10-01) per the series catalogue | listed only; not downloaded; ratings and approval status not checked |
| Gauge-based daily basin rainfall (built here) | daily, 2007-10-02 to 2026-11-15; usable only from 15:00 UTC on the observation day | built; no sub-daily timing |
| ERA5 (Open-Meteo) | hourly | have; about 8% of gauge rainfall on 2015-05-24 and 2016-05-29; not used as an input |
| MRMS hourly radar+gauge QPE, public Iowa State archive | `GaugeCorr_QPE_01H` first listed 2015-05-06 (absent 2015-05-04); `MultiSensor_QPE_01H_Pass2` listed on the probed 2021-2026 dates; none for 2012-01-25 and 2013-10-31; continuity between probed dates NOT verified | listed only; not downloaded; format, timestamps, accuracy not validated |
| MRMS on AWS, HRRR, Stage IV, NLDAS-2, ASOS, USGS 15-min rain gauges | see `S2` | not used; NLDAS-2 needs an Earthdata login that the user places in `~/.netrc` (never requested in chat); Stage IV unverified; USGS 15-min rain gauges exist only from 2023-11-21 (Hunt) and 2025-05-12 (Johnson Creek): 4 of the 18 events have at least one (2024-07-24: Hunt only; the three 2025-2026 events: both) |

The only sub-daily rainfall source that covers most events is the radar-based product: the archive lists no hourly product for the first 2 of the 18 evaluated events (2012-01-25 and 2013-10-31) and lists files on every probed date of the other 16 (two of those dates, 2015-05-18 and 2016-05-17, have 22 of 24 hourly files).

### 3.2 Upstream gauge selection and reliability
**Selection rule (fixed before any run, no use of evaluated-event results beyond what already exists):** all seven gauges with 15-min stage since 2007 form the set for C and D: N Fk Guadalupe near Hunt (08165300), Hunt (08165500), Johnson Creek (08166000), Kerrville above Bear Creek (08166140), Kerrville (08166200), Center Point (08166250), Comfort (08167000). Bergheim (08167200, 52 km above Spring Branch, since 2016-10-26) is excluded from the primary set because its absence in folds 1-3 would make the input set differ by fold; it may be added in a post-hoc sub-analysis. **Caution:** the earlier suggestion to try Comfort first was made after seeing the lead table for the evaluated events, so any single-gauge variant is a selection informed by evaluated events and must be labelled post hoc.

| Gauge | Drainage (sq mi) | River km above 08167500 | Reliability findings (`reports/upstream_feasibility`, `S1`, `S8`) |
|---|---|---|---|
| N Fk near Hunt | 169 | 166.5 | daily stage 99.7% of days on average; no datum step |
| Hunt | 288 | 157.4 | 99.3%; below 80% window coverage in 2025-07-05 |
| Johnson Creek | 114 | n/a (tributary) | 98.7%; -1.34 ft step in 2024; below 80% in 2018-10-17 |
| Kerrville above Bear Ck | 494 | 144.0 | 98.5%; below 80% in 2015-05-17 |
| Kerrville | 510 | 140.2 | 98.4%; below 80% in 2018-10-17 and 2025-07-05 |
| Center Point | 553 | 130.0 | 99.0% (worst year 85.3%); +0.89 ft step in 2026 (possibly provisional); below 80% in 2025-07-05 |
| Comfort | 839 | 101.6 | 97.7%; **+2.90 ft step in 2011** (+2.20 ft net drift 2007-2026); below 80% in 2016-05-19 and 2026-06-15 |

(Daily-stage completeness and steps are from the matched-discharge audit; "below 80%" is the 15-min coverage in `[t0-48 h, t0+3 h]` on the 15-min grid, recomputed here.) **Consequences:** (a) absolute upstream stage must not be an input, since a datum step identifies the year; inputs are relative stage, rises, and elevation above the gauge's own causal minimum (3.11); (b) outages cluster in large events (3 of 8 gauges below 80% in the window of 2025-07-05; 2 of 8 in 2018-10-17), exactly where the information matters most; (c) discharge would add rating-curve and provisional-data questions that were not checked here and is derived from stage at these gauges, so stage is the default (question 5); (d) archived NWIS values are the approved or provisional record, not as-received telemetry, so research-mode results do not describe real-time behaviour.

### 3.3 Temporal resolution and timestamp alignment
- **Clock:** everything is UTC (cached gauge files are stamped `+00:00`). The gauge-rainfall day is the 24 h ending about 12-14 UTC and is usable only from 15:00 UTC on that day.
- **Grid:** the model grid is the target gauge's 15-min grid. **Finding (`S8`):** several upstream gauges report at 5-min stamps in recent files (24 of the 135 gauge-event series with data, in the events of 2019-05-08, 2021-10-14, 2024-07-24, 2025-07-05, 2026-06-15 and 2026-07-15; target gauge 15 min in a one-request check). The earlier timing analysis assumed 15-min spacing, so its coverage statistic can exceed 1 and its "3 h rise" is 1 h on 5-min data. **Rule:** keep only readings stamped exactly on :00, :15, :30, :45 (no averaging, no interpolation); a mark with no reading is missing. Recomputing the earlier timing on this grid changes no event's class (3.6).
- **Availability at issue time t:** a stage reading stamped t' is usable at issue time t if t' <= t (reporting latency of archived data is not measured; for real-time use a latency parameter would be added). An hourly rainfall total for the hour ending at HH:00 is usable from HH:00 + L; **L = 0 in the primary research-mode run, L = 1 h in a pre-specified sensitivity run**. The product's timestamp convention (start or end of hour) and units must be verified from file metadata before use.
- **Rainfall product continuity:** the archive product name changes between the probed 2018-2019 and 2021 dates; whether the algorithm changed is not verified; this is a non-stationarity risk in B and D (3.12).
- **Research mode versus operational mode:** gauge-corrected radar QPE is a retrospective product; the latency and availability of an equivalent product in real time were not verified. Results of B and D are research-mode and must not be described as real-time capability.

### 3.4 Missing-data handling
- Same treatment as the target channel in `src/flashflood/seq.py`: a missing value is set to 0 in the value channels with mask 0 (never imputed as a real value) and the window's missing fraction is a side input; per-gauge masks are separate channels.
- No imputation from future samples; any forward fill is causal and limited (the Phase 1A rule: lag reference filled forward by at most 4 steps; the same limit for upstream gauges, to be confirmed in question 12).
- A gauge with no data in a window is all-masked for that row; the model must not receive another gauge's value in its place.
- **Two evaluation row sets for B, C, D:** (i) the common eligible rows of Phase 1D/1E (primary, so every number is comparable with all earlier phases; missing added inputs are masked), and (ii) *complete-input rows*, where every added input is fully observed in its window (sensitivity). Differences between (i) and (ii) show how much of any effect depends on missing data.
- **Pre-specified missing-input robustness option (later, needs approval):** randomly masking whole gauges during training (input dropout) so the model learns to cope with outages. Not part of A-D as defined.
- Rainfall: hours with no archive file are missing (mask 1); the archive probe found two hours missing on 2015-05-18 and on 2016-05-17 (22 of 24 files; `mrms_archive_probe.csv`).

### 3.5 Event coverage and usable historical events (`S1`, `S1b`)
Evaluated >= 10 ft events (experimental target, **not** a flood stage): 18 events, 14 storm clusters. Official NWS stages (action 25, minor 30, moderate 36, major 39 ft) are kept separate: 6 official events (5 storms) are contained in 5 of the 18 (the 2026 pair is one >= 10 ft event). "Recorded" = gauges with at least 80% of the 15-min marks in `[t0-48 h, t0+3 h]`; "installed" excludes Bergheim before 2016-10-26. Leads are the best consistent first-rise lead in hours under timing rules v2 / v3 recomputed on the 15-min grid; `none` = no consistent upstream response. QPE = hourly radar+gauge product listed on every probed UTC date from the day before the event start to the event end (G = `GaugeCorr_QPE_01H`, M = `MultiSensor_QPE_01H_Pass2`). Gauge-daily = largest daily basin total on those dates (mm; reporting stations inside the basin that day).

| Event start (UTC) | Peak ft (NWS stage) | Fold / cluster | Prov. | Gauges recorded / installed | Dropout (<80%) | Lead h v2 / v3 | Class | QPE | Gauge-daily mm (stations) |
|---|---|---|---|---|---|---|---|---|---|
| 2012-01-25 12:15 | 10.09 (none) | 1 / 12 |  | 7 / 7 |  | none / none | local-or-downstream | none | 34 (67) |
| 2013-10-31 06:30 | 14.95 (none) | 1 / 20 |  | 7 / 7 |  | none / none | local-or-downstream | none | 14 (65) |
| 2015-05-17 16:30 | 11.72 (none) | 2 / 27 |  | 6 / 7 | Kerrville abv Bear | 2.75 / 2.75 | ambiguous | G | 35 (64) |
| 2015-05-23 23:15 | 34.50 (minor) | 2 / 27 |  | 7 / 7 |  | 0.00 / 0.00 | local-or-downstream | G | 119 (65) |
| 2015-10-30 12:30 | 30.06 (minor) | 2 / 31 |  | 7 / 7 |  | -1.50 / -1.50 | local-or-downstream | G | 34 (68) |
| 2016-05-18 07:00 | 13.46 (none) | 3 / 33 |  | 7 / 7 |  | 2.50 / 2.50 | ambiguous | G | 46 (70) |
| 2016-05-19 15:45 | 18.41 (none) | 3 / 33 |  | 6 / 7 | Comfort | 0.00 / 35.25 | ambiguous | G | 46 (70) |
| 2016-05-29 20:30 | 26.07 (action) | 3 / 33 |  | 7 / 7 |  | 16.25 / 16.25 | **upstream-led** | G | 64 (64) |
| 2016-06-02 17:30 | 12.80 (none) | 3 / 33 |  | 7 / 7 |  | 18.25 / 18.25 | **upstream-led** | G | 31 (67) |
| 2018-09-09 15:15 | 12.64 (none) | 4 / 41 |  | 8 / 8 |  | -7.00 / -7.00 | local-or-downstream | G | 44 (60) |
| 2018-09-22 16:15 | 10.30 (none) | 4 / 43 |  | 8 / 8 |  | 2.50 / 2.50 | ambiguous | G | 23 (61) |
| 2018-10-17 00:45 | 24.37 (none; below 25) | 4 / 45 |  | 6 / 8 | Johnson Ck, Kerrville | 25.75 / 25.75 | **upstream-led** | G | 63 (60) |
| 2019-05-08 20:45 | 12.18 (none) | 4 / 48 |  | 8 / 8 |  | 2.00 / 2.00 | ambiguous | G | 10 (58) |
| 2021-10-14 04:45 | 19.73 (none) | 5 / 56 |  | 8 / 8 |  | none / none | local-or-downstream | M | 41 (77) |
| 2024-07-24 14:45 | 12.34 (none) | 5 / 63 |  | 8 / 8 |  | none / 24.25 | ambiguous | M | 64 (71) |
| 2025-07-05 03:45 | 30.03 (minor) | 6 / 70 |  | 5 / 8 | Hunt, Kerrville, Center Point | 20.00 / 20.00 | **upstream-led** | M | 79 (68) |
| 2026-06-15 18:30 | 13.58 (none) | 6 / 75 | yes | 7 / 8 | Comfort | 6.25 / 6.25 | **upstream-led** | M | 51 (74) |
| 2026-07-15 18:30 | 36.75 (moderate) | 6 / 77 | yes | 8 / 8 |  | 18.00 / 36.75 | **upstream-led** | M | 172 (65) |

(Here "none" under peak means the peak did not reach the 25 ft action stage.) The six official events (`S1b`): 2015-05-24 01:15 (34.50 ft, minor, fold 2; class local-or-downstream), 2015-10-30 14:15 (30.06, minor, fold 2; local-or-downstream), 2016-05-30 01:15 (26.07, action, fold 3; upstream-led), 2025-07-05 06:15 (30.03, minor, fold 6; upstream-led), 2026-07-15 23:00 (25.04, action, fold 6, provisional; upstream-led) and 2026-07-17 00:30 (36.75, moderate, fold 6, provisional; upstream-led). The last two share one >= 10 ft event and one storm cluster.

### 3.6 Identification of upstream-driven versus locally generated floods
**Rule, fixed before any model is run, from observed data only (`S1`, `S4`).** Take the best consistent first-rise lead (hours; the upstream gauge whose rise precedes the Spring Branch rise by the most, among gauges whose first-rise and steepest-rise timings agree within 6 h) under the two timing rules already in the project: v2 (anchored to the Spring Branch rise anywhere in the event window) and v3 (anchored to the catalogued event's own rise). Band each: *long* >= 6 h, *short* 1 h to < 6 h, *none* = no consistent response or lead < 1 h.
- **upstream-led:** long under both rules.
- **local-or-downstream-led:** none under both rules.
- **ambiguous:** everything else (short under both, or the two rules disagree).

**Result:** 6 upstream-led (5 storm clusters; 3 of them with peaks >= 25 ft, 2 provisional), 6 local-or-downstream-led (6 clusters; 2 with peaks >= 25 ft: the 2015-05 and 2015-10 floods), 6 ambiguous (5 clusters; none >= 25 ft). The same classes result from the stored feasibility tables and from the 15-min-grid recomputation (`S8`). Notes: 2026-06-15 is marginal (a single consistent gauge, lead 6.25 h, 0.25 h above the cut-off); 2026-07-15 has a v3 lead of 36.75 h that is physically implausible (a multi-pulse storm; the v2 lead is 18.00 h); 2016-05-19 and 2024-07-24 are ambiguous because the rules disagree (multi-pulse storms). Under a stricter 2 ft per 3 h trigger only 4 of 18 events have a best lead of 6 h or more in the stored sensitivity table (`sensitivity_trigger_and_tolerance.csv`), so the upstream-led group is sensitive to this choice and a pre-specified sensitivity analysis will repeat the strata with the 2 ft trigger.
**What the classes mean and do not mean:** they describe the response at upstream *gauges*, not where the rain fell (radar could refine this, post hoc). They are defined with post-event information and are used only to stratify evaluation, never as an input, a training filter or a model-selection criterion. The class table will be frozen (file hash recorded) when the guide approves this protocol.

### 3.7 Hydrological travel-time considerations (`S3_travel_time`)
River distances above Spring Branch from NLDI flowline geometry (main stem): Bergheim 52.3 km, Comfort 101.6, Center Point 130.0, Kerrville 140.2, Kerrville above Bear Creek 144.0, Hunt 157.4, N Fk near Hunt 166.5 (Johnson Creek is a tributary: no main-stem distance). Implied flood-wave speeds from median leads are 2.2 to 3.3 m/s (Bergheim 3.28, Comfort 2.17, Kerrville 2.47, Hunt 3.06, N Fk 2.64 m/s) and 1.7 to 1.9 m/s from the longest leads (Comfort, Kerrville, Hunt), which supports the timings; medians at Center Point (13.14 m/s) and Kerrville above Bear Creek (4.44 m/s) are not travel times because they mix storms centred between gauges. Arithmetic illustration only (distance divided by 2 or 3 m/s): Comfort 9.4 to 14.1 h, Hunt 14.6 to 21.9 h, N Fk near Hunt 15.4 to 23.1 h. Measured best leads in the upstream-led events are 6.25 to 25.75 h.
**Implications.** (i) Leads of 6 to 26 h are much longer than the 15 min to 3 h horizons, so for upstream-led events the question is whether the model can use *old* upstream information to anticipate onset within 3 h; longer horizons (6 to 12 h) would be a natural target but are outside the project's fixed horizons (question 9). (ii) With a 24 h window the earliest rise at the farthest gauge (25.75 h in 2018-10-17) is just outside the window at the moment of Spring Branch onset, while nearer gauges (Comfort 16.25 h in that event) are inside; a 48 h upstream window is a pre-specified secondary variant requiring an embargo re-derivation (3.8, question 8). (iii) The drainage below Comfort is 476 sq mi of 1,315 (36.2%) and below Bergheim 212 sq mi (16.1%) (`S3`): rain falling there cannot be seen by upstream stage, which is the mechanism for the local-or-downstream class. (iv) Tributary contributions: Johnson Creek is the only tributary gauge in C (no main-stem distance; the other six lie on the main-stem path, N Fk near Hunt being a headwater fork); other tributary gauges are too short or too small (Honey Creek sites 2007-2014, 0.35 to 0.53 sq mi; Cypress Creek since 2023-09). Sub-basin polygons for rainfall zones are **not yet fetched**; the default zones (question 11) are the area above Comfort (839 sq mi) and the residual below it (476 sq mi), to be derived from NLDI catchments at stage 1.

### 3.8 Chronological train-validation-test splits (`S5_fold_data_availability`)
The six Phase 1D folds are used **unchanged**: expanding training window, a validation chunk before each test block, embargo 27 h 15 min = 24 h window + 3 h maximum horizon + one 15-min step, boundaries in quiet periods, scalers and target scales fitted on training rows only.

| Fold | Training | Validation | Test block | Years of hourly QPE in training / validation | Events (up / local / ambiguous) | Clusters |
|---|---|---|---|---|---|---|
| 1 | 2007-10-02 to 2010-12-06 | 2010-12-07 to 2011-12-30 | 2012-01-01 to 2014-12-31 | 0 / 0 | 2 (0 / 2 / 0) | 2 |
| 2 | to 2013-03-07 | 2013-03-08 to 2014-12-30 | 2015 | 0 / 0 | 3 (0 / 2 / 1) | 2 |
| 3 | to 2013-12-29 | 2013-12-30 to 2015-12-30 | 2016-2017 | 0 / 0.65 | 4 (2 / 0 / 2) | 1 |
| 4 | to 2015-12-30 | 2015-12-31 to 2017-12-30 | 2018-2019 | 0.65 / 2.00 | 4 (1 / 1 / 2) | 4 |
| 5 | to 2017-12-29 | 2017-12-30 to 2019-12-30 | 2020-2024 | 2.65 / 2.00 | 2 (0 / 1 / 1) | 2 |
| 6 | to 2022-12-30 | 2022-12-31 to 2024-12-30 | 2025 to 2026-11-22 | 7.65 / 2.00 | 3 (3 / 0 / 0) | 3 |

**Consequences.** (1) **C is defined in all six folds** (gauge stage since 2007). (2) **B and D are defined only where hourly rainfall exists in training**: folds 4, 5, 6 (0.65, 2.65 and 7.65 years); fold 4 is marginal. The default is to run B and D on folds 5 and 6 only, report fold 4 as a labelled extra, and report A and C on exactly the same folds for every paired comparison. In folds 5-6 the upstream-led events are the three of fold 6 (2025-07-05, 2026-06-15, 2026-07-15; two provisional), i.e. **three events in three storm clusters**. A longer-record hourly source would remove this limit but none is verified (NLDAS-2 needs an Earthdata login; its precipitation provenance is not verified). (3) A window longer than 24 h for any channel group requires re-deriving the embargo as window + 3 h + one step (for 48 h: 51 h 15 min) and re-asserting the boundary rule; the quiet-period rule (no cluster in the 96 h before a boundary) leaves room for this. (4) No fold boundary, event-to-fold mapping or embargo is changed by this protocol.

### 3.9 Consistent evaluation across A, B, C and D
- **Same rows and events:** the Phase 1B/1D eligible held-out rows; the 18 evaluated >= 10 ft events (14 clusters), the 25 rapid rises >= 4 ft/3 h (22 clusters), the 13 rises >= 8 ft/3 h (10 clusters), the 6 official events (5 storms) as descriptive only. Subsets: all rows, flood windows (6 h before rise onset to the peak), rapid-rise windows, rising-water rows (Phase 1E definitions).
- **Pairs:** C versus A on folds 1-6 (primary); B, D versus A and D versus B, C on the folds where both are defined, with A and C re-reported on those folds.
- **Strata:** all events; upstream-led; local-or-downstream-led; ambiguous (reported separately, never pooled into either firm class); official events listed individually.
- **Primary outcome (pre-specified):** seed-mean flood-window RMSE at the **1 h and 3 h horizons** (the horizons where the information gap lies); 15 min and 30 min are reported but not primary, to limit forking paths.
- **Uncertainty:** paired storm-cluster bootstrap (2,000 resamples; seed-averaged replicates) as in Phase 1E for all-row and pooled subsets; per-seed and per-fold values; **per-event paired ratios (RMSE of X over RMSE of Y) for every event in the strata**. Intervals in strata with fewer than 10 clusters are shown but not used in any rule (3.9 and section 4).
- **Pre-registered decision rule (defaults; guide to confirm, question 10).** X "consistently improves" on Y in stratum S at horizon h if (i) the pooled paired flood-window RMSE difference over S is negative and at least 5% of Y's RMSE, (ii) it is negative in at least two thirds of S's events, and (iii) it is negative for all three seeds. "Consistently degrades" is the mirror image. Otherwise "no consistent difference". **Harm check:** for every added-input configuration, the upper 95% bound of the all-row paired difference at every horizon must not exceed +2% of A's RMSE, else it is flagged. The margins (5% and 2%) are chosen from the scale of the Phase 1E differences (0.9% to 1.9% of the 24 h error at the pooled level, with seed-level values from about -0.5% to +2.6% at 3 h in flood windows) and are not tuned on any result of this plan. **Nothing is adopted automatically; the default stays hydrology-only until the guide decides.**
- **Negative controls and sanity checks:** the shuffled-upstream control (section 2, optional); the local-or-downstream stratum under C (H2); the A runs must reproduce Phase 1E 24 h predictions to within numerical tolerance if the row set is the same (as `E7` did for Phase 1D), or the differences must be explained.

### 3.10 Forecasting metrics and event-detection metrics
- **Forecasting:** RMSE and MAE per horizon and subset in feet, per seed and seed-mean, with the paired differences above; skill versus persistence; per-fold and per-event window RMSE; peak-capture ratio for the 18 events (descriptive).
- **Event detection:** the Phase 1A fixed alarm rule (1 h hysteresis, 1 h matching tolerance) on the regression forecasts, for the experimental targets (stage >= 10 ft; rises >= 4 and >= 8 ft per 3 h) **and separately and descriptively** for the official stages. Per seed (mean [min-max]): early hits, late detections, misses, false-alarm episodes, median lead time, always with the number of events and storm clusters beside it (as in `E6b`). Only 6 official events from 5 storms exist, so no detection claim is made for them.
- **Onset timing:** the onset-timing diagnostic completed for Phase 1E (`docs/PHASE1E_ONSET_PROTOCOL.md`, `reports/PHASE1E_ONSET_TIMING.md`, code `src/flashflood/onset.py`) is the intended secondary evidence on whether added inputs change *when* the model responds: the key quantities are the lead and lag at 10%, 50% and 90% of the rise and the issue time of the first forecast of half the rise relative to the rise onset (baseline for A: no forecast of half the rise before the onset in any of the 18 events). Its definitions are reused unchanged if the guide approves; its 0.5 ft pre-onset flag is not used as evidence because it did not separate anticipation from reaction to the first uptick.
- Improvements in regression error are not read as improvements in detection or lead time, and no warning capability is claimed.

### 3.11 Data-leakage risks and safeguards
| Risk | Safeguard | Test to write |
|---|---|---|
| Hourly rainfall total for the hour ending after the issue time enters a row | availability rule: hour ending HH:00 usable from HH:00 + L (L = 0 primary, 1 h sensitivity) | change all rainfall after t to extreme values; features at t unchanged |
| Daily gauge total of day D used before 15:00 UTC on D | existing causality rule | same perturbation test on the daily features |
| Upstream reading stamped after the issue time | only stamps <= t; 15-min grid rule (3.3) | corrupt upstream values after t; model inputs at t unchanged |
| Archived NWIS values edited with later information (spike removal, shifts applied backwards) | disclosed as research-mode; no feature uses differences between versions; provisional flags retained | check that provisional-flagged rows are carried to the report; document, cannot be eliminated |
| Normalisation statistics from validation or test blocks | per-fold statistics from training windows only, separately for each channel group | assert statistics unchanged when held-out values are altered |
| Event class (3.6) uses post-event information | class used only to stratify evaluation; class columns absent from the feature matrix; table frozen with a hash | assert no class field reaches the model; assert hash unchanged at analysis time |
| Gauge or zone chosen using the evaluated events | all seven gauges, fixed set; single-gauge variants labelled post hoc | assert the configuration file lists the pre-registered set |
| Absolute upstream stage identifies the era (datum step at Comfort in 2011) | relative stage, change and elevation above own causal 7-day minimum only | shifting a gauge's stage by a constant leaves all its features unchanged (relative stage, change and elevation above the causal minimum are shift-invariant; a step inside the 7-day minimum window perturbs the last feature for up to 7 days, to be documented) |
| Longer input window than the embargo covers | embargo >= window + 3 h + one step for every channel group | assert embargo against the configured windows |
| Hyperparameters tuned on test results | hidden size 64 and all settings inherited; none tuned in this plan (the inherited values came from Phase 1C validation; mild look-ahead for early folds, as already disclosed) | config equality assertions across A-D |
| Rainfall product built with gauge data that also validates it | validate against the daily gauge product only as a plausibility check, not as independent truth; compare the radar-only product if available | n/a (documentation) |
| Shared fitting of a bias correction across folds | no bias correction in the primary run | n/a |
| Choosing metrics or strata after seeing results | primary outcome, strata, margins and decision rule fixed here; deviations logged | n/a (protocol deviation log) |

### 3.12 Limitations and expected research challenges
- **Very few upstream-driven events:** 6 events from 5 storm clusters (3 official-stage events: one in each of 2016-05, 2025-07 and 2026-07; two provisional). Under B and D only three events in three clusters (folds 5-6).
- **Dropouts at the worst time:** in the window of 2025-07-05, 3 of 8 upstream gauges were below 80% coverage; 2 in 2018-10-17.
- **Class sensitivity:** with a stricter trigger only 4 of 18 events have a >= 6 h lead; multi-pulse storms (2016-05, 2026-07) make timing ambiguous.
- **Rainfall product issues:** unvalidated against this basin's storms; timing convention unverified; product name and probably algorithm change between 2019 and 2021 (3.3); training record only 0.65 to 7.65 years in folds 4-6; ERA5 failed here, so a radar failure is possible; gauge-corrected radar may not be available in real time (research mode only).
- **One catchment, one gauge, one model family, three seeds, retrospective cross-validation:** no transfer or operational claim. No multiplicity correction across the many strata, horizons and configurations (the primary outcome limits this but does not remove it).
- **More inputs, same data volume:** C adds 21 per-step channels and 14 side inputs to 3 and 2 (3 + 7 x 3 channels; 2 + 7 x 2 side), which can overfit 14 clusters; the shuffled control and the harm check are meant to expose this.
- **Compute:** small (section 5), but any change in window length or number of seeds multiplies it.
- **Expected null results are plausible:** the Phase 1D/1E history shows that added modelling capacity or context did not help; the protocol is designed so that a null result is informative (effect-size estimates per event), not a failure.

## 4. Sample size and power: stated plainly
Six upstream-led events from five storm clusters **cannot give a statistically significant result** for any reasonable rule: an exact two-sided sign test on 6 events has a smallest attainable p-value of 2 x 0.5^6 = 0.031 (all six agree), and counting the five independent clusters it is 2 x 0.5^5 = 0.0625, which is above 0.05; the cluster bootstrap with five groups is unreliable. For B and D (three events in three clusters) the smallest two-sided p-value is 2 x 0.5^3 = 0.25. The strata are also not independent samples of storms: two upstream-led events (2016-05-29, 2016-06-02) share storm cluster 33 with two ambiguous events (2016-05-18, 2016-05-19), and cluster 27 holds one ambiguous and one local-or-downstream event (2015-05-17, 2015-05-23). The analysis is therefore framed as **effect-size estimation**: per-event paired ratios, per-seed and per-fold consistency, and the directional rule of section 3.9, reported with event and cluster counts. Secondary analyses (single-gauge variants, 48 h upstream window, 2 ft trigger sensitivity of the classes, complete-input rows, latency L = 1 h, Bergheim added, ridge with the same inputs) are **pre-specified only as labelled secondary analyses and will be run only if the guide approves them**; they do not enter the decision rule.

## 5. Staged execution plan (every gate needs explicit approval)
Effort figures are my estimates for one student, not measurements; the only measured compute is Phase 1E (median 1.8 min per 24 h GRU run).
| Stage | Content | Estimate | Gate to proceed |
|---|---|---|---|
| 0 | Guide reviews this draft and decides section 6; the class table and decision rule are frozen (hash) | guide's time | written decisions; **no compute** |
| 1 | Data: download full-record stage for the 7 gauges with full re-query handling (errors never swallowed), 15-min grid rule, gap statistics; fetch NLDI catchments for rainfall zones; download and **validate the hourly QPE** against the daily gauge product on the 2015-05 and 2016-05 floods (where ERA5 failed) and check timestamps, units, product-name continuity | 4-6 working days (archive volume not assessed) | validation report; go/no-go for B and D |
| 2 | Builders and tests (section 8): availability rule, masks, relative/anomaly channels, row-identity and leakage tests; dry run on one fold, one seed, with outputs deleted and logged as in Phase 1E | 3-4 working days | all tests pass; guide informed of the dry-run deviation log |
| 3 | Run: A and C on six folds, B and D on folds 5-6 (fold 4 extra), seeds 0-2: A 18 + C 18 + B 6 + D 6 = 48 runs (+6 if fold 4 is run for B and D; +18 for the shuffled-upstream control on six folds); extra input channels may raise run time above the 1.8 min measured for A (not measured) | roughly 1.5 to 6 hours of compute if a run takes 2 to 7 minutes (only the 1.8 min for A is measured) | none until stage 2 gate |
| 4 | Evaluation with the pre-registered rule; per-event tables; report with limitations | 3-4 working days | report reviewed by the guide |
| 5 | Decision about the central claim and any hybrid work | guide | not part of this protocol |

## 6. Questions requiring the guide's decision (with my current default)
1. May the central claim be reframed to "does upstream context change forecasts, and for which floods", keeping any hybrid for later? **Default: yes; the hybrid remains deferred.**
2. Run this experiment before any hybrid, with the fixed GRU 24 h? **Default: yes.**
3. Should ridge H, the strongest baseline, also be run with the same added inputs as a cheap linear control? **Default: yes (no deep model needed).**
4. Gauge set for C and D: all seven long-record gauges (default), a single gauge, or main-stem gauges only; Bergheim excluded from the primary set. **Default: all seven.**
5. Stage only, or stage plus discharge for upstream gauges (discharge as an *input* is not discharge forecasting)? **Default: stage only.**
6. Rainfall source for B and D: the public hourly radar+gauge archive (default), NLDAS-2 (needs the user's own Earthdata login), or the radar-only product; and whether B and D may be limited to folds 5-6. **Default: archive product, folds 5-6, fold 4 as an extra.**
7. Rainfall availability assumption: research mode with L = 0 and L = 1 h sensitivity, labelled non-operational. **Default: yes.**
8. Input window: keep 24 h for all channel groups (default), or allow 48 h for upstream channels as a secondary variant (needs a new embargo).
9. Keep the four horizons (default) or add longer ones (6 h, 12 h) for upstream experiments, which would change the project's scope. **Default: keep.**
10. Decision-rule margins (5% benefit, 2% harm), two-thirds of events, all three seeds, primary horizons 1 h and 3 h; and whether to run the shuffled-upstream control (18 extra runs). **Default: as in section 3.9, control yes.**
11. Rainfall zones: two zones (above and below Comfort) or three (adding Comfort to Bergheim, 264 sq mi) or finer. **Default: two.**
12. Causal fill limit for upstream gauges: 4 steps as for the target, or none. **Default: 4 steps.**
13. Classification rule: both timing rules, thresholds 6 h and 1 h as in 3.6, and the labelling of 2016-05-19 and 2024-07-24 as ambiguous. **Default: as written.**
14. Scope of the early-warning claim: restrict it to events with an upstream signal and state that stage-based models cannot warn for the rest? **Default: yes.**
15. Is a literature review (to be added by the guide or student) required before approval?

## 7. Assumptions, deviations and what would change my mind
**Assumptions.** The Phase 1D folds, the 24 h GRU and the Phase 1E code are reused unchanged. Gauge stage values at 15-min marks are representative of 5-min readings. The hourly radar product is usable as archived. Timing rules v2 and v3 are acceptable descriptive tools.
**Deviations from earlier phases (all logged here).** (1) The supporting analysis recomputed the upstream timing on a 15-min grid and added four gauge-event series re-queried from NWIS because the earlier cache lacked them (the original fetch swallowed errors; the series exist). The earlier tables and documents are unchanged and both versions are reported; no event class changes (`S8`, `S6b`, `reports/upstream_protocol_support/README.md`). (2) The one-time public-service probes used the network (index pages of a public archive; one NWIS query per missing gauge-event; no personal data). (3) Documents that said "92-station" (`docs/GUIDE_BRIEF.md`, `docs/UPSTREAM_INPUT_FEASIBILITY.md` section 4) disagreed with `reports/gauge_rainfall/README.md` (187 stations inside the basin; 58 to 77 reporting on the event days in `S1`); the wording was corrected afterwards by the project owner's assistant (see the addendum at the end of `docs/UPSTREAM_INPUT_FEASIBILITY.md`).
**What would change my mind.** The 15-min-grid recomputation or a later radar-based check reclassifying several events; a failed rainfall validation (then B and D are dropped or deferred); the A re-run not reproducing the Phase 1E 24 h results; C helping local-or-downstream events as much as upstream-led events (suspect leakage or an era proxy); the shuffled control retaining the benefit; gauge dropouts masking most inputs in exactly the large events; or a guide preference for a different estimand (for example a different horizon set).

## 8. Reproducibility and artifact plan
- **Experiment ids:** new ids in `experiments/REGISTRY.md` for (a) this protocol and its support tables (documentation), (b) the A-D comparison when approved (suggested prefix `UI`, to be assigned by the project owner; this draft does not edit the registry).
- **Folders:** supporting tables `reports/upstream_protocol_support/`; experiment outputs in a new `reports/upstream_inputs/` with runs `fold{k}_gru_cfg{A|B|C|D}_w24h_h64_s{seed}` (configuration, history, checkpoint with SHA-256, predictions, manifest) as in Phase 1E; frozen class table with hash; protocol copy with deviation log. No Phase 1C-1E artifact is touched; existing predictions are read-only references.
- **Scripts (proposed):** `fetch_upstream_full.py` (no swallowed errors), `build_upstream_features.py`, `run_upstream_inputs.py`, `eval_upstream_inputs.py`, reusing `src/flashflood/{seq,dl,folds,metrics,experiment,events}.py`.
- **Tests to add before any training** (`tests/test_upstream_inputs.py`): the table in 3.11 (causality perturbations for stage, hourly rainfall and daily rainfall; constant-shift invariance; 15-min grid; per-fold statistics; embargo versus windows; no class field in features; identical rows and folds across A-D; configuration equality except for input width; reproduction of Phase 1E 24 h predictions by A).
- **Reproduce the support tables:** `.venv/bin/python scripts/build_upstream_protocol_support.py` (offline) and `.venv/bin/python -m pytest -q tests/test_upstream_protocol_support.py`.
