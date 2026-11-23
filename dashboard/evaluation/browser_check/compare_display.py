"""Compare what the faculty dashboard DISPLAYED (dump from dump_display.js) with values recomputed from the project's saved result tables.
Usage (project root):  .venv/bin/python dashboard/evaluation/browser_check/compare_display.py out.json
This check is optional (it needs Playwright for the dump step); it is not part of pytest."""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(".")
PAGE_DIR = ROOT / "dashboard/evaluation"
HZ = ["15m", "30m", "1h", "3h"]
HLAB = {"15m": "15 min", "30m": "30 min", "1h": "1 hour", "3h": "3 hours"}
LABEL = {"persistence": "Persistence", "trend_v2": "Damped trend", "ridge_H": "Ridge regression", "xgb_H": "XGBoost", "lstm": "LSTM", "gru": "GRU", "transformer": "Transformer"}
ORDER = ["persistence", "trend_v2", "ridge_H", "xgb_H", "lstm", "gru", "transformer"]
checks, fails = [], []


def ok(name, cond, detail=""):
    checks.append(name)
    if not cond:
        fails.append(f"{name}: {detail}")


def f(txt):
    """parse a displayed number ('−' is a minus sign; '—' means none)"""
    t = txt.replace("−", "-").replace(",", "").replace("%", "").replace("+", "").strip()
    return None if t in ("—", "") else float(t)


def near(shown, expect, dec, label):
    if expect is None or (isinstance(expect, float) and np.isnan(expect)):
        ok(label, shown == "—", f"shown {shown!r}, expected none")
        return
    s = f(shown)
    ok(label, s is not None and abs(s - expect) <= 0.5 * 10 ** (-dec) + 1e-9, f"shown {shown}, expected {expect:.{dec + 2}f}")


def sgn(v, d):
    return ("+" if v > 0 else "−" if v < 0 else "") + f"{abs(v):.{d}f}"


