"""Batch mode: export every available chart of the catalogue (never run automatically).

    python scripts/export_gallery.py                       # HTML for every available chart
    python scripts/export_gallery.py --formats html png    # add PNG (needs the optional kaleido package)
    python scripts/export_gallery.py --family J --limit 10 # one family, at most ten charts
    python scripts/export_gallery.py --ids C-042 L-262

Writes to ``artifacts/exports/`` (git-ignored) with a progress line per chart and an ``export_index.csv``.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.reporting import exports  # noqa: E402
from src.visualization import registry  # noqa: E402
from src.workspace import Workspace  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--formats", nargs="+", default=["html"], choices=["html", "json", "png", "svg", "pdf"])
    ap.add_argument("--family", default="", help="one family letter A–L")
    ap.add_argument("--ids", nargs="*", default=None, help="explicit chart IDs")
    ap.add_argument("--limit", type=int, default=None, help="maximum number of charts")
    ap.add_argument("--out", default=None, help="output folder (default artifacts/exports)")
    args = ap.parse_args()

    cap = exports.capabilities()
    if set(args.formats) & {"png", "svg", "pdf"} and not cap["plotly_static_images"]:
        print("note:", cap["plotly_static_note"], "Static formats will be reported as not written.")
    ws = Workspace.load()
    ids = args.ids or [s.chart_id for s in registry.all_specs()
                       if s.implemented and (not args.family or s.category == args.family.upper())]
    out = Path(args.out) if args.out else ws.cfg.project_root / "artifacts" / "exports"
    t0 = time.perf_counter()
    res = exports.export_eligible_charts(
        ws, out, ids, tuple(args.formats), args.limit,
        progress=lambda i, n, cid: print(f"[{i}/{n}] {cid} ({time.perf_counter() - t0:.0f}s)", flush=True))
    res.to_csv(out / "export_index.csv", index=False, encoding="utf-8")
    ok = int((res["status"] == "exported").sum()) if len(res) else 0
    print(f"{ok} of {len(res)} charts exported to {out} in {time.perf_counter() - t0:.0f}s")
    return 0 if ok == len(res) else 1


if __name__ == "__main__":
    sys.exit(main())
