import numpy as np
import pandas as pd
import pytest

from football_analytics.config import Config
from football_analytics.features import (_pct_of, add_percentiles, event_flags, per90, role_fit_scores,
                                         workload_suitability)
from football_analytics.parsing import parse_events


def test_per90_basic_and_zero_minutes():
    r = per90([3, 2, 5], [270, 0, 45])
    assert r[0] == pytest.approx(1.0)
    assert np.isnan(r[1])                      # zero minutes -> NaN, never inf
    assert r[2] == pytest.approx(10.0)


def test_no_division_by_zero_warning():
    with np.errstate(all="raise"):
        per90(np.array([1.0, 0.0]), np.array([0.0, 0.0]))


def _season(rows):
    df = pd.DataFrame(rows)
    df["role_family"] = df["primary_role"].map({"CB": "Defender", "CF": "Forward", "FB": "Defender"})
    return df


def test_min_minutes_filter_and_role_group_normalisation():
    cfg = Config(min_minutes=180, min_group_size=3)
    s = _season([
        {"player_id": 1, "team_id": 1, "primary_role": "CF", "minutes_played": 900, "xg_p90": 0.6},
        {"player_id": 2, "team_id": 1, "primary_role": "CF", "minutes_played": 900, "xg_p90": 0.3},
        {"player_id": 3, "team_id": 1, "primary_role": "CF", "minutes_played": 900, "xg_p90": 0.1},
        {"player_id": 4, "team_id": 1, "primary_role": "CF", "minutes_played": 60, "xg_p90": 2.0},  # below threshold
        {"player_id": 5, "team_id": 1, "primary_role": "CB", "minutes_played": 900, "xg_p90": 0.05},
        {"player_id": 6, "team_id": 1, "primary_role": "FB", "minutes_played": 900, "xg_p90": 0.02},
    ])
    s["eligible"] = s["minutes_played"] >= cfg.min_minutes
    out = add_percentiles(s, ["xg_p90"], cfg).set_index("player_id")
    # CF group has 3 eligible players -> role-level benchmark; low-minute player excluded from the pool
    assert out.loc[1, "benchmark_level"] == "role" and out.loc[1, "benchmark_n"] == 3
    assert out.loc[1, "xg_p90_pct"] > out.loc[2, "xg_p90_pct"] > out.loc[3, "xg_p90_pct"]
    assert out.loc[4, "xg_p90_pct"] == pytest.approx(100.0)     # scored vs pool, flagged by eligibility
    # CB has only 1 eligible player -> falls back to role family (Defender, n=2), explicitly labelled
    assert out.loc[5, "benchmark_level"] == "role family" and out.loc[5, "benchmark_group"] == "Defender"
    assert bool(out.loc[5, "small_benchmark_warning"])


def test_missing_feature_handled_by_renormalising_weights():
    cfg = Config()
    s = pd.DataFrame({"player_id": [1, 2], "xg_p90_pct": [80.0, np.nan], "shots_p90_pct": [60.0, 40.0]})
    rf = role_fit_scores(s, "CF", cfg).set_index("player_id")
    w = cfg.role_metric_weights["CF"]
    assert rf.loc[1, "role_fit"] == pytest.approx((80 * w["xg_p90"] + 60 * w["shots_p90"]) /
                                                  (w["xg_p90"] + w["shots_p90"]))
    assert rf.loc[2, "role_fit"] == pytest.approx(40.0)
    assert rf.loc[2, "role_fit_completeness"] < rf.loc[1, "role_fit_completeness"]


def test_percentile_helper_ties_and_nan():
    p = _pct_of(np.array([1.0, 2.0, np.nan]), np.array([1.0, 2.0, 3.0, np.nan]))
    assert p[0] == pytest.approx(50 / 3)
    assert np.isnan(p[2])


def test_progressive_pass_and_xa_flags():
    events = [
        {"id": "s1", "index": 2, "period": 1, "minute": 3, "second": 0, "type": {"name": "Shot"},
         "team": {"id": 1}, "player": {"id": 9}, "location": [110, 40],
         "shot": {"statsbomb_xg": 0.4, "outcome": {"name": "Goal"}, "type": {"name": "Open Play"}}},
        {"id": "p1", "index": 1, "period": 1, "minute": 2, "second": 0, "type": {"name": "Pass"},
         "team": {"id": 1}, "player": {"id": 8}, "location": [60, 40],
         "pass": {"end_location": [100, 40], "goal_assist": True, "assisted_shot_id": "s1"}},
        {"id": "p2", "index": 3, "period": 1, "minute": 4, "second": 0, "type": {"name": "Pass"},
         "team": {"id": 1}, "player": {"id": 8}, "location": [60, 40], "pass": {"end_location": [55, 40]}},
    ]
    df, _ = parse_events(events, 1)
    f = event_flags(df).set_index("event_id")
    assert f.loc["p1", "progressive_passes"] == 1 and f.loc["p2", "progressive_passes"] == 0
    assert f.loc["p1", "xa"] == pytest.approx(0.4) and f.loc["p1", "assists"] == 1
    assert f.loc["s1", "goals"] == 1 and f.loc["s1", "npxg"] == pytest.approx(0.4)


def test_penalty_excluded_from_npxg_and_shootout_excluded():
    events = [
        {"id": "a", "index": 1, "period": 1, "minute": 3, "second": 0, "type": {"name": "Shot"}, "team": {"id": 1},
         "player": {"id": 9}, "shot": {"statsbomb_xg": 0.76, "outcome": {"name": "Goal"}, "type": {"name": "Penalty"}}},
        {"id": "b", "index": 2, "period": 5, "minute": 121, "second": 0, "type": {"name": "Shot"}, "team": {"id": 1},
         "player": {"id": 9}, "shot": {"statsbomb_xg": 0.76, "outcome": {"name": "Goal"}, "type": {"name": "Penalty"}}},
    ]
    df, _ = parse_events(events, 1)
    f = event_flags(df)
    assert len(f) == 1                     # period 5 (shoot-out) excluded
    assert f["npxg"].sum() == 0 and f["xg"].sum() == pytest.approx(0.76)


def test_workload_suitability_bounds():
    s = workload_suitability([0, 200, 400, np.nan], [7, 7, 2, np.nan])
    assert s[0] == 100 and 0 <= s[2] < s[1] < 100 and s[3] == 100
