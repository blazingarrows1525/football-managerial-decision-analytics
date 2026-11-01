"""Execute the notebook top-to-bottom in a fresh kernel and save outputs in place.

Usage: python scripts/execute_notebook.py [--mode REAL_OPEN_DATA|DEMO_SYNTHETIC] [--out path.ipynb]

FMA_HEADLESS=1 is set so live ipywidgets controls print a note instead of
rendering (static default views are always produced).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks" / "Football_Managerial_Decision_Analytics.ipynb"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default=None, help="override DATA_MODE in the configuration cell")
    ap.add_argument("--out", default=str(NB))
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()
    nb = nbformat.read(NB, as_version=4)
    if args.mode:
        for c in nb.cells:
            if c.cell_type == "code" and "DATA_MODE      =" in c.source:
                c.source = re.sub(r"DATA_MODE\s+= fcfg\.\w+", f"DATA_MODE      = fcfg.{args.mode}", c.source)
    os.environ["FMA_HEADLESS"] = "1"
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    client = NotebookClient(nb, timeout=args.timeout, kernel_name="python3",
                            resources={"metadata": {"path": str(NB.parent)}})
    t0 = time.perf_counter()
    try:
        client.execute()
        status = 0
    except Exception as exc:  # report the failing cell, still save partial outputs
        print(f"EXECUTION FAILED: {type(exc).__name__}: {str(exc)[:2000]}", file=sys.stderr)
        status = 1
    nbformat.write(nb, args.out)
    n_code = sum(c.cell_type == "code" for c in nb.cells)
    n_err = sum(any(o.get("output_type") == "error" for o in c.get("outputs", [])) for c in nb.cells
                if c.cell_type == "code")
    print(f"executed {n_code} code cells in {time.perf_counter() - t0:.0f}s; cells with errors: {n_err}; "
          f"saved {args.out} ({Path(args.out).stat().st_size / 1e6:.1f} MB)")
    return status or (1 if n_err else 0)


if __name__ == "__main__":
    sys.exit(main())
