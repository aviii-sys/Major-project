"""Builds reports/phase1a/PHASE1A_TABLES.md from the CSV outputs of run_phase1a.py (no hand-copied numbers)."""
import ast
from pathlib import Path

import pandas as pd

T = Path("reports/phase1a/tables")
HZ = ["15m", "30m", "1h", "3h"]
MODELS = ["persistence", "trend", "ridge_H", "ridge_HR", "xgb_H", "xgb_HR"]
DEF_ORDER = ["official_action_25ft", "official_minor_30ft", "official_moderate_36ft", "experimental_stage_10ft", "experimental_stage_15ft",
             "experimental_rise_4ft_3h", "experimental_rise_8ft_3h"]
out = []


def ci(s):
    try:
        a, b = ast.literal_eval(s)
        return f"[{a:.2f}, {b:.2f}]"
    except Exception:
        return ""


def section(title, df, note=""):
    out.append(f"\n### {title}\n")
    if note:
        out.append(note + "\n")
    out.append(df.to_markdown(index=False))


r = pd.read_csv(T / "regression_metrics.csv")
for proto, sub, title in [("chrono_test", "all", "Stage forecast error, chronological TEST, all rows"),
                          ("chrono_test", "event_windows_stage10ft", "Stage forecast error, chronological TEST, event windows of the experimental >=10 ft events"),
                          ("chrono_test", "event_windows_rise4ft3h", "Stage forecast error, chronological TEST, event windows of the experimental >=4 ft/3 h rapid rises"),
                          ("blocked_cv_NONCAUSAL", "event_windows_stage10ft", "Stage forecast error, blocked CV (NON-CAUSAL), event windows of >=10 ft events")]:
    d = r[(r.protocol == proto) & (r.subset == sub)]
    rows = []
    for m in MODELS:
        row = {"model": m}
        for h in HZ:
            x = d[(d.model == m) & (d.horizon == h)]
            if x.empty:
                row[f"RMSE ft {h}"] = ""
                continue
            x = x.iloc[0]
            row[f"RMSE ft {h}"] = f"{x.rmse:.3f}" + (f" {ci(x.rmse_ci)}" if "rmse_ci" in x and isinstance(x.rmse_ci, str) else "")
        rows.append(row)
    n = d[d.model == "persistence"].set_index("horizon").n.to_dict()
    section(title, pd.DataFrame(rows), f"Rows scored: {n}. Brackets are 95% storm-cluster bootstrap intervals where computed.")
    rows = []
    for m in MODELS[1:]:
        row = {"model": m}
        for h in HZ:
            x = d[(d.model == m) & (d.horizon == h)]
            if x.empty:
                continue
            x = x.iloc[0]
            row[f"skill {h}"] = f"{x.skill_vs_persistence:.2f}" + (f" {ci(x.skill_ci)}" if "skill_ci" in x and isinstance(x.skill_ci, str) else "")
        rows.append(row)
    out.append("\nSkill versus persistence (1 - MSE/MSE_persistence; 0 = no better than persistence):\n")
    out.append(pd.DataFrame(rows).to_markdown(index=False))

d = pd.read_csv(T / "event_detection.csv")
for proto, title in [("chrono_test", "Event detection, chronological TEST (2022-01-01 onward; 2026 data provisional)"),
                     ("blocked_cv_NONCAUSAL", "Event detection, blocked CV, whole record (NON-CAUSAL: trained on future blocks)")]:
    rows = []
    for defn in DEF_ORDER:
        for h in HZ:
            for m in ["persistence", "trend", "ridge_H", "xgb_H", "xgb_HR"]:
                x = d[(d.protocol == proto) & (d.definition == defn) & (d.horizon == h) & (d.model == m)]
                if x.empty:
                    continue
                x = x.iloc[0]
                rows.append({"definition": defn, "h": h, "model": m, "early hits / events [95% CI]": f"{int(x.early_hits)}/{int(x.n_events)} [{x.POD_ci_lo:.2f}, {x.POD_ci_hi:.2f}]",
                             "late": int(x.late), "missed": int(x.misses), "false alarms / episodes": f"{int(x.false_alarms)}/{int(x.alarm_episodes)}",
                             "false alarms per yr": round(x.false_alarms_per_year, 2),
                             "median lead h": "" if pd.isna(x.median_lead_h) else round(x.median_lead_h, 2), "not evaluable": int(x.n_not_evaluable)})
    section(title, pd.DataFrame(rows))

ie = pd.read_csv(T / "independent_event_counts.csv")
section("Event counts by protocol (events vs distinct storm clusters)", ie.pivot_table(index="definition", columns="protocol", values=["events", "distinct_storm_clusters"], aggfunc="first").reset_index().round(0).astype(str))
pe = pd.read_csv(T / "per_event_results.csv")
q = pe[(pe.protocol == "chrono_test") & pe.definition.isin(["official_action_25ft"]) & pe.model.isin(["persistence", "trend", "ridge_H", "xgb_H"]) & pe.horizon.isin(["1h", "3h"])].copy()
q["event_start_utc"] = q.event_start.str[:16]
section("Official >=25 ft events inside the TEST period: per-event results (descriptive; n = 3 events, 2 storms)",
        q[["event_start_utc", "peak_ft", "provisional_data", "horizon", "model", "status", "lead_h", "peak_forecast_ft", "peak_ratio", "window_rmse_ft", "window_rmse_persistence_ft"]].round(2),
        "peak_forecast_ft = forecast of the peak stage issued h before the peak; peak_ratio = forecast / observed peak. provisional_data = event lies in USGS provisional data (2026).")
Path("reports/phase1a/PHASE1A_TABLES.md").write_text("# Phase 1A result tables (generated)\n" + "\n".join(out) + "\n")
print("written", len("\n".join(out)), "chars")
