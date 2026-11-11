"""Spatial pitch charts beyond the core set: zones, density, hulls, arrows, lanes, sequences and the xT surface.

Coordinate convention (StatsBomb): the pitch is 120 x 80 units, the origin is the top-left corner and *every*
team's events are recorded attacking left to right, in both halves. No per-half flip is therefore needed, and
both teams of a match are shown attacking towards x = 120 unless a chart mirrors one of them explicitly.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import PITCH_LENGTH, PITCH_WIDTH
from src.visualization.pitch import attack_arrow, draw_pitch, heatmap_layer
from src.visualization.theme import (AMBER, COLORWAY, HEAT_SCALE, INK, MUTED, NAVY, RED,
                                     SEQ_SCALE, SHOT_COLORS, SLATE, TEAL, _empty, _missing, low_sample, sub)

MAX_POINTS = 4000
MAX_ARROWS = 500


def mirror(ev: pd.DataFrame) -> pd.DataFrame:
    """Flip both axes (used to show an opponent attacking right to left on a shared pitch)."""
    out = ev.copy()
    for c, size in (("x", PITCH_LENGTH), ("end_x", PITCH_LENGTH), ("y", PITCH_WIDTH), ("end_y", PITCH_WIDTH)):
        if c in out.columns:
            out[c] = size - out[c]
    return out


def _located(ev: pd.DataFrame | None, need_end: bool = False) -> tuple[pd.DataFrame | None, str | None]:
    cols = ["x", "y"] + (["end_x", "end_y"] if need_end else [])
    msg = _missing(ev, cols)
    if msg:
        return None, msg
    d = ev.dropna(subset=cols)
    if d.empty:
        return None, "No located events for this selection."
    return d, None


def _sample(d: pd.DataFrame, limit: int, seed: int = 0) -> tuple[pd.DataFrame, str]:
    if len(d) <= limit:
        return d, ""
    return d.sample(limit, random_state=seed), f" · random sample of {limit:,} of {len(d):,} drawn (seed {seed})"


def event_points(ev: pd.DataFrame | None, title: str, color_by: str | None = None, half: bool = False,
                 seed: int = 0) -> go.Figure:
    """Locations of the selected events, optionally coloured by a categorical field."""
    d, msg = _located(ev)
    if msg:
        return _empty(msg, title)
    n = len(d)
    d, note = _sample(d, MAX_POINTS, seed)
    fig = draw_pitch(half=half)
    groups = [(None, d)] if not color_by or color_by not in d.columns else list(
        d.assign(**{color_by: d[color_by].fillna("Successful / none").astype(str)}).groupby(color_by))
    for i, (name, g) in enumerate(groups):
        who = g["player_name"].fillna("") if "player_name" in g.columns else pd.Series("", index=g.index)
        fig.add_trace(go.Scatter(x=g["x"], y=g["y"], mode="markers", name=f"{name} ({len(g)})" if name else "events",
                                 marker=dict(size=6, color=COLORWAY[i % len(COLORWAY)], opacity=0.6,
                                             line=dict(color="white", width=0.4)),
                                 customdata=np.stack([who, g["minute"] if "minute" in g else np.zeros(len(g))], -1),
                                 hovertemplate="%{customdata[0]} · minute %{customdata[1]}<extra></extra>",
                                 showlegend=name is not None))
    attack_arrow(fig)
    fig.update_layout(title=sub(title, f"{n:,} located events{note}" + low_sample(n, 20, "events")), height=520,
                      legend=dict(orientation="h", y=-0.05))
    return fig


def arrow_map(ev: pd.DataFrame | None, title: str, color: str = NAVY, seed: int = 0,
              success_col: str | None = "outcome") -> go.Figure:
    """Start-to-end arrows (passes, carries). Arrow heads mark the end; failed passes are drawn in red."""
    d, msg = _located(ev, need_end=True)
    if msg:
        return _empty(msg, title)
    n = len(d)
    d, note = _sample(d, MAX_ARROWS, seed)
    fig = draw_pitch()
    is_pass = "type" in d.columns and (d["type"] == "Pass").all()
    ok = d[success_col].isna() if (is_pass and success_col in d.columns) else pd.Series(True, index=d.index)
    for name, g, c in (("completed" if is_pass else "actions", d[ok], color), ("incomplete", d[~ok], RED)):
        if g.empty:
            continue
        xs = np.column_stack([g["x"], g["end_x"], np.full(len(g), np.nan)]).ravel()
        ys = np.column_stack([g["y"], g["end_y"], np.full(len(g), np.nan)]).ravel()
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=c, width=1.2), opacity=0.5,
                                 name=f"{name} ({len(g)})", hoverinfo="skip"))
        # screen angle: clockwise from "up"; the y axis is drawn downwards, so screen-up is -dy
        ang = np.degrees(np.arctan2(g["end_x"] - g["x"], -(g["end_y"] - g["y"])))
        who = g["player_name"].fillna("") if "player_name" in g.columns else pd.Series("", index=g.index)
        fig.add_trace(go.Scatter(x=g["end_x"], y=g["end_y"], mode="markers", showlegend=False,
                                 marker=dict(symbol="triangle-up", angle=ang, size=7, color=c, opacity=0.85),
                                 text=who, hovertemplate="%{text}<extra></extra>"))
    attack_arrow(fig)
    fig.update_layout(title=sub(title, f"{n:,} actions with start and end location{note} · arrow head = end point"),
                      height=520, legend=dict(orientation="h", y=-0.05))
    return fig


def density_contours(ev: pd.DataFrame | None, title: str, end: bool = False) -> go.Figure:
    """Smoothed 2-D density of event locations (contours). Smoothing spreads mass into nearby empty space."""
    d, msg = _located(ev, need_end=end)
    if msg:
        return _empty(msg, title)
    if len(d) < 30:
        return _empty(f"A density needs at least 30 located events (selection has {len(d)}); use the point map.",
                      title)
    x, y = (d["end_x"], d["end_y"]) if end else (d["x"], d["y"])
    fig = go.Figure(go.Histogram2dContour(x=x, y=y, colorscale=HEAT_SCALE, ncontours=12, showscale=False,
                                          xbins=dict(start=0, end=120, size=6), ybins=dict(start=0, end=80, size=5),
                                          contours=dict(coloring="fill"), line=dict(width=0), hoverinfo="skip"))
    draw_pitch(fig, lines_on_top=True)
    attack_arrow(fig)
    fig.update_layout(title=sub(title, f"{len(d):,} {'end' if end else 'start'} locations · contours of a smoothed "
                                       f"6 × 5 unit histogram · shading between events is interpolation, not data"),
                      height=520)
    return fig


def zone_grid(ev: pd.DataFrame | None, title: str, nx: int = 6, ny: int = 5, share: bool = True) -> go.Figure:
    """Counts (or shares) of events on an nx by ny zone grid with the pitch drawn on top."""
    d, msg = _located(ev)
    if msg:
        return _empty(msg, title)
    h, xe, ye = np.histogram2d(d["x"].clip(0, 119.99), d["y"].clip(0, 79.99), bins=(nx, ny),
                               range=[[0, 120], [0, 80]])
    z = (h / h.sum() * 100 if share else h).T
    text = np.vectorize(lambda v, c: f"{v:.1f}%<br>({int(c)})" if share else f"{int(c)}")(z, h.T)
    fig = go.Figure(go.Heatmap(x=(xe[:-1] + xe[1:]) / 2, y=(ye[:-1] + ye[1:]) / 2, z=z, colorscale=SEQ_SCALE,
                               text=text, texttemplate="%{text}", textfont=dict(size=10), xgap=1, ygap=1,
                               colorbar=dict(title="% of events" if share else "events", thickness=12, len=0.6),
                               hovertemplate="zone centre (%{x:.0f}, %{y:.0f}): %{text}<extra></extra>"))
    draw_pitch(fig, lines_on_top=True)
    attack_arrow(fig)
    fig.update_layout(title=sub(title, f"{len(d):,} located events on a {nx} × {ny} grid · each cell shows share and "
                                       f"(count) · empty cells are true zeros for this selection"), height=540)
    return fig


def convex_hull(ev: pd.DataFrame | None, title: str, central_share: float = 0.9) -> go.Figure:
    """Convex hull of the central share of event locations: an observed event footprint, not a playing area.

    Points are ranked by distance from the median location and the outermost ``1 - central_share`` are left out
    of the hull (they are still drawn) so a single stray action does not define the shape.
    """
    from scipy.spatial import ConvexHull, QhullError

    d, msg = _located(ev)
    if msg:
        return _empty(msg, title)
    if len(d) < 8:
        return _empty(f"A hull needs at least 8 located events (selection has {len(d)}).", title)
    pts = d[["x", "y"]].to_numpy(float)
    centre = np.median(pts, axis=0)
    dist = np.hypot(*(pts - centre).T)
    core = pts[dist <= np.quantile(dist, central_share)]
    fig = draw_pitch()
    shown, note = _sample(d, MAX_POINTS)
    fig.add_trace(go.Scatter(x=shown["x"], y=shown["y"], mode="markers", name="event locations",
                             marker=dict(size=5, color=SLATE, opacity=0.45), hoverinfo="skip"))
    try:
        hull = ConvexHull(core)
        ring = np.append(hull.vertices, hull.vertices[0])
        fig.add_trace(go.Scatter(x=core[ring, 0], y=core[ring, 1], mode="lines", fill="toself",
                                 fillcolor="rgba(42,157,143,0.18)", line=dict(color=TEAL, width=2.5),
                                 name=f"hull of central {central_share:.0%}", hoverinfo="skip"))
        area = f" · hull area {hull.volume / (PITCH_LENGTH * PITCH_WIDTH):.0%} of the pitch"
    except QhullError:
        area = " · hull not defined (points are collinear)"
    fig.add_trace(go.Scatter(x=[centre[0]], y=[centre[1]], mode="markers", name="median location",
                             marker=dict(symbol="x", size=11, color=INK)))
    attack_arrow(fig)
    fig.update_layout(title=sub(title, f"{len(d):,} located events{note}{area} · footprint of recorded on-ball "
                                       f"events only — it says nothing about positioning off the ball"),
                      height=520, legend=dict(orientation="h", y=-0.05))
    return fig


def period_split(ev: pd.DataFrame | None, title: str) -> go.Figure:
    """Zone-share heatmaps for the first and second half side by side (same attacking direction)."""
    d, msg = _located(ev)
    if msg:
        return _empty(msg, title)
    if "period" not in d.columns:
        return _empty("Required field not available: period", title)
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.04,
                        subplot_titles=[f"First half (n = {int((d['period'] == 1).sum()):,})",
                                        f"Second half (n = {int((d['period'] == 2).sum()):,})"])
    for c, p in enumerate((1, 2), 1):
        g = d[d["period"] == p]
        if len(g):
            fig.add_trace(heatmap_layer(g, row=1, col=c, showscale=c == 2), 1, c)
        draw_pitch(fig, row=1, col=c, lines_on_top=True)
    fig.update_layout(title=sub(title, "share of the half's located events per zone · both halves are shown attacking "
                                       "left to right (source coordinates are already normalised per team)"),
                      height=420)
    return fig


def pair_heatmaps(ev_a: pd.DataFrame | None, ev_b: pd.DataFrame | None, name_a: str, name_b: str, title: str
                  ) -> go.Figure:
    """Zone-share heatmaps of two selections side by side (team vs opponent, home vs away, ...)."""
    a, msg_a = _located(ev_a)
    b, msg_b = _located(ev_b)
    if msg_a and msg_b:
        return _empty(msg_a, title)
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.04,
                        subplot_titles=[f"{name_a} (n = {0 if a is None else len(a):,})",
                                        f"{name_b} (n = {0 if b is None else len(b):,})"])
    for c, g in enumerate((a, b), 1):
        if g is not None and len(g):
            fig.add_trace(heatmap_layer(g, row=1, col=c, showscale=c == 2), 1, c)
        draw_pitch(fig, row=1, col=c, lines_on_top=True)
    fig.update_layout(title=sub(title, "share of each selection's located events per zone · both panels attack left "
                                       "to right · shares are within-panel, so colours compare shape, not volume"),
                      height=420)
    return fig


LANES = ["Left wing", "Left half-space", "Centre", "Right half-space", "Right wing"]
THIRDS = ["Defensive third", "Middle third", "Attacking third"]


def progression_lanes(passes: pd.DataFrame | None, title: str) -> go.Figure:
    """Progressive passes by the lane and third they start from (5 lanes x 3 thirds)."""
    d, msg = _located(passes, need_end=True)
    if msg:
        return _empty(msg, title)
    lane = np.clip((d["y"].to_numpy(float) / 80 * 5).astype(int), 0, 4)
    third = np.clip((d["x"].to_numpy(float) / 120 * 3).astype(int), 0, 2)
    grid = np.zeros((5, 3), dtype=int)
    np.add.at(grid, (lane, third), 1)
    gain = pd.Series((d["end_x"] - d["x"]).to_numpy(float)).groupby(lane).mean().reindex(range(5))
    fig = go.Figure(go.Heatmap(z=grid, x=THIRDS, y=LANES, colorscale=SEQ_SCALE, text=grid, texttemplate="%{text}",
                               xgap=3, ygap=3, colorbar=dict(title="passes", thickness=12),
                               hovertemplate="%{y} · %{x}: %{z} passes<extra></extra>"))
    for i, g in enumerate(gain):
        if pd.notna(g):
            fig.add_annotation(x=2.62, y=i, text=f"avg +{g:.0f}", showarrow=False, font=dict(size=10, color=MUTED),
                               xref="x", yref="y", xanchor="left")
    fig.update_layout(title=sub(title, f"{len(d):,} passes · lanes are fifths of the pitch width as seen attacking left "
                                       f"to right (y = 0 is the left touchline) · right margin = mean x-gain in pitch "
                                       f"units" + (" · the defensive third is empty because progressive passes start at x ≥ 48 by "
                                                  "definition" if grid[:, 0].sum() == 0 else "")),
                      xaxis=dict(range=[-0.5, 3.1]), yaxis=dict(autorange="reversed"), height=440, margin=dict(l=130))
    return fig


def zone_transitions(passes: pd.DataFrame | None, title: str) -> go.Figure:
    """Sankey of completed passes between thirds x (wide / central) zones: an explicit start-to-end transition."""
    d, msg = _located(passes, need_end=True)
    if msg:
        return _empty(msg, title)

    def zone(x: pd.Series, y: pd.Series) -> np.ndarray:
        third = np.clip((x.to_numpy(float) / 120 * 3).astype(int), 0, 2)
        wide = ((y.to_numpy(float) < 80 / 3) | (y.to_numpy(float) > 160 / 3)).astype(int)
        return third * 2 + wide

    names = [f"{t} · {w}" for t in ("Def", "Mid", "Att") for w in ("central", "wide")]
    z0, z1 = zone(d["x"], d["y"]), zone(d["end_x"], d["end_y"])
    tab = pd.crosstab(z0, z1).reindex(index=range(6), columns=range(6), fill_value=0)
    src, tgt, val = [], [], []
    for i in range(6):
        for j in range(6):
            if tab.loc[i, j] >= max(3, 0.004 * len(d)):
                src.append(i); tgt.append(6 + j); val.append(int(tab.loc[i, j]))
    if not val:
        return _empty("Too few passes to form zone transitions.", title)
    colors = [NAVY, NAVY, TEAL, TEAL, AMBER, AMBER]
    fig = go.Figure(go.Sankey(
        node=dict(label=[f"from {n}" for n in names] + [f"to {n}" for n in names], color=colors * 2, pad=14,
                  thickness=14),
        link=dict(source=src, target=tgt, value=val, color="rgba(141,153,174,0.3)",
                  hovertemplate="%{source.label} → %{target.label}: %{value} passes<extra></extra>")))
    shown = sum(val)
    fig.update_layout(title=sub(title, f"{len(d):,} completed passes · zone = third × (central | wide third of the "
                                       f"width) · flows below {max(3, int(0.004 * len(d)))} passes hidden "
                                       f"({shown / len(d):.0%} shown)"), height=520)
    return fig


def shot_facets(shots: pd.DataFrame | None, by: str = "shot_body_part", title: str = "Shots") -> go.Figure:
    """Half-pitch shot maps split by a shot attribute (body part, shot type or outcome)."""
    msg = _missing(shots, ["x", "y", "shot_xg", "outcome", by])
    if msg:
        return _empty(msg, title)
    d = shots.dropna(subset=["x", "y"])
    if d.empty:
        return _empty("No shots for this selection.", title)
    keys = d[by].fillna("Unknown").value_counts().head(4).index.tolist()
    fig = make_subplots(rows=1, cols=len(keys), horizontal_spacing=0.02, subplot_titles=[
        f"{k}: {int((d[by].fillna('Unknown') == k).sum())} shots · "
        f"{d.loc[d[by].fillna('Unknown') == k, 'shot_xg'].sum():.1f} xG" for k in keys])
    for c, k in enumerate(keys, 1):
        g = d[d[by].fillna("Unknown") == k]
        draw_pitch(fig, row=1, col=c, half=True)
        fig.add_trace(go.Scatter(x=g["x"], y=g["y"], mode="markers", showlegend=False,
                                 marker=dict(size=5 + 34 * g["shot_xg"].fillna(0.02),
                                             color=[SHOT_COLORS.get(o, SLATE) for o in g["outcome"]], opacity=0.85,
                                             line=dict(color="white", width=0.6),
                                             symbol=["star" if o == "Goal" else "circle" for o in g["outcome"]]),
                                 customdata=np.stack([g["player_name"].fillna(""), g["shot_xg"].round(3),
                                                      g["outcome"].fillna("")], -1),
                                 hovertemplate="%{customdata[0]}<br>xG %{customdata[1]} · %{customdata[2]}"
                                               "<extra></extra>"), 1, c)
    fig.update_layout(title=sub(title, f"{len(d):,} shots split by {by.replace('_', ' ')} · marker size = StatsBomb xG · "
                                       f"star = goal · attacking half only"), height=430)
    return fig


def xt_surface(grid: Any, title: str = "Expected Threat surface") -> go.Figure:
    """The fitted xT grid on the pitch. Values are project-computed (see ``src.features.values``)."""
    if grid is None:
        return _empty("Too few actions to fit an xT grid for this selection.", title)
    xs = (np.arange(grid.nx) + 0.5) * PITCH_LENGTH / grid.nx
    ys = (np.arange(grid.ny) + 0.5) * PITCH_WIDTH / grid.ny
    fig = go.Figure(go.Heatmap(x=xs, y=ys, z=grid.grid, colorscale=SEQ_SCALE, xgap=1, ygap=1,
                               colorbar=dict(title="xT", thickness=12, len=0.6),
                               hovertemplate="cell centre (%{x:.0f}, %{y:.0f}): xT %{z:.3f}<extra></extra>"))
    draw_pitch(fig, lines_on_top=True)
    attack_arrow(fig)
    fig.update_layout(title=sub(title, f"project-computed, {grid.nx} × {grid.ny} grid · fitted in-sample on "
                                       f"{grid.n_moves:,} passes and carries and {grid.n_shots:,} shots from "
                                       f"{grid.n_matches} matches · shot value = mean StatsBomb xG per cell · "
                                       f"{'converged' if grid.converged else 'NOT converged'} after {grid.iterations} "
                                       f"iterations"), height=540)
    return fig


def possession_list(flags: pd.DataFrame, match_id: Any, team_id: Any | None = None, min_events: int = 8
                    ) -> pd.DataFrame:
    """Possessions of a match that end in a shot, with length and shot value (candidates for the sequence view)."""
    ev = flags[flags["match_id"] == match_id]
    if ev.empty:
        return pd.DataFrame()
    g = ev.groupby("possession")
    out = pd.DataFrame({"team_id": g["possession_team_id"].first(), "events": g.size(), "minute": g["minute"].min(),
                        "shots": g["shots"].sum(), "xg": g["xg"].sum(), "goal": g["goals"].sum()}).reset_index()
    out = out[(out["shots"] > 0) & (out["events"] >= min_events)]
    if team_id is not None:
        out = out[out["team_id"] == team_id]
    return out.sort_values("xg", ascending=False).reset_index(drop=True)


def sequence_animation(flags: pd.DataFrame | None, match_id: Any, possession: Any, title: str) -> go.Figure:
    """Animated ball path of one possession (passes, carries, shot) from the event stream.

    Only the ball-carrier's recorded events are known; the positions of the other 21 players are not in the
    event data and are not drawn.
    """
    msg = _missing(flags, ["match_id", "possession", "x", "y", "type"])
    if msg:
        return _empty(msg, title)
    ev = flags[(flags["match_id"] == match_id) & (flags["possession"] == possession)
               & flags["type"].isin(["Pass", "Carry", "Shot", "Dribble"])].dropna(subset=["x", "y"])
    ev = ev[ev["team_id"] == ev["possession_team_id"]].sort_values("index")
    if len(ev) < 3:
        return _empty("This possession has fewer than three located on-ball actions.", title)
    ev = ev.tail(40)
    colors = {"Pass": NAVY, "Carry": TEAL, "Shot": RED, "Dribble": AMBER}
    fig = draw_pitch()
    n_static = len(fig.data)
    fig.add_trace(go.Scatter(x=[], y=[], mode="lines", line=dict(color=SLATE, width=2), hoverinfo="skip",
                             showlegend=False))
    fig.add_trace(go.Scatter(x=[], y=[], mode="markers+text", marker=dict(size=14, color=AMBER,
                                                                         line=dict(color=INK, width=1.5)),
                             textposition="top center", showlegend=False))
    frames = []
    xs, ys = [], []
    for k, r in enumerate(ev.itertuples()):
        ex = r.end_x if pd.notna(r.end_x) else r.x
        ey = r.end_y if pd.notna(r.end_y) else r.y
        xs += [r.x, ex, None]
        ys += [r.y, ey, None]
        who = str(r.player_name).split()[-1] if isinstance(r.player_name, str) else ""
        frames.append(go.Frame(name=str(k), traces=[n_static, n_static + 1], data=[
            go.Scatter(x=list(xs), y=list(ys)),
            go.Scatter(x=[ex], y=[ey], text=[f"{who} · {r.type}"], marker=dict(color=colors.get(r.type, AMBER)))]))
    fig.frames = frames
    fig.data[n_static].update(x=frames[-1].data[0].x, y=frames[-1].data[0].y)
    fig.data[n_static + 1].update(x=frames[-1].data[1].x, y=frames[-1].data[1].y, text=frames[-1].data[1].text)
    attack_arrow(fig)
    fig.update_layout(
        title=sub(title, f"{len(ev)} on-ball actions of possession {possession} (minute {int(ev['minute'].min())}–"
                         f"{int(ev['minute'].max())}) · ball path from recorded events only; other players' positions "
                         f"are unknown"),
        height=560,
        updatemenus=[dict(type="buttons", x=0.02, y=-0.02, direction="left", showactive=False, buttons=[
            dict(label="▶ play", method="animate", args=[None, dict(frame=dict(duration=450, redraw=False),
                                                                    fromcurrent=False, transition=dict(duration=0))]),
            dict(label="■ stop", method="animate", args=[[None], dict(mode="immediate",
                                                                      frame=dict(duration=0, redraw=False))])])],
        sliders=[dict(active=len(frames) - 1, x=0.2, len=0.78, y=-0.02, currentvalue=dict(prefix="action "),
                      steps=[dict(method="animate", label=str(k + 1),
                                  args=[[str(k)], dict(mode="immediate", frame=dict(duration=0, redraw=False))])
                             for k in range(len(frames))])])
    return fig


def centroid_shape(ev: pd.DataFrame | None, title: str, min_events: int = 10) -> go.Figure:
    """Median location of each player's on-ball events: an event-location summary, not a formation.

    Players are not in these places at the same time; the chart describes where each player's recorded actions
    cluster, which is biased towards where the ball is.
    """
    msg = _missing(ev, ["x", "y", "player_id", "player_name"])
    if msg:
        return _empty(msg, title)
    d = ev.dropna(subset=["x", "y", "player_id"])
    if d.empty:
        return _empty("No located events for this selection.", title)
    g = d.groupby(["player_id", "player_name"]).agg(x=("x", "median"), y=("y", "median"), n=("x", "size"),
                                                    sx=("x", "std"), sy=("y", "std")).reset_index()
    g = g[g["n"] >= min_events]
    if g.empty:
        return _empty(f"No player has at least {min_events} located events.", title)
    fig = draw_pitch()
    for r in g.itertuples():
        fig.add_shape(type="circle", x0=r.x - r.sx / 2, x1=r.x + r.sx / 2, y0=r.y - r.sy / 2, y1=r.y + r.sy / 2,
                      line=dict(color="rgba(29,53,87,0.25)", width=1), fillcolor="rgba(29,53,87,0.06)")
    fig.add_trace(go.Scatter(x=g["x"], y=g["y"], mode="markers+text",
                             text=g["player_name"].str.split().str[-1], textposition="top center",
                             textfont=dict(size=10, color=INK),
                             marker=dict(size=9 + 16 * g["n"] / g["n"].max(), color=NAVY,
                                         line=dict(color="white", width=1.5)),
                             customdata=g["n"], hovertext=g["player_name"],
                             hovertemplate="%{hovertext}: %{customdata} events<extra></extra>", showlegend=False))
    attack_arrow(fig)
    fig.update_layout(title=sub(title, f"{len(g)} players with ≥ {min_events} located events · marker = median event "
                                       f"location, ellipse = ±½ SD · NOT simultaneous positions and NOT a formation"),
                      height=540)
    return fig


def freeze_frame(frame: dict | None, event: pd.Series | None, title: str = "StatsBomb 360 freeze frame") -> go.Figure:
    """One StatsBomb 360 freeze frame: visible players at the moment of an event and the camera's visible area.

    Only players inside the broadcast camera view are recorded, so the frame is a partial snapshot.
    """
    if not frame or not frame.get("freeze_frame"):
        return _empty("No 360 freeze frame is loaded for this event. 360 files are optional and are downloaded "
                      "per match on request.", title)
    fig = draw_pitch()
    area = frame.get("visible_area") or []
    if len(area) >= 6:
        fig.add_trace(go.Scatter(x=area[0::2], y=area[1::2], mode="lines", fill="toself",
                                 fillcolor="rgba(233,162,59,0.10)", line=dict(color=AMBER, width=1, dash="dot"),
                                 name="camera visible area", hoverinfo="skip"))
    ff = pd.DataFrame(frame["freeze_frame"])
    ff["x"] = ff["location"].str[0]
    ff["y"] = ff["location"].str[1]
    for mask, name, color, symbol in ((ff["teammate"] & ~ff["actor"], "team-mates", NAVY, "circle"),
                                      (~ff["teammate"], "opponents", RED, "circle"),
                                      (ff["actor"], "actor", AMBER, "star")):
        g = ff[mask]
        if len(g):
            fig.add_trace(go.Scatter(x=g["x"], y=g["y"], mode="markers", name=f"{name} ({len(g)})",
                                     marker=dict(size=13 if name == "actor" else 11, color=color, symbol=symbol,
                                                 line=dict(color="white", width=1.5)),
                                     text=np.where(g["keeper"], "goalkeeper", name),
                                     hovertemplate="%{text}<extra></extra>"))
    what = ""
    if event is not None:
        what = f"{event.get('type', '')} by {event.get('player_name', '')}, minute {event.get('minute', '')} · "
    attack_arrow(fig)
    fig.update_layout(title=sub(title, f"{what}{len(ff)} visible players · only players inside the camera view are "
                                       f"recorded (partial snapshot) · actor's team attacks left to right"),
                      height=540, legend=dict(orientation="h", y=-0.05))
    return fig