def main(dump_path: str) -> int:
    D = json.loads(Path(dump_path).read_text())
    ok("no console errors or warnings", D["errors"] == [], str(D["errors"][:3]))
    d1 = pd.read_csv("reports/phase1d/tables/D1_pooled_regression_metrics.csv")
    c1 = pd.read_csv("reports/phase1c/tables/C1_regression_metrics.csv")
    c1 = c1[c1.protocol == "chrono_test"].assign(model=lambda d: d.model.replace({"ridge_H0": "ridge_H", "xgb_H0": "xgb_H"}))

    # ---- headline stat cards
    p0 = json.loads(Path("reports/phase0/phase0_results.json").read_text())["hydro"]
    d6 = pd.read_csv("reports/phase1d/tables/D6_event_coverage_and_exclusions.csv")
    ev18 = int(d6[(d6.definition == "experimental_stage_10ft") & (d6.status == "evaluated")].events.iloc[0])
    folds = len(pd.read_csv("reports/phase1d/fold_specification.csv"))
    official = json.loads(Path("reports/phase0/phase0_results.json").read_text())["events"]["n_events_action"]
    reg = len(json.loads(Path("experiments/registry.json").read_text())["entries"])
    col = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "--ignore=tests/test_evaluation_dashboard.py", "-p", "no:cacheprovider"], capture_output=True, text=True)
    n_tests = len([l for l in col.stdout.splitlines() if "::" in l])
    got = [s["n"].replace(",", "") for s in D["stats"]]
    ok("stat cards", got == [str(p0["rows_raw"]), str(ev18), str(folds), str(official), str(n_tests), str(reg)], f"{got} vs {[p0['rows_raw'], ev18, folds, official, n_tests, reg]}")

    # ---- model comparison: all 32 interactive states
    for rec in D["models"]:
        src = d1 if rec["ev"] == "cv" else c1
        for side, subset in (("left", "all"), ("right", rec["s"])):
            rows = D["models"][D["models"].index(rec)][side][1:]                      # drop header
            sub = src[(src.subset == subset) & (src.horizon == rec["h"])].set_index("model")
            exp_models = [m for m in ORDER if m in sub.index]
            ok(f"models/{rec['ev']}/{rec['h']}/{rec['m']}/{subset} row order", [r[0] for r in rows] == [LABEL[m] for m in exp_models], str([r[0] for r in rows]))
            for r, m in zip(rows, exp_models):
                s = sub.loc[m]
                if rec["m"] == "rmse":
                    near(r[1], float(s.rmse_ft), 4, f"{rec['ev']}/{rec['h']}/{subset}/{m} rmse"); near(r[2], float(s.rmse_ci_lo), 4, f"{m} ci lo"); near(r[3], float(s.rmse_ci_hi), 4, f"{m} ci hi")
                else:
                    near(r[1], float(s.skill_vs_persistence), 3, f"{rec['ev']}/{rec['h']}/{subset}/{m} skill")
                    if rec["ev"] == "cv":
                        near(r[2], float(s.skill_ci_lo), 3, f"{m} skill lo"); near(r[3], float(s.skill_ci_hi), 3, f"{m} skill hi")
                ok(f"{rec['ev']}/{rec['h']}/{subset}/{m} rows", int(r[4].replace(",", "")) == int(s.n_rows), r[4])
        # the 'reading' sentence names the best non-reference model
        sub = src[(src.subset == "all") & (src.horizon == rec["h"]) & (src.model != "persistence")].set_index("model")
        best = (sub.rmse_ft.idxmin() if rec["m"] == "rmse" else sub.skill_vs_persistence.idxmax())
        ok(f"readout best/{rec['ev']}/{rec['h']}/{rec['m']}", f"point estimate is {LABEL[best]} (" in rec["readout"], rec["readout"][:160])
    ok("32 interactive model states checked (2 evidence sets x 4 horizons x 2 metrics x 2 subsets)", len(D["models"]) == 32, str(len(D["models"])))

    # ---- findings (displayed tables and sentences), repeated at every horizon setting
    fl = d1[d1.subset == "event_windows_stage10ft"].set_index(["horizon", "model"]).rmse_ft
    for fd in D["findings"]:
        h = fd["h"]
        hdr, *rows = fd["f1t"]
        for r, x in zip(rows, HZ):
            for m, cell in zip(["persistence", "trend_v2", "xgb_H", "lstm", "gru"], r[1:6]):
                exp = (fl[(x, m)] / fl[(x, "ridge_H")] - 1) * 100
                ok(f"f1 table {x}/{m}", cell == sgn(exp, 1) + "%", f"{cell} vs {sgn(exp, 1)}%")
            near(r[6], float(fl[(x, "ridge_H")]), 3, f"f1 ridge {x}")
        chart = [t for t in fd["f1"] if t.endswith("%") and t[0] in "+−-"]
        exp_c = [sgn((fl[(h, m)] / fl[(h, "ridge_H")] - 1) * 100, 1) + "%" for m in ["persistence", "trend_v2", "xgb_H", "lstm", "gru"]]
        ok(f"f1 chart labels at {h}", chart == exp_c, f"{chart} vs {exp_c}")
    fd = D["findings"][0]
    c2 = pd.read_csv("reports/phase1c/tables/C2b_posthoc_vs_ridge_and_trend.csv")
    c2 = c2[(c2.subset == "event_windows_stage10ft") & (c2.reference == "ridge_H0") & (c2.model == "gru")].set_index("horizon")
    d3 = pd.read_csv("reports/phase1d/tables/D3_paired_model_differences.csv")
    d3 = d3[(d3.subset == "event_windows_stage10ft") & (d3.reference == "ridge_H") & (d3.model == "gru")].set_index("horizon")
    rows = fd["f2t"][1:]
    for r, (src, x) in zip(rows, [(c2, h) for h in HZ] + [(d3, h) for h in HZ]):
        ok(f"f2 {r[0][:9]} {x}", r[1] == HLAB[x] and r[2] == sgn(src.loc[x, "rmse_diff_ft"], 3) and r[3] == sgn(src.loc[x, "ci_lo"], 3) and r[4] == sgn(src.loc[x, "ci_hi"], 3), str(r))
    det = pd.read_csv("reports/phase1d/tables/D5_fixed_rule_detection_pooled_oof.csv")
    det = det[(det.definition == "experimental_rise_4ft_3h") & (det.horizon == "3h")].set_index("model")
    ok("f2 sentence rapid-rise hits", all(f" {int(det.loc[m, 'early_hits'])} ({n})" in fd["f2a"] for m, n in [("ridge_H", "ridge"), ("trend_v2", "damped trend"), ("gru", "GRU"), ("lstm", "LSTM")]), fd["f2a"][-200:])
    o3b = pd.read_csv("reports/phase1e_onset/tables/O3b_median_lead_by_variant.csv")
    o3b = o3b[(o3b.horizon == "3h") & o3b.variant.isin(["GRU 24 h (all seeds)", "GRU 72 h (all seeds)", "persistence", "trend_v2", "ridge_H"])]
    for r, (_, s) in zip(fd["f3t"][1:], o3b.iterrows()):
        near(r[1], float(s.lead_f10_h), 3, "f3 lead10"); near(r[2], float(s.lead_f50_h), 3, "f3 lead50"); near(r[3], float(s.lead_f90_h), 3, "f3 lead90"); near(r[4], 3 - float(s.lead_f50_h), 2, "f3 lag50")
    ex = pd.read_csv("reports/phase1d/oof_predictions.csv.gz", usecols=["timestamp_utc", "stage_ft", "pred_gru_3h_ft"])
    ex = ex[(ex.timestamp_utc >= "2025-07-04 21:00") & (ex.timestamp_utc <= "2025-07-05 21:00")].reset_index(drop=True)
    i_obs = int((ex.stage_ft >= 10).values.argmax()); i_gru = int((ex.pred_gru_3h_ft >= 10).values.argmax())
    lag_h = (i_gru + 12 - i_obs) * 0.25
    ok("f3 example lag sentence", f"{lag_h:.2f} h" in fd["f3a"] and f"{lag_h:.2f} h later" in " ".join(fd["f3c"]), f"{lag_h:.2f} not in {fd['f3a'][:120]}")
    lag50 = 3 - float(o3b[o3b.variant == "GRU 24 h (all seeds)"].lead_f50_h.iloc[0])
    ok("f3 median lag sentence", f"median {lag50:g} h" in fd["f3a"], fd["f3a"][100:260])
    o3c = pd.read_csv("reports/phase1e_onset/tables/O3c_issue_time_of_first_forecast_vs_onset.csv")
    g = o3c[(o3c.horizon == "3h") & (o3c.level == "50% of the rise") & (o3c.variant == "GRU 24 h")].iloc[0]
    ok("f3 before-onset sentence", f"<b>{0}</b>" not in fd["f3e"] and f": 0." in fd["f3e"] and f"{g.median_issue_vs_onset_h:.2f} h after the onset" in fd["f3e"], fd["f3e"])
    ok("f3 max events before onset is 0 across all variants/horizons", int(o3c[o3c.level == "50% of the rise"].events_first_forecast_issued_before_onset_any_seed.max()) == 0)
    s1 = pd.read_csv("reports/upstream_protocol_support/tables/S1_event_availability_18.csv").sort_values("event_start_utc")
    for r, (_, s) in zip(fd["f4t"][1:], s1.iterrows()):
        ok(f"f4 {s.event_start_utc[:10]}", r[0] == s.event_start_utc and r[2] == s.proposed_class and r[5] == str(int(s.fold)) and r[6] == str(int(s.storm_cluster)), str(r))
        near(r[1], float(s.peak_ft), 2, "f4 peak"); near(r[3], s.v2_best_lead_h_15min_grid if pd.notna(s.v2_best_lead_h_15min_grid) else None, 2, "f4 lead v2"); near(r[4], s.v3_best_lead_h_15min_grid if pd.notna(s.v3_best_lead_h_15min_grid) else None, 2, "f4 lead v3")
    up = s1[s1.proposed_class == "upstream-led"].v2_best_lead_h_15min_grid
    ok("f4 sentence", f"{up.min():g} to {up.max():g} hours" in fd["f4a"] and "In 6 of the 18" in fd["f4a"], fd["f4a"][:200])
    e3 = pd.read_csv("reports/phase1e/tables/E3_decision_rule.csv")
    for r, (_, s) in zip(fd["f5t"][1:], e3.iterrows()):
        ok(f"f5 {s.horizon}", r[0] == HLAB[s.horizon] and r[1] == sgn(s.flood10_pooled_diff, 4) and r[2] == s.flood10_ci and r[3] == s["(ii) folds 72h better (need >=4 of 6)"] and r[4] == s["(iii) seeds 72h better (need 3 of 3)"] and r[5] == ("yes" if s["CONSISTENT IMPROVEMENT"] else "no"), str(r))
    e8 = pd.read_csv("reports/phase1e/tables/E8_training_diagnostics.csv")
    slow = e8[e8.window_h == 72].train_seconds.median() / e8[e8.window_h == 24].train_seconds.median()
    ok("f5 sentence", "improved at 0 of 4" in fd["f5a"] and f"{slow:.1f} times slower" in fd["f5a"] and "significantly worse at 3 horizons" in fd["f5a"], fd["f5a"][:300])
    mp = pd.read_csv("reports/phase1d/event_to_fold_mapping.csv")
    mp = mp[mp.definition == "experimental_stage_10ft"]
    ok("strip table", len(D["strip"]) - 1 == len(mp) == 20 and [r[0] for r in D["strip"][1:]] == [str(x)[:16] for x in mp.event_start], str(D["strip"][:2]))

    # ---- milestone, roadmap and limitation text
    txt = {m["title"]: m["text"] for m in D["milestones"]}
    ok("milestone data audit", f"{p0['rows_raw']:,} rows" in txt["Data acquisition and audit"] and "99.55%" in txt["Data acquisition and audit"], txt["Data acquisition and audit"][:140])
    ok("milestone window", "36 matched" in txt["Input-window comparison (24 h versus 72 h)"] and f"{slow:.1f} times" in txt["Input-window comparison (24 h versus 72 h)"])
    ok("milestone upstream", "6 are upstream-led (5 storms), 6 local-or-downstream-led and 6 ambiguous" in txt["Upstream gauge feasibility and research protocol"] and f"{up.min():g} to {up.max():g} h" in txt["Upstream gauge feasibility and research protocol"])
    ok("milestone onset", f"{lag50:g} h" in txt["Onset-timing analysis"])
    tl = {t["name"]: t for t in D["timeline"]}
    ok("roadmap counts", (tl["First evaluation"]["done"], tl["First evaluation"]["todo"]) == (10, 0) and (tl["Second evaluation"]["done"], tl["Third evaluation"]["done"]) == (0, 0) and "10 of 10" in tl["First evaluation"]["note"] and "0 of 5" in tl["Second evaluation"]["note"] and "0 of 4" in tl["Third evaluation"]["note"], str(tl))
    ok("roadmap labels", tl["First evaluation"]["chip"].startswith("Current") and tl["Second evaluation"]["chip"] == "Proposed" and tl["Third evaluation"]["chip"] == "Proposed")
    era = re.search(r"\| 2015-05-24 [^|]*\| ([0-9.]+) \| [0-9.]+ \| ([0-9.]+) \|", Path("reports/gauge_rainfall/README.md").read_text())
    pct = round(100 * float(era.group(2)) / float(era.group(1)), 1)
    lim = {l["title"]: l["text"] for l in D["limits"]}
    ok("limitation ERA5", f"{pct}% of the gauge estimate" in lim["Rainfall data limitations"], lim["Rainfall data limitations"][:120])
    ok("limitation power", "0.031" in lim["Limited statistical power"] and "6 upstream-led events from 5 storms" in lim["Limited statistical power"], lim["Limited statistical power"][:140])

    # ---- navigation, links, chrome
    ok("all 9 nav links scroll to their section and become active", len(D["nav"]) == 9 and all(-4 <= n["top"] <= 130 and n["active"] for n in D["nav"]), str(D["nav"]))
    bad = []
    for href in D["hrefs"]:
        if href.startswith("#") or href.startswith("http"):
            continue
        if not (PAGE_DIR / href).resolve().exists():
            bad.append(href)
    ok("every relative link resolves to an existing file", not bad, str(bad[:5]))
    ok("replay dashboard is linked", "../replay/index.html" in D["hrefs"])
    ok("projector mode and theme toggle work", D["projector"] is True and D["theme"] in ("light", "dark"), f"{D['projector']} {D['theme']}")
    print(f"{len(checks) - len(fails)} of {len(checks)} checks passed")
    for x in fails[:40]:
        print("FAIL", x)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
