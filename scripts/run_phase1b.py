"""Phase 1B (classical strengthening): implements docs/PHASE1B_PROTOCOL.md exactly.

Selection steps use VALIDATION data only.  The (already inspected) test period is scored once per final configuration and is EXPLORATORY.
Outputs: reports/phase1b/{tables,figures,frozen}.   Usage: python scripts/run_phase1b.py [--quick] [--no-gauge]
"""
import argparse
import hashlib
import json
import time
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss

from flashflood import data, events, metrics, models, splits

warnings.filterwarnings("ignore")
OUT = Path("reports/phase1b")
TAB, FROZEN = OUT / "tables", OUT / "frozen"
for p in (TAB, FROZEN):
    p.mkdir(parents=True, exist_ok=True)
HZ = list(data.HORIZONS)
EXC = {"official_action_25ft": 25.0, "official_minor_30ft": 30.0, "official_moderate_36ft": 36.0, "experimental_stage_10ft": 10.0, "experimental_stage_15ft": 15.0}
RAP = {"experimental_rise_4ft_3h": 4.0, "experimental_rise_8ft_3h": 8.0}
PROB_TARGETS = {"experimental_stage_10ft": ("exceed", 10.0), "experimental_stage_15ft": ("exceed", 15.0),
                "experimental_rise_4ft_3h": ("rapid", 4.0), "experimental_rise_8ft_3h": ("rapid", 8.0)}
THETAS = [0.02, 0.05] + [round(x, 2) for x in np.arange(0.10, 0.91, 0.05)]
LAMBDAS = (0.0, 10.0, 50.0)
TREND_W = {"15m": 1, "30m": 2, "1h": 4}
TREND_PHI = (0.25, 0.5, 0.75, 1.0)
RES: dict = {}


def md(df, name):
    df.to_csv(TAB / f"{name}.csv", index=False)
    (TAB / f"{name}.md").write_text(df.to_markdown(index=False, floatfmt=".3g"))


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def f2(prec, rec):
    return 0.0 if (prec + rec) == 0 else 5 * prec * rec / (4 * prec + rec)


