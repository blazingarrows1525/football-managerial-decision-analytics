"""Descriptive summaries used by notebooks, the dashboard and the report builder.

Every function returns plain tables or dictionaries computed from the bundle; nothing here is hard-coded.
Rates always carry their numerator and denominator so the sample behind a number is visible.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.analytics.uncertainty import bootstrap_ci
from src.features.event_features import ON_TARGET

SET_PIECE_PATTERNS = ["From Corner", "From Free Kick", "From Throw In"]
STATE_ORDER = ["leading", "drawing", "trailing"]


def team_matches(bundle: Any, team: str) -> pd.DataFrame:
    """The team's rows of ``team_stats`` in chronological order."""
    ts = bundle.team_stats
    return ts[ts["team_name"] == team].sort_values("match_date").reset_index(drop=True)


def team_id_of(bundle: Any, team: str) -> Any:
    ts = bundle.team_stats
    hit = ts.loc[ts["team_name"] == team, "team_id"]
    return hit.iloc[0] if len(hit) else None


def season_kpis(bundle: Any, team: str, match_ids: list | None = None) -> dict[str, Any]:
    """Headline numbers for a team over the selected matches (all values computed, none assumed)."""
    tm = team_matches(bundle, team)
    if match_ids is not None:
        tm = tm[tm["match_id"].isin(match_ids)]
    n = len(tm)
    if n == 0:
        return {"matches": 0}
    ev = bundle.tables["events"]
    ids = set(tm["match_id"])
    app = bundle.tables["appearances"]
    used = app[app["match_id"].isin(ids) & (app["team_name"] == team) & (app["minutes_played"] > 0)]
    res = tm["result"].value_counts()
    return {
        "matches": n, "wins": int(res.get("W", 0)), "draws": int(res.get("D", 0)), "losses": int(res.get("L", 0)),
        "points": float(tm["points"].sum()), "points_per_match": float(tm["points"].mean()),
        "goals_for": int(tm["goals_for"].sum()), "goals_against": int(tm["goals_against"].sum()),
        "xg_for": float(tm["xg"].sum()), "xg_against": float(tm["xg_against"].sum()),
        "shots_for": int(tm["shots"].sum()), "shots_against": int(tm["shots_against"].sum()),
        "events": int(ev["match_id"].isin(ids).sum()), "players_used": int(used["player_id"].nunique()),
        "first_match": tm["match_date"].min(), "last_match": tm["match_date"].max(),
        "possession_proxy_pct": float(tm["possession_proxy_pct"].mean()),
        "pass_completion_pct": float(tm["pass_completion_pct"].mean()),
    }


def concentration(values: pd.Series, top: int | None = None) -> pd.DataFrame:
    """Sorted contributions with cumulative share (Pareto table). ``values`` is indexed by label."""
    v = values.dropna()
    v = v[v > 0].sort_values(ascending=False)
    if top:
        v = v.head(top)
    total = float(values.dropna().clip(lower=0).sum())
    out = pd.DataFrame({"label": v.index.astype(str), "value": v.to_numpy(float)})
    out["share"] = out["value"] / total if total else np.nan
    out["cumulative_share"] = out["share"].cumsum()
    out["rank"] = np.arange(1, len(out) + 1)
    return out


def gini(values: Any) -> float:
    """Gini coefficient of non-negative contributions (0 = equal shares, 1 = one contributor)."""
    v = np.sort(np.asarray(values, float))
    v = v[~np.isnan(v)]
    if len(v) == 0 or v.sum() == 0:
        return float("nan")
    n = len(v)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(v) / (n * v.sum()))


def score_state_segments(bundle: Any, match_id: Any, team_id: Any) -> pd.DataFrame:
    """Continuous leading / drawing / trailing segments of one match for one team (minutes on the match clock)."""
    goals = bundle.tables["goals"]
    g = goals[goals["match_id"] == match_id].sort_values("elapsed_min")
    ev = bundle.tables["events"]
    end = float(ev.loc[ev["match_id"] == match_id, "elapsed_min"].max())
    rows, t0, diff = [], 0.0, 0
    for r in g.itertuples():
        t = float(r.elapsed_min)
        rows.append({"start": t0, "end": t, "goal_diff": diff})
        diff += 1 if r.scoring_team_id == team_id else -1
        t0 = t
    rows.append({"start": t0, "end": end, "goal_diff": diff})
    seg = pd.DataFrame(rows)
    seg["minutes"] = seg["end"] - seg["start"]
    seg["state"] = np.select([seg["goal_diff"] > 0, seg["goal_diff"] < 0], ["leading", "trailing"], "drawing")
    seg["match_id"] = match_id
    return seg[seg["minutes"] > 0].reset_index(drop=True)


