"""End-to-end orchestration: acquire -> parse -> validate -> features -> analytical tables.

The notebook calls the individual steps for storytelling; ``build_bundle`` runs
them all (used by tests, the export step and quick re-runs).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .config import Config, DEMO_SYNTHETIC
from .features import (add_percentiles, all_metric_columns, event_flags, player_match_stats, player_season_table,
                       team_match_stats, workload_features)
from .ingestion import DataStore, prepare_synthetic, select_matches
from .manager_analysis import load_manager_mapping
from .parsing import parse_all
from .substitution_analysis import enrich_substitutions
from .validation import quality_checks


@dataclass
class Bundle:
    """Container for every canonical and analytical table of one run."""
    config: Config
    store: DataStore | None = None
    catalogue: pd.DataFrame | None = None
    matches_available: int = 0
    tables: dict[str, Any] = field(default_factory=dict)
    flags: pd.DataFrame | None = None
    pms: pd.DataFrame | None = None
    season: pd.DataFrame | None = None
    season_pct: pd.DataFrame | None = None
    team_stats: pd.DataFrame | None = None
    workload: pd.DataFrame | None = None
    subs: pd.DataFrame | None = None
    quality: pd.DataFrame | None = None
    quality_log: pd.DataFrame | None = None
    timings: dict[str, float] = field(default_factory=dict)
    manager_source: str = "none"


def acquire(config: Config, offline: bool = False) -> tuple[DataStore, pd.DataFrame, list[dict], list[dict], dict]:
    """Catalogue -> match list -> selected match files (cached)."""
    if config.data_mode == DEMO_SYNTHETIC:
        prepare_synthetic(config)
    store = DataStore(config, offline=offline)
    catalogue = store.competitions()
    ok = ((catalogue["competition_id"] == config.competition_id) & (catalogue["season_id"] == config.season_id)).any()
    if not ok:
        raise ValueError(f"competition_id={config.competition_id}, season_id={config.season_id} is not in the "
                         f"source catalogue; choose a pair from the catalogue table.")
    matches_raw = store.matches_raw(config.competition_id, config.season_id)
    selected = select_matches(matches_raw, config.match_limit, config.focus_team)
    files = store.match_files([m["match_id"] for m in selected], include_360=config.include_360)
    return store, catalogue, matches_raw, selected, files


def build_tables(bundle: Bundle, selected: list[dict], files: dict) -> Bundle:
    cfg = bundle.config
    t0 = time.perf_counter()
    tables = parse_all(selected, files)
    bundle.timings["parse_s"] = time.perf_counter() - t0
    mapping = load_manager_mapping(cfg.project_root / cfg.managers_csv)
    if tables["managers"].empty and mapping is not None:
        tables["managers"] = mapping
        bundle.manager_source = "user-supplied managers.csv"
    elif not tables["managers"].empty:
        bundle.manager_source = "StatsBomb matches.json (managers field)"
    bundle.tables = tables
    return bundle


def build_features(bundle: Bundle) -> Bundle:
    cfg = bundle.config
    t = bundle.tables
    t0 = time.perf_counter()
    bundle.flags = event_flags(t["events"])
    bundle.pms = player_match_stats(bundle.flags, t["appearances"], t["matches"])
    bundle.season = player_season_table(bundle.pms, t["appearances"], cfg)
    bundle.season_pct = add_percentiles(bundle.season, all_metric_columns(cfg) + [
        "defensive_actions_p90", "touches_p90", "turnovers_p90"], cfg)
    bundle.team_stats = team_match_stats(bundle.flags, t["matches"], t["goals"], t["formations"], t["managers"])
    bundle.workload = workload_features(t["appearances"], t["matches"])
    bundle.subs = enrich_substitutions(bundle)
    bundle.timings["features_s"] = time.perf_counter() - t0
    return bundle


def build_bundle(config: Config, offline: bool = False) -> Bundle:
    """Run every step and return the populated bundle."""
    t0 = time.perf_counter()
    store, catalogue, matches_raw, selected, files = acquire(config, offline=offline)
    bundle = Bundle(config=config, store=store, catalogue=catalogue, matches_available=len(matches_raw))
    bundle.timings["acquire_s"] = time.perf_counter() - t0
    build_tables(bundle, selected, files)
    bundle.quality, bundle.quality_log = quality_checks(bundle.tables)
    build_features(bundle)
    bundle.timings["total_s"] = time.perf_counter() - t0
    return bundle
