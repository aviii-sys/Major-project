# Data-availability and feasibility assessment: additional predictive inputs for USGS 08167500

Written 2026-11-22 (Decision 3 of the Phase 1D review). **Descriptive only: no model was trained and no forecasting skill is claimed.** Question: is the main limitation of the current models (all trail sharp flood onsets by about 3 h) the absence of upstream predictive information, and which such inputs exist, for which events, and with what lead time? Scripts: `scripts/assess_upstream_inputs.py`; tables in `reports/upstream_feasibility/tables/`; raw listings in `data/raw/upstream/`.

## 0. Method and a correction to disclose
For each >= 10 ft event (all 20 in the catalogue, so 2 events outside the cross-validation are included here; the cross-validated 18 are reported separately) the 15-min stage at each long-record upstream gauge was fetched for [event start - 36 h - 24 h, event end + 18 h + 12 h] and two rise timings were measured identically at the upstream gauge and at 08167500: the **first** 3-hour stage rise of at least 1 ft and the **steepest** 3-hour rise. **Lead = time at 08167500 minus time at the upstream gauge** (positive: the upstream gauge rises first). A gauge "responds" if its 3-hour rise reaches 1 ft in the window; a pair is "consistent" if the two timings differ by at most 6 h.
**The first analysis run was invalid and is kept only as evidence** (`FIRST_RUN_INVALID_*.csv`): (1) gauges whose stage column is named like `00065_15-minute update` were silently dropped as "no data" (three of eight gauges returned nothing); (2) its "20% of amplitude" arrival time could be triggered by an earlier minor pulse and produced implausible leads of up to -30 h. Both were fixed in version 2 (all tables below are version 2). Validation: in the 2025-07-05 flood the two timing methods agree to within about 2 h at every responding gauge; over all 77 responding gauge-event pairs, 59 agree within 6 h and 18 do not, and only the 59 are used for lead statistics.

## 1. What exists upstream (verified from NWIS and NLDI)
The NLDI upstream navigation returns 33 NWIS sites, 14 of them with 15-minute (`uv`) series for stage, discharge or rain.
| Gauge | Drainage (sq mi) | 15-min stage | Events with usable data (of 20) |
|---|---|---|---|
| Guadalupe at FM 474 nr Bergheim (08167200) | 1,103 | since 2016-10-26 (discharge since 2019-10) | 6 |
| Guadalupe at Comfort (08167000) | 839 | 2007-10-01 on | 18 |
| Guadalupe nr Center Point (08166250) | 553 | 2007-10-06 on | 19 |
| Guadalupe at Kerrville (08166200) | 510 | 2007-10-01 on | 17 |
| Guadalupe abv Bear Ck at Kerrville (08166140) | 494 | 2007-10-01 on | 19 |
| Guadalupe at Hunt (08165500) | 288 | 2007-10-01 on | 20 |
| N Fk Guadalupe nr Hunt (08165300) | 169 | 2007-10-01 on | 20 |
| Johnson Ck nr Ingram (08166000) | 114 | 2007-10-01 on | 18 |
Target gauge: 1,315 sq mi. Other sites: tributary stage gauges exist (Honey Creek sites 2007-2014 with 0.35-0.53 sq mi; Cypress Ck at Saur Farm since 2023-09; S Fk Guadalupe at Lynx Haven since 2026-04), too short or too small to support the event record.
**Sub-daily rainfall is the scarce input:** USGS 15-min rain gauges inside the basin exist only for Hunt (since 2023-11-21), Johnson Creek (since 2025-05-12) and a few sites since 2026-07; Honey Creek rain gauges are daily and end in 2014.

