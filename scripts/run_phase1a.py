"""Phase 1A: persistence / trend / ridge / XGBoost baselines for stage at USGS 08167500.

Implements docs/PHASE1A_PROTOCOL.md exactly.  Outputs: reports/phase1a/{tables,figures}, results.json.
Usage: python scripts/run_phase1a.py [--quick]      (--quick: fewer XGBoost trees, for smoke testing only)
"""
import argparse
import json
import time
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from flashflood import data, events, metrics, models, splits  # noqa: E402

warnings.filterwarnings("ignore")
OUT = Path("reports/phase1a")
TAB, FIG = OUT / "tables", OUT / "figures"
for p in (TAB, FIG):
    p.mkdir(parents=True, exist_ok=True)

HZ = list(data.HORIZONS)                                    # 15m, 30m, 1h, 3h
EXCEED = {"official_action_25ft": 25.0, "official_minor_30ft": 30.0, "official_moderate_36ft": 36.0,
          "experimental_stage_10ft": 10.0, "experimental_stage_15ft": 15.0}
RAPID = {"experimental_rise_4ft_3h": 4.0, "experimental_rise_8ft_3h": 8.0}
MODELS = ["persistence", "trend", "ridge_H", "ridge_HR", "xgb_H", "xgb_HR"]
C = dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#e6e5e1", s1="#2a78d6", s2="#eb6834", s3="#1baf7a")
plt.rcParams.update({"figure.facecolor": C["surface"], "axes.facecolor": C["surface"], "savefig.facecolor": C["surface"], "axes.edgecolor": C["grid"],
                     "axes.labelcolor": C["ink2"], "text.color": C["ink"], "xtick.color": C["ink2"], "ytick.color": C["ink2"],
                     "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left"})
RES: dict = {}


