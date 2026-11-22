"""Builds docs/PROJECT_EXPLAINER.html: a plain-language, shareable explainer of the project and a plan for presenting it to the university.
All charts are inline SVG drawn from the project's own data (out-of-fold predictions, cached gauge records); all numbers come from result tables.
Usage: PYTHONPATH=scripts python scripts/make_explainer.py        Output: docs/PROJECT_EXPLAINER.html
"""
import html
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from flashflood import data  # noqa: E402

OUT = Path("docs/PROJECT_EXPLAINER.html")


# ------------------------------------------------------------------ small SVG helpers (colours come from CSS classes so both themes work)
def svg_line_chart(series, x0, x1, ymax, width=680, height=310, ml=46, mr=14, mt=14, mb=44, ylabel="", xticks=(), yticks=(), vlines=(), notes=()):
    pw, ph = width - ml - mr, height - mt - mb
    X = lambda t: ml + (pd.Timestamp(t) - x0) / (x1 - x0) * pw  # noqa: E731
    Y = lambda v: mt + ph - (v / ymax) * ph  # noqa: E731
    g = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" xmlns="http://www.w3.org/2000/svg">']
    for yv in yticks:
        g.append(f'<line class="grid" x1="{ml}" x2="{width - mr}" y1="{Y(yv):.1f}" y2="{Y(yv):.1f}"/><text class="lbl" x="{ml - 6}" y="{Y(yv) + 4:.1f}" text-anchor="end">{yv}</text>')
    for tv, lab in xticks:
        g.append(f'<line class="grid v" x1="{X(tv):.1f}" x2="{X(tv):.1f}" y1="{mt}" y2="{mt + ph}"/><text class="lbl" x="{X(tv):.1f}" y="{height - mb + 16}" text-anchor="middle">{lab}</text>')
    g.append(f'<text class="lbl" x="{ml}" y="{height - 6}" text-anchor="start">times are UTC</text>')
    g.append(f'<text class="lbl" x="12" y="{mt + ph / 2:.0f}" text-anchor="middle" transform="rotate(-90 12 {mt + ph / 2:.0f})">{ylabel}</text>')
    for cls, s, dash in series:
        pts = " ".join(f"{X(t):.1f},{Y(v):.1f}" for t, v in zip(s.index, s.values) if x0 <= t <= x1 and np.isfinite(v))
        g.append(f'<polyline class="ln {cls}" points="{pts}"' + (f' stroke-dasharray="{dash}"' if dash else "") + "/>")
    for t, cls in vlines:
        g.append(f'<line class="vm {cls}" x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{mt}" y2="{mt + ph}"/>')
    for tx, ty, text, cls in notes:
        g.append(f'<text class="note {cls}" x="{X(tx):.1f}" y="{Y(ty):.1f}">{text}</text>')
    g.append("</svg>")
    return "".join(g)


def gauge_svg():
    H, W, top, bot = 470, 520, 12, 24
    Y = lambda ft: top + (H - top - bot) * (1 - ft / 40.0)  # noqa: E731
    g = [f'<svg class="gauge" viewBox="0 0 {W} {H}" role="img" xmlns="http://www.w3.org/2000/svg">']
    bands = [(25, 30, "band-action", "Action 25 ft"), (30, 36, "band-minor", "Minor flood 30 ft"), (36, 39, "band-moderate", "Moderate flood 36 ft"), (39, 40, "band-major", "Major flood 39 ft")]
    g.append(f'<rect class="staff" x="70" y="{Y(40):.1f}" width="46" height="{Y(0) - Y(40):.1f}"/>')
    for lo, hi, cls, lab in bands:
        g.append(f'<rect class="{cls}" x="70" y="{Y(hi):.1f}" width="46" height="{Y(lo) - Y(hi):.1f}"/>')
        g.append(f'<text class="lbl strong" x="126" y="{Y(lo) + 4:.1f}">{lab}</text>')
    for ft in range(0, 41, 5):
        g.append(f'<line class="tick" x1="62" x2="70" y1="{Y(ft):.1f}" y2="{Y(ft):.1f}"/><text class="lbl" x="56" y="{Y(ft) + 4:.1f}" text-anchor="end">{ft}</text>')
    g.append(f'<text class="lbl" x="56" y="{top - 1}" text-anchor="end">ft</text>')
    ev = [(36.75, "2026-07-17: 36.8 ft", 0), (34.5, "2015-05-24: 34.5 ft", 0), (30.06, "2015-10-30 and 2025-07-05: 30.0 ft", 4), (26.07, "2016-05-30: 26.1 ft", 0), (25.04, "2026-07-15: 25.0 ft", 10)]
    for ft, lab, dy in ev:
        g.append(f'<circle class="evt" cx="93" cy="{Y(ft):.1f}" r="4.5"/><text class="lbl evtxt" x="306" y="{Y(ft) + 4 + dy:.1f}">{lab}</text>')
        g.append(f'<line class="lead" x1="97" x2="300" y1="{Y(ft):.1f}" y2="{Y(ft) + dy:.1f}"/>')
    g.append(f'<circle class="evt dim" cx="93" cy="{Y(2.86):.1f}" r="4.5"/><text class="lbl" x="126" y="{Y(2.86) - 10:.1f}">Highest reading in our first dataset (2022-2023): 2.86 ft</text>')
    g.append(f'<line class="lead" x1="97" x2="120" y1="{Y(2.86):.1f}" y2="{Y(2.86) - 14:.1f}"/>')
    g.append("</svg>")
    return "".join(g)