## 2. Lead time of the upstream rise over Spring Branch (version 2; consistent pairs; descriptive)
Per gauge, all 20 events (`upstream_gauge_lead_summary.csv`): responds / consistent / median first-rise lead (range) / events with lead >= 3 h.
| Gauge | Responds | Consistent | Median lead h (range) | Lead >= 3 h |
|---|---|---|---|---|
| Bergheim (1,103) | 5 | 4 | 4.4 (0.8 to 8.3) | 2 |
| Comfort (839) | 12 | 9 | 13.0 (0.0 to 16.3) | 5 |
| Center Point (553) | 13 | 11 | 2.8 (-12.5 to 21.5) | 5 |
| Kerrville (510) | 8 | 7 | 15.8 (-9.5 to 20.5) | 4 |
| Kerrville abv Bear Ck (494) | 11 | 8 | 9.0 (-8.8 to 22.5) | 4 |
| Hunt (288) | 10 | 8 | 14.3 (-32.5 to 23.5) | 5 |
| N Fk nr Hunt (169) | 8 | 6 | 17.5 (-31.3 to 25.8) | 4 |
| Johnson Ck (114) | 10 | 6 | 0.4 (-7.5 to 22.8) | 2 |
Negative leads mean the Spring Branch rise began first: the rain fell nearer to Spring Branch than to that gauge. Wide ranges at one gauge mean the lead depends on where the storm fell.
**Per event, using the best consistent gauge (18 events cross-validated in Phase 1D; `upstream_event_level_lead.csv`):**
- 13 of 18 show a consistent response at some upstream gauge; **6 of 18 have a best lead of 6 h or more** (2016-06-02: 18 h; 2016-05-29: 16 h; 2018-10-17: 26 h; 2025-07-05: 20 h; 2026-06-15: 6 h; 2026-07-15/17: 19 h), 10 of 18 at least 1 h.
- **8 of 18 events would have given no usable upstream warning** (no consistent response or best lead under 1 h): 2012-01-25, 2013-10-31, 2015-05-23/24 (34.5 ft, best lead 0 h), 2015-10-30 (30.1 ft, best lead -1.5 h), 2016-05-19 (best lead 0 h), 2018-09-09, 2021-10-14 and 2024-07-24, because the rain fell downstream of the upstream gauges (or, for 2016-05-19, level with them). Four further events have best leads of only about 2-3 h (2015-05-17, 2016-05-18, 2018-09-22, 2019-05-08).
- Of the 6 official >= 25 ft events (5 storms): 2016-05-30, 2025-07-05 and 2026-07-15/17 have upstream leads of 16-20 h; 2015-05-24 and 2015-10-30 have none. One of them, 2015-10-30, had the lowest 3 h peak capture of the six official events in Phase 1D (peak ratio 0.25 to 0.44 across models).

## 2b. Robustness checks (run after the first write-up; `upstream_sensitivity.py`, `audit_upstream_gauges.py`)
**Sensitivity to my choices (18 cross-validated events; `sensitivity_trigger_and_tolerance.csv`).** Events with a consistent upstream response / best lead >= 3 h / best lead >= 6 h / no usable warning, for a rise trigger of 0.5, 1 (reported) and 2 ft per 3 h, with a timing-agreement tolerance of 6 h: 0.5 ft: 13 / 7 / 5 / 8; **1 ft: 13 / 6 / 6 / 8**; 2 ft: 10 / 5 / 4 / 12. Across all nine trigger-and-tolerance settings the count with a lead of at least 3 h ranges from 4 to 8 and the count with no usable warning from 7 to 13. So "about a third have a long upstream lead and about half have none" is reasonably robust, and a stricter trigger shrinks the long-lead group.
**River distance and a physical check (`upstream_gauge_lead_summary_with_river_distance.csv`).** Main-stem river distances above 08167500 from NLDI flowline geometry: Bergheim 52 km, Comfort 102 km, Center Point 130 km, Kerrville 140 km, Hunt 157 km, N Fk near Hunt 167 km. Implied flood-wave speeds from the median first-rise leads: Bergheim 3.3, Comfort 2.2, Kerrville 2.5, Hunt 3.1 and N Fk 2.6 m/s; from the longest lead (storms in the upper basin) Comfort 1.7, Kerrville 1.9, Hunt 1.9 m/s. These are realistic flood-wave celerities, which supports the timings. Center Point (13 m/s) and the Kerrville-above-Bear-Creek gauge (4.4 m/s) give unrealistic speeds from medians because their medians mix storms centred between gauges; medians are therefore not travel times.
**Gauge quality (daily values, 2007-2026; `upstream_audit_*.csv`).** Daily stage is present for 97.7% to 99.7% of days on average at the seven gauges that have it (worst single year 85.3%, Center Point; Bergheim has no daily stage and was not audited). **Datum or channel-control shifts:** the stage at matched low discharge shows a **+2.90 ft step at Comfort in 2011** (+2.2 ft net drift over the record), -1.34 ft at Johnson Creek in 2024 and +0.89 ft at Center Point in 2026 (possibly provisional data); the other four gauges show no step above 0.5 ft. My lead-time analysis uses rises, which these shifts do not affect, but **any model input built on absolute upstream stage would need rises, anomalies or a datum correction**, especially Comfort.

