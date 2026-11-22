# Viva study guide: defending this project

How to use it: cover the **Answer**, read the **Hint**, and try to answer aloud first. Every number below comes from this project's own tables (verified); if an examiner asks for one you cannot reproduce, say where the table is rather than guessing. The project's strongest feature is its evaluation design; its biggest honesty point is that the deep models did not clearly beat simple baselines. Say both.

## A. The problem and the data
**Q1. In one minute: what is this project and what did you find?**
Hint: problem, approach, main result, main limitation.
Answer: forecast the stage of the Guadalupe River at Spring Branch 15 min to 3 h ahead from 15-min history, aiming at early warning of flash floods. I built a strict evaluation, compared persistence, a damped trend, ridge, XGBoost, LSTM and GRU (and a Transformer), and found that deep models give no robust advantage over ridge or the damped trend under blocked chronological cross-validation. Every model trails sharp flood onsets by about 3 h at the 3 h horizon, because stage history alone does not contain information about rain falling upstream. Upstream gauges rise 6 to 26 h earlier in roughly a third of the events (6 to 8 of 18), so the next step is adding upstream inputs.

**Q2. Why is a flash flood hard to forecast from the river's own history?**
Hint: what has to happen before the stage at the gauge moves?
Answer: the stage at the gauge only moves after rain has fallen, run off and travelled down the river. Nothing in the gauge's own past tells you that a storm has just hit upstream. That is why all models lag sharp onsets.

**Q3. What data did you use, and what was wrong with your first dataset?**
Hint: think about thresholds and what the data contained.
Answer: USGS 15-min stage and discharge from 2007-10-02 (99.55% complete), NWS official flood stages (25, 30, 36, 39 ft), NOAA gauge rainfall, ERA5. The first working dataset (2022-2023) contained no flood at all (peak 2.86 ft against a 25 ft action stage), and its thresholds (2.175 ft) sat near the median of the record (above them 50.9% of the time), so they were not flood levels. I extended to 2007 onward.

**Q4. What is the difference between an "official" flood and your "experimental" events?**
Hint: who defines each, and why does it matter for claims?
Answer: official = NWS stages for this gauge (6 events at or above 25 ft, from 5 storms). Experimental = my own targets (stage >= 10 or 15 ft; rises of 4 or 8 ft in 3 h) chosen because there are too few official events to evaluate statistically. I never describe experimental results as flood-detection capability.

**Q5. Why does it matter that 20 events come from only 16 storms?**
Hint: independence.
Answer: events in the same storm are not independent (2016-05 has four events in one storm cluster). Statistics that treat them as independent overstate confidence. I resample whole storm clusters in the bootstrap and report both event and cluster counts.

## B. Leakage and evaluation design (the core of the project)
**Q6. Why not split the data randomly into train and test?**
Hint: neighbouring 15-min samples.
Answer: adjacent samples are almost identical and belong to the same storm, so a random split puts near-copies of test samples in training and inflates results. Time-series forecasting must be evaluated on later data than it was trained on, with whole storms kept together.

**Q7. Describe your cross-validation.**
Hint: direction of time, gaps, what is fitted where.
Answer: six expanding-window folds. Fold k trains on data before a validation chunk, validates on the chunk just before the held-out block, and tests on the block. Later data never trains a model evaluated on earlier events. Scalers and target scales are fitted on each fold's own training rows. Boundaries lie in quiet periods so no storm cluster is split.

**Q8. What is the embargo and how long is it?**
Hint: input window plus horizon.
Answer: 27 h 15 min = 24 h input window + 3 h maximum horizon + one 15-min step, placed between train and validation and between validation and test. It guarantees that no training target shares a timestamp with any test input window.

**Q9. Your first run had a data-handling defect. What was it and what did you do?**
Hint: rolling windows and a single missing value.
Answer: strict rolling features needed 100% of samples, so one missing 15-min sample blanked 72 hours of rows and removed the largest test event from every model (scored as a miss). I found it after seeing test output, fixed it (causal gap bridging, tolerant windows, an "evaluable event" rule), re-ran everything, kept the original results reproducible and logged it as deviation 3. The corrected test results are therefore labelled post-hoc and exploratory.

**Q10. Why do you keep saying "exploratory"?**
Hint: how many times has the data been looked at?
Answer: the whole record, including the 2022+ test period, was inspected in earlier phases, and some design choices were made with that knowledge. So none of it is untouched validation. I can only claim retrospective blocked cross-validation.

