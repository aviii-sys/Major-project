# Phase 0 Report: Data Audit for Flash-Flood Forecasting at USGS 08167500

Station: Guadalupe River near Spring Branch, TX (NWS id SRGT2). Audit run: 2026-11-22 (UTC).
Scope: Phase 0 only. No model was trained and no model metric was computed. Everything below is descriptive statistics of observed data plus documented source facts. Items I could not verify are marked **[UNVERIFIED]**.

Reproduce: `scripts/fetch_meta.py` -> `scripts/fetch_usgs.py --start 2007-10-02` -> `scripts/fetch_openmeteo.py --dataset precip|land --start 2007-10-02 --end 2026-11-15` -> `scripts/audit_phase0.py`. Raw-file checksums: `data/raw/MANIFEST.sha256`. Package versions: `requirements.lock`. All tables referenced are in `reports/phase0/tables/`, figures in `reports/phase0/figures/`, machine-readable numbers in `reports/phase0/phase0_results.json`.

## Headline findings

1. **The 2007-10-02 to 2026-11-22 record is good quality** (99.55% of 15-min stage values present), and it contains the 2015 and 2025-07-05 floods as continuous 15-min data.
2. **There are very few official flood events.** Using NWS categories on this record: action stage (25 ft) reached in 6 events (5 independent storms), minor flood (30 ft) in 4, moderate (36 ft) in 1, major (39 ft) in 0. This is not enough for event-based evaluation at official thresholds alone (section 7).
3. **The old thresholds (2.175 / 2.260 ft) must be discarded.** Over the full record the river is above 2.175 ft in 50.9% of rows. They are roughly the median, not a flood level. Official flood stages are 25/30/36/39 ft.
4. **Rainfall source is the weakest link.** NLDAS-2 (preferred) could not be downloaded (needs a NASA Earthdata login). The substitute, Open-Meteo/ERA5 reanalysis rainfall, is physically inconsistent with the flood timing in 2 of 6 events (E01, E03). Both candidate sources are retrospective (about 4 to 5 days of latency) and cannot drive a live system.
5. **Hourly rain cannot inform the 15 and 30 minute horizons** beyond what the hydrograph itself shows (section 4).

## 1. Hydrological data coverage and quality

Source: USGS NWIS instantaneous values, parameters 00065 (gage height, ft) and 00060 (discharge, ft3/s). Stage IV data starts 2007-10-02 (series catalogue); discharge IV starts 1986-10-01.

| Item | Result |
|---|---|
| Range | 2007-10-02 05:00 UTC to 2026-11-22 06:00 UTC |
| Rows / expected 15-min steps | 668,307 / 671,141 |
| Off-grid timestamps, duplicates | 0, 0 |
| Dominant step | 15 min (668,122 of 668,306 intervals); other steps are gaps |
| Missing stage / discharge | 3,022 (0.45%) / 2,834 (0.42%) |
| Gap runs (stage) | 186; 89 are >= 1 h; 15 >= 6 h; 13 >= 24 h; longest 96 h (2008-10-11, 2009-07-24) |
| Worst years | 2008 (95.6% complete), 2009 (98.9%); all others >= 99.4% |
| Approved vs provisional (stage) | 638,199 approved (A); **29,920 provisional (P), all from 2026-01-12 on**; 188 rows with no qualifier (2020-04-13 to 2020-07-20, stage only) |
| Estimated discharge ("e") | 196 rows |

Other quality checks:
- **Negative stage is normal** (39,096 rows, min -1.23 ft); it reflects the gauge datum, not an error.
- **Zero discharge in 44,165 rows (6.6%)**, with stage up to 1.1 ft at zero flow. In 2022 to 2024, 2,355 rows sit at a flat stage floor of about -1.22 ft (all with Q = 0): dry channel or sensor floor **[UNVERIFIED which]**. These periods should be masked or labelled, not treated as normal variation.
- Stage-discharge consistency: median discharge in a fixed stage band (2.45 to 2.95 ft) is 115 to 195 cfs across years, so no gross rating shift at low flow (`hydro_rating_drift_check`). This does not test high-flow ratings.
- Largest 15-min jumps (up to 4.25 ft) all fall inside the real flood rises of 2015-05, 2015-10, 2025-07 and 2013-10; only 3 jumps exceed 3 ft. No isolated spike pattern was found, but I did not individually validate them against another sensor.