## 2c. A second anchoring (v3) and what the plots showed (`upstream_anchored_v3.py`, figures in `reports/upstream_feasibility/figures/`)
Visual inspection of the 14 plotted events showed that the v2 timing can anchor on a small earlier Spring Branch pulse: in 2024-07-24 Comfort rises about 17-19 h before the main pulse, but v2 reports no consistent response. A second definition (v3) anchors both gauges to the catalogued event's own rise (Spring Branch window [t0 - 12 h, t0 + 3 h], upstream window [t0 - 48 h, t0 + 3 h]). **v2 is not replaced; both are reported.** v3 reclassifies two events and itself fails on clustered storms: 2024-07-24 becomes a 24 h lead (supported by the plot), but 2016-05-19 (35 h) and the 2026-07-15 value (37 h versus 19 h in v2) are physically implausible, because the upstream window contains the pulse of an earlier storm of the same cluster. **So neither definition is reliable for multi-pulse storms, and the honest summary is a range: of the 18 events, 6 (v2) to 8 (v3, one of them implausible) have an upstream lead of at least 6 hours, and 6 to 8 have no usable upstream warning.** Consistent response at some gauge: 13 (v2) or 14 (v3) of 18.
**Gauges drop out during the largest floods.** In the plots, the Kerrville and Hunt traces in 2018-10-17 and 2025-07-05, and the Comfort trace in 2016-05-19, become straight lines across gaps in the record. In the v3 windows, 2 of the 8 upstream gauges had less than 80% coverage in 2018-10-17 and in 2025-07-05 (and 1 in 2015-05-17 and in 2016-05-19). A stage-based upstream input is therefore least reliable exactly in the extreme events where it would matter most, and any model using it would need a missing-input strategy and an evaluation of how it behaves during outages.

## 3. Other candidate inputs
| Input | Availability found | Covers the held-out events? | Status |
|---|---|---|---|
| Upstream river stage (above) | 15-min since 2007 at 7 gauges | 13 of 18 respond | **available now, free** |
| Radar QPE, MRMS on AWS (`noaa-mrms-pds`) | listing starts 2020-10-14 (verified) | 5 of 18 events (2021-10 on) | too short alone; the Iowa State archive below goes back further |
| Stage IV radar+gauge QPE | NCAR/EOL page reachable but its coverage could not be read | unverified | **[UNVERIFIED]** (the MRMS gauge-corrected product above is a comparable alternative) |
| **Radar QPE, Iowa State MRMS archive (`mtarchive`)** | **verified 2026-11-22:** `GaugeCorr_QPE_01H` and `RadarOnly_QPE_01H` (hourly, 24 files per day), 2-minute `PrecipRate`, for 2015-05-23/24, 2015-10-30, 2016-05-29 and 2018-10-17; the `mrms/` folder first appears between 2014-09-01 and 2014-12-01 (monthly probe; exact first date not pinned) | **16 of 18 events by date** (every event from 2015-05 on). 2012-01-25 has older `nmq/` tile data (format and quality unassessed); 2013-10-31 has nothing | **available, not yet downloaded or validated**; whether it captures these storms (ERA5 did not) is untested |
| HRRR on AWS (`noaa-hrrr-bdp-pds`) | starts 2014-07-30 (verified) | 16 of 18 events | model analysis/forecast, not observation; skill for these storms unassessed |
| NLDAS-2 hourly forcing | catalogue to 2026 (verified earlier) | all | needs your Earthdata login, not configured |
| ERA5 / ERA5-Land hourly | have it | all | inadequate for flood storms (about 8% of gauge rainfall on 2015-05-24 and 2016-05-29) |
| Hourly airport/ASOS stations | 8 stations in or near the area in `global-hourly` for 2015 | yes, sparse | precipitation quality untested |
| Daily gauge product (built) | 2007-2026 | yes | **not a storm-onset signal**: daily totals, available from 15:00 UTC on the observation day |
| USGS 15-min rain gauges | 1-3 years only | 2 to 4 events | too short |
**Hydrological travel-time information:** measured here directly from the gauge lead times (about 13-20 h from the upper river to Spring Branch when the storm fell upstream; implied wave speeds 1.7-3.3 m/s along 52-157 km of channel, section 2b). NHDPlus velocity attributes were not used.

