"""DEMO_SYNTHETIC data generator (StatsBomb-shaped JSON).

Produces a small fictional league so the full pipeline, charts and tests run
without network access. Team and player names are obviously fictional
("Synthetic ..."). These records are NOT real football observations and must
never be presented as such — every dashboard shows the synthetic-data banner.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import numpy as np

COMP_ID, SEASON_ID = 9999, 9999
FORMATION = 3421
XI_POSITIONS = [("Goalkeeper", 1), ("Right Center Back", 3), ("Center Back", 4), ("Left Center Back", 5),
                ("Right Wing Back", 7), ("Left Wing Back", 8), ("Right Defensive Midfield", 9),
                ("Left Defensive Midfield", 11), ("Right Attacking Midfield", 18), ("Left Attacking Midfield", 20),
                ("Center Forward", 23)]
BENCH_POSITIONS = ["Goalkeeper", "Center Back", "Right Wing Back", "Left Defensive Midfield",
                   "Left Attacking Midfield", "Center Forward", "Center Back"]
ROLE_X = {"Goalkeeper": 8, "Center Back": 28, "Right Center Back": 30, "Left Center Back": 30,
          "Right Wing Back": 55, "Left Wing Back": 55, "Right Defensive Midfield": 50, "Left Defensive Midfield": 50,
          "Right Attacking Midfield": 78, "Left Attacking Midfield": 78, "Center Forward": 92}
ROLE_Y = {"Right": 62, "Left": 18}
TEAMS = ["Synthetic Albion", "Synthetic Borough", "Synthetic City", "Synthetic Rovers"]


def _clock(minute: int, second: int) -> str:
    return f"{minute:02d}:{second:02d}"


def _ts(period: int, minute: int, second: int) -> str:
    rel = minute * 60 + second - (0 if period == 1 else 45 * 60)
    return f"00:{rel // 60:02d}:{rel % 60:02d}.000"


def _mirror(loc: Any) -> list[float]:
    """Opponent's frame: both axes flip (StatsBomb records each team attacking left -> right)."""
    return [120.0 - float(loc[0]), 80.0 - float(loc[1])]


def _squads(rng: np.random.Generator) -> dict[str, list[dict]]:
    squads, pid = {}, 900000
    for ti, team in enumerate(TEAMS):
        players = []
        for k, (pos, _) in enumerate(XI_POSITIONS + [(p, 0) for p in BENCH_POSITIONS]):
            pid += 1
            players.append({"player_id": pid, "player_name": f"Synth {team.split()[1][:3]} Player {k + 1}",
                            "position": pos, "jersey_number": k + 1, "quality": float(rng.normal(1.0, 0.15))})
        squads[team] = players
    return squads


