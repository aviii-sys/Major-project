"""Plots: stage rise at Spring Branch versus three upstream gauges for the events with a long upstream lead and those with no usable warning (cached data only).
Output: reports/upstream_feasibility/figures"""
import warnings
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")
from assess_upstream_inputs import fetch, rise_timing  # noqa: E402
from flashflood import experiment  # noqa: E402

OUT = Path("reports/upstream_feasibility/figures"); OUT.mkdir(parents=True, exist_ok=True)
C = dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#e6e5e1")
plt.rcParams.update({"figure.facecolor": C["surface"], "axes.facecolor": C["surface"], "savefig.facecolor": C["surface"], "axes.edgecolor": C["grid"], "axes.labelcolor": C["ink2"],
                     "text.color": C["ink"], "xtick.color": C["ink2"], "ytick.color": C["ink2"], "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 8, "axes.titleweight": "bold", "axes.titlelocation": "left"})
GAUGES = {"08167000": ("Comfort (102 km up)", "#2a78d6"), "08166200": ("Kerrville (140 km up)", "#eb6834"), "08165500": ("Hunt (157 km up)", "#1baf7a")}
LONG = ["2016-05-29 20:30", "2016-06-02 17:30", "2018-10-17 00:45", "2025-07-05 03:45", "2026-06-15 18:30", "2026-07-15 18:30"]
NONE = ["2012-01-25 12:15", "2013-10-31 06:30", "2015-05-23 23:15", "2015-10-30 12:30", "2016-05-19 15:45", "2018-09-09 15:15", "2021-10-14 04:45", "2024-07-24 14:45"]
lead = pd.read_csv("reports/upstream_feasibility/tables/upstream_event_level_lead.csv").set_index("event_start")
ctx = experiment.build_context(); idx = ctx.s.index
ev = ctx.ev_all["experimental_stage_10ft"]
E = {str(idx[int(e.i0)])[:16]: e for e in ev.itertuples()}


def panel(ax, key):
    e = E[key]; t0, t1 = idx[int(e.i0)], idx[int(e.i1)]
    lo, hi = t0 - pd.Timedelta("36h"), t1 + pd.Timedelta("18h")
    sb = ctx.s.loc[lo:hi]
    ax.plot(sb.index, sb - sb.min(), color=C["ink"], lw=1.6, label="Spring Branch (target)")
    sbt = rise_timing(ctx.s, lo, hi)
    if sbt["status"] == "responds":
        ax.axvline(sbt["t_first"], color=C["ink"], lw=0.8, ls=":")
    for site, (name, col) in GAUGES.items():
        d = fetch(site, lo - pd.Timedelta("24h"), hi + pd.Timedelta("12h"))
        if len(d):
            s = d["00065"].loc[lo:hi]
            if s.notna().sum() > 40:
                ax.plot(s.index, s - s.min(), color=col, lw=1, label=name)
    b = lead.loc[key]
    tag = f"best upstream lead {b.best_first_rise_lead_h:.0f} h" if pd.notna(b.best_first_rise_lead_h) else "no consistent upstream response"
    ax.set_title(f"{key[:10]}  peak {e.peak_ft:.1f} ft\n{tag}", fontsize=8)
    ax.tick_params(axis="x", labelrotation=30, labelsize=6.5); ax.set_ylabel("stage rise above window minimum (ft)", fontsize=7)


for name, keys, nrow, ncol, title in (("fig_upstream_long_lead_events.png", LONG, 2, 3, "Events where the rise appears upstream hours earlier (best upstream lead 6 h or more)"),
                                     ("fig_upstream_no_warning_events.png", NONE, 2, 4, "Events with no usable upstream warning (no consistent response, or lead under 1 h)")):
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.0 * ncol, 3.6 * nrow))
    for ax, k in zip(axes.ravel(), keys):
        panel(ax, k)
    for ax in axes.ravel()[len(keys):]:
        ax.set_visible(False)
    axes.ravel()[0].legend(frameon=False, fontsize=6.5, loc="upper right")
    fig.suptitle(title + "   (dotted line = first 1 ft/3 h rise at Spring Branch)", fontsize=9, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.96)); fig.savefig(OUT / name, dpi=120); plt.close(fig)
print("figures written")
