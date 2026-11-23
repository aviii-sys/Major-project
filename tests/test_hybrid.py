"""Hybrid Transformer+LSTM (E23) and the warning-lead harness (E22): structure, branch windows, the stability-selection rule, lead counting, and checks on saved outputs."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from flashflood import dl, hybrid, leadtime
from flashflood.seq import SeqData

sys.path.insert(0, "scripts")


def _x(b=4, seed=0):
    g = torch.Generator().manual_seed(seed)
    return torch.randn(b, 96, 3, generator=g), torch.randn(b, 2, generator=g)


def test_shapes_and_four_settings_with_s0_matching_the_phase1c_transformer():
    assert list(hybrid.SETTINGS) == ["S0", "S1", "S2", "S3"]
    for name, cfg in hybrid.SETTINGS.items():
        net = hybrid.HybridNet(cfg)
        x, st = _x()
        assert net(x, st).shape == (4, 4)
    s0 = hybrid.SETTINGS["S0"]
    assert (s0.d_model, s0.n_layers, s0.n_heads, s0.ff_mult, s0.dropout, s0.norm_first, s0.lr, s0.warmup_steps) == (64, 2, 4, 2, 0.1, False, 1e-3, 0)
    # the Transformer branch of S0 has exactly the parameters of the Phase 1C Transformer encoder (projection, positions, encoder layers, pooling)
    ref = dl.Net("transformer", 64)
    ref_n = sum(p.numel() for m in (ref.proj, ref.enc, ref.pool) for p in m.parameters()) + ref.pos.numel()
    h = hybrid.HybridNet(s0, use_l=False)
    assert sum(p.numel() for m in (h.proj, h.enc, h.pool) for p in m.parameters()) + h.pos.numel() == ref_n
    assert hybrid.HybridNet(hybrid.SETTINGS["S3"]).n_params() < hybrid.HybridNet(hybrid.SETTINGS["S0"]).n_params()


def test_prenorm_settings_have_a_final_layer_norm_and_postnorm_does_not():
    assert hybrid.HybridNet(hybrid.SETTINGS["S1"]).enc.norm is not None and hybrid.HybridNet(hybrid.SETTINGS["S0"]).enc.norm is None


def test_branch_windows_the_lstm_sees_only_the_last_6_hours_the_transformer_sees_all_24():
    x, st = _x()
    x2 = x.clone(); x2[:, :72, :] += 5.0                                      # change everything older than the last 24 steps
    torch.manual_seed(1)
    lonly = hybrid.HybridNet(hybrid.SETTINGS["S0"], use_t=False).eval()
    assert torch.allclose(lonly(x, st), lonly(x2, st))
    torch.manual_seed(1)
    tonly = hybrid.HybridNet(hybrid.SETTINGS["S0"], use_l=False).eval()
    assert not torch.allclose(tonly(x, st), tonly(x2, st))
    both = hybrid.HybridNet(hybrid.SETTINGS["S0"]).eval()
    assert not torch.allclose(both(x, st), both(x2, st))
    x3 = x.clone(); x3[:, -24:, :] += 5.0                                     # change the last 6 h: both branches must respond
    assert not torch.allclose(lonly(x, st), lonly(x3, st)) and not torch.allclose(tonly(x, st), tonly(x3, st))
    with pytest.raises(ValueError):
        hybrid.HybridNet(hybrid.SETTINGS["S0"], use_t=False, use_l=False)


def test_warmup_schedule():
    assert hybrid.lr_factor(0, 0) == 1.0 and hybrid.lr_factor(0, 300) == pytest.approx(1 / 300) and hybrid.lr_factor(299, 300) == 1.0 and hybrid.lr_factor(10_000, 300) == 1.0


def _synthetic(n=3000, seed=0):
    r = np.random.default_rng(seed)
    sv = 2 + np.cumsum(r.normal(0, 0.05, n)).clip(-1, 8)
    sd = SeqData(sv, "cpu")
    idx = np.arange(400, n - 20)
    sd.fit_stats(idx[:1500])
    y = np.stack([np.r_[sv[k:] - sv[:-k], np.zeros(k)] for k in (1, 2, 4, 12)], axis=1).astype(np.float32)
    return sd, torch.tensor(y / y.std(0)), torch.ones(n, 4), idx


def test_training_is_deterministic_for_a_seed_and_restores_the_best_state():
    sd, Y, M, idx = _synthetic()
    kw = dict(max_epochs=2, rows_per_epoch=1500, batch=256, log=lambda *_: None)
    n1, h1 = hybrid.train_run_hybrid(hybrid.SETTINGS["S1"], 3, sd, Y, M, idx[:1500], idx[1500:2000], **kw)
    n2, h2 = hybrid.train_run_hybrid(hybrid.SETTINGS["S1"], 3, sd, Y, M, idx[:1500], idx[1500:2000], **kw)
    assert [e["val_loss"] for e in h1] == pytest.approx([e["val_loss"] for e in h2], abs=1e-9)
    assert all(torch.equal(a, b) for a, b in zip(n1.state_dict().values(), n2.state_dict().values()))
    p = dl.predict(n1, sd, idx[2000:2100], torch.ones(4))
    assert p.shape == (100, 4) and np.isfinite(p).all()


def test_stability_selection_rule(tmp_path):
    from run_hybrid_h1 import select

    def mk(setting, fold, loss, best_epoch=5):
        d = tmp_path / "stability" / f"fold{fold}_{setting}_s0"
        d.mkdir(parents=True)
        (d / "config.json").write_text(json.dumps({"fold": fold, "setting": {"name": setting}, "best_val_scaled_loss": loss, "best_epoch": best_epoch, "epochs_run": 12, "train_seconds": 10.0}))
    for f in range(1, 7):
        mk("S0", f, 1.0 * f); mk("S1", f, 0.95 * f); mk("S2", f, 0.999 * f); mk("S3", f, 1.2 * f)
    res = select(tmp_path)
    assert res["chosen_setting"] == "S1"                                       # 5% lower validation loss than S0 in every fold
    for f in range(1, 7):                                                      # now no setting beats S0 by at least 1%
        for s, m in (("S1", 0.995), ("S2", 0.997)):
            c = tmp_path / "stability" / f"fold{f}_{s}_s0" / "config.json"
            d = json.loads(c.read_text()); d["best_val_scaled_loss"] = m * f; c.write_text(json.dumps(d))
    assert select(tmp_path)["chosen_setting"] == "S0"


def _pe(rows):
    return pd.DataFrame(rows, columns=["status", "lead_h"])


def test_lead_counting_uses_a_30_minute_threshold_and_ignores_not_evaluable():
    pe = _pe([("early", 0.25), ("early", 0.5), ("early", 1.0), ("late", np.nan), ("miss", np.nan), ("not_evaluable", np.nan)])
    s = leadtime.summarize(pe)
    assert s["events"] == 5 and s["early_hits"] == 3 and s["hits_with_lead_ge_30min"] == 2 and s["hits_with_lead_ge_60min"] == 1 and s["late"] == 1 and s["misses"] == 1
    assert s["median_lead_h_of_early_hits"] == 0.5


def test_h0_reproduces_phase1d_detection_counts():
    p = Path("reports/hybrid_h0/tables/H0_2_reproduction_check_vs_D5.csv")
    if not p.exists():
        pytest.skip("H0 outputs not present")
    c = pd.read_csv(p)
    assert len(c) == 72 and c.match.all()


def test_saved_hybrid_runs_match_their_manifest():
    man = Path("reports/hybrid_h1/runs/manifest.json")
    if not man.exists():
        pytest.skip("hybrid runs not present")
    m = json.loads(man.read_text())
    assert len(m) >= 18
    for name, h in m.items():
        d = Path("reports/hybrid_h1/runs") / name
        assert dl.sha256_file(d / "predictions.npz") == h["predictions_sha256"] and dl.sha256_file(d / "checkpoint.pt") == h["checkpoint_sha256"]