Figures: `fig1_coverage.png` (monthly completeness), `fig2_hydrograph.png`, `fig3_annual_max.png`.

## 2. Rainfall and weather sources

### 2.1 NASA NLDAS-2 (NLDAS_FORA0125_H), the preferred source: NOT ACQUIRED

Verified: hourly, 1/8 degree (0.125), 1979 to present, latest granule 2026-11-18 12:00 UTC (NASA CMR catalogue). Downloads redirect to NASA Earthdata login (HTTP 302); no credentials exist on this machine. The point-extraction service (Hydrology Data Rods) is being discontinued (NASA notice). Gridded downloads would need OPeNDAP or a subsetting service because 19 years of global files is impractical.
**[UNVERIFIED]** I did not read how NLDAS-2 derives precipitation (the catalogue text I read only states that non-precipitation fields come from NARR) or confirm that soil moisture lives in the separate NOAH product (NLDAS_NOAH0125_H). Check the product documentation before relying on either.
To proceed you would create a free Earthdata account and place the credentials in `~/.netrc` yourself. Do not paste them into chat.

### 2.2 Open-Meteo (ERA5 / ERA5-Land): acquired, with caveats

From Open-Meteo's own documentation (fetched 2026-11-22): ERA5 is 0.25 degree (about 25 km), hourly, 1940 to present, with a 5 day delay. ERA5-Land is 0.1 degree (about 11 km), hourly, with a 5 day delay. **ERA5-Land does not provide precipitation in this API**; precipitation comes from ERA5. I confirmed this empirically: requesting `era5_land` precipitation returned 100% null. Hourly precipitation is the "sum of the preceding hour". The page does not state explicitly that the timestamp is the end of that window; I assumed it is (consistent with E04 below) **[UNVERIFIED]**.

| Property | Result |
|---|---|
| Basin | USGS NLDI polygon, area 1,316 sq mi (USGS lists 1,315) |
| Rainfall cells | 13 ERA5 0.25-degree cells overlap the basin; area-weighted; 4 central cells hold 68% of the weight; no NaN hours, 2007-10-02 to 2026-11-15 23:00 |
| Rainfall stats | annual basin means 396 to 894 mm (2008 to 2025); 9.6% of hours > 0.1 mm; max hourly 20.3 mm |
| Land variables (soil moisture 3 layers, 2 m temperature, humidity) | 53 ERA5-Land 0.1-degree cells overlap the basin. **Only 15 of 53 were downloaded at report time (download still running, resumable)**. Any basin mean from them is spatially biased and is not used in this report's conclusions. |
| Licence | CC BY 4.0; free tier is non-commercial only; limits 600/min, 5,000/hour, 10,000/day. Cite Zippenfenig (2023), Open-Meteo.com Weather API, Zenodo, doi:10.5281/ZENODO.7970649; "Generated using Copernicus Climate Change Service information"; Hersbach et al. (2023) ERA5 hourly data on single levels; Muñoz Sabater (2019) ERA5-Land. |

**Spatial note:** area weighting at 0.1 degree for rainfall would be false precision, so rainfall uses the native 0.25 degree grid. The basin is only about 5 ERA5 cells wide, so sub-basin rainfall structure (which matters for flash floods) is not resolved.

### 2.3 Does the rainfall source reproduce the flood-producing rain? (`events_vs_rainfall`, `fig5_event_panels.png`)

| Event | Peak (UTC) | Stage ft | ERA5 basin rain 24 h / 72 h before peak (mm) | Consistent with rise timing? |
|---|---|---|---|---|
| E01 | 2015-05-24 03:45 | 34.5 | 5.4 / 18.2 | **No**: heaviest ERA5 rain (about 20 mm on 05-25 UTC) comes after the peak |
| E02 | 2015-10-30 15:00 | 30.1 | 32.8 / 32.8 | Yes: rain and rise coincide |
| E03 | 2016-05-30 02:45 | 26.1 | 0.6 / 7.5 | **No**: heaviest ERA5 rain (26 mm on 05-31 UTC) comes after the peak |
| E04 | 2025-07-05 09:45 | 30.0 | 65.5 / 94.6 | Yes: rain peak 12 h before crossing |
| E05/E06 | 2026-07-15 / 07-17 | 25.0 / 36.8 | 30.0 / 101 and 12.4 / 104 | Plausible: one storm from 07-14 |

