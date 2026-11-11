"""Helpers for the research notebooks: workspace start-up, registry-backed chart display, narrative blocks.

The notebooks stay thin: analysis lives in ``src`` and a notebook cell calls it. ``show`` renders a chart from
the same registry the dashboard uses, so a figure in a notebook and on a dashboard page is the same code.
"""
from __future__ import annotations

import os
import time
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from src.visualization import registry
from src.visualization.availability import check, package_installed
from src.workspace import Params, Workspace

STATIC = os.environ.get("FMA_STATIC") == "1"      # static PNG outputs (used for the committed, executed copies)
HEADLESS = os.environ.get("FMA_HEADLESS") == "1"  # no live widgets
_TIMINGS: list[tuple[str, float]] = []


def configure_renderer() -> str:
    """Interactive Plotly output by default; static PNG when ``FMA_STATIC=1`` and kaleido is installed.

    Static output keeps the committed notebooks small and visible on GitHub (which does not run JavaScript).
    Re-running a notebook without the variable gives fully interactive figures.
    """
    if STATIC and package_installed("kaleido"):
        pio.renderers.default = "png"
        r = pio.renderers["png"]
        r.width, r.height, r.scale = 980, None, 1
        return "static PNG (FMA_STATIC=1)"
    try:
        import google.colab  # noqa: F401

        pio.renderers.default = "colab"
    except ImportError:
        pio.renderers.default = "notebook_connected+plotly_mimetype"
    return "interactive Plotly"


def start(seed: int = 42, **config: Any) -> Workspace:
    """Load the workspace (downloads and parses on first run, then reads the processed cache) and report it."""
    from IPython.display import Markdown, display

    from src.config import default_config

    t0 = time.perf_counter()
    mode = configure_renderer()
    ws = Workspace.load(default_config(**config))
    ws.seed = seed
    m = ws.tables["matches"]
    secs = time.perf_counter() - t0
    _TIMINGS.append(("load workspace", secs))
    banner = ("\n\n> **SYNTHETIC DEMO DATA — NOT REAL FOOTBALL OBSERVATIONS**" if ws.synthetic else "")
    display(Markdown(
        f"**Workspace ready in {secs:.1f}s** ({'processed cache' if ws.bundle.from_cache else 'parsed from raw files'}) · "
        f"{m['competition_name'].iloc[0]} {m['season_name'].iloc[0]} · {len(m)} matches · "
        f"{len(ws.tables['events']):,} events · focus team **{ws.focus}** · figures: {mode} · seed {seed}{banner}"))
    return ws


def timed(label: str):
    """Context manager that records how long a pipeline step took (shown by :func:`timings`)."""
    class _T:
        def __enter__(self):
            self.t = time.perf_counter()
            return self

        def __exit__(self, *exc):
            _TIMINGS.append((label, time.perf_counter() - self.t))
            return False

    return _T()


def timings() -> pd.DataFrame:
    return pd.DataFrame(_TIMINGS, columns=["step", "seconds"]).round(2)


def show(chart_id: str, ws: Workspace, notes: bool = True, **params: Any) -> None:
    """Render one registry chart with its ID, method note and caveat. Unavailable charts say why."""
    from IPython.display import Markdown, display

    spec = registry.get(chart_id)
    status, reason = check(spec, ws)
    if status != registry.IMPLEMENTED_AVAILABLE:
        display(Markdown(f"> **{chart_id} · {spec.name}** — *{status.replace('_', ' ')}*: {reason}"))
        return
    p: Params = ws.params(**params)
    t0 = time.perf_counter()
    fig = registry.render(chart_id, ws, p)
    if isinstance(fig, go.Figure):
        if STATIC:
            fig.update_layout(width=980)
        fig.show()
    else:
        import matplotlib.pyplot as plt

        display(fig)
        plt.close(fig)
    _TIMINGS.append((f"chart {chart_id}", time.perf_counter() - t0))
    if notes:
        bits = [f"`{chart_id}` {spec.name}"]
        if spec.methodology_note:
            bits.append(f"*Method:* {spec.methodology_note}")
        if spec.caveat:
            bits.append(f"*Caveat:* {spec.caveat}")
        display(Markdown(" · ".join(bits)))


def _block(kind: str, text: str) -> None:
    from IPython.display import Markdown, display

    display(Markdown(f"**{kind}.** {text}"))


def interpret(text: str) -> None:
    """Interpretation written from values computed in the cell above."""
    _block("Interpretation", text)


def implication(text: str) -> None:
    _block("Managerial implication", text)


def limitation(text: str) -> None:
    _block("Limitation", text)


def catalogue(ws: Workspace, validate: bool = False) -> pd.DataFrame:
    """Chart catalogue with the status of every entry for the loaded data."""
    cols = ["chart_id", "name", "category", "status", "reason", "library", "estimated_cost", "params",
            "research_question"]
    return registry.status_table(ws, validate=validate)[cols]


def explorer(ws: Workspace, default: str = "C-042") -> None:
    """Interactive chart explorer (search, family filter, chart picker). Falls back to a static table.

    With widgets it renders only the selected chart; nothing is drawn for the rest of the catalogue.
    """
    from IPython.display import Markdown, display

    table = catalogue(ws)
    try:
        import ipywidgets as W

        if HEADLESS or STATIC:
            raise ImportError("headless run")
    except ImportError:
        counts = registry.status_counts(registry.status_table(ws))
        display(Markdown(
            f"**Chart explorer (static fallback).** Live controls appear when the notebook is run interactively "
            f"with ipywidgets. The catalogue holds {len(table)} entries: "
            + ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in counts.items())
            + f". Call `show(\"<chart_id>\", ws)` to render any available chart; `{default}` is shown below."))
        display(table.head(12))
        show(default, ws)
        return

    cats = ["All families"] + list(dict.fromkeys(table["category"]))
    query = W.Text(description="Search", placeholder="name, question or ID", layout=W.Layout(width="320px"))
    family = W.Dropdown(options=cats, description="Family", layout=W.Layout(width="380px"))
    only = W.Checkbox(value=True, description="available only")
    pick = W.Dropdown(description="Chart", layout=W.Layout(width="720px"))
    out = W.Output()

    def refresh(*_):
        hits = registry.search(registry.status_table(ws), query.value,
                               None if family.value == "All families" else family.value,
                               status=registry.IMPLEMENTED_AVAILABLE if only.value else None)
        pick.options = [(f"{r.chart_id} · {r.name}", r.chart_id) for r in hits.itertuples()] or [("no match", None)]

    def draw(change):
        with out:
            out.clear_output(wait=True)
            if change["new"]:
                spec = registry.get(change["new"])
                display(Markdown(f"**{spec.chart_id} · {spec.name}** — {spec.research_question}"))
                show(change["new"], ws)

    for w in (query, family, only):
        w.observe(refresh, names="value")
    pick.observe(draw, names="value")
    refresh()
    display(W.VBox([W.HBox([query, family, only]), pick, out]))