def build_charts():
    o = pd.read_csv("reports/phase1d/oof_predictions.csv.gz", usecols=["timestamp_utc", "stage_ft", "pred_gru_3h_ft", "pred_trend_v2_3h_ft"])
    o["t"] = pd.to_datetime(o.timestamp_utc, utc=True)
    o = o.set_index("t").loc["2025-07-04 12:00":"2025-07-06 06:00"]
    obs = o.stage_ft
    fg = o.pred_gru_3h_ft.copy(); fg.index = fg.index + pd.Timedelta("3h")
    ft = o.pred_trend_v2_3h_ft.copy(); ft.index = ft.index + pd.Timedelta("3h")
    x0, x1 = pd.Timestamp("2025-07-04 12:00", tz="UTC"), pd.Timestamp("2025-07-06 06:00", tz="UTC")
    first = lambda s: (lambda r: r.index[0])((s - s.shift(12)).dropna().pipe(lambda i: i[i >= 1.0]))  # noqa: E731
    t_obs, t_gru = first(obs), first(fg.loc[obs.index.min():obs.index.max()])
    delay = (t_gru - t_obs) / pd.Timedelta("1h")
    xt = [(pd.Timestamp(f"2025-07-{d:02d} {h:02d}:00", tz="UTC"), f"Jul {d} {h:02d}h") for d, h in [(4, 12), (5, 0), (5, 12), (6, 0)]]
    c1 = svg_line_chart([("s-obs", obs, None), ("s-gru", fg.loc[x0:x1], None), ("s-trend", ft.loc[x0:x1], "5 4")], x0, x1, 32, ylabel="river height (ft)", xticks=xt, yticks=(0, 10, 20, 30),
                        vlines=[(t_obs, "vm-obs"), (t_gru, "vm-gru")],
                        notes=[(t_obs - pd.Timedelta("1h"), 24.5, "rise begins", "end obs"), (t_gru + pd.Timedelta("1h"), 17.5, f"forecast shows it {delay:.0f} h later", "gru")])
    # chart 2: upstream versus Spring Branch
    reg = data.load_stage()
    sb = reg.stage_ft.loc["2025-07-04 00:00":"2025-07-06 00:00"]
    series, trig = [("s-obs", sb - sb.min(), None)], {"Spring Branch": sb.index[0]}
    def rise(s):
        r = (s - s.shift(12)).dropna(); r = r[r >= 1.0]; return r.index[0]
    t_sb = rise(sb); leads = {}
    for site, cls, name in (("08167000", "s-comfort", "Comfort"), ("08165500", "s-hunt", "Hunt")):
        f = sorted(Path("data/raw/upstream/iv").glob(f"{site}_20250702_*.csv"))[0]
        d = pd.read_csv(f, index_col=0, parse_dates=True)["00065"].loc["2025-07-04 00:00":"2025-07-06 00:00"]
        series.append((cls, d - d.min(), None)); leads[name] = (t_sb - rise(d)) / pd.Timedelta("1h")
    x0b, x1b = pd.Timestamp("2025-07-04 00:00", tz="UTC"), pd.Timestamp("2025-07-06 00:00", tz="UTC")
    xt2 = [(pd.Timestamp(f"2025-07-{d:02d} {h:02d}:00", tz="UTC"), f"Jul {d} {h:02d}h") for d, h in [(4, 0), (4, 12), (5, 0), (5, 12), (6, 0)]]
    c2 = svg_line_chart(series, x0b, x1b, 36, ylabel="rise above the lowest reading (ft)", xticks=xt2, yticks=(0, 10, 20, 30), vlines=[(t_sb, "vm-obs")],
                        notes=[(pd.Timestamp("2025-07-04 02:00", tz="UTC"), 33, f"Comfort rose {leads['Comfort']:.0f} h and Hunt {leads['Hunt']:.0f} h before Spring Branch", "end obs")])
    return c1, c2, delay, leads