Also: of the 25 largest 24 h ERA5 basin-rain episodes, only 2 were followed by stage >= 25 ft. The largest (108 mm, 2025-06-12) peaked at 8.4 ft (`top_rain_episodes_vs_river_response`). Causes could be reanalysis error, spatial structure, antecedent wetness, or timing; I cannot separate them here.

### 2.4 Selected source

**Provisional: Open-Meteo ERA5 for rainfall, ERA5-Land for soil moisture/temperature/humidity, with NLDAS-2 as the intended upgrade.** This is a pragmatic choice because it is the only source I could obtain, not a validated one. Before Phase 1 rainfall features are trusted, I recommend validating against a gauge- or radar-based product (NLDAS-2, or an alternative such as MRMS/Stage IV **[not evaluated]**).

## 3. Data dictionary (draft aligned table `data/processed/aligned_15min_DRAFT.csv.gz`)

| Column | Unit | Meaning |
|---|---|---|
| index (UTC) | ISO 8601 UTC | 15-min grid, 2007-10-02 05:00 to 2026-11-22 06:00 |
| stage_ft | ft | USGS gage height (datum per USGS); NaN when missing |
| q_cfs | ft3/s | USGS discharge; 0 is real zero flow, NaN is missing |
| stage_cd, q_cd | code | USGS qualifier: A approved, P provisional, "e" estimated |
| stage_observed | bool | True if stage was measured at this step |
| wx_hour_utc | UTC | hourly weather label used: latest label <= row time (causal) |
| rain_age_min | min | row time minus wx_hour_utc: 0, 15, 30 or 45 |
| precip_mm_1h | mm | area-weighted basin mean ERA5 precipitation, preceding-hour sum; NaN after 2026-11-15 23:00 |
| soil_moisture_*, temperature_2m, relative_humidity_2m | m3/m3, C, % | ERA5-Land basin means; **partial-cell, do not use yet** |

Local time at the gauge is CST/CDT; every timestamp here is UTC.

## 4. Missing data and synchronisation

**Rule used:** no interpolation or repetition of hourly values as independent rainfall. Each 15-min row carries the latest completed hourly value and its age (`rain_age_min`, uniformly 25% each of 0/15/30/45). Missing measurements stay NaN with an observed flag.

| Issue | Size |
|---|---|
| Rows with stage missing | 3,022 (0.45%) |
| Rows with no rainfall (record ends 6 days before hydrology, ERA5 delay) | 601 rows, 2026-11-16 to 2026-11-22 |
| Weather NaN inside the history | 0 (reanalysis is gap-free) |
| Zero-flow / sensor-floor rows | 44,165 / 2,355 |

**Effect on the 15 and 30 minute horizons.** The newest rainfall value at issue time covers a window that ended up to 45 minutes earlier, and no source tells us the rain that will fall in the next 15 or 30 minutes. The hydrology is fast: from first crossing 25 ft to peak took 0.25 to 5 h; rise onset to peak 4 to 17 h (47 h for the double crest); the fastest 15-min rise was 17 ft/h (2025-07-05) and the largest 3 h rise was 23 ft. So the 15 and 30 min horizons will be driven almost entirely by the stage/discharge history, and hourly reanalysis rain can contribute mostly at 1 h and longer. This is a reasoned inference from these statistics, not a tested result. Horizon 2 to 3 h is where rainfall inputs matter most, which is exactly where ERA5 reliability is weakest (2.3).

**Real time.** ERA5 has a 5 day delay and the newest NLDAS-2 granule was 4 days old, so neither can feed a live forecast. A "real-time" prototype can only be a historical replay unless a different live rainfall input is chosen **[options not evaluated]**.

## 5. Verified flood-event catalogue (`event_catalogue_action_stage`)

Method: contiguous periods with stage >= 25 ft, merged if separated by < 24 h; rise onset = last time stage was within 0.5 ft of the preceding 72 h minimum. Annual peaks (USGS peak file) were checked against the continuous record, not assumed to have 15-min data.

