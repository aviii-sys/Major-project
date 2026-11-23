# Faculty Evaluation Dashboard (first evaluation)

A single offline page (`index.html`, about 0.2 MB, no server, no internet, no external libraries) that presents the project's real progress for the first faculty evaluation. It is separate from, and links to, the historical-replay dashboard (`../replay/index.html`), which is unchanged.

> Research progress view built from saved result tables. All experimental results are exploratory (retrospective, test period already inspected). The hybrid Transformer-LSTM has **not** been implemented. The three-stage academic roadmap is a **proposal**: the university's requirements are not documented in the project and must be confirmed with the faculty.

## Launch
```
open dashboard/evaluation/index.html                                   # macOS; or open the file in any modern browser
PYTHONPATH=src .venv/bin/python scripts/build_evaluation_dashboard.py  # rebuild from the result tables (about 10 s; it also runs the test suite once)
```
Controls: top navigation with section highlighting, **Projector mode** (larger text), light/dark theme, interactive model comparison (evidence set, horizon, metric, event subset), tooltips on every chart mark, a data table under every chart, print styles.

## Sections
A project overview (with the proposed, not implemented, architecture) · B three-phase academic roadmap (proposal) · C research progress (nine milestones, each with task status and evidence strength) · D model comparison (ordinary rows versus flood windows; cross-validation and the Phase 1C single split that includes the Transformer) · E five findings with their limits · F existing system demonstration (link to the replay dashboard, implemented components, not-implemented list) · G challenges and limitations · H next steps (proposed) · I evidence and verification.

## Where the numbers come from
`scripts/build_evaluation_dashboard.py` reads the project's result tables (`reports/phase0|1c|1d|1e|1e_onset|upstream_protocol_support`, `experiments/registry.json`, `docs/UPSTREAM_INPUT_PROTOCOL.md`) and embeds them. Numbers in the text come from a `facts` dictionary (value, source file, derivation), listed with the SHA-256 of every source file in section I. No percentage-completion figures are used: the roadmap counts deliverables that exist with an evidence file, and says so.

## Verification
- `tests/test_evaluation_dashboard.py` (13 tests, in `pytest`): embedded model, paired-difference, detection, window, onset and upstream data equal the CSVs by an independent lookup; key facts are recomputed independently; source hashes match (a changed source makes the page stale and fails the test); every linked file exists; no external resources; the page script has valid JavaScript syntax; the roadmap is labelled a proposal, no second- or third-evaluation deliverable is marked done, the hybrid and other unimplemented items are listed as not implemented, and no completion percentages appear.
- Optional browser check (`browser_check/`; Playwright is not a project dependency): drives the real page through all 32 model-comparison states and the findings at every horizon, then compares 1,763 displayed values with the source tables, and checks navigation, links, projector mode and theme. Last run: 1,763 of 1,763 passed, no console errors. Usage in `browser_check/dump_display.js` and `compare_display.py`.
- Screenshots in `screenshots/` (desktop, projector mode, dark mobile).

## Assumptions, limitations, deviations
- The academic phase structure is a proposal (not documented anywhere in the project).
- The Transformer appears only in the Phase 1C single-split comparison; it was not part of the cross-validation. That panel is labelled as not directly comparable.
- GRU and LSTM in the cross-validation are single training seeds.
- The model-comparison intervals are the storm-cluster bootstrap intervals stored in the result tables.
- The page counts tests excluding its own test file (to avoid recursion when it runs the suite at build time).
- A static single-file page was used (as for the replay dashboard) because no dashboard library is installed and offline use is required.

Companion document: `docs/FACULTY_EVALUATION_PREP.md` (audit, proposed academic phases, presentation structure, demonstrations, likely questions and answers).