## 4. What this implies (interpretation with limits)
1. **Supported by this assessment:** for about a third to 44% of the events (6 to 8 of 18 depending on the timing definition, section 2c; the 6 clear cases include 3 of the 5 official storms) upstream stage rises 6 to 26 hours before Spring Branch, far more than the 3 h horizon, so a stage-only model that cannot see upstream gauges is information-limited for exactly the rapid events it lags. This is the strongest evidence so far for the hypothesis that the principal limitation is missing upstream information.
2. **Not supported:** that upstream gauges would fix early warning in general. For 6 to 8 of 18 events (including two official floods, 2015-05-24 and 2015-10-30) the rain fell downstream of, or level with, every upstream gauge; for these only rainfall information at the right place and time (radar or dense sub-daily gauges) could help, and radar QPE appears to exist by date for 16 of the 18 events through the Iowa State MRMS archive (from late 2014), but it has not been downloaded or validated against the 92-station gauge product, so its usefulness for these storms is unknown.
3. **Not tested:** that a model can convert an upstream rise into an accurate downstream forecast. Lead time measures when information exists, not what a model extracts. A cross-validated experiment on the existing folds would be needed, with the same event-level evaluation.
4. **Statistical caution:** only 14 storm clusters are evaluated; adding several upstream channels raises the risk of overfitting; any input experiment must keep the one-factor-at-a-time rule and report events and clusters.

## 5. Limitations of this assessment
Lead times use a 1 ft/3 h trigger (sensitivity in 2b); the outage and datum audit used daily values and a crude matched-discharge test, and Bergheim was not audited; river distances come from NLDI flowline geometry for main-stem gauges only (no river distance for the tributary gauge at Johnson Creek); the event catalogue is defined at Spring Branch only, so storms that only raised upstream gauges are not counted; 18 of 77 responding pairs have inconsistent timings and were excluded from the lead statistics; the 2 events outside the cross-validation (2010) are included in the per-gauge table but excluded from the per-event summary; the two UNVERIFIED archives were not read in detail; no data volume or processing cost was assessed for radar archives.

## 6. Suggested questions for the research guide
1. Is adding upstream gauge stage as inputs (a data-driven, free, 15-min source) an acceptable change of the project's central claim, from "a hybrid architecture improves forecasting" to "a hybrid with upstream context improves forecasting of upstream-driven floods"?
2. For the storms that fell downstream of all upstream gauges (including two official floods, 2015-05-24 and 2015-10-30), is it acceptable to state that stage-based models cannot warn, and to scope the early-warning claim accordingly?
3. Is it worth verifying Stage IV availability and building a radar-based rainfall input for the post-2020 events only, as a limited case study?
4. Should NLDAS-2 (Earthdata) be pursued, given its 1/8-degree resolution and the ERA5 experience?
5. Which single upstream gauge should be tried first (Comfort has the best coverage and median lead; Center Point and Kerrville add redundancy)?