def _gen_match(rng: np.random.Generator, match_id: int, home: str, away: str, squads: dict, team_ids: dict
               ) -> tuple[list[dict], list[dict], tuple[int, int]]:
    events: list[dict] = []
    idx = [0]
    poss = [0]

    def add(period, minute, second, typ, team, extra=None, player=None, loc=None):
        idx[0] += 1
        e = {"id": str(uuid.UUID(int=int(rng.integers(0, 2 ** 63)) << 64 | idx[0])), "index": idx[0],
             "period": period, "timestamp": _ts(period, minute, second), "minute": minute, "second": second,
             "type": {"name": typ}, "possession": poss[0], "possession_team": {"id": team_ids[team], "name": team},
             "play_pattern": {"name": "Regular Play"}, "team": {"id": team_ids[team], "name": team}, "duration": 0.0}
        if player is not None:
            e["player"] = {"id": player["player_id"], "name": player["player_name"]}
            e["position"] = {"name": player["cur_pos"]}
        if loc is not None:
            e["location"] = [round(float(loc[0]), 1), round(float(loc[1]), 1)]
        if extra:
            e.update(extra)
        events.append(e)
        return e

    on = {}
    bench = {}
    lineup_pos: dict[int, list[dict]] = {}
    for team in (home, away):
        sq = [dict(p) for p in squads[team]]
        for p in sq:
            p["cur_pos"] = p["position"]
        on[team] = sq[:11]
        bench[team] = sq[11:]
        for p in sq[:11]:
            lineup_pos[p["player_id"]] = [{"position": p["position"], "from": "00:00", "to": None, "from_period": 1,
                                           "to_period": None, "start_reason": "Starting XI",
                                           "end_reason": "Final Whistle"}]
    for team in (home, away):
        add(1, 0, 0, "Half Start", team)
    for team in (home, away):
        add(1, 0, 0, "Starting XI", team, {"tactics": {"formation": FORMATION, "lineup": [
            {"player": {"id": p["player_id"], "name": p["player_name"]}, "position": {"name": p["position"]},
             "jersey_number": p["jersey_number"]} for p in on[team]]}})
    score = {home: 0, away: 0}
    sub_plan = {t: sorted(rng.choice(np.arange(56, 89), size=int(rng.integers(3, 6)), replace=False).tolist())
                for t in (home, away)}
    red_minute = int(rng.integers(30, 85)) if rng.random() < 0.15 else None
    red_team = home if rng.random() < 0.5 else away
    stoppage = {1: int(rng.integers(1, 4)), 2: int(rng.integers(3, 7))}
    strength = {home: 1.08, away: 1.0}

    def pick(team, pos_filter=None, exclude_gk=True):
        cands = [p for p in on[team] if (not exclude_gk or p["cur_pos"] != "Goalkeeper")]
        if pos_filter:
            c2 = [p for p in cands if pos_filter(p["cur_pos"])]
            cands = c2 or cands
        w = np.array([max(p["quality"], 0.2) for p in cands])
        return cands[int(rng.choice(len(cands), p=w / w.sum()))]

    def ploc(p):
        x = ROLE_X.get(p["cur_pos"], 60) + rng.normal(0, 12)
        side = "Right" if p["cur_pos"].startswith("Right") else ("Left" if p["cur_pos"].startswith("Left") else None)
        y = (ROLE_Y[side] if side else 40) + rng.normal(0, 10)
        return np.clip([x, y], [1, 1], [119, 79])

    for period in (1, 2):
        start = 0 if period == 1 else 45
        if period == 2:
            for team in (home, away):
                add(2, 45, 0, "Half Start", team)
        for minute in range(start, start + 45 + stoppage[period]):
            for team in (home, away):
                if period == 2 and minute in sub_plan[team] and bench[team]:
                    off = pick(team)
                    same = [b for b in bench[team] if b["position"].split()[-1] == off["cur_pos"].split()[-1]]
                    inc = (same or [b for b in bench[team] if b["position"] != "Goalkeeper"] or bench[team])[0]
                    sec = int(rng.integers(0, 3))
                    add(2, minute, sec, "Substitution", team, {"substitution": {
                        "replacement": {"id": inc["player_id"], "name": inc["player_name"]},
                        "outcome": {"name": "Tactical"}}}, player=off)
                    lineup_pos[off["player_id"]][-1].update({"to": _clock(minute, sec), "to_period": 2,
                                                             "end_reason": "Substitution - Off (Tactical)"})
                    inc["cur_pos"] = off["cur_pos"]
                    lineup_pos[inc["player_id"]] = [{"position": off["cur_pos"], "from": _clock(minute, sec),
                                                     "to": None, "from_period": 2, "to_period": None,
                                                     "start_reason": "Substitution - On (Tactical)",
                                                     "end_reason": "Final Whistle"}]
                    on[team].remove(off)
                    bench[team].remove(inc)
                    on[team].append(inc)
            if red_minute == minute and len(on[red_team]) == 11:
                p = pick(red_team, lambda s: "Back" in s or "Defensive" in s)
                add(period, minute, 3, "Foul Committed", red_team, {"foul_committed": {"card": {"name": "Red Card"}}},
                    player=p, loc=ploc(p))
                lineup_pos[p["player_id"]][-1].update({"to": _clock(minute, 3), "to_period": period,
                                                       "end_reason": "Sent Off"})
                on[red_team].remove(p)
            cur_sec = 4
            for _ in range(int(rng.integers(5, 9))):
                team = home if rng.random() < 0.52 else away
                opp = away if team == home else home
                poss[0] += 1
                sec = min(59, cur_sec + int(rng.integers(0, 7)))
                cur_sec = sec
                p = pick(team)
                loc = ploc(p)
                for _k in range(int(rng.integers(1, 4))):
                    rec = pick(team)
                    end = np.clip(loc + np.array([rng.normal(8, 14), rng.normal(0, 14)]), [1, 1], [119, 79])
                    ok = rng.random() < (0.84 * min(p["quality"], 1.15))
                    pas = {"recipient": {"id": rec["player_id"], "name": rec["player_name"]},
                           "end_location": [round(float(end[0]), 1), round(float(end[1]), 1)],
                           "length": float(np.hypot(*(end - loc))), "angle": float(np.arctan2(*(end - loc)[::-1])),
                           "height": {"name": "Ground Pass"}, "body_part": {"name": "Right Foot"}}
                    if not ok:
                        pas["outcome"] = {"name": "Incomplete"}
                    if end[0] > 102 and rng.random() < 0.3:
                        pas["cross"] = True
                    add(period, minute, sec, "Pass", team, {"pass": pas}, player=p, loc=loc)
                    if not ok:
                        q = pick(opp)
                        add(period, minute, sec, rng.choice(["Ball Recovery", "Interception"]), opp, player=q,
                            loc=_mirror(end))
                        break
                    cend = np.clip(end + np.array([rng.normal(5, 6), rng.normal(0, 5)]), [1, 1], [119, 79])
                    add(period, minute, sec, "Carry", team, {"carry": {"end_location": [round(float(cend[0]), 1),
                                                                                         round(float(cend[1]), 1)]}},
                        player=rec, loc=end)
                    p, loc = rec, cend
                    if rng.random() < 0.25:
                        q = pick(opp)
                        add(period, minute, sec, "Pressure", opp, player=q, loc=_mirror(loc))
                    if rng.random() < 0.06:
                        q = pick(opp)
                        won = rng.random() < 0.6
                        add(period, minute, sec, "Duel", opp, {"duel": {"type": {"name": "Tackle"},
                                                                        "outcome": {"name": "Won" if won else "Lost In Play"}}},
                            player=q, loc=_mirror(loc))
                    if rng.random() < 0.04:
                        q = pick(opp, lambda s: "Back" in s)
                        add(period, minute, sec, "Clearance", opp, {"clearance": {"aerial_won": bool(rng.random() < .5)}},
                            player=q, loc=_mirror(loc))
                if rng.random() < 0.035 * strength[team]:
                    shooter = pick(team, lambda s: "Forward" in s or "Attacking" in s)
                    sl = np.array([rng.uniform(96, 115), rng.uniform(25, 55)])
                    xg = float(np.clip(rng.beta(1.3, 9) * shooter["quality"], 0.01, 0.95))
                    r = rng.random()
                    outcome = "Goal" if r < xg else ("Saved" if r < xg + 0.3 else rng.choice(["Off T", "Blocked"]))
                    add(period, minute, sec, "Shot", team, {"shot": {
                        "statsbomb_xg": xg, "end_location": [120.0, round(float(rng.uniform(34, 46)), 1), 1.0],
                        "outcome": {"name": outcome}, "type": {"name": "Open Play"},
                        "body_part": {"name": "Right Foot"}, "technique": {"name": "Normal"}}},
                        player=shooter, loc=sl)
                    if outcome == "Goal":
                        score[team] += 1
                    elif outcome == "Saved":
                        gk = next((g for g in on[opp] if g["cur_pos"] == "Goalkeeper"), None)
                        if gk:
                            add(period, minute, sec, "Goal Keeper", opp, {"goalkeeper": {"type": {"name": "Shot Saved"}}},
                                player=gk, loc=[4, 40])
                if rng.random() < 0.02:
                    q = pick(opp)
                    card = {"card": {"name": "Yellow Card"}} if rng.random() < 0.3 else {}
                    add(period, minute, sec, "Foul Committed", opp, {"foul_committed": card} if card else None,
                        player=q, loc=_mirror(loc))
        end_min = start + 45 + stoppage[period]
        for team in (home, away):
            add(period, end_min, 0, "Half End", team)

    lineups = []
    for team in (home, away):
        rows = []
        for p in squads[team]:
            rows.append({"player_id": p["player_id"], "player_name": p["player_name"], "player_nickname": None,
                         "jersey_number": p["jersey_number"], "country": {"id": 0, "name": "Synthetic"},
                         "cards": [], "positions": lineup_pos.get(p["player_id"], [])})
        lineups.append({"team_id": team_ids[team], "team_name": team, "lineup": rows})
    return events, lineups, (score[home], score[away])


