"""Pipeline integrity, derived values, model gating, decision-support outputs and generated documents."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.analytics import clustering, descriptive as desc, models
from src.analytics import lineup_optimizer as xi
from src.data import cache, provenance
from src.data.schemas import TABLE_CONTRACTS, check_contracts
from src.features import network_features as nf
from src.features import values
from src.pipeline import subset_bundle
from src.reporting import insight_cards, report_builder
from src.visualization import model as model_charts
from src.workspace import Workspace


# ------------------------------------------------------------------ data integrity
def test_table_contracts_hold(synthetic_bundle):
    c = check_contracts(synthetic_bundle)
    assert set(c["table"]) == set(TABLE_CONTRACTS)
    assert (c["status"] == "PASS").all(), c[c["status"] != "PASS"].to_string()


def test_events_link_to_known_matches_teams_and_players(synthetic_bundle):
    t = synthetic_bundle.tables
    ev = t["events"]
    assert set(ev["match_id"]) <= set(t["matches"]["match_id"])
    teams = set(t["matches"]["home_team_id"]) | set(t["matches"]["away_team_id"])
    assert set(ev["team_id"].dropna()) <= teams
    squad = set(zip(t["squads"]["match_id"], t["squads"]["player_id"]))
    acted = ev.dropna(subset=["player_id"])
    assert set(zip(acted["match_id"], acted["player_id"])) <= squad


def test_coordinates_and_xg_are_in_range_and_xg_only_on_shots(synthetic_bundle):
    ev = synthetic_bundle.tables["events"]
    assert ev["x"].dropna().between(0, 120).all() and ev["y"].dropna().between(0, 80).all()
    assert ev["shot_xg"].dropna().between(0, 1).all()
    assert (ev.loc[ev["shot_xg"].notna(), "type"] == "Shot").all()


def test_goals_reconcile_with_the_published_score(synthetic_bundle):
    t = synthetic_bundle.tables
    g = t["goals"].groupby(["match_id", "scoring_team_id"]).size()
    for m in t["matches"].itertuples():
        assert g.get((m.match_id, m.home_team_id), 0) == m.home_score
        assert g.get((m.match_id, m.away_team_id), 0) == m.away_score


def test_per90_and_percentile_rules(synthetic_bundle):
    s = synthetic_bundle.season_pct
    cfg = synthetic_bundle.config
    assert (s["eligible"] == (s["minutes_played"] >= cfg.min_minutes)).all()
    ok = s[s["eligible"] & (s["minutes_played"] > 0)].iloc[0]
    assert ok["xg_p90"] == pytest.approx(ok["xg"] / ok["minutes_played"] * 90)
    assert s.loc[s["minutes_played"] == 0, "xg_p90"].isna().all(), "no per-90 value for zero minutes"
    # players below the threshold never enter a benchmark pool and are flagged as low coverage
    low = s[~s["eligible"]]
    assert (low["coverage_label"] == "low data coverage").all()
    pools = s[s["eligible"]].groupby("benchmark_group").size()
    assert (s["benchmark_n"].dropna() <= pools.max()).all()
    assert s["xg_p90_pct"].dropna().between(0, 100).all()


def test_score_state_segments_cover_the_match_exactly(synthetic_ws):
    b = synthetic_ws.bundle
    tm = synthetic_ws.team_matches()
    r = tm.iloc[0]
    seg = desc.score_state_segments(b, r["match_id"], r["team_id"])
    ev = b.tables["events"]
    assert seg["minutes"].sum() == pytest.approx(ev.loc[ev["match_id"] == r["match_id"], "elapsed_min"].max())
    assert (seg["start"].iloc[1:].to_numpy() == seg["end"].iloc[:-1].to_numpy()).all()
    assert seg["goal_diff"].iloc[-1] == r["goals_for"] - r["goals_against"]
    st = synthetic_ws.state_time()
    assert np.allclose(st[["leading_share", "drawing_share", "trailing_share"]].sum(axis=1), 1.0)


def test_pairing_minutes_are_symmetric_and_bounded(synthetic_ws):
    m = desc.pairing_minutes(synthetic_ws.bundle, synthetic_ws.focus, min_minutes=1)
    assert np.allclose(m.to_numpy(), m.to_numpy().T)
    diag = np.diag(m.to_numpy())
    assert (m.to_numpy() <= np.minimum.outer(diag, diag) + 1e-6).all(), "shared minutes cannot exceed either player's"


def test_subset_bundle_recomputes_and_leaves_the_source_alone(synthetic_ws):
    b = synthetic_ws.bundle
    ids = synthetic_ws.match_ids()[:2]
    n_before = len(b.tables["events"])
    sub = subset_bundle(b, ids)
    assert set(sub.tables["matches"]["match_id"]) == set(ids)
    assert len(sub.tables["events"]) < n_before == len(b.tables["events"])
    assert set(sub.team_stats["match_id"]) == set(ids)
    assert sub.season_pct["minutes_played"].sum() < b.season_pct["minutes_played"].sum()


def test_processed_cache_round_trip(synthetic_config, synthetic_bundle):
    cache.save_bundle(synthetic_bundle)
    again = cache.load_bundle(synthetic_config)
    assert again is not None and again.from_cache
    for name in ("flags", "season_pct", "team_stats", "subs"):
        pd.testing.assert_frame_equal(getattr(again, name).reset_index(drop=True),
                                      getattr(synthetic_bundle, name).reset_index(drop=True), check_dtype=False)
    assert set(again.tables) >= {"matches", "events", "appearances", "spells", "goals"}
    assert len(again.tables["events"]) == len(synthetic_bundle.tables["events"])
    changed = type(synthetic_config)(**{**synthetic_config.to_dict(), "min_minutes": 45})
    assert cache.fingerprint(changed) != cache.fingerprint(synthetic_config)
    assert cache.load_bundle(changed) is None, "a changed definition must never be served from an old cache"


# ------------------------------------------------------------------ derived values
def _toy_xt_events(n: int = 4000, seed: int = 0) -> pd.DataFrame:
    """Passes move the ball 10 units forward and 30% fail; shots near goal carry more xG closer in."""
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 108, n)
    y = rng.uniform(5, 75, n)
    outcome = np.where(rng.uniform(size=n) < 0.7, None, "Incomplete")  # 30% of passes lose the ball
    moves = pd.DataFrame({"match_id": 1, "type": "Pass", "x": x, "y": y, "end_x": np.clip(x + 10, 0, 119.9),
                          "end_y": y, "outcome": outcome, "shot_xg": np.nan})
    sx = rng.uniform(90, 119.9, 300)
    shots = pd.DataFrame({"match_id": 1, "type": "Shot", "x": sx, "y": rng.uniform(25, 55, 300), "end_x": np.nan,
                          "end_y": np.nan, "outcome": "Saved", "shot_xg": (sx - 85) / 100})
    return pd.concat([moves, shots], ignore_index=True)


def test_xt_grid_is_a_valid_surface():
    ev = _toy_xt_events()
    g = values.fit_xt(ev, nx=12, ny=8)
    assert g is not None and g.converged
    assert (g.grid >= 0).all() and (g.grid <= 1).all()
    cols = g.grid.mean(axis=0)
    assert cols[-1] > cols[len(cols) // 2] > cols[0], "threat must rise towards the opponent's goal"
    assert values.xt_sanity(g)["passed"].all()
    added = values.add_xt(ev, g)
    assert added["xt_added"].mean() > 0, "moving the ball forward adds threat in this toy world"
    assert values.fit_xt(ev.head(50)) is None, "too few actions must not produce a surface"


def test_xt_ignores_failed_passes():
    ev = _toy_xt_events()
    failed = ev.copy()
    failed.loc[failed["type"] == "Pass", "outcome"] = "Incomplete"
    g = values.fit_xt(failed, nx=12, ny=8)
    assert values.add_xt(failed, g).empty
    assert g.grid[:, :6].max() == pytest.approx(0.0), "with no completed pass, threat exists only where shots are"


def test_network_helpers(synthetic_ws):
    fl = synthetic_ws.flags
    tid = synthetic_ws.team_id()
    mid = synthetic_ws.default_match()
    passes = fl[(fl["team_id"] == tid) & (fl["type"] == "Pass")]
    nodes, edges = nf.aggregate_network(passes, min_passes=1)
    assert len(nodes) and nodes["passes"].is_monotonic_decreasing
    assert set(edges["player_id"]) <= set(nodes["player_id"])
    mat = nf.pair_pass_matrix(passes)
    comp = passes[passes["outcome"].isna() & passes["pass_recipient_id"].notna()]
    assert mat.values.sum() <= len(comp)
    g = nf.match_pass_graph(fl, mid, tid)
    sim = nf.remove_node_scenario(g, synthetic_ws.names())
    if len(sim):
        assert (sim["pass_share_involved"].between(0, 1)).all()
        assert sim["efficiency_change_pct"].max() <= 1e-9 or sim["efficiency_change_pct"].notna().all()


# ------------------------------------------------------------------ models and clustering
def test_model_gate_blocks_small_samples(synthetic_ws):
    res = synthetic_ws.models()
    assert res["fitted"] is False and "gate" in res and res["gate"]["matches"] < res["gate"]["min_matches"]
    for fig in (model_charts.model_comparison_bars(res), model_charts.roc_multi(res), model_charts.confusion_chart(res),
                model_charts.learning_curve_chart(res)):
        assert len(fig.data) == 0 and "sample gate" in fig.layout.annotations[0].text
    assert synthetic_ws.permutation() is None and synthetic_ws.pdp() is None
    assert synthetic_ws.shap()["status"].startswith("No model")


def test_unsupported_targets_are_documented():
    names = " ".join(t for t, _ in models.UNSUPPORTED_TARGETS).lower()
    for word in ("result", "injury", "market value"):
        assert word in names
    assert "started" in models.TARGET_DEFINITION


def test_clustering_requires_enough_players():
    few = pd.DataFrame({"minutes_played": [900.0] * 5, "primary_role": ["CM"] * 5, "a": np.arange(5.0),
                        "b": np.arange(5.0), "c": np.arange(5.0)})
    assert clustering.clustering_comparison(few, ["a", "b", "c"], 0) is None
    assert clustering.pca_summary(few, ["a", "b", "c"], 0) is None
    assert clustering.outlier_scores(few, ["a", "b", "c"], 0) is None


def test_clustering_survives_a_constant_metric():
    rng = np.random.default_rng(0)
    d = pd.DataFrame(rng.normal(size=(40, 4)), columns=list("abcd"))
    d["const"] = 1.0
    d["minutes_played"], d["primary_role"], d["role_family"] = 900.0, "CM", "Midfielder"
    d["player_id"], d["player_name"], d["team_name"] = range(40), [f"p{i}" for i in range(40)], "T"
    res = clustering.clustering_comparison(d, list("abcd") + ["const"], 0, k_values=range(2, 5))
    assert res is not None and "const" not in res["metrics"] and res["effects"]["epsilon2"].notna().all()
    assert clustering.cluster_stability(res["X"], res["k_best"], n_boot=5)["ari"].between(-1, 1).all()


@pytest.mark.real_data
def test_real_data_results_match_the_documented_baseline(real_ws):
    """The shared package must reproduce the numbers of the preserved, executed enhanced notebook."""
    snap = report_builder.results_snapshot(real_ws)
    assert (snap["matches"], snap["events"], snap["players_in_squads"]) == (34, 137765, 460)
    assert snap["quality_checks"] == "16/16" and snap["points"] == 90 and snap["xpts"] == pytest.approx(74.8, abs=0.3)
    assert snap["goals_for"] == 89 and snap["xg_for"] == pytest.approx(72.7, abs=0.05)
    assert snap["top3_chance_share"] == pytest.approx(0.401, abs=0.002)
    assert snap["corr_significant_after_fdr"] == 0 and snap["corr_top"]["variable"] == "xg_against"
    assert snap["corr_top"]["rho"] == pytest.approx(-0.428, abs=0.002)
    assert snap["clustering"]["k_best"] == 2 and snap["clustering"]["silhouette"] == pytest.approx(0.318, abs=0.002)
    assert snap["cv_f1"]["Logistic regression"] == pytest.approx(0.811, abs=0.002)
    assert snap["holdout_auc"] == pytest.approx(0.775, abs=0.002)
    assert snap["xi_agreement_mean_pct"] == pytest.approx(77.7, abs=0.1)
    assert snap["sub_top3_share"] == pytest.approx(0.825, abs=0.002)


# ------------------------------------------------------------------ starting XI
def test_shortlist_respects_constraints_and_availability(synthetic_ws):
    ws = synthetic_ws
    team, mid = ws.focus, ws.match_ids()[-1]
    ctx = ws.xi_context(team, mid)
    formation = next(iter(ws.cfg.formation_templates))
    res = xi.optimize_xi(ctx, formation, ws.cfg)
    lu = res.lineup
    assert len(lu) == 11 and lu["player_id"].is_unique and (lu["slot_role"] == "GK").sum() == 1
    assert (lu["compatibility"] > 0).all()
    assert set(lu["player_id"]) <= set(ctx.candidates["player_id"])
    out = lu.loc[lu["slot_role"] != "GK", "player_id"].iloc[0]
    res2 = xi.optimize_xi(ctx, formation, ws.cfg, unavailable=[out])
    assert out not in set(res2.lineup["player_id"])
    assert res2.total_score <= res.total_score + 1e-9, "removing a player cannot improve the best assignment"


def test_weights_change_the_score_decomposition(synthetic_ws):
    import dataclasses

    ws = synthetic_ws
    ctx = ws.xi_context(ws.focus, ws.match_ids()[-1])
    formation = next(iter(ws.cfg.formation_templates))
    only_fit = dataclasses.replace(ws.cfg, xi_score_weights={"role_fit": 1.0, "recent_form": 0.0,
                                                             "sample_reliability": 0.0, "workload_suitability": 0.0,
                                                             "lineup_continuity": 0.0})
    lu = xi.optimize_xi(ctx, formation, only_fit).lineup
    natural = lu[lu["compatibility"] == 1]
    assert np.allclose(natural["score"], natural["role_fit"].fillna(0), atol=2.5), \
        "with all weight on role fit the slot score is the role-fit value (plus the small side tie-breaker)"


# ------------------------------------------------------------------ documents
def test_evidence_cards_are_complete_and_computed(synthetic_ws):
    cards = insight_cards.build_cards(synthetic_ws, include_slow=False)
    assert len(cards) >= 4
    for c in cards:
        assert set(c) == set(insight_cards.CARD_FIELDS)
        assert all(c[k] for k in insight_cards.CARD_FIELDS), c["title"]
        assert any(ch.isdigit() for ch in c["evidence"]), "evidence must quote computed values"
        from src.visualization import registry

        assert c["chart_id"] in registry.load()
    text = insight_cards.cards_markdown(cards)
    for banned in ("caused", "proved", "the best substitution", "made the team win"):
        assert banned not in text.lower()


def test_manifest_is_complete_and_holds_no_event_data(synthetic_bundle, tmp_path):
    man = provenance.build_manifest(synthetic_bundle, {"status": "not checked"})
    for key in ("source", "scope", "retrieval", "versions", "files", "tables", "validation", "transformations",
                "derived_table_dependencies", "data_limitations"):
        assert key in man
    assert man["synthetic"] is True and "Synthetic" in man["source"]["name"]
    assert man["retrieval"]["files"] == len(man["files"]) > 0
    assert all(len(f["sha256"]) == 64 and f["bytes"] > 0 for f in man["files"])
    assert man["scope"]["matches_analysed"] == len(synthetic_bundle.tables["matches"])
    assert man["tables"]["events"]["rows"] == len(synthetic_bundle.tables["events"])
    blob = json.dumps(man, default=str)
    assert "shot_xg" not in blob and len(blob) < 400_000, "the manifest stores hashes and counts, not data"
    path = provenance.write_manifest(synthetic_bundle)
    assert "synthetic" in str(path).replace("\\", "/"), "synthetic runs must not overwrite the real manifest"
    assert json.loads(path.read_text(encoding="utf-8"))["manifest_version"] == man["manifest_version"]


def test_real_source_terms_are_recorded():
    text = " ".join(provenance.TERMS_SUMMARY).lower()
    assert "distribute" in text and "commercial" in text and "logo" in text
    assert provenance.SOURCE_REPOSITORY_URL.endswith("hudl/open-data")


def test_report_builders_produce_documents(synthetic_ws):
    from src.visualization import registry

    table = registry.status_table(synthetic_ws)
    cat = report_builder.catalogue_markdown(synthetic_ws, table)
    assert "SYNTHETIC DEMO DATA" in cat and "A-001" in cat and "K-244" in cat and "not_implemented" in cat
    dd = report_builder.data_dictionary_markdown(synthetic_ws)
    assert "## Table `events`" in dd and "per-90 rate" in dd and "possession_proxy_pct" in dd
    snap = report_builder.results_snapshot(synthetic_ws, include_slow=False)
    assert snap["synthetic"] is True and snap["matches"] == len(synthetic_ws.team_matches())
    cards = insight_cards.build_cards(synthetic_ws, include_slow=False)
    rep = report_builder.analysis_report_markdown(synthetic_ws, snap, cards, registry.status_counts(table))
    assert "## 10. Limitations" in rep and "association" in rep
    prov = report_builder.provenance_markdown(provenance.build_manifest(synthetic_ws.bundle))
    assert "SHA-256" in prov and "## Validation" in prov


def test_synthetic_outputs_never_share_folders_with_real_outputs(synthetic_config):
    from src.config import REAL_OPEN_DATA, Config

    real = Config(project_root=synthetic_config.project_root, data_mode=REAL_OPEN_DATA)
    for attr in ("raw_dir", "processed_dir", "manifest_dir", "figures_dir", "html_dir", "tables_dir", "reports_dir"):
        assert getattr(real, attr) != getattr(synthetic_config, attr), attr


def test_workspace_defaults_are_valid(synthetic_ws):
    p = synthetic_ws.params()
    assert p.team == synthetic_ws.focus and p.match_id in synthetic_ws.match_ids()
    assert p.player_id in set(synthetic_ws.squad()["player_id"]) and p.formation in synthetic_ws.cfg.formation_templates
    assert isinstance(synthetic_ws, Workspace) and synthetic_ws.synthetic
