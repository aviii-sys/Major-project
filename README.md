# Flash-flood forecasting at USGS 08167500 (Guadalupe River near Spring Branch, TX)

Research project: can a Transformer-LSTM hybrid improve multi-horizon (15 min, 30 min, 1 h, 3 h) river-stage forecasting and rapid-rise anticipation beyond well-evaluated GRU, LSTM and classical baselines, under sparse extreme-event data? **The hybrid has not been built yet**; the work so far is data audit, baselines, deep baselines and a strict evaluation framework. Current findings are in `reports/` (latest: `PHASE1E_REPORT.md`, GRU 24 h versus 72 h input window: 72 h not adopted; `PHASE1E_ONSET_TIMING.md`, how late the forecasts are; a historical-replay viewer of the saved forecasts is in `dashboard/replay/` (not live); the hybrid Transformer-LSTM has code, a protocol (`docs/HYBRID_H1_PROTOCOL.md`) and tests but **no trained result** (its first run was stopped; warning-lead evaluation of the baselines is in `reports/hybrid_h0/`); the first-evaluation progress dashboard is `dashboard/evaluation/index.html` with the presentation pack `docs/FACULTY_EVALUATION_PREP.md`; cross-validation: `PHASE1D_REPORT.md`; upstream inputs: `docs/UPSTREAM_INPUT_FEASIBILITY.md`; guide brief: `docs/GUIDE_BRIEF.md`).

**Integrity rules in force:** the 2022+ test period and in fact the whole 2007-2026 record have been inspected, so every result is *exploratory*; nothing is tuned on held-out data; official NWS flood stages (25/30/36/39 ft) are kept separate from experimental targets (stage >= 10/15 ft; rises of 4/8 ft in 3 h); all protocols were written before the experiments they govern and every deviation is logged in them (see `docs/`, `experiments/REGISTRY.md`).

## Setup
```
brew install uv libomp                  # macOS (libomp is needed by XGBoost)
uv venv --python 3.11 && uv pip install -e .      # or: uv pip install -r requirements.lock
.venv/bin/python -m pytest -q           # 89 tests
```
Two machine-specific warnings: (1) **PyTorch and XGBoost crash (segmentation fault, OpenMP clash) when used in the same process**: run deep and classical stages as separate processes (the Phase 1D runner has `--stage dl` and `--stage classical`). (2) Long trainings pause if the Mac sleeps; use `caffeinate -i -w <pid>`.

## Layout
| Path | Contents |
|---|---|
| `src/flashflood/` | library: `data` (loading, causal features), `events` (events, alarms, matching), `splits`, `folds` (blocked CV), `metrics`, `models` (classical), `experiment` (shared context), `seq` and `dl` (deep models) |
| `scripts/` | one script per step: `fetch_*` (data), `audit_*` and `build_*` (datasets), `run_phase1a/b/c/d/e` (experiments), `eval_phase1c/d/e` and `make_*tables` (evaluation), `assess_upstream_inputs.py` and related (feasibility study) |
| `docs/` | protocols fixed before each experiment (`PHASE1A..1E`), feasibility study, guide brief; `docs/archive/` keeps superseded drafts |
| `experiments/REGISTRY.md` | every experiment: where it lives, its protocol, its status (primary, archived, exploratory) |
| `reports/` | reports per phase and all tables, figures, run artifacts (checkpoints with SHA-256 manifests); `*_original_strict` and `FIRST_RUN_INVALID_*` are preserved on purpose |
| `data/raw`, `data/processed` | fetched data (re-creatable with the fetch scripts; checksums in `data/raw/MANIFEST.sha256`) |
| `dashboard/replay/` | historical-replay dashboard of the saved out-of-fold forecasts: `index.html` (open in a browser, works offline), template, README, screenshots; built by `scripts/build_replay_dashboard.py` |
| `dashboard/evaluation/` | faculty evaluation dashboard (first-evaluation progress review) built from the saved result tables: `index.html`, template, README, screenshots, optional browser check; built by `scripts/build_evaluation_dashboard.py` |
| `tests/` | leakage, protocol, metric, onset-timing and dashboard tests (`test_phase1a..1e.py`, `test_onset.py`, `test_replay.py`, `test_evaluation_dashboard.py`, `test_upstream_protocol_support.py`) |

## Reproduction order (each experiment script is resumable)
Data: `scripts/fetch_meta.py`, `fetch_usgs.py --start 2007-10-02`, `fetch_openmeteo.py --dataset precip`, `fetch_ghcnd.py`, `build_gauge_rain.py`, `audit_phase0.py`.
Experiments: `run_phase1a.py` (and `--legacy --out reports/phase1a_original_strict`), `run_phase1b.py`, `run_phase1c_dl.py` then `eval_phase1c.py`, `run_phase1d_cv.py --stage dl` then `--stage classical` then `eval_phase1d.py`, `run_phase1e_window.py` then `eval_phase1e.py`, then `PYTHONPATH=src python scripts/run_onset_timing.py` (onset timing, saved predictions only) `PYTHONPATH=src python scripts/build_replay_dashboard.py` (replay dashboard) and `PYTHONPATH=src python scripts/build_evaluation_dashboard.py` (faculty dashboard).

## Data sources and attribution
USGS NWIS (public domain); NOAA/NCEI GHCN-Daily and NLDI/NWPS (public); Open-Meteo ERA5 (CC BY 4.0, non-commercial free tier; cite Zippenfenig 2023, Open-Meteo.com Weather API, doi:10.5281/ZENODO.7970649; "Generated using Copernicus Climate Change Service information"). NLDAS-2 (NASA GES DISC) needs an Earthdata login and is not yet used. The folder is not under version control by default (see `ARTIFACTS.md` for what to keep and what is re-creatable).
