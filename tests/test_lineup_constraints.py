import numpy as np
import pandas as pd
import pytest

from football_analytics.config import Config
from football_analytics.lineup_optimizer import DecisionContext, optimize_xi

ROLES_POS = [("GK", "Goalkeeper"), ("GK", "Goalkeeper"), ("CB", "Right Center Back"), ("CB", "Center Back"),
             ("CB", "Left Center Back"), ("CB", "Center Back"), ("FB", "Right Back"), ("FB", "Left Back"),
             ("DM", "Center Defensive Midfield"), ("CM", "Right Center Midfield"), ("CM", "Left Center Midfield"),
             ("CM", "Center Midfield"), ("W", "Right Wing"), ("W", "Left Wing"), ("CF", "Center Forward"),
             ("CF", "Center Forward")]


def make_ctx(roles_pos=ROLES_POS, minutes=900.0):
    cfg = Config()
    rng = np.random.default_rng(0)
    n = len(roles_pos)
    cand = pd.DataFrame({
        "player_id": np.arange(1, n + 1), "player_name": [f"P{i}" for i in range(1, n + 1)],
        "primary_role": [r for r, _ in roles_pos], "primary_position": [p for _, p in roles_pos],
        "minutes_played": minutes, "sample_reliability": 100.0, "coverage_label": "high data coverage",
        "form_score": rng.uniform(30, 80, n), "workload_suitability": 100.0, "lineup_continuity": 0.0})
    metrics = sorted({m for w in cfg.role_metric_weights.values() for m in w})
    sp = pd.DataFrame({"player_id": cand["player_id"], "team_id": 1})
    for m in metrics:
        sp[f"{m}_pct"] = rng.uniform(0, 100, n)
    ctx = DecisionContext(team_id=1, team_name="T", asof=pd.Timestamp("2024-01-01"), candidates=cand,
                          season_pct=sp, previous_starters=set(), pool_description="test")
    return ctx, cfg


@pytest.mark.parametrize("formation", list(Config().formation_templates))
def test_exactly_11_unique_players_one_gk_all_slots(formation):
    ctx, cfg = make_ctx()
    r = optimize_xi(ctx, formation, cfg)
    assert len(r.lineup) == 11
    assert r.lineup["player_id"].is_unique
    assert set(r.lineup["slot"]) == {s["slot"] for s in cfg.formation_templates[formation]}
    assert (r.lineup["slot_role"] == "GK").sum() == 1
    gk = r.lineup.loc[r.lineup["slot_role"] == "GK", "primary_role"].iloc[0]
    assert gk == "GK"
    assert (r.lineup["compatibility"] > 0).all()


def test_unavailable_players_excluded():
    ctx, cfg = make_ctx()
    first = optimize_xi(ctx, "4-3-3", cfg)
    out = list(first.lineup["player_id"].iloc[:3])
    r = optimize_xi(ctx, "4-3-3", cfg, unavailable=out)
    assert not set(out) & set(r.lineup["player_id"])
    assert any("Marked unavailable" in x for x in r.omitted["reason"])


def test_insufficient_depth_warns_instead_of_fabricating():
    roles = [rp for rp in ROLES_POS if rp[0] != "GK"]           # no goalkeeper available
    ctx, cfg = make_ctx(roles)
    r = optimize_xi(ctx, "4-3-3", cfg)
    assert "GK" not in set(r.lineup["slot"])
    assert len(r.lineup) == 10
    assert any("Insufficient depth" in w and "GK" in w for w in r.warnings)


def test_deterministic_for_same_input():
    ctx, cfg = make_ctx()
    a = optimize_xi(ctx, "4-2-3-1", cfg).lineup
    b = optimize_xi(ctx, "4-2-3-1", cfg).lineup
    pd.testing.assert_frame_equal(a, b)


def test_players_without_pre_decision_data_not_selected():
    ctx, cfg = make_ctx()
    ctx.season_pct.loc[ctx.season_pct["player_id"] == 15, [c for c in ctx.season_pct if c.endswith("_pct")]] = np.nan
    r = optimize_xi(ctx, "4-3-3", cfg)
    assert 15 not in set(r.lineup["player_id"])


def test_forced_what_if_pins_player():
    ctx, cfg = make_ctx()
    base = optimize_xi(ctx, "4-3-3", cfg)
    bench_cf = [p for p in (15, 16) if p not in set(base.lineup["player_id"])][0]
    r = optimize_xi(ctx, "4-3-3", cfg, forced={"ST": bench_cf})
    assert r.lineup.set_index("slot").loc["ST", "player_id"] == bench_cf
    assert r.total_score <= base.total_score + 1e-9          # optimum cannot improve when constrained
