"""End-to-end integration on the offline synthetic league (no network)."""
import numpy as np

from football_analytics import lineup_optimizer as lo
from football_analytics import manager_analysis as ma
from football_analytics import modeling as md
from football_analytics import reporting
from football_analytics import substitution_analysis as sa
from football_analytics import visualizations as viz
from football_analytics.ingestion import DataStore
from football_analytics.player_analysis import radar_metrics


def test_cached_offline_load_works(synthetic_bundle):
    store = DataStore(synthetic_bundle.config, offline=True)
    assert len(store.competitions()) == 1
    assert (store.manifest_frame()["from_cache"]).all()


def test_canonical_tables_and_features(synthetic_bundle):
    b = synthetic_bundle
    for k in ("matches", "events", "appearances", "substitutions_raw", "goals", "formations"):
        assert len(b.tables[k]) > 0, k
    assert b.pms["minutes_played"].ge(0).all()
    assert {"xg_p90", "progressive_passes_p90", "eligible", "coverage_label"} <= set(b.season.columns)
    assert len(b.team_stats) == 2 * len(b.tables["matches"])
    assert set(b.subs["game_state"]) <= {"leading", "drawing", "trailing"}


def test_player_dashboard_view(synthetic_bundle):
    b = synthetic_bundle
    p = b.season_pct.sort_values("minutes_played").iloc[-1]
    fig = viz.player_radar(b.season_pct, p["player_id"], radar_metrics(p["primary_role"], b.config))
    assert len(fig.data) >= 2


def test_xi_selection_for_valid_squad(synthetic_bundle):
    b = synthetic_bundle
    team = b.tables["matches"]["home_team"].iloc[0]
    ctx = lo.decision_context(b, team)
    r = lo.optimize_xi(ctx, "3-4-2-1", b.config)
    assert len(r.lineup) == 11 and r.lineup["player_id"].is_unique
    fig = viz.xi_pitch(r.lineup, "XI")
    assert len(fig.data) >= 2


def test_historical_xi_uses_only_prior_matches(synthetic_bundle):
    b = synthetic_bundle
    m = b.tables["matches"].iloc[-1]
    ctx = lo.decision_context(b, m["home_team"], match_id=m["match_id"])
    assert (ctx.season_pct["last_appearance"] < m["match_date"]).all()


def test_substitution_analysis_runs(synthetic_bundle):
    b = synthetic_bundle
    m = b.tables["matches"].iloc[1]
    rec = sa.recommend_substitution(b, m["match_id"], m["away_team"], 65.0)
    assert rec["status"] in {"ok", "No eligible outgoing or incoming players.",
                             "No compatible bench candidate for the top outgoing options."}
    imp = sa.impact_windows(b)
    assert "contaminated" in imp.columns


def test_manager_profiles_and_model_gate(synthetic_bundle):
    b = synthetic_bundle
    prof = ma.manager_profiles(b)
    assert (prof["sample_status"].str.contains("descriptive only")).all()   # 6 matches < 10
    res = md.fit_start_model(b, b.tables["matches"]["home_team"].iloc[0])
    assert res["fitted"] is False and "gate" in res


def test_exports_written(synthetic_bundle, tmp_path):
    b = synthetic_bundle
    inv = reporting.export_tables(b)
    assert (b.config.processed_dir / "appearances.csv").exists()
    assert inv["rows"].gt(0).all()
    card = reporting.write_dataset_card(b, tmp_path / "card.md")
    text = card.read_text(encoding="utf-8")
    assert "Illustrative synthetic data" in text
    dd = reporting.write_data_dictionary(b, tmp_path / "dd.md")
    assert "minutes_played" in dd.read_text(encoding="utf-8")
    assert reporting.write_run_config(b).exists()
    assert reporting.write_manifest(b).exists()
    html = viz.export_figure(viz.coverage_cards(__import__("pandas").DataFrame({"measure": ["Teams"], "value": [4]})),
                             str(tmp_path / "f.html"))
    assert (tmp_path / "f.html").exists() and html["html"]
    assert np.isfinite(b.timings["total_s"])


def test_synthetic_outputs_never_share_real_folders(synthetic_bundle):
    from football_analytics.config import Config

    syn = synthetic_bundle.config
    real = Config(project_root=syn.project_root)
    for attr in ("processed_dir", "figures_dir", "exports_dir", "raw_dir", "reports_dir"):
        assert getattr(syn, attr) != getattr(real, attr), attr
    assert "synthetic" in syn.processed_dir.parts and syn.reports_dir != syn.project_root / "reports"
