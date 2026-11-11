"""End-to-end orchestration: acquire -> parse -> validate -> features -> analytical tables.

Notebooks call the individual steps for storytelling; ``build_bundle`` runs them all and is what the
Streamlit dashboard, the tests and the report builder use. One code path means one set of metric definitions.
"""
from __future__ import annotations

import time
from typing import Any, Callable

import pandas as pd

from src.config import DEMO_SYNTHETIC, Config, default_config
from src.data.loaders import build_tables, load_manager_mapping
from src.data.schemas import Bundle
from src.data.statsbomb_client import DataStore, LazyMatchFiles, select_matches
from src.data.validators import quality_checks
from src.features.event_features import event_flags
from src.features.lineup_features import workload_features
from src.features.player_features import add_percentiles, all_metric_columns, player_match_stats, player_season_table
from src.features.substitution_features import enrich_substitutions
from src.features.team_features import team_match_stats
from src.logging_config import get_logger

log = get_logger(__name__)

Progress = Callable[[int, int, Any], None]


def prepare_synthetic(config: Config) -> None:
    """Generate the DEMO_SYNTHETIC fixture dataset into ``data/raw/synthetic`` if it is absent."""
    from src.data.synthetic import write_synthetic_dataset

    if config.data_mode != DEMO_SYNTHETIC:
        raise ValueError("prepare_synthetic is only valid in DEMO_SYNTHETIC mode")
    if not (config.raw_dir / "competitions.json").exists():
        write_synthetic_dataset(config.raw_dir, seed=config.random_seed)


def acquire(config: Config, offline: bool = False, progress: Progress | None = None
            ) -> tuple[DataStore, pd.DataFrame, list[dict], list[dict], LazyMatchFiles]:
    """Catalogue -> match list -> lazily loaded match files (downloaded once, then read from the raw cache)."""
    if config.data_mode == DEMO_SYNTHETIC:
        prepare_synthetic(config)
    store = DataStore(config, offline=offline)
    catalogue = store.competitions()
    known = ((catalogue["competition_id"] == config.competition_id)
             & (catalogue["season_id"] == config.season_id)).any()
    if not known:
        raise ValueError(f"competition_id={config.competition_id}, season_id={config.season_id} is not in the "
                         f"source catalogue; choose a pair from the catalogue table.")
    matches_raw = store.matches_raw(config.competition_id, config.season_id)
    selected = select_matches(matches_raw, config.match_limit, config.focus_team)
    files = LazyMatchFiles(store, [m["match_id"] for m in selected], include_360=False, progress=progress)
    return store, catalogue, matches_raw, selected, files


def build_features(bundle: Bundle) -> Bundle:
    """Run every feature step in order and store the analytical tables on the bundle."""
    cfg, t = bundle.config, bundle.tables
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


def build_bundle(config: Config | None = None, offline: bool = False, use_cache: bool = True,
                 progress: Progress | None = None) -> Bundle:
    """Return the fully populated bundle, reading the processed cache when its fingerprint still matches."""
    from src.data import cache

    config = config or default_config()
    if config.data_mode == DEMO_SYNTHETIC:
        prepare_synthetic(config)
    if use_cache:
        cached = cache.load_bundle(config)
        if cached is not None:
            return cached
    t0 = time.perf_counter()
    store, catalogue, matches_raw, selected, files = acquire(config, offline=offline, progress=progress)
    bundle = Bundle(config=config, store=store, catalogue=catalogue, matches_available=len(matches_raw))
    build_tables(bundle, selected, files)
    bundle.timings["acquire_parse_s"] = time.perf_counter() - t0
    bundle.manifest = store.manifest_frame()
    mapping = load_manager_mapping(config.project_root / config.managers_csv)
    if bundle.tables["managers"].empty and mapping is not None:
        bundle.tables["managers"] = mapping
        bundle.manager_source = "user-supplied managers.csv"
    bundle.quality, bundle.quality_log = quality_checks(bundle.tables)
    build_features(bundle)
    bundle.timings["total_s"] = time.perf_counter() - t0
    log.info("bundle built in %.1fs (%s events, %s matches)", bundle.timings["total_s"],
             len(bundle.tables["events"]), len(bundle.tables["matches"]))
    if use_cache:
        try:
            cache.save_bundle(bundle)
        except Exception as exc:  # a cache failure must never break the analysis
            log.warning("processed cache not written: %s", exc)
    return bundle


def focus_team(bundle: Bundle) -> str:
    """Configured focus team, or the team with the most analysed matches when none is configured."""
    if bundle.config.focus_team and bundle.config.focus_team in set(bundle.team_stats["team_name"]):
        return bundle.config.focus_team
    return str(bundle.team_stats["team_name"].value_counts().index[0])


def subset_bundle(bundle: Bundle, match_ids: Any) -> Bundle:
    """A new bundle restricted to the given matches, with every feature table rebuilt on that subset.

    Used by the dashboard's global filters (opponent, venue, date range, result) so that every KPI and chart is
    computed from the filtered matches rather than merely hidden. The source bundle is not modified.
    """
    ids = set(match_ids)
    tables = {}
    for name, df in bundle.tables.items():
        if isinstance(df, pd.DataFrame) and "match_id" in df.columns:
            tables[name] = df[df["match_id"].isin(ids)].reset_index(drop=True)
        else:
            tables[name] = df
    sub = Bundle(config=bundle.config, store=bundle.store, catalogue=bundle.catalogue,
                 matches_available=bundle.matches_available, tables=tables, manifest=bundle.manifest,
                 manager_source=bundle.manager_source, timings=dict(bundle.timings))
    sub.quality, sub.quality_log = quality_checks(sub.tables)
    build_features(sub)
    return sub