def score_state_time(bundle: Any, team: str) -> pd.DataFrame:
    """Minutes spent leading, drawing and trailing in every match of the team."""
    tm = team_matches(bundle, team)
    rows = []
    for r in tm.itertuples():
        seg = score_state_segments(bundle, r.match_id, r.team_id)
        mins = seg.groupby("state")["minutes"].sum()
        rows.append({"match_id": r.match_id, "match_date": r.match_date, "opponent": r.opponent, "result": r.result,
                     **{s: float(mins.get(s, 0.0)) for s in STATE_ORDER}})
    out = pd.DataFrame(rows)
    if len(out):
        total = out[STATE_ORDER].sum(axis=1)
        for s in STATE_ORDER:
            out[f"{s}_share"] = out[s] / total
    return out


def event_score_state(bundle: Any, team: str) -> pd.Series:
    """Score state of ``team`` at the moment of each of its events (index aligned with ``bundle.flags``)."""
    fl = bundle.flags
    tid = team_id_of(bundle, team)
    state = pd.Series(index=fl.index, dtype=object)
    for mid in fl.loc[fl["team_id"] == tid, "match_id"].unique():
        seg = score_state_segments(bundle, mid, tid)
        m = (fl["match_id"] == mid) & (fl["team_id"] == tid)
        t = fl.loc[m, "elapsed_min"].to_numpy(float)
        idx = np.clip(np.searchsorted(seg["end"].to_numpy(float), t, side="left"), 0, len(seg) - 1)
        state.loc[m] = seg["state"].to_numpy()[idx]
    return state


def goals_breakdown(bundle: Any, team: str) -> pd.DataFrame:
    """Goals scored and conceded with play pattern and body part (own goals labelled as such)."""
    tid = team_id_of(bundle, team)
    ids = set(team_matches(bundle, team)["match_id"])
    gl = bundle.tables["goals"].merge(
        bundle.flags[["match_id", "index", "shot_body_part", "play_pattern", "shot_xg"]], on=["match_id", "index"],
        how="left")
    gl = gl[gl["match_id"].isin(ids)].copy()
    gl["side"] = np.where(gl["scoring_team_id"] == tid, "scored", "conceded")
    gl["how"] = np.where(gl["goal_type"] == "own goal", "Own goal", gl["play_pattern"].fillna("Other"))
    gl["body"] = np.where(gl["goal_type"] == "own goal", "Own goal", gl["shot_body_part"].fillna("Unknown"))
    gl["origin"] = np.where(gl["how"].isin(SET_PIECE_PATTERNS), "Restart-initiated possession",
                            np.where(gl["how"] == "Own goal", "Own goal", "Open-play possession"))
    return gl


def shot_origin_split(bundle: Any, team: str) -> pd.DataFrame:
    """Shots, xG and goals by how the possession started (StatsBomb ``play_pattern``), for and against."""
    tid = team_id_of(bundle, team)
    ids = set(team_matches(bundle, team)["match_id"])
    sh = bundle.flags[(bundle.flags["type"] == "Shot") & bundle.flags["match_id"].isin(ids)].copy()
    sh["side"] = np.where(sh["team_id"] == tid, "for", "against")
    sh["origin"] = np.where(sh["play_pattern"].isin(SET_PIECE_PATTERNS), "Restart-initiated", "Open play / other")
    sh["penalty"] = sh["shot_type"].eq("Penalty")
    sh.loc[sh["penalty"], "origin"] = "Penalty"
    out = (sh.groupby(["side", "origin"]).agg(shots=("event_id", "size"), xg=("shot_xg", "sum"),
                                              goals=("outcome", lambda s: int((s == "Goal").sum()))).reset_index())
    out["xg_per_shot"] = out["xg"] / out["shots"]
    return out


