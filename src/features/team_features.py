"""Team match statistics, formation and style summaries, expected points."""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any

from src.features.player_features import _safe_rate


def team_match_stats(flags: pd.DataFrame, matches: pd.DataFrame, goals: pd.DataFrame,
                     formations_df: pd.DataFrame, managers: pd.DataFrame) -> pd.DataFrame:
    """One row per team per match with style indicators (proxies labelled as such)."""
    sums = ["shots", "shots_on_target", "xg", "npxg", "passes", "passes_completed", "progressive_passes",
            "progressive_carries", "final_third_passes", "box_passes", "pressures", "counterpressures",
            "defensive_actions", "final_third_touches", "box_touches", "touches", "crosses_completed",
            "fouls_committed", "yellow_cards", "red_cards"]
    t = flags.groupby(["match_id", "team_id"])[sums].sum().reset_index()
    sp_shot = flags["shots"].astype(bool) & (flags["play_pattern"].isin(["From Corner", "From Free Kick",
                                                                          "From Throw In"])
                                             | flags["shot_type"].isin(["Free Kick", "Penalty", "Corner"]))
    t = t.merge(flags[sp_shot].groupby(["match_id", "team_id"]).size().rename("set_piece_shots").reset_index(),
                on=["match_id", "team_id"], how="left")
    t["set_piece_shots"] = t["set_piece_shots"].fillna(0)
    # PPDA approximation: opponent passes in their own 60% (x <= 72 in their frame) divided by the
    # team's tackles + interceptions + fouls + failed challenges in the same zone (x >= 48 in its frame).
    opp_pass = flags[flags["passes"].astype(bool) & (flags["x"] <= 72)].groupby(["match_id", "team_id"]).size()
    def_act = flags[(flags["tackles"].astype(bool) | flags["interceptions"].astype(bool)
                     | flags["fouls_committed"].astype(bool) | (flags["type"] == "Dribbled Past"))
                    & (flags["x"] >= 48)].groupby(["match_id", "team_id"]).size()
    m = matches.set_index("match_id")
    rows = []
    for _, r in t.iterrows():
        mid, tid = r["match_id"], r["team_id"]
        mm = m.loc[mid]
        home = tid == mm["home_team_id"]
        opp = mm["away_team_id"] if home else mm["home_team_id"]
        rows.append({"match_id": mid, "team_id": tid, "opponent_id": opp,
                     "team_name": mm["home_team"] if home else mm["away_team"],
                     "opponent": mm["away_team"] if home else mm["home_team"],
                     "home_away": "home" if home else "away", "match_date": mm["match_date"],
                     "ppda": (opp_pass.get((mid, opp), 0) / def_act.get((mid, tid), np.nan))
                     if def_act.get((mid, tid), 0) else np.nan})
    t = t.merge(pd.DataFrame(rows), on=["match_id", "team_id"], how="left")
    opp_cols = ["shots", "shots_on_target", "xg", "passes", "final_third_touches"]
    opp = t[["match_id", "team_id"] + opp_cols].rename(columns={"team_id": "opponent_id",
                                                                **{c: f"{c}_against" for c in opp_cols}})
    t = t.merge(opp, on=["match_id", "opponent_id"], how="left")
    gf = goals.groupby(["match_id", "scoring_team_id"]).size()
    t["goals_for"] = [gf.get((mm, tt), 0) for mm, tt in zip(t["match_id"], t["team_id"])]
    t["goals_against"] = [gf.get((mm, oo), 0) for mm, oo in zip(t["match_id"], t["opponent_id"])]
    t["goal_diff"] = t["goals_for"] - t["goals_against"]
    t["result"] = np.select([t["goal_diff"] > 0, t["goal_diff"] == 0], ["W", "D"], default="L")
    t["points"] = t["result"].map({"W": 3, "D": 1, "L": 0})
    t["possession_proxy_pct"] = _safe_rate(t["passes"], t["passes"] + t["passes_against"], 100)
    t["field_tilt_pct"] = _safe_rate(t["final_third_touches"],
                                     t["final_third_touches"] + t["final_third_touches_against"], 100)
    t["pass_completion_pct"] = _safe_rate(t["passes_completed"], t["passes"], 100)
    t["xg_diff"] = t["xg"] - t["xg_against"]
    start_f = formations_df[formations_df["type"] == "Starting XI"][["match_id", "team_id", "formation"]]
    t = t.merge(start_f.rename(columns={"formation": "starting_formation"}), on=["match_id", "team_id"], how="left")
    shifts = formations_df[formations_df["formation_changed"]].groupby(["match_id", "team_id"]).size()
    t["in_match_formation_changes"] = [shifts.get((mm, tt), 0) for mm, tt in zip(t["match_id"], t["team_id"])]
    if not managers.empty:
        mg = managers.drop_duplicates(["match_id", "team_id"])[["match_id", "team_id", "manager_id", "manager_name"]]
        t = t.merge(mg, on=["match_id", "team_id"], how="left")
    else:
        t["manager_id"] = np.nan
        t["manager_name"] = None
    return t.sort_values(["match_date", "match_id", "home_away"], ascending=[True, True, False]).reset_index(drop=True)