def main(quick: bool, use_gauge: bool) -> None:
    n_est = 80 if quick else 600
    n_clf = 60 if quick else 400
    reg = data.load_stage(); s = reg.s; sv = s.values; n = len(s)
    prov = reg.provisional.values
    H = data.hydro_features(s); X2 = data.h2_extra(s)
    R = data.rain_features(data.load_rain_hourly(), s.index)
    if use_gauge:
        G = data.gauge_features(pd.read_csv("data/processed/gauge_basin_daily.csv"), s.index)
    else:
        G = pd.DataFrame(index=s.index)
    XALL = pd.concat([H, X2, R, G], axis=1)
    H_cols, H2_cols, R_cols, G_cols = list(H.columns), list(H.columns) + list(X2.columns), list(R.columns), list(G.columns)
    SETS = {"H": H_cols, "H2": H2_cols, "H2+R": H2_cols + R_cols}
    if use_gauge:
        SETS.update({"H2+G": H2_cols + G_cols, "H2+R+G": H2_cols + R_cols + G_cols})
    tg = data.targets(s)
    clusters = events.storm_clusters(s); groups = splits.group_ids(s.index, clusters)
    lab, vs, ts = splits.chronological_split(s.index, clusters)
    fold, bounds = splits.blocked_folds(s.index, clusters)
    labv = lab.values; foldv = fold.values
    base_ok = XALL[data.REQUIRED_COLS].notna().all(axis=1).values & XALL[R_cols].notna().all(axis=1).values
    elig = {h: base_ok & tg[h].notna().values & s.notna().values for h in HZ}
    elev = ((s >= 5.0) | (XALL["d_3h"] >= 1.0)).fillna(False).values
    ev_all = {k: events.exceedance_events(s, t) for k, t in EXC.items()}
    ev_all.update({k: events.rapid_rise_events(s, t) for k, t in RAP.items()})
    kind_of = {k: ("exceed" if k in EXC else "rapid") for k in ev_all}
    thr_of = {**EXC, **RAP}
    protos = {"chrono_val": labv == "val", "chrono_test": labv == "test", "blocked_cv_NONCAUSAL": ~np.isnan(foldv)}
    years = {"chrono_test": (s.index[-1] - ts).days / 365.25, "blocked_cv_NONCAUSAL": (s.index[-1] - s.index[0]).days / 365.25, "chrono_val": (ts - vs).days / 365.25}
    log(f"rows {n}; eligible 1h train/val/test = {[(elig['1h'] & (labv == k)).sum() for k in ('train', 'val', 'test')]}; sets {list(SETS)}")

    def win_mask(ev, kind):
        m = np.zeros(n, bool)
        for e in ev.itertuples():
            lo = events.rise_onset_index(sv, e.i0) if kind == "exceed" else e.i0
            m[max(0, lo - 24):(e.peak_i if kind == "exceed" else e.i1) + 1] = True
        return m

    def events_in(defn, pmask):
        ev = ev_all[defn]
        return ev[pmask[ev.i0.values]].reset_index(drop=True) if len(ev) else ev

    val_win = np.zeros(n, bool)
    for dname in ("experimental_stage_10ft", "experimental_rise_4ft_3h"):
        val_win |= win_mask(events_in(dname, protos["chrono_val"]), kind_of[dname])
    RES["validation_event_counts"] = {d: len(events_in(d, protos["chrono_val"])) for d in ev_all}
    log(f"validation events: {RES['validation_event_counts']}")

    cache_raw, cache_lin = {}, {}

    def Xraw(name):
        if name not in cache_raw:
            cache_raw[name] = XALL[SETS[name]].values.astype(np.float32)
        return cache_raw[name]

    def Xlin(name):
        if name not in cache_lin:
            cache_lin[name] = data.prep_linear(XALL, SETS[name]).astype(np.float32)
        return cache_lin[name]

    def fit_reg(kind, set_name, h, lam, tr, va):
        y = tg[h].values; w = 1.0 + lam * elev
        X = Xlin(set_name) if kind == "ridge" else Xraw(set_name)
        best = None
        if kind == "ridge":
            for a in models.RIDGE_ALPHAS:
                m = models.fit_ridge(X[tr], y[tr], a, w[tr]); e = models.rmse(m.predict(X[va]), y[va])
                if best is None or e < best[0]:
                    best = (e, m, {"alpha": a})
        else:
            for d in models.XGB_DEPTHS:
                m, bi = models.fit_xgb(X[tr], y[tr], d, X[va], y[va], n_estimators=n_est, w=w[tr]); e = models.rmse(m.predict(X[va]), y[va])
                if best is None or e < best[0]:
                    best = (e, m, {"depth": d, "trees": bi})
        return best[1], best[2], best[1].predict(X[va])

    def window_rmse(pred_va, h, va):
        sel = val_win[va] & elig[h][va]
        yv = tg[h].values[va]
        return models.rmse(pred_va[sel], yv[sel]) if sel.sum() else np.nan

    # ---------------------------------------------------------------- A. feature-set selection (XGBoost, lambda = 0, validation)
    tr_idx = {h: elig[h] & (labv == "train") for h in HZ}; va_idx = {h: elig[h] & (labv == "val") for h in HZ}
    rowsA = []
    for sname in SETS:
        for h in HZ:
            _, par, pv = fit_reg("xgb", sname, h, 0.0, tr_idx[h], va_idx[h])
            vmask = va_idx[h]
            rowsA.append({"feature_set": sname, "horizon": h, "val_event_window_rmse": window_rmse(pv, h, vmask),
                          "val_all_row_rmse": models.rmse(pv, tg[h].values[vmask]), **par})
        log(f"A: feature set {sname} done")
    A = pd.DataFrame(rowsA); md(A, "A_feature_set_selection_validation")
    mean_win = A.groupby("feature_set").val_event_window_rmse.mean()
    best_set = mean_win.idxmin()
    adopted = best_set if (best_set == "H2" or mean_win[best_set] <= 0.95 * mean_win["H2"]) else "H2"
    RES["feature_set_mean_val_event_window_rmse"] = mean_win.to_dict(); RES["adopted_feature_set"] = adopted
    log(f"adopted feature set: {adopted} ({mean_win.round(4).to_dict()})")

    # ---------------------------------------------------------------- B. lambda selection (validation)
    rowsB = []
    for kind in ("ridge", "xgb"):
        for lam in LAMBDAS:
            for h in HZ:
                _, par, pv = fit_reg(kind, adopted, h, lam, tr_idx[h], va_idx[h])
                rowsB.append({"model": kind, "lambda": lam, "horizon": h, "val_event_window_rmse": window_rmse(pv, h, va_idx[h]),
                              "val_all_row_rmse": models.rmse(pv, tg[h].values[va_idx[h]]), **par})
        log(f"B: {kind} lambdas done")
    B = pd.DataFrame(rowsB); md(B, "B_lambda_selection_validation")
    chosen_lam = {}
    for kind in ("ridge", "xgb"):
        g = B[B.model == kind].groupby("lambda")[["val_event_window_rmse", "val_all_row_rmse"]].mean()
        lam = float(g.val_event_window_rmse.idxmin())
        if g.loc[lam, "val_all_row_rmse"] > 1.10 * g.loc[0.0, "val_all_row_rmse"]:
            lam = 0.0
        chosen_lam[kind] = lam
    RES["chosen_lambda"] = chosen_lam
    log(f"chosen lambda: {chosen_lam}")

    # ---------------------------------------------------------------- C. damped trend (validation)
    rowsC, trend_cfg = [], {}
    for h, k in data.HORIZONS.items():
        best = None
        for wn, ws in TREND_W.items():
            dcol = XALL[f"d_{wn}"].values
            for phi in TREND_PHI:
                ch = models.trend_change_v2(dcol, ws, k, phi)
                m = va_idx[h] & ~np.isnan(ch)
                e = models.rmse(ch[m & val_win], tg[h].values[m & val_win]) if (m & val_win).sum() else np.nan
                rowsC.append({"horizon": h, "window": wn, "phi": phi, "val_event_window_rmse": e,
                              "val_all_row_rmse": models.rmse(ch[m], tg[h].values[m])})
                if not np.isnan(e) and (best is None or e < best[0]):
                    best = (e, wn, ws, phi)
        trend_cfg[h] = {"window": best[1], "window_steps": best[2], "phi": best[3]}
    md(pd.DataFrame(rowsC), "C_trend_v2_grid_validation"); RES["trend_v2_selected"] = trend_cfg

    # ---------------------------------------------------------------- D. final regression models: val / test / blocked CV predictions
    pred = {p: {} for p in protos}
    tuned = {}
    final_specs = {"ridge_H0": ("ridge", "H", 0.0), "xgb_H0": ("xgb", "H", 0.0),
                   "ridge_B": ("ridge", adopted, chosen_lam["ridge"]), "xgb_B": ("xgb", adopted, chosen_lam["xgb"])}
    for h, k in data.HORIZONS.items():
        y = tg[h].values
        for pname in protos:
            for mname in ("persistence", "trend_p1a", "trend_v2"):
                if mname == "persistence":
                    ch = models.persistence_change(n)
                elif mname == "trend_p1a":
                    ch = models.trend_change(XALL["d_1h"].values, k)
                else:
                    c = trend_cfg[h]; ch = models.trend_change_v2(XALL[f"d_{c['window']}"].values, c["window_steps"], k, c["phi"])
                a = np.full(n, np.nan); mk = elig[h] & protos[pname] & ~np.isnan(ch); a[mk] = ch[mk]; pred[pname][(mname, h)] = a
        for mname, (kind, sname, lam) in final_specs.items():
            tr, va = tr_idx[h], va_idx[h]
            te = elig[h] & (labv == "test"); cv_ok = elig[h] & ~np.isnan(foldv)
            m_val, par, pv = fit_reg(kind, sname, h, lam, tr, va)
            a = np.full(n, np.nan); a[va] = pv; pred["chrono_val"][(mname, h)] = a
            X = Xlin(sname) if kind == "ridge" else Xraw(sname); w = 1.0 + lam * elev
            if kind == "ridge":
                m_fin = models.fit_ridge(X[tr | va], y[tr | va], par["alpha"], w[tr | va])
            else:
                m_fin, _ = models.fit_xgb(X[tr | va], y[tr | va], par["depth"], n_estimators=par["trees"], w=w[tr | va])
            a = np.full(n, np.nan); a[te] = m_fin.predict(X[te]); pred["chrono_test"][(mname, h)] = a
            a = np.full(n, np.nan)
            for f in range(int(np.nanmax(foldv)) + 1):
                trm, tem = cv_ok & (foldv != f), cv_ok & (foldv == f)
                if tem.sum() == 0:
                    continue
                if kind == "ridge":
                    a[tem] = models.fit_ridge(X[trm], y[trm], par["alpha"], w[trm]).predict(X[tem])
                else:
                    a[tem] = models.fit_xgb(X[trm], y[trm], par["depth"], n_estimators=par["trees"], w=w[trm])[0].predict(X[tem])
            pred["blocked_cv_NONCAUSAL"][(mname, h)] = a
            tuned[f"{mname}_{h}"] = {"kind": kind, "feature_set": sname, "lambda": lam, **par}
            joblib.dump(m_fin, FROZEN / f"model_{mname}_{h}.joblib")
        log(f"D: final regression models h={h} done")
    RES["tuned"] = tuned
    REG_MODELS = ["persistence", "trend_p1a", "trend_v2", "ridge_H0", "xgb_H0", "ridge_B", "xgb_B"]

    # ---------------------------------------------------------------- E. regression metrics
    win_sub = {"event_windows_stage10ft": win_mask(ev_all["experimental_stage_10ft"], "exceed"), "event_windows_rise4ft3h": win_mask(ev_all["experimental_rise_4ft_3h"], "rapid")}
    rows = []
    for pname, pm in protos.items():
        for h, k in data.HORIZONS.items():
            yc = tg[h].values
            for sub, smask in {"all": np.ones(n, bool), **win_sub}.items():
                base = elig[h] & pm & smask
                for mname in REG_MODELS:
                    a = pred[pname][(mname, h)]; mk = base & ~np.isnan(a)
                    if mk.sum() < 30:
                        continue
                    st = metrics.reg_stats(a[mk] - yc[mk], -yc[mk])
                    if pname != "chrono_val":
                        st.update(metrics.cluster_bootstrap(a[mk] - yc[mk], -yc[mk], groups[mk], b=300 if quick else 2000))
                    rows.append({"protocol": pname, "subset": sub, "horizon": h, "model": mname, **st})
    md(pd.DataFrame(rows), "E_regression_metrics")

    # ---------------------------------------------------------------- detection helpers
    def detect(raw, evp, k, elig_h, pname):
        """Event-level confusion for one alarm series. Alarm episodes are matched against ALL events (so an alarm near a
        not-evaluable event is not miscounted as false); POD etc. use evaluable events only (>= 50% minimal-input rows in lead window)."""
        if len(evp) == 0:
            return None, pd.DataFrame()
        ev_ok = np.array([elig_h[max(0, e.i0 - k - 4):e.i0 + 1].mean() >= 0.5 for e in evp.itertuples()])
        st = events.alarm_state(raw); a0, a1 = events.alarm_episodes(st)
        res_all, n_ep, n_fa = events.match(evp, a0, a1, k)
        res = res_all[ev_ok].reset_index(drop=True)
        n_ev = len(res)
        pe = res_all.copy(); pe.loc[~ev_ok, "status"] = "not_evaluable"
        if n_ev == 0:
            return None, pe
        early, late, miss = int((res.status == "early").sum()), int((res.status == "late").sum()), int((res.status == "miss").sum())
        pod_ci = metrics.clopper_pearson(early, n_ev); far_ci = metrics.clopper_pearson(n_fa, n_ep) if n_ep else (np.nan, np.nan)
        leads = res.lead_h.dropna()
        summ = {"n_events": n_ev, "n_not_evaluable": int((~ev_ok).sum()), "early_hits": early, "late": late, "misses": miss, "POD": early / n_ev,
                "POD_ci_lo": pod_ci[0], "POD_ci_hi": pod_ci[1], "alarm_episodes": n_ep, "false_alarm_episodes": n_fa,
                "precision_episode": (1 - n_fa / n_ep) if n_ep else np.nan, "FAR": n_fa / n_ep if n_ep else np.nan, "FAR_ci_lo": far_ci[0], "FAR_ci_hi": far_ci[1],
                "CSI": early / (early + late + miss + n_fa) if (early + late + miss + n_fa) else np.nan,
                "false_alarms_per_year": n_fa / years[pname], "median_lead_h": float(leads.median()) if len(leads) else np.nan,
                "lead_h_min": float(leads.min()) if len(leads) else np.nan, "lead_h_max": float(leads.max()) if len(leads) else np.nan,
                "independent_storm_clusters": int(len(np.unique(groups[res_all.i0.values[ev_ok]])))}
        return summ, pe

    def fixed_rule_raw(a, k, kind, thr):
        shat = sv + a
        ok = ~np.isnan(shat)
        if kind == "exceed":
            raw = shat >= thr
        else:
            raw = (shat - pd.Series(sv).shift(12 - k).values) >= thr
        return np.where(ok, raw, False)

    # ---------------------------------------------------------------- F. fixed-rule detection for the regression models
    rowsF, rowsFe = [], []
    for pname, pm in protos.items():
        for defn in ev_all:
            evp = events_in(defn, pm)
            for h, k in data.HORIZONS.items():
                for mname in REG_MODELS:
                    a = pred[pname][(mname, h)]
                    raw = fixed_rule_raw(np.where(np.isnan(a), np.nan, a), k, kind_of[defn], thr_of[defn]) & (~np.isnan(a))
                    summ, pe = detect(raw, evp, k, elig[h] & pm, pname)
                    if summ:
                        rowsF.append({"protocol": pname, "definition": defn, "horizon": h, "model": mname, **summ})
                    if len(pe):
                        pe = pe.assign(protocol=pname, definition=defn, horizon=h, model=mname, event_start=lambda d: d.t0, provisional_data=lambda d: [bool(prov[a_:b_ + 1].any()) for a_, b_ in zip(d.i0, d.i1)])
                        rowsFe.append(pe[["protocol", "definition", "horizon", "model", "event_start", "peak_ft", "status", "lead_h", "provisional_data"]])
        log(f"F: fixed-rule detection {pname} done")
    md(pd.DataFrame(rowsF), "F_fixed_rule_detection"); md(pd.concat(rowsFe), "F_fixed_rule_per_event")

    # ---------------------------------------------------------------- G. probability-based detection
    rowsG, rowsGe, rowsRL, rowsCal, rowsSw, rowsTh = [], [], [], [], [], []
    probs_store = {}
    learners = ["logistic", "xgb_plain", "xgb_weighted"]
    Xl, Xr = Xlin(adopted), Xraw(adopted)
    for tname, (kind, T) in PROB_TARGETS.items():
        for h, k in data.HORIZONS.items():
            if kind == "exceed":
                yy = s.shift(-k).values; ylab = (yy >= T).astype(float); yok = ~np.isnan(yy)
            else:
                a_, b_ = s.shift(-k).values, s.shift(12 - k).values; ylab = ((a_ - b_) >= T).astype(float); yok = ~(np.isnan(a_) | np.isnan(b_))
            rowsok = elig[h] & yok
            tr, va, te = rowsok & (labv == "train"), rowsok & (labv == "val"), rowsok & (labv == "test"); cvm = rowsok & ~np.isnan(foldv)
            npos_tr, npos_va = int(ylab[tr].sum()), int(ylab[va].sum())
            n_val_ev = len(events_in(tname, protos["chrono_val"]))
            if npos_tr < 30:
                rowsTh.append({"target": tname, "horizon": h, "learner": "all", "note": f"skipped: only {npos_tr} training positive rows"}); continue
            for lname in learners:
                if lname == "logistic":
                    m = models.fit_logit(Xl[tr], ylab[tr]); pva = m.predict_proba(Xl[va])[:, 1]; trees = None
                    pfun = lambda mask, m=m: m.predict_proba(Xl[mask])[:, 1]   # noqa: E731
                else:
                    spw = 1.0 if lname == "xgb_plain" else float(np.clip(np.sqrt((~tr[tr]).sum() * 0 + (ylab[tr] == 0).sum() / max(ylab[tr].sum(), 1)), 1, 30))
                    m, trees = models.fit_xgb_clf(Xr[tr], ylab[tr], 3, spw, Xr[va], ylab[va], n_estimators=n_clf)
                    pva = m.predict_proba(Xr[va])[:, 1]
                    pfun = lambda mask, m=m: m.predict_proba(Xr[mask])[:, 1]   # noqa: E731
                # threshold on validation rows: maximise F2 (ties -> higher theta)
                theta, best_f2 = None, -1
                if npos_va >= 30:
                    for th in THETAS:
                        pr = pva >= th; tp = float((pr & (ylab[va] == 1)).sum()); prec = tp / max(pr.sum(), 1); rec = tp / max(ylab[va].sum(), 1)
                        f = f2(prec, rec)
                        if f >= best_f2:
                            best_f2, theta = f, th
                rowsTh.append({"target": tname, "horizon": h, "learner": lname, "train_positive_rows": npos_tr, "val_positive_rows": npos_va, "independent_val_events": n_val_ev,
                               "theta": theta, "val_row_F2": best_f2 if theta is not None else np.nan, "xgb_trees": trees,
                               "note": "" if theta is not None else f"no threshold selectable: {npos_va} validation positive rows (< 30)"})
                if theta is None:
                    continue
                pte = np.full(n, np.nan); pte[te] = pfun(te)
                pva_full = np.full(n, np.nan); pva_full[va] = pva
                pcv = np.full(n, np.nan)
                for f in range(int(np.nanmax(foldv)) + 1):
                    trm, tem = cvm & (foldv != f), cvm & (foldv == f)
                    if tem.sum() == 0 or ylab[trm].sum() < 10:
                        continue
                    if lname == "logistic":
                        pcv[tem] = models.fit_logit(Xl[trm], ylab[trm]).predict_proba(Xl[tem])[:, 1]
                    else:
                        mm, _ = models.fit_xgb_clf(Xr[trm], ylab[trm], 3, spw, n_estimators=trees); pcv[tem] = mm.predict_proba(Xr[tem])[:, 1]
                probs_store[f"{tname}|{h}|{lname}"] = {"val": pva_full, "test": pte, "cv": pcv, "theta": theta}
                for pname, parr in (("chrono_val", pva_full), ("chrono_test", pte), ("blocked_cv_NONCAUSAL", pcv)):
                    raw = np.where(np.isnan(parr), False, parr >= theta)
                    summ, pe = detect(raw, events_in(tname, protos[pname]), k, elig[h] & protos[pname], pname)
                    if summ:
                        rowsG.append({"protocol": pname, "target": tname, "horizon": h, "learner": lname, "theta_from_validation": theta, **summ})
                    if len(pe):
                        pe = pe.assign(protocol=pname, target=tname, horizon=h, learner=lname, event_start=lambda d: d.t0)
                        rowsGe.append(pe[["protocol", "target", "horizon", "learner", "event_start", "peak_ft", "status", "lead_h"]])
                # row-level metrics, calibration and descriptive sweep on TEST rows
                pt, yt = pte[te], ylab[te]
                if yt.sum() > 0:
                    pr = pt >= theta; tp = float((pr & (yt == 1)).sum())
                    rowsRL.append({"target": tname, "horizon": h, "learner": lname, "theta": theta, "test_rows": int(te.sum()), "test_positive_rows": int(yt.sum()),
                                   "row_precision": tp / max(pr.sum(), 1), "row_recall": tp / yt.sum(), "AP": float(average_precision_score(yt, pt)),
                                   "brier": float(brier_score_loss(yt, pt)), "logloss": float(log_loss(yt, np.clip(pt, 1e-6, 1 - 1e-6), labels=[0, 1]))})
                    qs = np.unique(np.quantile(pt, np.linspace(0, 1, 11)))
                    bins = np.clip(np.searchsorted(qs[1:-1], pt, side="right"), 0, len(qs) - 2)
                    for bi_ in range(len(qs) - 1):
                        sel = bins == bi_
                        if sel.sum():
                            rowsCal.append({"target": tname, "horizon": h, "learner": lname, "bin": bi_, "n": int(sel.sum()), "mean_predicted": float(pt[sel].mean()), "observed_freq": float(yt[sel].mean())})
                for th in (0.1, 0.3, 0.5, 0.7, 0.9):
                    raw = np.where(np.isnan(pte), False, pte >= th)
                    summ, _ = detect(raw, events_in(tname, protos["chrono_test"]), k, elig[h] & protos["chrono_test"], "chrono_test")
                    if summ:
                        rowsSw.append({"target": tname, "horizon": h, "learner": lname, "theta_sweep_descriptive_only": th, **{c: summ[c] for c in ("n_events", "early_hits", "late", "misses", "alarm_episodes", "false_alarm_episodes", "POD", "FAR", "CSI", "median_lead_h")}})
            log(f"G: {tname} h={h} done")
    md(pd.DataFrame(rowsTh), "G_threshold_selection_validation"); md(pd.DataFrame(rowsG), "G_prob_detection_event_level"); md(pd.concat(rowsGe), "G_prob_detection_per_event")
    md(pd.DataFrame(rowsRL), "G_prob_row_level_test"); md(pd.DataFrame(rowsCal), "G_prob_calibration_test"); md(pd.DataFrame(rowsSw), "G_threshold_sweep_test_descriptive")

    # independent event counts by protocol (events and distinct storm clusters)
    ie = []
    for defn in ev_all:
        for pname, pm in protos.items():
            e_ = events_in(defn, pm)
            ie.append({"definition": defn, "protocol": pname, "events": len(e_), "distinct_storm_clusters": int(len(np.unique(groups[e_.i0.values]))) if len(e_) else 0})
    md(pd.DataFrame(ie), "independent_event_counts")

    # ---------------------------------------------------------------- frozen artifacts (hashes, predictions, configs)
    arrays = {}
    for pname in ("chrono_val", "chrono_test", "blocked_cv_NONCAUSAL"):
        for (mname, h), a in pred[pname].items():
            arrays[f"reg|{pname}|{mname}|{h}"] = a.astype(np.float32)
    for key, d in probs_store.items():
        for part in ("val", "test", "cv"):
            arrays[f"prob|{key}|{part}"] = d[part].astype(np.float32)
    np.savez_compressed(FROZEN / "predictions.npz", index=s.index.asi8, **arrays)
    sha = hashlib.sha256(open(FROZEN / "predictions.npz", "rb").read()).hexdigest()
    cfg = {"frozen_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), "predictions_sha256": sha, "adopted_feature_set": adopted, "chosen_lambda": chosen_lam,
           "trend_v2": trend_cfg, "tuned": tuned, "boundaries": {"val_start": str(vs), "test_start": str(ts)}, "versions": {"pandas": pd.__version__, "numpy": np.__version__},
           "note": "Test period was already inspected before Phase 1B; results on it are exploratory. Events after 2026-11-22 can serve as a prospective check."}
    (FROZEN / "config.json").write_text(json.dumps(cfg, indent=2, default=str))
    (OUT / "results.json").write_text(json.dumps(RES, indent=2, default=str))
    log("done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); ap.add_argument("--no-gauge", action="store_true")
    a = ap.parse_args(); main(a.quick, not a.no_gauge)
