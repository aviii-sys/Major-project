"""Phase 1E tests: the input-window length must be the ONLY difference between the 24 h and 72 h configurations."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from flashflood import dl, experiment, folds
from flashflood.seq import SeqData


def _series(n=2500, seed=0):
    r = np.random.default_rng(seed)
    sv = 2 + np.cumsum(r.normal(0, 0.05, n)).clip(-1, 8)
    sv[r.random(n) < 0.02] = np.nan
    return sv


def test_window_72h_shapes_and_causality():
    sv = _series()
    sd = SeqData(sv, "cpu", window=288)
    sd.fit_stats(np.arange(400, 1200))
    x, s = sd.batch(torch.tensor([1300, 1800]))
    assert x.shape == (2, 288, 3) and s.shape == (2, 2)
    sv2 = sv.copy(); sv2[1301:] = 77.0                               # corrupt everything after the first end index
    sd2 = SeqData(sv2, "cpu", window=288); sd2.stats = sd.stats
    x2, s2 = sd2.batch(torch.tensor([1300]))
    assert torch.allclose(x[0], x2[0]) and torch.allclose(s[0], s2[0])


def test_the_24h_window_is_the_tail_of_the_72h_window():
    """Same end index: the last 96 steps of the 72 h window are the 24 h window (before normalisation), so only the amount of history differs."""
    sv = _series(); sv[:] = np.nan_to_num(sv, nan=2.0)
    a, b = SeqData(sv, "cpu", window=96), SeqData(sv, "cpu", window=288)
    ra = a.raw_channels(torch.tensor([1500]))
    rb = b.raw_channels(torch.tensor([1500]))
    assert torch.allclose(ra[0][0], rb[0][0][-96:]) and torch.allclose(ra[1][0], rb[1][0][-96:]) and torch.allclose(ra[4], rb[4])


def test_gru_parameters_do_not_depend_on_window_length():
    """Matched seeds give identical initial weights for the 24 h and 72 h models, and the same network accepts both lengths."""
    torch.manual_seed(3); n1 = dl.Net("gru", 64)
    torch.manual_seed(3); n2 = dl.Net("gru", 64)
    for (k1, v1), (k2, v2) in zip(n1.state_dict().items(), n2.state_dict().items()):
        assert k1 == k2 and torch.equal(v1, v2)
    assert n1(torch.randn(2, 96, 3), torch.randn(2, 2)).shape == (2, 4) and n1(torch.randn(2, 288, 3), torch.randn(2, 2)).shape == (2, 4)


def test_phase1e_folds_equal_phase1d_folds():
    p = Path("reports/phase1d/fold_specification.csv")
    if not p.exists():
        pytest.skip("Phase 1D specification not present")
    ctx = experiment.build_context()
    spec = folds.design_folds(ctx.s.index, ctx.clusters)
    saved = pd.read_csv(p)
    for c in ("train_end", "val_start", "val_end", "test_start", "test_end"):
        assert (pd.to_datetime(spec[c], utc=True).values == pd.to_datetime(saved[c], utc=True).values).all()


RUNS = Path("reports/phase1e/runs")


@pytest.mark.skipif(not (Path("reports/phase1e/decision.json").exists()), reason="Phase 1E outputs not present")
def test_matched_runs_differ_only_by_window():
    names = sorted(p.name for p in RUNS.glob("fold*_gru_w*"))
    assert len(names) == 36
    same_keys = ("fold", "arch", "hidden", "seed", "optimizer", "lr", "batch", "grad_clip", "max_epochs", "patience", "rows_per_epoch", "min_history_steps_for_training_rows", "rows", "sigma_ft", "boundaries")
    for k in range(1, 7):
        for s in range(3):
            a = json.load(open(RUNS / f"fold{k}_gru_w24h_h64_s{s}" / "config.json"))
            b = json.load(open(RUNS / f"fold{k}_gru_w72h_h64_s{s}" / "config.json"))
            for key in same_keys:
                assert a[key] == b[key], (k, s, key)
            assert a["window_steps"] == 96 and b["window_steps"] == 288 and not a["quick"] and not b["quick"]


@pytest.mark.skipif(not (Path("reports/phase1e/decision.json").exists()), reason="Phase 1E outputs not present")
def test_decision_file_follows_the_preregistered_rule():
    dec = pd.read_csv("reports/phase1e/tables/E3_decision_rule.csv")
    n_cons = int(dec["CONSISTENT IMPROVEMENT"].sum())
    worse = bool(dec["all_rows_significantly_worse"].any())
    d = json.load(open("reports/phase1e/decision.json"))
    assert d["adopt_72h"] == bool(n_cons >= 2 and not worse) and d["horizons_with_consistent_improvement_in_flood_windows"] == n_cons
