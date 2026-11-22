"""Phase 1C tests: causal windows, train-only statistics, masked loss, determinism, and identical eligibility to the frozen classical predictions."""
from pathlib import Path

import numpy as np
import pytest
import torch

from flashflood import dl, experiment
from flashflood.seq import WINDOW, SeqData

RNG = np.random.default_rng(0)


def _series(n=1500, nan_frac=0.02, seed=0):
    r = np.random.default_rng(seed)
    sv = 2 + np.cumsum(r.normal(0, 0.05, n)).clip(-1, 8)
    sv[r.random(n) < nan_frac] = np.nan
    sv[600] = 3.0
    return sv


def test_windows_use_only_data_up_to_t():
    sv = _series()
    sd = SeqData(sv, "cpu"); sd.fit_stats(np.arange(200, 900))
    x0, s0 = sd.batch(torch.tensor([700, 1000]))
    sv2 = sv.copy(); sv2[701:] = 99.0; sv2[1001:] = -5.0             # corrupt everything after the first end index
    sd2 = SeqData(sv2, "cpu"); sd2.stats = sd.stats
    x1, s1 = sd2.batch(torch.tensor([700]))
    assert torch.allclose(x0[0], x1[0]) and torch.allclose(s0[0], s1[0])


def test_missing_samples_are_masked_not_imputed():
    sv = _series(nan_frac=0.0)
    sv[690:695] = np.nan
    sd = SeqData(sv, "cpu"); sd.fit_stats(np.arange(200, 600))
    x, _ = sd.batch(torch.tensor([700]))
    mask = x[0, :, 2]
    assert int(mask.sum()) == WINDOW - 5                              # exactly the 5 missing stage samples are masked
    assert (x[0, mask == 0, 0] == 0).all() and (x[0, mask == 0, 1] == 0).all()


def test_normalisation_statistics_use_training_windows_only():
    sv = _series(nan_frac=0.0)
    train = np.arange(200, 700)
    a = SeqData(sv, "cpu").fit_stats(train, seed=1)
    sv_future = sv.copy(); sv_future[701:] = 1e3                      # data after the last training end index
    b = SeqData(sv_future, "cpu").fit_stats(train, seed=1)
    assert a == b


def test_masked_loss_ignores_invalid_targets():
    pred = torch.zeros(4, 4); y = torch.ones(4, 4); m = torch.ones(4, 4); m[:, 1] = 0; y[:, 1] = 1e6
    assert abs(float(dl.masked_loss(pred, y, m)) - 1.0) < 1e-6


@pytest.mark.parametrize("arch", ["lstm", "gru", "transformer"])
def test_models_output_four_horizons(arch):
    net = dl.Net(arch, 32)
    out = net(torch.randn(5, WINDOW, 3), torch.randn(5, 2))
    assert out.shape == (5, 4)


@pytest.mark.parametrize("arch", ["lstm", "transformer"])
def test_training_is_deterministic_on_cpu(arch):
    sv = _series(); sd = SeqData(sv, "cpu"); sd.fit_stats(np.arange(150, 900))
    Y = torch.randn(len(sv), 4); M = torch.ones(len(sv), 4); sigma = torch.ones(4)
    runs = []
    for _ in range(2):
        net, _ = dl.train_run(arch, 16, 7, sd, Y, M, sigma, np.arange(150, 900), np.arange(900, 1100), max_epochs=2, rows_per_epoch=300, log=lambda *_: None)
        runs.append(dl.predict(net, sd, np.arange(1100, 1200), sigma))
    assert np.allclose(runs[0], runs[1], atol=1e-6)


FROZEN = Path("reports/phase1b/frozen/predictions.npz")


@pytest.mark.skipif(not FROZEN.exists(), reason="frozen Phase 1B predictions not present")
def test_eligibility_identical_to_frozen_classical_predictions():
    ctx = experiment.build_context()
    z = np.load(FROZEN)
    for h in experiment.HZ:
        for proto, name in (("chrono_test", "test"), ("chrono_val", "val")):
            frozen_rows = np.isfinite(z[f"reg|{proto}|ridge_H0|{h}"])
            mine = ctx.elig[h] & (ctx.lab == name)
            assert (frozen_rows == mine).all(), (h, proto)
