# NOAA gauge-based daily basin rainfall product (USGS 08167500 upstream basin)

Built by `scripts/fetch_ghcnd.py` then `scripts/build_gauge_rain.py` (numbers below come from `build_notes.json` and `tables/`). Output: `data/processed/gauge_basin_daily.csv`, 6,985 days, 2007-10-02 to 2026-11-15.

## Source and units
NOAA/NCEI GHCN-Daily `PRCP` (COOP, CoCoRaHS and a few airport stations), metric units, **mm per observation day**. Downloaded 2026-11-22 with attributes `MFLAG,QFLAG,SFLAG,OBS_TIME`; raw files untouched in `data/raw/ghcnd/`. Flag meanings are quoted from the NCEI readme saved in `data/raw/meta/ghcnd_readme.txt`.

## Station coverage
664 stations lie inside the basin polygon (USGS NLDI, 1,316 sq mi) or within 0.25 degrees of it; **187 are inside the basin** (176 CoCoRaHS, 9 COOP, 2 airport/WBAN). Per-station table: `tables/station_table.csv` (first/last date, valid days, QC failures, network). The network grows over time: median reporting stations inside the basin per day rises from **25 (partial 2007) to about 59 (2025)** (`tables/coverage_by_year.csv`, `figures/fig1_station_counts_by_year.png`). **The product is therefore not statistically homogeneous through time**: early years rest on fewer, mostly COOP, gauges.

## Quality flags (applied before any averaging)
A daily value is dropped if it is missing or negative, if `QFLAG` is non-blank (any failed NCEI check; 1,577 rows), or if `MFLAG` is `P` (missing presumed zero) or `I` (no precipitation data reported) (2,188 rows). `MFLAG` `T` (trace) and `H` (zero reported but precipitation noted) are kept as 0 mm and counted (36,221 rows); this treats uncertain zeros as zeros and slightly biases very light rain downward. Multi-day accumulations that failed the NCEI length check are dropped through `QFLAG`; accumulations not caught by it would be assigned to one day.

## Observation times and temporal alignment
The product day D is the 24 h ending at the observer's morning reading (about 7 to 8 am local, i.e. roughly 12 to 14 UTC on D). COOP stations carry `OBS_TIME` (mostly 0700/0800/0900; stations outside 0600-0900 are excluded). **All CoCoRaHS rows carry no `OBS_TIME`**; they were assigned to the same morning family on the basis of the CoCoRaHS observing protocol (7 am; my recollection, not verified against CoCoRaHS documentation) and checked empirically: the basin-mean daily totals of COOP-only and CoCoRaHS-only stations correlate at **0.95 on the same day and only 0.28 / 0.25 when shifted by -1 / +1 day** (349 days with both above 10 mm; `tables/obs_time_family_check.csv`). Airport stations report calendar days and are excluded (4 of 664 stations).
**Causality rule for forecasting features:** day D is treated as available only from **15:00 UTC on D**. A feature at an issue time earlier than that must use the previous day. Daily totals carry no sub-daily timing, so this product cannot provide storm-onset information for 15-min to 3-h forecasts; it supports antecedent-wetness features and independent validation of other rainfall sources.

## Spatial weighting (not a simple average)
Inverse-distance weighting onto a 0.05-degree grid inside the basin (128 cells, equal-area weights), using stations within 60 km. The method was chosen by **leave-one-station-out cross-validation** on 38,968 wet station-days (>= 5 mm) at in-basin stations:
| Method | MAE mm | RMSE mm | bias mm |
|---|---|---|---|
| IDW power 2, 12 nearest (selected; lowest MAE of 9 IDW settings) | 5.43 | 9.81 | -1.80 |
| nearest station only | 6.38 | 11.69 | -1.62 |
| simple mean of all reporting stations within 60 km | 8.76 | 14.71 | -3.59 |
The simple average is clearly worse (MAE 61% higher) and is only reported as a comparison column (`simple_mean_inside_mm`, mean of in-basin reporting stations). IDW still smooths extremes (negative bias on wet days), so basin rainfall in intense storms is probably underestimated. There is no independent basin-wide truth (for example radar) in this project to calibrate it against.

## Missing days and quality labels
1 day is missing (fewer than 3 reporting stations) and 1 day is labelled `low_coverage` (fewer than 3 in-basin stations or less than 80% of the basin within 25 km of two reporting stations); every other day is `ok`. Columns: `basin_idw_mm`, `simple_mean_inside_mm`, `max_station_mm`, `n_stations_inside`, `n_stations_total`, `coverage_frac_25km_2stations`, `quality`.

## Comparison with ERA5 (Open-Meteo), 24 h ending 13 UTC (`tables/gauge_vs_era5_daily.csv`)
All good days: Pearson 0.74 (Spearman 0.75), mean 2.00 mm (gauges) versus 1.75 mm (ERA5). Days with gauge basin rain >= 10 mm (397 days): Pearson 0.50, mean **23.5 versus 15.5 mm**. Selected event days (`tables/event_days_gauge_vs_era5.csv`):
| Observation day | gauge IDW mm | simple mean mm | ERA5 mm |
|---|---|---|---|
| 2015-05-24 (flood peak 2015-05-24 03:45 UTC) | 119.4 | 131.8 | 9.9 |
| 2015-10-30 | 33.6 | 42.9 | 21.1 |
| 2016-05-29 | 64.5 | 62.3 | 5.0 |
| 2025-07-04 | 79.1 | 68.6 | 31.0 |
| 2025-07-05 | 56.4 | 48.7 | 57.2 |
| 2026-07-16 | 171.5 | 179.9 | 31.7 |
For the **2015-05 and 2016-05 floods ERA5 captures about 8% and 8% of the gauge basin rainfall on the key day** and puts its heaviest rain after the flood peak; for 2025-07-05 and 2026-07-14 it is close. **ERA5-Land/ERA5 rainfall should not be used as a reliable flood-rainfall input for this basin** without a bias correction; it stays in the project only as a comparison dataset.

## Limitations
Daily resolution only; observation days differ slightly by station; volunteer-network quality and time-varying station density; IDW smoothing; the product was validated against held-out stations, not against an independent basin-total reference. Gauge totals include rain that fell outside the basin only through interpolation near the boundary (stations within 25 km of the edge were used).
