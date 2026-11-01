"""Exports and auto-generated evidence documents built from the ACTUAL run.

``write_dataset_card`` and ``write_data_dictionary`` regenerate
``reports/DATASET_CARD.md`` and ``reports/DATA_DICTIONARY.md`` from the tables in
memory, so reported counts can never drift from the data.
"""
from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import COORDINATE_SYSTEM, SYNTHETIC_WARNING
from .data_sources import STATSBOMB_ATTRIBUTION, source_register
from .features import METRIC_DEFINITIONS, metric_dictionary
from .validation import coverage_summary, dataset_scale, missingness


def _df_md(df: pd.DataFrame, max_rows: int = 60) -> str:
    if df is None or df.empty:
        return "_(none)_"
    d = df.head(max_rows).copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].round(3)
    cols = [str(c) for c in d.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in d.itertuples(index=False):
        lines.append("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) else str(v).replace("|", "/")
                                       for v in row) + " |")
    return "\n".join(lines)


def export_tables(bundle: Any) -> pd.DataFrame:
    """Write processed analytical tables (CSV always; Parquet when pyarrow is available)."""
    cfg = bundle.config
    out_dir = cfg.processed_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    t = bundle.tables
    tables = {
        "matches": t["matches"], "managers": t["managers"], "appearances": t["appearances"],
        "substitutions": bundle.subs, "goals": t["goals"], "formations": t["formations"],
        "player_match_stats": bundle.pms, "player_season": bundle.season_pct, "team_match_stats": bundle.team_stats,
        "workload": bundle.workload, "period_bounds": t["period_bounds"],
        "events": t["events"].drop(columns=["tactics_lineup"], errors="ignore"),
    }
    rows = []
    for name, df in tables.items():
        if df is None:
            continue
        csv = out_dir / f"{name}.csv"
        if name != "events":  # events are large; parquet only
            df.to_csv(csv, index=False, encoding="utf-8")
        pq = out_dir / f"{name}.parquet"
        try:
            df.to_parquet(pq, index=False)
            pq_ok = True
        except Exception:
            pq_ok = False
        rows.append({"table": name, "rows": len(df), "columns": df.shape[1],
                     "csv": csv.name if name != "events" else "(parquet only)", "parquet": pq.name if pq_ok else "n/a"})
    return pd.DataFrame(rows)


def write_run_config(bundle: Any, extra: dict | None = None) -> Path:
    cfg = bundle.config
    path = cfg.exports_dir / "run_config.json"
    payload = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "python": platform.python_version(), "config": cfg.to_dict(), "timings_s": bundle.timings,
               "manager_source": bundle.manager_source, **(extra or {})}
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def write_manifest(bundle: Any) -> Path:
    path = bundle.config.exports_dir / "source_manifest.csv"
    bundle.store.manifest_frame().to_csv(path, index=False, encoding="utf-8")
    return path


