from types import SimpleNamespace


from tests.legacy_namespaces import sa
from src.config import Config
from src.data.parsers import parse_all
from helpers import lineups, match_meta, standard_match


def _bundle_with_goal_and_subs(rules=None):
    b = standard_match()
    b.add(1, 10, 0, "Shot", 1, 110, "Center Forward", location=[110, 40],
          shot={"statsbomb_xg": 0.3, "outcome": {"name": "Goal"}, "type": {"name": "Open Play"}})
    b.add(2, 60, 0, "Substitution", 2, 210, "Center Forward",
          substitution={"replacement": {"id": 212, "name": "P212"}, "outcome": {"name": "Tactical"}})
    b.add(2, 61, 0, "Substitution", 1, 109, "Right Wing",
          substitution={"replacement": {"id": 112, "name": "P112"}, "outcome": {"name": "Tactical"}})
    b.add(2, 75, 0, "Substitution", 1, 111, "Left Wing",
          substitution={"replacement": {"id": 113, "name": "P113"}, "outcome": {"name": "Injury"}})
    b.end()
    cfg = Config()
    if rules:
        cfg.sub_rules.update(rules)
    t = parse_all([match_meta(1, 1, 0)], {1: {"events": b.events, "lineups": lineups()}})
    return SimpleNamespace(config=cfg, tables=t)


def test_game_state_from_team_perspective():
    bun = _bundle_with_goal_and_subs()
    subs = sa.enrich_substitutions(bun).set_index("player_on_id")
    assert subs.loc[212, "game_state"] == "trailing" and subs.loc[212, "goal_diff"] == -1
    assert subs.loc[112, "game_state"] == "leading" and subs.loc[112, "goal_diff"] == 1
    assert subs.loc[112, "home_away"] == "home" and subs.loc[212, "home_away"] == "away"


def test_window_rules_are_configurable():
    bun = _bundle_with_goal_and_subs()
    s = sa.enrich_substitutions(bun)
    home = s[s["team_id"] == 1].sort_values("index")
    assert list(home["window_number"]) == [1, 2]                  # 14 minutes apart -> 2 windows
    bun2 = _bundle_with_goal_and_subs(rules={"window_grouping_seconds": 20 * 60, "max_substitutions": 3})
    s2 = sa.enrich_substitutions(bun2)
    home2 = s2[s2["team_id"] == 1].sort_values("index")
    assert list(home2["window_number"]) == [1, 1]
    assert list(home2["subs_remaining_after"]) == [2, 1]


def test_bench_excludes_used_and_pitch_contains_only_active():
    bun = _bundle_with_goal_and_subs()
    t = bun.tables
    # at 70' elapsed (P2 minute 70 -> 47 + 25 = 72 elapsed) team 1: 109 off, 112 on
    elapsed = 47 + 25
    pitch = sa.on_pitch_at(t["spells"], 1, 1, elapsed)
    bench = sa.bench_at(t["appearances"], t["spells"], 1, 1, elapsed)
    assert 112 in set(pitch["player_id"]) and 109 not in set(pitch["player_id"])
    assert 112 not in set(bench["player_id"]) and 109 not in set(bench["player_id"])  # replaced player cannot return
    assert set(bench["player_id"]) == {113, 114}
    assert len(pitch) == 11


def test_recommendation_respects_eligibility(synthetic_bundle):
    b = synthetic_bundle
    m = b.tables["matches"].iloc[4]
    rec = sa.recommend_substitution(b, m["match_id"], m["home_team"], 62.0)
    ctx = rec["context"]
    if rec["status"] == "ok":
        assert rec["recommended_on"]["player_id"] in set(ctx["bench"]["player_id"])
        assert rec["recommended_off"]["player_id"] in set(ctx["on_pitch"]["player_id"])
        assert "unknown" in rec["recommended_on"]["injury_status"]   # missing injury data is never 'fit'
    assert "final decision" in rec["human_note"]


def test_scenario_uses_only_pre_decision_events(synthetic_bundle):
    b = synthetic_bundle
    m = b.tables["matches"].iloc[2]
    early = sa.scenario_context(b, m["match_id"], m["home_team"], 20.0)
    late = sa.scenario_context(b, m["match_id"], m["home_team"], 80.0)
    assert early["team_live"]["passes"] <= late["team_live"]["passes"]
    goals = b.tables["goals"]
    g20 = goals[(goals["match_id"] == m["match_id"]) & (goals["elapsed_min"] < 20)]
    assert early["team_score"] + early["opponent_score"] == len(g20)
    # pre-match history excludes the match itself and later matches
    sp = early["season_pct"]
    assert (sp["last_appearance"] < m["match_date"]).all() if len(sp) else True


def test_intent_rule():
    assert sa.infer_intent(-1, 65)[0] == "attack"
    assert sa.infer_intent(1, 65)[0] == "protect"
    assert sa.infer_intent(0, 50)[0] == "balance"


def test_no_allowance_returns_status(synthetic_bundle):
    b = synthetic_bundle
    old = dict(b.config.sub_rules)
    try:
        b.config.sub_rules["max_substitutions"] = 0
        m = b.tables["matches"].iloc[0]
        rec = sa.recommend_substitution(b, m["match_id"], m["home_team"], 60.0)
        assert "No substitution allowance" in rec["status"]
    finally:
        b.config.sub_rules.clear()
        b.config.sub_rules.update(old)