def goalkeeping_proxy(bundle: Any, min_on_target: int = 8) -> pd.DataFrame:
    """On-target shots faced, their pre-shot xG and goals conceded per main goalkeeper.

    Pre-shot xG is a crude reference: the open data carry no post-shot model, so this is not a goals-prevented
    measure in the strict sense.
    """
    app = bundle.tables["appearances"]
    gk_main = (app[app["match_role"] == "GK"].sort_values("minutes_played")
               .drop_duplicates(["match_id", "team_id"], keep="last")[["match_id", "team_id", "player_name"]])
    shots = bundle.flags[(bundle.flags["type"] == "Shot") & bundle.flags["outcome"].isin(list(ON_TARGET))]
    opp = bundle.team_stats[["match_id", "team_id", "opponent_id"]].rename(
        columns={"team_id": "shooting_team", "opponent_id": "gk_team"})
    ot = shots.merge(opp, left_on=["match_id", "team_id"], right_on=["match_id", "shooting_team"])
    ot = ot.merge(gk_main.rename(columns={"team_id": "gk_team", "player_name": "keeper"}), on=["match_id", "gk_team"])
    gk = ot.groupby("keeper").agg(on_target=("event_id", "size"), xg_on_target=("shot_xg", "sum"),
                                  conceded=("outcome", lambda s: int((s == "Goal").sum())))
    gk = gk[gk["on_target"] >= min_on_target].copy()
    gk["save_pct"] = 100 * (1 - gk["conceded"] / gk["on_target"])
    gk["prevented_proxy"] = gk["xg_on_target"] - gk["conceded"]
    return gk.sort_values("prevented_proxy").reset_index()


def player_consistency(bundle: Any, team: str, min_match_minutes: float = 45, min_matches: int = 10,
                       seed: int = 0) -> pd.DataFrame:
    """Match-level mean, spread and coefficient of variation of progression and chance involvement per player."""
    pm = bundle.pms[(bundle.pms["team_name"] == team) & (bundle.pms["minutes_played"] >= min_match_minutes)].copy()
    if pm.empty:
        return pd.DataFrame()
    pm["involve_p90"] = (pm["xg"] + pm["xa"]) / pm["minutes_played"] * 90
    pm["prog_p90"] = (pm["progressive_passes"] + pm["progressive_carries"]) / pm["minutes_played"] * 90
    cons = pm.groupby("player_name").agg(n=("match_id", "size"), prog_mean=("prog_p90", "mean"),
                                         prog_sd=("prog_p90", "std"), inv_mean=("involve_p90", "mean"),
                                         inv_sd=("involve_p90", "std"))
    cons = cons[cons["n"] >= min_matches].copy()
    # CV is only meaningful for a positive mean well away from zero
    cons["prog_cv"] = np.where(cons["prog_mean"] > 0.5, cons["prog_sd"] / cons["prog_mean"], np.nan)
    ci = {p: bootstrap_ci(pm.loc[pm["player_name"] == p, "involve_p90"].to_numpy(), seed=seed) for p in cons.index}
    cons["inv_lo"] = [ci[p][0] for p in cons.index]
    cons["inv_hi"] = [ci[p][1] for p in cons.index]
    return cons.reset_index()


TEAM_STYLE_SIGNS = {"xg": 1, "xg_against": -1, "shots": 1, "possession_proxy_pct": 1, "field_tilt_pct": 1,
                    "ppda": -1, "pass_completion_pct": 1, "pressures": 1}


def team_consistency(bundle: Any, team: str) -> tuple[pd.DataFrame, pd.Series]:
    """Within-season z-scores per match (sign flipped so positive = favourable) and the raw CV per metric."""
    tm = team_matches(bundle, team)
    cols = [c for c in TEAM_STYLE_SIGNS if c in tm.columns]
    z = pd.DataFrame({c: TEAM_STYLE_SIGNS[c] * (tm[c] - tm[c].mean()) / tm[c].std() for c in cols})
    z.index = [f"{d:%d %b} {str(o)[:14]} ({r})" for d, o, r in zip(tm["match_date"], tm["opponent"], tm["result"])]
    cv = (tm[cols].std() / tm[cols].mean().abs()).sort_values()
    return z, cv


