"""The chart registry: schema, honest statuses and data-availability gating."""
from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from src.visualization import availability, registry
from src.workspace import Workspace


@pytest.fixture(scope="module")
def specs():
    return registry.all_specs()


def test_catalogue_covers_the_atlas_numbering(specs):
    numbers = {s.number for s in specs if s.category in "ABCDEFGHIJK"}
    assert numbers == set(range(1, 245)), "every atlas ID 001-244 must have exactly one entry"
    assert len({s.chart_id for s in specs}) == len(specs)


def test_family_ranges_match_the_atlas(specs):
    ranges = {"A": (1, 16), "B": (17, 39), "C": (40, 66), "D": (67, 108), "E": (109, 136), "F": (137, 148),
              "G": (149, 169), "H": (170, 185), "I": (186, 198), "J": (199, 220), "K": (221, 244)}
    for s in specs:
        if s.category in ranges:
            lo, hi = ranges[s.category]
            assert lo <= s.number <= hi, s.chart_id


def test_every_spec_has_the_required_fields(specs):
    for s in specs:
        assert s.name and s.research_question.endswith("?"), s.chart_id
        assert s.category in registry.CATEGORIES
        assert s.library in ("plotly", "mplsoccer", "matplotlib")
        assert s.estimated_cost in ("low", "medium", "high")
        assert set(s.params) <= set(registry.PARAM_NAMES)
        if s.implemented:
            assert callable(s.renderer) and s.test_name and s.methodology_note, s.chart_id
            assert s.required_columns, f"{s.chart_id} declares no prerequisites"
        else:
            assert len(s.unavailable_reason) > 30, f"{s.chart_id} must explain why it is not implemented"


def test_unsupported_modalities_are_not_implemented():
    for cid in ("E-126", "E-127", "E-128", "K-244", "B-038"):
        assert not registry.get(cid).implemented


def test_register_rejects_duplicates_and_silent_gaps():
    with pytest.raises(ValueError):
        registry.register(registry.get("A-001"))
    with pytest.raises(ValueError):
        registry.register(registry.ChartSpec("Z-999", "x", "A", "why?"))


def test_status_table_counts_add_up(synthetic_ws):
    table = registry.status_table(synthetic_ws)
    counts = registry.status_counts(table)
    assert sum(counts.values()) == len(table) == len(registry.all_specs())
    assert counts[registry.NOT_IMPLEMENTED] == sum(not s.implemented for s in registry.all_specs())
    assert set(table["status"]) <= set(registry.STATUSES)
    bad = table[(table["status"] != registry.IMPLEMENTED_AVAILABLE) & (table["reason"] == "")]
    assert bad.empty, "every non-available chart must carry a reason"


def test_validation_reports_no_failures_on_the_fixture(synthetic_ws):
    table = registry.status_table(synthetic_ws, validate=True)
    failed = table[table["status"] == registry.FAILED_VALIDATION]
    assert failed.empty, failed[["chart_id", "reason"]].to_string()


def test_search_filters_by_text_and_facets(synthetic_ws):
    table = registry.status_table(synthetic_ws)
    hits = registry.search(table, "pass network")
    assert len(hits) and hits["name"].str.lower().str.contains("network").all()
    cat = registry.CATEGORIES["J"]
    assert set(registry.search(table, category=cat)["category"]) == {cat}
    assert registry.search(table, "zzzz-not-a-chart").empty
    na = registry.search(table, status=registry.NOT_IMPLEMENTED)
    assert set(na["chart_id"]) >= {"E-126", "E-128"}


def _without_column(ws: Workspace, table: str, column: str) -> Workspace:
    b = copy.copy(ws.bundle)
    if table in ("flags", "season_pct", "team_stats", "subs", "pms", "season", "workload"):
        setattr(b, table, getattr(b, table).drop(columns=[column]))
    else:
        b.tables = dict(b.tables)
        b.tables[table] = b.tables[table].drop(columns=[column])
    return Workspace(b)


def test_missing_column_makes_a_chart_unavailable_with_the_field_named(synthetic_ws):
    ws = _without_column(synthetic_ws, "events", "shot_xg")
    status, reason = availability.check(registry.get("E-110"), ws)
    assert status == registry.IMPLEMENTED_UNAVAILABLE and "shot_xg" in reason
    fig = registry.render("E-110", ws)
    assert len(fig.data) == 0, "an unavailable chart must not draw data"


def test_missing_table_and_sample_gates(synthetic_ws):
    status, reason = availability.check(registry.get("E-129"), synthetic_ws)
    assert status == registry.IMPLEMENTED_UNAVAILABLE and "360" in reason
    gated = replace(registry.get("C-040"), minimum_matches=999)
    status, reason = availability.check(gated, synthetic_ws)
    assert status == registry.IMPLEMENTED_UNAVAILABLE and "999" in reason
    gated = replace(registry.get("B-017"), minimum_players=10_000)
    assert availability.check(gated, synthetic_ws)[0] == registry.IMPLEMENTED_UNAVAILABLE


def test_missing_optional_package_is_reported(synthetic_ws, monkeypatch):
    monkeypatch.setattr(availability, "package_installed", lambda name: False)
    status, reason = availability.check(registry.get("E-113"), synthetic_ws)
    assert status == registry.IMPLEMENTED_UNAVAILABLE and "mplsoccer" in reason


def test_prerequisite_summary_lists_tables(synthetic_ws):
    info = availability.missing_summary(registry.get("F-137"), synthetic_ws)
    assert info["status"] == registry.IMPLEMENTED_AVAILABLE
    assert {t["table"] for t in info["tables"]} == {"events"}


@pytest.mark.real_data
def test_real_data_catalogue_has_no_failures(real_ws):
    table = registry.status_table(real_ws, validate=True)
    counts = registry.status_counts(table)
    assert counts[registry.FAILED_VALIDATION] == 0, table[table["status"] == registry.FAILED_VALIDATION].to_string()
    assert counts[registry.IMPLEMENTED_AVAILABLE] >= 270
    assert counts[registry.NOT_IMPLEMENTED] == 5
