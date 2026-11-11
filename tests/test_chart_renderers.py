"""Every implemented renderer: valid fixture, empty and missing data, edge cases, no mutation, labels, export."""
from __future__ import annotations

import matplotlib.figure
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from src.features.event_features import EVENT_KINDS, select_events
from src.reporting import exports
from src.visualization import (audit, comparison, distribution, inference, lineup, model, passing, pitch,
                               registry, scouting, spatial, static_pitch, substitution, team)
from src.visualization.availability import check
from src.visualization.theme import SYNTHETIC_WATERMARK, finalize, wrap_title

IMPLEMENTED = [s.chart_id for s in registry.all_specs() if s.implemented]


def _title(fig) -> str:
    if isinstance(fig, go.Figure):
        return fig.layout.title.text or ""
    return " ".join(t.get_text() for t in fig.texts) + " ".join(ax.get_title(loc="left") for ax in fig.axes)


def _annotations(fig) -> str:
    return " ".join(a.text or "" for a in fig.layout.annotations) if isinstance(fig, go.Figure) else \
        " ".join(t.get_text() for t in fig.texts)


@pytest.mark.parametrize("chart_id", IMPLEMENTED)
def test_renderer_on_fixture(chart_id, synthetic_ws):
    """Each renderer returns a figure on the fixture; unavailable ones return a labelled empty state."""
    spec = registry.get(chart_id)
    status, reason = check(spec, synthetic_ws)
    fig = registry.render(chart_id, synthetic_ws)
    assert isinstance(fig, (go.Figure, matplotlib.figure.Figure)), chart_id
    if isinstance(fig, go.Figure):
        fig.to_dict()  # serialisable
        if status == registry.IMPLEMENTED_AVAILABLE:
            assert fig.layout.title.text, f"{chart_id} has no title"
        else:
            assert len(fig.data) == 0 and reason
    # synthetic fixtures must be watermarked on every figure and must not claim the real source
    assert SYNTHETIC_WATERMARK in _annotations(fig), f"{chart_id} lacks the synthetic watermark"
    assert "Synthetic test fixture" in _title(fig) or "Synthetic test fixture" in _annotations(fig)
    assert "Data: StatsBomb Open Data" not in _title(fig)
    if not isinstance(fig, go.Figure):
        plt.close(fig)


def test_rendering_does_not_mutate_the_source_tables(synthetic_ws):
    b = synthetic_ws.bundle
    frames = {"flags": b.flags, "season_pct": b.season_pct, "team_stats": b.team_stats, "subs": b.subs,
              "pms": b.pms, "appearances": b.tables["appearances"], "matches": b.tables["matches"]}

    def fingerprint():
        out = {}
        for k, df in frames.items():
            simple = df[[c for c in df.columns if df[c].dtype != object or isinstance(
                df[c].dropna().iloc[0] if df[c].notna().any() else "", (str, bool, int, float))]]
            out[k] = (df.shape, tuple(df.columns), int(pd.util.hash_pandas_object(simple, index=True).sum()))
        return out

    before = fingerprint()
    p = synthetic_ws.params()
    for cid in IMPLEMENTED:
        if check(registry.get(cid), synthetic_ws)[0] == registry.IMPLEMENTED_AVAILABLE:
            fig = registry.get(cid).renderer(synthetic_ws, p)
            if not isinstance(fig, go.Figure):
                plt.close(fig)
    assert fingerprint() == before, "a renderer modified a shared table in place"


