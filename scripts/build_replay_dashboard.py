"""Build the historical-replay dashboard (E19) from the SAVED out-of-fold predictions.
Exploratory retrospective historical replay: not a live forecasting system or an operational flood-warning service.
Usage (project root): PYTHONPATH=src python scripts/build_replay_dashboard.py        Output: dashboard/replay/index.html (self-contained, works offline)
Open it with:  open dashboard/replay/index.html     (or  python -m http.server --directory dashboard/replay  and browse to localhost:8000)
"""
import json
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
from flashflood import experiment, replay  # noqa: E402

DIR = Path("dashboard/replay")


def main() -> None:
    ctx = experiment.build_context()
    doc = replay.build_document(ctx)
    payload = json.dumps(doc, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    html = (DIR / "template.html").read_text()
    assert "__REPLAY_DATA__" in html
    out = DIR / "index.html"
    out.write_text(html.replace("__REPLAY_DATA__", payload))
    print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB; {doc['meta']['n_events']} events; {len(doc['meta']['models'])} models)")


if __name__ == "__main__":
    main()
