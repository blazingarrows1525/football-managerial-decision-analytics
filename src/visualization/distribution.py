"""Distribution charts (catalogue family B): one metric, optionally split by a grouping column.

All functions take a DataFrame, a numeric column and an optional grouping column, return a Plotly figure and
never mutate their input. Groups with fewer than ``MIN_GROUP`` values are dropped from density-style charts and
named in the subtitle, because a density drawn from a handful of points invents shape that is not in the data.
"""
from __future__ import annotations


import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats as sps

from src.features.player_features import METRIC_LABELS
from src.visualization.theme import (AMBER, COLORWAY, FAMILY_COLORS, GRID, INK, NAVY, RED, _empty, _missing, low_sample, sub)

MIN_GROUP = 5


def nice(metric: str) -> str:
    """Readable label for a metric column."""
    return METRIC_LABELS.get(metric, str(metric).replace("_p90", " /90").replace("_pct", " %").replace("_", " "))


def _groups(df: pd.DataFrame | None, col: str, by: str | None, min_n: int = 1
            ) -> tuple[list[tuple[str, np.ndarray]], list[str], str | None]:
    """Clean per-group arrays, the names of dropped groups and an empty-state message."""
    msg = _missing(df, [col] + ([by] if by else []))
    if msg:
        return [], [], msg
    d = df[[col] + ([by] if by else [])].copy()
    d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d.dropna(subset=[col])
    if d.empty:
        return [], [], f"No numeric values for '{nice(col)}'."
    if not by:
        return [("All", d[col].to_numpy(float))], [], None
    out, dropped = [], []
    for name, g in d.groupby(by, sort=True):
        (out if len(g) >= min_n else dropped).append((str(name), g[col].to_numpy(float)))
    if not out:
        return [], [], f"No group has at least {min_n} values for '{nice(col)}'."
    return out, [n for n, _ in dropped], None


def _color(name: str, i: int) -> str:
    return FAMILY_COLORS.get(name, COLORWAY[i % len(COLORWAY)])


def _scope(groups: list, dropped: list[str]) -> str:
    n = sum(len(v) for _, v in groups)
    txt = f"n = {n:,}" + (f" in {len(groups)} groups" if len(groups) > 1 else "")
    if dropped:
        txt += f" · groups below {MIN_GROUP} values not drawn: {', '.join(dropped)}"
    return txt


def histogram(df: pd.DataFrame | None, col: str, by: str | None = None, bins: int = 30, title: str | None = None
              ) -> go.Figure:
    """Histogram with a fixed number of equal-width bins shared by all groups."""
    title = title or f"Histogram — {nice(col)}"
    groups, dropped, msg = _groups(df, col, by)
    if msg:
        return _empty(msg, title)
    allv = np.concatenate([v for _, v in groups])
    lo, hi = float(allv.min()), float(allv.max())
    size = (hi - lo) / bins if hi > lo else 1.0
    fig = go.Figure()
    for i, (name, v) in enumerate(groups):
        fig.add_trace(go.Histogram(x=v, name=f"{name} (n={len(v)})", marker_color=_color(name, i), opacity=0.75,
                                   xbins=dict(start=lo, end=hi + size, size=size)))
    fig.update_layout(barmode="overlay" if len(groups) > 1 else "relative", bargap=0.03,
                      title=sub(title, f"{bins} equal-width bins · {_scope(groups, dropped)}"),
                      xaxis_title=nice(col), yaxis_title="count", height=420, showlegend=len(groups) > 1)
    return fig


