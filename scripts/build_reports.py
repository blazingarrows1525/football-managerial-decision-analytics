"""Build the evidence documents and the provenance manifest from the current data.

Run from the repository root:

    python scripts/build_reports.py            # real StatsBomb open data (downloads on first run)
    python scripts/build_reports.py --offline  # use the local raw cache only

Writes
    data/manifest/source_manifest.json
    docs/DATA_PROVENANCE.md, docs/DATA_DICTIONARY.md, docs/VISUALIZATION_CATALOGUE.md
    artifacts/tables/results.json, chart_status.csv, evidence_cards.csv
    artifacts/reports/ANALYSIS_REPORT_V3.md
Synthetic runs (FMA_DATA_MODE=DEMO_SYNTHETIC) write only under artifacts/synthetic and data/manifest/synthetic.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import default_config  # noqa: E402
from src.data.provenance import build_manifest, source_revision, write_manifest  # noqa: E402
from src.reporting import insight_cards, report_builder  # noqa: E402
from src.visualization import registry  # noqa: E402
from src.workspace import Workspace  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--offline", action="store_true", help="do not contact the network (raw cache only)")
    args = ap.parse_args()
    t0 = time.perf_counter()
    cfg = default_config()
    ws = Workspace.load(cfg, offline=args.offline, use_cache=False)
    print(f"bundle built in {time.perf_counter() - t0:.1f}s · {len(ws.tables['events']):,} events · "
          f"{len(ws.tables['matches'])} matches · mode {cfg.data_mode}")

    revision = {"status": "not checked (offline)"} if args.offline or cfg.is_synthetic else source_revision()
    manifest_path = write_manifest(ws.bundle, revision)
    manifest = build_manifest(ws.bundle, revision)
    print(f"manifest: {manifest_path} · source revision {revision.get('commit_sha') or revision['status']}")

    table = registry.status_table(ws, validate=True)
    counts = registry.status_counts(table)
    print("chart status:", counts)
    cards = insight_cards.build_cards(ws)
    snap = report_builder.results_snapshot(ws)
    snap["chart_status"] = counts

    for d in (cfg.tables_dir, cfg.reports_dir):
        d.mkdir(parents=True, exist_ok=True)
    (cfg.tables_dir / "results.json").write_text(json.dumps(snap, indent=1, default=str), encoding="utf-8")
    table.to_csv(cfg.tables_dir / "chart_status.csv", index=False, encoding="utf-8")
    insight_cards.cards_frame(cards).to_csv(cfg.tables_dir / "evidence_cards.csv", index=False, encoding="utf-8")
    (cfg.reports_dir / "ANALYSIS_REPORT_V3.md").write_text(
        report_builder.analysis_report_markdown(ws, snap, cards, counts), encoding="utf-8")

    if cfg.is_synthetic:
        print("synthetic mode: docs/ not written")
    else:
        docs = ROOT / "docs"
        docs.mkdir(exist_ok=True)
        (docs / "VISUALIZATION_CATALOGUE.md").write_text(report_builder.catalogue_markdown(ws, table),
                                                         encoding="utf-8")
        (docs / "DATA_DICTIONARY.md").write_text(report_builder.data_dictionary_markdown(ws), encoding="utf-8")
        (docs / "DATA_PROVENANCE.md").write_text(report_builder.provenance_markdown(manifest), encoding="utf-8")
    failed = counts[registry.FAILED_VALIDATION]
    print(f"done in {time.perf_counter() - t0:.1f}s · {failed} chart(s) failed validation")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
