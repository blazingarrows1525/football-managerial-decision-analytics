"""Raw-to-canonical table loading steps."""
from __future__ import annotations

import pandas as pd
import time
from pathlib import Path
from typing import TYPE_CHECKING

from src.data.parsers import parse_all

if TYPE_CHECKING:
    from src.data.schemas import Bundle


def build_tables(bundle: Bundle, selected: list, files: dict) -> Bundle:
    """Parse raw JSON into canonical tables (timed)."""
    t0 = time.perf_counter()
    bundle.tables = parse_all(selected, files)
    bundle.timings["parse_s"] = time.perf_counter() - t0
    bundle.manager_source = ("StatsBomb matches.json (managers field)" if not bundle.tables["managers"].empty
                             else "none — manager analysis unavailable")
    return bundle


def load_manager_mapping(path: Path) -> pd.DataFrame | None:
    """Optional user-supplied mapping: match_id, team_id, manager_name[, manager_id, source]."""
    if not path.exists():
        return None
    df = pd.read_csv(path)
    need = {"match_id", "team_id", "manager_name"}
    if not need.issubset(df.columns):
        raise ValueError(f"managers.csv must contain columns {need}")
    df["manager_source"] = df.get("source", "user-supplied managers.csv")
    return df
