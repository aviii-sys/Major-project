# Separate 1998-2007 discharge-only forecasting dataset (USGS 08167500, parameter 00060)

Built by `scripts/build_discharge_dataset.py`; data in `data/processed/discharge_1998_2007_15min.csv.gz` (15-min grid, 1998-01-01 to 2007-10-01 UTC). **It is kept separate from the primary 2007-onward stage dataset, and no gage height is inferred from discharge.** Discharge is in ft3/s.

## What is in it
Columns: `q_cfs` (NaN when not observed), `q_cd` (USGS qualifier), `observed`, `estimated` ('e' qualifier), `in_usable_event_window` (True only within +/-24 h of an event that passed every check below).

## Which years and why
Years 1998 to 2007 passed the yearly criteria (15-min spacing, completeness, no negative values; `yearly_audit.md`). 1986-1995 is hourly and 1996-1997 is incomplete, so they are excluded. The 1997 and 2002 floods are not usable (their 15-min records stop during the rising limb; see `flood_day_check.md` and `daily_flood_days_failing_15min.csv`).

## Event-level checks (`event_catalogue_checked.csv`)
Events use **experimental** discharge thresholds (10,000, 20,000 and 30,000 cfs; NWS publishes no flow equivalents for this gauge); events within 24 h merge. An event is USABLE only if all of: **U1** no gap longer than 2 h within 24 h of the event; **U2** every UTC day within 24 h of the event whose independent USGS daily mean is >= 5,000 cfs has >= 90% of its samples and a 15-min maximum >= the daily mean; **U3** at most 5% estimated ('e') samples.
Result: **13 of 17** events >= 10,000 cfs usable (10,000: 17 events/13 usable; 20,000: 10/8; 30,000: 5/4). Not usable: 2000-10-25 and 2000-11-03 (a flood day below 90% coverage), 2002-07-01 (adjacent to the missing July 2002 flood days), 2004-11-17 (the day has 75% coverage; strict rule). Floods whose 15-min data are entirely absent cannot appear as candidate events, so they are listed separately from the daily record.
The 2007-08-17 flood (56,400 cfs) is usable and is not in the primary stage dataset (stage data start 2007-10-02).

## Limitations
Few events (13 usable at >= 10,000 cfs), a different period and rating conditions from the primary dataset, and no stage. A discharge-forecasting experiment on it must use its own chronological, storm-grouped splits and must not be pooled with stage results. No models have been run on it yet.
