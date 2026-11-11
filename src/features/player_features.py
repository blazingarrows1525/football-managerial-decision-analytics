"""Player match and season tables, per-90 rates, role percentiles and profile helpers."""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any
from typing import TYPE_CHECKING

from src.config import ROLE_FAMILY, ROLE_LABEL, role_for_position

if TYPE_CHECKING:
    from src.config import Config

METRIC_DEFINITIONS: dict[str, tuple[str, str, str, str, str]] = {
    "minutes_played": ("Actual playing time on pitch incl. stoppage (periods 1-4) from Starting XI/substitution/"
                       "sending-off events", "sum of spell lengths", "-", "minutes", "events: Starting XI, "
                       "Substitution, Foul Committed/Bad Behaviour cards, Half Start/End"),
    "goals": ("Shots with outcome Goal in periods 1-4 (shoot-out excluded)", "count", "-", "goals", "shot.outcome"),
    "npxg": ("Sum of StatsBomb xG on non-penalty shots", "sum xG", "-", "xG", "shot.statsbomb_xg, shot.type"),
    "xg": ("Sum of StatsBomb xG on all shots (periods 1-4)", "sum xG", "-", "xG", "shot.statsbomb_xg"),
    "xa": ("xG of shots assisted by the player's passes (pass.assisted_shot_id)", "sum xG", "-", "xG",
           "pass.assisted_shot_id, shot.statsbomb_xg"),
    "shots": ("Shot events (periods 1-4)", "count", "-", "shots", "type=Shot"),
    "shots_on_target": ("Shots with outcome Goal / Saved / Saved To Post", "count", "-", "shots", "shot.outcome"),
    "assists": ("Passes flagged goal_assist by StatsBomb", "count", "-", "assists", "pass.goal_assist"),
    "key_passes": ("Passes flagged shot_assist or goal_assist", "count", "-", "passes",
                   "pass.shot_assist, pass.goal_assist"),
    "passes": ("Pass attempts", "count", "-", "passes", "type=Pass"),
    "passes_completed": ("Passes with no outcome (StatsBomb: no outcome = complete)", "count", "-", "passes",
                         "pass.outcome"),
    "pass_completion_pct": ("Completed / attempted passes", "passes_completed", "passes", "%", "pass.outcome"),
    "long_pass_completion_pct": ("Completion of passes >= 30 units (yards)", "completed long", "long passes", "%",
                                 "pass.length, pass.outcome"),
    "progressive_passes": ("PROJECT DEFINITION: completed open-play pass starting outside the defending 40% "
                           "(x >= 48) and ending >=25% closer to the opponent goal centre", "count", "-", "passes",
                           "location, pass.end_location, pass.type, pass.outcome"),
    "final_third_passes": ("Completed passes from x<80 ending x>=80", "count", "-", "passes", "location, end_location"),
    "box_passes": ("Completed passes ending in the penalty area from outside it", "count", "-", "passes",
                   "location, end_location"),
    "crosses_completed": ("Completed passes flagged cross", "count", "-", "passes", "pass.cross, pass.outcome"),
    "through_balls": ("Passes with technique Through Ball", "count", "-", "passes", "pass.technique"),
    "progressive_carries": ("PROJECT DEFINITION: carry ending >=25% closer to goal centre, end x >= 48 and >=5 units "
                            "forward", "count", "-", "carries", "location, carry.end_location"),
    "carries_into_final_third": ("Carries from x<80 ending x>=80", "count", "-", "carries", "carry.end_location"),
    "carries_into_box": ("Carries ending in the penalty area from outside it", "count", "-", "carries",
                         "carry.end_location"),
    "dribbles": ("Dribble (take-on) attempts", "count", "-", "dribbles", "type=Dribble"),
    "dribbles_completed": ("Dribbles with outcome Complete", "count", "-", "dribbles", "dribble.outcome"),
    "touches": ("On-ball actions (pass, receipt, carry, shot, dribble, clearance, interception, recovery, block, ...)",
                "count", "-", "actions", "type, location"),
    "box_touches": ("On-ball actions located in the opponent penalty area", "count", "-", "actions", "location"),
    "final_third_touches": ("On-ball actions with x >= 80", "count", "-", "actions", "location"),
    "tackles": ("Duels of type Tackle", "count", "-", "tackles", "duel.type"),
    "tackles_won": ("Tackles with outcome Won / Success / Success In Play / Success Out", "count", "-", "tackles",
                    "duel.outcome"),
    "interceptions": ("Interception events", "count", "-", "actions", "type=Interception"),
    "blocks": ("Block events", "count", "-", "actions", "type=Block"),
    "clearances": ("Clearance events", "count", "-", "actions", "type=Clearance"),
    "ball_recoveries": ("Ball Recovery events without recovery_failure", "count", "-", "actions", "ball_recovery"),
    "pressures": ("Pressure events", "count", "-", "actions", "type=Pressure"),
    "counterpressures": ("Pressure events flagged counterpress", "count", "-", "actions", "counterpress"),
    "aerials_won": ("aerial_won flag on pass/shot/clearance/miscontrol", "count", "-", "duels", "*.aerial_won"),
    "aerials_lost": ("Duels of type Aerial Lost", "count", "-", "duels", "duel.type"),
    "defensive_actions": ("tackles + interceptions + blocks + clearances + ball recoveries", "sum", "-", "actions",
                          "derived"),
    "fouls_committed": ("Foul Committed events", "count", "-", "fouls", "type"),
    "fouls_won": ("Foul Won events", "count", "-", "fouls", "type"),
    "yellow_cards": ("Yellow cards (foul_committed/bad_behaviour card)", "count", "-", "cards", "card"),
    "red_cards": ("Red or second-yellow cards", "count", "-", "cards", "card"),
    "turnovers": ("Dispossessed + Miscontrol events", "count", "-", "actions", "type"),
    "gk_saves": ("Goal Keeper events whose type is a save", "count", "-", "saves", "goalkeeper.type"),
    "gk_claims": ("Goal Keeper collected / punch / sweeper / smother actions", "count", "-", "actions",
                  "goalkeeper.type"),
    "gk_goals_conceded": ("Goal Keeper events of type Goal Conceded", "count", "-", "goals", "goalkeeper.type"),
}

