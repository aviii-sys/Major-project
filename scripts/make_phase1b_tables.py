"""Builds reports/phase1b/PHASE1B_TABLES.md from the CSV outputs of run_phase1b.py (no hand-copied numbers), and re-renders all
markdown tables under reports/**/tables from their CSVs with a number format that keeps years/counts readable."""
import ast
import json
from pathlib import Path

import pandas as pd

T = Path("reports/phase1b/tables")
HZ = ["15m", "30m", "1h", "3h"]
REG = ["persistence", "trend_p1a", "trend_v2", "ridge_H0", "xgb_H0", "ridge_B", "xgb_B"]
DEFS = ["official_action_25ft", "official_minor_30ft", "official_moderate_36ft", "experimental_stage_10ft", "experimental_stage_15ft",
        "experimental_rise_4ft_3h", "experimental_rise_8ft_3h"]
out = []


def ci(v):
    try:
        a, b = ast.literal_eval(v)
        return f"[{a:.2f}, {b:.2f}]"
    except Exception:
        return ""


def sec(title, df, note=""):
    out.append(f"\n### {title}\n")
    if note:
        out.append(note + "\n")
    out.append(df.to_markdown(index=False))


res = json.load(open("reports/phase1b/results.json"))
out.append(f"Adopted feature set: **{res['adopted_feature_set']}**. Chosen sample-weight lambda: {res['chosen_lambda']}. "
           f"Validation independent events: {res['validation_event_counts']}.")
A = pd.read_csv(T / "A_feature_set_selection_validation.csv")
sec("A. Feature-set selection (validation event-window RMSE, ft; XGBoost, lambda = 0)", A.pivot(index="feature_set", columns="horizon", values="val_event_window_rmse")[HZ].round(3).reset_index().assign(mean=lambda d: d[HZ].mean(axis=1).round(4)),
    "Rule: a set richer than H2 is adopted only if its mean is at least 5% lower than H2's.")
B = pd.read_csv(T / "B_lambda_selection_validation.csv")
sec("B. Sample-weight lambda selection (validation, mean over horizons)", B.groupby(["model", "lambda"])[["val_event_window_rmse", "val_all_row_rmse"]].mean().round(4).reset_index())
C = pd.read_csv(T / "C_trend_v2_grid_validation.csv")
sec("C. Damped trend: selected (window, phi) per horizon (validation event-window RMSE)",
    C.loc[C.groupby("horizon").val_event_window_rmse.idxmin()].round(4).reset_index(drop=True))

E = pd.read_csv(T / "E_regression_metrics.csv")
for proto, sub, title in [("chrono_val", "all", "Regression RMSE (ft), VALIDATION, all rows"),
                          ("chrono_test", "all", "Regression RMSE (ft), chronological TEST (exploratory), all rows"),
                          ("chrono_test", "event_windows_stage10ft", "Regression RMSE (ft), TEST (exploratory), windows of >=10 ft events"),
                          ("chrono_test", "event_windows_rise4ft3h", "Regression RMSE (ft), TEST (exploratory), windows of >=4 ft/3 h rises"),
                          ("blocked_cv_NONCAUSAL", "event_windows_stage10ft", "Regression RMSE (ft), blocked CV (NON-CAUSAL), windows of >=10 ft events")]:
    d = E[(E.protocol == proto) & (E["subset"] == sub)]
    rows = []
    for m in REG:
        r = {"model": m}
        for h in HZ:
            x = d[(d.model == m) & (d.horizon == h)]
            if len(x):
                x = x.iloc[0]; r[f"RMSE {h}"] = f"{x.rmse:.3f}" + (f" {ci(x.rmse_ci)}" if "rmse_ci" in x and isinstance(x.rmse_ci, str) else "")
        rows.append(r)
    sec(title, pd.DataFrame(rows), f"Rows scored per horizon: {d[d.model == 'persistence'].set_index('horizon').n.to_dict()}.")
    rows = []
    for m in REG[1:]:
        r = {"model": m}
        for h in HZ:
            x = d[(d.model == m) & (d.horizon == h)]
            if len(x):
                x = x.iloc[0]; r[f"skill {h}"] = f"{x.skill_vs_persistence:.2f}" + (f" {ci(x.skill_ci)}" if "skill_ci" in x and isinstance(x.skill_ci, str) else "")
        rows.append(r)
    out.append("\nSkill versus persistence:\n"); out.append(pd.DataFrame(rows).to_markdown(index=False))