CSS = """
:root{--paper:#f6f9fa;--card:#ffffff;--ink:#12222a;--muted:#4b5f68;--line:#d3dfe3;--accent:#0a6a86;--accent-soft:#e1f0f4;--warn:#9a5b00;--warn-soft:#fbf0dc;--good:#1d7a4b;--bad:#a8332c;
--s1:#6250d6;--s2:#c98500;--s3:#0a6a86;--s4:#1d7a4b;--b-action:#ecc94b;--b-minor:#e8892b;--b-mod:#d0453c;--b-major:#8a3a9c;--font-body:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;--font-head:'Space Grotesk','Inter',system-ui,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--paper:#0e1a20;--card:#14252d;--ink:#e5eef1;--muted:#9fb3bb;--line:#27393f;--accent:#58bcd8;--accent-soft:#16323c;--warn:#e6a845;--warn-soft:#2c2415;--good:#52c28a;--bad:#ef7a72;--s1:#9a8cf0;--s2:#e3a23b;--s3:#58bcd8;--s4:#52c28a;--b-action:#c9a62a;--b-minor:#d4782a;--b-mod:#c4473f;--b-major:#a55bb8;color-scheme:dark}}
:root[data-theme="dark"]{--paper:#0e1a20;--card:#14252d;--ink:#e5eef1;--muted:#9fb3bb;--line:#27393f;--accent:#58bcd8;--accent-soft:#16323c;--warn:#e6a845;--warn-soft:#2c2415;--good:#52c28a;--bad:#ef7a72;--s1:#9a8cf0;--s2:#e3a23b;--s3:#58bcd8;--s4:#52c28a;--b-action:#c9a62a;--b-minor:#d4782a;--b-mod:#c4473f;--b-major:#a55bb8;color-scheme:dark}
body{background:var(--paper);color:var(--ink);font-family:var(--font-body);font-size:16px;line-height:1.6;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:0}
.wrap{max-width:820px;margin:0 auto;padding-block:40px 80px}
h1,h2,h3{font-family:var(--font-head);line-height:1.2;text-wrap:balance;margin:0}
h1{font-size:clamp(1.9rem,5vw,2.7rem);letter-spacing:-.01em}
h2{font-size:1.55rem;margin-top:3rem;padding-top:1.2rem;border-top:1px solid var(--line)}
h3{font-size:1.1rem;margin-top:1.6rem}
p{margin:.7rem 0}
.eyebrow{font-size:.78rem;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);font-weight:600}
.lede{font-size:1.15rem;color:var(--muted);max-width:60ch}
.status{background:var(--warn-soft);border-left:4px solid var(--warn);padding:.8rem 1rem;border-radius:4px;margin:1.4rem 0}
.status strong{color:var(--warn)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:1.1rem 1.25rem}
ul.plain{padding-left:1.2rem;margin:.6rem 0}ul.plain li{margin:.35rem 0}
.toc{display:flex;flex-wrap:wrap;gap:.4rem .9rem;margin:1.2rem 0 0;padding:0;list-style:none;font-size:.92rem}
.toc a{color:var(--accent);text-decoration:none;border-bottom:1px solid transparent}.toc a:hover{border-bottom-color:var(--accent)}
.steps{display:grid;gap:.8rem;margin:1rem 0;padding:0;list-style:none;counter-reset:s}
.steps li{counter-increment:s;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.9rem 1.1rem .9rem 3.2rem;position:relative}
.steps li::before{content:counter(s);position:absolute;left:1rem;top:.85rem;width:1.6rem;height:1.6rem;border-radius:50%;background:var(--accent);color:var(--paper);font-weight:700;font-size:.85rem;display:flex;align-items:center;justify-content:center;font-family:var(--font-head)}
.steps b{font-family:var(--font-head)}
.tablewrap{overflow-x:auto;margin:1rem 0;border:1px solid var(--line);border-radius:10px;background:var(--card)}
table{border-collapse:collapse;width:100%;min-width:520px;font-size:.93rem}
th,td{padding:.55rem .8rem;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;font-size:.8rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);background:var(--accent-soft)}
tr:last-child td{border-bottom:0}td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.best{font-weight:700;color:var(--accent)}
figure{margin:1.4rem 0;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:1rem 1rem .8rem;overflow-x:auto}
figure .scroll{min-width:560px}
figcaption{font-size:.9rem;color:var(--muted);margin-top:.6rem}
svg.chart,svg.gauge{width:100%;height:auto;display:block}
.lbl{fill:var(--muted);font-size:12px;font-family:var(--font-body)}.lbl.strong{fill:var(--ink);font-weight:600}.evtxt{fill:var(--ink)}
.grid{stroke:var(--line);stroke-width:1}.grid.v{stroke-dasharray:2 4}.tick{stroke:var(--muted);stroke-width:1.5}
.ln{fill:none;stroke-width:2.2;stroke-linejoin:round}.s-obs{stroke:var(--ink);stroke-width:2.6}.s-gru{stroke:var(--s1)}.s-trend{stroke:var(--s2)}.s-comfort{stroke:var(--s3)}.s-hunt{stroke:var(--s4)}
.vm{stroke-width:1.4;stroke-dasharray:4 3}.vm-obs{stroke:var(--ink)}.vm-gru{stroke:var(--s1)}
.note{font-size:12.5px;font-weight:600;fill:var(--ink)}.note.gru{fill:var(--s1)}.note.end{text-anchor:start}
.staff{fill:var(--card);stroke:var(--line)}.band-action{fill:var(--b-action)}.band-minor{fill:var(--b-minor)}.band-moderate{fill:var(--b-mod)}.band-major{fill:var(--b-major)}
.evt{fill:var(--ink);stroke:var(--paper);stroke-width:2}.evt.dim{fill:var(--muted)}.lead{stroke:var(--muted);stroke-width:1;stroke-dasharray:2 3}
.legend{display:flex;flex-wrap:wrap;gap:.4rem 1.2rem;font-size:.88rem;margin-top:.3rem}.legend span::before{content:"";display:inline-block;width:1.4rem;height:0;border-top:3px solid;margin-right:.4rem;vertical-align:middle}
.l-obs::before{border-color:var(--ink)}.l-gru::before{border-color:var(--s1)}.l-trend::before{border-top-style:dashed;border-color:var(--s2)}.l-comfort::before{border-color:var(--s3)}.l-hunt::before{border-color:var(--s4)}
.bars{display:grid;gap:.5rem;margin:1rem 0}.bar{display:grid;grid-template-columns:130px 1fr 60px;gap:.7rem;align-items:center;font-size:.93rem}
.bar .track{background:var(--accent-soft);border-radius:6px;height:20px;overflow:hidden}.bar .fill{background:var(--accent);height:100%;border-radius:6px}.bar .fill.lo{background:var(--s2)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:1rem}@media(max-width:640px){.two{grid-template-columns:1fr}.bar{grid-template-columns:100px 1fr 52px}}
.can h3{color:var(--good);margin-top:0}.cannot h3{color:var(--bad);margin-top:0}
.can li::marker{color:var(--good)}.cannot li::marker{color:var(--bad)}
.callout{background:var(--accent-soft);border-radius:10px;padding:1rem 1.2rem;margin:1.2rem 0}
code{font-family:ui-monospace,Menlo,monospace;font-size:.86em;background:var(--accent-soft);padding:.1em .35em;border-radius:4px}
.foot{margin-top:3rem;padding-top:1rem;border-top:1px solid var(--line);font-size:.86rem;color:var(--muted)}
@media print{body{background:#fff;color:#000}.card,figure,.steps li{break-inside:avoid}}
"""