def kde(df: pd.DataFrame | None, col: str, by: str | None = None, title: str | None = None) -> go.Figure:
    """Gaussian kernel density (Scott bandwidth) per group; sample points are shown as a rug."""
    title = title or f"Kernel density — {nice(col)}"
    groups, dropped, msg = _groups(df, col, by, MIN_GROUP)
    if msg:
        return _empty(msg, title)
    allv = np.concatenate([v for _, v in groups])
    pad = 0.08 * (np.ptp(allv) or 1.0)
    xs = np.linspace(allv.min() - pad, allv.max() + pad, 240)
    fig = go.Figure()
    for i, (name, v) in enumerate(groups):
        c = _color(name, i)
        if np.ptp(v) == 0:
            continue
        fig.add_trace(go.Scatter(x=xs, y=sps.gaussian_kde(v)(xs), mode="lines", name=f"{name} (n={len(v)})",
                                 line=dict(color=c, width=2.5), fill="tozeroy", opacity=0.6))
        fig.add_trace(go.Scatter(x=v, y=np.full(len(v), -0.012 * (i + 1)) * 0, mode="markers", showlegend=False,
                                 marker=dict(symbol="line-ns-open", color=c, size=8), hoverinfo="skip"))
    fig.update_layout(title=sub(title, f"Scott bandwidth · ticks on the axis = observations · {_scope(groups, dropped)}"),
                      xaxis_title=nice(col), yaxis_title="density", height=420)
    return fig


def ecdf(df: pd.DataFrame | None, col: str, by: str | None = None, title: str | None = None) -> go.Figure:
    """Empirical cumulative distribution: no binning or smoothing, every observation is a step."""
    title = title or f"ECDF — {nice(col)}"
    groups, dropped, msg = _groups(df, col, by)
    if msg:
        return _empty(msg, title)
    fig = go.Figure()
    for i, (name, v) in enumerate(groups):
        v = np.sort(v)
        fig.add_trace(go.Scatter(x=v, y=np.arange(1, len(v) + 1) / len(v), mode="lines", line_shape="hv",
                                 name=f"{name} (n={len(v)})", line=dict(color=_color(name, i), width=2.5)))
    fig.add_hline(y=0.5, line=dict(color=GRID, dash="dot"))
    fig.update_layout(title=sub(title, f"share of observations at or below each value · {_scope(groups, dropped)}"),
                      xaxis_title=nice(col), yaxis=dict(title="cumulative share", tickformat=".0%"), height=420)
    return fig


def box_points(df: pd.DataFrame | None, col: str, by: str | None = None, title: str | None = None,
               hover: str | None = None) -> go.Figure:
    """Box plot with every observation drawn beside the box."""
    title = title or f"Box plot with points — {nice(col)}"
    msg = _missing(df, [col] + ([by] if by else []))
    if msg:
        return _empty(msg, title)
    d = df.dropna(subset=[col])
    if d.empty:
        return _empty(f"No values for '{nice(col)}'.", title)
    fig = go.Figure()
    keys = sorted(d[by].dropna().astype(str).unique()) if by else ["All"]
    for i, name in enumerate(keys):
        g = d[d[by].astype(str) == name] if by else d
        fig.add_trace(go.Box(y=g[col], name=f"{name} (n={len(g)})", boxpoints="all", jitter=0.45, pointpos=-1.7,
                             marker=dict(color=_color(name, i), size=5, opacity=0.7), line=dict(color=_color(name, i)),
                             text=g[hover] if hover and hover in g else None,
                             hovertemplate=("%{text}<br>" if hover and hover in g else "") + "%{y:.2f}<extra></extra>"))
    fig.update_layout(title=sub(title, f"box = quartiles, whiskers = 1.5 × IQR, points = observations · n = {len(d):,}"
                                + low_sample(len(d), 10)),
                      yaxis_title=nice(col), height=440, showlegend=False)
    return fig


def violin(df: pd.DataFrame | None, col: str, by: str | None = None, title: str | None = None) -> go.Figure:
    """Violin with inner quartile box; density is not extended beyond the observed range."""
    title = title or f"Violin — {nice(col)}"
    groups, dropped, msg = _groups(df, col, by, MIN_GROUP)
    if msg:
        return _empty(msg, title)
    fig = go.Figure()
    for i, (name, v) in enumerate(groups):
        fig.add_trace(go.Violin(y=v, name=f"{name} (n={len(v)})", box_visible=True, meanline_visible=True,
                                line_color=_color(name, i), spanmode="hard", points=False, opacity=0.8))
    fig.update_layout(title=sub(title, f"inner box = quartiles, line = mean · density clipped to the observed range · "
                                       f"{_scope(groups, dropped)}"),
                      yaxis_title=nice(col), height=440, showlegend=False)
    return fig


