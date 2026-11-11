"""Source register, attribution text and raw-file inventory helpers."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd

SOURCE_REGISTER: list[dict[str, str]] = [
    {
        "source": "StatsBomb Open Data (Hudl)",
        "url": "https://github.com/hudl/open-data",
        "role_in_project": "PRIMARY: competitions, matches (incl. managers, referee, stadium), lineups, events",
        "access": "Public GitHub repository, raw JSON over HTTPS",
        "terms": "StatsBomb Public Data User Agreement (LICENSE.pdf in the repository): research and analysis "
                 "use; no redistribution, sale or commercial exploitation of the data; published analysis must "
                 "credit StatsBomb with its logo.",
        "status": "used",
    },
    {
        "source": "API-Football v3",
        "url": "https://www.api-football.com/documentation-v3",
        "role_in_project": "OPTIONAL enrichment (coach, injuries, fixtures) — requires the user's own key",
        "access": "REST API; key from Colab Secrets / environment variable API_FOOTBALL_KEY",
        "terms": "Subscription terms of the provider; coverage varies by league",
        "status": "not used by default (no key supplied)",
    },
    {
        "source": "Metrica Sports sample data",
        "url": "https://github.com/metrica-sports/sample-data",
        "role_in_project": "OPTIONAL separate tracking demo only (anonymised; never merged with named players)",
        "access": "Public GitHub repository",
        "terms": "See repository licence",
        "status": "not used",
    },
    {
        "source": "football-data.co.uk",
        "url": "https://www.football-data.co.uk/",
        "role_in_project": "OPTIONAL supplementary team-level results only",
        "access": "CSV downloads",
        "terms": "See website notes",
        "status": "not used",
    },
    {
        "source": "User-supplied files",
        "url": "data/external/",
        "role_in_project": "USER_DATA mode (StatsBomb-format JSON) and optional managers.csv mapping",
        "access": "Local files placed by the user",
        "terms": "User must hold rights to use the files",
        "status": "optional",
    },
]

STATSBOMB_ATTRIBUTION = (
    "Data: StatsBomb Open Data (https://github.com/hudl/open-data), provided by StatsBomb / Hudl. "
    "Used for educational, non-commercial research."
)


def source_register() -> pd.DataFrame:
    """Return the source register as a DataFrame."""
    return pd.DataFrame(SOURCE_REGISTER)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def raw_inventory(root: Path) -> pd.DataFrame:
    """Inventory of raw files on disk (count and bytes per resource folder)."""
    rows = []
    if root.exists():
        for p in root.rglob("*.json"):
            rel = p.relative_to(root)
            rows.append({"folder": rel.parts[0] if len(rel.parts) > 1 else "(root)",
                         "file": str(rel), "bytes": p.stat().st_size})
    return pd.DataFrame(rows, columns=["folder", "file", "bytes"])


# ---------------------------------------------------------------------------
# Machine-readable provenance manifest
# ---------------------------------------------------------------------------
SOURCE_REPOSITORY = "hudl/open-data"
SOURCE_REPOSITORY_URL = "https://github.com/hudl/open-data"
SOURCE_TERMS_URL = "https://github.com/hudl/open-data/blob/master/LICENSE.pdf"
SOURCE_DOCS_URL = "https://github.com/hudl/open-data/tree/master/doc"
ATTRIBUTION_REQUIREMENT = ("State StatsBomb as the data source and use the StatsBomb logo (Media Pack) when "
                           "publishing analysis based on the data.")
# Read from LICENSE.pdf of the source repository (StatsBomb Public Data User Agreement) on 2026-11-10.
TERMS_SUMMARY = [
    "The data are provided for analysis and research; analysis and conclusions may be shared publicly (1.1).",
    "The user may not edit, distort, distribute, reproduce, sell or provide the data to third parties (1.2.1).",
    "No commercial exploitation of the data or of analysis derived from it (1.2.2).",
    "Publications of analysis must be accredited with the StatsBomb brand logo (1.4).",
    "The service is provided as is; StatsBomb may withdraw it at any time (2.1, 3.2).",
]
DATA_LIMITATIONS = [
    "Team-centric sample: every analysed match involves the focus team; opponents appear twice (home and away).",
    "League matches only: no cup, European or international fixtures.",
    "No player age, height, injury, fitness, GPS, tracking, salary or market-value data.",
    "No post-shot xG; StatsBomb xG is a model output of the provider.",
    "StatsBomb 360 freeze frames are published for these matches but are optional and not loaded by default.",
    "Manager identity is the name recorded per match; tenure outside the analysed matches is unknown.",
]


def source_revision(timeout: int = 8) -> dict[str, str]:
    """Latest commit of the source repository at verification time. Reports failure instead of guessing."""
    import requests

    url = f"https://api.github.com/repos/{SOURCE_REPOSITORY}/commits/master"
    try:
        r = requests.get(url, timeout=timeout, headers={"Accept": "application/vnd.github+json"})
        r.raise_for_status()
        j = r.json()
        return {"status": "ok", "commit_sha": j["sha"], "commit_date": j["commit"]["committer"]["date"],
                "checked_via": url}
    except Exception as exc:
        return {"status": f"unavailable ({type(exc).__name__})", "commit_sha": "", "commit_date": "",
                "checked_via": url}


def build_manifest(bundle: Any, revision: dict[str, str] | None = None) -> dict[str, Any]:
    """Provenance manifest of one run: source, files with hashes, parsed row counts, validation and lineage."""
    from datetime import datetime, timezone

    from src.config import FEATURE_VERSION, PARSER_VERSION, SCHEMA_VERSION
    from src.data.schemas import ANALYTICAL_TABLES, TABLE_CONTRACTS, check_contracts

    cfg = bundle.config
    man = bundle.manifest if isinstance(bundle.manifest, pd.DataFrame) else pd.DataFrame()
    files = []
    if len(man):
        for r in man.sort_values("relative_path").itertuples():
            files.append({"path": r.relative_path, "resource": r.resource, "match_id": None if pd.isna(r.match_id)
                          else int(r.match_id), "bytes": int(r.bytes), "sha256": r.sha256, "status": r.status,
                          "source_url": r.source_url, "file_written_utc": r.file_written_utc})
    m = bundle.tables["matches"]
    tables = {}
    for name, df in bundle.tables.items():
        if isinstance(df, pd.DataFrame):
            tables[name] = {"rows": len(df), "columns": int(df.shape[1])}
    for name in ANALYTICAL_TABLES:
        df = getattr(bundle, name, None)
        if isinstance(df, pd.DataFrame):
            tables[name] = {"rows": len(df), "columns": int(df.shape[1])}
    q = bundle.quality if isinstance(bundle.quality, pd.DataFrame) else pd.DataFrame()
    contracts = check_contracts(bundle)
    written = [f["file_written_utc"] for f in files if f["file_written_utc"]]
    return {
        "manifest_version": "1.0.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_mode": cfg.data_mode,
        "synthetic": cfg.is_synthetic,
        "source": {
            "name": "StatsBomb Open Data" if not cfg.is_synthetic else "Synthetic test fixture (not real data)",
            "publisher": "StatsBomb / Hudl" if not cfg.is_synthetic else "this project (generated)",
            "repository": SOURCE_REPOSITORY_URL if not cfg.is_synthetic else "",
            "base_url": cfg.statsbomb_base_url if not cfg.is_synthetic else "",
            "terms_url": SOURCE_TERMS_URL if not cfg.is_synthetic else "",
            "documentation_url": SOURCE_DOCS_URL if not cfg.is_synthetic else "",
            "attribution_requirement": ATTRIBUTION_REQUIREMENT if not cfg.is_synthetic else "",
            "terms_summary": TERMS_SUMMARY if not cfg.is_synthetic else [],
            "revision_at_verification": revision or {"status": "not checked"},
        },
        "scope": {
            "competition_id": int(cfg.competition_id), "season_id": int(cfg.season_id),
            "competition_name": str(m["competition_name"].iloc[0]) if len(m) else "",
            "season_name": str(m["season_name"].iloc[0]) if len(m) else "",
            "focus_team": cfg.focus_team, "matches_published_for_season": int(bundle.matches_available),
            "matches_analysed": int(len(m)), "match_ids": sorted(int(i) for i in m["match_id"]),
            "first_match_date": str(m["match_date"].min().date()) if len(m) else "",
            "last_match_date": str(m["match_date"].max().date()) if len(m) else "",
        },
        "retrieval": {"earliest_file_written_utc": min(written) if written else "",
                      "latest_file_written_utc": max(written) if written else "",
                      "files": len(files), "bytes": int(sum(f["bytes"] for f in files)),
                      "failed_files": int(sum(f["status"] != "ok" for f in files))},
        "versions": {"parser": PARSER_VERSION, "schema": SCHEMA_VERSION, "feature": FEATURE_VERSION},
        "files": files,
        "tables": tables,
        "validation": {
            "rules_passed": int((q["status"] == "PASS").sum()) if len(q) else 0, "rules_total": int(len(q)),
            "rules": q.to_dict("records") if len(q) else [],
            "contracts_passed": int((contracts["status"] == "PASS").sum()), "contracts_total": int(len(contracts)),
        },
        "transformations": [
            "parse matches, lineups and events JSON into flat canonical tables (no raw row deleted)",
            "add an elapsed-minute clock from period bounds",
            "reconstruct on-pitch spells and minutes from Starting XI, Substitution and sending-off events",
            "derive event flags (progressive actions, box touches, key passes, ...)",
            "aggregate to player-match, player-season (per 90, role percentiles) and team-match tables",
            "enrich substitutions with score state, timing band, roles and rule windows",
        ],
        "derived_table_dependencies": {
            "appearances": ["events", "squads", "period_bounds"], "spells": ["events", "period_bounds"],
            "goals": ["events", "matches"], "formations": ["events"], "flags": ["events"],
            "pms": ["flags", "appearances", "matches"], "season": ["pms", "appearances"],
            "season_pct": ["season"], "team_stats": ["flags", "matches", "goals", "formations", "managers"],
            "workload": ["appearances", "matches"], "subs": ["substitutions_raw", "goals", "sending_offs",
                                                             "appearances", "team_stats"],
        },
        "table_contracts": {k: {"grain": c.grain, "key": list(c.key), "origin": c.origin}
                            for k, c in TABLE_CONTRACTS.items()},
        "data_limitations": DATA_LIMITATIONS if not cfg.is_synthetic else [
            "Synthetic fixture generated for tests and layout checks; not real football observations."],
    }


def write_manifest(bundle: Any, revision: dict[str, str] | None = None) -> Path:
    """Write ``data/manifest/source_manifest.json`` (hashes and counts only; no source data is redistributed)."""
    import json

    out = bundle.config.manifest_dir
    out.mkdir(parents=True, exist_ok=True)
    path = out / "source_manifest.json"
    path.write_text(json.dumps(build_manifest(bundle, revision), indent=1, default=str), encoding="utf-8")
    return path
