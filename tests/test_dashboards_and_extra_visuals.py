import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from football_analytics import advanced_visuals as av
from football_analytics import dashboards as db
from football_analytics import reporting
from football_analytics.config import Config
from football_analytics.tactical_analysis import expected_points

EMPTY = pd.DataFrame()
BANDS = Config().sub_timing_bands


def _is_message(fig: go.Figure) -> bool:
    return any(a.text and ("No " in a.text or "not available" in a.text or "Need" in a.text)
               for a in fig.layout.annotations)


@pytest.mark.parametrize("fn,args", [
    (av.action_heatmap, (EMPTY, "t")),
    (av.rotation_matrix, (EMPTY, EMPTY, "X")),
    (av.lineup_similarity, (EMPTY, EMPTY, "X")),
    (av.squad_percentile_heatmap, (EMPTY, "X", ["xg_p90"], 0)),
    (av.minutes_sunburst, (EMPTY, "X")),
    (av.match_momentum, (EMPTY, EMPTY, 1)),
    (av.phase_profile, (EMPTY, EMPTY, EMPTY, "X", Config().match_phases)),
    (av.dominance_scatter, (EMPTY, "X")),
    (av.xg_distribution, (EMPTY, "X", [])),
    (av.team_style_radar, (EMPTY, "X")),
    (av.pass_direction_rose, (EMPTY, "t")),
    (av.subs_team_band_heatmap, (EMPTY, BANDS)),
    (db.season_dashboard, (EMPTY, EMPTY, "X")),
    (db.player_dashboard, (EMPTY, EMPTY, EMPTY, 1, Config())),
    (db.match_dashboard, (EMPTY, EMPTY, EMPTY, 1)),
    (db.substitution_dashboard, (EMPTY, "X", BANDS)),
])
def test_new_visuals_empty_states(fn, args):
    fig = fn(*args)
    assert isinstance(fig, go.Figure) and _is_message(fig)


def test_heatmap_shares_sum_to_100():
    ev = pd.DataFrame({"x": [10, 10, 100, 110.0], "y": [10, 12, 70, 40.0]})
    layer = av.heatmap_layer(ev, (12, 8))
    assert np.nansum(layer.z) == pytest.approx(100.0)
    assert np.nansum(layer.customdata) == 4


def test_pass_rose_forward_is_zero_degrees():
    p = pd.DataFrame({"x": [50.0] * 3, "y": [40.0] * 3, "end_x": [70.0, 70.0, 30.0], "end_y": [40.0, 40.0, 40.0],
                      "outcome": [None, "Incomplete", None]})
    fig = av.pass_direction_rose(p, "rose", sectors=4)
    r = list(fig.data[0].r)
    assert r[0] == 2 and r[2] == 1                      # forward sector 0°, backward sector 180°
    assert fig.data[0].customdata[0] == pytest.approx(50.0)


def test_expected_points_are_probabilities(synthetic_bundle):
    b = synthetic_bundle
    xp = expected_points(b.flags, b.team_stats, n_sims=2000, seed=1)
    assert len(xp) == len(b.team_stats)
    probs = xp[["p_win", "p_draw", "p_loss"]]
    assert probs.ge(0).all().all() and np.allclose(probs.sum(axis=1), 1)
    assert xp["xpts"].between(0, 3).all()
    # the two sides of a match: p_win(A) == p_loss(B)
    m = xp.groupby("match_id")
    assert np.allclose(m["p_win"].max() + m["p_win"].min() + m["p_draw"].first(), 1, atol=1e-9)


def test_dashboards_build_on_synthetic_bundle(synthetic_bundle, tmp_path):
    b = synthetic_bundle
    t = b.tables
    team = t["matches"]["home_team"].iloc[0]
    p = b.season_pct.sort_values("minutes_played").iloc[-1]
    xp = expected_points(b.flags, b.team_stats, n_sims=500)
    figs = {
        "season": db.season_dashboard(b.team_stats, xp, team, banner="SYN"),
        "player": db.player_dashboard(b.season_pct, b.pms, b.flags, p["player_id"], b.config),
        "match": db.match_dashboard(b.flags, t["goals"], t["matches"], t["matches"]["match_id"].iloc[0]),
        "subs": db.substitution_dashboard(b.subs, team, b.config.sub_timing_bands),
        "rotation": av.rotation_matrix(t["appearances"], t["matches"], team),
        "similarity": av.lineup_similarity(t["appearances"], t["matches"], team),
        "phase": av.phase_profile(b.flags, t["goals"], b.team_stats, team, b.config.match_phases),
        "style": av.team_style_radar(b.team_stats, team),
    }
    for name, fig in figs.items():
        assert not _is_message(fig), name
        assert len(fig.data) >= 1, name
    page = reporting.write_dashboard_html([(k, "d", f) for k, f in figs.items()], tmp_path / "d.html", "Demo",
                                          banner="Illustrative synthetic data")
    html = page.read_text(encoding="utf-8")
    assert html.count('class="fig"') == len(figs) and "Illustrative synthetic data" in html
    assert html.count("cdn.plot.ly") == 1                  # plotly.js loaded once
