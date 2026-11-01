"""Zip the code, notebook and docs (no raw data) for upload to Google Colab.

Usage: python scripts/make_colab_bundle.py  ->  dist/football_analytics_colab_bundle.zip
"""
from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = ["src", "notebooks", "tests", "scripts", "reports", "requirements.txt", "README.md", "data/README.md"]
SKIP_PARTS = {"__pycache__", ".ipynb_checkpoints", ".pytest_cache"}


def main() -> Path:
    out = ROOT / "dist" / "football_analytics_colab_bundle.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for item in INCLUDE:
            p = ROOT / item
            files = [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file()]
            for f in files:
                if SKIP_PARTS & set(f.parts):
                    continue
                z.write(f, f.relative_to(ROOT))
        for d in ("data/raw", "data/processed", "data/external", "outputs/figures", "outputs/exports"):
            z.writestr(f"{d}/.gitkeep", "")
    print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB)")
    return out


if __name__ == "__main__":
    main()
