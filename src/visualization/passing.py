"""Passing-network charts added in V3 (catalogue family F).

Encoding used by every network figure: node position = mean origin of the player's passes, node size = the
stated centrality or pass volume, edge width = completed passes between the pair (both directions drawn).
"""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.visualization.pitch import attack_arrow, draw_pitch
from src.visualization.theme import (AMBER, FAMILY_COLORS, INK, MUTED, NAVY, RED, SLATE, TEAL, _empty, _missing, heat, sub)


def _draw_network(fig: go.Figure, nodes: pd.DataFrame, edges: pd.DataFrame, size: pd.Series, color: Any,
                  row: int | None = None, col: int | None = None, edge_color: str = NAVY) -> None:
    kw = dict(row=row, col=col) if row else {}
    if edges is not None and not edges.empty:
        mx = edges["count"].max()
        for r in edges.itertuples():
            fig.add_trace(go.Scatter(x=[r.x0, r.x1], y=[r.y0, r.y1], mode="lines", hoverinfo="skip",
                                     line=dict(color=edge_color, width=0.5 + 6 * r.count / mx),
                                     opacity=0.2 + 0.6 * r.count / mx, showlegend=False), **kw)
    fig.add_trace(go.Scatter(x=nodes["x"], y=nodes["y"], mode="markers+text",
                             text=nodes["display_name"].astype(str).str.split().str[-1], textposition="top center",
                             textfont=dict(size=10, color=INK),
                             marker=dict(size=size, color=color, line=dict(color="white", width=2)),
                             customdata=nodes["passes"], hovertext=nodes["display_name"],
                             hovertemplate="%{hovertext}: %{customdata} passes<extra></extra>", showlegend=False), **kw)


def network_chart(nodes: pd.DataFrame | None, edges: pd.DataFrame | None, title: str, scope: str,
                  size_by: pd.Series | None = None, size_label: str = "passes made",
                  color_by: pd.Series | None = None) -> go.Figure:
    """Pass network with a stated node-size measure and optional role colouring.

    ``size_by`` and ``color_by`` are indexed by ``player_id`` (centrality values, role family names).
    """
    msg = _missing(nodes, ["x", "y", "passes", "display_name", "player_id"])
    if msg:
        return _empty(msg, title)
    s = nodes["player_id"].map(size_by).fillna(0) if size_by is not None else nodes["passes"]
    size = 10 + 26 * s / (s.max() or 1)
    if color_by is not None:
        fam = nodes["player_id"].map(color_by)
        color = [FAMILY_COLORS.get(f, SLATE) for f in fam]
    else:
        color = TEAL
    fig = draw_pitch()
    _draw_network(fig, nodes, edges, size, color)
    if color_by is not None:
        for f in pd.unique(nodes["player_id"].map(color_by).dropna()):
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=str(f),
                                     marker=dict(size=10, color=FAMILY_COLORS.get(f, SLATE))))
    attack_arrow(fig)
    n_edges = 0 if edges is None else len(edges)
    fig.update_layout(title=sub(title, f"{scope} · {len(nodes)} players, {n_edges} pass links shown · node = mean pass "
                                       f"origin, size = {size_label} · edge width = completed passes between the pair"),
                      height=540, legend=dict(orientation="h", y=-0.05))
    return fig


def centrality_bars(summary: pd.DataFrame | None, team: str, top: int = 14) -> go.Figure:
    """Season-average PageRank, betweenness and pass share per player."""
    msg = _missing(summary, ["player", "matches", "pagerank", "betweenness", "pass_share"])
    if msg:
        return _empty(msg, "Network centrality")
    d = summary.tail(top)
    lab = [f"{p} ({m})" for p, m in zip(d["player"], d["matches"])]
    fig = go.Figure()
    for col, name, c in (("pagerank", "PageRank (weighted by passes)", NAVY),
                         ("betweenness", "betweenness (1 / passes as distance)", TEAL),
                         ("pass_share", "share of team passes (made + received)", AMBER)):
        fig.add_bar(y=lab, x=d[col], orientation="h", name=name, marker_color=c)
    fig.update_layout(barmode="group", title=sub(f"{team}: pass-network centrality, season average",
                                                 f"mean over each player's match networks (count in brackets; minimum "
                                                 f"5) · each network uses completed passes before the first "
                                                 f"substitution so all nodes shared the pitch"),
                      xaxis_title="centrality (unitless, each measure on its own definition)",
                      height=max(440, 34 * len(d) + 130), margin=dict(l=220), legend=dict(orientation="h", y=1.07))
    return fig