| ID | First >= 25 ft (UTC) | Peak (UTC) | Peak ft / cfs | h above 25 ft | Onset to peak h | Max 15-min rise ft/h | Max 3 h rise ft | Highest NWS category |
|---|---|---|---|---|---|---|---|---|
| E01 | 2015-05-24 01:15 | 2015-05-24 03:45 | 34.50 / 59,800 | 22.3 | 7.5 | 8.6 | 20.8 | minor |
| E02 | 2015-10-30 14:15 | 2015-10-30 15:00 | 30.06 / 43,100 | 2.5 | 4.0 | 16.9 | 23.3 | minor |
| E03 | 2016-05-30 01:15 | 2016-05-30 02:45 | 26.07 / 33,200 | 4.0 | 7.8 | 7.0 | 12.7 | action |
| E04 | 2025-07-05 06:15 | 2025-07-05 09:45 | 30.03 / 35,000 | 10.5 | 6.8 | 17.0 | 22.2 | minor |
| E05 | 2026-07-15 23:00 | 2026-07-15 23:15 | 25.04 / 24,200 | 0.5 | 17.3 | 4.3 | 12.0 | action |
| E06 | 2026-07-17 00:30 | 2026-07-17 05:30 | 36.75 / 54,000 | 15.0 | 47.5 | 6.8 | 17.3 | moderate |

- **E05 and E06 are two crests of one storm** (they merge at 48 h separation; 5 independent events at that setting). **E05 and E06 are provisional (P) data** and may be revised by USGS.
- Time from first crossing of action stage to minor stage: 0.75 h (E01, E02), 3.5 h (E04), 1.25 h (E06); E03 and E05 never reached minor. Time minor to moderate (E06): 2.5 h. Observed-stage warnings anchored on these categories leave under 4 hours of lead, so useful lead time must come from forecasting.
- **2015 and 2025-07-05 are both present** as continuous 15-min data (observation fraction 1.0 around both).
- **The 2007-08-17 peak (33.68 ft, 56,400 cfs) predates stage IV data (2007-10-02) and is not covered.** The 2018-10-17 peak (24.37 ft) is just under action stage.
- For every annual peak from 2007-10 to 2025, the IV maximum equals the USGS peak value (`annual_peaks_vs_iv_record`), consistent with the peaks being derived from the same record.
- Caveat: these events are defined by stage threshold only. I did not cross-check them against NWS storm reports or impact records **[UNVERIFIED as damaging floods]**.

## 6. Flood stages and warning-threshold recommendations

Official source: NWS NWPS gauge SRGT2 (same station: USGS id 08167500, same coordinates). Categories in feet: **action 25, minor 30, moderate 36, major 39**. NWS flow equivalents are not published (-9999). Stage values on the NWS historic crest list (e.g., 45.25 ft in 1978) equal the USGS peak file, so the stage scale is consistent between the two sources. "Action" is a preparedness level; the first flood category is minor (30 ft).

Recommendations (for your review, not applied):
1. **Discard 2.175 / 2.260 ft / 0.0075 per hour.** They are about the median of the full record and the rise-rate unit is ambiguous.
2. **Anchor official categories to NWS stages** for any warning evaluation: Watch >= 25 ft, Warning >= 30 ft, Critical >= 36 ft, reported descriptively only (n = 6, 4, 1 events).
3. **Use non-official development tiers for training/model selection**, clearly labelled prototype and chosen by event availability, not hydrology: stage >= 10 ft (20 events), >= 15 ft (9), and rapid-rise episodes of >= 4 ft in 3 h (27) or >= 8 ft in 3 h (15).
4. Final warning thresholds can only be tuned for detection versus false alarm if enough events exist (section 7); with the current count they remain prototype values.

## 7. Event distribution and split suitability (`event_counts_by_threshold`, `event_counts_by_year`, `split_event_counts`, `fig4_event_counts.png`)

Independent events by threshold (24 h separation): >= 5 ft 49; >= 8 ft 24; >= 10 ft 20; >= 15 ft 9; >= 20 ft 6; **>= 25 ft 6; >= 30 ft 4; >= 36 ft 1; >= 39 ft 0**. Rapid rise in 3 h: >= 1 ft 89; >= 2 ft 53; >= 4 ft 27; >= 8 ft 15. Results are stable to separation of 12 to 72 h except at 25 ft (6 to 5).

Candidate chronological splits (train | validation | test), event first-crossing dates:

