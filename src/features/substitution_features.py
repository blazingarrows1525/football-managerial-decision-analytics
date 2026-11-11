"""Substitution enrichment: timing, state, role flow, bench reconstruction."""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any
from typing import TYPE_CHECKING

from src.config import role_for_position
from src.features.match_state import assign_band, men_on_pitch, score_at, state_label

if TYPE_CHECKING:
    from src.config import Config


def _windows(team_subs: pd.DataFrame, rules: dict) -> list[int]:
    """Window number per substitution; interval (period-start) changes optionally free."""
    out, w, last_t = [], 0, None
    for _, s in team_subs.iterrows():
        interval = s["second"] == 0 and s["minute"] in (45, 90, 105) and s["period"] in (2, 3, 4)
        if interval and not rules.get("interval_changes_use_window", False):
            out.append(0)
            continue
        if last_t is None or (s["elapsed_min"] - last_t) * 60 > rules.get("window_grouping_seconds", 90):
            w += 1
        last_t = s["elapsed_min"]
        out.append(w)
    return out


def enrich_substitutions(bundle: Any) -> pd.DataFrame:
    """One row per substitution with game state, timing band, roles, rule usage and manager."""
    cfg: Config = bundle.config
    t = bundle.tables
    subs, matches, goals, so = t["substitutions_raw"].copy(), t["matches"], t["goals"], t["sending_offs"]
    if subs.empty:
        return subs
    app = t["appearances"]
    m = matches.set_index("match_id")
    rows = []
    for _, s in subs.iterrows():
        mm = m.loc[s["match_id"]]
        home = s["team_id"] == mm["home_team_id"]
        opp = mm["away_team_id"] if home else mm["home_team_id"]
        tg, og = score_at(goals, s["match_id"], s["team_id"], opp, before_index=s["index"])
        rows.append({"home_away": "home" if home else "away", "opponent_id": opp,
                     "opponent": mm["away_team"] if home else mm["home_team"], "match_date": mm["match_date"],
                     "team_score": tg, "opponent_score": og, "goal_diff": tg - og, "game_state": state_label(tg - og),
                     "man_advantage": men_on_pitch(so, s["match_id"], s["team_id"], opp, before_index=s["index"])})
    subs = pd.concat([subs.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    subs["timing_band"] = [assign_band(p, mi, cfg.sub_timing_bands) for p, mi in zip(subs["period"], subs["minute"])]
    subs["match_phase"] = [assign_band(p, mi, cfg.match_phases) for p, mi in zip(subs["period"], subs["minute"])]
    on_pos = app.set_index(["match_id", "player_id"])["match_position"]
    subs["on_position"] = [on_pos.get((a, b)) for a, b in zip(subs["match_id"], subs["player_on_id"])]
    subs["off_role"] = subs["off_position"].map(role_for_position)
    subs["on_role"] = subs["on_position"].map(role_for_position)
    subs["like_for_like"] = subs["off_role"] == subs["on_role"]
    # Lineup-file display names (nickname when published) — event names are full legal names.
    disp = app.drop_duplicates(["match_id", "player_id"]).set_index(["match_id", "player_id"])["player_name"]
    subs["player_on_display"] = [disp.get((a, b), n) for a, b, n in zip(subs["match_id"], subs["player_on_id"],
                                                                         subs["player_on_name"])]
    subs["player_off_display"] = [disp.get((a, b), n) for a, b, n in zip(subs["match_id"], subs["player_off_id"],
                                                                          subs["player_off_name"])]
    subs = subs.sort_values(["match_id", "team_id", "index"])
    subs["sub_number"] = subs.groupby(["match_id", "team_id"]).cumcount() + 1
    subs["window_number"] = 0
    for _, idx in subs.groupby(["match_id", "team_id"]).groups.items():
        subs.loc[idx, "window_number"] = _windows(subs.loc[idx], cfg.sub_rules)
    et = subs["period"] >= 3
    subs["max_subs_allowed"] = cfg.sub_rules["max_substitutions"] + np.where(
        et, cfg.sub_rules["extra_time_additional_substitutions"], 0)
    subs["subs_remaining_after"] = subs["max_subs_allowed"] - subs["sub_number"]
    subs["rule_source"] = cfg.sub_rules["source"]
    subs["multi_sub_window"] = subs.duplicated(["match_id", "team_id", "window_number"], keep=False) & (
        subs["window_number"] > 0)
    mg = t["managers"].drop_duplicates(["match_id", "team_id"])
    if not mg.empty:
        subs = subs.merge(mg[["match_id", "team_id", "manager_id", "manager_name"]], on=["match_id", "team_id"],
                          how="left")
    # Identity validation against squads
    squad = set(zip(app["match_id"], app["player_id"]))
    subs["identity_check"] = np.where(
        [(a, b) in squad and (a, c) in squad for a, b, c in zip(subs["match_id"], subs["player_off_id"],
                                                               subs["player_on_id"])], "ok",
        "player not found in matchday squad")
    return subs.sort_values(["match_date", "match_id", "index"]).reset_index(drop=True)


def timing_profile(subs: pd.DataFrame, by: str | None = None, bands: list[dict] | None = None) -> pd.DataFrame:
    """Counts and shares of substitutions per timing band (optionally per group)."""
    if subs.empty:
        return pd.DataFrame()
    order = [b["label"] for b in bands] if bands else sorted(subs["timing_band"].dropna().unique())
    keys = [by, "timing_band"] if by else ["timing_band"]
    c = subs.groupby(keys).size().rename("substitutions").reset_index()
    total = c.groupby(by)["substitutions"].transform("sum") if by else c["substitutions"].sum()
    c["share_pct"] = (c["substitutions"] / total * 100).round(1)
    c["timing_band"] = pd.Categorical(c["timing_band"], categories=order, ordered=True)
    return c.sort_values(keys).reset_index(drop=True)


def state_profile(subs: pd.DataFrame, by: str | None = None) -> pd.DataFrame:
    keys = [by, "game_state"] if by else ["game_state"]
    g = subs.groupby(keys)
    out = pd.DataFrame({"substitutions": g.size(), "median_minute": g["minute"].median(),
                        "mean_minute": g["minute"].mean().round(1),
                        "attacking_change_pct": g.apply(lambda d: (d["on_role"].isin(["CF", "W", "AM"])
                                                                   & ~d["off_role"].isin(["CF", "W", "AM"])).mean()
                                                        * 100).round(1)}).reset_index()
    return out


def role_flow(subs: pd.DataFrame) -> pd.DataFrame:
    """Outgoing role -> incoming role counts (for the flow / Sankey chart)."""
    f = subs.dropna(subset=["off_role", "on_role"]).groupby(["off_role", "on_role"]).size().rename("count")
    return f.reset_index()


def on_pitch_at(spells: pd.DataFrame, match_id: Any, team_id: Any, elapsed: float) -> pd.DataFrame:
    s = spells[(spells["match_id"] == match_id) & (spells["team_id"] == team_id)]
    return s[(s["start"] <= elapsed) & (s["end"] > elapsed)]


def bench_at(appearances: pd.DataFrame, spells: pd.DataFrame, match_id: Any, team_id: Any, elapsed: float
             ) -> pd.DataFrame:
    """Eligible incoming players: matchday-squad members who have not appeared before ``elapsed``.

    A player who came on and was later replaced cannot return; a starter is never on the bench.
    """
    sq = appearances[(appearances["match_id"] == match_id) & (appearances["team_id"] == team_id)]
    s = spells[(spells["match_id"] == match_id) & (spells["team_id"] == team_id)]
    used = set(s.loc[s["start"] <= elapsed, "player_id"])
    return sq[~sq["player_id"].isin(used)]


def substitution_decisions(subs: pd.DataFrame, grouping_seconds: float = 90) -> pd.DataFrame:
    """Collapse simultaneous changes (same team, within ``grouping_seconds``) into one decision."""
    if subs.empty:
        return pd.DataFrame()
    rows = []
    for (mid, tid), g in subs.sort_values("elapsed_min").groupby(["match_id", "team_id"]):
        gid, last = 0, None
        for _, s in g.iterrows():
            if last is None or (s["elapsed_min"] - last) * 60 > grouping_seconds:
                gid += 1
            last = s["elapsed_min"]
            rows.append({**s.to_dict(), "decision_id": f"{mid}-{tid}-{gid}"})
    d = pd.DataFrame(rows)
    agg = d.groupby("decision_id").agg(
        match_id=("match_id", "first"), team_id=("team_id", "first"), opponent_id=("opponent_id", "first"),
        team_name=("team_name", "first"), elapsed_min=("elapsed_min", "min"), minute=("minute", "first"),
        game_state=("game_state", "first"), n_changes=("index", "size"),
        players_on=("player_on_name", lambda x: ", ".join(x)), players_off=("player_off_name", lambda x: ", ".join(x)))
    return agg.reset_index()
