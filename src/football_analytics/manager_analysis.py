"""Observable managerial decision patterns (not personality or 'skill' scores).

Indicators are measured per manager-team spell from lineups, formations and
substitutions: observed tactical flexibility, rotation tendency, substitution
timing profile and game-state response profile. Every indicator is reported
with its sample size; comparisons require ``config.min_manager_matches``.
Manager identity comes from the source's match metadata (or an optional
user-supplied managers.csv) — never guessed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import Config


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


def lineup_continuity(appearances: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """Starters retained from the team's previous match IN THE DATASET (gap days reported)."""
    st = appearances[appearances["is_starter"]].merge(matches[["match_id", "match_date"]], on="match_id")
    rows = []
    for team, g in st.groupby("team_id"):
        order = g[["match_id", "match_date"]].drop_duplicates().sort_values("match_date")
        prev_set, prev_date = None, None
        for _, m in order.iterrows():
            cur = set(g.loc[g["match_id"] == m["match_id"], "player_id"])
            if prev_set is not None:
                kept = len(cur & prev_set)
                rows.append({"team_id": team, "match_id": m["match_id"], "match_date": m["match_date"],
                             "starters_retained": kept, "lineup_changes": 11 - kept,
                             "days_since_prev_dataset_match": (m["match_date"] - prev_date).days})
            prev_set, prev_date = cur, m["match_date"]
    return pd.DataFrame(rows)


def _entropy(counts: pd.Series) -> float:
    p = counts / counts.sum()
    if len(p) <= 1:
        return 0.0
    return float(-(p * np.log(p)).sum() / np.log(len(p)))


def manager_profiles(bundle: Any) -> pd.DataFrame:
    """One row per manager-team spell with observable decision indicators and sample sizes."""
    cfg: Config = bundle.config
    ts, subs = bundle.team_stats, bundle.subs
    if ts["manager_name"].isna().all():
        return pd.DataFrame()
    cont = lineup_continuity(bundle.tables["appearances"], bundle.tables["matches"])
    rows = []
    for (mgr, team), g in ts.dropna(subset=["manager_name"]).groupby(["manager_name", "team_name"]):
        ids = set(g["match_id"])
        s = subs[(subs["team_name"] == team) & subs["match_id"].isin(ids)]
        c = cont[cont["match_id"].isin(ids) & (cont["team_id"].isin(g["team_id"]))]
        fcounts = g["starting_formation"].value_counts()
        n = len(g)
        first = s.sort_values("index").groupby("match_id").first()
        rows.append({
            "manager": mgr, "team": team, "matches": n,
            "sample_status": "comparable sample" if n >= cfg.min_manager_matches
            else f"descriptive only (n<{cfg.min_manager_matches})",
            "points_per_match": round(g["points"].mean(), 2), "xg_diff_per_match": round(g["xg_diff"].mean(), 2),
            "formations_used": int(fcounts.size), "most_used_formation": fcounts.index[0] if len(fcounts) else None,
            "most_used_share_pct": round(100 * fcounts.iloc[0] / n, 1) if len(fcounts) else np.nan,
            "formation_diversity_index": round(_entropy(fcounts), 2) if len(fcounts) else np.nan,
            "in_match_formation_changes_per_match": round(g["in_match_formation_changes"].mean(), 2),
            "mean_lineup_changes": round(c["lineup_changes"].mean(), 2) if len(c) else np.nan,
            "continuity_pairs": len(c),
            "subs_per_match": round(len(s) / n, 2),
            "median_sub_minute": float(s["minute"].median()) if len(s) else np.nan,
            "median_first_sub_minute": float(first["minute"].median()) if len(first) else np.nan,
            "early_subs_pct_before_60": round(100 * (s["minute"] < 60).mean(), 1) if len(s) else np.nan,
            "late_subs_pct_75_plus": round(100 * (s["minute"] >= 75).mean(), 1) if len(s) else np.nan,
            "multi_sub_window_pct": round(100 * s["multi_sub_window"].mean(), 1) if len(s) else np.nan,
            "subs_when_trailing_pct": round(100 * (s["game_state"] == "trailing").mean(), 1) if len(s) else np.nan,
            "subs_when_leading_pct": round(100 * (s["game_state"] == "leading").mean(), 1) if len(s) else np.nan,
            "like_for_like_pct": round(100 * s["like_for_like"].mean(), 1) if len(s) else np.nan,
            "injury_subs": int((s["sub_reason"] == "Injury").sum()),
            "substitutions": len(s),
        })
    out = pd.DataFrame(rows).sort_values("matches", ascending=False).reset_index(drop=True)
    return out


def response_after_conceding(bundle: Any) -> pd.DataFrame:
    """Minutes from conceding to the team's next substitution (same match), per manager."""
    goals, subs, ts = bundle.tables["goals"], bundle.subs, bundle.team_stats
    rows = []
    for _, g in goals.iterrows():
        conceding = ts[(ts["match_id"] == g["match_id"]) & (ts["team_id"] != g["scoring_team_id"])]
        if conceding.empty:
            continue
        c = conceding.iloc[0]
        nxt = subs[(subs["match_id"] == g["match_id"]) & (subs["team_id"] == c["team_id"])
                   & (subs["elapsed_min"] > g["elapsed_min"])]
        rows.append({"manager": c.get("manager_name"), "team": c["team_name"], "match_id": g["match_id"],
                     "conceded_minute": g["minute"],
                     "minutes_to_next_sub": (nxt["elapsed_min"].min() - g["elapsed_min"]) if len(nxt) else np.nan})
    return pd.DataFrame(rows)


def pooled_reference(profiles: pd.DataFrame, focus_manager: str, cfg: Config) -> pd.DataFrame:
    """Focus manager vs the pooled small-sample managers (clearly labelled reference, not a ranking)."""
    if profiles.empty or focus_manager not in set(profiles["manager"]):
        return pd.DataFrame()
    f = profiles[profiles["manager"] == focus_manager]
    rest = profiles[profiles["manager"] != focus_manager]
    cols = ["subs_per_match", "median_sub_minute", "median_first_sub_minute", "early_subs_pct_before_60",
            "late_subs_pct_75_plus", "multi_sub_window_pct", "formation_diversity_index",
            "in_match_formation_changes_per_match"]
    weights = rest["matches"]
    pooled = {c: np.average(rest[c].dropna(), weights=weights[rest[c].notna()]) if rest[c].notna().any() else np.nan
              for c in cols}
    out = pd.DataFrame({"indicator": cols, focus_manager: f[cols].iloc[0].values,
                        f"pooled other managers (n={int(weights.sum())} matches, "
                        f"{len(rest)} managers)": [pooled[c] for c in cols]})
    return out.round(2)
