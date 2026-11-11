"""Processed-table cache (Parquet) keyed by a fingerprint of the raw files and the code versions.

The raw JSON is parsed once; the canonical and analytical tables are then stored under
``data/processed/<fingerprint>/`` (git-ignored). The fingerprint covers the raw file names and sizes, the
parser/feature/schema versions and the analysis configuration, so a stale cache can never be served after a
definition changes. Nothing here is redistributed: the cache lives only on the machine that built it.
"""
from __future__ import annotations

import hashlib
import json
import pickle
import time
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import FEATURE_VERSION, PARSER_VERSION, SCHEMA_VERSION, Config
from src.data.schemas import ANALYTICAL_TABLES, Bundle
from src.logging_config import get_logger

log = get_logger(__name__)

CACHE_FORMAT = 2


def _raw_signature(config: Config) -> list[list[Any]]:
    """Stable signature of the raw cache: relative path and byte size of every JSON file."""
    root = config.raw_dir
    if not root.exists():
        return []
    return sorted([str(p.relative_to(root)).replace("\\", "/"), p.stat().st_size] for p in root.rglob("*.json")
                  if "three-sixty" not in p.parts)


def fingerprint(config: Config) -> str:
    """Hash of everything that determines the processed tables."""
    payload = {
        "format": CACHE_FORMAT, "schema": SCHEMA_VERSION, "parser": PARSER_VERSION, "feature": FEATURE_VERSION,
        "mode": config.data_mode, "competition": config.competition_id, "season": config.season_id,
        "match_limit": config.match_limit, "focus_team": config.focus_team, "min_minutes": config.min_minutes,
        "min_group_size": config.min_group_size, "role_metric_weights": config.role_metric_weights,
        "raw": _raw_signature(config),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


def cache_dir(config: Config) -> Path:
    return config.processed_dir / fingerprint(config)


def _write_frame(df: pd.DataFrame, path: Path) -> str:
    """Write one table as Parquet; fall back to pickle for column types Parquet cannot represent."""
    try:
        df.to_parquet(_file(path, "parquet"), index=False)
        return "parquet"
    except Exception as exc:
        log.info("%s stored as pickle (%s)", path.name, type(exc).__name__)
        df.to_pickle(_file(path, "pickle"))
        return "pickle"


def _file(path: Path, kind: str) -> Path:
    # Table keys contain dots ("tables.events"), so the extension is appended rather than substituted.
    return path.parent / f"{path.name}.{'parquet' if kind == 'parquet' else 'pkl'}"


def _read_frame(path: Path, kind: str) -> pd.DataFrame:
    return pd.read_parquet(_file(path, kind)) if kind == "parquet" else pd.read_pickle(_file(path, kind))


def save_bundle(bundle: Bundle) -> Path:
    """Persist every table of the bundle; returns the cache folder."""
    cfg = bundle.config
    if not _raw_signature(cfg):
        raise RuntimeError("raw cache is empty; nothing to fingerprint")
    out = cache_dir(cfg)
    out.mkdir(parents=True, exist_ok=True)
    kinds: dict[str, str] = {}
    for name, df in bundle.tables.items():
        if isinstance(df, pd.DataFrame):
            kinds[f"tables.{name}"] = _write_frame(df, out / f"tables.{name}")
    for name in ANALYTICAL_TABLES + ["catalogue", "quality", "quality_log", "manifest"]:
        df = getattr(bundle, name, None)
        if isinstance(df, pd.DataFrame):
            kinds[name] = _write_frame(df, out / name)
    meta = {"format": CACHE_FORMAT, "fingerprint": fingerprint(cfg), "kinds": kinds,
            "matches_available": bundle.matches_available, "manager_source": bundle.manager_source,
            "timings": bundle.timings, "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "schema_version": SCHEMA_VERSION, "parser_version": PARSER_VERSION, "feature_version": FEATURE_VERSION}
    (out / "cache_meta.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    return out


def load_bundle(config: Config) -> Bundle | None:
    """Return the cached bundle when a cache with the current fingerprint exists, else ``None``."""
    if not _raw_signature(config):
        return None
    src = cache_dir(config)
    meta_path = src / "cache_meta.json"
    if not meta_path.exists():
        return None
    t0 = time.perf_counter()
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        bundle = Bundle(config=config, matches_available=int(meta["matches_available"]),
                        manager_source=meta["manager_source"], timings=dict(meta["timings"]))
        for key, kind in meta["kinds"].items():
            df = _read_frame(src / key, kind)
            if key.startswith("tables."):
                bundle.tables[key.split(".", 1)[1]] = df
            else:
                setattr(bundle, key, df)
    except (OSError, ValueError, KeyError, pickle.UnpicklingError) as exc:
        log.warning("processed cache unreadable, rebuilding (%s)", exc)
        return None
    bundle.timings["cache_load_s"] = time.perf_counter() - t0
    bundle.from_cache = True
    return bundle
