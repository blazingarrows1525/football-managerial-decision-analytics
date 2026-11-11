"""Event-level flags (progressive actions, box entries, shot outcomes, ...)."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.data.parsers import SENDING_OFF_CARDS, SET_PIECE_PASS_TYPES, TACKLE_WON_OUTCOMES
from src.features.player_features import COUNT_COLS

GOAL_X, GOAL_Y = 120.0, 40.0

ON_BALL_TYPES = {"Pass", "Ball Receipt*", "Carry", "Shot", "Dribble", "Miscontrol", "Dispossessed", "Clearance",
                 "Interception", "Ball Recovery", "Block", "Goal Keeper", "50/50", "Shield"}

ON_TARGET = {"Goal", "Saved", "Saved To Post", "Saved to Post"}

GK_SAVE_TYPES = {"Shot Saved", "Shot Saved Off T", "Shot Saved To Post", "Penalty Saved", "Penalty Saved To Post",
                 "Save"}

GK_CLAIM_TYPES = {"Collected", "Punch", "Keeper Sweeper", "Smother"}


def _closer(x, y, ex, ey, frac=0.25):
    d0 = np.hypot(GOAL_X - x, GOAL_Y - y)
    d1 = np.hypot(GOAL_X - ex, GOAL_Y - ey)
    return d1 <= (1 - frac) * d0


def _in_box(x, y):
    return (x >= 102) & (y >= 18) & (y <= 62)


def event_flags(events: pd.DataFrame) -> pd.DataFrame:
    """Add one boolean/numeric column per countable action (periods 1-4 only)."""
    ev = events[events["period"].between(1, 4)].copy()
    t = ev["type"]
    is_pass = t == "Pass"
    completed = is_pass & ev["outcome"].isna()
    open_play = ~ev["pass_type"].isin(SET_PIECE_PASS_TYPES)
    ev["passes"] = is_pass
    ev["passes_completed"] = completed
    ev["long_passes"] = is_pass & (ev["pass_length"] >= 30)
    ev["long_passes_completed"] = completed & (ev["pass_length"] >= 30)
    ev["progressive_passes"] = (completed & open_play & (ev["x"] >= 48) & (ev["end_x"] >= 48)
                                & _closer(ev["x"], ev["y"], ev["end_x"], ev["end_y"]))
    ev["final_third_passes"] = completed & (ev["x"] < 80) & (ev["end_x"] >= 80)
    ev["box_passes"] = completed & ~_in_box(ev["x"], ev["y"]) & _in_box(ev["end_x"], ev["end_y"])
    ev["crosses_completed"] = completed & ev["pass_cross"].fillna(False).astype(bool)
    ev["through_balls"] = is_pass & ev["pass_through_ball"].fillna(False).astype(bool)
    ev["key_passes"] = is_pass & (ev["pass_shot_assist"].fillna(False) | ev["pass_goal_assist"].fillna(False)).astype(bool)
    ev["assists"] = is_pass & ev["pass_goal_assist"].fillna(False).astype(bool)
    is_shot = t == "Shot"
    ev["shots"] = is_shot
    ev["shots_on_target"] = is_shot & ev["outcome"].isin(ON_TARGET)
    ev["goals"] = is_shot & (ev["outcome"] == "Goal")
    ev["xg"] = np.where(is_shot, ev["shot_xg"].fillna(0.0), 0.0)
    ev["npxg"] = np.where(is_shot & (ev["shot_type"] != "Penalty"), ev["shot_xg"].fillna(0.0), 0.0)
    shot_xg = ev.loc[is_shot].set_index("event_id")["shot_xg"]
    ev["xa"] = np.where(is_pass, ev["pass_assisted_shot_id"].map(shot_xg).fillna(0.0), 0.0)
    is_carry = t == "Carry"
    ev["progressive_carries"] = (is_carry & _closer(ev["x"], ev["y"], ev["end_x"], ev["end_y"])
                                 & (ev["end_x"] >= 48) & ((ev["end_x"] - ev["x"]) >= 5))
    ev["carries_into_final_third"] = is_carry & (ev["x"] < 80) & (ev["end_x"] >= 80)
    ev["carries_into_box"] = is_carry & ~_in_box(ev["x"], ev["y"]) & _in_box(ev["end_x"], ev["end_y"])
    ev["dribbles"] = t == "Dribble"
    ev["dribbles_completed"] = ev["dribbles"] & (ev["outcome"] == "Complete")
    on_ball = t.isin(ON_BALL_TYPES) & ev["x"].notna()
    ev["touches"] = on_ball
    ev["box_touches"] = on_ball & _in_box(ev["x"], ev["y"])
    ev["final_third_touches"] = on_ball & (ev["x"] >= 80)
    ev["tackles"] = (t == "Duel") & (ev["duel_type"] == "Tackle")
    ev["tackles_won"] = ev["tackles"] & ev["outcome"].isin(TACKLE_WON_OUTCOMES)
    ev["interceptions"] = t == "Interception"
    ev["blocks"] = t == "Block"
    ev["clearances"] = t == "Clearance"
    ev["ball_recoveries"] = (t == "Ball Recovery") & (ev["outcome"] != "Failed")
    ev["pressures"] = t == "Pressure"
    ev["counterpressures"] = ev["pressures"] & ev["counterpress"].fillna(False).astype(bool)
    ev["aerials_won"] = ev["aerial_won"].fillna(False).astype(bool)
    ev["aerials_lost"] = (t == "Duel") & (ev["duel_type"] == "Aerial Lost")
    ev["defensive_actions"] = (ev["tackles"].astype(int) + ev["interceptions"] + ev["blocks"] + ev["clearances"]
                               + ev["ball_recoveries"])
    ev["fouls_committed"] = t == "Foul Committed"
    ev["fouls_won"] = t == "Foul Won"
    ev["yellow_cards"] = ev["card"] == "Yellow Card"
    ev["red_cards"] = ev["card"].isin(SENDING_OFF_CARDS)
    ev["turnovers"] = t.isin(["Dispossessed", "Miscontrol"])
    gk = t == "Goal Keeper"
    ev["gk_saves"] = gk & ev["goalkeeper_type"].isin(GK_SAVE_TYPES)
    ev["gk_claims"] = gk & ev["goalkeeper_type"].isin(GK_CLAIM_TYPES)
    ev["gk_goals_conceded"] = gk & (ev["goalkeeper_type"] == "Goal Conceded")
    for c in COUNT_COLS:
        if ev[c].dtype == bool:
            ev[c] = ev[c].astype(int)
    return ev


def event_family(t: str) -> str:
    """Group StatsBomb event types into readable families."""
    if t in ("Pass", "Ball Receipt*"):
        return "Passing"
    if t in ("Carry", "Dribble", "Miscontrol", "Dispossessed", "Shield"):
        return "Carrying & dribbling"
    if t in ("Pressure", "Duel", "Interception", "Block", "Clearance", "Ball Recovery", "Dribbled Past", "50/50",
             "Foul Committed", "Foul Won", "Error", "Offside"):
        return "Defending & duels"
    if t in ("Shot", "Goal Keeper", "Own Goal For", "Own Goal Against"):
        return "Shooting & goalkeeping"
    if t in ("Starting XI", "Half Start", "Half End", "Substitution", "Tactical Shift", "Injury Stoppage",
             "Player On", "Player Off", "Referee Ball-Drop", "Bad Behaviour"):
        return "Match administration"
    return "Other"


# ---------------------------------------------------------------------------
# Event selection shared by the pitch charts, the dashboard filters and the notebooks
# ---------------------------------------------------------------------------
# name -> (description, has an end location, row filter). Every filter uses source fields or flags defined above.
EVENT_KINDS: dict[str, tuple[str, bool, Any]] = {
    "Shots": ("Shot events", False, lambda f: f["type"] == "Shot"),
    "Passes": ("All pass attempts", True, lambda f: f["type"] == "Pass"),
    "Completed passes": ("Passes with no failure outcome", True, lambda f: f["passes_completed"] == 1),
    "Progressive passes": ("Completed passes starting at x >= 48 that end at least 25% closer to goal", True,
                           lambda f: f["progressive_passes"] == 1),
    "Key passes": ("Passes that directly assist a shot (source flag)", True, lambda f: f["key_passes"] == 1),
    "Crosses": ("Passes flagged as crosses by the source", True, lambda f: f["pass_cross"].astype(bool)),
    "Through balls": ("Passes flagged as through balls by the source", True,
                      lambda f: f["pass_through_ball"].astype(bool)),
    "Switches": ("Passes flagged as switches of play by the source", True, lambda f: f["pass_switch"].astype(bool)),
    "Set-piece passes": ("Corners, free kicks, throw-ins, goal kicks and kick-offs", True,
                         lambda f: f["pass_type"].isin(list(SET_PIECE_PASS_TYPES))),
    "Carries": ("Ball carries (movement with the ball)", True, lambda f: f["type"] == "Carry"),
    "Progressive carries": ("Carries that move the ball at least 25% closer to goal", True,
                            lambda f: f["progressive_carries"] == 1),
    "Dribbles": ("Take-on attempts", False, lambda f: f["type"] == "Dribble"),
    "Pressures": ("Pressure events applied to an opponent", False, lambda f: f["type"] == "Pressure"),
    "Ball recoveries": ("Ball Recovery events", False, lambda f: f["type"] == "Ball Recovery"),
    "Interceptions": ("Interception events", False, lambda f: f["type"] == "Interception"),
    "Tackles": ("Duels of type Tackle", False, lambda f: f["tackles"] == 1),
    "Clearances": ("Clearance events", False, lambda f: f["type"] == "Clearance"),
    "Blocks": ("Block events", False, lambda f: f["type"] == "Block"),
    "Defensive actions": ("Tackles, interceptions, blocks, clearances and recoveries", False,
                          lambda f: f["defensive_actions"] == 1),
    "Touches": ("On-ball events counted as touches", False, lambda f: f["touches"] == 1),
    "Goalkeeper actions": ("Goal Keeper events (saves, claims, sweeper actions)", False,
                           lambda f: f["type"] == "Goal Keeper"),
    "Fouls committed": ("Foul Committed events", False, lambda f: f["type"] == "Foul Committed"),
}


def select_events(flags: pd.DataFrame, kind: str = "Touches", team_id: Any = None, player_id: Any = None,
                  match_ids: Any = None, period: int | None = None, minute_range: tuple[float, float] | None = None,
                  outcome: str | None = None) -> pd.DataFrame:
    """Filter the event table by kind and the global filters. Returns a view-safe copy; input is not mutated."""
    if kind not in EVENT_KINDS:
        raise KeyError(f"unknown event kind {kind!r}; choose one of {sorted(EVENT_KINDS)}")
    m = EVENT_KINDS[kind][2](flags)
    if team_id is not None:
        m &= flags["team_id"] == team_id
    if player_id is not None:
        m &= flags["player_id"] == player_id
    if match_ids is not None:
        ids = match_ids if isinstance(match_ids, (list, tuple, set, np.ndarray, pd.Series)) else [match_ids]
        m &= flags["match_id"].isin(list(ids))
    if period is not None:
        m &= flags["period"] == period
    if minute_range is not None:
        m &= flags["minute"].between(minute_range[0], minute_range[1])
    if outcome == "successful":
        m &= flags["outcome"].isna() | flags["outcome"].isin(["Goal", "Complete", "Won", "Success", "Success In Play"])
    elif outcome == "unsuccessful":
        m &= flags["outcome"].notna() & ~flags["outcome"].isin(["Goal", "Complete", "Won", "Success",
                                                                "Success In Play"])
    return flags[m].copy()
