"""Phase 1D tests: leakage-free expanding-window blocked chronological folds."""
import numpy as np
import pandas as pd
import pytest

from flashflood import events, experiment, folds


@pytest.fixture(scope="module")
def setup():
    ctx = experiment.build_context()
    spec = folds.design_folds(ctx.s.index, ctx.clusters)
    return ctx, spec


def test_six_folds_in_chronological_order(setup):
    ctx, spec = setup
    assert len(spec) == 6
    assert (spec.test_start.diff().dropna() > pd.Timedelta(0)).all()
    assert (spec.test_end.iloc[:-1].values < spec.test_start.iloc[1:].values).all()          # blocks contiguous, non-overlapping


def test_training_and_validation_strictly_precede_test_with_embargo(setup):
    ctx, spec = setup
    idx = ctx.s.index
    for r in spec.itertuples():
        tr, va, te = folds.fold_masks(idx, r)
        assert not (tr & te).any() and not (va & te).any() and not (tr & va).any()
        assert idx[tr].max() < idx[va].min() - pd.Timedelta(hours=27)                        # train / validation embargo
        assert idx[va].max() <= r.test_start - folds.EMBARGO                                  # validation / test embargo
        assert idx[tr].max() + pd.Timedelta(hours=3) < idx[te].min() - pd.Timedelta(hours=24)  # train targets never touch a test input window
        assert idx[va].max() + pd.Timedelta(hours=3) < idx[te].min() - pd.Timedelta(hours=23)


def test_no_future_data_is_used_to_fit_an_earlier_block(setup):
    ctx, spec = setup
    idx = ctx.s.index
    for r in spec.itertuples():
        tr, va, te = folds.fold_masks(idx, r)
        assert idx[tr | va].max() < r.test_start                                             # nothing from the block or later


def test_no_storm_cluster_is_split_between_train_validation_and_test(setup):
    ctx, spec = setup
    idx = ctx.s.index
    for r in spec.itertuples():
        tr, va, te = folds.fold_masks(idx, r)
        for c in ctx.clusters.itertuples():
            sl = slice(c.i0, c.i1 + 1)
            sets = {name for name, m in (("train", tr), ("val", va), ("test", te)) if m[sl].any()}
            assert len(sets) <= 1, (r.fold, c.cluster_id, sets)


def test_every_boundary_is_in_a_quiet_period(setup):
    ctx, spec = setup
    for r in spec.itertuples():
        for t in (r.test_start, r.val_start):
            near = ctx.clusters[(ctx.clusters.t0 <= t) & (ctx.clusters.t1 >= t - folds.CLEAR)]
            assert len(near) == 0


def test_every_event_is_in_one_fold_or_documented_exclusion(setup):
    ctx, spec = setup
    m = folds.event_to_fold(ctx.ev_all, ctx.kind_of, spec, ctx.s.index, ctx.clusters, ctx.groups)
    assert ((m.status == "evaluated") == m.fold.notna()).all()
    assert (m[m.status == "excluded"].reason.str.len() > 0).all()
    e10 = m[m.definition == "experimental_stage_10ft"]
    assert len(e10) == 20 and (e10.status == "evaluated").sum() == 18                       # two 2010 events excluded: initial segment
    assert (m[m.status == "excluded"].event_start < spec.test_start.min()).all()
    # an event and its whole storm cluster are never in different folds
    ev = m[m.status == "evaluated"]
    assert (ev.groupby("storm_cluster").fold.nunique() <= 1).all()


def test_test_blocks_partition_the_post_initial_record(setup):
    ctx, spec = setup
    idx = ctx.s.index
    cover = np.zeros(len(idx), int)
    for r in spec.itertuples():
        cover += folds.fold_masks(idx, r)[2].astype(int)
    assert cover.max() == 1                                                                   # no timestamp is held out twice
    assert (cover[idx >= spec.test_start.min()] == 1).all()                                   # every later timestamp is held out once
    assert (cover[idx < spec.test_start.min()] == 0).all()


# ---------------------------------------------------------------- artifact-level checks (skipped if the Phase 1D outputs are absent)
from pathlib import Path  # noqa: E402
import json  # noqa: E402

OOF = Path("reports/phase1d/oof_predictions.csv.gz")


@pytest.mark.skipif(not OOF.exists(), reason="Phase 1D outputs not present")
def test_saved_fold_configs_respect_precedence_and_embargo():
    spec = pd.read_csv("reports/phase1d/fold_specification.csv", parse_dates=["test_start"])
    for r in spec.itertuples():
        for a in ("gru", "lstm"):
            c = json.load(open(f"reports/phase1d/runs/fold{r.fold}_{a}_h64_s0/config.json"))
            b = {k: pd.Timestamp(v) for k, v in c["boundaries"].items()}
            assert b["train_end"] < b["val_start"] - pd.Timedelta(hours=27)
            assert b["val_end"] <= r.test_start - pd.Timedelta(hours=27)
            assert c["seed"] == 0 and c["hidden"] == 64 and c["window_steps"] == 96 and c["quick"] is False


@pytest.mark.skipif(not OOF.exists(), reason="Phase 1D outputs not present")
def test_oof_predictions_unique_and_inside_their_own_block():
    o = pd.read_csv(OOF)
    spec = pd.read_csv("reports/phase1d/fold_specification.csv", parse_dates=["test_start", "test_end"])
    assert not o.timestamp_utc.duplicated().any()
    ts = pd.to_datetime(o.timestamp_utc, utc=True)
    for r in spec.itertuples():
        t = ts[o.fold == r.fold]
        assert (t >= r.test_start).all() and (t <= r.test_end).all()