def det_table(df, key, models, title, note=""):
    rows = []
    for dname in DEFS if key == "definition" else list(df[key].unique()):
        for h in HZ:
            for m in models:
                col = "model" if key == "definition" else "learner"
                x = df[(df[key] == dname) & (df.horizon == h) & (df[col] == m)]
                if x.empty:
                    continue
                x = x.iloc[0]
                r = {key: dname, "h": h, col: m}
                if "theta_from_validation" in x:
                    r["theta (val)"] = x.theta_from_validation
                r.update({"early hits / events [95% CI]": f"{int(x.early_hits)}/{int(x.n_events)} [{x.POD_ci_lo:.2f}, {x.POD_ci_hi:.2f}]", "late": int(x.late), "missed": int(x.misses),
                          "false-alarm episodes / episodes": f"{int(x.false_alarm_episodes)}/{int(x.alarm_episodes)}", "precision (episode)": round(x.precision_episode, 2) if pd.notna(x.precision_episode) else "",
                          "CSI": round(x.CSI, 2), "median lead h [min, max]": "" if pd.isna(x.median_lead_h) else f"{x.median_lead_h:.2f} [{x.lead_h_min:.2f}, {x.lead_h_max:.2f}]",
                          "false alarms / yr": round(x.false_alarms_per_year, 2), "storm clusters": int(x.independent_storm_clusters), "not evaluable": int(x.n_not_evaluable)})
                rows.append(r)
    sec(title, pd.DataFrame(rows), note)


F = pd.read_csv(T / "F_fixed_rule_detection.csv")
for proto, title in [("chrono_test", "Fixed alarm rule, chronological TEST (exploratory)"), ("blocked_cv_NONCAUSAL", "Fixed alarm rule, blocked CV (NON-CAUSAL)")]:
    det_table(F[F.protocol == proto], "definition", ["persistence", "trend_v2", "ridge_B", "xgb_B"], title)
G = pd.read_csv(T / "G_prob_detection_event_level.csv")
for proto, title in [("chrono_test", "Probability-based detection, chronological TEST (exploratory); theta from validation only"),
                     ("blocked_cv_NONCAUSAL", "Probability-based detection, blocked CV (NON-CAUSAL; theta from chronological validation applied unchanged)"),
                     ("chrono_val", "Probability-based detection, VALIDATION (where theta was chosen; optimistic by construction)")]:
    d = G[G.protocol == proto].rename(columns={"target": "definition"}).assign(model=lambda x: x.learner)
    det_table(d, "definition", ["logistic", "xgb_plain", "xgb_weighted"], title, "Official thresholds are not modelled (too few training events).")
sec("Probability thresholds selected on validation (row-level F2)", pd.read_csv(T / "G_threshold_selection_validation.csv"))
sec("Row-level test metrics at the validation threshold", pd.read_csv(T / "G_prob_row_level_test.csv").round(4))
sec("Descriptive threshold sweep on TEST (never used for selection)", pd.read_csv(T / "G_threshold_sweep_test_descriptive.csv").round(3))
ie = pd.read_csv(T / "independent_event_counts.csv")
sec("Independent events and distinct storm clusters", ie)
pe = pd.read_csv(T / "F_fixed_rule_per_event.csv")
sec("Events marked not evaluable (all protocols/horizons/models)", pe[pe.status == "not_evaluable"].drop_duplicates(["protocol", "definition", "event_start", "horizon"])[["protocol", "definition", "event_start", "horizon", "peak_ft"]])
Path("reports/phase1b/PHASE1B_TABLES.md").write_text("# Phase 1B result tables (generated)\n" + "\n".join(out) + "\n")

# re-render every markdown table from its CSV with a safer number format
n_re = 0
for csv_path in Path("reports").glob("**/tables/*.csv"):
    df = pd.read_csv(csv_path)
    try:
        csv_path.with_suffix(".md").write_text(df.to_markdown(index=False, floatfmt=".6g"))
        n_re += 1
    except Exception:
        pass
print("PHASE1B_TABLES.md written;", n_re, "markdown tables re-rendered")
