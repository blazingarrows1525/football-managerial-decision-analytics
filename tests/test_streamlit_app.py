"""Streamlit dashboard smoke and behaviour tests with ``AppTest``.

The app is driven on the synthetic fixture league (no network, no secrets). Every page and every view of every
page must render without an exception and without a renderer error; global filters must change the numbers.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "app.py")
TIMEOUT = 600

VIEWS = {
    "pages/01_Executive_Overview.py": {},
    "pages/02_Match_Centre.py": {"w_match_view": ["Timeline", "Shots & xG", "Team comparison", "Events",
                                                  "Time on pitch"]},
    "pages/03_Player_Lab.py": {"w_player_view": ["Profile", "Compare", "Distributions", "Consistency", "Maps",
                                                 "Similar players", "Exposure"]},
    "pages/04_Team_Tactics.py": {"w_tactics_view": ["Style", "Formations", "Passing network", "Progression",
                                                    "Defending", "Set pieces", "Opponents"]},
    "pages/05_Pitch_And_Events.py": {"w_px_style": ["Points", "Zone heatmap", "Zone grid 3×3", "Zone grid 5×5",
                                                    "Density contours", "Event footprint (hull)", "By half"],
                                     "w_px_extra": ["Team vs opponent territory", "Possession sequence",
                                                    "Expected Threat surface", "360 freeze frame",
                                                    "Not available with event data"]},
    "pages/06_Starting_XI_Lab.py": {"w_xi_view": ["Shortlist", "Why these players", "Versus the actual XI",
                                                  "Alternatives", "Constraints", "Season backtest"]},
    "pages/07_Substitution_Lab.py": {"w_sub_view": ["Historical patterns", "Scenario at a chosen minute",
                                                    "Before / after windows", "Bench", "Backtest"]},
    "pages/08_Managerial_Intelligence.py": {"w_mgr_view": ["Formations", "Rotation", "Substitutions",
                                                           "After conceding", "Comparison and uncertainty",
                                                           "Decision audit trail", "Evidence cards"]},
    "pages/09_Statistical_Explorer.py": {"w_stat_view": ["Metric pair", "Correlation matrices",
                                                         "Match-level associations", "Group tests", "Uncertainty",
                                                         "Power and sensitivity"]},
    "pages/10_Model_Evaluation.py": {"w_model_section": ["Supervised: start selection",
                                                         "Unsupervised: player profiles"]},
    "pages/11_Data_Quality_And_Sources.py": {"w_dq_view": ["Source and manifest", "Validation", "Missingness",
                                                           "Duplicates and outliers", "Schema and dictionary",
                                                           "Coverage and lineage"]},
    "pages/12_Methodology_And_About.py": {"w_about_view": ["Research design", "Metrics and formulas",
                                                           "Decision-support methods", "Boundaries and limitations",
                                                           "Reproduce", "Versions"]},
    "pages/13_Chart_Explorer.py": {},
}


@pytest.fixture(scope="module", autouse=True)
def synthetic_app_env(tmp_path_factory):
    """Point the app at a temporary project root in synthetic mode for the whole module."""
    old = {k: os.environ.get(k) for k in ("FMA_DATA_MODE", "FMA_PROJECT_ROOT")}
    os.environ["FMA_DATA_MODE"] = "DEMO_SYNTHETIC"
    os.environ["FMA_PROJECT_ROOT"] = str(tmp_path_factory.mktemp("app_project"))
    yield
    for k, v in old.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def _clean(at: AppTest, where: str) -> None:
    assert not at.exception, f"{where}: {[e.value for e in at.exception]}"
    assert not at.error, f"{where}: {[e.value for e in at.error]}"


def _metric(at: AppTest, label: str) -> str:
    hits = [m.value for m in at.metric if m.label == label]
    assert hits, f"metric {label!r} not found among {[m.label for m in at.metric]}"
    return hits[0]


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    return at


def test_app_starts_on_the_overview_with_the_synthetic_banner(app):
    _clean(app, "app.py")
    assert [t.value for t in app.title] == ["Executive Overview"]
    assert len(app.metric) >= 8
    text = " ".join(m.value for m in app.markdown)
    assert "SYNTHETIC DEMO DATA" in text, "synthetic sessions must show the watermark banner"
    assert "not a live feed" in text
    assert "st.secrets" not in Path(APP).read_text(encoding="utf-8")


@pytest.mark.parametrize("page", list(VIEWS))
def test_every_page_and_view_renders(page):
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    at.switch_page(page).run()
    _clean(at, page)
    assert len(at.title) == 1, f"{page} must show exactly one title"
    for key, options in VIEWS[page].items():
        for opt in options:
            at.session_state[key] = opt
            at.run()
            _clean(at, f"{page} · {key} = {opt}")


def test_model_page_toggles():
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    at.switch_page("pages/10_Model_Evaluation.py").run()
    at.session_state["w_model_fit"] = True
    at.run()
    _clean(at, "model fit toggle")
    warned = " ".join(w.value for w in at.warning)
    assert "Not statistically supportable" in warned, "the fixture is too small: the gate must refuse to fit"
    at.session_state["w_model_section"] = "Unsupervised: player profiles"
    at.session_state["w_model_unsup"] = True
    for view in ("PCA", "Cluster selection", "Algorithm agreement", "Stability and outliers"):
        at.session_state["w_unsup_view"] = view
        at.run()
        _clean(at, f"unsupervised · {view}")


def test_filters_change_the_numbers_and_reset_restores_them(app, synthetic_ws):
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    total = int(_metric(at, "Matches"))
    at.session_state["f_venue"] = "home"
    at.run()
    _clean(at, "venue filter")
    home = int(_metric(at, "Matches"))
    assert 0 < home < total, "the venue filter must change the match count"
    events_home = _metric(at, "Events analysed")
    at.session_state["f_venue"] = "away"
    at.run()
    assert int(_metric(at, "Matches")) == total - home
    assert _metric(at, "Events analysed") != events_home or total - home == home
    scope = " ".join(m.value for m in at.markdown)
    assert "venue: away" in scope, "the active filters must be shown on the page"
    reset = [b for b in at.button if b.label == "Reset filters"]
    assert reset
    reset[0].click().run()
    _clean(at, "reset")
    assert int(_metric(at, "Matches")) == total


def test_empty_scope_shows_a_helpful_state():
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    at.session_state["f_venue"] = "home"
    at.run()
    played = {m.value for m in at.metric if m.label == "Record (W-D-L)"}
    w, d, l = (int(x) for x in played.pop().split("-"))
    missing = [r for r, n in (("W", w), ("D", d), ("L", l)) if n == 0]
    if not missing:
        pytest.skip("the fixture team has every result at home; no empty combination to test")
    at.session_state["f_results"] = missing[:1]
    at.run()
    _clean(at, "empty scope")
    assert any("No match satisfies the current filters" in w.value for w in at.warning)
    assert not at.metric, "no KPI may be shown for an empty scope"


def test_selection_persists_across_navigation():
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    at.session_state["f_venue"] = "home"
    at.session_state["f_min_minutes"] = 30
    at.run()
    at.switch_page("pages/03_Player_Lab.py").run()
    _clean(at, "player lab after filter")
    assert at.session_state["f_venue"] == "home" and at.session_state["f_min_minutes"] == 30
    at.switch_page("pages/02_Match_Centre.py").run()
    _clean(at, "match centre after filter")
    assert "venue: home" in " ".join(m.value for m in at.markdown)


def test_presentation_mode_renders():
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    at.session_state["f_presentation"] = True
    at.run()
    _clean(at, "presentation mode")
    assert "stSidebar" in " ".join(m.value for m in at.markdown), "presentation mode hides the sidebar via CSS"
    assert not [b for b in at.get("download_button")], "export controls are hidden in presentation mode"


def test_chart_explorer_search_and_render():
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    at.switch_page("pages/13_Chart_Explorer.py").run()
    _clean(at, "explorer")
    assert int(_metric(at, "Catalogue entries")) >= 270
    at.session_state["explorer_q"] = "voronoi"
    at.run()
    _clean(at, "explorer search")
    text = " ".join(m.value for m in at.markdown)
    assert "E-126" in text and "not implemented" in text
    at.session_state["explorer_q"] = "pareto"
    at.run()
    _clean(at, "explorer render")
    assert "B-029" in " ".join(m.value for m in at.markdown)


@pytest.mark.real_data
def test_real_data_overview_numbers(monkeypatch):
    monkeypatch.setenv("FMA_DATA_MODE", "REAL_OPEN_DATA")
    monkeypatch.delenv("FMA_PROJECT_ROOT", raising=False)
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    _clean(at, "real overview")
    assert _metric(at, "Matches") == "34" and _metric(at, "Points") == "90"
    assert _metric(at, "Record (W-D-L)") == "28-6-0"
    assert "SYNTHETIC DEMO DATA" not in " ".join(m.value for m in at.markdown)
    at.session_state["f_venue"] = "home"
    at.run()
    assert _metric(at, "Matches") == "17"


@pytest.mark.real_data
@pytest.mark.slow
@pytest.mark.parametrize("page", list(VIEWS))
def test_every_page_and_view_renders_on_real_data(page, monkeypatch):
    monkeypatch.setenv("FMA_DATA_MODE", "REAL_OPEN_DATA")
    monkeypatch.delenv("FMA_PROJECT_ROOT", raising=False)
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    at.switch_page(page).run()
    _clean(at, page)
    if page.endswith("10_Model_Evaluation.py"):
        at.session_state["w_model_fit"] = True
        at.session_state["w_model_unsup"] = True
    for key, options in VIEWS[page].items():
        for opt in options:
            at.session_state[key] = opt
            at.run()
            _clean(at, f"{page} · {key} = {opt}")
    if page.endswith("10_Model_Evaluation.py"):
        at.session_state["w_model_section"] = "Supervised: start selection"
        for view in ("Comparison", "Discrimination", "Calibration and errors", "Explainability", "Learning curve",
                     "Leakage audit"):
            at.session_state["w_model_view"] = view
            at.run()
            _clean(at, f"model · {view}")
        assert not [w for w in at.warning if "Not statistically supportable" in w.value]