| Event definition | A: <=2017 / 2018-21 / 2022+ | B: <=2019 / 2020-22 / 2023+ | C: <=2016 / 2017-20 / 2021+ |
|---|---|---|---|
| >= 10 ft | 11 / 5 / 4 | 15 / 1 / 4 | 11 / 4 / 5 |
| >= 15 ft | 5 / 2 / 2 | 6 / 1 / 2 | 5 / 1 / 3 |
| >= 25 ft (action) | 3 / 0 / 3 | 3 / 0 / 3 | 3 / 0 / 3 |
| >= 30 ft (minor) | 2 / 0 / 2 | 2 / 0 / 2 | 2 / 0 / 2 |
| rapid >= 4 ft/3 h | 14 / 6 / 7 | 18 / 2 / 7 | 14 / 4 / 9 |
| rapid >= 8 ft/3 h | 9 / 1 / 5 | 9 / 1 / 5 | 9 / 0 / 6 |

Assessment:
- **At official action stage and above, the data are not sufficient for a train/validation/test event evaluation.** Validation has zero events in every split, and the test set holds 3 action events that are only 2 independent storms. With 3 test events, recall can only be 0, 1/3, 2/3 or 1, and even 3 of 3 detected gives an exact (Clopper-Pearson) two-sided 95% interval for recall of roughly 29% to 100% (lower bound = 0.025^(1/3)). Compute the intervals you report with an exact binomial method.
- Lower-tier definitions (>= 10 ft, rapid rise) give usable counts, but the validation set is still thin (1 to 6 events).
- Hydroclimate is not stationary over splits: 2022 to 2023 had no events above 5 ft, while 2025 to 2026 hold 3 of the 6 action events, so a chronological test set is dominated by the wettest recent years.

## 8. Limitations and methodology recommendations

Limitations
- Single catchment; 6 official-stage events (5 storms); only 1 event reaches moderate; none reaches major.
- Rainfall is reanalysis, coarse (0.25 degree), inconsistent with 2 of 6 events, and not available in real time.
- NLDAS-2 not yet obtained; soil moisture/temperature/humidity incomplete (15 of 53 cells).
- 2026 data are provisional and may change.
- The 15 and 30 minute horizons will be mostly stage-driven (inference, to be tested in Phase 1).
- Threshold choices for development tiers are availability-driven, not hydrological.

Recommendations (decision needed from you)
1. **Extend the event history using discharge-only IV before 2007-10.** I verified 15-min discharge IV at samples from 1997-06 and 2002-06/07 (1987-07 was only hourly, a mixed-resolution record); the annual peak file lists 1997 (116,000 cfs), 2002 (94,400 cfs) and 2007-08 (56,400 cfs) floods. This would add large events but requires a discharge-based target and continuity checks, **[not yet done]**.
2. **Use blocked evaluation with whole events held out** (rolling-origin or leave-one-storm-out), report counts with exact confidence intervals, and treat official-category results as descriptive.
3. **Obtain NLDAS-2 (or another gauge/radar rainfall product)** and re-run the section 2.3 consistency check before trusting rainfall features.
4. **Mask zero-flow/sensor-floor periods and provisional 2026 data** (or hold 2026 out of training).
5. Consider a second catchment only if it has comparable event counts; otherwise state the single-station limitation.
6. Label the prototype a historical replay system, not a real-time one, unless a live rainfall feed is chosen.

## Addendum (2026-11-22, written during Phase 1A): corrections to this report
- **Section 8, recommendation 1 was wrong in its evidence.** I wrote that 15-min discharge was verified for 1997 and 2002. That check looked only at short samples around the flood dates and confirmed 15-min spacing; it did not check that the flood peaks were present. They are not: the 15-min record stops during the rising limb in both years and has no samples on the main flood days (see `reports/PHASE1A_REPORT.md`, section 1). The 1997 and 2002 floods fail the continuity audit and are excluded.
- **Section 2.3:** the follow-up gauge comparison (`reports/rain_validation/`) shows ERA5 misses the 2015-05 and 2016-05 storms by roughly an order of magnitude and misplaces them, rather than merely shifting them in time.
- **Section 5:** the Phase 0 event catalogue is unchanged.

## 9. Scripts delivered

| Script | Purpose |
|---|---|
| `scripts/fetch_meta.py` | station info, series catalogue, NLDI basin, NWS gauge record, annual peaks |
| `scripts/fetch_usgs.py` | chunked, resumable USGS IV download (stage, discharge, qualifiers) |
| `scripts/fetch_openmeteo.py` | resumable per-cell ERA5 rainfall (`--dataset precip`) and ERA5-Land (`--dataset land`) download |
| `scripts/audit_phase0.py` | all tables, figures, results JSON, and the draft aligned table |
| `scripts/audit_hydro.py` | superseded early 2022-2023 check; its thresholds are obsolete (kept only for history) |
