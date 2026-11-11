import pytest

from src.data.parsers import parse_all
from helpers import lineups, match_meta, standard_match


def _apps(builder):
    P = parse_all([match_meta(1)], {1: {"events": builder.events, "lineups": lineups()}})
    return P["appearances"].set_index("player_id"), P


def test_starter_without_substitution_plays_full_actual_time():
    b = standard_match()
    b.end()
    a, _ = _apps(b)
    # 47 min first half (incl. 2 min stoppage) + 48 min second half
    assert a.loc[101, "minutes_played"] == pytest.approx(95.0)
    assert a.loc[101, "squad_status"] == "starter"


def test_player_substituted_off_and_substitute_on():
    b = standard_match()
    b.add(2, 60, 0, "Substitution", 1, 110, "Center Forward",
          substitution={"replacement": {"id": 112, "name": "P112"}, "outcome": {"name": "Tactical"}})
    b.end()
    a, _ = _apps(b)
    assert a.loc[110, "minutes_played"] == pytest.approx(47 + 15)      # off at 60:00 in P2
    assert a.loc[112, "minutes_played"] == pytest.approx(95 - 62)
    assert a.loc[112, "squad_status"] == "used_substitute"
    assert a.loc[112, "sub_on_minute"] == 60
    # A substitute is never silently credited with 90 minutes
    assert a.loc[112, "minutes_played"] < 90


def test_unused_substitute_zero_minutes():
    b = standard_match()
    b.end()
    a, _ = _apps(b)
    assert a.loc[113, "minutes_played"] == 0
    assert a.loc[113, "minutes_flag"] == "unused_substitute"


def test_red_card_dismissal_ends_spell():
    b = standard_match()
    b.add(1, 30, 0, "Foul Committed", 2, 203, "Right Center Back", foul_committed={"card": {"name": "Red Card"}})
    b.end()
    a, _ = _apps(b)
    assert a.loc[203, "minutes_played"] == pytest.approx(30.0)
    assert bool(a.loc[203, "sent_off"])


def test_second_yellow_in_first_half_stoppage():
    b = standard_match()
    b.add(1, 46, 30, "Foul Committed", 2, 205, "Left Back", foul_committed={"card": {"name": "Second Yellow"}})
    b.end()
    a, _ = _apps(b)
    assert a.loc[205, "minutes_played"] == pytest.approx(46.5)


def test_half_time_substitution():
    b = standard_match()
    b.add(2, 45, 0, "Substitution", 1, 107, "Right Center Midfield",
          substitution={"replacement": {"id": 113, "name": "P113"}, "outcome": {"name": "Tactical"}})
    b.end()
    a, _ = _apps(b)
    assert a.loc[107, "minutes_played"] == pytest.approx(47.0)
    assert a.loc[113, "minutes_played"] == pytest.approx(48.0)


def test_extra_time_counts_periods_3_and_4():
    b = standard_match(extra_time=True)
    b.add(3, 100, 0, "Substitution", 1, 109, "Right Wing",
          substitution={"replacement": {"id": 114, "name": "P114"}, "outcome": {"name": "Tactical"}})
    b.end()
    a, P = _apps(b)
    assert a.loc[101, "minutes_played"] == pytest.approx(95 + 32)
    assert a.loc[109, "minutes_played"] == pytest.approx(95 + 10)
    assert a.loc[114, "minutes_played"] == pytest.approx(22)


def test_temporary_player_off_on_is_ignored():
    b = standard_match()
    b.add(1, 20, 0, "Player Off", 1, 104, "Left Center Back")
    b.add(1, 22, 0, "Player On", 1, 104, "Left Center Back")
    b.end()
    a, _ = _apps(b)
    assert a.loc[104, "minutes_played"] == pytest.approx(95.0)


def test_unknown_timing_flagged_when_no_starting_xi():
    b = standard_match(skip_xi_for=2)
    b.end()
    a, P = _apps(b)
    away = a[a["team_id"] == 2]
    assert away["minutes_played"].isna().all()
    assert (away["minutes_flag"] == "unknown_no_starting_xi_event").all()
    assert any("no Starting XI" in str(i) for i in P["parse_issues"]["issue"])
