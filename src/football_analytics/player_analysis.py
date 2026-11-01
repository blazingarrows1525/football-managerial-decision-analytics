"""Player intelligence: profiles, role benchmarks, strengths/weaknesses, threshold sensitivity."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .config import Config, ROLE_LABEL

METRIC_LABELS: dict[str, str] = {
    "xg_p90": "xG /90", "npxg_p90": "npxG /90", "xa_p90": "xA /90", "goals_p90": "Goals /90",
    "shots_p90": "Shots /90", "key_passes_p90": "Key passes /90", "progressive_passes_p90": "Prog. passes /90",
    "progressive_carries_p90": "Prog. carries /90", "final_third_passes_p90": "Final-third passes /90",
    "box_passes_p90": "Passes into box /90", "crosses_completed_p90": "Completed crosses /90",
    "dribbles_completed_p90": "Completed dribbles /90", "box_touches_p90": "Box touches /90",
    "tackles_won_p90": "Tackles won /90", "interceptions_p90": "Interceptions /90", "clearances_p90": "Clearances /90",
    "ball_recoveries_p90": "Recoveries /90", "pressures_p90": "Pressures /90", "aerials_won_p90": "Aerials won /90",
    "pass_completion_pct": "Pass completion %", "long_pass_completion_pct": "Long-pass completion %",
    "gk_saves_p90": "Saves /90", "gk_claims_p90": "Claims & sweeps /90", "defensive_actions_p90": "Def. actions /90",
    "touches_p90": "Touches /90", "turnovers_p90": "Turnovers /90", "blocks_p90": "Blocks /90",
}


def label(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric.replace("_", " "))


def radar_metrics(role: str | None, config: Config) -> list[str]:
    """Metrics shown on a role's radar: the role-fit components."""
    return list(config.role_metric_weights.get(role or "CM", config.role_metric_weights["CM"]).keys())


def player_profile(season_pct: pd.DataFrame, player_id: Any, team_id: Any = None) -> dict[str, Any]:
    s = season_pct[season_pct["player_id"] == player_id]
    if team_id is not None:
        s = s[s["team_id"] == team_id]
    if s.empty:
        return {}
    r = s.sort_values("minutes_played", ascending=False).iloc[0]
    return {
        "player": r["player_name"], "team": r["team_name"], "primary_position": r.get("primary_position"),
        "role": ROLE_LABEL.get(r.get("primary_role"), "unknown"), "appearances": int(r["appearances"]),
        "starts": int(r["starts"]), "minutes": round(float(r["minutes_played"]), 0),
        "goals": int(r["goals"]), "xG": round(float(r["xg"]), 2), "assists": int(r["assists"]),
        "xA": round(float(r["xa"]), 2), "coverage": r["coverage_label"],
        "benchmark": f"{r.get('benchmark_group')} ({r.get('benchmark_level')}, n={int(r['benchmark_n'])})"
        if pd.notna(r.get("benchmark_n")) else "n/a",
    }


def strengths_weaknesses(season_pct: pd.DataFrame, player_id: Any, config: Config, team_id: Any = None,
                         top: int = 3) -> pd.DataFrame:
    """Highest and lowest role-relevant percentiles (observed metrics only)."""
    s = season_pct[season_pct["player_id"] == player_id]
    if team_id is not None:
        s = s[s["team_id"] == team_id]
    if s.empty:
        return pd.DataFrame(columns=["type", "metric", "value", "percentile"])
    r = s.iloc[0]
    rows = []
    for m in radar_metrics(r.get("primary_role"), config):
        pc = r.get(f"{m}_pct")
        if pd.notna(pc):
            rows.append({"metric": label(m), "value": round(float(r[m]), 2), "percentile": round(float(pc), 0)})
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["type", "metric", "value", "percentile"])
    df = df.sort_values("percentile", ascending=False)
    st = df.head(top).assign(type="relative strength")
    wk = df.tail(top).sort_values("percentile").assign(type="relative weakness")
    wk = wk[~wk["metric"].isin(st["metric"])]
    return pd.concat([st, wk])[["type", "metric", "value", "percentile"]].reset_index(drop=True)


def threshold_sensitivity(season: pd.DataFrame, metric: str, thresholds: list[float] | None = None,
                          top: int = 5) -> pd.DataFrame:
    """How the leaderboard for ``metric`` changes with the minimum-minutes threshold."""
    thresholds = thresholds or [90, 180, 270, 450, 900]
    rows = []
    for t in thresholds:
        e = season[season["minutes_played"] >= t].dropna(subset=[metric])
        lead = e.nlargest(top, metric)
        rows.append({"min_minutes": t, "eligible_players": len(e),
                     f"top_{top}": ", ".join(f"{n} ({v:.2f})" for n, v in zip(lead["player_name"], lead[metric]))})
    return pd.DataFrame(rows)


def leaderboard(season_pct: pd.DataFrame, metric: str, role_family: str | None = None, min_minutes: float = 0,
                n: int = 15, team: str | None = None) -> pd.DataFrame:
    s = season_pct[season_pct["minutes_played"] >= min_minutes]
    if role_family and role_family != "All":
        s = s[s["role_family"] == role_family]
    if team and team != "All":
        s = s[s["team_name"] == team]
    s = s.dropna(subset=[metric])
    cols = ["player_name", "team_name", "primary_position", "minutes_played", metric, f"{metric}_pct",
            "coverage_label"]
    return s.nlargest(n, metric)[[c for c in cols if c in s.columns]].reset_index(drop=True)


def rolling_form_series(pms: pd.DataFrame, player_id: Any, metrics: list[str], window: int = 5) -> pd.DataFrame:
    """Rolling per-90 over the last ``window`` appearances (chronological)."""
    p = pms[pms["player_id"] == player_id].sort_values("match_date").copy()
    if p.empty:
        return p
    base = [m.replace("_p90", "") for m in metrics if m.endswith("_p90")]
    roll_min = p["minutes_played"].rolling(window, min_periods=1).sum()
    for b in base:
        if b in p.columns:
            with np.errstate(divide="ignore", invalid="ignore"):
                p[f"roll_{b}_p90"] = np.where(roll_min > 0, p[b].rolling(window, min_periods=1).sum() / roll_min * 90,
                                              np.nan)
    p["roll_minutes"] = roll_min
    p["appearance_no"] = range(1, len(p) + 1)
    return p