PER90_BASE = ["goals", "npxg", "xg", "xa", "shots", "shots_on_target", "assists", "key_passes", "passes",
              "progressive_passes", "final_third_passes", "box_passes", "crosses_completed", "through_balls",
              "progressive_carries", "carries_into_final_third", "carries_into_box", "dribbles", "dribbles_completed",
              "touches", "box_touches", "final_third_touches", "tackles", "tackles_won", "interceptions", "blocks",
              "clearances", "ball_recoveries", "pressures", "counterpressures", "aerials_won", "defensive_actions",
              "fouls_committed", "fouls_won", "turnovers", "gk_saves", "gk_claims"]

COUNT_COLS = PER90_BASE + ["passes_completed", "long_passes", "long_passes_completed", "aerials_lost",
                           "yellow_cards", "red_cards", "gk_goals_conceded"]


def player_match_stats(flags: pd.DataFrame, appearances: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """One row per player-match appearance with action counts and minutes."""
    pe = flags.dropna(subset=["player_id"])
    agg = pe.groupby(["match_id", "team_id", "player_id"])[COUNT_COLS].sum().reset_index()
    app = appearances[appearances["appeared"]].copy()
    out = app.merge(agg, on=["match_id", "team_id", "player_id"], how="left")
    out[COUNT_COLS] = out[COUNT_COLS].fillna(0)
    out = out.merge(matches[["match_id", "match_date", "home_team_id", "away_team_id", "home_team", "away_team"]],
                    on="match_id", how="left")
    out["home_away"] = np.where(out["team_id"] == out["home_team_id"], "home", "away")
    out["opponent"] = np.where(out["home_away"] == "home", out["away_team"], out["home_team"])
    return out.sort_values(["match_date", "match_id"]).reset_index(drop=True)


def _safe_rate(num, den, scale=1.0):
    num = np.asarray(num, dtype=float)
    den = np.asarray(den, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(den > 0, num / den * scale, np.nan)
    return r


def per90(count: Any, minutes: Any) -> np.ndarray:
    """count / minutes * 90, NaN when minutes <= 0 (never divides by zero)."""
    return _safe_rate(count, minutes, 90.0)


def player_season_table(pms: pd.DataFrame, appearances: pd.DataFrame, config: Config,
                        asof: pd.Timestamp | None = None, matches: pd.DataFrame | None = None) -> pd.DataFrame:
    """Season-to-date player table. ``asof`` keeps only matches strictly before that date (leakage control)."""
    p = pms.copy()
    a = appearances.copy()
    if asof is not None:
        p = p[p["match_date"] < asof]
        if matches is not None:
            ids = set(matches.loc[matches["match_date"] < asof, "match_id"])
            a = a[a["match_id"].isin(ids)]
    if p.empty:  # e.g. decision before the first analysed match: no history yet
        cols = (["team_id", "player_id", "player_name", "team_name", "minutes_played", "appearances", "starts",
                 "primary_position", "primary_role", "role_family", "last_appearance", "eligible",
                 "sample_reliability", "coverage_label", "pass_completion_pct", "long_pass_completion_pct"]
                + COUNT_COLS + [f"{c}_p90" for c in PER90_BASE])
        return pd.DataFrame(columns=list(dict.fromkeys(cols)))
    g = p.groupby(["team_id", "player_id"])
    season = g[COUNT_COLS + ["minutes_played"]].sum()
    season["appearances"] = g.size()
    season["starts"] = g["is_starter"].sum()
    season["sub_appearances"] = season["appearances"] - season["starts"]
    season["subbed_off"] = g["sub_off_minute"].apply(lambda s: s.notna().sum())
    season["player_name"] = g["player_name"].last()
    season["team_name"] = g["team_name"].last()
    season["last_appearance"] = g["match_date"].max()
    season = season.reset_index()
    unused = (a[a["squad_status"] == "unused_substitute"].groupby(["team_id", "player_id"]).size()
              .rename("unused_sub_count"))
    squad_n = a.groupby(["team_id", "player_id"]).size().rename("matchday_squads")
    season = season.merge(unused, on=["team_id", "player_id"], how="left").merge(
        squad_n, on=["team_id", "player_id"], how="left")
    season["unused_sub_count"] = season["unused_sub_count"].fillna(0).astype(int)
    # Primary position: the match position carrying the most minutes.
    pos = (p.dropna(subset=["match_position"]).groupby(["team_id", "player_id", "match_position"])["minutes_played"]
           .sum().reset_index().sort_values("minutes_played", ascending=False)
           .drop_duplicates(["team_id", "player_id"]))
    season = season.merge(pos[["team_id", "player_id", "match_position"]].rename(
        columns={"match_position": "primary_position"}), on=["team_id", "player_id"], how="left")
    season["primary_role"] = season["primary_position"].map(role_for_position)
    season["role_family"] = season["primary_role"].map(ROLE_FAMILY)
    season["starts_pct"] = _safe_rate(season["starts"], season["appearances"], 100)
    season["avg_minutes"] = _safe_rate(season["minutes_played"], season["appearances"])
    for c in PER90_BASE:
        season[f"{c}_p90"] = per90(season[c], season["minutes_played"])
    season["pass_completion_pct"] = _safe_rate(season["passes_completed"], season["passes"], 100)
    season["long_pass_completion_pct"] = _safe_rate(season["long_passes_completed"], season["long_passes"], 100)
    season["tackle_success_pct"] = _safe_rate(season["tackles_won"], season["tackles"], 100)
    season["dribble_success_pct"] = _safe_rate(season["dribbles_completed"], season["dribbles"], 100)
    season["goals_minus_xg"] = season["goals"] - season["xg"]
    season["eligible"] = season["minutes_played"] >= config.min_minutes
    season["sample_reliability"] = np.clip(season["minutes_played"] / config.reliability_full_minutes, 0, 1) * 100
    season["coverage_label"] = np.select(
        [season["minutes_played"] >= config.reliability_full_minutes, season["minutes_played"] >= config.min_minutes],
        ["high data coverage", "moderate data coverage"], default="low data coverage")
    return season.sort_values("minutes_played", ascending=False).reset_index(drop=True)


def _pct_of(values: np.ndarray, pool: np.ndarray) -> np.ndarray:
    """Percentile (0-100) of each value within a reference pool (mid-rank for ties)."""
    pool = np.sort(pool[~np.isnan(pool)])
    out = np.full(len(values), np.nan)
    if len(pool) == 0:
        return out
    ok = ~np.isnan(values)
    lo = np.searchsorted(pool, values[ok], side="left")
    hi = np.searchsorted(pool, values[ok], side="right")
    out[ok] = (lo + hi) / 2.0 / len(pool) * 100.0
    return out


def add_percentiles(season: pd.DataFrame, metrics: list[str], config: Config) -> pd.DataFrame:
    """Percentile of each metric within the player's benchmark group.

    Benchmark pool = *eligible* players (>= min_minutes). Group = primary role when
    that role has >= ``min_group_size`` eligible players, otherwise role family
    (explicitly labelled). Players below the threshold get a percentile versus the
    pool but carry a low-coverage label.
    """
    s = season.copy()
    metrics = [m for m in metrics if m in s.columns]
    if s.empty:
        for c in ["benchmark_level", "benchmark_group", "benchmark_n", "small_benchmark_warning"] + [
                f"{m}_pct" for m in metrics]:
            s[c] = pd.Series(dtype=float)
        return s
    elig = s[s["eligible"].astype(bool)]
    role_n = elig.groupby("primary_role").size()
    fam_n = elig.groupby("role_family").size()
    s["benchmark_level"] = np.where(s["primary_role"].map(role_n).fillna(0) >= config.min_group_size, "role",
                                    "role family")
    s["benchmark_group"] = np.where(s["benchmark_level"] == "role", s["primary_role"], s["role_family"])
    s["benchmark_n"] = np.where(s["benchmark_level"] == "role", s["primary_role"].map(role_n),
                                s["role_family"].map(fam_n)).astype(float)
    for m in metrics:
        col = np.full(len(s), np.nan)
        for (lvl, grp), idx in s.groupby(["benchmark_level", "benchmark_group"]).groups.items():
            key = "primary_role" if lvl == "role" else "role_family"
            pool = elig.loc[elig[key] == grp, m].to_numpy(dtype=float)
            col[s.index.get_indexer(idx)] = _pct_of(s.loc[idx, m].to_numpy(dtype=float), pool)
        s[f"{m}_pct"] = col
    s["small_benchmark_warning"] = s["benchmark_n"].fillna(0) < config.min_group_size
    return s


def role_fit_scores(season_pct: pd.DataFrame, role: str, config: Config) -> pd.DataFrame:
    """Transparent role-fit = weighted mean of the role's metric percentiles (0-100).

    Missing metrics are dropped and the weights renormalised; the share of weight
    actually available is reported as ``role_fit_completeness``.
    """
    weights = config.role_metric_weights.get(role, {})
    s = season_pct
    num = np.zeros(len(s))
    wsum = np.zeros(len(s))
    for m, w in weights.items():
        col = f"{m}_pct"
        if col not in s.columns:
            continue
        v = s[col].to_numpy(dtype=float)
        ok = ~np.isnan(v)
        num[ok] += w * v[ok]
        wsum[ok] += w
    total_w = sum(weights.values()) or 1.0
    with np.errstate(invalid="ignore", divide="ignore"):
        fit = np.where(wsum > 0, num / np.where(wsum > 0, wsum, 1), np.nan)
    return pd.DataFrame({"player_id": s["player_id"].values, "role": role, "role_fit": fit,
                         "role_fit_completeness": wsum / total_w * 100}, index=s.index)


def all_metric_columns(config: Config) -> list[str]:
    cols = set()
    for w in list(config.role_metric_weights.values()) + list(config.sub_intent_metrics.values()):
        cols.update(w.keys())
    return sorted(cols)


def recent_form(pms: pd.DataFrame, season_pct: pd.DataFrame, config: Config, asof: pd.Timestamp | None = None,
                window: int | None = None) -> pd.DataFrame:
    """Role composite over each player's last ``window`` appearances before ``asof``.

    Per-90 rates over the window are converted to percentiles against the season
    benchmark pool (eligible players), then combined with the player's role weights.
    """
    window = window or config.form_window
    p = pms if asof is None else pms[pms["match_date"] < asof]
    if p.empty:
        return pd.DataFrame(columns=["team_id", "player_id", "form_score", "form_minutes", "form_apps"])
    last = p.sort_values("match_date").groupby(["team_id", "player_id"]).tail(window)
    g = last.groupby(["team_id", "player_id"])
    rec = g[COUNT_COLS + ["minutes_played"]].sum()
    rec["form_apps"] = g.size()
    rec = rec.reset_index()
    for c in PER90_BASE:
        rec[f"{c}_p90"] = per90(rec[c], rec["minutes_played"])
    rec["pass_completion_pct"] = _safe_rate(rec["passes_completed"], rec["passes"], 100)
    rec["long_pass_completion_pct"] = _safe_rate(rec["long_passes_completed"], rec["long_passes"], 100)
    rec = rec.merge(season_pct[["team_id", "player_id", "primary_role", "role_family"]], on=["team_id", "player_id"],
                    how="left")
    elig = season_pct[season_pct["eligible"].astype(bool)]
    scores = np.full(len(rec), np.nan)
    for role, idx in rec.groupby("primary_role").groups.items():
        weights = config.role_metric_weights.get(role, {})
        fam = ROLE_FAMILY.get(role)
        pool_df = elig[elig["role_family"] == fam]
        num = np.zeros(len(idx))
        wsum = np.zeros(len(idx))
        for m, w in weights.items():
            if m not in rec.columns or m not in pool_df.columns:
                continue
            v = _pct_of(rec.loc[idx, m].to_numpy(dtype=float), pool_df[m].to_numpy(dtype=float))
            ok = ~np.isnan(v)
            num[ok] += w * v[ok]
            wsum[ok] += w
        with np.errstate(invalid="ignore", divide="ignore"):
            scores[rec.index.get_indexer(idx)] = np.where(wsum > 0, num / np.where(wsum > 0, wsum, 1), np.nan)
    rec["form_score"] = scores
    rec = rec.rename(columns={"minutes_played": "form_minutes"})
    return rec[["team_id", "player_id", "form_score", "form_minutes", "form_apps"]]


def metric_dictionary() -> pd.DataFrame:
    return pd.DataFrame([{"metric": k, "definition": v[0], "numerator": v[1], "denominator": v[2], "unit": v[3],
                          "source_fields": v[4]} for k, v in METRIC_DEFINITIONS.items()])

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
