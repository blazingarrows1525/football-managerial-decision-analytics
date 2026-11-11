"""Player scouting charts added in V3 (catalogue family D)."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.visualization.distribution import nice
from src.visualization.theme import (AMBER, COLORWAY, MUTED, NAVY, TEAL, _empty, _missing, heat, sub)


def consistency_quadrant(cons: pd.DataFrame | None, team: str) -> go.Figure:
    """Mean progressive actions per 90 against their match-to-match coefficient of variation."""
    msg = _missing(cons, ["player_name", "n", "prog_mean", "prog_cv"])
    if msg:
        return _empty(msg, "Consistency vs output")
    d = cons.dropna(subset=["prog_cv"])
    if d.empty:
        return _empty("No player has enough matches for a consistency estimate.", "Consistency vs output")
    fig = go.Figure(go.Scatter(x=d["prog_mean"], y=d["prog_cv"], mode="markers+text",
                               text=d["player_name"].str.split().str[-1], textposition="top center",
                               textfont=dict(size=9),
                               marker=dict(size=6 + d["n"] * 0.7, color=TEAL, opacity=0.85,
                                           line=dict(color="white", width=1)),
                               customdata=d["n"], hovertext=d["player_name"],
                               hovertemplate="%{hovertext}<br>mean %{x:.1f}/90 · CV %{y:.2f} · %{customdata} matches"
                                             "<extra></extra>"))
    fig.add_hline(y=d["prog_cv"].median(), line=dict(color=MUTED, dash="dot"))
    fig.add_vline(x=d["prog_mean"].median(), line=dict(color=MUTED, dash="dot"))
    fig.update_layout(title=sub(f"{team}: output vs consistency",
                                f"{len(d)} players with ≥ 10 matches of ≥ 45 minutes · x = mean progressive passes + "
                                f"carries per 90 across matches · y = SD / mean (lower = steadier) · dotted = medians · "
                                f"CV is shown only where the mean is clearly above zero"),
                      xaxis_title="mean progressive actions per 90 (match level)",
                      yaxis_title="coefficient of variation", height=480)
    return fig


def interval_chart(table: pd.DataFrame | None, title: str, x_title: str, label_col: str = "player",
                   value: str = "rate_p90", lo: str = "lo", hi: str = "hi", n_col: str | None = "matches"
                   ) -> go.Figure:
    """Point estimates with bootstrap intervals (forest layout)."""
    msg = _missing(table, [label_col, value, lo, hi])
    if msg:
        return _empty(msg, title)
    d = table.sort_values(value)
    lab = [f"{p} (n={int(n)})" for p, n in zip(d[label_col], d[n_col])] if n_col and n_col in d else list(d[label_col])
    fig = go.Figure(go.Scatter(x=d[value], y=lab, mode="markers", marker=dict(color=NAVY, size=9),
                               error_x=dict(type="data", symmetric=False, array=d[hi] - d[value],
                                            arrayminus=d[value] - d[lo], color=TEAL, thickness=4, width=0),
                               hovertemplate="%{y}<br>%{x:.2f}<extra></extra>"))
    fig.update_layout(title=sub(title, f"{len(d)} rows · bars = 95% bootstrap interval, resampling matches · "
                                       f"overlapping intervals are statistical ties"),
                      xaxis_title=x_title, height=max(380, 26 * len(d) + 130), margin=dict(l=220))
    return fig


def similar_players_chart(sim: pd.DataFrame | None, player_name: str) -> go.Figure:
    """Nearest statistical neighbours of a player by distance in standardised per-90 space."""
    msg = _missing(sim, ["player_name", "team_name", "distance", "cosine_similarity"])
    if msg:
        return _empty(msg, f"Players most similar to {player_name}")
    d = sim.iloc[::-1]
    fig = go.Figure(go.Bar(y=d["player_name"] + " · " + d["team_name"].str[:20], x=d["distance"], orientation="h",
                           marker_color=NAVY, text=[f"{v:.2f}  (cos {c:.2f})"
                                                    for v, c in zip(d["distance"], d["cosine_similarity"])],
                           textposition="outside", cliponaxis=False))
    fig.update_layout(title=sub(f"Players statistically closest to {player_name}",
                                f"{len(d)} nearest neighbours in the same role family · Euclidean distance on z-scores "
                                f"of the profile metrics (smaller = closer) · similarity is relative to this dataset "
                                f"and metric set; it is not a replacement recommendation"),
                      xaxis=dict(title="distance in standardised metric space", rangemode="tozero"),
                      height=max(380, 30 * len(d) + 130), margin=dict(l=260, r=110))
    return fig


def role_fit_heatmap(matrix: pd.DataFrame | None, team: str) -> go.Figure:
    """Role-fit composite (0-100) of each squad player for each compatible role."""
    if matrix is None or matrix.empty or matrix.notna().sum().sum() == 0:
        return _empty("No role-fit scores for this selection.", "Role-fit matrix")
    m = matrix.loc[matrix.max(axis=1).sort_values(ascending=False).index]
    fig = heat(m.to_numpy(float), list(m.columns), list(m.index), "", fmt=".0f", colorbar="fit", zmin=0, zmax=100)
    fig.update_layout(title=sub(f"{team}: player-role fit matrix",
                                f"{len(m)} players above the minutes threshold · cell = weighted mean of the role's "
                                f"metric percentiles (0–100) · blank = role not compatible with the player's primary "
                                f"role in the configured compatibility table · a transparent heuristic, not a rating"),
                      margin=dict(l=190), xaxis=dict(tickangle=-30))
    return fig


def squad_depth_chart(depth: pd.DataFrame | None, team: str) -> go.Figure:
    """Minutes actually played in each role, by player (who has covered which role)."""
    msg = _missing(depth, ["match_role", "player_name", "minutes"])
    if msg:
        return _empty(msg, "Squad depth by role")
    d = depth[depth["minutes"] >= 45]
    roles = d.groupby("match_role")["minutes"].sum().sort_values(ascending=False).index
    fig = go.Figure()
    for i, (p, g) in enumerate(d.groupby("player_name")):
        g = g.set_index("match_role").reindex(roles)
        fig.add_bar(x=list(roles), y=g["minutes"], name=p, marker_color=COLORWAY[i % len(COLORWAY)],
                    text=[str(p).split()[-1] if v and v > 250 else "" for v in g["minutes"].fillna(0)],
                    textposition="inside", textfont=dict(size=9), hovertemplate=p + ": %{y:.0f} min as %{x}"
                    "<extra></extra>")
    n_per_role = d.groupby("match_role")["player_name"].nunique()
    thin = [r for r in roles if n_per_role[r] <= 1]
    fig.update_layout(barmode="stack", showlegend=False,
                      title=sub(f"{team}: squad depth — minutes by role and player",
                                f"roles are the positions recorded in the matches · spells under 45 minutes hidden · "
                                + (f"single-player roles: {', '.join(thin)}" if thin else "every role has ≥ 2 players")),
                      xaxis_title="match role", yaxis_title="minutes played", height=480)
    return fig


def exposure_timeline(workload: pd.DataFrame | None, appearances: pd.DataFrame | None, matches: pd.DataFrame | None,
                      player_id: Any, player_name: str) -> go.Figure:
    """Minutes-based exposure of one player before each match: minutes in the previous 7, 14 and 28 days."""
    msg = _missing(workload, ["match_id", "player_id", "minutes_prev_7d", "minutes_prev_14d", "minutes_prev_28d"])
    if msg:
        return _empty(msg, "Minutes-based exposure")
    w = workload[workload["player_id"] == player_id].merge(matches[["match_id", "match_date"]], on="match_id")
    w = w.merge(appearances[["match_id", "player_id", "minutes_played"]], on=["match_id", "player_id"], how="left")
    w = w.sort_values("match_date")
    if w.empty:
        return _empty(f"{player_name} is not in any match-day squad.", "Minutes-based exposure")
    fig = go.Figure()
    fig.add_bar(x=w["match_date"], y=w["minutes_played"], name="minutes in this match", marker_color="#d5dbe3")
    for col, name, c in (("minutes_prev_7d", "previous 7 days", AMBER), ("minutes_prev_14d", "previous 14 days", TEAL),
                         ("minutes_prev_28d", "previous 28 days", NAVY)):
        fig.add_trace(go.Scatter(x=w["match_date"], y=w[col], mode="lines+markers", name=name,
                                 line=dict(color=c, width=2)))
    fig.update_layout(title=sub(f"{player_name}: minutes-based exposure before each match",
                                f"{len(w)} match-day squads · counts minutes in the analysed league matches only (no "
                                f"cup, European or international minutes exist in the data) · an exposure proxy, NOT "
                                f"physical load or fatigue"),
                      yaxis_title="minutes", height=440, legend=dict(orientation="h", y=-0.2))
    return fig


def xt_bars(player_xt: pd.DataFrame | None, team: str, top: int = 15) -> go.Figure:
    """xT added by passes and by carries for the team's players."""
    msg = _missing(player_xt, ["player_name", "team_name", "xt_pass", "xt_carry", "xt_total", "minutes_played"])
    if msg:
        return _empty(msg, "xT added by player")
    d = player_xt[player_xt["team_name"] == team].sort_values("xt_total", ascending=False).head(top).iloc[::-1]
    if d.empty:
        return _empty("No players for this team.", "xT added by player")
    fig = go.Figure()
    fig.add_bar(y=d["player_name"], x=d["xt_pass"], orientation="h", name="completed passes", marker_color=NAVY)
    fig.add_bar(y=d["player_name"], x=d["xt_carry"], orientation="h", name="carries", marker_color=TEAL)
    for r in d.itertuples():
        if pd.notna(r.xt_p90):
            fig.add_annotation(x=max(r.xt_total, 0), y=r.player_name, text=f"  {r.xt_p90:.2f}/90", showarrow=False,
                               xanchor="left", font=dict(size=10, color=MUTED))
    fig.update_layout(barmode="relative", title=sub(f"{team}: Expected Threat added (project-computed xT)",
                                                    f"top {len(d)} by total · xT added = xT(end cell) − xT(start cell) "
                                                    f"of completed passes and carries · grid fitted in-sample on the "
                                                    f"analysed matches · derived value, not a StatsBomb field"),
                      xaxis_title="xT added (season total)", height=max(420, 26 * len(d) + 130),
                      margin=dict(l=190, r=80), legend=dict(orientation="h", y=1.07))
    return fig


