"""Tiny hand-built StatsBomb-shaped fixtures for unit tests (test-only, not an analytical source)."""
from __future__ import annotations

from typing import Any

POS_433 = ["Goalkeeper", "Right Back", "Right Center Back", "Left Center Back", "Left Back",
           "Center Defensive Midfield", "Right Center Midfield", "Left Center Midfield", "Right Wing",
           "Center Forward", "Left Wing"]
TEAMS = {1: "Home FC", 2: "Away FC"}


class EventBuilder:
    def __init__(self) -> None:
        self.events: list[dict] = []
        self.i = 0

    def add(self, period: int, minute: int, second: int, typ: str, team: int, player: int | None = None,
            position: str | None = None, **extra: Any) -> dict:
        self.i += 1
        e: dict[str, Any] = {"id": f"e{self.i}", "index": self.i, "period": period, "minute": minute,
                             "second": second, "timestamp": "00:00:00.000", "type": {"name": typ},
                             "team": {"id": team, "name": TEAMS[team]}, "possession": self.i,
                             "possession_team": {"id": team, "name": TEAMS[team]}}
        if player is not None:
            e["player"] = {"id": player, "name": f"P{player}"}
            e["position"] = {"name": position or "Center Forward"}
        e.update(extra)
        self.events.append(e)
        return e


def starters(team: int) -> list[tuple[int, str]]:
    base = 100 * team
    return [(base + k + 1, POS_433[k]) for k in range(11)]


def standard_match(extra_time: bool = False, skip_xi_for: int | None = None) -> EventBuilder:
    """P1 0:00-47:00 (47 min), P2 45:00-93:00 (48 min) => 95 min; optional ET 2 x 16 min."""
    b = EventBuilder()
    for t in (1, 2):
        b.add(1, 0, 0, "Half Start", t)
    for t in (1, 2):
        if t == skip_xi_for:
            continue
        b.add(1, 0, 0, "Starting XI", t, tactics={"formation": 433, "lineup": [
            {"player": {"id": pid, "name": f"P{pid}"}, "position": {"name": pos}, "jersey_number": k + 1}
            for k, (pid, pos) in enumerate(starters(t))]})
    b.add(1, 5, 0, "Pass", 1, 110, "Center Forward", location=[60.0, 40.0],
          **{"pass": {"end_location": [70.0, 30.0], "recipient": {"id": 109, "name": "P109"}, "length": 14.1}})
    b.add(1, 47, 0, "Half End", 1)
    b.add(1, 47, 0, "Half End", 2)
    b.add(2, 45, 0, "Half Start", 1)
    b.add(2, 45, 0, "Half Start", 2)
    if not extra_time:
        b.end = lambda: (b.add(2, 93, 0, "Half End", 1), b.add(2, 93, 0, "Half End", 2))
    else:
        def end():
            b.add(2, 93, 0, "Half End", 1)
            b.add(2, 93, 0, "Half End", 2)
            b.add(3, 90, 0, "Half Start", 1)
            b.add(3, 90, 0, "Half Start", 2)
            b.add(3, 106, 0, "Half End", 1)
            b.add(3, 106, 0, "Half End", 2)
            b.add(4, 105, 0, "Half Start", 1)
            b.add(4, 105, 0, "Half Start", 2)
            b.add(4, 121, 0, "Half End", 1)
            b.add(4, 121, 0, "Half End", 2)
        b.end = end
    return b


def lineups(bench: dict[int, list[int]] | None = None) -> list[dict]:
    bench = bench or {1: [112, 113, 114], 2: [212, 213]}
    out = []
    for t in (1, 2):
        rows = [{"player_id": pid, "player_name": f"P{pid}", "jersey_number": k + 1, "cards": [],
                 "positions": [{"position": pos, "start_reason": "Starting XI"}]}
                for k, (pid, pos) in enumerate(starters(t))]
        rows += [{"player_id": pid, "player_name": f"P{pid}", "jersey_number": 20 + k, "cards": [], "positions": []}
                 for k, pid in enumerate(bench[t])]
        out.append({"team_id": t, "team_name": TEAMS[t], "lineup": rows})
    return out


def match_meta(match_id: int = 1, home_score: int = 0, away_score: int = 0, date: str = "2024-01-01") -> dict:
    return {"match_id": match_id, "match_date": date, "kick_off": "15:00:00.000",
            "competition": {"competition_id": 1, "competition_name": "Test League", "country_name": "X"},
            "season": {"season_id": 1, "season_name": "2024"},
            "home_team": {"home_team_id": 1, "home_team_name": TEAMS[1],
                          "managers": [{"id": 1, "name": "Coach Home"}]},
            "away_team": {"away_team_id": 2, "away_team_name": TEAMS[2],
                          "managers": [{"id": 2, "name": "Coach Away"}]},
            "home_score": home_score, "away_score": away_score}