def formation_summary(team_stats: pd.DataFrame, team: str | None = None, min_matches: int = 3) -> pd.DataFrame:
    """Starting-formation usage and observed outcomes (descriptive; small samples flagged)."""
    t = team_stats if not team or team == "All" else team_stats[team_stats["team_name"] == team]
    if t.empty or "starting_formation" not in t:
        return pd.DataFrame()
    g = t.groupby("starting_formation")
    out = pd.DataFrame({
        "matches": g.size(), "wins": g["result"].apply(lambda s: (s == "W").sum()),
        "draws": g["result"].apply(lambda s: (s == "D").sum()), "losses": g["result"].apply(lambda s: (s == "L").sum()),
        "points_per_match": g["points"].mean(), "xg_for": g["xg"].mean(), "xg_against": g["xg_against"].mean(),
        "goals_for": g["goals_for"].mean(), "goals_against": g["goals_against"].mean(),
        "possession_proxy_pct": g["possession_proxy_pct"].mean(), "field_tilt_pct": g["field_tilt_pct"].mean(),
    }).round(2).reset_index().sort_values("matches", ascending=False)
    out["sample_warning"] = np.where(out["matches"] < min_matches, f"n<{min_matches}: descriptive only", "")
    return out.reset_index(drop=True)


def team_style_summary(team_stats: pd.DataFrame) -> pd.DataFrame:
    """Per-team average style indicators across analysed matches."""
    cols = ["goals_for", "goals_against", "xg", "xg_against", "shots", "shots_against", "possession_proxy_pct",
            "field_tilt_pct", "pass_completion_pct", "progressive_passes", "pressures", "ppda", "set_piece_shots",
            "points"]
    g = team_stats.groupby("team_name")
    out = g[cols].mean().round(2)
    out.insert(0, "matches", g.size())
    return out.sort_values("matches", ascending=False).reset_index()


def match_timeline_events(events: pd.DataFrame, goals: pd.DataFrame, match_id: Any) -> pd.DataFrame:
    """Goals, cards, substitutions and formation changes for one match."""
    ev = events[events["match_id"] == match_id]
    rows = []
    for _, g in goals[goals["match_id"] == match_id].iterrows():
        team = ev.loc[ev["team_id"] == g["scoring_team_id"], "team_name"]
        rows.append({"elapsed_min": g["elapsed_min"], "minute": g["minute"], "period": g["period"],
                     "team_name": team.iloc[0] if len(team) else g["scoring_team_id"], "event": "Goal",
                     "detail": f"{g['player_name']} ({g['goal_type']})"})
    cards = ev[ev["card"].notna()]
    for _, c in cards.iterrows():
        rows.append({"elapsed_min": c["elapsed_min"], "minute": c["minute"], "period": c["period"],
                     "team_name": c["team_name"], "event": c["card"], "detail": c["player_name"]})
    for _, s in ev[ev["type"] == "Substitution"].iterrows():
        rows.append({"elapsed_min": s["elapsed_min"], "minute": s["minute"], "period": s["period"],
                     "team_name": s["team_name"], "event": "Substitution",
                     "detail": f"OFF {s['player_name']} / ON {s['sub_replacement_name']} ({s['outcome']})"})
    for _, f in ev[ev["type"] == "Tactical Shift"].iterrows():
        rows.append({"elapsed_min": f["elapsed_min"], "minute": f["minute"], "period": f["period"],
                     "team_name": f["team_name"], "event": "Tactical shift", "detail": f"formation {f['formation']}"})
    return pd.DataFrame(rows).sort_values("elapsed_min").reset_index(drop=True) if rows else pd.DataFrame(
        columns=["elapsed_min", "minute", "period", "team_name", "event", "detail"])


def cumulative_xg(flags: pd.DataFrame, match_id: Any) -> pd.DataFrame:
    s = flags[(flags["match_id"] == match_id) & (flags["type"] == "Shot")][
        ["team_name", "elapsed_min", "minute", "shot_xg", "outcome", "player_name"]].copy()
    s = s.sort_values("elapsed_min")
    s["cum_xg"] = s.groupby("team_name")["shot_xg"].cumsum()
    return s


def expected_points(flags: pd.DataFrame, team_stats: pd.DataFrame, n_sims: int = 5000, seed: int = 0
                    ) -> pd.DataFrame:
    """Expected points per team-match by simulating every shot as a Bernoulli(xG) trial.

    A shot-based xPts model (periods 1-4; own goals not simulated). It summarises
    chance quality, not what "should" have happened, and assumes shots are independent.
    """
    rng = np.random.default_rng(seed)
    shots = flags[(flags["type"] == "Shot") & flags["period"].between(1, 4)]
    rows = []
    for mid, g in team_stats.groupby("match_id"):
        if len(g) != 2:
            continue
        t0, t1 = g.iloc[0], g.iloc[1]
        sim = {}
        for t in (t0, t1):
            xg = shots.loc[(shots["match_id"] == mid) & (shots["team_id"] == t["team_id"]), "shot_xg"].fillna(0)
            xg = xg.to_numpy(dtype=float)
            sim[t["team_id"]] = (rng.random((n_sims, len(xg))) < xg).sum(axis=1) if len(xg) else np.zeros(n_sims)
        for t, o in ((t0, t1), (t1, t0)):
            a, b = sim[t["team_id"]], sim[o["team_id"]]
            pw, pd_ = float((a > b).mean()), float((a == b).mean())
            rows.append({"match_id": mid, "team_id": t["team_id"], "team_name": t["team_name"],
                         "match_date": t["match_date"], "p_win": pw, "p_draw": pd_, "p_loss": 1 - pw - pd_,
                         "xpts": 3 * pw + pd_, "points": t["points"]})
    return pd.DataFrame(rows).sort_values(["match_date", "match_id"]).reset_index(drop=True)
