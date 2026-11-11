"""Pass-network charts."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.visualization.pitch import attack_arrow, draw_pitch
from src.visualization.theme import INK, NAVY, TEAL, _empty, _missing, add_banner


def pass_network_chart(nodes: pd.DataFrame, edges: pd.DataFrame, title: str, cutoff: float | None = None,
                       banner: str | None = None) -> go.Figure:
    msg = _missing(nodes, ["x", "y", "passes", "display_name"])
    if msg:
        return _empty(msg, title)
    fig = draw_pitch()
    if edges is not None and not edges.empty:
        mx = edges["count"].max()
        for r in edges.itertuples():
            fig.add_trace(go.Scatter(x=[r.x0, r.x1], y=[r.y0, r.y1], mode="lines", hoverinfo="skip",
                                     line=dict(color=NAVY, width=0.5 + 6 * r.count / mx),
                                     opacity=0.25 + 0.6 * r.count / mx, showlegend=False))
    fig.add_trace(go.Scatter(x=nodes["x"], y=nodes["y"], mode="markers+text", text=nodes["display_name"].str.split()
                             .str[-1], textposition="top center", textfont=dict(size=10, color=INK),
                             marker=dict(size=10 + 25 * nodes["passes"] / nodes["passes"].max(), color=TEAL,
                                         line=dict(color="white", width=2)),
                             customdata=nodes["passes"], hovertext=nodes["display_name"],
                             hovertemplate="%{hovertext}: %{customdata} passes<extra></extra>", showlegend=False))
    attack_arrow(fig)
    sub = f"until first substitution ({cutoff:.0f}' elapsed)" if cutoff else ""
    fig.update_layout(title=f"{title}<br><sup>node = average pass origin, size = passes; edge width = completed "
                            f"passes between pair (min shown) {sub}</sup>", height=540)
    return add_banner(fig, banner)