def md(df, name, index=False):
    df.to_csv(TAB / f"{name}.csv", index=index)
    (TAB / f"{name}.md").write_text(df.to_markdown(index=index, floatfmt=".3g"))


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main(quick: bool, legacy: bool = False) -> None:
    n_est = 80 if quick else 600
    reg = data.load_stage()
    s = reg.s
    p_hr = data.load_rain_hourly()
    H, R = data.hydro_features(s, strict=legacy), data.rain_features(p_hr, s.index)
    X = pd.concat([H, R], axis=1)
    H_cols, HR_cols = list(H.columns), list(H.columns) + list(R.columns)
    tg = data.targets(s)
    clusters = events.storm_clusters(s)
    groups = splits.group_ids(s.index, clusters)
    lab, vs, ts = splits.chronological_split(s.index, clusters)
    fold, bounds = splits.blocked_folds(s.index, clusters)
    prov = reg.provisional.values
    sv = s.values
    n = len(s)
    log(f"grid {n} rows; valid stage {int(s.notna().sum())}; storm clusters {len(clusters)}; val starts {vs}; test starts {ts}")
    RES["boundaries"] = {"val_start": str(vs), "test_start": str(ts), "blocked_cv_bounds": [str(b) for b in bounds]}

    # ---------------------------------------------------------------- eligibility + counts
    elig = {}
    cnt = [{"item": "15-min grid rows", "n": n}, {"item": "valid stage rows", "n": int(s.notna().sum())},
           {"item": "rows masked as sensor-floor (stage <= -1.2 ft)", "n": int((reg.stage_ft <= data.FLOOR_FT).sum())},
           {"item": "rows with complete hydrology features", "n": int(H.notna().all(axis=1).sum())},
           {"item": "rows with complete hydrology+rain features", "n": int(X[HR_cols].notna().all(axis=1).sum())},
           {"item": "storm clusters (>=5 ft or >=1 ft/3h, <72 h merged)", "n": len(clusters)}]
    for h, k in data.HORIZONS.items():
        e = (X[HR_cols].notna().all(axis=1) & tg[h].notna() & s.notna()).values
        elig[h] = e
        for split in ("train", "val", "test"):
            cnt.append({"item": f"eligible rows h={h} {split}", "n": int((e & (lab.values == split)).sum())})
    md(pd.DataFrame(cnt), "data_prep_counts")

    # ---------------------------------------------------------------- models: chronological + blocked CV
    pred_chrono, pred_val, pred_cv = {}, {}, {}      # (model,h) -> np.array of CHANGE predictions (NaN where none)
    tuned = {}
    for h, k in data.HORIZONS.items():
        y = tg[h].values
        e = elig[h]
        tr, va, te = e & (lab.values == "train"), e & (lab.values == "val"), e & (lab.values == "test")
        cv_ok = e & ~np.isnan(fold.values)
        for model in ("persistence", "trend"):
            ch = models.persistence_change(n) if model == "persistence" else models.trend_change(H["d_1h"].values, k)
            for store, msk in ((pred_chrono, te), (pred_val, va), (pred_cv, cv_ok)):
                a = np.full(n, np.nan); a[msk] = ch[msk]; store[(model, h)] = a
        for fs_name, cols in (("H", H_cols), ("HR", HR_cols)):
            Xv = X[cols].values
            # ridge: tune alpha on validation (train-only fit)
            best = min(((models.rmse(models.fit_ridge(Xv[tr], y[tr], a).predict(Xv[va]), y[va]), a) for a in models.RIDGE_ALPHAS))
            alpha = best[1]
            m_val = models.fit_ridge(Xv[tr], y[tr], alpha)
            a = np.full(n, np.nan); a[va] = m_val.predict(Xv[va]); pred_val[(f"ridge_{fs_name}", h)] = a
            m_fin = models.fit_ridge(Xv[tr | va], y[tr | va], alpha)
            a = np.full(n, np.nan); a[te] = m_fin.predict(Xv[te]); pred_chrono[(f"ridge_{fs_name}", h)] = a
            # xgboost: tune depth on validation with early stopping
            runs = []
            for d in models.XGB_DEPTHS:
                m, bi = models.fit_xgb(Xv[tr], y[tr], d, Xv[va], y[va], n_estimators=n_est)
                runs.append((models.rmse(m.predict(Xv[va]), y[va]), d, bi, m))
            _, depth, best_iter, m_best = min(runs, key=lambda r: r[0])
            a = np.full(n, np.nan); a[va] = m_best.predict(Xv[va]); pred_val[(f"xgb_{fs_name}", h)] = a
            m_fin, _ = models.fit_xgb(Xv[tr | va], y[tr | va], depth, n_estimators=best_iter)
            a = np.full(n, np.nan); a[te] = m_fin.predict(Xv[te]); pred_chrono[(f"xgb_{fs_name}", h)] = a
            tuned[f"{fs_name}_{h}"] = {"ridge_alpha": alpha, "xgb_depth": depth, "xgb_trees": best_iter}
            log(f"chrono h={h} {fs_name}: ridge alpha={alpha}, xgb depth={depth} trees={best_iter}")
            # blocked CV with the hyperparameters fixed from the chronological validation (no tuning on folds)
            ar, ax = np.full(n, np.nan), np.full(n, np.nan)
            for f in range(int(np.nanmax(fold.values)) + 1):
                trm, tem = cv_ok & (fold.values != f), cv_ok & (fold.values == f)
                if tem.sum() == 0:
                    continue
                ar[tem] = models.fit_ridge(Xv[trm], y[trm], alpha).predict(Xv[tem])
                mm, _ = models.fit_xgb(Xv[trm], y[trm], depth, n_estimators=best_iter)
                ax[tem] = mm.predict(Xv[tem])
            pred_cv[(f"ridge_{fs_name}", h)], pred_cv[(f"xgb_{fs_name}", h)] = ar, ax
            log(f"blocked-CV h={h} {fs_name} done")
    RES["tuned"] = tuned

    # ---------------------------------------------------------------- regression metrics
    def true_change(h):
        return tg[h].values

    def windows(ev, kind):
        idx = np.zeros(n, bool)
        for e in ev.itertuples():
            lo = events.rise_onset_index(sv, e.i0) if kind == "exceed" else e.i0
            idx[max(0, lo - 24):(e.peak_i if kind == "exceed" else e.i1) + 1] = True
        return idx

    ev_all = {name: events.exceedance_events(s, T) for name, T in EXCEED.items()}
    ev_all.update({name: events.rapid_rise_events(s, T) for name, T in RAPID.items()})
    kinds = {name: ("exceed" if name in EXCEED else "rapid") for name in ev_all}
    protos = {"chrono_test": (pred_chrono, lab.values == "test"), "chrono_val": (pred_val, lab.values == "val"),
              "blocked_cv_NONCAUSAL": (pred_cv, ~np.isnan(fold.values))}
    reg_rows = []
    for pname, (pred, pmask) in protos.items():
        per_sub = {"all": np.ones(n, bool), "approved_only": ~prov, "event_windows_stage10ft": windows(ev_all["experimental_stage_10ft"], "exceed"),
                   "event_windows_rise4ft3h": windows(ev_all["experimental_rise_4ft_3h"], "rapid")}
        for h, k in data.HORIZONS.items():
            yc = true_change(h)
            for sub, smask in per_sub.items():
                base = elig[h] & pmask & smask
                if sub == "approved_only":
                    base &= ~np.r_[prov[k:], np.zeros(k, bool)]
                for mod in MODELS:
                    a = pred[(mod, h)]
                    mk = base & ~np.isnan(a)
                    if mk.sum() < 50:
                        continue
                    st = metrics.reg_stats(a[mk] - yc[mk], -yc[mk])
                    if sub in ("all", "event_windows_stage10ft", "event_windows_rise4ft3h") and pname != "chrono_val":
                        st.update(metrics.cluster_bootstrap(a[mk] - yc[mk], -yc[mk], groups[mk], b=300 if quick else 2000))
                    reg_rows.append({"protocol": pname, "subset": sub, "horizon": h, "model": mod, **st})
    reg_df = pd.DataFrame(reg_rows)
    md(reg_df, "regression_metrics")

    # ---------------------------------------------------------------- event detection + per-event tables
    det_rows, per_event = [], []
    years = {"chrono_test": (s.index[-1] - ts).days / 365.25, "blocked_cv_NONCAUSAL": (s.index[-1] - s.index[0]).days / 365.25,
             "chrono_val": (ts - vs).days / 365.25}
    for pname, (pred, pmask) in protos.items():
        for defn, ev in ev_all.items():
            kind = kinds[defn]
            thr = EXCEED.get(defn, RAPID.get(defn))
            evp = ev[pmask[ev.i0.values]].reset_index(drop=True) if len(ev) else ev
            if len(evp) == 0:
                continue
            win = windows(evp, kind)
            for h, k in data.HORIZONS.items():
                yc = true_change(h)
                base_rise = pd.Series(sv).shift(12 - k).values       # s(t+h-3h): observed at issue time
                # an event is EVALUABLE only if >= 80% of the issue times that could earn lead credit are eligible rows
                ev_ok = np.array([elig[h][max(0, e.i0 - k - 4):e.i0 + 1].mean() >= 0.8 for e in evp.itertuples()]) if not legacy else np.ones(len(evp), bool)
                n_ne = int((~ev_ok).sum())
                for e in evp[~ev_ok].itertuples():
                    for mod in MODELS:
                        per_event.append({"protocol": pname, "definition": defn, "event_start": e.t0, "peak_ft": e.peak_ft, "horizon": h, "model": mod,
                                          "status": "not_evaluable", "provisional_data": bool(prov[e.i0:e.i1 + 1].any())})
                evh = evp[ev_ok].reset_index(drop=True)
                if len(evh) == 0:
                    continue
                for mod in MODELS:
                    a = pred[(mod, h)]
                    ok = elig[h] & pmask & ~np.isnan(a)
                    shat = np.where(ok, sv + a, np.nan)
                    raw = (shat >= thr) if kind == "exceed" else ((shat - base_rise) >= thr)
                    raw = np.where(ok & ~np.isnan(shat), raw, False)
                    st = events.alarm_state(raw)
                    a0, a1 = events.alarm_episodes(st)
                    res_ev, n_ep, n_fa = events.match(evh, a0, a1, k)
                    n_ev = len(evh)
                    early = int((res_ev.status == "early").sum()); late = int((res_ev.status == "late").sum()); miss = int((res_ev.status == "miss").sum())
                    pod_ci = metrics.clopper_pearson(early, n_ev)
                    far_ci = metrics.clopper_pearson(n_fa, n_ep) if n_ep else (np.nan, np.nan)
                    leads = res_ev.lead_h.dropna()
                    det_rows.append({"protocol": pname, "definition": defn, "horizon": h, "model": mod, "n_events": n_ev, "n_not_evaluable": n_ne,
                                     "early_hits": early, "late": late, "misses": miss, "POD": early / n_ev, "POD_ci_lo": pod_ci[0], "POD_ci_hi": pod_ci[1],
                                     "alarm_episodes": n_ep, "false_alarms": n_fa, "FAR": n_fa / n_ep if n_ep else np.nan, "FAR_ci_lo": far_ci[0], "FAR_ci_hi": far_ci[1],
                                     "CSI": early / (early + late + miss + n_fa) if (early + late + miss + n_fa) else np.nan,
                                     "false_alarms_per_year": n_fa / years[pname], "median_lead_h": float(leads.median()) if len(leads) else np.nan})
                    # per-event rows: detection + peak capture + window error
                    for e, r in zip(evh.itertuples(), res_ev.itertuples()):
                        lo = events.rise_onset_index(sv, e.i0) if kind == "exceed" else e.i0
                        w = np.zeros(n, bool); w[max(0, lo - 24):(e.peak_i if kind == "exceed" else e.i1) + 1] = True
                        mk = w & ok
                        pi = e.peak_i - k
                        peak_hat = float(shat[pi]) if pi >= 0 and not np.isnan(shat[pi]) else np.nan
                        per_event.append({"protocol": pname, "definition": defn, "event_start": e.t0, "peak_ft": e.peak_ft, "horizon": h, "model": mod,
                                          "status": r.status, "lead_h": r.lead_h, "peak_forecast_ft": peak_hat, "peak_error_ft": peak_hat - e.peak_ft,
                                          "peak_ratio": peak_hat / e.peak_ft if not np.isnan(peak_hat) else np.nan,
                                          "window_n": int(mk.sum()),
                                          "window_rmse_ft": models.rmse(a[mk], yc[mk]) if mk.sum() else np.nan,
                                          "window_rmse_persistence_ft": float(np.sqrt(np.mean(yc[mk] ** 2))) if mk.sum() else np.nan,
                                          "provisional_data": bool(prov[e.i0:e.i1 + 1].any())})
    det = pd.DataFrame(det_rows)
    md(det, "event_detection")
    md(pd.DataFrame(per_event), "per_event_results")
    # independent-event disclosure table
    disc = []
    for defn, ev in ev_all.items():
        for pname, (_, pmask) in protos.items():
            if len(ev):
                evp = ev[pmask[ev.i0.values]]
                cl = np.unique(groups[evp.i0.values]) if len(evp) else []
                disc.append({"definition": defn, "protocol": pname, "events": len(evp), "distinct_storm_clusters": len(cl)})
    md(pd.DataFrame(disc), "independent_event_counts")
    figures(reg, s, pred_chrono, tg, ev_all, ts, reg_df)
    (OUT / "results.json").write_text(json.dumps(RES, indent=2, default=str))
    log("done")


