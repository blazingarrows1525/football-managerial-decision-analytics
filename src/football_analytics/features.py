"""Feature engineering: event flags, player-match / season tables, per-90, percentiles,
form, workload proxies, team-match style metrics and match state.

Every metric is defined in ``METRIC_DEFINITIONS`` (numerator, denominator, unit,
source fields) and exported into the data dictionary. Project-defined metrics
(e.g. progressive pass) are approximations, labelled as such — they are not
provider-published metrics.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .config import Config, ROLE_FAMILY, role_for_position
from .parsing import SENDING_OFF_CARDS, SET_PIECE_PASS_TYPES, TACKLE_WON_OUTCOMES

GOAL_X, GOAL_Y = 120.0, 40.0
ON_BALL_TYPES = {"Pass", "Ball Receipt*", "Carry", "Shot", "Dribble", "Miscontrol", "Dispossessed", "Clearance",
                 "Interception", "Ball Recovery", "Block", "Goal Keeper", "50/50", "Shield"}
ON_TARGET = {"Goal", "Saved", "Saved To Post", "Saved to Post"}
GK_SAVE_TYPES = {"Shot Saved", "Shot Saved Off T", "Shot Saved To Post", "Penalty Saved", "Penalty Saved To Post",
                 "Save"}
GK_CLAIM_TYPES = {"Collected", "Punch", "Keeper Sweeper", "Smother"}

# name: (definition, numerator, denominator, unit, source fields)
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


# ---------------------------------------------------------------------------
# Player-match and player-season tables
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Form and workload
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Team-match style metrics
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Match state
# ---------------------------------------------------------------------------
def score_at(goals: pd.DataFrame, match_id: Any, team_id: Any, opponent_id: Any,
             elapsed: float | None = None, before_index: int | None = None) -> tuple[int, int]:
    """(team goals, opponent goals) strictly before an event index or elapsed minute."""
    g = goals[goals["match_id"] == match_id]
    if before_index is not None:
        g = g[g["index"] < before_index]
    elif elapsed is not None:
        g = g[g["elapsed_min"] < elapsed]
    return int((g["scoring_team_id"] == team_id).sum()), int((g["scoring_team_id"] == opponent_id).sum())


def state_label(goal_diff: int) -> str:
    return "leading" if goal_diff > 0 else ("trailing" if goal_diff < 0 else "drawing")


def men_on_pitch(send_offs: pd.DataFrame, match_id: Any, team_id: Any, opponent_id: Any,
                 elapsed: float | None = None, before_index: int | None = None) -> int:
    """Numerical advantage (+) / disadvantage (-) from sending-offs before the moment."""
    s = send_offs[send_offs["match_id"] == match_id]
    if before_index is not None:
        s = s[s["index"] < before_index]
    elif elapsed is not None:
        s = s[s["elapsed_min"] < elapsed]
    return int((s["team_id"] == opponent_id).sum() - (s["team_id"] == team_id).sum())


def assign_band(period: Any, minute: Any, bands: list[dict]) -> str | None:
    """Assign a (period, clock minute) to a configured analytical band."""
    for b in bands:
        if period in b["periods"] and b["min"] <= minute <= b["max"]:
            return b["label"]
    return None


def metric_dictionary() -> pd.DataFrame:
    return pd.DataFrame([{"metric": k, "definition": v[0], "numerator": v[1], "denominator": v[2], "unit": v[3],
                          "source_fields": v[4]} for k, v in METRIC_DEFINITIONS.items()])
