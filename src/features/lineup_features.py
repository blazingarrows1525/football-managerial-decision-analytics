"""Minutes-based exposure (workload proxy) and starting-XI continuity features."""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any


def workload_features(appearances: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """Pre-match workload proxies for every matchday-squad row.

    All values use only matches strictly before the row's match. They describe
    minutes/rest within the analysed dataset only (other competitions are NOT
    included) and are not medical fatigue measures.
    """
    a = appearances.merge(matches[["match_id", "match_date"]], on="match_id", how="left")
    a = a.sort_values(["match_date", "match_id"])
    rows = []
    for team, ta in a.groupby("team_id"):
        team_matches = ta[["match_id", "match_date"]].drop_duplicates().sort_values("match_date").reset_index(drop=True)
        prev_match = dict(zip(team_matches["match_id"], team_matches["match_id"].shift()))
        prev_date = dict(zip(team_matches["match_id"], team_matches["match_date"].shift()))
        team_match_index = {m: i for i, m in enumerate(team_matches["match_id"])}
        hist = ta[ta["appeared"]][["player_id", "match_id", "match_date", "minutes_played", "is_starter"]]
        starters_by_match = ta[ta["is_starter"]].groupby("match_id")["player_id"].apply(set).to_dict()
        for _, r in ta.iterrows():
            d, pid, mid = r["match_date"], r["player_id"], r["match_id"]
            h = hist[(hist["player_id"] == pid) & (hist["match_date"] < d)]
            pm = prev_match.get(mid)
            consec = 0
            i = team_match_index[mid] - 1
            while i >= 0 and pid in starters_by_match.get(team_matches.loc[i, "match_id"], set()):
                consec += 1
                i -= 1
            prior_team_matches = team_match_index[mid]
            rows.append({
                "match_id": mid, "team_id": team, "player_id": pid,
                "minutes_prev_7d": h.loc[h["match_date"] >= d - pd.Timedelta(days=7), "minutes_played"].sum(),
                "minutes_prev_14d": h.loc[h["match_date"] >= d - pd.Timedelta(days=14), "minutes_played"].sum(),
                "minutes_prev_28d": h.loc[h["match_date"] >= d - pd.Timedelta(days=28), "minutes_played"].sum(),
                "rest_days": (d - h["match_date"].max()).days if len(h) else np.nan,
                "team_rest_days": (d - prev_date[mid]).days if pd.notna(prev_date.get(mid)) else np.nan,
                "started_prev_match": (pid in starters_by_match.get(pm, set())) if pm is not None and pd.notna(pm) else np.nan,
                "consecutive_starts_before": consec,
                "starts_before": int(h["is_starter"].sum()),
                "apps_before": len(h),
                "prior_team_matches": prior_team_matches,
                "start_share_before": h["is_starter"].sum() / prior_team_matches if prior_team_matches else np.nan,
                "minutes_share_before": (h["minutes_played"].sum() / (prior_team_matches * 95.0)
                                         if prior_team_matches else np.nan),
            })
    return pd.DataFrame(rows)


def workload_suitability(minutes_prev_7d: Any, rest_days: Any) -> np.ndarray:
    """0-100 proxy: penalise >180 min in the previous 7 days and < 3 rest days.

    A heuristic for rotation discussion only — NOT fatigue or injury risk.
    """
    m7 = np.nan_to_num(np.asarray(minutes_prev_7d, dtype=float), nan=0.0)
    rd = np.asarray(rest_days, dtype=float)
    score = 100 - np.clip((m7 - 180) / 90 * 40, 0, 40)
    score = score - np.where(~np.isnan(rd) & (rd < 3), 25, 0)
    return np.clip(score, 0, 100)


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