def figures(reg, s, pred_chrono, tg, ev_all, ts, reg_df):
    sub = reg_df[(reg_df.protocol == "chrono_test") & (reg_df.subset == "all")]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    cols = {"ridge_H": C["s3"], "xgb_H": C["s1"], "xgb_HR": C["s2"]}
    for ax, metric, ci in ((axes[0], "skill_vs_persistence", "skill_ci"), (axes[1], "rmse", "rmse_ci")):
        for j, (mod, col) in enumerate(cols.items()):
            d = sub[sub.model == mod].set_index("horizon").reindex(HZ)
            x = np.arange(len(HZ)) + (j - 1) * 0.22
            ax.bar(x, d[metric], width=0.2, color=col, label=mod)
            if ci in d:
                lo = np.array([c[0] for c in d[ci]]); hi = np.array([c[1] for c in d[ci]])
                ax.errorbar(x, d[metric], yerr=[d[metric] - lo, hi - d[metric]], fmt="none", ecolor=C["ink2"], lw=0.8, capsize=2)
        ax.set_xticks(range(len(HZ))); ax.set_xticklabels(HZ); ax.grid(axis="x", visible=False)
    axes[0].set_title("Test: skill vs persistence (all rows; 95% storm-cluster CI)"); axes[1].set_title("Test: RMSE (ft)")
    axes[0].set_ylabel("skill (0 = persistence)"); axes[1].set_ylabel("RMSE (ft)"); axes[0].legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "fig1_test_skill_rmse.png", dpi=150); plt.close(fig)

    ev = ev_all["official_action_25ft"]
    ev = ev[ev.t0 >= ts]
    if len(ev):
        fig, axes = plt.subplots(1, len(ev), figsize=(5 * len(ev), 3.6), squeeze=False)
        for ax, e in zip(axes[0], ev.itertuples()):
            a, b = e.t0 - pd.Timedelta("1D"), e.t1 + pd.Timedelta("1D")
            ax.plot(s.loc[a:b].index, s.loc[a:b].values, color=C["ink"], lw=1.4, label="observed")
            for h, col in (("1h", C["s3"]), ("3h", C["s2"])):
                k = data.HORIZONS[h]
                pc = pd.Series(pred_chrono[("xgb_H", h)], index=s.index)
                f = (s + pc).shift(k)                                    # forecast issued k steps earlier, plotted at target time
                ax.plot(f.loc[a:b].index, f.loc[a:b].values, color=col, lw=1.1, label=f"XGB (H) {h} ahead")
            p3 = s.shift(data.HORIZONS["3h"]); ax.plot(p3.loc[a:b].index, p3.loc[a:b].values, color=C["ink2"], lw=0.9, ls="--", label="persistence 3h")
            ax.set_title(f"{e.t0:%Y-%m-%d}  peak {e.peak_ft:.1f} ft (test event)", fontsize=9); ax.set_ylabel("stage (ft)")
            ax.tick_params(axis="x", labelrotation=30, labelsize=7)
        axes[0, 0].legend(frameon=False, fontsize=7)
        fig.tight_layout(); fig.savefig(FIG / "fig2_test_events_forecasts.png", dpi=150); plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--legacy", action="store_true", help="reproduce the ORIGINAL first run (strict features, no not-evaluable rule)")
    ap.add_argument("--out", default="reports/phase1a")
    a = ap.parse_args()
    OUT = Path(a.out)
    TAB, FIG = OUT / "tables", OUT / "figures"
    for _p in (TAB, FIG):
        _p.mkdir(parents=True, exist_ok=True)
    main(a.quick, a.legacy)
