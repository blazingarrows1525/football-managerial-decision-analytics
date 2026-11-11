"""Typed containers and table contracts shared by notebooks and the dashboard."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pandas as pd

from src.config import SCHEMA_VERSION

if TYPE_CHECKING:
    from src.config import Config
    from src.data.statsbomb_client import DataStore

# Analytical tables stored directly on the bundle (canonical tables live in ``bundle.tables``).
ANALYTICAL_TABLES = ["flags", "pms", "season", "season_pct", "team_stats", "workload", "subs"]


@dataclass
class Bundle:
    """Every canonical and analytical table of one run."""
    config: Config
    store: DataStore | None = None
    catalogue: pd.DataFrame | None = None
    matches_available: int = 0
    tables: dict = field(default_factory=dict)
    flags: pd.DataFrame | None = None
    pms: pd.DataFrame | None = None
    season: pd.DataFrame | None = None
    season_pct: pd.DataFrame | None = None
    team_stats: pd.DataFrame | None = None
    workload: pd.DataFrame | None = None
    subs: pd.DataFrame | None = None
    quality: pd.DataFrame | None = None
    quality_log: pd.DataFrame | None = None
    manifest: pd.DataFrame | None = None
    timings: dict = field(default_factory=dict)
    manager_source: str = "none"
    from_cache: bool = False

    def table(self, name: str) -> pd.DataFrame | None:
        """Look a table up by name: analytical tables first, then canonical tables. ``None`` when absent."""
        if name in ANALYTICAL_TABLES or name in ("quality", "quality_log", "manifest", "catalogue"):
            return getattr(self, name, None)
        value = self.tables.get(name)
        return value if isinstance(value, pd.DataFrame) else None


@dataclass(frozen=True)
class TableContract:
    """What a table must contain for the analyses built on it to be valid."""
    name: str
    grain: str
    key: tuple[str, ...]
    required: tuple[str, ...]
    origin: str            # "source" (parsed StatsBomb fields) or "derived" (computed by this project)
    description: str


TABLE_CONTRACTS: dict[str, TableContract] = {c.name: c for c in [
    TableContract("matches", "one row per match", ("match_id",),
                  ("match_id", "match_date", "home_team_id", "home_team", "away_team_id", "away_team", "home_score",
                   "away_score", "competition_id", "season_id"),
                  "source", "Match metadata from matches/<competition>/<season>.json."),
    TableContract("managers", "one row per match and team", ("match_id", "team_id"),
                  ("match_id", "team_id", "manager_name"),
                  "source", "Manager identity as published in the matches file."),
    TableContract("events", "one row per event", ("event_id",),
                  ("event_id", "match_id", "index", "period", "minute", "second", "type", "team_id", "team_name",
                   "player_id", "x", "y", "elapsed_min"),
                  "source", "Flattened event stream from events/<match_id>.json plus an elapsed-time clock."),
    TableContract("squads", "one row per match, team and squad player", ("match_id", "team_id", "player_id"),
                  ("match_id", "team_id", "player_id", "player_name"),
                  "source", "Match-day squads (starters and bench) from lineups/<match_id>.json."),
    TableContract("appearances", "one row per match and squad player", ("match_id", "player_id"),
                  ("match_id", "team_id", "team_name", "player_id", "player_name", "squad_status", "is_starter",
                   "minutes_played"),
                  "derived", "Minutes reconstructed from Starting XI, Substitution and sending-off events."),
    TableContract("spells", "one row per continuous on-pitch spell", ("match_id", "player_id", "start"),
                  ("match_id", "team_id", "player_id", "start", "end", "minutes"),
                  "derived", "On-pitch intervals used for minutes, bench state and pairing analysis."),
    TableContract("goals", "one row per goal", ("match_id", "index"),
                  ("match_id", "index", "scoring_team_id", "elapsed_min", "goal_type"),
                  "derived", "Goal timeline (shots with outcome Goal and own goals) reconciled with the scoreline."),
    TableContract("formations", "one row per formation record", ("match_id", "team_id", "index"),
                  ("match_id", "team_id", "index", "formation", "elapsed_min"),
                  "source", "Formations recorded on Starting XI and Tactical Shift events."),
    TableContract("flags", "one row per event", ("event_id",),
                  ("event_id", "match_id", "team_id", "player_id", "type", "x", "y"),
                  "derived", "Events with boolean analysis flags (progressive pass, key pass, box touch, ...)."),
    TableContract("pms", "one row per player and match", ("match_id", "player_id"),
                  ("match_id", "player_id", "team_id", "minutes_played"),
                  "derived", "Player match statistics (event counts joined to reconstructed minutes)."),
    TableContract("season_pct", "one row per player and team", ("player_id", "team_id"),
                  ("player_id", "player_name", "team_name", "primary_role", "minutes_played"),
                  "derived", "Player season totals, per-90 rates and role-group percentiles."),
    TableContract("team_stats", "one row per team and match", ("match_id", "team_id"),
                  ("match_id", "team_id", "team_name", "opponent", "goals_for", "goals_against", "xg", "xg_against",
                   "points", "result"),
                  "derived", "Team match statistics with opponent values and result."),
    TableContract("workload", "one row per player and match", ("match_id", "player_id"),
                  ("match_id", "team_id", "player_id"),
                  "derived", "Pre-match minutes-based exposure features (no physical-load data exists)."),
    TableContract("subs", "one row per substitution", ("match_id", "event_id"),
                  ("match_id", "team_id", "player_off_id", "player_on_id", "elapsed_min", "game_state"),
                  "derived", "Substitutions enriched with score state, timing band and roles."),
]}


def check_contracts(bundle: Bundle) -> pd.DataFrame:
    """Compare every table with its contract: presence, required columns and key uniqueness."""
    rows: list[dict[str, Any]] = []
    for name, c in TABLE_CONTRACTS.items():
        df = bundle.table(name)
        if df is None:
            rows.append({"table": name, "origin": c.origin, "rows": 0, "status": "MISSING",
                         "missing_columns": ", ".join(c.required), "duplicate_keys": None, "grain": c.grain})
            continue
        missing = [col for col in c.required if col not in df.columns]
        key_ok = all(k in df.columns for k in c.key)
        dup = int(df.duplicated(list(c.key)).sum()) if key_ok and len(df) else (None if not key_ok else 0)
        status = "PASS" if not missing and (dup == 0) else ("FLAG" if not missing else "FAIL")
        rows.append({"table": name, "origin": c.origin, "rows": len(df), "status": status,
                     "missing_columns": ", ".join(missing), "duplicate_keys": dup, "grain": c.grain})
    out = pd.DataFrame(rows)
    out.attrs["schema_version"] = SCHEMA_VERSION
    return out
