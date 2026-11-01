import numpy as np

from football_analytics.parsing import parse_all
from football_analytics.validation import coverage_summary, quality_checks
from helpers import lineups, match_meta, standard_match


def _tables(builder, home=0, away=0):
    return parse_all([match_meta(1, home, away)], {1: {"events": builder.events, "lineups": lineups()}})


def test_clean_fixture_passes_all_checks():
    b = standard_match()
    b.end()
    res, log = quality_checks(_tables(b))
    assert (res["status"] == "PASS").all(), res[res["status"] != "PASS"]


def test_detects_out_of_range_coordinates_and_xg():
    b = standard_match()
    b.add(1, 10, 0, "Pass", 1, 102, "Right Back", location=[130.0, 40.0], **{"pass": {"end_location": [10, 10]}})
    b.add(1, 11, 0, "Shot", 1, 110, "Center Forward", location=[100, 40],
          shot={"statsbomb_xg": 1.7, "outcome": {"name": "Off T"}})
    b.end()
    res, log = quality_checks(_tables(b))
    r = res.set_index("check")
    assert r.loc["Event coordinates outside 120x80", "violations"] == 1
    assert r.loc["xG outside [0,1]", "violations"] == 1
    assert len(log) >= 2                 # flagged records are logged, not silently dropped


def test_score_reconciliation_flags_mismatch():
    b = standard_match()
    b.add(1, 10, 0, "Shot", 1, 110, "Center Forward", location=[110, 40],
          shot={"statsbomb_xg": 0.2, "outcome": {"name": "Goal"}})
    b.end()
    ok, _ = quality_checks(_tables(b, 1, 0))
    bad, log = quality_checks(_tables(b, 2, 0))
    assert ok.set_index("check").loc["Event goals != published score", "violations"] == 0
    assert bad.set_index("check").loc["Event goals != published score", "violations"] == 1
    assert log["action"].str.contains("events 1-0 vs metadata 2-0").any()


def test_own_goal_attributed_to_benefiting_team():
    b = standard_match()
    b.add(1, 20, 0, "Own Goal Against", 2, 203, "Right Center Back")
    b.add(1, 20, 0, "Own Goal For", 1)
    b.end()
    t = _tables(b, 1, 0)
    assert list(t["goals"]["scoring_team_id"]) == [1]


def test_xi_size_violation_detected():
    b = standard_match()
    xi = next(e for e in b.events if e["type"]["name"] == "Starting XI")
    xi["tactics"]["lineup"] = xi["tactics"]["lineup"][:10]
    b.end()
    res, _ = quality_checks(_tables(b))
    assert res.set_index("check").loc["Team-matches without exactly 11 starters", "violations"] == 1


def test_synthetic_bundle_quality_and_coverage(synthetic_bundle):
    q = synthetic_bundle.quality
    assert (q["status"] == "PASS").all(), q[q["status"] != "PASS"]
    cov = coverage_summary(synthetic_bundle.tables)
    assert "Attendance / weather / injuries" in set(cov["coverage measure"])
    assert np.isfinite(synthetic_bundle.season["minutes_played"]).all()