**Q11. What is pre-registration and why did you do it?**
Hint: when is the protocol written?
Answer: writing the protocol, metrics and decision rules before running the experiment, so the analysis cannot be bent after seeing results. Deviations are listed in the protocol.

## C. Baselines and metrics
**Q12. Why include persistence and a damped trend?**
Hint: what is the cheapest possible forecaster?
Answer: persistence (the future equals now) shows whether a model adds anything; the damped trend (extrapolate the recent rate with a damping factor) is a two-parameter heuristic. A complex model that cannot beat them is not earning its complexity. In my results ridge and the damped trend were hard to beat.

**Q13. Why is RMSE alone not enough for a flood system?**
Hint: most rows are quiet river.
Answer: about 500,000 held-out rows are mostly quiet, so overall RMSE is dominated by easy cases. I also report flood-window RMSE (issue times from 6 h before rise onset to the peak) and event-level detection. Better RMSE does not imply better detection or lead time: in Phase 1D the GRU matched ridge on overall RMSE but detected fewer rapid rises at 3 h.

**Q14. Explain early hit, late detection, miss and false alarm in your event metric.**
Hint: when is the alarm raised relative to the event start?
Answer: a model raises an alarm when its forecast exceeds a threshold, held for 1 h (hysteresis) to avoid flicker. An event is an early hit if an alarm was issued before the event began and its target time overlaps the event within a 1 h tolerance; lead time is event start minus the first such alarm. An alarm only after the event began is late (not a hit); no overlapping alarm is a miss; an alarm episode matching no event is a false alarm.

**Q15. What is a confidence interval from the storm-cluster bootstrap, and why exact binomial intervals for POD?**
Hint: what is resampled, and how many events are there?
Answer: I resample whole storm clusters (and weekly blocks of quiet time) with replacement, recompute the metric, and take the 2.5th and 97.5th percentiles. For detection rates with a handful of events I use the exact Clopper-Pearson interval: 3 hits out of 3 still gives a lower bound of only about 29%.

**Q16. What does "skill versus persistence" mean?**
Answer: 1 - MSE_model / MSE_persistence. Zero means no better than persistence; one is perfect.

## D. Models and results
**Q17. Which models did you train and with what inputs?**
Answer: ridge and XGBoost on engineered stage-history features; LSTM, GRU and Transformer encoders on a 24 h window (96 steps) of stage relative to the current stage, its 15-min change and a missing-data mask, with a shared encoder and four horizon-specific heads, hidden size 64, five seeds (Phase 1C) or one seed per fold (Phase 1D). No rainfall inputs, because ERA5 failed and the gauge rainfall is only daily.

**Q18. Headline result of the cross-validation?**
Hint: who won, and where were the deep models worse?
Answer: pooled over 18 held-out events, ridge H was best or tied on overall RMSE (3 h: 0.256 ft; GRU 0.258, LSTM 0.257). In flood windows at 15 and 30 min GRU and LSTM were significantly worse than ridge and the damped trend (for example GRU minus ridge +0.037 ft at 15 min); at 1 h and 3 h no difference could be established. For rapid rises at 3 h ridge detected 12 of 25, damped trend 10, GRU 7, LSTM 4.

**Q19. An earlier single split showed the GRU ahead. Why did you not trust it?**
Answer: it had only 4 test events and the seed spread (about 0.1 ft in flood windows at 3 h) was as large as many of the gaps. It did not replicate under cross-validation. I report it as a non-robust finding, not as proof.

**Q20. Why did the Transformer do badly?**
Hint: what can you actually claim?
Answer: I cannot claim why. It trained unstably (best epoch between 1 and 15, validation loss 0.319 to 0.363 against 0.29-0.31 for LSTM and GRU), but that is one untuned configuration. It is not evidence that Transformers are unsuitable. A bounded diagnostic experiment is planned, not run.

**Q21. All your models trail sharp onsets by about 3 hours. Explain.**
Answer: the 3 h forecast of a rise that has not yet started at the gauge cannot be made from the gauge's history. The models only recognise a rise once it begins, so a 3 h forecast follows the observation about 3 h late and catches up near the peak. It is an information limit, not a tuning problem.

