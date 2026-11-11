"""Like-for-like player comparison: similarity search, role-fit matrix and comparison tables."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.config import ROLE_LABEL, Config
from src.features.player_features import label, role_fit_scores

DEFAULT_PROFILE_METRICS = ["xg_p90", "xa_p90", "key_passes_p90", "progressive_passes_p90",
                           "progressive_carries_p90", "dribbles_completed_p90", "box_touches_p90", "pressures_p90",
                           "tackles_won_p90", "interceptions_p90", "clearances_p90", "aerials_won_p90",
                           "ball_recoveries_p90", "pass_completion_pct"]


def profile_matrix(season_pct: pd.DataFrame, metrics: list[str], min_minutes: float, include_gk: bool = False
                   ) -> tuple[pd.DataFrame, np.ndarray]:
    """Eligible players and their z-standardised metric matrix (rows with a missing metric are dropped)."""
    d = season_pct[season_pct["minutes_played"] >= min_minutes]
    if not include_gk:
        d = d[d["primary_role"] != "GK"]
    d = d.dropna(subset=metrics).reset_index(drop=True)
    x = d[metrics].to_numpy(float)
    sd = x.std(axis=0)
    sd[sd == 0] = 1.0
    return d, (x - x.mean(axis=0)) / sd


def similar_players(season_pct: pd.DataFrame, player_id: Any, metrics: list[str] | None = None,
                    min_minutes: float = 180, k: int = 8, same_family: bool = True) -> pd.DataFrame:
    """Nearest neighbours of a player in standardised per-90 space (Euclidean distance on z-scores).

    Distance depends on the metric set and on the standardisation sample; it describes statistical resemblance
    in this dataset, not interchangeability on the pitch.
    """
    metrics = metrics or DEFAULT_PROFILE_METRICS
    d, z = profile_matrix(season_pct, metrics, min_minutes)
    hit = np.flatnonzero(d["player_id"].to_numpy() == player_id)
    if not len(hit):
        return pd.DataFrame()
    i = int(hit[0])
    dist = np.sqrt(((z - z[i]) ** 2).sum(axis=1))
    cos = (z @ z[i]) / (np.linalg.norm(z, axis=1) * np.linalg.norm(z[i]) + 1e-12)
    out = d[["player_id", "player_name", "team_name", "primary_role", "role_family", "minutes_played"]].copy()
    out["distance"], out["cosine_similarity"] = dist, cos
    out = out.drop(index=i)
    if same_family:
        out = out[out["role_family"] == d.loc[i, "role_family"]]
    return out.sort_values("distance").head(k).reset_index(drop=True)


def comparison_table(season_pct: pd.DataFrame, player_ids: list, metrics: list[str]) -> pd.DataFrame:
    """Side-by-side values and role-group percentiles for the selected players."""
    rows = []
    for pid in player_ids:
        r = season_pct[season_pct["player_id"] == pid]
        if r.empty:
            continue
        r = r.sort_values("minutes_played", ascending=False).iloc[0]
        for m in metrics:
            rows.append({"player": r["player_name"], "metric": label(m), "value": r.get(m, np.nan),
                         "percentile": r.get(f"{m}_pct", np.nan), "benchmark_group": r.get("benchmark_group"),
                         "benchmark_n": r.get("benchmark_n")})
    return pd.DataFrame(rows)


def role_fit_matrix(season_pct: pd.DataFrame, team: str, config: Config, min_minutes: float | None = None
                    ) -> pd.DataFrame:
    """Role-fit composite (0-100) of every squad player for every role, masked where the role is not compatible.

    The composite is the weighted mean of role-specific percentiles from ``config.role_metric_weights``; a blank
    cell means the position-compatibility table gives the player no eligibility for that role.
    """
    min_minutes = config.min_minutes if min_minutes is None else min_minutes
    squad = season_pct[(season_pct["team_name"] == team) & (season_pct["minutes_played"] >= min_minutes)]
    roles = list(config.role_metric_weights)
    mat = pd.DataFrame(index=squad["player_name"].tolist(), columns=roles, dtype=float)
    for role in roles:
        fit = role_fit_scores(season_pct, role, config)
        if fit is None or fit.empty:
            continue
        col = "role_fit" if "role_fit" in fit.columns else fit.columns[-1]
        score = fit.set_index("player_id")[col]
        for r in squad.itertuples():
            comp = config.role_compatibility.get(r.primary_role, {}).get(role, 0.0)
            mat.loc[r.player_name, role] = score.get(r.player_id, np.nan) if comp > 0 else np.nan
    mat.columns = [ROLE_LABEL.get(c, c) for c in mat.columns]
    return mat