def page(c1, c2, delay, leads):
    return f"""<title>Guadalupe Flood Forecasting</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Space+Grotesk:wght@500;700&display=swap">
<style>{CSS}</style>
<div class="wrap">
<p class="eyebrow">Progress explainer for the university review &middot; snapshot 22 Nov 2026</p>
<h1>Forecasting Flash Floods on the Guadalupe River</h1>
<p class="lede">What we built, what we found, and how we plan to present it. Written in plain language; the full technical record is in the project files listed at the end.</p>
<div class="status"><strong>Research in progress.</strong> This snapshot includes the latest experiment (does 72 hours of history help more than 24 hours? No, see finding 6). The hybrid model has not been built yet, and nothing here is a warning system.</div>
<ul class="toc"><li><a href="#short">Short version</a></li><li><a href="#problem">The problem</a></li><li><a href="#did">What we did</a></li><li><a href="#found">What we found</a></li><li><a href="#wrong">What went wrong</a></li><li><a href="#claims">What we can claim</a></li><li><a href="#next">What is next</a></li><li><a href="#present">How we present it</a></li><li><a href="#glossary">Glossary</a></li><li><a href="#files">Where everything is</a></li></ul>

<h2 id="short">The short version</h2>
<ul class="plain">
<li>We are testing whether AI models can forecast the water level of a Texas river 15 minutes to 3 hours ahead, early enough to warn people before a flash flood.</li>
<li>Most of the work so far went into testing fairly: checking the data, stopping the models from cheating, and comparing them against simple methods.</li>
<li>Result: neural networks (LSTM and GRU) did not clearly beat simple methods such as ridge regression. Every model, simple or neural, reacts about 3 hours late to a sudden rise.</li>
<li>Reason: the river gauge only finds out about heavy rain when the water arrives. Gauges further up the river often rise 6 to 26 hours earlier, in roughly a third of the floods we studied.</li>
<li>Next: bring in that upstream information, then test the Transformer-LSTM hybrid on it. We do not claim that any model gives reliable flood warnings yet.</li>
</ul>

<h2 id="problem">The problem in plain words</h2>
<p>A flash flood is a fast rise of a river after heavy rain, sometimes within minutes or hours. We study one measuring point, the Guadalupe River near Spring Branch, Texas (US Geological Survey station 08167500). It records the water height, called <b>stage</b>, in feet every 15 minutes. The US National Weather Service defines flood levels for this gauge.</p>
<figure><div class="scroll">{gauge_svg()}</div><figcaption>The official flood levels at the gauge, with the six official-level events in our 2007 to 2026 record. The grey dot at the bottom is the highest reading in the first dataset we planned to use: it never came near a flood.</figcaption></figure>
<p><b>The task:</b> given the recent history of the stage, predict the stage 15 minutes, 30 minutes, 1 hour and 3 hours ahead. <b>The difficulty:</b> the gauge changes only after the rain has fallen, run off the land and travelled down the river. Nothing in the gauge's own past says that a storm has just hit upstream.</p>

<h2 id="did">What we did, step by step</h2>
<ol class="steps">
<li><b>Checked the data before trusting it.</b> The first dataset we planned to use (2022 to 2023) never rose above 2.86 ft, so it contained no flood. We rebuilt the dataset for 2007 to 2026. It has 20 events above 10 ft, coming from only 16 separate storms, and 6 events at official flood levels from 5 storms. (The 10 ft level is our own experimental target, not an official flood level, and we keep the two apart.)</li>
<li><b>Set strict rules for fair testing.</b> Neighbouring 15-minute readings are almost identical. If test readings sit next to training readings, a model looks good just by remembering. So we keep whole storms together, only test on later periods than the model was trained on, and leave a gap of 27 hours 15 minutes between them.</li>
<li><b>Built simple benchmarks.</b> Persistence ("the future equals now"), a damped trend ("keep moving the way it is moving, but less"), ridge regression and XGBoost. A fancy model has to beat these to be worth its complexity.</li>
<li><b>Trained neural networks.</b> LSTM, GRU and a Transformer, using the last 24 hours of the river's own readings.</li>
<li><b>Tested six times on later periods.</b> Each time the models learn from the past and are scored on a later block they have never seen. In total 18 flood events were forecast out of sample.</li>
<li><b>Asked why every model is late.</b> We looked at rainfall data and at gauges further up the river.</li>
<li><b>Tested whether more history helps.</b> We repeated the GRU test with 72 hours of history instead of 24 hours (36 training runs). The rule for deciding was written down in advance (default: keep 24 hours). The result is in finding 6.</li>
</ol>

<h2 id="found">What we found</h2>
<h3>1. Simple methods are very hard to beat</h3>
<p>Typical error in feet (lower is better), measured on about 500,000 forecasts the models had never seen. "Flood windows" are the hours around the rise of the 18 flood events.</p>
<div class="tablewrap"><table><thead><tr><th>Method</th><th class="num">All times, 1 h ahead</th><th class="num">All times, 3 h ahead</th><th class="num">Flood windows, 1 h</th><th class="num">Flood windows, 3 h</th></tr></thead><tbody>
<tr><td>Persistence (the future equals now)</td><td class="num">0.119</td><td class="num">0.308</td><td class="num">1.771</td><td class="num">4.687</td></tr>
<tr><td>Damped trend</td><td class="num">0.083</td><td class="num">0.265</td><td class="num">1.157</td><td class="num">4.017</td></tr>
<tr><td>Ridge regression</td><td class="num best">0.078</td><td class="num best">0.256</td><td class="num best">1.111</td><td class="num best">3.960</td></tr>
<tr><td>GRU neural network</td><td class="num">0.081</td><td class="num">0.258</td><td class="num">1.210</td><td class="num">4.092</td></tr>
<tr><td>LSTM neural network</td><td class="num">0.081</td><td class="num">0.257</td><td class="num">1.198</td><td class="num">4.091</td></tr>
</tbody></table></div>
<p>Two things to notice. The neural networks are no better than ridge regression. And during floods the error is roughly 15 times larger than at other times, which is exactly when accuracy matters most. In the flood windows at 15 and 30 minutes the neural networks were slightly <i>worse</i> than the simple methods. An early test on a single split had shown the GRU ahead. That did not survive the stricter six-fold test.</p>

<h3>2. Catching sudden rises is hard for every model</h3>
<p>Counting how many sudden rises (at least 4 ft within 3 hours, an experimental target) each method flagged in time when forecasting 3 hours ahead. There were 25 such events.</p>
<div class="bars">
<div class="bar"><span>Ridge</span><span class="track"><span class="fill" style="width:48%;display:block"></span></span><b>12 of 25</b></div>
<div class="bar"><span>Damped trend</span><span class="track"><span class="fill" style="width:40%;display:block"></span></span><b>10 of 25</b></div>
<div class="bar"><span>GRU</span><span class="track"><span class="fill lo" style="width:28%;display:block"></span></span><b>7 of 25</b></div>
<div class="bar"><span>LSTM</span><span class="track"><span class="fill lo" style="width:16%;display:block"></span></span><b>4 of 25</b></div>
</div>

<h3>3. Everyone is late</h3>
<figure><div class="scroll">{c1}</div><div class="legend"><span class="l-obs">what the river did</span><span class="l-gru">GRU forecast made 3 hours ahead</span><span class="l-trend">damped-trend forecast made 3 hours ahead</span></div><figcaption>The July 2025 flood at Spring Branch. Each forecast is drawn at the time it is about. Both forecasts show the sharp rise {delay:.0f} hours after it really began, and only catch up near the peak. This happens in all 18 flood events.</figcaption></figure>
<p>The reason is not a weak model. A forecast of a rise that has not yet started at the gauge cannot be made from the gauge's own history. The model sees the rise only once it begins.</p>

<h3>4. Rainfall data we tried did not help</h3>
<p>The common global rainfall dataset (ERA5) reported about 10 mm of rain over the basin on the day of the May 2015 flood. A network of rain gauges, combined into one basin estimate, gave about 119 mm, so ERA5 held roughly 8% of it. The gauge estimate only gives daily totals, so it cannot signal when a storm starts.</p>

<h3>5. The missing information is often upstream</h3>
<figure><div class="scroll">{c2}</div><div class="legend"><span class="l-obs">Spring Branch (the gauge we forecast)</span><span class="l-comfort">Comfort, about 102 km upstream</span><span class="l-hunt">Hunt, about 157 km upstream</span></div><figcaption>July 2025 flood. The gauges upstream rose many hours before Spring Branch, which is the early information the models do not currently see.</figcaption></figure>
<p>Seven gauges upstream have 15-minute records for the whole period. Over the 18 flood events, the upstream gauges rose 6 to 26 hours before Spring Branch in 6 to 8 events (the range depends on how the rise is timed; storms with several pulses are ambiguous). In another 6 to 8 events the rain fell below the upstream gauges, so they give no warning. That group includes two official floods (May 2015 and October 2015). The gauges also stopped recording during two of the biggest floods, and one important gauge has a 2.9 ft datum shift in 2011, so any model using them needs care.</p>
<div class="callout"><b>What this means.</b> The main limit is probably missing information, not model size. Adding upstream gauges could help for floods that start upstream. For floods that start close to Spring Branch, only rainfall information at the right place and time could help. We have not yet tested whether a model can use the upstream signal.</div>

<h3>6. Three days of history instead of one did not help</h3>
<p>We repeated the GRU test with 72 hours of the river's own history instead of 24 hours: 3 training runs each on all six test periods, 36 in total. The rule was fixed in advance: switch only if the longer history clearly improves flood-time forecasts at two or more of the four horizons. It improved none. Over all forecasts the 72 hour version was slightly worse at 15 minutes, 30 minutes and 1 hour (by about 1 to 2% of the error), it took about three times as long to train, and it showed no clear gain in catching sudden rises. So the default stays at 24 hours.</p>
<p>This fits the upstream finding: more of the river's own past does not say where the rain fell. It does not prove that no model could use longer history. With three training runs per setting and 14 storms in the tests, it is one more exploratory result, not a final answer.</p>

<h2 id="wrong">What went wrong, and how we handled it</h2>
<p>Finding and recording our own mistakes is part of the method. They are all written into the project documents.</p>
<ul class="plain">
<li><b>The first dataset had no flood.</b> We caught it in the first data check and rebuilt the dataset.</li>
<li><b>A data bug hid the biggest test flood.</b> One missing reading blanked 72 hours of inputs, so the largest flood was scored as a miss for every model. We found it, fixed it, kept both versions of the results, and labelled the corrected results as exploratory.</li>
<li><b>Our first upstream analysis was wrong.</b> It silently dropped three gauges and gave impossible timings. We rewrote it and kept the invalid files as evidence.</li>
<li><b>We overclaimed once.</b> We said 15-minute discharge data existed for two historic floods (1997 and 2002). The peaks were missing, and we corrected the claim.</li>
</ul>

<h2 id="claims">What we can and cannot claim</h2>
<div class="two">
<div class="card can"><h3>We can say</h3><ul class="plain"><li>Our tests are built to avoid cheating: whole storms are kept together and tests are on later periods.</li><li>Simple methods are strong baselines for this gauge.</li><li>Neural networks showed no reliable advantage over them in this setup.</li><li>For some floods, upstream gauges hold hours of advance information.</li><li>The common global rainfall dataset was inadequate for the storms we checked.</li></ul></div>
<div class="card cannot"><h3>We cannot say</h3><ul class="plain"><li>That any model gives reliable flash-flood warnings.</li><li>That deep learning is better, or that Transformers are unsuitable (we tested one setup).</li><li>That results hold at other rivers.</li><li>That anything is untouched validation: the whole record was inspected, so all results are exploratory.</li><li>That this runs in real time. It is a study on historical data.</li></ul></div>
</div>
<p>There are few independent events (14 storms in the out-of-sample tests, and only 5 storms at official flood levels), so all numbers carry wide uncertainty.</p>

<h2 id="next">What is next, and what we ask the guide</h2>
<ul class="plain">
<li>Review the 24 hour versus 72 hour result with the guide (the pre-agreed rule says keep 24 hours).</li>
<li>Discuss adding upstream gauges as inputs before building the hybrid Transformer-LSTM, so that the hybrid starts from the best available information.</li>
<li>A bounded check of why the Transformer trained unstably (it is not evidence against Transformers).</li>
</ul>
<p><b>Questions for the guide:</b></p>
<ol class="plain">
<li>May the central claim become: "a hybrid that also sees upstream context improves forecasting of upstream-driven floods, and we report its limits for the rest"?</li>
<li>Is it acceptable to limit the early-warning claim to floods that have an upstream signal?</li>
<li>Should radar rainfall (available for 16 of the 18 events by date) be validated against the gauge estimate first?</li>
<li>Which upstream gauge first? Comfort has the best coverage.</li>
<li>Should the hybrid be built before or after the upstream-input test? We recommend after.</li>
</ol>

<h2 id="present">How we present it to the university</h2>
<div class="status"><strong>Assumptions to confirm with the guide first.</strong> We assume a panel of faculty and the guide, about 15 to 20 minutes plus questions, with slides. If the slot, the panel, or the required deliverables are different (a live demo, code walk-through, written report), adapt the plan below.</div>
<h3>The one message</h3>
<p><i>"We built a strict test bench for flash-flood forecasting and found that the bottleneck is missing upstream information, not model complexity."</i></p>
<h3>Three takeaways for the audience</h3>
<ol class="plain"><li>The testing is rigorous: no cheating, strict comparison with simple methods, and mistakes are recorded.</li><li>The result is a clear, honest finding: neural networks did not beat simple methods, and every model is about 3 hours late to sudden rises.</li><li>The data point to the next step: upstream gauges often rise hours earlier.</li></ol>
<h3>Suggested slides (about 20 minutes)</h3>
<div class="tablewrap"><table><thead><tr><th>#</th><th>Slide</th><th>Key message</th><th>Show</th><th class="num">Min</th></tr></thead><tbody>
<tr><td>1</td><td>Title and question</td><td>Can AI forecast a flash flood early enough to warn?</td><td>One sentence, one photo of the river</td><td class="num">1</td></tr>
<tr><td>2</td><td>The problem</td><td>A gauge learns about rain only when water arrives</td><td>The gauge diagram with flood levels</td><td class="num">2</td></tr>
<tr><td>3</td><td>The data and the first fix</td><td>The first dataset had no flood; we rebuilt it</td><td>20 events, 16 storms, 6 official events</td><td class="num">2</td></tr>
<tr><td>4</td><td>Fair testing</td><td>Whole storms together, later periods only, a gap between</td><td>A simple timeline of folds (past trains, future tests)</td><td class="num">2</td></tr>
<tr><td>5</td><td>Models compared</td><td>Simple benchmarks versus neural networks</td><td>Four short bullets</td><td class="num">1.5</td></tr>
<tr><td>6</td><td>Main result</td><td>Neural networks did not beat simple methods</td><td>The results table and the bar chart</td><td class="num">2.5</td></tr>
<tr><td>7</td><td>Everyone is late</td><td>A 3 hour forecast shows a rise 3 hours late</td><td>The July 2025 chart</td><td class="num">2</td></tr>
<tr><td>8</td><td>Why: upstream gauges</td><td>The early signal exists upstream for some floods</td><td>The upstream chart and the 6 to 8 of 18 range</td><td class="num">2.5</td></tr>
<tr><td>9</td><td>Mistakes and fixes</td><td>We record and correct our errors</td><td>The four items above</td><td class="num">1.5</td></tr>
<tr><td>10</td><td>What we claim and do not</td><td>Careful scope builds trust</td><td>The two columns</td><td class="num">1.5</td></tr>
<tr><td>11</td><td>Next steps and ask</td><td>Upstream inputs, then the hybrid</td><td>Three bullets and the guide questions</td><td class="num">1.5</td></tr>
</tbody></table></div>
<p>Keep backup slides ready (not presented unless asked): results by fold, detection tables, the test protocol, the upstream feasibility study, and the 24 hour versus 72 hour experiment.</p>
<h3>Say and avoid</h3>
<div class="two"><div class="card can"><h3>Say</h3><ul class="plain"><li>"Our test is designed so models cannot cheat."</li><li>"Simple methods were hard to beat."</li><li>"The information a sudden rise needs often sits upstream."</li><li>"These results are exploratory."</li></ul></div><div class="card cannot"><h3>Avoid</h3><ul class="plain"><li>"Our AI predicts floods."</li><li>"Deep learning is better."</li><li>"This is a real-time warning system."</li><li>Any number you cannot point to in a project table.</li></ul></div></div>
<h3>The demo</h3>
<p>There is no live dashboard yet, so do not present one. Instead, walk through one flood (the July 2025 chart): what the river did, what each model forecast, and where upstream rose first. It is more convincing than a mock-up.</p>
<h3>Preparing</h3>
<ul class="plain"><li>Rehearse twice with a timer; cut a slide before you cut your pace.</li><li>Learn the eight numbers: 20 events, 16 storms, 18 tested, 14 independent storms, 6 official events, 12 of 25 versus 7 of 25, 3 hours late, 6 to 8 of 18.</li><li>Read the viva study guide and practise the questions aloud (<code>docs/VIVA_STUDY_GUIDE.md</code>).</li><li>Bring a PDF of the slides as a backup and have the project folder open to the reports.</li><li>If asked about the hybrid: "It is the central proposal. These results tell us what to feed it first."</li></ul>

<h2 id="glossary">Glossary</h2>
<div class="tablewrap"><table><thead><tr><th>Term</th><th>Meaning</th></tr></thead><tbody>
<tr><td>Stage</td><td>Water height at the gauge, in feet.</td></tr>
<tr><td>Forecast horizon</td><td>How far ahead we predict: 15 min, 30 min, 1 h, 3 h.</td></tr>
<tr><td>Baseline</td><td>A simple method a new model must beat.</td></tr>
<tr><td>Persistence</td><td>Predict that the future equals the present.</td></tr>
<tr><td>Damped trend</td><td>Extend the recent rate of change, reduced by a damping factor.</td></tr>
<tr><td>RMSE</td><td>Typical size of the forecast error, in feet. Lower is better.</td></tr>
<tr><td>Cross-validation</td><td>Repeating the train-then-test process on several periods.</td></tr>
<tr><td>Leakage</td><td>Test information accidentally reaching the model during training, which makes results look better than they are.</td></tr>
<tr><td>Storm cluster</td><td>Several flood events from the same storm; they are not independent.</td></tr>
<tr><td>Lead time</td><td>How much earlier a warning arrives than the event.</td></tr>
<tr><td>Upstream gauge</td><td>A river gauge higher up the river, so water reaches it first.</td></tr>
<tr><td>Exploratory</td><td>Results from data that has been looked at before, so not a clean final test.</td></tr>
<tr><td>Hybrid model</td><td>The proposed model that combines a Transformer and an LSTM. Not built yet.</td></tr>
</tbody></table></div>

<h2 id="files">Where everything is</h2>
<div class="tablewrap"><table><thead><tr><th>What</th><th>File in the project</th></tr></thead><tbody>
<tr><td>Overview and how to run it</td><td><code>README.md</code></td></tr>
<tr><td>Latest results report</td><td><code>reports/PHASE1D_REPORT.md</code></td></tr>
<tr><td>Upstream gauge study</td><td><code>docs/UPSTREAM_INPUT_FEASIBILITY.md</code></td></tr>
<tr><td>Short brief for the guide</td><td><code>docs/GUIDE_BRIEF.md</code></td></tr>
<tr><td>Plans written before each experiment</td><td><code>docs/PHASE1A_PROTOCOL.md</code> to <code>PHASE1E_PROTOCOL.md</code></td></tr>
<tr><td>Questions and answers for the viva</td><td><code>docs/VIVA_STUDY_GUIDE.md</code></td></tr>
<tr><td>Every experiment and its status</td><td><code>experiments/REGISTRY.md</code></td></tr>
</tbody></table></div>
<p class="foot">All numbers come from the project's own result tables and every result is exploratory. Data: US Geological Survey and NOAA (public), ERA5 via Open-Meteo (CC BY 4.0). Page generated from the project by <code>scripts/make_explainer.py</code>.</p>
</div>"""


if __name__ == "__main__":
    c1, c2, delay, leads = build_charts()
    OUT.write_text(page(c1, c2, delay, leads))
    print("written", OUT, f"({OUT.stat().st_size // 1024} KB); forecast delay {delay:.1f} h; leads {leads}")
