"""Data-availability checks for chart specifications.

A chart is available only when every required table and column exists with data, the sample meets the stated
minimums and any optional package is installed. The reason names the exact missing piece so the limitation is
visible instead of being silently skipped.
"""
from __future__ import annotations

import importlib.util
from typing import Any

from src.visualization.registry import (IMPLEMENTED_AVAILABLE, IMPLEMENTED_UNAVAILABLE, NOT_IMPLEMENTED, ChartSpec)

HOW_TO_OBTAIN = {
    "frames_360": "download the optional StatsBomb 360 file for the match (Pitch & Event Explorer → 360 frames, or "
                  "DataStore.three_sixty(match_id))",
    "tracking": "optical or GPS tracking data from a licensed provider (not part of StatsBomb Open Data)",
    "player_bio": "an authorised player-metadata source joined on a verified player identifier",
}


def package_installed(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def check(spec: ChartSpec, ws: Any) -> tuple[str, str]:
    """Return ``(status, reason)`` for one specification against the loaded workspace."""
    if not spec.implemented:
        return NOT_IMPLEMENTED, spec.unavailable_reason
    if spec.requires_package and not package_installed(spec.requires_package):
        return IMPLEMENTED_UNAVAILABLE, (f"optional package '{spec.requires_package}' is not installed "
                                         f"(pip install -r requirements-optional.txt)")
    bundle = ws.bundle
    tables = set(spec.required_tables) | set(spec.required_columns)
    for t in sorted(tables):
        if t == "frames_360":
            if not ws.has_360():
                return IMPLEMENTED_UNAVAILABLE, ("no StatsBomb 360 file has been downloaded; to obtain it: "
                                                 + HOW_TO_OBTAIN[t])
            continue
        df = bundle.table(t)
        if df is None:
            how = HOW_TO_OBTAIN.get(t)
            return IMPLEMENTED_UNAVAILABLE, f"table '{t}' is not loaded" + (f"; to obtain it: {how}" if how else "")
        if len(df) < spec.minimum_rows:
            return IMPLEMENTED_UNAVAILABLE, f"table '{t}' has {len(df)} rows (needs at least {spec.minimum_rows})"
        missing = [c for c in spec.required_columns.get(t, ()) if c not in df.columns]
        if missing:
            return IMPLEMENTED_UNAVAILABLE, f"missing field(s) in '{t}': {', '.join(missing)}"
        empty = [c for c in spec.required_columns.get(t, ()) if df[c].notna().sum() == 0]
        if empty:
            return IMPLEMENTED_UNAVAILABLE, f"field(s) in '{t}' contain no values: {', '.join(empty)}"
    n_matches = len(ws.team_matches())
    if n_matches < spec.minimum_matches:
        return IMPLEMENTED_UNAVAILABLE, (f"{n_matches} matches for the focus team (needs at least "
                                         f"{spec.minimum_matches})")
    if spec.minimum_players:
        n_players = int(bundle.season_pct["eligible"].sum()) if bundle.season_pct is not None else 0
        if n_players < spec.minimum_players:
            return IMPLEMENTED_UNAVAILABLE, (f"{n_players} players above the minutes threshold (needs at least "
                                             f"{spec.minimum_players})")
    return IMPLEMENTED_AVAILABLE, ""


def missing_summary(spec: ChartSpec, ws: Any) -> dict[str, Any]:
    """Prerequisites of a chart and which of them are satisfied (for the chart explorer)."""
    status, reason = check(spec, ws)
    bundle = ws.bundle
    rows = []
    for t in sorted(set(spec.required_tables) | set(spec.required_columns)):
        df = bundle.table(t)
        cols = spec.required_columns.get(t, ())
        rows.append({"table": t, "loaded": df is not None, "rows": 0 if df is None else len(df),
                     "required_columns": ", ".join(cols) or "—",
                     "missing_columns": ", ".join(c for c in cols if df is None or c not in df.columns) or "—"})
    return {"status": status, "reason": reason, "tables": rows, "minimum_matches": spec.minimum_matches,
            "minimum_players": spec.minimum_players, "requires_package": spec.requires_package}