EMPTY = pd.DataFrame()
EMPTY_CASES = [
    ("histogram", lambda: distribution.histogram(EMPTY, "xg_p90")),
    ("kde", lambda: distribution.kde(None, "xg_p90", "role_family")),
    ("ecdf", lambda: distribution.ecdf(pd.DataFrame({"xg_p90": []}), "xg_p90")),
    ("box", lambda: distribution.box_points(EMPTY, "xg_p90", "role_family")),
    ("violin", lambda: distribution.violin(EMPTY, "xg_p90")),
    ("raincloud", lambda: distribution.raincloud(EMPTY, "xg_p90")),
    ("strip", lambda: distribution.strip(EMPTY, "xg_p90")),
    ("ridgeline", lambda: distribution.ridgeline(EMPTY, "xg_p90", "role_family")),
    ("beeswarm", lambda: distribution.beeswarm(EMPTY, "xg_p90")),
    ("quantile", lambda: distribution.quantile_profile(EMPTY, "xg_p90")),
    ("qq", lambda: distribution.qq_plot(EMPTY, "xg_p90")),
    ("pareto", lambda: distribution.pareto(EMPTY, "t")),
    ("small_multiples", lambda: distribution.small_multiples(EMPTY, ["a"], "g")),
    ("bump", lambda: comparison.bump_chart(EMPTY, "t")),
    ("percentile_bars", lambda: comparison.percentile_bars(EMPTY, 1, ["xg_p90"])),
    ("event_points", lambda: spatial.event_points(EMPTY, "t")),
    ("arrow_map", lambda: spatial.arrow_map(None, "t")),
    ("density", lambda: spatial.density_contours(EMPTY, "t")),
    ("zone_grid", lambda: spatial.zone_grid(EMPTY, "t")),
    ("hull", lambda: spatial.convex_hull(EMPTY, "t")),
    ("period_split", lambda: spatial.period_split(EMPTY, "t")),
    ("pair_heatmaps", lambda: spatial.pair_heatmaps(EMPTY, None, "a", "b", "t")),
    ("lanes", lambda: spatial.progression_lanes(EMPTY, "t")),
    ("transitions", lambda: spatial.zone_transitions(EMPTY, "t")),
    ("shot_facets", lambda: spatial.shot_facets(EMPTY)),
    ("xt_surface", lambda: spatial.xt_surface(None)),
    ("sequence", lambda: spatial.sequence_animation(EMPTY, 1, 1, "t")),
    ("centroids", lambda: spatial.centroid_shape(EMPTY, "t")),
    ("freeze_frame", lambda: spatial.freeze_frame(None, None)),
    ("shot_map", lambda: pitch.shot_map(EMPTY, "t")),
    ("pass_map", lambda: pitch.pass_map(EMPTY, "t")),
    ("action_heatmap", lambda: pitch.action_heatmap(EMPTY, "t")),
    ("network", lambda: passing.network_chart(EMPTY, EMPTY, "t", "s")),
    ("centrality_bars", lambda: passing.centrality_bars(EMPTY, "T")),
    ("centrality_scatter", lambda: passing.centrality_scatter(None, "T")),
    ("network_compare", lambda: passing.network_compare(EMPTY, EMPTY, None, None, "a", "b", "t", "c")),
    ("pair_heatmap", lambda: passing.pair_heatmap(EMPTY, "t", "s")),
    ("role_matrix", lambda: passing.role_matrix(None, "t", "s")),
    ("robustness", lambda: passing.robustness_chart(EMPTY, "t", "s")),
    ("xg_diff", lambda: team.xg_diff_distribution(EMPTY, "T")),
    ("shot_volume", lambda: team.shot_volume_quality(None, "T")),
    ("state_share", lambda: team.score_state_share(EMPTY, "T")),
    ("percentile_profile", lambda: team.team_percentile_profile(EMPTY, "T")),
    ("formation_timeline", lambda: team.formation_timeline(EMPTY, "T")),
    ("origin_split", lambda: team.origin_split_chart(EMPTY, "T")),
    ("consistency", lambda: team.team_consistency_chart(EMPTY, pd.Series(dtype=float), "T")),
    ("xpts", lambda: team.xpts_chart(EMPTY, "T")),
    ("goalkeeping", lambda: team.goalkeeping_chart(EMPTY)),
    ("consistency_quadrant", lambda: scouting.consistency_quadrant(EMPTY, "T")),
    ("interval", lambda: scouting.interval_chart(EMPTY, "t", "x")),
    ("similar", lambda: scouting.similar_players_chart(EMPTY, "P")),
    ("role_fit", lambda: scouting.role_fit_heatmap(EMPTY, "T")),
    ("depth", lambda: scouting.squad_depth_chart(EMPTY, "T")),
    ("xt_bars", lambda: scouting.xt_bars(None, "T")),
    ("slot_suitability", lambda: lineup.slot_suitability(EMPTY, "4-3-3")),
    ("role_occupancy", lambda: lineup.role_occupancy(EMPTY, "T")),
    ("formation_transitions", lambda: lineup.formation_transitions(EMPTY, "T")),
    ("co_start", lambda: lineup.co_start_network(EMPTY, "T")),
    ("pairing", lambda: lineup.pairing_heatmap(None, "T")),
    ("formation_sensitivity", lambda: lineup.formation_sensitivity(EMPTY, "T")),
    ("frontier", lambda: lineup.selection_frontier(EMPTY, None)),
    ("feasibility", lambda: lineup.feasibility_audit(None, None, "4-3-3")),
    ("timing_by_group", lambda: substitution.timing_by_group(EMPTY, "T")),
    ("role_matching", lambda: substitution.role_matching_matrix(None, "T")),
    ("bench_usage", lambda: substitution.bench_usage_chart(EMPTY, "T")),
    ("candidate_table", lambda: substitution.candidate_table(None, "t")),
    ("scenario", lambda: substitution.scenario_comparison(None)),
    ("manager_uncertainty", lambda: substitution.manager_uncertainty(EMPTY)),
    ("evidence_cards", lambda: substitution.evidence_cards_table([])),
    ("corr_matrix", lambda: inference.correlation_matrix_chart(EMPTY, None, "spearman", "s")),
    ("forest", lambda: inference.forest_chart(EMPTY, "goal_diff", "s")),
    ("regression", lambda: inference.regression_scatter(EMPTY, "a", "b", None, "s")),
    ("partial", lambda: inference.partial_chart([], "s")),
    ("bootstrap_hist", lambda: inference.bootstrap_hist([], 0.0, "t", "x", "s")),
    ("permutation", lambda: inference.permutation_chart(None, "a", "b", "v")),
    ("effect_sizes", lambda: inference.effect_size_chart([])),
    ("posthoc", lambda: inference.posthoc_heatmap(EMPTY, None, "v", "g")),
    ("acf", lambda: inference.acf_chart(EMPTY, EMPTY, "xg", "T")),
    ("stability", lambda: inference.stability_chart(EMPTY, "t", "y")),
    ("model_bars", lambda: model.model_comparison_bars({"fitted": False})),
    ("roc", lambda: model.roc_multi(None)),
    ("calibration", lambda: model.calibration_multi({"fitted": False})),
    ("shap", lambda: model.shap_beeswarm({"status": "SHAP is not installed"})),
    ("scree", lambda: model.scree_chart(None)),
    ("cluster_selection", lambda: model.cluster_selection_chart(None)),
    ("outliers", lambda: model.outlier_chart(None)),
    ("missingness_bar", lambda: audit.missingness_bar(EMPTY)),
    ("nullity", lambda: audit.nullity_matrix(None)),
    ("categorical", lambda: audit.categorical_frequency(EMPTY, "type")),
    ("validation", lambda: audit.validation_panel(EMPTY)),
]


