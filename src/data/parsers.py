"""Parse raw StatsBomb JSON into canonical tables (matches, lineups, events, appearances, ...)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any

from src.config import COORDINATE_SYSTEM, ROLE_FAMILY, format_formation, role_for_position

SENDING_OFF_CARDS = {"Red Card", "Second Yellow"}

TACKLE_WON_OUTCOMES = {"Won", "Success", "Success In Play", "Success Out"}

SET_PIECE_PASS_TYPES = {"Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off"}


def _g(d: Any, *keys: str, default: Any = None) -> Any:
    """Safe nested getter: _g(e, 'pass', 'outcome', 'name')."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def _xy(loc: Any, i: int) -> float:
    if isinstance(loc, (list, tuple)) and len(loc) > i and loc[i] is not None:
        try:
            return float(loc[i])
        except (TypeError, ValueError):
            return np.nan
    return np.nan


def parse_matches(matches_raw: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (matches, match_managers). Absent fields stay missing, never invented."""
    rows, mgr_rows = [], []
    for m in matches_raw:
        home, away = m.get("home_team", {}), m.get("away_team", {})
        rows.append({
            "match_id": int(m["match_id"]),
            "match_date": m.get("match_date"),
            "kick_off": m.get("kick_off"),
            "competition_id": _g(m, "competition", "competition_id"),
            "competition_name": _g(m, "competition", "competition_name"),
            "country_name": _g(m, "competition", "country_name"),
            "season_id": _g(m, "season", "season_id"),
            "season_name": _g(m, "season", "season_name"),
            "match_week": m.get("match_week"),
            "competition_stage": _g(m, "competition_stage", "name"),
            "home_team_id": home.get("home_team_id"),
            "home_team": home.get("home_team_name"),
            "away_team_id": away.get("away_team_id"),
            "away_team": away.get("away_team_name"),
            "home_score": m.get("home_score"),
            "away_score": m.get("away_score"),
            "stadium": _g(m, "stadium", "name"),
            "referee": _g(m, "referee", "name"),
            "match_status": m.get("match_status"),
            "data_version": _g(m, "metadata", "data_version"),
            "xy_fidelity_version": _g(m, "metadata", "xy_fidelity_version"),
            "shot_fidelity_version": _g(m, "metadata", "shot_fidelity_version"),
        })
        for side, team in (("home", home), ("away", away)):
            for mg in team.get("managers") or []:
                mgr_rows.append({
                    "match_id": int(m["match_id"]),
                    "team_id": team.get(f"{side}_team_id"),
                    "team_name": team.get(f"{side}_team_name"),
                    "manager_id": mg.get("id"),
                    "manager_name": mg.get("nickname") or mg.get("name"),
                    "manager_full_name": mg.get("name"),
                    "manager_country": _g(mg, "country", "name"),
                    "manager_source": "StatsBomb matches.json",
                })
    matches = pd.DataFrame(rows)
    if not matches.empty:
        matches["match_date"] = pd.to_datetime(matches["match_date"], errors="coerce")
        matches = matches.sort_values(["match_date", "match_id"]).reset_index(drop=True)
    managers = pd.DataFrame(mgr_rows, columns=["match_id", "team_id", "team_name", "manager_id", "manager_name",
                                                "manager_full_name", "manager_country", "manager_source"])
    return matches, managers


def parse_lineups(lineups_raw: list[dict] | None, match_id: int) -> pd.DataFrame:
    """Matchday squad rows (starters + bench) from a lineup file."""
    rows = []
    for team in lineups_raw or []:
        for p in team.get("lineup") or []:
            positions = p.get("positions") or []
            first_sub_pos = next((q.get("position") for q in positions
                                  if str(q.get("start_reason", "")).startswith("Substitution - On")), None)
            cards = p.get("cards") or []
            rows.append({
                "match_id": int(match_id),
                "team_id": team.get("team_id"),
                "team_name": team.get("team_name"),
                "player_id": p.get("player_id"),
                "player_name": p.get("player_nickname") or p.get("player_name"),
                "player_full_name": p.get("player_name"),
                "jersey_number": p.get("jersey_number"),
                "nationality": _g(p, "country", "name"),
                "lineup_n_positions": len(positions),
                "lineup_first_position": positions[0].get("position") if positions else None,
                "lineup_sub_on_position": first_sub_pos,
                "lineup_started": any(q.get("start_reason") == "Starting XI" for q in positions),
                "lineup_yellow_cards": sum(c.get("card_type") == "Yellow Card" for c in cards),
                "lineup_sending_offs": sum(c.get("card_type") in SENDING_OFF_CARDS for c in cards),
            })
    return pd.DataFrame(rows)


def _flatten_event(e: dict, match_id: int) -> dict[str, Any]:
    t = _g(e, "type", "name")
    loc = e.get("location")
    row: dict[str, Any] = {
        "event_id": e.get("id"),
        "match_id": int(match_id),
        "index": e.get("index"),
        "period": e.get("period"),
        "minute": e.get("minute"),
        "second": e.get("second"),
        "timestamp": e.get("timestamp"),
        "type": t,
        "team_id": _g(e, "team", "id"),
        "team_name": _g(e, "team", "name"),
        "player_id": _g(e, "player", "id"),
        "player_name": _g(e, "player", "name"),
        "position_name": _g(e, "position", "name"),
        "possession": e.get("possession"),
        "possession_team_id": _g(e, "possession_team", "id"),
        "play_pattern": _g(e, "play_pattern", "name"),
        "x": _xy(loc, 0), "y": _xy(loc, 1),
        "end_x": np.nan, "end_y": np.nan,
        "duration": e.get("duration"),
        "under_pressure": bool(e.get("under_pressure", False)),
        "counterpress": bool(e.get("counterpress", False)),
        "outcome": None,
        "pass_recipient_id": None, "pass_recipient_name": None, "pass_length": np.nan, "pass_angle": np.nan,
        "pass_height": None, "pass_type": None, "pass_technique": None, "pass_body_part": None,
        "pass_cross": False, "pass_switch": False, "pass_through_ball": False,
        "pass_shot_assist": False, "pass_goal_assist": False, "pass_assisted_shot_id": None,
        "shot_xg": np.nan, "shot_type": None, "shot_body_part": None, "shot_technique": None,
        "shot_end_z": np.nan, "shot_key_pass_id": None,
        "duel_type": None, "aerial_won": False, "card": None,
        "goalkeeper_type": None,
        "sub_replacement_id": None, "sub_replacement_name": None,
        "formation": None,
        "tactics_lineup": None,
    }
    if t == "Pass":
        p = e.get("pass", {})
        end = p.get("end_location")
        row.update({
            "end_x": _xy(end, 0), "end_y": _xy(end, 1),
            "outcome": _g(p, "outcome", "name"),
            "pass_recipient_id": _g(p, "recipient", "id"), "pass_recipient_name": _g(p, "recipient", "name"),
            "pass_length": p.get("length", np.nan), "pass_angle": p.get("angle", np.nan),
            "pass_height": _g(p, "height", "name"), "pass_type": _g(p, "type", "name"),
            "pass_technique": _g(p, "technique", "name"), "pass_body_part": _g(p, "body_part", "name"),
            "pass_cross": bool(p.get("cross", False)), "pass_switch": bool(p.get("switch", False)),
            "pass_through_ball": bool(p.get("through_ball", False)) or _g(p, "technique", "name") == "Through Ball",
            "pass_shot_assist": bool(p.get("shot_assist", False)),
            "pass_goal_assist": bool(p.get("goal_assist", False)),
            "pass_assisted_shot_id": p.get("assisted_shot_id"),
            "aerial_won": bool(p.get("aerial_won", False)),
        })
    elif t == "Shot":
        s = e.get("shot", {})
        end = s.get("end_location")
        row.update({
            "end_x": _xy(end, 0), "end_y": _xy(end, 1), "shot_end_z": _xy(end, 2),
            "outcome": _g(s, "outcome", "name"),
            "shot_xg": s.get("statsbomb_xg", np.nan),
            "shot_type": _g(s, "type", "name"), "shot_body_part": _g(s, "body_part", "name"),
            "shot_technique": _g(s, "technique", "name"), "shot_key_pass_id": s.get("key_pass_id"),
            "aerial_won": bool(s.get("aerial_won", False)),
        })
    elif t == "Carry":
        end = _g(e, "carry", "end_location")
        row.update({"end_x": _xy(end, 0), "end_y": _xy(end, 1)})
    elif t == "Dribble":
        row["outcome"] = _g(e, "dribble", "outcome", "name")
    elif t == "Duel":
        row["duel_type"] = _g(e, "duel", "type", "name")
        row["outcome"] = _g(e, "duel", "outcome", "name")
    elif t == "Interception":
        row["outcome"] = _g(e, "interception", "outcome", "name")
    elif t == "Clearance":
        row["aerial_won"] = bool(_g(e, "clearance", "aerial_won", default=False))
    elif t == "Miscontrol":
        row["aerial_won"] = bool(_g(e, "miscontrol", "aerial_won", default=False))
    elif t == "Ball Recovery":
        row["outcome"] = "Failed" if _g(e, "ball_recovery", "recovery_failure", default=False) else "Success"
    elif t == "Goal Keeper":
        row["goalkeeper_type"] = _g(e, "goalkeeper", "type", "name")
        row["outcome"] = _g(e, "goalkeeper", "outcome", "name")
    elif t == "Foul Committed":
        row["card"] = _g(e, "foul_committed", "card", "name")
    elif t == "Bad Behaviour":
        row["card"] = _g(e, "bad_behaviour", "card", "name")
    elif t == "Substitution":
        row["sub_replacement_id"] = _g(e, "substitution", "replacement", "id")
        row["sub_replacement_name"] = _g(e, "substitution", "replacement", "name")
        row["outcome"] = _g(e, "substitution", "outcome", "name")
    elif t in ("Starting XI", "Tactical Shift"):
        row["formation"] = format_formation(_g(e, "tactics", "formation"))
        row["tactics_lineup"] = [
            {"player_id": _g(q, "player", "id"), "player_name": _g(q, "player", "name"),
             "position_name": _g(q, "position", "name"), "jersey_number": q.get("jersey_number")}
            for q in _g(e, "tactics", "lineup", default=[]) or []
        ]
    return row


def parse_events(events_raw: list[dict] | None, match_id: int) -> tuple[pd.DataFrame, list[dict]]:
    """Flatten one match's events. Malformed records are flagged, not fatal."""
    rows, issues = [], []
    for i, e in enumerate(events_raw or []):
        try:
            if not isinstance(e, dict) or "type" not in e:
                raise ValueError("record is not an event dict with a 'type'")
            rows.append(_flatten_event(e, match_id))
        except Exception as exc:  # keep going; log the record
            issues.append({"match_id": match_id, "record_position": i, "issue": f"malformed event: {exc}",
                           "action": "excluded"})
    df = pd.DataFrame(rows)
    if not df.empty:
        df["coordinate_system"] = COORDINATE_SYSTEM
    return df, issues


def period_bounds(events: pd.DataFrame) -> pd.DataFrame:
    """Start/end clock (seconds) and cumulative offset of each played period per match.

    Elapsed playing time = offset[period] + (clock - start[period]), so stoppage time
    counts and first-half stoppage does not overlap the second half. Period 5
    (penalty shoot-out) is excluded from playing time.
    """
    if events.empty:
        return pd.DataFrame(columns=["match_id", "period", "start_clock", "end_clock", "duration", "offset"])
    ev = events[events["period"].between(1, 4)].copy()
    ev["clock"] = ev["minute"] * 60 + ev["second"]
    out = []
    for mid, g in ev.groupby("match_id"):
        offset = 0.0
        for per, gp in g.groupby("period"):
            hs = gp.loc[gp["type"] == "Half Start", "clock"]
            he = gp.loc[gp["type"] == "Half End", "clock"]
            start = float(hs.min()) if len(hs) else float(gp["clock"].min())
            end = float(he.max()) if len(he) else float(gp["clock"].max())
            dur = max(end - start, 0.0)
            out.append({"match_id": mid, "period": int(per), "start_clock": start, "end_clock": end,
                        "duration": dur, "offset": offset,
                        "bounds_source": "half_start_end_events" if len(hs) and len(he) else "event_clock_range"})
            offset += dur
    return pd.DataFrame(out)


def add_elapsed(events: pd.DataFrame, bounds: pd.DataFrame) -> pd.DataFrame:
    """Add ``elapsed_min``: minutes of playing time since kick-off (period-aware)."""
    if events.empty:
        events["elapsed_min"] = pd.Series(dtype=float)
        return events
    b = bounds[["match_id", "period", "start_clock", "duration", "offset"]].rename(
        columns={"start_clock": "_p_start", "duration": "_p_dur", "offset": "_p_offset"})
    ev = events.merge(b, on=["match_id", "period"], how="left")
    clock = ev["minute"] * 60 + ev["second"]
    rel = (clock - ev["_p_start"]).clip(lower=0)
    rel = np.minimum(rel, ev["_p_dur"])
    ev["elapsed_min"] = (ev["_p_offset"] + rel) / 60.0
    # Shoot-out (period 5) and periods without bounds sit at the end of play.
    totals = bounds.groupby("match_id")["duration"].sum() / 60.0
    shoot = ev["period"] >= 5
    ev.loc[shoot, "elapsed_min"] = ev.loc[shoot, "match_id"].map(totals)
    ev = ev.drop(columns=["_p_start", "_p_dur", "_p_offset"])
    return ev.sort_values(["match_id", "index"]).reset_index(drop=True)


def match_lengths(bounds: pd.DataFrame) -> pd.Series:
    """Total playing time (minutes, periods 1-4) per match."""
    return bounds.groupby("match_id")["duration"].sum() / 60.0


def goal_timeline(events: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """One row per goal in play (periods 1-4), attributed to the scoring team."""
    cols = ["match_id", "index", "period", "minute", "elapsed_min", "scoring_team_id", "player_name", "goal_type"]
    if events.empty:
        return pd.DataFrame(columns=cols)
    ev = events[events["period"].between(1, 4)]
    shots = ev[(ev["type"] == "Shot") & (ev["outcome"] == "Goal")].copy()
    shots["scoring_team_id"] = shots["team_id"]
    shots["goal_type"] = np.where(shots["shot_type"] == "Penalty", "penalty", "open/set play")
    og_for = ev[ev["type"] == "Own Goal For"].copy()
    og_for["scoring_team_id"] = og_for["team_id"]
    og_for["goal_type"] = "own goal"
    # Fallback: only "Own Goal Against" present -> credit the opponent.
    og_against = ev[ev["type"] == "Own Goal Against"].copy()
    og_against = og_against[~og_against["match_id"].isin(og_for["match_id"])]
    if not og_against.empty:
        opp = matches.set_index("match_id")[["home_team_id", "away_team_id"]]
        og_against["scoring_team_id"] = [
            (opp.loc[m, "away_team_id"] if t == opp.loc[m, "home_team_id"] else opp.loc[m, "home_team_id"])
            for m, t in zip(og_against["match_id"], og_against["team_id"])]
        og_against["goal_type"] = "own goal"
    goals = pd.concat([shots, og_for, og_against], ignore_index=True)
    if goals.empty:
        return pd.DataFrame(columns=cols)
    return goals[cols].sort_values(["match_id", "index"]).reset_index(drop=True)


def sending_offs(events: pd.DataFrame) -> pd.DataFrame:
    cols = ["match_id", "index", "period", "minute", "elapsed_min", "team_id", "player_id", "player_name", "card"]
    if events.empty:
        return pd.DataFrame(columns=cols)
    return events[events["card"].isin(SENDING_OFF_CARDS)][cols].reset_index(drop=True)


def formations(events: pd.DataFrame) -> pd.DataFrame:
    """Starting formation and every in-match tactical shift per team."""
    cols = ["match_id", "team_id", "team_name", "index", "period", "minute", "elapsed_min", "type",
            "formation", "formation_changed"]
    if events.empty:
        return pd.DataFrame(columns=cols)
    f = events[events["type"].isin(["Starting XI", "Tactical Shift"])].copy()
    f = f.sort_values(["match_id", "team_id", "index"])
    f["prev_formation"] = f.groupby(["match_id", "team_id"])["formation"].shift()
    f["formation_changed"] = (f["type"] == "Tactical Shift") & (f["formation"] != f["prev_formation"])
    return f[cols].reset_index(drop=True)


def build_appearances(events: pd.DataFrame, squads: pd.DataFrame, bounds: pd.DataFrame
                      ) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Reconstruct on-pitch spells and minutes from Starting XI, Substitution and sending-off events.

    Returns (appearances, spells, quality_issues). Minutes are actual playing time
    including stoppage time (periods 1-4). Temporary "Player Off/On" treatment
    breaks are ignored. If a team has no Starting XI event, minutes are left
    unknown (NaN) and flagged rather than assumed.
    """
    issues: list[dict] = []
    spells: list[dict] = []
    lengths = match_lengths(bounds)
    first_pos = (events.dropna(subset=["player_id", "position_name"])
                 .sort_values("index").groupby(["match_id", "player_id"])["position_name"].first())
    mode_pos = (events.dropna(subset=["player_id", "position_name"])
                .groupby(["match_id", "player_id"])["position_name"].agg(lambda s: s.value_counts().index[0]))
    squad_idx = squads.set_index(["match_id", "player_id"]) if not squads.empty else None
    teams_with_xi: set = set()

    for mid, g in events.groupby("match_id"):
        end_min = float(lengths.get(mid, np.nan))
        g = g.sort_values("index")
        for _, xi in g[g["type"] == "Starting XI"].iterrows():
            team = xi["team_id"]
            teams_with_xi.add((mid, team))
            on: dict[Any, dict] = {}
            appeared: set = set()
            for q in xi["tactics_lineup"] or []:
                on[q["player_id"]] = {"start": 0.0, "position": q["position_name"], "start_reason": "starting_xi",
                                      "player_name": q["player_name"], "on_minute": 0, "on_period": 1}
                appeared.add(q["player_id"])
            if len(on) != 11:
                issues.append({"match_id": mid, "team_id": team, "issue": f"Starting XI has {len(on)} players",
                               "action": "flagged"})
            team_ev = g[(g["team_id"] == team) & ((g["type"] == "Substitution") | g["card"].isin(SENDING_OFF_CARDS))]
            for _, e in team_ev.iterrows():
                if e["period"] >= 5:
                    continue
                pid = e["player_id"]
                if e["type"] == "Substitution":
                    if pid in on:
                        s = on.pop(pid)
                        spells.append({**s, "match_id": mid, "team_id": team, "player_id": pid, "end": e["elapsed_min"],
                                       "end_reason": f"substituted ({e['outcome'] or 'unspecified'})",
                                       "off_minute": e["minute"], "off_period": e["period"]})
                    else:
                        issues.append({"match_id": mid, "team_id": team, "player_id": pid,
                                       "issue": "substituted-off player not on pitch in reconstructed timeline",
                                       "action": "flagged; replacement still added"})
                    rep = e["sub_replacement_id"]
                    if rep is None or (isinstance(rep, float) and np.isnan(rep)):
                        issues.append({"match_id": mid, "team_id": team, "issue": "substitution without replacement id",
                                       "action": "flagged"})
                        continue
                    if rep in appeared:
                        issues.append({"match_id": mid, "team_id": team, "player_id": rep,
                                       "issue": "replacement had already appeared", "action": "flagged; ignored"})
                        continue
                    pos = None
                    if squad_idx is not None and (mid, rep) in squad_idx.index:
                        pos = squad_idx.loc[(mid, rep), "lineup_sub_on_position"]
                    pos = pos or first_pos.get((mid, rep)) or e["position_name"]
                    on[rep] = {"start": e["elapsed_min"], "position": pos, "start_reason": "substitute",
                               "player_name": e["sub_replacement_name"], "on_minute": e["minute"],
                               "on_period": e["period"]}
                    appeared.add(rep)
                else:  # sending off
                    if pid in on:
                        s = on.pop(pid)
                        spells.append({**s, "match_id": mid, "team_id": team, "player_id": pid, "end": e["elapsed_min"],
                                       "end_reason": f"sent off ({e['card']})",
                                       "off_minute": e["minute"], "off_period": e["period"]})
            for pid, s in on.items():
                spells.append({**s, "match_id": mid, "team_id": team, "player_id": pid, "end": end_min,
                               "end_reason": "final whistle", "off_minute": None, "off_period": None})

    sp = pd.DataFrame(spells, columns=["match_id", "team_id", "player_id", "player_name", "position", "start", "end",
                                       "start_reason", "end_reason", "on_minute", "on_period", "off_minute",
                                       "off_period"])
    if not sp.empty:
        sp["minutes"] = (sp["end"] - sp["start"]).clip(lower=0)
        if (sp["end"] < sp["start"]).any():
            issues.append({"issue": f"{int((sp['end'] < sp['start']).sum())} spells end before they start",
                           "action": "minutes clipped at 0 and flagged"})

    # Aggregate spells to one appearance row per player-match.
    agg = (sp.groupby(["match_id", "team_id", "player_id"])
           .agg(minutes_played=("minutes", "sum"), on_elapsed=("start", "min"), off_elapsed=("end", "max"),
                start_reason=("start_reason", "first"), entry_position=("position", "first"),
                end_reason=("end_reason", "last"), sub_on_minute=("on_minute", "first"),
                sub_off_minute=("off_minute", "last"), n_spells=("start", "size"))
           .reset_index()) if not sp.empty else pd.DataFrame(
        columns=["match_id", "team_id", "player_id", "minutes_played", "on_elapsed", "off_elapsed", "start_reason",
                 "entry_position", "end_reason", "sub_on_minute", "sub_off_minute", "n_spells"])
    agg["appeared"] = True
    agg["is_starter"] = agg["start_reason"] == "starting_xi"
    agg.loc[agg["is_starter"], "sub_on_minute"] = np.nan
    agg["sent_off"] = agg["end_reason"].astype(str).str.startswith("sent off")
    agg["minutes_flag"] = "derived_from_events"

    # Merge in the full matchday squad (unused substitutes get 0 minutes).
    if not squads.empty:
        base = squads[["match_id", "team_id", "team_name", "player_id", "player_name", "jersey_number",
                       "nationality", "lineup_n_positions", "lineup_started", "lineup_yellow_cards"]]
        app = base.merge(agg, on=["match_id", "team_id", "player_id"], how="outer", indicator=True)
        missing_from_squad = app["_merge"] == "right_only"
        if missing_from_squad.any():
            issues.append({"issue": f"{int(missing_from_squad.sum())} event-timeline players absent from lineup file",
                           "action": "kept; squad fields missing"})
        mismatch = (app["_merge"] == "left_only") & (app["lineup_n_positions"] > 0)
        for _, r in app[mismatch].iterrows():
            issues.append({"match_id": r["match_id"], "team_id": r["team_id"], "player_id": r["player_id"],
                           "issue": "lineup file shows positions but player absent from event timeline",
                           "action": "flagged; minutes unknown"})
        app = app.drop(columns="_merge")
        app["appeared"] = app["appeared"].astype("boolean").fillna(False).astype(bool)
        app["is_starter"] = app["is_starter"].astype("boolean").fillna(False).astype(bool)
        app["sent_off"] = app["sent_off"].astype("boolean").fillna(False).astype(bool)
        unused = ~app["appeared"]
        app.loc[unused, "minutes_played"] = 0.0
        app.loc[unused, "minutes_flag"] = "unused_substitute"
        app.loc[mismatch.values, "minutes_played"] = np.nan
        app.loc[mismatch.values, "minutes_flag"] = "unknown_lineup_event_mismatch"
    else:
        app = agg

    # Teams with no Starting XI event: minutes cannot be derived.
    no_xi = [(m, t) for m, t in app[["match_id", "team_id"]].drop_duplicates().itertuples(index=False)
             if (m, t) not in teams_with_xi]
    for m, t in no_xi:
        sel = (app["match_id"] == m) & (app["team_id"] == t)
        app.loc[sel, "minutes_played"] = np.nan
        app.loc[sel, "minutes_flag"] = "unknown_no_starting_xi_event"
        issues.append({"match_id": m, "team_id": t, "issue": "no Starting XI event", "action": "minutes unknown"})

    app["squad_status"] = np.select([app["is_starter"], app["appeared"]], ["starter", "used_substitute"],
                                    default="unused_substitute")
    app["match_position"] = [mode_pos.get((m, p)) for m, p in zip(app["match_id"], app["player_id"])]
    app["match_position"] = app["match_position"].fillna(app.get("entry_position"))
    app["match_role"] = app["match_position"].map(role_for_position)
    if "player_name" in app.columns and not sp.empty:
        names = sp.drop_duplicates(["match_id", "player_id"]).set_index(["match_id", "player_id"])["player_name"]
        fill = pd.Series([names.get((m, p)) for m, p in zip(app["match_id"], app["player_id"])], index=app.index)
        app["player_name"] = app["player_name"].fillna(fill)
    return app.reset_index(drop=True), sp, issues


def substitutions(events: pd.DataFrame) -> pd.DataFrame:
    """Raw substitution events (direction: ``player`` leaves, ``replacement`` enters)."""
    cols = ["match_id", "event_id", "index", "period", "minute", "second", "elapsed_min", "team_id", "team_name",
            "player_off_id", "player_off_name", "player_on_id", "player_on_name", "off_position", "sub_reason"]
    if events.empty:
        return pd.DataFrame(columns=cols)
    s = events[events["type"] == "Substitution"].rename(columns={
        "player_id": "player_off_id", "player_name": "player_off_name", "sub_replacement_id": "player_on_id",
        "sub_replacement_name": "player_on_name", "position_name": "off_position", "outcome": "sub_reason"})
    return s[[c for c in cols if c in s.columns]].reset_index(drop=True)


def role_family(role: str | None) -> str | None:
    return ROLE_FAMILY.get(role) if isinstance(role, str) else None


def parse_all(matches_raw: list[dict], files: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """Run every parser and return canonical tables plus a parse-issue log."""
    matches, managers = parse_matches(matches_raw)
    ev_frames, sq_frames, issues = [], [], []
    for mid, rec in files.items():
        if rec.get("events") is None:
            issues.append({"match_id": mid, "issue": "events file unavailable", "action": "match excluded"})
            continue
        df, iss = parse_events(rec["events"], mid)
        issues.extend(iss)
        ev_frames.append(df)
        if rec.get("lineups") is None:
            issues.append({"match_id": mid, "issue": "lineups file unavailable", "action": "bench unknown"})
        else:
            sq_frames.append(parse_lineups(rec["lineups"], mid))
    events = pd.concat(ev_frames, ignore_index=True) if ev_frames else pd.DataFrame()
    squads = pd.concat(sq_frames, ignore_index=True) if sq_frames else pd.DataFrame()
    bounds = period_bounds(events)
    events = add_elapsed(events, bounds)
    parsed_ids = set(events["match_id"].unique()) if not events.empty else set()
    matches["parsed"] = matches["match_id"].isin(parsed_ids)
    appearances, spells, app_issues = build_appearances(events, squads, bounds)
    issues.extend(app_issues)
    return {
        "matches": matches, "managers": managers, "events": events, "squads": squads,
        "period_bounds": bounds, "appearances": appearances, "spells": spells,
        "substitutions_raw": substitutions(events), "goals": goal_timeline(events, matches),
        "sending_offs": sending_offs(events), "formations": formations(events),
        "parse_issues": pd.DataFrame(issues),
    }
