import numpy as np

from football_analytics.parsing import parse_all, parse_events, parse_lineups, substitutions
from helpers import EventBuilder, lineups, match_meta, standard_match


def test_missing_nested_keys_do_not_crash():
    b = EventBuilder()
    b.add(1, 1, 0, "Pass", 1, 101)                 # no location, no pass dict
    b.add(1, 2, 0, "Shot", 1, 110, shot={})        # empty shot dict
    b.add(1, 3, 0, "Pressure", 2)                  # no player
    df, issues = parse_events(b.events, 1)
    assert len(df) == 3 and not issues
    assert df["x"].isna().all()
    assert np.isnan(df.loc[df["type"] == "Shot", "shot_xg"].iloc[0])
    assert df.loc[df["type"] == "Pressure", "player_id"].isna().all()


def test_malformed_record_flagged_not_fatal():
    b = EventBuilder()
    b.add(1, 1, 0, "Pass", 1, 101, location=[50, 40])
    events = b.events + ["not an event", {"no_type": True}]
    df, issues = parse_events(events, 7)
    assert len(df) == 1
    assert len(issues) == 2 and all(i["action"] == "excluded" for i in issues)


def test_substitution_direction():
    b = standard_match()
    b.add(2, 60, 0, "Substitution", 1, 110, "Center Forward",
          substitution={"replacement": {"id": 112, "name": "P112"}, "outcome": {"name": "Tactical"}})
    b.end()
    df, _ = parse_events(b.events, 1)
    s = substitutions(df)
    assert s.loc[0, "player_off_id"] == 110 and s.loc[0, "player_on_id"] == 112
    assert s.loc[0, "sub_reason"] == "Tactical"


def test_ids_preserved_as_integers():
    b = standard_match()
    b.end()
    P = parse_all([match_meta(123456789)], {123456789: {"events": b.events, "lineups": lineups()}})
    ev = P["events"]
    assert set(ev["match_id"]) == {123456789}
    assert ev["player_id"].dropna().map(float).map(float.is_integer).all()
    assert 110 in set(P["appearances"]["player_id"])


def test_coordinates_not_swapped():
    b = EventBuilder()
    b.add(1, 1, 0, "Pass", 1, 101, location=[100.0, 20.0],
          **{"pass": {"end_location": [110.0, 5.0], "recipient": {"id": 102, "name": "P102"}}})
    df, _ = parse_events(b.events, 1)
    r = df.iloc[0]
    assert (r["x"], r["y"], r["end_x"], r["end_y"]) == (100.0, 20.0, 110.0, 5.0)
    assert r["coordinate_system"].startswith("statsbomb_120x80")


def test_pass_outcome_absent_means_complete_and_recipient_parsed():
    b = EventBuilder()
    b.add(1, 1, 0, "Pass", 1, 101, location=[50, 40], **{"pass": {"recipient": {"id": 102, "name": "P102"}}})
    b.add(1, 2, 0, "Pass", 1, 101, location=[50, 40], **{"pass": {"outcome": {"name": "Incomplete"}}})
    df, _ = parse_events(b.events, 1)
    assert df["outcome"].isna().iloc[0] and df["outcome"].iloc[1] == "Incomplete"
    assert df["pass_recipient_id"].iloc[0] == 102


def test_lineup_parsing_identifies_bench():
    sq = parse_lineups(lineups(), 1)
    assert len(sq) == 11 * 2 + 5
    assert (sq["lineup_n_positions"] == 0).sum() == 5