def raincloud(df: pd.DataFrame | None, col: str, by: str | None = None, title: str | None = None) -> go.Figure:
    """Raincloud: half-violin (shape), box (quartiles) and jittered raw points for each group."""
    title = title or f"Raincloud — {nice(col)}"
    groups, dropped, msg = _groups(df, col, by, MIN_GROUP)
    if msg:
        return _empty(msg, title)
    fig = go.Figure()
    for i, (name, v) in enumerate(groups):
        fig.add_trace(go.Violin(x=v, y0=f"{name} (n={len(v)})", orientation="h", side="positive", width=1.6,
                                line_color=_color(name, i), box_visible=True, points="all", pointpos=-0.55,
                                jitter=0.35, marker=dict(size=4, opacity=0.6), spanmode="hard", showlegend=False))
    fig.update_layout(title=sub(title, f"cloud = density, box = quartiles, rain = observations · {_scope(groups, dropped)}"),
                      xaxis_title=nice(col), height=max(360, 130 * len(groups) + 120), violingap=0.05)
    return fig


def strip(df: pd.DataFrame | None, col: str, by: str | None = None, title: str | None = None,
          hover: str | None = None, seed: int = 0) -> go.Figure:
    """Strip plot with deterministic jitter and transparency to limit overplotting; group medians are marked."""
    title = title or f"Strip plot — {nice(col)}"
    msg = _missing(df, [col] + ([by] if by else []))
    if msg:
        return _empty(msg, title)
    d = df.dropna(subset=[col])
    if d.empty:
        return _empty(f"No values for '{nice(col)}'.", title)
    rng = np.random.default_rng(seed)
    keys = sorted(d[by].dropna().astype(str).unique()) if by else ["All"]
    fig = go.Figure()
    for i, name in enumerate(keys):
        g = d[d[by].astype(str) == name] if by else d
        fig.add_trace(go.Scatter(x=i + rng.uniform(-0.28, 0.28, len(g)), y=g[col], mode="markers", name=name,
                                 marker=dict(color=_color(name, i), size=7, opacity=0.6,
                                             line=dict(color="white", width=0.5)),
                                 text=g[hover] if hover and hover in g else None,
                                 hovertemplate=("%{text}<br>" if hover and hover in g else "") + "%{y:.2f}<extra></extra>"))
        fig.add_shape(type="line", x0=i - 0.35, x1=i + 0.35, y0=g[col].median(), y1=g[col].median(),
                      line=dict(color=INK, width=2))
    fig.update_layout(title=sub(title, f"horizontal jitter is random (seed {seed}) and carries no meaning · bar = "
                                       f"group median · n = {len(d):,}"),
                      xaxis=dict(tickvals=list(range(len(keys))),
                                 ticktext=[f"{k} (n={int((d[by].astype(str) == k).sum()) if by else len(d)})"
                                           for k in keys]),
                      yaxis_title=nice(col), height=440, showlegend=False)
    return fig


def ridgeline(df: pd.DataFrame | None, col: str, by: str, title: str | None = None) -> go.Figure:
    """Ridgeline: one scaled kernel density per group, stacked vertically for shape comparison."""
    title = title or f"Ridgeline — {nice(col)} by {by.replace('_', ' ')}"
    groups, dropped, msg = _groups(df, col, by, MIN_GROUP)
    if msg:
        return _empty(msg, title)
    allv = np.concatenate([v for _, v in groups])
    pad = 0.08 * (np.ptp(allv) or 1.0)
    xs = np.linspace(allv.min() - pad, allv.max() + pad, 220)
    fig = go.Figure()
    for i, (name, v) in enumerate(groups[::-1]):
        if np.ptp(v) == 0:
            continue
        dens = sps.gaussian_kde(v)(xs)
        dens = dens / dens.max() * 0.9
        c = _color(name, len(groups) - 1 - i)
        fig.add_trace(go.Scatter(x=xs, y=np.full_like(xs, i), mode="lines", line=dict(color=c, width=0.5),
                                 showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=xs, y=i + dens, mode="lines", fill="tonexty", line=dict(color=c, width=2),
                                 name=name, showlegend=False,
                                 hovertemplate=f"{name}<br>{nice(col)} %{{x:.2f}}<extra></extra>"))
        fig.add_annotation(x=np.median(v), y=i, text="▲", showarrow=False, font=dict(color=INK, size=9), yshift=-8)
    fig.update_layout(title=sub(title, f"each ridge scaled to the same height (shapes comparable, areas not) · ▲ = "
                                       f"median · {_scope(groups, dropped)}"),
                      xaxis_title=nice(col),
                      yaxis=dict(tickvals=list(range(len(groups))),
                                 ticktext=[f"{n} (n={len(v)})" for n, v in groups[::-1]], showgrid=False),
                      height=max(380, 85 * len(groups) + 140))
    return fig


