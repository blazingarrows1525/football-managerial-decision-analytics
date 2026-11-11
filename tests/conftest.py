"""Shared fixtures.

The suite runs entirely on a generated synthetic fixture league, so it needs no network and no real data
(this is what CI uses). Tests marked ``real_data`` additionally check the real StatsBomb cache and are
skipped automatically when ``data/raw/statsbomb`` is not present.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(Path(__file__).resolve().parent)):
    if p not in sys.path:
        sys.path.insert(0, p)

REAL_CACHE = ROOT / "data" / "raw" / "statsbomb" / "competitions.json"


def pytest_configure(config):
    config.addinivalue_line("markers", "real_data: needs the downloaded StatsBomb cache (skipped when absent)")
    config.addinivalue_line("markers", "slow: slower end-to-end checks")


def pytest_collection_modifyitems(config, items):
    if REAL_CACHE.exists():
        return
    skip = pytest.mark.skip(reason="real StatsBomb cache not present (data/raw/statsbomb)")
    for item in items:
        if "real_data" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def synthetic_config(tmp_path_factory):
    from src.config import DEMO_SYNTHETIC, Config

    root = tmp_path_factory.mktemp("synthetic_project")
    return Config(project_root=root, data_mode=DEMO_SYNTHETIC, competition_id=9999, season_id=9999,
                  focus_team="Synthetic Albion", min_minutes=90, min_group_size=3)


@pytest.fixture(scope="session")
def synthetic_ws(synthetic_config):
    """Workspace on the synthetic fixture league (offline, deterministic)."""
    from src.workspace import Workspace

    return Workspace.load(synthetic_config, use_cache=False)


@pytest.fixture(scope="session")
def synthetic_bundle(synthetic_ws):
    return synthetic_ws.bundle


@pytest.fixture(scope="session")
def real_ws():
    """Workspace on the real cached data (only for tests marked ``real_data``)."""
    from src.config import REAL_OPEN_DATA, Config
    from src.workspace import Workspace

    return Workspace.load(Config(data_mode=REAL_OPEN_DATA), offline=True)