@pytest.mark.parametrize("name,build", EMPTY_CASES, ids=[c[0] for c in EMPTY_CASES])
def test_empty_or_missing_input_gives_a_controlled_empty_state(name, build):
    fig = build()
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0, f"{name} drew data from an empty input"
    assert fig.layout.annotations and fig.layout.annotations[0].text, f"{name} gives no explanation"


def test_static_pitch_functions_handle_empty_input():
    for fig in (static_pitch.hexbin_map(EMPTY, "t"), static_pitch.pass_flow(None, "t"),
                static_pitch.pizza(EMPTY, 1, ["xg_p90"], ["xG"])):
        assert isinstance(fig, matplotlib.figure.Figure)
        assert not fig.axes[0].collections, "an empty-state static figure must not draw data"
        plt.close(fig)


def test_missing_required_field_names_the_field():
    df = pd.DataFrame({"x": [1.0, 2.0], "y": [1.0, 2.0]})
    fig = pitch.shot_map(df, "t")
    assert "shot_xg" in fig.layout.annotations[0].text and len(fig.data) == 0


def test_single_group_and_single_player_inputs():
    one = pd.DataFrame({"m": np.linspace(0, 1, 12), "g": ["only"] * 12, "player_name": [f"p{i}" for i in range(12)]})
    for fn in (distribution.histogram, distribution.kde, distribution.ecdf, distribution.violin,
               distribution.raincloud, distribution.quantile_profile):
        assert len(fn(one, "m", "g").data) >= 1
    assert len(distribution.box_points(one, "m", "g", hover="player_name").data) == 1
    single = one.head(1)
    assert len(distribution.kde(single, "m", "g").data) == 0, "one value cannot support a density"
    assert len(distribution.strip(single, "m", "g").data) == 1
    constant = one.assign(m=1.0)
    assert len(distribution.qq_plot(constant, "m").data) == 0


def test_small_groups_are_dropped_and_named():
    df = pd.DataFrame({"m": np.arange(14.0), "g": ["big"] * 12 + ["tiny"] * 2})
    fig = distribution.violin(df, "m", "g")
    assert len(fig.data) == 1 and "tiny" in fig.layout.title.text


def test_low_sample_warning_appears():
    ts = pd.DataFrame({"team_name": ["T"] * 4, "xg_diff": [0.1, -0.2, 0.5, 1.0], "result": list("WLDW"),
                       "match_date": pd.date_range("2024-01-01", periods=4)})
    assert "LOW SAMPLE" in team.xg_diff_distribution(ts, "T").layout.title.text


def test_sampling_is_disclosed_and_deterministic():
    rng = np.random.default_rng(0)
    n = spatial.MAX_POINTS + 500
    ev = pd.DataFrame({"x": rng.uniform(0, 120, n), "y": rng.uniform(0, 80, n), "minute": 1,
                       "player_name": "p"})
    a, b = spatial.event_points(ev, "t"), spatial.event_points(ev, "t")
    assert "random sample" in a.layout.title.text
    drawn = sum(len(t.x) for t in a.data if t.mode == "markers" and len(t.x) > 3)
    assert drawn == spatial.MAX_POINTS
    assert list(a.data[-1].x) == list(b.data[-1].x)