def write_synthetic_dataset(root: Path, seed: int = 42, rounds: int = 2) -> dict[str, Any]:
    """Write competitions.json, matches, events and lineups for a fictional 4-team double round robin."""
    rng = np.random.default_rng(seed)
    root = Path(root)
    for sub in ("matches", "events", "lineups"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    team_ids = {t: 99000 + i for i, t in enumerate(TEAMS)}
    squads = _squads(rng)
    fixtures = []
    for r in range(rounds):
        for i, h in enumerate(TEAMS):
            for j, a in enumerate(TEAMS):
                if i < j:
                    fixtures.append((h, a) if r == 0 else (a, h))
    matches = []
    date = np.datetime64("2030-08-10")
    for k, (h, a) in enumerate(fixtures):
        mid = 99000000 + k
        ev, lu, (hs, as_) = _gen_match(rng, mid, h, a, squads, team_ids)
        (root / "events" / f"{mid}.json").write_text(json.dumps(ev), encoding="utf-8")
        (root / "lineups" / f"{mid}.json").write_text(json.dumps(lu), encoding="utf-8")
        md = str(date + np.timedelta64(7 * (k // 2) + (k % 2) * 3, "D"))
        matches.append({
            "match_id": mid, "match_date": md, "kick_off": "15:00:00.000",
            "competition": {"competition_id": COMP_ID, "country_name": "Synthetic", "competition_name": "Synthetic League"},
            "season": {"season_id": SEASON_ID, "season_name": "2030/2031"},
            "home_team": {"home_team_id": team_ids[h], "home_team_name": h,
                          "managers": [{"id": 990 + TEAMS.index(h), "name": f"Synthetic Coach {TEAMS.index(h) + 1}",
                                        "nickname": None, "country": {"name": "Synthetic"}}]},
            "away_team": {"away_team_id": team_ids[a], "away_team_name": a,
                          "managers": [{"id": 990 + TEAMS.index(a), "name": f"Synthetic Coach {TEAMS.index(a) + 1}",
                                        "nickname": None, "country": {"name": "Synthetic"}}]},
            "home_score": hs, "away_score": as_, "match_status": "available", "match_week": k // 2 + 1,
            "competition_stage": {"name": "Regular Season"}, "stadium": None, "referee": None,
            "metadata": {"data_version": "synthetic"}})
    (root / "matches" / str(COMP_ID)).mkdir(parents=True, exist_ok=True)
    (root / "matches" / str(COMP_ID) / f"{SEASON_ID}.json").write_text(json.dumps(matches), encoding="utf-8")
    comps = [{"competition_id": COMP_ID, "season_id": SEASON_ID, "country_name": "Synthetic",
              "competition_name": "Synthetic League (DEMO — not real data)", "competition_gender": "n/a",
              "competition_youth": False, "competition_international": False, "season_name": "2030/2031",
              "match_available": None, "match_available_360": None}]
    (root / "competitions.json").write_text(json.dumps(comps), encoding="utf-8")
    return {"matches": len(matches), "teams": len(TEAMS)}