def _swarm_offsets(v: np.ndarray, radius: float) -> np.ndarray:
    """Greedy beeswarm: place each point at the nearest free horizontal offset."""
    order = np.argsort(v)
    off = np.zeros(len(v))
    placed: list[tuple[float, float]] = []
    for i in order:
        cand = 0.0
        near = [(y, o) for y, o in placed if abs(y - v[i]) < radius]
        step = 0
        while any(abs(cand - o) < radius * 0.9 for _, o in near):
            step += 1
            cand = (step + 1) // 2 * radius * 0.9 * (1 if step % 2 else -1)
        off[i] = cand
        placed.append((v[i], cand))
    return off


def beeswarm(df: pd.DataFrame | None, col: str, by: str | None = None, title: str | None = None,
             hover: str | None = None) -> go.Figure:
    """Beeswarm: every observation is drawn without overlap, so both density and individual values are visible."""
    title = title or f"Beeswarm — {nice(col)}"
    msg = _missing(df, [col] + ([by] if by else []))
    if msg:
        return _empty(msg, title)
    d = df.dropna(subset=[col])
    if d.empty:
        return _empty(f"No values for '{nice(col)}'.", title)
    if len(d) > 1500:
        return _empty(f"{len(d):,} points are too many for a beeswarm; use the violin or histogram instead.", title)
    keys = sorted(d[by].dropna().astype(str).unique()) if by else ["All"]
    span = float(np.ptp(d[col])) or 1.0
    fig = go.Figure()
    for i, name in enumerate(keys):
        g = d[d[by].astype(str) == name] if by else d
        v = g[col].to_numpy(float)
        off = _swarm_offsets(v / span, 0.022)
        width = max(1e-9, np.abs(off).max())
        fig.add_trace(go.Scatter(x=i + off / max(width, 0.4) * 0.4, y=v, mode="markers", name=name,
                                 marker=dict(color=_color(name, i), size=7, line=dict(color="white", width=0.6)),
                                 text=g[hover] if hover and hover in g else None,
                                 hovertemplate=("%{text}<br>" if hover and hover in g else "") + "%{y:.2f}<extra></extra>"))
    fig.update_layout(title=sub(title, f"points are spread sideways only to avoid overlap · n = {len(d):,}"),
                      xaxis=dict(tickvals=list(range(len(keys))), ticktext=keys), yaxis_title=nice(col),
                      height=460, showlegend=False)
    return fig


def quantile_profile(df: pd.DataFrame | None, col: str, by: str | None = None, title: str | None = None
                     ) -> go.Figure:
    """Quantile function (value at each percentile); differences between groups read off vertically."""
    title = title or f"Quantile plot — {nice(col)}"
    groups, dropped, msg = _groups(df, col, by, MIN_GROUP)
    if msg:
        return _empty(msg, title)
    q = np.linspace(0.02, 0.98, 49)
    fig = go.Figure()
    for i, (name, v) in enumerate(groups):
        fig.add_trace(go.Scatter(x=q * 100, y=np.quantile(v, q), mode="lines+markers", name=f"{name} (n={len(v)})",
                                 line=dict(color=_color(name, i), width=2), marker=dict(size=4)))
    fig.update_layout(title=sub(title, f"2nd to 98th percentile · {_scope(groups, dropped)}"),
                      xaxis_title="percentile", yaxis_title=nice(col), height=420)
    return fig


