"""Shared Plotly theme, palette and small figure helpers (empty states, banners, notes)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from typing import Any
from typing import Iterable

INK = "#1f2933"

MUTED = "#6b7280"

PAPER = "#fbfaf7"

GRID = "#e7e4dc"

NAVY = "#1d3557"

TEAL = "#2a9d8f"

AMBER = "#e9a23b"

RED = "#c8553d"

SLATE = "#8d99ae"

PURPLE = "#7b5ea7"

PITCH_FILL = "#eef2ec"

PITCH_LINE = "#8f9d93"

COLORWAY = [NAVY, TEAL, AMBER, RED, PURPLE, SLATE, "#457b9d", "#b5838d"]

RESULT_COLORS = {"W": TEAL, "D": SLATE, "L": RED}

STATE_COLORS = {"leading": TEAL, "drawing": SLATE, "trailing": RED}

FAMILY_COLORS = {"Goalkeeper": PURPLE, "Defender": NAVY, "Midfielder": TEAL, "Forward": AMBER}

SHOT_COLORS = {"Goal": AMBER, "Saved": NAVY, "Saved To Post": NAVY, "Off T": SLATE, "Blocked": "#b8c0cc",
               "Post": PURPLE, "Wayward": "#c9ced6", "Saved Off Target": NAVY}

SEQ_SCALE = [[0, "#f1f5f4"], [0.5, "#7fb7ad"], [1, NAVY]]

DIV_SCALE = [[0, RED], [0.5, "#f7f5f0"], [1, NAVY]]


def register_theme(name: str = "fma") -> None:
    tmpl = go.layout.Template()
    tmpl.layout = go.Layout(
        font=dict(family="Inter, Segoe UI, Helvetica, Arial, sans-serif", size=13, color=INK),
        title=dict(font=dict(size=17, color=INK), x=0.01, xanchor="left"),
        paper_bgcolor=PAPER, plot_bgcolor=PAPER, colorway=COLORWAY,
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor="#cfcabd", ticks="outside", tickcolor="#cfcabd"),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor="#cfcabd", ticks="outside", tickcolor="#cfcabd"),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
        hoverlabel=dict(bgcolor="white", bordercolor="#cfcabd", font=dict(color=INK)),
        margin=dict(l=60, r=30, t=70, b=50),
    )
    pio.templates[name] = tmpl
    pio.templates.default = name


def _empty(message: str, title: str = "", height: int = 260) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                       font=dict(size=14, color=MUTED))
    fig.update_layout(title=title, height=height, xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


def _missing(df: pd.DataFrame | None, cols: Iterable[str]) -> str | None:
    """Return a message if the frame is empty or lacks required columns."""
    if df is None or len(df) == 0:
        return "No data available for this selection."
    miss = [c for c in cols if c not in df.columns]
    if miss:
        return f"Required field(s) not available in this dataset: {', '.join(miss)}"
    return None


def _rows(df: pd.DataFrame | None, col: str, value: Any) -> pd.DataFrame | None:
    """Filter ``df[col] == value`` tolerating missing frames/columns (returns None -> empty-state)."""
    if df is None or col not in df.columns:
        return None
    return df[df[col] == value]


def add_banner(fig: go.Figure, text: str | None) -> go.Figure:
    """Persistent banner (e.g. synthetic-data warning) above a chart."""
    if text:
        fig.add_annotation(text=f"<b>{text}</b>", x=0.5, y=1.13, xref="paper", yref="paper", showarrow=False,
                           font=dict(color="white", size=12), bgcolor=RED, borderpad=4)
    return fig


def source_note(fig: go.Figure, text: str) -> go.Figure:
    fig.add_annotation(text=text, x=0, y=-0.12, xref="paper", yref="paper", showarrow=False, xanchor="left",
                       font=dict(size=10, color=MUTED))
    return fig

EVENT_FAMILY_COLORS = {"Passing": NAVY, "Carrying & dribbling": TEAL, "Defending & duels": RED,
                       "Shooting & goalkeeping": AMBER, "Match administration": SLATE, "Other": PURPLE}


def _team(ts: pd.DataFrame, team: str) -> pd.DataFrame | None:
    t = _rows(ts, "team_name", team)
    return t.sort_values("match_date").reset_index(drop=True) if t is not None and len(t) else t


def _mlabel(r) -> str:
    return f"{r['match_date']:%d %b} {'v' if r['home_away'] == 'home' else '@'} {str(r['opponent'])[:14]}"

FAMILY_ORDER = ["Defender", "Midfielder", "Forward"]

HEAT_SCALE = [[0.0, "rgba(238,242,236,0)"], [0.15, "#d7e8e1"], [0.4, "#8cc5b8"], [0.65, "#3f8f99"],
              [0.85, "#2b5f86"], [1.0, NAVY]]

ROLE_ORDER = ["GK", "CB", "FB", "WB", "DM", "CM", "AM", "WM", "W", "CF"]


def _match_label(row: pd.Series, team: str) -> str:
    opp = row["away_team"] if row["home_team"] == team else row["home_team"]
    ha = "H" if row["home_team"] == team else "A"
    return f"{row['match_date']:%d %b} {opp[:14]} ({ha})"

KPI_NUM = dict(font=dict(size=30, color=NAVY))

KPI_TITLE = dict(font=dict(size=12, color=MUTED))


# ---------------------------------------------------------------------------
# Helpers shared by the registry renderers
# ---------------------------------------------------------------------------
ATTRIBUTION_SHORT = "Data: StatsBomb Open Data"
SYNTHETIC_WATERMARK = "SYNTHETIC DEMO DATA — NOT REAL FOOTBALL OBSERVATIONS"
LOW_SAMPLE_COLOR = AMBER


def sub(title: str, subtitle: str | None = None) -> str:
    """Title with a smaller method / scope line underneath."""
    return f"{title}<br><sup>{subtitle}</sup>" if subtitle else title


def low_sample(n: int, minimum: int, unit: str = "observations") -> str:
    """Suffix for subtitles when a chart rests on fewer than ``minimum`` units."""
    return f" · LOW SAMPLE: {n} {unit} (< {minimum})" if n < minimum else ""


def table_figure(df: pd.DataFrame | None, title: str, max_rows: int = 25, height: int | None = None,
                 decimals: int = 2) -> go.Figure:
    """Render a DataFrame as a Plotly table (used for audit trails and evidence tables)."""
    if df is None or len(df) == 0:
        return _empty("No rows for this selection.", title)
    d = df.head(max_rows).copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].round(decimals)
        elif pd.api.types.is_datetime64_any_dtype(d[c]):
            d[c] = d[c].dt.strftime("%Y-%m-%d")
    fig = go.Figure(go.Table(
        header=dict(values=[f"<b>{str(c).replace('_', ' ')}</b>" for c in d.columns], fill_color=NAVY,
                    font=dict(color="white", size=12), align="left", height=30),
        cells=dict(values=[d[c].astype(object).where(d[c].notna(), "—").tolist() for c in d.columns],
                   fill_color=[["white", "#f4f2ec"] * (len(d) // 2 + 1)], align="left", height=26,
                   font=dict(color=INK, size=11))))
    more = f" · first {max_rows} of {len(df)} rows" if len(df) > max_rows else f" · {len(df)} rows"
    fig.update_layout(title=sub(title, more.strip(" ·")), height=height or min(760, 130 + 27 * len(d)),
                      margin=dict(l=10, r=10, t=70, b=10))
    return fig


def heat(z: Any, x: list, y: list, title: str, colorscale: Any = None, zmid: float | None = None,
         fmt: str = ".2f", height: int | None = None, colorbar: str = "", zmin: float | None = None,
         zmax: float | None = None, annotate: bool = True, hover: str | None = None) -> go.Figure:
    """Annotated heatmap with consistent styling. NaN cells stay blank (never shown as zero)."""
    import numpy as _np

    arr = _np.asarray(z, dtype=float)
    text = _np.where(_np.isnan(arr), "", _np.vectorize(lambda v: format(v, fmt))(_np.nan_to_num(arr))) \
        if annotate else None
    fig = go.Figure(go.Heatmap(z=arr, x=[str(v) for v in x], y=[str(v) for v in y],
                               colorscale=colorscale or SEQ_SCALE, zmid=zmid, zmin=zmin, zmax=zmax,
                               text=text, texttemplate="%{text}" if annotate else None,
                               textfont=dict(size=10), xgap=2, ygap=2, hoverongaps=False,
                               colorbar=dict(title=colorbar, thickness=12),
                               hovertemplate=hover or "%{y} · %{x}: %{z:" + fmt + "}<extra></extra>"))
    fig.update_layout(title=title, height=height or max(360, 90 + 24 * len(y)),
                      yaxis=dict(autorange="reversed"), xaxis=dict(side="bottom"))
    return fig


def wrap_title(text: str, width: int = 56, sub_width: int = 84) -> tuple[str, int, int]:
    """Wrap a ``title<br><sup>subtitle</sup>`` string so it never runs off a half-width chart.

    Returns the wrapped HTML and the number of title and subtitle lines (used to size the top margin).
    """
    import re
    import textwrap

    if not text:
        return text, 0, 0
    m = re.match(r"^(.*?)(?:<br>\s*<sup>(.*)</sup>\s*)?$", text, flags=re.S)
    head, tail = (m.group(1), m.group(2)) if m else (text, None)
    head_lines = []
    for part in head.split("<br>"):
        head_lines += textwrap.wrap(part.strip(), width, break_long_words=False) or [""]
    sub_lines = textwrap.wrap(tail.replace("<br>", " ").strip(), sub_width, break_long_words=False) if tail else []
    html = "<br>".join(head_lines) + "".join(f"<br><sup>{line}</sup>" for line in sub_lines)
    return html, len(head_lines), len(sub_lines)


def finalize(fig: Any, scope: str = "", synthetic: bool = False, attribution: str = ATTRIBUTION_SHORT) -> Any:
    """Add the source / scope line and, for synthetic fixtures, the mandatory watermark.

    For Plotly figures the title is wrapped to fit a half-width container, the attribution becomes the last
    line of the title block (so it can never collide with legends or axis titles) and legends placed under the
    plot are moved clear of the x-axis title. Works for Matplotlib figures too, so every exported chart carries
    its provenance.
    """
    foot = attribution + (f" · {scope}" if scope else "")
    if isinstance(fig, go.Figure):
        import textwrap

        html, n_head, n_sub = wrap_title(fig.layout.title.text if fig.layout.title and fig.layout.title.text
                                         else "")
        foot_lines = textwrap.wrap(foot, 84, break_long_words=False)
        html += "".join(f'<br><sup><span style="color:{MUTED}">{line}</span></sup>' for line in foot_lines)
        top = 40 + 23 * max(n_head, 0) + 15 * (n_sub + len(foot_lines))
        # A horizontal legend goes directly above the plot, under the title block: placed below the plot it
        # collides with the x-axis title on short charts.
        lg = fig.layout.legend
        legend_rows = 0
        if lg is not None and lg.orientation == "h" and fig.layout.showlegend is not False:
            names = [t.name for t in fig.data if t.name and t.showlegend is not False]
            if names:
                legend_rows = max(1, -(-sum(len(str(n)) + 7 for n in names) // 78))
                fig.update_layout(legend=dict(y=1.0, yanchor="bottom", x=0, xanchor="left", font=dict(size=11)))
        top += 21 * legend_rows
        cur = fig.layout.margin.t if fig.layout.margin and fig.layout.margin.t is not None else 70
        fig.update_layout(title=dict(text=html, yref="container", y=1.0, yanchor="top", pad=dict(t=16, l=2),
                                     font=dict(size=16)),
                          margin=dict(t=max(cur, top)))
        if top > cur and fig.layout.height:
            fig.update_layout(height=fig.layout.height + (top - cur))
        if synthetic:
            fig.add_annotation(text=f"<b>{SYNTHETIC_WATERMARK}</b>", x=0.5, y=0.5, xref="paper", yref="paper",
                               showarrow=False, font=dict(color="rgba(200,85,61,0.55)", size=20), textangle=-18,
                               name="synthetic-watermark")
            fig.add_annotation(text=f"<b>{SYNTHETIC_WATERMARK}</b>", x=1, y=1, xref="paper", yref="paper",
                               yanchor="bottom", xanchor="right", showarrow=False,
                               font=dict(color="white", size=10), bgcolor=RED, borderpad=3)
        return fig
    try:  # Matplotlib figure
        fig.text(0.01, 0.005, foot, fontsize=7, color=MUTED, ha="left", va="bottom")
        if synthetic:
            fig.text(0.5, 0.5, SYNTHETIC_WATERMARK, fontsize=16, color=RED, alpha=0.45, ha="center", va="center",
                     rotation=18, weight="bold")
    except AttributeError:
        pass
    return fig


register_theme()
