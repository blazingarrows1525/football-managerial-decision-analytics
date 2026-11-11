"""Searchable chart explorer: find a chart by name, question or family, check its prerequisites, render it.

Nothing is rendered until a chart is selected; the catalogue table itself is cheap (no renderer is executed).
"""
from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard import components, filters, state
from src.visualization import registry
from src.visualization.availability import missing_summary
from src.workspace import Workspace

STATUS_LABEL = {registry.IMPLEMENTED_AVAILABLE: "available", registry.IMPLEMENTED_UNAVAILABLE: "unavailable",
                registry.NOT_IMPLEMENTED: "not implemented", registry.FAILED_VALIDATION: "failed validation"}


@st.cache_data(show_spinner=False)
def _status(_ws: Workspace, scope_key: tuple) -> pd.DataFrame:
    return registry.status_table(_ws, validate=False)


def selectors(spec: registry.ChartSpec, ws: Workspace, tm: pd.DataFrame, prefix: str) -> dict[str, Any]:
    """Show only the selectors a chart declares and return the chosen parameters."""
    out: dict[str, Any] = {}
    names = [n for n in spec.params if n not in ("team", "min_minutes")]
    if not names:
        return out
    cols = st.columns(min(4, len(names)))
    for col, n in zip(cols * 3, names):
        with col:
            if n == "match":
                out["match_id"] = filters.match_select(ws, tm, key=f"{prefix}_match")
            elif n == "player":
                out["player_id"] = filters.player_select(ws, key=f"{prefix}_player")
            elif n == "compare":
                out["compare_id"] = filters.player_select(ws, key=f"{prefix}_compare", label_text="Compare with",
                                                          exclude=out.get("player_id"))
            elif n == "metric":
                out["metric"] = filters.metric_select(f"{prefix}_metric")
            elif n == "metric_y":
                out["metric_y"] = filters.metric_select(f"{prefix}_metric_y", "Second metric", default="xa_p90")
            elif n == "team_metric":
                out["team_metric"] = filters.metric_select(f"{prefix}_tmetric", "Team metric", filters.TEAM_METRICS)
            elif n == "group":
                out["group"] = filters.group_select(f"{prefix}_group")
            elif n == "kind":
                out["kind"] = filters.kind_select(f"{prefix}_kind")
            elif n == "formation":
                out["formation"] = filters.formation_select(ws, f"{prefix}_formation")
            elif n == "minute":
                out["minute"] = st.slider("Match minute", 46, 88, 65, key=f"{prefix}_minute")
            elif n == "method":
                out["method"] = st.selectbox("Method", ["spearman", "pearson", "kendall"], key=f"{prefix}_method")
    return out


def render(ws: Workspace, tm: pd.DataFrame, key: str = "explorer") -> None:
    """The explorer UI: search and facets on the left of the flow, chart with prerequisites below."""
    table = _status(ws, tuple(tm["match_id"]))
    counts = registry.status_counts(table)
    components.kpi_row([
        ("Catalogue entries", f"{len(table)}", "Chart concepts in the registry, including unavailable ones."),
        ("Available now", f"{counts[registry.IMPLEMENTED_AVAILABLE]}", "Renderer exists and prerequisites are met "
                                                                        "for the data in scope."),
        ("Unavailable", f"{counts[registry.IMPLEMENTED_UNAVAILABLE]}", "Renderer exists; data or optional package "
                                                                        "missing."),
        ("Not implemented", f"{counts[registry.NOT_IMPLEMENTED]}", "Concept listed with the reason it is not built."),
    ], per_row=4)
    c1, c2, c3, c4 = st.columns([0.34, 0.26, 0.2, 0.2])
    query = c1.text_input("Search name, question or method", key=f"{key}_q", placeholder="e.g. pass network, xG, "
                                                                                          "bootstrap")
    cats = ["All families"] + list(dict.fromkeys(table["category"]))
    cat = c2.selectbox("Family", cats, key=f"{key}_cat")
    stat = c3.selectbox("Status", ["Any status"] + list(STATUS_LABEL.values()), key=f"{key}_status")
    lib = c4.selectbox("Library", ["Any library"] + sorted(table["library"].unique()), key=f"{key}_lib")
    inv = {v: k for k, v in STATUS_LABEL.items()}
    hits = registry.search(table, query, None if cat == "All families" else cat, None,
                           None if lib == "Any library" else lib, inv.get(stat))
    st.caption(f"{len(hits)} of {len(table)} charts match. Select one to render it; nothing is drawn until then.")
    if hits.empty:
        st.info("No chart matches these filters.")
        return
    ids = hits["chart_id"].tolist()
    names = dict(zip(hits["chart_id"], hits["name"]))
    stats = dict(zip(hits["chart_id"], hits["status"]))
    if st.session_state.get(f"{key}_pick") not in ids:
        st.session_state[f"{key}_pick"] = ids[0]
    pick = st.selectbox("Chart", ids, key=f"{key}_pick",
                        format_func=lambda i: f"{i} · {names[i]}" + ("" if stats[i] == registry.IMPLEMENTED_AVAILABLE
                                                                    else f"  [{STATUS_LABEL[stats[i]]}]"))
    spec = registry.get(pick)
    info = missing_summary(spec, ws)
    left, right = st.columns([0.62, 0.38])
    with left:
        st.markdown(f"**{spec.chart_id} · {spec.name}**  \n{spec.research_question}")
        st.caption(f"{spec.category_name} · {spec.library} · data: {spec.data_modality} · cost: "
                   f"{spec.estimated_cost}")
    with right:
        st.markdown(f"**Status:** {STATUS_LABEL[info['status']]}" + (f" — {info['reason']}" if info["reason"] else ""))
        if spec.caveat:
            st.caption(f"What it cannot claim: {spec.caveat}")
    with st.expander("Prerequisites checked against the loaded data"):
        if info["tables"]:
            st.dataframe(pd.DataFrame(info["tables"]), hide_index=True, width="stretch")
        st.caption(f"Minimum matches: {info['minimum_matches']} · minimum eligible players: "
                   f"{info['minimum_players']} · optional package: {info['requires_package'] or 'none'}")
    if info["status"] != registry.IMPLEMENTED_AVAILABLE:
        return
    over = selectors(spec, ws, tm, f"{key}_{pick}")
    if spec.estimated_cost == "high" and not st.toggle("Render this chart (it needs a few seconds of computation)",
                                                       key=f"{key}_{pick}_go"):
        return
    with st.spinner("Rendering…"):
        components.chart(pick, ws, state.params(ws, **over), key=f"{key}_{pick}_fig")
