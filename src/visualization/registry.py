"""Visualization registry: one specification per chart concept, with prerequisites and an auditable status.

Every catalogue entry is a :class:`ChartSpec`. An entry with a ``renderer`` is implemented; whether it is
*available* depends on the data actually loaded and is decided by :mod:`src.visualization.availability`.
Entries without a renderer are listed as ``not_implemented`` with the reason, so the catalogue never claims a
chart that does not exist.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd

REGISTRY_SCHEMA_VERSION = "1.0.0"

IMPLEMENTED_AVAILABLE = "implemented_and_available"
IMPLEMENTED_UNAVAILABLE = "implemented_but_unavailable"
NOT_IMPLEMENTED = "not_implemented"
FAILED_VALIDATION = "failed_validation"
STATUSES = (IMPLEMENTED_AVAILABLE, IMPLEMENTED_UNAVAILABLE, NOT_IMPLEMENTED, FAILED_VALIDATION)

CATEGORIES = {
    "A": "Data audit and coverage",
    "B": "Descriptive and distribution analytics",
    "C": "Match and team analysis",
    "D": "Player performance and scouting",
    "E": "Pitch, spatial and event analytics",
    "F": "Passing networks and team structure",
    "G": "Tactical, lineup and formation analytics",
    "H": "Substitution and match-state analytics",
    "I": "Managerial intelligence",
    "J": "Statistics, inference and uncertainty",
    "K": "Machine learning and diagnostic plots",
    "L": "Additional project charts and composite dashboards",
}

# Selector names a renderer may declare in ``params`` (used by the chart explorers to show only relevant controls).
PARAM_NAMES = ("team", "match", "player", "compare", "metric", "metric_y", "team_metric", "group", "kind",
               "formation", "minute", "min_minutes", "method")


@dataclass(frozen=True)
class ChartSpec:
    chart_id: str
    name: str
    category: str
    research_question: str
    required_tables: tuple[str, ...] = ()
    required_columns: dict[str, tuple[str, ...]] = field(default_factory=dict)
    optional_columns: tuple[str, ...] = ()
    minimum_rows: int = 1
    minimum_matches: int = 1
    minimum_players: int = 0
    data_modality: str = "event"
    renderer: Callable[[Any, Any], Any] | None = None
    library: str = "plotly"
    unavailable_reason: str = ""
    methodology_note: str = ""
    caveat: str = ""
    test_name: str = "tests/test_chart_renderers.py::test_renderer_on_fixture"
    estimated_cost: str = "low"
    params: tuple[str, ...] = ()
    requires_package: str | None = None
    legacy_artifact: str = ""

    @property
    def implemented(self) -> bool:
        return self.renderer is not None

    @property
    def category_name(self) -> str:
        return CATEGORIES.get(self.category, self.category)

    @property
    def number(self) -> int:
        return int(self.chart_id.split("-")[1])


REGISTRY: dict[str, ChartSpec] = {}


def register(spec: ChartSpec) -> ChartSpec:
    if spec.chart_id in REGISTRY:
        raise ValueError(f"duplicate chart id {spec.chart_id}")
    if spec.category not in CATEGORIES:
        raise ValueError(f"unknown category {spec.category!r} for {spec.chart_id}")
    bad = [p for p in spec.params if p not in PARAM_NAMES]
    if bad:
        raise ValueError(f"{spec.chart_id}: unknown params {bad}")
    if spec.renderer is None and not spec.unavailable_reason:
        raise ValueError(f"{spec.chart_id}: an entry without a renderer must state why")
    REGISTRY[spec.chart_id] = spec
    return spec


def load() -> dict[str, ChartSpec]:
    """Import the catalogue (idempotent) and return the registry."""
    if not REGISTRY:
        from src.visualization import catalogue  # noqa: F401  (registers every entry on import)
    return REGISTRY


def get(chart_id: str) -> ChartSpec:
    return load()[chart_id]


def all_specs() -> list[ChartSpec]:
    return sorted(load().values(), key=lambda s: (s.category, s.number))


def scope_text(ws: Any, params: Any = None) -> str:
    """Dataset scope shown in the footer of every rendered chart."""
    m = ws.tables["matches"]
    comp = f"{m['competition_name'].iloc[0]} {m['season_name'].iloc[0]}" if len(m) else "no matches"
    return f"{comp} · {len(m)} matches analysed · {m['match_date'].min():%d %b %Y}–{m['match_date'].max():%d %b %Y}" \
        if len(m) else comp


def attribution_text(ws: Any) -> str:
    """Source line for chart footers: the real source, or an explicit statement that the data are synthetic."""
    from src.visualization.theme import ATTRIBUTION_SHORT

    return "Synthetic test fixture — not StatsBomb data, not real football" if ws.synthetic else ATTRIBUTION_SHORT


def render(chart_id: str, ws: Any, params: Any = None, with_footer: bool = True) -> Any:
    """Render one chart. Unavailable or unimplemented charts return a labelled empty state, never fake data."""
    from src.visualization.availability import check
    from src.visualization.theme import _empty, finalize

    spec = get(chart_id)
    status, reason = check(spec, ws)
    title = f"{spec.chart_id} · {spec.name}"
    if status != IMPLEMENTED_AVAILABLE:
        fig = _empty(f"{status.replace('_', ' ')}: {reason}", title, height=240)
    else:
        fig = spec.renderer(ws, params if params is not None else ws.params())
    if with_footer:
        fig = finalize(fig, f"{scope_text(ws)} · chart {spec.chart_id}", synthetic=ws.synthetic,
                       attribution=attribution_text(ws))
    return fig


def status_table(ws: Any, validate: bool = False) -> pd.DataFrame:
    """Catalogue with the status of every entry for the loaded data.

    With ``validate=True`` each available renderer is executed once with default parameters; a renderer that
    raises is reported as ``failed_validation`` with the exception text.
    """
    from src.visualization.availability import check

    rows = []
    p = ws.params() if validate else None
    for s in all_specs():
        status, reason = check(s, ws)
        if validate and status == IMPLEMENTED_AVAILABLE:
            try:
                fig = s.renderer(ws, p)
                if fig is None:
                    raise ValueError("renderer returned None")
            except Exception as exc:  # reported, never hidden
                status, reason = FAILED_VALIDATION, f"{type(exc).__name__}: {exc}"
        rows.append({"chart_id": s.chart_id, "name": s.name, "category": s.category_name, "status": status,
                     "reason": reason, "library": s.library, "data_modality": s.data_modality,
                     "estimated_cost": s.estimated_cost, "params": ", ".join(s.params),
                     "research_question": s.research_question, "methodology_note": s.methodology_note,
                     "caveat": s.caveat, "required_tables": ", ".join(s.required_tables),
                     "required_columns": "; ".join(f"{t}: {', '.join(c)}" for t, c in s.required_columns.items()),
                     "minimum_matches": s.minimum_matches, "minimum_players": s.minimum_players,
                     "renderer": getattr(s.renderer, "__name__", "") if s.renderer else "", "test_name": s.test_name
                     if s.renderer else "", "legacy_artifact": s.legacy_artifact})
    return pd.DataFrame(rows)


def status_counts(table: pd.DataFrame) -> dict[str, int]:
    c = table["status"].value_counts()
    return {s: int(c.get(s, 0)) for s in STATUSES}


def search(table: pd.DataFrame, query: str = "", category: str | None = None, modality: str | None = None,
           library: str | None = None, status: str | None = None) -> pd.DataFrame:
    """Filter a status table by free text (name, question, method note) and by facet."""
    out = table
    if query:
        q = query.lower().strip()
        text = (out["name"] + " " + out["research_question"] + " " + out["methodology_note"] + " "
                + out["chart_id"]).str.lower()
        out = out[text.apply(lambda t: all(w in t for w in q.split()))]
    for col, val in (("category", category), ("data_modality", modality), ("library", library), ("status", status)):
        if val:
            out = out[out[col] == val]
    return out
