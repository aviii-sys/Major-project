"""Shared experiment context: reproduces the Phase 1B data, eligibility, splits, events and event windows exactly,
so that deep models are trained and scored on the same rows as the classical baselines."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import data, events, metrics, splits

HZ = list(data.HORIZONS)
EXC = {"official_action_25ft": 25.0, "official_minor_30ft": 30.0, "official_moderate_36ft": 36.0, "experimental_stage_10ft": 10.0, "experimental_stage_15ft": 15.0}
RAP = {"experimental_rise_4ft_3h": 4.0, "experimental_rise_8ft_3h": 8.0}


@dataclass
class Ctx:
    s: pd.Series
    sv: np.ndarray
    n: int
    prov: np.ndarray
    tg: dict            # horizon -> np.ndarray of stage change s(t+h)-s(t)
    elig: dict          # horizon -> bool array (Phase 1B eligibility v2, common rows)
    lab: np.ndarray     # 'train' | 'val' | 'test' | 'purge'
    vs: pd.Timestamp
    ts: pd.Timestamp
    clusters: pd.DataFrame
    groups: np.ndarray
    ev_all: dict
    kind_of: dict
    thr_of: dict
    H: pd.DataFrame

    def win_mask(self, ev: pd.DataFrame, kind: str) -> np.ndarray:
        m = np.zeros(self.n, bool)
        for e in ev.itertuples():
            lo = events.rise_onset_index(self.sv, e.i0) if kind == "exceed" else e.i0
            m[max(0, lo - 24):(e.peak_i if kind == "exceed" else e.i1) + 1] = True
        return m

    def events_in(self, defn: str, pmask: np.ndarray) -> pd.DataFrame:
        ev = self.ev_all[defn]
        return ev[pmask[ev.i0.values]].reset_index(drop=True) if len(ev) else ev

    def val_windows(self) -> np.ndarray:
        pm = self.lab == "val"
        w = np.zeros(self.n, bool)
        for d in ("experimental_stage_10ft", "experimental_rise_4ft_3h"):
            w |= self.win_mask(self.events_in(d, pm), self.kind_of[d])
        return w


def build_context() -> Ctx:
    reg = data.load_stage()
    s = reg.s
    H = data.hydro_features(s)
    R = data.rain_features(data.load_rain_hourly(), s.index)
    base_ok = H[data.REQUIRED_COLS].notna().all(axis=1).values & R.notna().all(axis=1).values
    tgs = data.targets(s)
    tg = {h: tgs[h].values for h in HZ}
    elig = {h: base_ok & ~np.isnan(tg[h]) & s.notna().values for h in HZ}
    clusters = events.storm_clusters(s)
    groups = splits.group_ids(s.index, clusters)
    lab, vs, ts = splits.chronological_split(s.index, clusters)
    ev_all = {k: events.exceedance_events(s, t) for k, t in EXC.items()}
    ev_all.update({k: events.rapid_rise_events(s, t) for k, t in RAP.items()})
    return Ctx(s=s, sv=s.values, n=len(s), prov=reg.provisional.values, tg=tg, elig=elig, lab=lab.values, vs=vs, ts=ts, clusters=clusters, groups=groups,
               ev_all=ev_all, kind_of={k: ("exceed" if k in EXC else "rapid") for k in ev_all}, thr_of={**EXC, **RAP}, H=H)


def fixed_rule_raw(ctx: Ctx, change_pred: np.ndarray, k: int, kind: str, thr: float) -> np.ndarray:
    shat = ctx.sv + change_pred
    ok = ~np.isnan(shat)
    raw = (shat >= thr) if kind == "exceed" else ((shat - pd.Series(ctx.sv).shift(12 - k).values) >= thr)
    return np.where(ok, raw, False)


def detect(ctx: Ctx, raw: np.ndarray, evp: pd.DataFrame, k: int, elig_h: np.ndarray, years: float):
    """Event-level confusion for one alarm series (Phase 1B definition: matching against ALL events; POD etc. on evaluable events,
    evaluable = >= 50% of the lead-credit issue times satisfy the minimal-input eligibility)."""
    if len(evp) == 0:
        return None, pd.DataFrame()
    ev_ok = np.array([elig_h[max(0, e.i0 - k - 4):e.i0 + 1].mean() >= 0.5 for e in evp.itertuples()])
    st = events.alarm_state(raw)
    a0, a1 = events.alarm_episodes(st)
    res_all, n_ep, n_fa = events.match(evp, a0, a1, k)
    res = res_all[ev_ok].reset_index(drop=True)
    pe = res_all.copy()
    pe.loc[~ev_ok, "status"] = "not_evaluable"
    n_ev = len(res)
    if n_ev == 0:
        return None, pe
    early, late, miss = int((res.status == "early").sum()), int((res.status == "late").sum()), int((res.status == "miss").sum())
    pod_ci = metrics.clopper_pearson(early, n_ev)
    leads = res.lead_h.dropna()
    summ = {"n_events": n_ev, "early_hits": early, "late": late, "misses": miss, "POD": early / n_ev, "POD_ci_lo": pod_ci[0], "POD_ci_hi": pod_ci[1],
            "alarm_episodes": n_ep, "false_alarm_episodes": n_fa, "precision_episode": (1 - n_fa / n_ep) if n_ep else np.nan,
            "false_alarms_per_year": n_fa / years, "median_lead_h": float(leads.median()) if len(leads) else np.nan,
            "storm_clusters": int(len(np.unique(ctx.groups[res_all.i0.values[ev_ok]])))}
    return summ, pe
