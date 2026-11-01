import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from football_analytics import visualizations as viz
from football_analytics.config import Config

EMPTY = pd.DataFrame()


def _is_message(fig: go.Figure) -> bool:
    return any("No data" in (a.text or "") or "not available" in (a.text or "") or "Not enough" in (a.text or "")
               or "No " in (a.text or "") for a in fig.layout.annotations)


@pytest.mark.parametrize("fn,args", [
    (viz.coverage_cards, (EMPTY,)),
    (viz.match_timeline, (EMPTY,)),
    (viz.results_overview, (EMPTY, "X")),
    (viz.team_trend, (EMPTY, "X")),
    (viz.leaderboard_chart, (EMPTY, ["xg_p90"], 0)),
    (viz.player_radar, (EMPTY, 1, ["xg_p90"])),
    (viz.comparison_scatter, (EMPTY, ["xg_p90", "shots_p90"], 0)),
    (viz.workload_bars, (EMPTY, "X")),
    (viz.role_distribution, (EMPTY, ["xg_p90"], 0)),
    (viz.formation_frequency, (EMPTY, "X")),
    (viz.formation_comparison, (EMPTY, "X")),
    (viz.xi_pitch, (EMPTY, "XI")),
    (viz.shot_map, (EMPTY, "shots")),
    (viz.pass_map, (EMPTY, "passes")),
    (viz.pass_network_chart, (EMPTY, EMPTY, "net")),
    (viz.substitution_timeline, (EMPTY, "subs")),
    (viz.sub_timing_histogram, (EMPTY, Config().sub_timing_bands)),
    (viz.subs_by_state, (EMPTY,)),
    (viz.role_flow_sankey, (EMPTY,)),
    (viz.impact_chart, (EMPTY,)),
    (viz.manager_formation_distribution, (EMPTY, "M")),
    (viz.rotation_trend, (EMPTY, "X")),
    (viz.manager_sub_profile, (EMPTY, "M", Config().sub_timing_bands)),
    (viz.correlation_heatmap, (EMPTY, ["a", "b"])),
    (viz.feature_distributions, (EMPTY, ["a"])),
    (viz.missingness_heatmap, (EMPTY,)),
    (viz.confusion_matrix_chart, (None,)),
    (viz.roc_chart, (EMPTY, 0.5)),
    (viz.calibration_chart, (EMPTY,)),
])
def test_empty_inputs_render_message(fn, args):
    fig = fn(*args)
    assert isinstance(fig, go.Figure)
    assert _is_message(fig)


def test_missing_optional_column_skips_only_that_chart():
    shots = pd.DataFrame({"x": [100.0], "y": [40.0], "outcome": ["Goal"]})   # no shot_xg column
    fig = viz.shot_map(shots, "shots")
    assert any("shot_xg" in (a.text or "") for a in fig.layout.annotations)
    ok = viz.shot_map(shots.assign(shot_xg=0.3, player_name="A", minute=10), "shots")
    assert len(ok.data) > 0


def test_filter_with_no_rows_does_not_crash():
    s = pd.DataFrame({"player_name": ["A"], "minutes_played": [50.0], "xg_p90": [0.5], "team_name": ["T"],
                      "role_family": ["Forward"], "primary_position": ["Center Forward"]})
    fig = viz.leaderboard_chart(s, ["xg_p90"], min_minutes=1000)
    assert _is_message(fig)


def test_pitch_uses_statsbomb_dimensions():
    fig = viz.draw_pitch()
    outer = fig.layout.shapes[0]
    assert (outer.x0, outer.y0, outer.x1, outer.y1) == (0, 0, 120, 80)
    assert fig.layout.yaxis.range[0] > fig.layout.yaxis.range[1]       # y axis reversed (0 = top touchline)
    assert fig.layout.yaxis.scaleanchor == "x"                          # equal aspect


def test_synthetic_banner_added():
    fig = viz.add_banner(go.Figure(), "Illustrative synthetic data")
    assert "synthetic" in fig.layout.annotations[0].text.lower()
