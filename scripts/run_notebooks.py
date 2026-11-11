"""Execute the research notebooks in fresh kernels and record what happened.

    python scripts/run_notebooks.py                 # all notebooks, static figures (visible on GitHub)
    python scripts/run_notebooks.py --interactive   # keep interactive Plotly outputs
    python scripts/run_notebooks.py --only Main     # notebooks whose name contains "Main"

Each notebook is executed top to bottom with nbclient and saved in place with its outputs. The run summary
(cells, errors, warnings written to stderr, figures, runtime) goes to
``artifacts/reports/notebook_execution.json``. The exit code is non-zero when any cell raised.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"


def audit(nb) -> dict:
    code = [c for c in nb.cells if c.cell_type == "code"]
    outs = [o for c in code for o in c.get("outputs", [])]
    stderr = [o for o in outs if o.get("output_type") == "stream" and o.get("name") == "stderr"]
    return {
        "cells": len(nb.cells), "code_cells": len(code),
        "markdown_cells": sum(c.cell_type == "markdown" for c in nb.cells),
        "executed_code_cells": sum(c.get("execution_count") is not None for c in code),
        "errors": sum(o.get("output_type") == "error" for o in outs),
        "stderr_outputs": len(stderr),
        "stderr_sample": ["".join(o["text"])[:300] for o in stderr[:3]],
        "static_figures": sum("image/png" in o.get("data", {}) for o in outs),
        "interactive_figures": sum("application/vnd.plotly.v1+json" in o.get("data", {}) for o in outs),
        "unavailable_chart_notices": sum("implemented but unavailable" in "".join(o.get("data", {}).get(
            "text/markdown", "")) or "not implemented" in "".join(o.get("data", {}).get("text/markdown", ""))
            for o in outs),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--interactive", action="store_true", help="keep interactive Plotly outputs (larger files)")
    ap.add_argument("--only", default="", help="run only notebooks whose file name contains this text")
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    os.environ["FMA_HEADLESS"] = "1"
    if not args.interactive:
        os.environ["FMA_STATIC"] = "1"
    paths = sorted(p for p in NB_DIR.glob("*.ipynb") if args.only.lower() in p.name.lower())
    if not paths:
        print("no notebooks found; run scripts/build_notebooks.py first")
        return 2
    results, failed = [], 0
    for path in paths:
        nb = nbformat.read(path, as_version=4)
        t0 = time.perf_counter()
        status = "ok"
        try:
            NotebookClient(nb, timeout=args.timeout, kernel_name="python3",
                           resources={"metadata": {"path": str(NB_DIR)}}).execute()
        except CellExecutionError as exc:
            status = f"cell error: {str(exc).splitlines()[-1][:200]}"
            failed += 1
        secs = time.perf_counter() - t0
        nbformat.write(nb, path)
        info = {"notebook": path.name, "status": status, "seconds": round(secs, 1),
                "size_mb": round(path.stat().st_size / 1e6, 2), **audit(nb)}
        results.append(info)
        print(f"{path.name}: {status} · {secs:.0f}s · {info['code_cells']} code cells · {info['errors']} errors · "
              f"{info['stderr_outputs']} stderr · {info['static_figures']} static + {info['interactive_figures']} "
              f"interactive figures · {info['size_mb']} MB")
    out = ROOT / "artifacts" / "reports"
    out.mkdir(parents=True, exist_ok=True)
    summary = {"executed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "python": platform.python_version(), "platform": platform.platform(),
               "figure_mode": "interactive" if args.interactive else "static PNG (FMA_STATIC=1)",
               "command": "python scripts/run_notebooks.py" + (" --interactive" if args.interactive else ""),
               "notebooks": results,
               "total_seconds": round(sum(r["seconds"] for r in results), 1),
               "total_errors": sum(r["errors"] for r in results)}
    if not args.only:
        (out / "notebook_execution.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"total {summary['total_seconds']}s · {summary['total_errors']} cell errors")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
