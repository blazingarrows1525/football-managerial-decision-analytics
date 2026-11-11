"""Score state, manpower state and timing-band helpers."""
from __future__ import annotations

import pandas as pd
from typing import Any


def score_at(goals: pd.DataFrame, match_id: Any, team_id: Any, opponent_id: Any,
             elapsed: float | None = None, before_index: int | None = None) -> tuple[int, int]:
    """(team goals, opponent goals) strictly before an event index or elapsed minute."""
    g = goals[goals["match_id"] == match_id]
    if before_index is not None:
        g = g[g["index"] < before_index]
    elif elapsed is not None:
        g = g[g["elapsed_min"] < elapsed]
    return int((g["scoring_team_id"] == team_id).sum()), int((g["scoring_team_id"] == opponent_id).sum())


def state_label(goal_diff: int) -> str:
    return "leading" if goal_diff > 0 else ("trailing" if goal_diff < 0 else "drawing")


def men_on_pitch(send_offs: pd.DataFrame, match_id: Any, team_id: Any, opponent_id: Any,
                 elapsed: float | None = None, before_index: int | None = None) -> int:
    """Numerical advantage (+) / disadvantage (-) from sending-offs before the moment."""
    s = send_offs[send_offs["match_id"] == match_id]
    if before_index is not None:
        s = s[s["index"] < before_index]
    elif elapsed is not None:
        s = s[s["elapsed_min"] < elapsed]
    return int((s["team_id"] == opponent_id).sum() - (s["team_id"] == team_id).sum())


def assign_band(period: Any, minute: Any, bands: list[dict]) -> str | None:
    """Assign a (period, clock minute) to a configured analytical band."""
    for b in bands:
        if period in b["periods"] and b["min"] <= minute <= b["max"]:
            return b["label"]
    return None
