"""Team and tactical intelligence: formation summaries, team style, pass networks."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


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


def pass_network(flags: pd.DataFrame, appearances: pd.DataFrame, match_id: Any, team_id: Any,
                 min_passes: int = 3) -> tuple[pd.DataFrame, pd.DataFrame, float | None]:
    """Nodes (average pass origin) and edges (completed passer->recipient counts).

    Restricted to the period before the team's first substitution so all nodes
    represent players on the pitch together. Returns (nodes, edges, cutoff_minute).
    """
    ev = flags[(flags["match_id"] == match_id) & (flags["team_id"] == team_id)]
    if ev.empty:
        return pd.DataFrame(), pd.DataFrame(), None
    subs = ev[ev["type"] == "Substitution"]["elapsed_min"]
    cutoff = float(subs.min()) if len(subs) else float(ev["elapsed_min"].max())
    p = ev[(ev["type"] == "Pass") & (ev["elapsed_min"] < cutoff) & ev["x"].notna()]
    comp = p[p["outcome"].isna() & p["pass_recipient_id"].notna()]
    nodes = (p.groupby(["player_id", "player_name"]).agg(x=("x", "mean"), y=("y", "mean"), passes=("x", "size"))
             .reset_index())
    names = appearances[(appearances["match_id"] == match_id)].set_index("player_id")["player_name"]
    nodes["display_name"] = nodes["player_id"].map(names).fillna(nodes["player_name"])
    edges = (comp.groupby(["player_id", "pass_recipient_id"]).size().rename("count").reset_index())
    edges = edges[edges["count"] >= min_passes]
    pos = nodes.set_index("player_id")[["x", "y"]]
    edges = edges[edges["player_id"].isin(pos.index) & edges["pass_recipient_id"].isin(pos.index)]
    if not edges.empty:
        edges = edges.assign(x0=edges["player_id"].map(pos["x"]), y0=edges["player_id"].map(pos["y"]),
                             x1=edges["pass_recipient_id"].map(pos["x"]), y1=edges["pass_recipient_id"].map(pos["y"]))
    return nodes, edges, cutoff


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