def test_pitch_orientation_and_mirror():
    fig = pitch.draw_pitch()
    assert tuple(fig.layout.xaxis.range) == (-4, 124)
    y = fig.layout.yaxis.range
    assert y[0] > y[1], "the y axis must run downwards (StatsBomb origin is top-left)"
    ev = pd.DataFrame({"x": [10.0, 100.0], "y": [5.0, 70.0], "end_x": [20.0, 110.0], "end_y": [10.0, 60.0]})
    m = spatial.mirror(ev)
    assert m["x"].tolist() == [110.0, 20.0] and m["y"].tolist() == [75.0, 10.0]
    assert m["end_x"].tolist() == [100.0, 10.0]
    pd.testing.assert_frame_equal(spatial.mirror(m), ev)
    assert ev["x"].tolist() == [10.0, 100.0], "mirror must not modify its input"


def test_arrow_heads_point_along_the_pass():
    ev = pd.DataFrame({"x": [10.0], "y": [40.0], "end_x": [30.0], "end_y": [40.0], "type": ["Pass"],
                       "outcome": [None], "player_name": ["p"]})
    fig = spatial.arrow_map(ev, "t")
    heads = [t for t in fig.data if t.mode == "markers" and t.marker.symbol == "triangle-up"]
    assert len(heads) == 1 and pytest.approx(float(heads[0].marker.angle[0])) == 90.0  # pointing right


def test_event_selection_filters(synthetic_ws):
    fl = synthetic_ws.flags
    tid = synthetic_ws.team_id()
    for kind in EVENT_KINDS:
        ev = select_events(fl, kind, team_id=tid)
        assert (ev["team_id"] == tid).all()
    first = select_events(fl, "Passes", period=1)
    assert set(first["period"]) <= {1}
    late = select_events(fl, "Passes", minute_range=(80, 200))
    assert late["minute"].min() >= 80
    ok = select_events(fl, "Passes", outcome="successful")
    assert ok["outcome"].isna().all()
    with pytest.raises(KeyError):
        select_events(fl, "Not an event kind")


def test_title_wrapping_and_footer():
    html, n_head, n_sub = wrap_title("A" * 30 + " " + "B" * 40 + "<br><sup>" + "word " * 40 + "</sup>")
    assert n_head == 2 and n_sub >= 2 and html.count("<sup>") == n_sub
    fig = finalize(go.Figure().update_layout(title="T", height=300), "scope text")
    assert "Data: StatsBomb Open Data" in fig.layout.title.text and "scope text" in fig.layout.title.text
    assert "SYNTHETIC" not in " ".join(a.text or "" for a in fig.layout.annotations)


def test_exports(tmp_path, synthetic_ws):
    fig = registry.render("C-040", synthetic_ws)
    out = exports.export_chart(fig, tmp_path, "C-040 results", ("html", "json", "png", "gif"))
    html = (tmp_path / "c_040_results.html").read_text(encoding="utf-8")
    assert "plotly" in html.lower() and "SYNTHETIC DEMO DATA" in html  # the dash is JSON-escaped in the file
    assert (tmp_path / "c_040_results.json").exists()
    assert out["gif"].startswith("not written")
    if exports.capabilities()["plotly_static_images"]:
        assert out["png"].endswith(".png") or out["png"].startswith("not written")
    else:
        assert "kaleido" in out["png"]
    static = registry.render("E-113", synthetic_ws)
    if isinstance(static, matplotlib.figure.Figure):
        res = exports.export_chart(static, tmp_path, "hexbin", ("png", "html"))
        assert (tmp_path / "hexbin.png").stat().st_size > 1000 and res["html"].startswith("not written")
        plt.close(static)
    csv = exports.table_csv(pd.DataFrame({"a": [1], "name": ["Hrádecký"]}))
    assert csv.startswith(b"\xef\xbb\xbf") and "Hrádecký".encode("utf-8") in csv


def test_batch_export_is_limited(tmp_path, synthetic_ws):
    seen = []
    res = exports.export_eligible_charts(synthetic_ws, tmp_path, max_charts=3,
                                         progress=lambda i, n, cid: seen.append((i, n, cid)))
    assert len(res) == 3 and (res["status"] == "exported").all() and len(seen) == 3


@pytest.mark.real_data
def test_real_data_figures_carry_the_source(real_ws):
    for cid in ("C-042", "E-110", "F-137", "J-202"):
        fig = registry.render(cid, real_ws)
        assert "Data: StatsBomb Open Data" in fig.layout.title.text
        assert SYNTHETIC_WATERMARK not in _annotations(fig)