def role_small_multiples(season_pct: pd.DataFrame | None, metrics: list[str], min_minutes: float) -> go.Figure:
    """Median of each metric by primary role, one panel per metric (roles with fewer than 5 players dropped)."""
    msg = _missing(season_pct, metrics + ["primary_role", "minutes_played"])
    if msg:
        return _empty(msg, "Role comparison")
    d = season_pct[season_pct["minutes_played"] >= min_minutes]
    size = d.groupby("primary_role").size()
    roles = size[size >= 5].index.tolist()
    if not roles:
        return _empty("No role has at least 5 eligible players.", "Role comparison")
    med = d[d["primary_role"].isin(roles)].groupby("primary_role")[metrics].median()
    cols = min(4, len(metrics))
    rows = int(np.ceil(len(metrics) / cols))
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=[nice(m) for m in metrics])
    for j, m in enumerate(metrics):
        s = med[m].sort_values()
        fig.add_trace(go.Bar(x=s.index, y=s.values, marker_color=NAVY, showlegend=False,
                             hovertemplate="%{x}: %{y:.2f}<extra></extra>"), j // cols + 1, j % cols + 1)
    dropped = size[size < 5].index.tolist()
    fig.update_layout(title=sub("Role comparison: median by primary role",
                                f"{int(size[roles].sum())} players with ≥ {min_minutes:.0f} minutes in {len(roles)} roles"
                                + (f" · roles below 5 players not shown: {', '.join(dropped)}" if dropped else "")
                                + " · each panel has its own scale"),
                      height=250 * rows + 120)
    return fig


def report_card(profile: dict | None, strengths: pd.DataFrame | None, missing: list[str]) -> go.Figure:
    """Player report card as a table: identity, exposure, strongest and weakest percentiles, missing evidence."""
    from src.visualization.theme import table_figure

    if not profile:
        return _empty("Player not found.", "Player report card")
    rows = [("Player", profile.get("player_name")), ("Team", profile.get("team_name")),
            ("Primary position", profile.get("primary_position")), ("Minutes", f"{profile.get('minutes_played', 0):.0f}"),
            ("Appearances / starts", f"{profile.get('appearances', 0)} / {profile.get('starts', 0)}"),
            ("Benchmark group", f"{profile.get('benchmark_group')} (n = {profile.get('benchmark_n')})"),
            ("Evidence coverage", profile.get("coverage_label"))]
    if strengths is not None and len(strengths):
        for r in strengths.itertuples():
            rows.append((f"{getattr(r, 'kind', 'metric')}".title(), f"{getattr(r, 'metric', '')}: percentile "
                                                                   f"{getattr(r, 'percentile', float('nan')):.0f}"))
    rows.append(("Evidence not available", ", ".join(missing) if missing else "—"))
    return table_figure(pd.DataFrame(rows, columns=["field", "value"]),
                        f"{profile.get('player_name')}: report card", max_rows=30)