def write_results_summary(bundle: Any, findings: dict[str, Any]) -> Path:
    cfg = bundle.config
    path = cfg.exports_dir / "results_summary.md"
    lines = [f"# Results summary — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", ""]
    if cfg.is_synthetic:
        lines += [f"> **{SYNTHETIC_WARNING}**", ""]
    lines += [f"Data mode: `{cfg.data_mode}`", ""]
    for k, v in findings.items():
        lines.append(f"## {k}")
        lines.append(_df_md(v) if isinstance(v, pd.DataFrame) else str(v))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_dataset_card(bundle: Any, path: Path) -> Path:
    cfg = bundle.config
    t = bundle.tables
    m = t["matches"]
    scale = dataset_scale(t, bundle.store.manifest_frame(), bundle.timings.get("total_s"))
    comp = m["competition_name"].iloc[0] if len(m) else "n/a"
    season = m["season_name"].iloc[0] if len(m) else "n/a"
    man = bundle.store.manifest_frame()
    first = man.loc[man["file_written_utc"] != "", "file_written_utc"].min() if not man.empty else "n/a"
    last_read = man["retrieved_utc"].max() if not man.empty else "n/a"
    inv = man.groupby("resource").agg(files=("relative_path", "size"), mb=("bytes", lambda b: round(b.sum() / 1e6, 2))
                                      ).reset_index() if not man.empty else pd.DataFrame()
    miss = missingness(t["events"], ["player_id", "team_id", "x", "y", "end_x", "outcome", "shot_xg",
                                     "pass_recipient_id", "position_name"])
    synthetic = cfg.is_synthetic
    text = f"""# Dataset Card

> Auto-generated by `football_analytics.reporting.write_dataset_card` from the executed run on
> {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. Do not edit counts by hand — re-run the notebook export cell.
{f"> **{SYNTHETIC_WARNING}**" if synthetic else ""}

## Source
| Field | Value |
|---|---|
| Data mode | `{cfg.data_mode}` |
| Provider | {"Synthetic generator (src/football_analytics/synthetic.py)" if synthetic else "StatsBomb Open Data (Hudl)"} |
| Source URL | {"n/a (generated locally)" if synthetic else "https://github.com/statsbomb/open-data (raw: " + cfg.statsbomb_base_url + ")"} |
| Licence / terms | {"n/a" if synthetic else "StatsBomb Open Data licence and attribution request — see repository LICENSE / README; educational, non-commercial use; cite StatsBomb and use its logo in published outputs. Verify current terms before redistribution."} |
| Raw files downloaded (UTC, earliest) | {first} |
| Last read from cache (UTC) | {last_read} |
| Competition / season | {comp} {season} (competition_id={cfg.competition_id}, season_id={cfg.season_id}) |
| Match selection | {"focus team: " + str(cfg.focus_team) if cfg.focus_team else "all teams"}; limit={cfg.match_limit}; {len(m)} analysed of {bundle.matches_available} published for this competition-season |
| Date coverage | {m['match_date'].min():%Y-%m-%d} to {m['match_date'].max():%Y-%m-%d} |
| Coordinate system | `{COORDINATE_SYSTEM}` |
| Attribution | {STATSBOMB_ATTRIBUTION if not synthetic else "Synthetic — no attribution"} |

## Scale (actual run)
{_df_md(scale)}

## File inventory
{_df_md(inv)}

## Coverage
{_df_md(coverage_summary(t))}

## Event-field missingness (all events; structural blanks expected — e.g. pressures have no outcome)
{_df_md(miss)}

## Relevant fields
Matches (date, teams, score, stage, stadium, referee, managers), lineups (matchday squad, jersey, positions,
cards), events (type, period, clock, team, player, position, location, end location, pass/shot/duel/...
qualifiers, StatsBomb xG, substitution replacement, tactics/formation).

## Intended use
Educational research on player performance, starting-XI and substitution decision support, and observable
managerial decision patterns. Not for betting, fantasy, scouting valuation or medical decisions.

## Known limitations
* StatsBomb open data covers selected competitions; this season's release covers one club's matches
  (team-centric sample): opponents appear in only 1-2 matches each, so their per-90 values are small-sample and
  measured against the same strong opponent.
* Only matches in the dataset are visible — cup / European fixtures are missing, so workload and rotation
  proxies under-count real load.
* No injury, suspension, training-load, tracking (except optional 360 frames, not used) or medical data.
* xG is StatsBomb's model output, not an observation.
* Manager identity from match metadata; no measures of leadership/man-management exist in the data.
"""
    path.write_text(text, encoding="utf-8")
    return path


