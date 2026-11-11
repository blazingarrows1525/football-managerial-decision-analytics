"""Comparison charts: rank changes, percentile profiles and paired values."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.visualization.distribution import nice
from src.visualization.theme import (AMBER, COLORWAY, GRID, MUTED, NAVY, SLATE, TEAL, _empty, _missing,
                                     low_sample, sub)


def cumulative_rank_table(pms: pd.DataFrame, matches: pd.DataFrame, team: str, metric: str = "xg",
                          top: int = 8) -> pd.DataFrame:
    """Rank of each player by the cumulative value of ``metric`` after every match of the team."""
    d = pms[pms["team_name"] == team]
    if d.empty or metric not in d.columns:
        return pd.DataFrame()
    order = d[["match_id", "match_date"]].drop_duplicates().sort_values("match_date").reset_index(drop=True)
    order["matchday"] = np.arange(1, len(order) + 1)
    piv = (d.pivot_table(index="match_id", columns="player_name", values=metric, aggfunc="sum")
           .reindex(order["match_id"]).fillna(0.0).cumsum())
    keep = piv.iloc[-1].sort_values(ascending=False).head(top).index
    rank = piv.rank(axis=1, ascending=False, method="min")[keep]
    long = rank.reset_index().melt("match_id", var_name="player", value_name="rank")
    long = long.merge(order, on="match_id")
    long["cumulative"] = [piv.loc[m, p] for m, p in zip(long["match_id"], long["player"])]
    return long.sort_values(["player", "matchday"]).reset_index(drop=True)


def bump_chart(rank_long: pd.DataFrame | None, title: str, value_label: str = "cumulative value") -> go.Figure:
    """Bump chart of rank over time (1 = highest). Ranks hide the size of gaps; hover shows the values."""
    msg = _missing(rank_long, ["player", "matchday", "rank", "cumulative"])
    if msg:
        return _empty(msg, title)
    fig = go.Figure()
    players = rank_long.groupby("player")["rank"].last().sort_values().index
    for i, p in enumerate(players):
        g = rank_long[rank_long["player"] == p]
        fig.add_trace(go.Scatter(x=g["matchday"], y=g["rank"], mode="lines+markers", name=p,
                                 line=dict(color=COLORWAY[i % len(COLORWAY)], width=2.5, shape="spline", smoothing=0.6),
                                 marker=dict(size=5), customdata=g["cumulative"],
                                 hovertemplate=p + "<br>matchday %{x}: rank %{y:.0f} · " + value_label
                                 + " %{customdata:.2f}<extra></extra>"))
        last = g.iloc[-1]
        fig.add_annotation(x=last["matchday"], y=last["rank"], text=str(p).split()[-1], xanchor="left", xshift=8,
                           showarrow=False, font=dict(size=10, color=COLORWAY[i % len(COLORWAY)]))
    n = int(rank_long["matchday"].max())
    fig.update_layout(title=sub(title, f"rank among the team after each of {n} matches · rank hides the size of the "
                                       f"gaps (hover for values)"),
                      xaxis=dict(title="matchday (chronological)", range=[0.5, n + 3.5]),
                      yaxis=dict(title="rank", autorange="reversed", dtick=1), height=460, showlegend=False)
    return fig


def percentile_bars(season_pct: pd.DataFrame | None, player_id: Any, metrics: list[str], title: str | None = None
                    ) -> go.Figure:
    """Role-group percentile of one player on each metric, with the raw value and the benchmark group named."""
    msg = _missing(season_pct, ["player_id", "player_name"])
    if msg:
        return _empty(msg, title or "Percentile profile")
    r = season_pct[season_pct["player_id"] == player_id]
    if r.empty:
        return _empty("Player not found in the season table.", title or "Percentile profile")
    r = r.sort_values("minutes_played", ascending=False).iloc[0]
    rows = [(m, r.get(f"{m}_pct"), r.get(m)) for m in metrics if f"{m}_pct" in season_pct.columns]
    rows = [(m, p, v) for m, p, v in rows if pd.notna(p)]
    title = title or f"{r['player_name']} — percentile profile"
    if not rows:
        return _empty(f"No percentiles for {r['player_name']}: below the minutes threshold "
                      f"({r['minutes_played']:.0f} min) or no benchmark group.", title)
    rows = rows[::-1]
    pct = [p for _, p, _ in rows]
    fig = go.Figure(go.Bar(y=[nice(m) for m, _, _ in rows], x=pct, orientation="h",
                           marker_color=[TEAL if p >= 67 else SLATE if p >= 34 else AMBER for p in pct],
                           text=[f"{p:.0f}  ·  {v:.2f}" for _, p, v in rows], textposition="outside",
                           cliponaxis=False, hovertemplate="%{y}: percentile %{x:.0f}<extra></extra>"))
    fig.add_vline(x=50, line=dict(color=MUTED, dash="dot"))
    grp, n = r.get("benchmark_group", "role group"), r.get("benchmark_n", np.nan)
    warn = low_sample(int(n) if pd.notna(n) else 0, 8, "players in the benchmark group")
    fig.update_layout(title=sub(title, f"percentile within {grp} (n = {n:.0f}) · label = percentile · raw value · "
                                       f"{r['minutes_played']:.0f} minutes{warn}"),
                      xaxis=dict(title="percentile within benchmark group", range=[0, 118]),
                      height=max(380, 30 * len(rows) + 130), margin=dict(l=190))
    return fig


def dumbbell(df: pd.DataFrame | None, label_col: str, a: str, b: str, name_a: str, name_b: str, title: str,
             x_title: str = "") -> go.Figure:
    """Paired values per row joined by a line (general dumbbell)."""
    msg = _missing(df, [label_col, a, b])
    if msg:
        return _empty(msg, title)
    d = df.dropna(subset=[a, b])
    if d.empty:
        return _empty("No complete pairs.", title)
    fig = go.Figure()
    for r in d.itertuples():
        fig.add_trace(go.Scatter(x=[getattr(r, a), getattr(r, b)], y=[getattr(r, label_col)] * 2, mode="lines",
                                 line=dict(color=GRID, width=3), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=d[a], y=d[label_col], mode="markers", name=name_a,
                             marker=dict(color=NAVY, size=10, line=dict(color="white", width=1))))
    fig.add_trace(go.Scatter(x=d[b], y=d[label_col], mode="markers", name=name_b,
                             marker=dict(color=AMBER, size=10, line=dict(color="white", width=1))))
    fig.update_layout(title=sub(title, f"n = {len(d)} pairs"), xaxis_title=x_title,
                      height=max(380, 26 * len(d) + 130), margin=dict(l=180), legend=dict(orientation="h", y=1.06))
    return fig


def grouped_bars(df: pd.DataFrame | None, category: str, value: str, group: str, title: str, y_title: str = "",
                 fmt: str = ".2f") -> go.Figure:
    """Grouped bars for a small category x group table."""
    msg = _missing(df, [category, value, group])
    if msg:
        return _empty(msg, title)
    fig = go.Figure()
    for i, (g, d) in enumerate(df.groupby(group, sort=False)):
        fig.add_bar(x=d[category], y=d[value], name=str(g), marker_color=COLORWAY[i % len(COLORWAY)],
                    text=[format(v, fmt) for v in d[value]], textposition="outside")
    fig.update_layout(barmode="group", title=title, yaxis_title=y_title, height=420,
                      legend=dict(orientation="h", y=1.08))
    return fig