def role_medians(bundle: Any, metrics: list[str]) -> pd.DataFrame:
    """Median of each metric per role family among eligible players, with the group size."""
    sp = bundle.season_pct
    elig = sp[sp["eligible"] & sp["role_family"].notna()]
    out = elig.groupby("role_family")[metrics].median()
    out.insert(0, "players", elig.groupby("role_family").size())
    return out


def zone_table(events: pd.DataFrame, nx: int = 6, ny: int = 5) -> pd.DataFrame:
    """Event counts on an ``nx`` by ``ny`` grid of the 120 x 80 pitch (rows = y bands, columns = x bands)."""
    d = events.dropna(subset=["x", "y"])
    xi = np.clip((d["x"].to_numpy(float) / 120 * nx).astype(int), 0, nx - 1)
    yi = np.clip((d["y"].to_numpy(float) / 80 * ny).astype(int), 0, ny - 1)
    grid = np.zeros((ny, nx), dtype=int)
    np.add.at(grid, (yi, xi), 1)
    return pd.DataFrame(grid, index=[f"y{j + 1}" for j in range(ny)], columns=[f"x{i + 1}" for i in range(nx)])


def squad_depth(bundle: Any, team: str) -> pd.DataFrame:
    """Minutes by player and match role for one team: who has actually covered each role."""
    app = bundle.tables["appearances"]
    d = app[(app["team_name"] == team) & (app["minutes_played"] > 0) & app["match_role"].notna()]
    out = (d.groupby(["match_role", "player_name"]).agg(minutes=("minutes_played", "sum"),
                                                        appearances=("match_id", "nunique"),
                                                        starts=("is_starter", "sum")).reset_index())
    return out.sort_values(["match_role", "minutes"], ascending=[True, False]).reset_index(drop=True)


def bench_usage(bundle: Any, team: str) -> pd.DataFrame:
    """How often each squad member was named on the bench and how often he was used from it."""
    app = bundle.tables["appearances"]
    d = app[(app["team_name"] == team) & (~app["is_starter"].astype(bool))]
    out = d.groupby("player_name").agg(bench_named=("match_id", "nunique"),
                                       used=("appeared", lambda s: int(s.astype(bool).sum())),
                                       sub_minutes=("minutes_played", "sum")).reset_index()
    out["unused"] = out["bench_named"] - out["used"]
    out["used_pct"] = 100 * out["used"] / out["bench_named"]
    return out.sort_values("bench_named", ascending=False).reset_index(drop=True)


def pairing_minutes(bundle: Any, team: str, min_minutes: float = 300) -> pd.DataFrame:
    """Shared on-pitch minutes for every pair of players, from reconstructed spells (validated non-overlapping)."""
    tid = team_id_of(bundle, team)
    sp = bundle.tables["spells"]
    sp = sp[sp["team_id"] == tid]
    tot = sp.groupby("player_name")["minutes"].sum()
    keep = tot[tot >= min_minutes].sort_values(ascending=False).index.tolist()
    mat = pd.DataFrame(0.0, index=keep, columns=keep)
    for _, g in sp[sp["player_name"].isin(keep)].groupby("match_id"):
        rows = g[["player_name", "start", "end"]].to_numpy()
        for i in range(len(rows)):
            for j in range(i, len(rows)):
                a, b = rows[i], rows[j]
                shared = max(0.0, min(a[2], b[2]) - max(a[1], b[1]))
                if shared:
                    mat.loc[a[0], b[0]] += shared
                    if a[0] != b[0]:
                        mat.loc[b[0], a[0]] += shared
    return mat


def co_start_counts(bundle: Any, team: str, min_starts: int = 5) -> pd.DataFrame:
    """How many times each pair of players started the same match."""
    app = bundle.tables["appearances"]
    st = app[(app["team_name"] == team) & app["is_starter"].astype(bool)]
    counts = st.groupby("player_name")["match_id"].nunique()
    keep = counts[counts >= min_starts].sort_values(ascending=False).index.tolist()
    piv = pd.crosstab(st["match_id"], st["player_name"]).reindex(columns=keep, fill_value=0).clip(upper=1)
    return piv.T.dot(piv)