TABLE_DOCS: dict[str, dict[str, str]] = {
    "matches": {"match_id": "StatsBomb match id (int)", "match_date": "kick-off date (local date, no tz)",
                "home_team_id/away_team_id": "StatsBomb team ids", "home_score/away_score": "final score (source)",
                "stadium/referee": "names when supplied; never imputed", "parsed": "events file parsed (bool)"},
    "appearances": {"squad_status": "starter / used_substitute / unused_substitute",
                    "minutes_played": "actual playing time incl. stoppage, periods 1-4, from event timeline",
                    "minutes_flag": "derived_from_events / unused_substitute / unknown_*",
                    "on_elapsed/off_elapsed": "elapsed playing minutes of entry/exit",
                    "sub_on_minute/sub_off_minute": "clock minute of entry/exit (stoppage counted, 45+2 = 47)",
                    "match_position": "most frequent event position in the match; match_role = project role code"},
    "substitutions": {"player_off_*/player_on_*": "direction from Substitution event: player leaves, replacement enters",
                      "team_score/opponent_score/goal_diff/game_state": "team-perspective score strictly before the event",
                      "timing_band": "configurable analytical band", "window_number": "0 = interval change; rules user-configured",
                      "man_advantage": "+ = opponent had more sending-offs before the event",
                      "identity_check": "players resolved against matchday squad"},
    "player_season": {"*_p90": "count / minutes_played * 90 (NaN if minutes = 0)",
                      "*_pct": "percentile within benchmark group of eligible players",
                      "eligible": "minutes_played >= config.min_minutes",
                      "sample_reliability": "min(1, minutes/900) * 100", "coverage_label": "high/moderate/low data coverage",
                      "primary_position": "minutes-weighted most common match position"},
    "team_match_stats": {"possession_proxy_pct": "PROXY: team passes / all passes in match",
                         "field_tilt_pct": "PROXY: final-third on-ball actions share",
                         "ppda": "APPROXIMATION: opponent passes in own 60% / team tackles+interceptions+fouls+failed "
                                 "challenges in that zone",
                         "result/points": "from reconciled goal events"},
    "workload": {"minutes_prev_7d/14d/28d": "minutes in earlier DATASET matches within window (proxy, not fatigue)",
                 "rest_days": "days since previous dataset appearance", "started_prev_match": "started team's previous "
                 "dataset match"},
}


def write_data_dictionary(bundle: Any, path: Path) -> Path:
    tables = {"matches": bundle.tables["matches"], "managers": bundle.tables["managers"],
              "appearances": bundle.tables["appearances"], "events": bundle.tables["events"],
              "substitutions": bundle.subs, "player_season": bundle.season_pct,
              "team_match_stats": bundle.team_stats, "workload": bundle.workload}
    parts = [f"# Data Dictionary\n\n> Auto-generated from the executed run "
             f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC). Types and missingness are measured, not assumed.\n"]
    if bundle.config.is_synthetic:
        parts.append(f"> **{SYNTHETIC_WARNING}**\n")
    parts.append("## Metric definitions\n" + _df_md(metric_dictionary(), 100) + "\n")
    for name, df in tables.items():
        if df is None or df.empty:
            continue
        docs = TABLE_DOCS.get(name, {})
        rows = []
        for c in df.columns:
            if c == "tactics_lineup":
                continue
            desc = docs.get(c, "")
            if not desc:
                for k, v in docs.items():
                    if "*" in k and (c.endswith(k.replace("*", "")) or c.startswith(k.replace("*", ""))):
                        desc = v
                        break
                    if "/" in k and c in k.split("/"):
                        desc = v
                        break
            base = c[:-4] if c.endswith("_p90") else (c[:-4] if c.endswith("_pct") else c)
            if not desc and base in METRIC_DEFINITIONS:
                desc = METRIC_DEFINITIONS[base][0] + (" — per 90" if c.endswith("_p90") else
                                                      (" — percentile" if c.endswith("_pct") else ""))
            rows.append({"field": c, "dtype": str(df[c].dtype), "missing_pct": round(df[c].isna().mean() * 100, 1),
                         "description / derivation": desc})
        parts.append(f"## Table `{name}` — {len(df):,} rows\n" + _df_md(pd.DataFrame(rows), 400) + "\n")
    parts.append("## Source register\n" + _df_md(source_register()) + "\n")
    path.write_text("\n".join(parts), encoding="utf-8")
    return path
