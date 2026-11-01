import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture(scope="session")
def synthetic_bundle(tmp_path_factory):
    """Full pipeline on the synthetic demo league (offline)."""
    from football_analytics.config import Config, DEMO_SYNTHETIC
    from football_analytics.pipeline import build_bundle

    root = tmp_path_factory.mktemp("synthetic_project")
    cfg = Config(project_root=root, data_mode=DEMO_SYNTHETIC, competition_id=9999, season_id=9999, focus_team=None,
                 min_minutes=90, min_group_size=3)
    return build_bundle(cfg)
