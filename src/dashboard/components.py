"""Reusable dashboard components: KPI strips, registry-backed charts with method notes, cards and downloads."""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard import layout
from src.reporting import exports
from src.visualization import registry
from src.visualization.availability import check
from src.workspace import Params, Workspace

PLOTLY_CONFIG = {"displaylogo": False, "responsive": True,
                 "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]}


def kpi_row(items: list[tuple[str, str, str | None]], per_row: int = 6) -> None:
    """KPI strip. ``items`` = (label, value, help text). Values are passed in already formatted."""
    for i in range(0, len(items), per_row):
        cols = st.columns(len(items[i:i + per_row]))
        for col, (label, value, help_) in zip(cols, items[i:i + per_row]):
            col.metric(label, value, help=help_)


def show(fig: Any, key: str) -> None:
    """Display a Plotly or Matplotlib figure at container width."""
    if isinstance(fig, go.Figure):
        st.plotly_chart(fig, width="stretch", key=key, config=PLOTLY_CONFIG, theme=None)
    else:
        import matplotlib.pyplot as plt

        st.pyplot(fig, width="stretch")
        plt.close(fig)


def chart(chart_id: str, ws: Workspace, p: Params, key: str | None = None, notes: bool = True,
          export: bool = True) -> None:
    """Render one registry chart with its method note, caveat and export controls.

    An unavailable chart shows the exact reason; a renderer error is caught and reported without breaking the
    page.
    """
    spec = registry.get(chart_id)
    key = key or f"chart_{chart_id}"
    status, reason = check(spec, ws)
    if status != registry.IMPLEMENTED_AVAILABLE:
        st.info(f"**{spec.chart_id} · {spec.name}** — {status.replace('_', ' ')}. {reason}")
        return
    try:
        fig = registry.render(chart_id, ws, p)
    except Exception as exc:  # shown to the user, never swallowed silently
        st.error(f"**{spec.chart_id} · {spec.name}** could not be drawn for this selection "
                 f"({type(exc).__name__}: {exc}).")
        return
    show(fig, key)
    if layout.presentation():
        if spec.caveat:
            st.caption(f"{spec.chart_id} · {spec.caveat}")
        return
    if notes:
        bits = [f"`{spec.chart_id}`"]
        if spec.methodology_note:
            bits.append(spec.methodology_note)
        if spec.caveat:
            bits.append(f"**Caveat:** {spec.caveat}")
        st.caption(" · ".join(bits))
    if export and isinstance(fig, go.Figure):
        with st.popover("Export", icon=":material/download:"):
            st.download_button("Interactive HTML", exports.figure_html(fig),
                               file_name=f"{exports.slug(spec.chart_id + '_' + spec.name)}.html", mime="text/html",
                               key=f"{key}_html", on_click="ignore")
            cap = exports.capabilities()
            if not cap["plotly_static_images"]:
                st.caption(cap["plotly_static_note"])


def table(df: pd.DataFrame | None, name: str, key: str, height: int | None = None, decimals: int = 2) -> None:
    """Data table with a CSV download of exactly what is shown."""
    if df is None or len(df) == 0:
        st.info("No rows for this selection.")
        return
    d = df.copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].round(decimals)
    st.dataframe(d, width="stretch", hide_index=True, height=height or "auto", key=f"{key}_df")
    if not layout.presentation():
        st.download_button(f"Download {len(d):,} rows (CSV)", exports.table_csv(d), file_name=f"{exports.slug(name)}.csv",
                           mime="text/csv", key=f"{key}_csv", on_click="ignore", icon=":material/download:")


def evidence_card(card: dict[str, str]) -> None:
    """Evidence card: finding, evidence, scope, supporting chart, relevance, limitation, next step."""
    st.markdown(
        f'<div class="fma-card"><h4>{card["title"]}</h4>'
        f'<p><b>{card["finding"]}</b></p>'
        f'<p><span class="fma-tag">Evidence</span>{card["evidence"]}</p>'
        f'<p><span class="fma-tag">Scope</span>{card["scope"]} · chart {card["chart_id"]}</p>'
        f'<p><span class="fma-tag">Relevance</span>{card["relevance"]}</p>'
        f'<p><span class="fma-tag">Cannot tell us</span>{card["limitation"]}</p>'
        f'<p><span class="fma-tag">Next</span>{card["next_step"]}</p></div>', unsafe_allow_html=True)


def definition(term: str, text: str) -> None:
    st.markdown(f"**{term}.** {text}")


def section(title: str, question: str | None = None) -> None:
    st.subheader(title)
    if question:
        st.caption(question)