def qq_plot(df: pd.DataFrame | None, col: str, title: str | None = None) -> go.Figure:
    """Normal Q-Q plot with the Shapiro-Wilk result: a diagnostic for choosing parametric or rank methods."""
    title = title or f"Normal Q-Q plot — {nice(col)}"
    groups, _, msg = _groups(df, col, None)
    if msg:
        return _empty(msg, title)
    v = groups[0][1]
    if len(v) < 8 or np.ptp(v) == 0:
        return _empty(f"Need at least 8 varying values for a Q-Q plot (have {len(v)}).", title)
    (osm, osr), (slope, intercept, r) = sps.probplot(v, dist="norm")
    w, p = sps.shapiro(v[:5000])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=osm, y=osr, mode="markers", marker=dict(color=NAVY, size=6, opacity=0.75),
                             name="observations"))
    fig.add_trace(go.Scatter(x=osm, y=slope * osm + intercept, mode="lines", line=dict(color=RED, width=2),
                             name="normal reference"))
    verdict = "consistent with normality" if p >= 0.05 else "departs from normality — prefer rank-based methods"
    fig.update_layout(title=sub(title, f"n = {len(v):,} · Shapiro–Wilk W = {w:.3f}, p = {p:.3g} · {verdict} · skew "
                                       f"{sps.skew(v):.2f}"),
                      xaxis_title="theoretical normal quantiles", yaxis_title=f"ordered {nice(col)}", height=440)
    return fig


def pareto(table: pd.DataFrame | None, title: str, value_label: str = "value", top: int = 20) -> go.Figure:
    """Pareto chart: sorted contributions (bars) and cumulative share (line) from a concentration table."""
    msg = _missing(table, ["label", "value", "cumulative_share"])
    if msg:
        return _empty(msg, title)
    d = table.head(top).assign(label=lambda t: t["label"].astype(str).str.split().str[-1])
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=d["label"], y=d["value"], marker_color=NAVY, name=value_label,
                         hovertemplate="%{x}: %{y:.2f}<extra></extra>"), secondary_y=False)
    fig.add_trace(go.Scatter(x=d["label"], y=d["cumulative_share"], mode="lines+markers", name="cumulative share",
                             line=dict(color=AMBER, width=2.5)), secondary_y=True)
    n80 = int((table["cumulative_share"] < 0.8).sum() + 1)
    fig.update_yaxes(title_text=value_label, secondary_y=False)
    fig.update_yaxes(title_text="cumulative share of total", tickformat=".0%", range=[0, 1.05], secondary_y=True,
                     showgrid=False)
    fig.update_layout(title=sub(title, f"{len(table)} contributors · top 3 = {table['share'].head(3).sum():.0%} of the "
                                       f"total · {n80} needed for 80% · second axis is a share of the same quantity"),
                      height=470, xaxis=dict(tickangle=-45, tickfont=dict(size=10)), margin=dict(b=90),
                      legend=dict(orientation="h", y=1.08))
    return fig


def small_multiples(df: pd.DataFrame | None, metrics: list[str], by: str, title: str | None = None) -> go.Figure:
    """One box-plot panel per metric with the same grouping, each on its own scale."""
    title = title or f"Small multiples by {by.replace('_', ' ')}"
    msg = _missing(df, metrics + [by])
    if msg:
        return _empty(msg, title)
    metrics = [m for m in metrics if df[m].notna().sum() >= MIN_GROUP]
    if not metrics:
        return _empty("No metric has enough values.", title)
    cols = min(4, len(metrics))
    rows = int(np.ceil(len(metrics) / cols))
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=[nice(m) for m in metrics])
    keys = sorted(df[by].dropna().astype(str).unique())
    for j, m in enumerate(metrics):
        for i, k in enumerate(keys):
            v = df.loc[df[by].astype(str) == k, m].dropna()
            fig.add_trace(go.Box(y=v, name=k, marker_color=_color(k, i), boxpoints=False, showlegend=j == 0,
                                 legendgroup=k), j // cols + 1, j % cols + 1)
    fig.update_xaxes(showticklabels=False)
    fig.update_layout(title=sub(title, f"each panel has its own y-axis (scales are not comparable across panels) · "
                                       f"n = {len(df):,} rows"),
                      height=260 * rows + 110, legend=dict(orientation="h", y=-0.06))
    return fig