def centrality_scatter(summary: pd.DataFrame | None, team: str) -> go.Figure:
    """PageRank against betweenness: hubs (many passes) versus bridges (on the shortest high-volume routes)."""
    msg = _missing(summary, ["player", "matches", "pagerank", "betweenness", "pass_share"])
    if msg:
        return _empty(msg, "Centrality comparison")
    d = summary
    fig = go.Figure(go.Scatter(x=d["pagerank"], y=d["betweenness"], mode="markers+text",
                               text=d["player"].astype(str).str.split().str[-1], textposition="top center",
                               textfont=dict(size=9),
                               marker=dict(size=8 + 60 * d["pass_share"], color=NAVY, opacity=0.8,
                                           line=dict(color="white", width=1)),
                               customdata=d["matches"], hovertext=d["player"],
                               hovertemplate="%{hovertext}<br>PageRank %{x:.3f} · betweenness %{y:.3f} · "
                                             "%{customdata} matches<extra></extra>"))
    fig.add_vline(x=d["pagerank"].median(), line=dict(color=MUTED, dash="dot"))
    fig.add_hline(y=d["betweenness"].median(), line=dict(color=MUTED, dash="dot"))
    fig.update_layout(title=sub(f"{team}: hubs and bridges",
                                f"{len(d)} players with ≥ 5 match networks · marker size = share of team passes · "
                                f"dotted = medians · centrality describes the recorded pass graph, not player quality"),
                      xaxis_title="mean PageRank (volume-weighted importance)",
                      yaxis_title="mean betweenness (bridge between team-mates)", height=480)
    return fig


def network_compare(nodes_a: pd.DataFrame | None, edges_a: pd.DataFrame | None, nodes_b: pd.DataFrame | None,
                    edges_b: pd.DataFrame | None, name_a: str, name_b: str, title: str, caveat: str) -> go.Figure:
    """Two pass networks side by side (score states, before / after a substitution)."""
    ok_a = nodes_a is not None and len(nodes_a) >= 3
    ok_b = nodes_b is not None and len(nodes_b) >= 3
    if not ok_a and not ok_b:
        return _empty("Too few passes in either selection to draw a network.", title)
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.03, subplot_titles=[
        f"{name_a} ({int(nodes_a['passes'].sum()) if ok_a else 0} passes)",
        f"{name_b} ({int(nodes_b['passes'].sum()) if ok_b else 0} passes)"])
    for c, (n, e, ok) in enumerate(((nodes_a, edges_a, ok_a), (nodes_b, edges_b, ok_b)), 1):
        draw_pitch(fig, row=1, col=c)
        if ok:
            _draw_network(fig, n, e, 9 + 20 * n["passes"] / n["passes"].max(), TEAL, row=1, col=c)
    fig.update_layout(title=sub(title, caveat), height=440)
    return fig


def pair_heatmap(matrix: pd.DataFrame | None, title: str, scope: str) -> go.Figure:
    """Passer-to-recipient completed-pass counts."""
    if matrix is None or matrix.empty:
        return _empty("No completed passes for this selection.", title)
    fig = heat(matrix.to_numpy(float), [str(c).split()[-1] for c in matrix.columns],
               [str(i) for i in matrix.index], "", fmt=".0f", colorbar="passes",
               hover="%{y} → %{x}: %{z:.0f} completed passes<extra></extra>")
    top = matrix.stack().sort_values(ascending=False)
    best = f"{top.index[0][0]} → {top.index[0][1]} ({int(top.iloc[0])})" if len(top) else ""
    fig.update_layout(title=sub(title, f"{scope} · rows = passer, columns = recipient · {int(matrix.values.sum()):,} "
                                       f"completed passes among the {len(matrix)} most involved players · most "
                                       f"frequent link: {best}"),
                      xaxis=dict(tickangle=-45, title="recipient"), yaxis=dict(autorange="reversed", title="passer"),
                      height=max(480, 30 * len(matrix) + 170), margin=dict(l=190))
    return fig