**Q21a. Did giving the GRU 72 hours of history instead of 24 hours help?**
Hint: what did you decide beforehand, and what do the seeds say?
Answer: no. I fixed a rule before training (36 runs: six folds, seeds 0-2, 24 h versus 72 h; adopt 72 h only if it consistently improves flood-window error at 2 or more of 4 horizons, with no horizon significantly worse over all rows). It improved at none: pooled 72 h minus 24 h flood-window RMSE was positive at all four horizons (+0.003 to +0.041 ft), and only one of three seeds favoured 72 h. Over all rows 72 h was significantly worse at 15 min, 30 min and 1 h, by 1.2% to 1.6%. Fixed-rule detection was not better. It took about three times as long to train. I cannot say why (untested ideas: no new information in days 2 and 3, harder optimisation, more missing data), and it does not show that longer context cannot help another model. Three seeds, exploratory.

## E. Rainfall and upstream inputs
**Q22. Why did you abandon ERA5 rainfall?**
Answer: on the 2015-05-24 flood ERA5 gave 9.9 mm for the basin on the key day while the interpolated NOAA gauge product (65 reporting stations inside the basin that day) gave about 119 mm (ERA5 about 8% of it), and it was not just a time shift (an hourly timing test against two USGS rain gauges gave a median offset of +0.4 h). It is a coarse reanalysis and misses convective storms.

**Q23. What is the finding about upstream gauges, and how sure are you?**
Hint: range, not one number.
Answer: seven upstream gauges have 15-min stage for the whole record. Over the 18 cross-validated events, the upstream stage rose 6 or more hours before Spring Branch in 6 to 8 events (the range depends on how the rise is timed; multi-pulse storms are ambiguous) and gave no usable warning in 6 to 8, because the rain fell downstream of the gauges. The implied flood-wave speeds (about 2 to 3 m/s) are physically realistic. The gauges also dropped out during two of the biggest floods. This describes when information exists, not whether a model can use it.

**Q24. Why not just build the hybrid now?**
Answer: the baselines show the limitation is probably information, not model complexity; a hybrid on the same inputs is unlikely to fix early warning. The central claim may need to become "a hybrid with upstream context improves forecasting of upstream-driven floods". That is a decision for the research guide.

## F. Integrity and limitations
**Q25. Name five limitations without looking.**
Answer: one gauge; few independent events (14 storm clusters evaluated, 27 bootstrap groups in flood windows); exposed test period, so exploratory; one seed per fold in the cross-validation; deep models used hyperparameters from an earlier split (mild look-ahead); early folds have little training data; no rainfall inputs; project not under version control.

**Q26. Did you ever find a mistake of your own? (They may ask.)**
Answer: yes, several, and I disclosed them: the 3-hour feature defect; a first upstream-timing analysis that silently dropped three gauges and produced implausible negative leads (kept as `FIRST_RUN_INVALID_*`); claiming 15-min discharge for 1997 and 2002 floods from a sample check when the peaks were actually missing; labelling a daily-maximum column as a daily mean once. Finding and recording them is part of the method.

**Q27. What would you do with six more months?**
Answer: add upstream-gauge inputs with a missing-input strategy and re-run the same cross-validation; validate MRMS radar rainfall (available by date for 16 of 18 events) against the gauge product; run the bounded Transformer diagnostic; build the hybrid and compare it with every baseline; calibrate warning categories.

## G. Traps examiners like
- "Your model has R^2 = 0.99." Smooth stage series give high R^2 even for persistence; it says nothing about floods.
- "Why not use accuracy?" Quiet rows dominate; a model that always predicts "no flood" is highly accurate and useless.
- "Is it real time?" No: both rainfall sources are retrospective (days of delay); this is a historical replay study.
- "Does it warn people?" No claim of warning capability. Lead time is short (typically under about an hour) and every model lags onset.

## H. Numbers worth memorising
20 events >= 10 ft, 16 storms; 18 evaluated, 14 clusters; 6 official events, 5 storms; embargo 27 h 15 min; six folds; ridge 3 h overall RMSE 0.256 ft; rapid-rise detection at 3 h: ridge 12/25, damped trend 10/25, GRU 7/25, LSTM 4/25; ERA5 about 8% of gauge rainfall on 2015-05-24; upstream lead 6 to 26 h in 6 to 8 of 18 events; Phase 1E: 36 runs, 72 h window not adopted (0 of 4 horizons improved in flood windows; all-row error 1.2% to 1.6% worse at 15 min to 1 h).