def role_matrix(matrix: pd.DataFrame | None, title: str, scope: str) -> go.Figure:
    """Completed passes between match roles."""
    if matrix is None or matrix.empty:
        return _empty("No completed passes for this selection.", title)
    share = matrix / matrix.values.sum() * 100
    fig = heat(share.to_numpy(float), list(matrix.columns), list(matrix.index), "", fmt=".1f",
               colorbar="% of passes", hover="%{y} → %{x}: %{z:.1f}% of completed passes<extra></extra>")
    fig.update_layout(title=sub(title, f"{scope} · rows = passer's match role, columns = recipient's match role · "
                                       f"{int(matrix.values.sum()):,} completed passes · roles are the positions "
                                       f"recorded for that match"),
                      xaxis_title="recipient role", yaxis=dict(autorange="reversed", title="passer role"), height=480)
    return fig


def robustness_chart(scenario: pd.DataFrame | None, title: str, scope: str) -> go.Figure:
    """Remove-one-player simulation on the pass graph."""
    msg = _missing(scenario, ["player", "efficiency_change_pct", "pass_share_involved"])
    if msg:
        return _empty(msg, title)
    d = scenario.sort_values("efficiency_change_pct", ascending=False)
    fig = go.Figure(go.Bar(y=d["player"].astype(str), x=d["efficiency_change_pct"], orientation="h",
                           marker_color=[RED if v < 0 else SLATE for v in d["efficiency_change_pct"]],
                           text=[f"{v:+.1f}% · in {s:.0%} of passes" for v, s in
                                 zip(d["efficiency_change_pct"], d["pass_share_involved"])],
                           textposition="outside", cliponaxis=False))
    fig.update_layout(title=sub(title, f"{scope} · SIMULATION on the recorded graph: change in weighted global "
                                       f"efficiency when a player's node is deleted · not a prediction — team-mates "
                                       f"would redistribute their passes"),
                      xaxis=dict(title="change in network efficiency (%)"),
                      height=max(400, 28 * len(d) + 130), margin=dict(l=190, r=170))
    return fig


def progression_network(nodes: pd.DataFrame | None, edges: pd.DataFrame | None, title: str, scope: str) -> go.Figure:
    """Pass links coloured by direction: forward links (towards the opponent's goal) against backward links."""
    msg = _missing(nodes, ["x", "y", "passes", "display_name"])
    if msg:
        return _empty(msg, title)
    fig = draw_pitch()
    if edges is not None and not edges.empty:
        mx = edges["count"].max()
        for r in edges.itertuples():
            fwd = r.x1 - r.x0
            c = TEAL if fwd > 3 else RED if fwd < -3 else SLATE
            fig.add_trace(go.Scatter(x=[r.x0, r.x1], y=[r.y0, r.y1], mode="lines", hoverinfo="skip",
                                     line=dict(color=c, width=0.6 + 6 * r.count / mx),
                                     opacity=0.3 + 0.55 * r.count / mx, showlegend=False))
        f = float(edges.loc[(edges["x1"] - edges["x0"]) > 3, "count"].sum() / edges["count"].sum())
    else:
        f = float("nan")
    fig.add_trace(go.Scatter(x=nodes["x"], y=nodes["y"], mode="markers+text",
                             text=nodes["display_name"].astype(str).str.split().str[-1], textposition="top center",
                             textfont=dict(size=10), marker=dict(size=14, color=NAVY, line=dict(color="white", width=2)),
                             showlegend=False, hoverinfo="skip"))
    for name, c in (("forward link (> 3 units)", TEAL), ("lateral", SLATE), ("backward link", RED)):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=name, line=dict(color=c, width=4)))
    attack_arrow(fig)
    fig.update_layout(title=sub(title, f"{scope} · link colour = direction between the two players' mean pass origins · "
                                       f"{f:.0%} of linked passes go to a more advanced team-mate"),
                      height=540, legend=dict(orientation="h", y=-0.05))
    return fig
