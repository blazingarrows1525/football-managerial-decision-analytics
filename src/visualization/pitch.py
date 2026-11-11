"""Pitch drawing and spatial event charts (StatsBomb 120 x 80 coordinates)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Any

from src.config import PITCH_LENGTH, PITCH_WIDTH
from src.visualization.theme import AMBER, GRID, HEAT_SCALE, INK, MUTED, NAVY, PAPER, PITCH_FILL, PITCH_LINE, RED, SEQ_SCALE, SHOT_COLORS, SLATE, TEAL, _empty, _missing, add_banner


def draw_pitch(fig: go.Figure | None = None, length: float = PITCH_LENGTH, width: float = PITCH_WIDTH,
               row: int | None = None, col: int | None = None, half: bool = False,
               lines_on_top: bool = False) -> go.Figure:
    """Draw a StatsBomb-dimension pitch (120 x 80, y downwards) with standard markings.

    ``lines_on_top`` draws the markings above the data layer (for heatmaps).
    """
    fig = fig or go.Figure()
    layer = "above" if lines_on_top else "below"
    lc = dict(color=PITCH_LINE, width=1.4)
    kw = dict(row=row, col=col) if row else {}
    sx, sy = length / 120, width / 80

    def rect(x0, y0, x1, y1, fill=None, lay=None):
        fig.add_shape(type="rect", x0=x0 * sx, y0=y0 * sy, x1=x1 * sx, y1=y1 * sy, line=lc,
                      fillcolor=fill or "rgba(0,0,0,0)", layer=lay or layer, **kw)

    rect(0, 0, 120, 80, PITCH_FILL, "below")
    if lines_on_top:
        rect(0, 0, 120, 80)
    fig.add_shape(type="line", x0=60 * sx, y0=0, x1=60 * sx, y1=80 * sy, line=lc, layer=layer, **kw)
    fig.add_shape(type="circle", x0=50 * sx, y0=30 * sy, x1=70 * sx, y1=50 * sy, line=lc, layer=layer, **kw)
    for x0, x1 in ((0, 18), (102, 120)):
        rect(x0, 18, x1, 62)
    for x0, x1 in ((0, 6), (114, 120)):
        rect(x0, 30, x1, 50)
    for x0, x1 in ((-2, 0), (120, 122)):
        rect(x0, 36, x1, 44)
    spots = [(60, 40), (12, 40), (108, 40)]
    fig.add_trace(go.Scatter(x=[s[0] * sx for s in spots], y=[s[1] * sy for s in spots], mode="markers",
                             marker=dict(color=PITCH_LINE, size=4), hoverinfo="skip", showlegend=False), **kw)
    # Penalty arcs (portion of r=10 circle outside the box)
    for cx, sign in ((12, 1), (108, -1)):
        th = np.linspace(-0.927, 0.927, 30)
        xs = cx + sign * 10 * np.cos(th)
        ys = 40 + 10 * np.sin(th)
        fig.add_trace(go.Scatter(x=xs * sx, y=ys * sy, mode="lines", line=lc, hoverinfo="skip", showlegend=False),
                      **kw)
    xr = [58 * sx, 124 * sx] if half else [-4, 124 * sx]
    ax = dict(range=xr, visible=False, constrain="domain")
    ay = dict(range=[84 * sy, -4], visible=False, scaleanchor="x" if not row else None, scaleratio=1)
    if row:
        fig.update_xaxes(**ax, row=row, col=col)
        fig.update_yaxes(**ay, row=row, col=col)
    else:
        fig.update_layout(xaxis=ax, yaxis=ay, plot_bgcolor=PAPER)
    return fig


def attack_arrow(fig: go.Figure, text: str = "Attacking direction") -> None:
    fig.add_annotation(x=75, y=85.5, ax=45, ay=85.5, xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                       arrowhead=2, arrowcolor=MUTED, text="")
    fig.add_annotation(x=60, y=88, text=text, showarrow=False, font=dict(size=10, color=MUTED))


def shot_map(shots: pd.DataFrame, title: str, banner: str | None = None) -> go.Figure:
    msg = _missing(shots, ["x", "y", "outcome", "shot_xg"])
    if msg:
        return _empty(msg, title)
    s = shots.dropna(subset=["x", "y"])
    fig = draw_pitch(half=True)
    for oc, g in s.groupby("outcome"):
        fig.add_trace(go.Scatter(x=g["x"], y=g["y"], mode="markers", name=f"{oc} ({len(g)})",
                                 marker=dict(size=6 + 40 * g["shot_xg"].fillna(0.02), color=SHOT_COLORS.get(oc, SLATE),
                                             opacity=0.85, line=dict(color=INK if oc == "Goal" else "white", width=1),
                                             symbol="star" if oc == "Goal" else "circle"),
                                 customdata=np.stack([g["player_name"], g["shot_xg"].round(3), g["minute"],
                                                      g.get("shot_body_part", pd.Series("", index=g.index))], axis=-1),
                                 hovertemplate="%{customdata[0]}<br>xG %{customdata[1]} · %{customdata[3]}<br>"
                                               "minute %{customdata[2]}<extra>" + str(oc) + "</extra>"))
    fig.update_layout(title=f"{title}<br><sup>{len(s)} shots · {s['shot_xg'].sum():.2f} xG · "
                            f"{(s['outcome'] == 'Goal').sum()} goals · marker size = StatsBomb xG</sup>",
                      height=520, legend=dict(orientation="h", y=-0.05))
    return add_banner(fig, banner)


def pass_map(passes: pd.DataFrame, title: str, max_passes: int = 600, banner: str | None = None) -> go.Figure:
    msg = _missing(passes, ["x", "y", "end_x", "end_y", "outcome"])
    if msg:
        return _empty(msg, title)
    p = passes.dropna(subset=["x", "y", "end_x", "end_y"])
    sampled = len(p) > max_passes
    if sampled:
        p = p.sample(max_passes, random_state=0)
    fig = draw_pitch()
    for name, sub, color in (("Completed", p[p["outcome"].isna()], NAVY), ("Incomplete", p[p["outcome"].notna()], RED)):
        xs, ys = [], []
        for r in sub.itertuples():
            xs += [r.x, r.end_x, None]
            ys += [r.y, r.end_y, None]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=1), opacity=0.45,
                                 name=f"{name} ({len(sub)})", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=sub["end_x"], y=sub["end_y"], mode="markers", showlegend=False,
                                 marker=dict(size=4, color=color), text=sub["pass_recipient_name"],
                                 hovertemplate="to %{text}<extra></extra>"))
    attack_arrow(fig)
    note = f" (random sample of {max_passes})" if sampled else ""
    fig.update_layout(title=f"{title}{note}", height=520, legend=dict(orientation="h", y=-0.05))
    return add_banner(fig, banner)


def progressive_actions_map(flags: pd.DataFrame, title: str, banner: str | None = None) -> go.Figure:
    msg = _missing(flags, ["x", "y", "end_x", "end_y", "progressive_passes", "progressive_carries"])
    if msg:
        return _empty(msg, title)
    fig = draw_pitch()
    for name, mask, color, dash in (("Progressive passes", flags["progressive_passes"] == 1, NAVY, "solid"),
                                    ("Progressive carries", flags["progressive_carries"] == 1, AMBER, "dot")):
        sub = flags[mask]
        xs, ys = [], []
        for r in sub.itertuples():
            xs += [r.x, r.end_x, None]
            ys += [r.y, r.end_y, None]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=1.6, dash=dash), opacity=0.6,
                                 name=f"{name} ({len(sub)})", hoverinfo="skip"))
    attack_arrow(fig)
    fig.update_layout(title=f"{title}<br><sup>Project definitions: passes start outside the defending 40%; both end "
                            f">=25% closer to goal centre in the attacking 60%</sup>", height=520, legend=dict(orientation="h", y=-0.05))
    return add_banner(fig, banner)


def key_pass_map(flags: pd.DataFrame, team_id: Any, title: str) -> go.Figure:
    """Every pass that led directly to a shot; amber = assist for a goal."""
    msg = _missing(flags, ["key_passes", "assists", "x", "y", "end_x", "end_y"])
    if msg:
        return _empty(msg, title)
    kp = flags[(flags["team_id"] == team_id) & (flags["key_passes"] == 1)].dropna(subset=["x", "y", "end_x", "end_y"])
    fig = draw_pitch()
    for name, sub, color, w in (("Shot assists", kp[kp["assists"] == 0], NAVY, 1.2),
                                ("Goal assists", kp[kp["assists"] == 1], AMBER, 2.6)):
        xs, ys = [], []
        for r in sub.itertuples():
            xs += [r.x, r.end_x, None]
            ys += [r.y, r.end_y, None]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=w), opacity=0.6,
                                 name=f"{name} ({len(sub)})", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=sub["end_x"], y=sub["end_y"], mode="markers", showlegend=False,
                                 marker=dict(size=6, color=color), text=sub["player_name"],
                                 hovertemplate="from %{text}<extra></extra>"))
    attack_arrow(fig)
    fig.update_layout(title=f"{title}<br><sup>{len(kp)} key passes · origin → shot location</sup>", height=520,
                      legend=dict(orientation="h", y=-0.05))
    return fig


def pass_flow_matrix(flags: pd.DataFrame, team_id: Any, title: str) -> go.Figure:
    """Completed passes between 9 pitch zones (thirds × lanes): how the team moves the ball."""
    msg = _missing(flags, ["x", "y", "end_x", "end_y", "passes_completed"])
    if msg:
        return _empty(msg, title)
    p = flags[(flags["team_id"] == team_id) & (flags["passes_completed"] == 1)].dropna(subset=["x", "y", "end_x", "end_y"])
    if p.empty:
        return _empty("No completed passes.", title)
    z0 = np.digitize(p["x"], [40, 80]) * 3 + np.digitize(p["y"], [80 / 3, 160 / 3])
    z1 = np.digitize(p["end_x"], [40, 80]) * 3 + np.digitize(p["end_y"], [80 / 3, 160 / 3])
    labs = [f"{t}-{l}" for t in ("Def", "Mid", "Att") for l in ("Left", "Centre", "Right")]
    mat = pd.crosstab(pd.Categorical(z0, categories=range(9)), pd.Categorical(z1, categories=range(9)),
                      dropna=False).to_numpy()
    share = mat / mat.sum() * 100
    fwd = (np.digitize(p["end_x"], [40, 80]) > np.digitize(p["x"], [40, 80])).mean()
    fig = go.Figure(go.Heatmap(z=share, x=labs, y=labs, colorscale=SEQ_SCALE, text=np.round(share, 1),
                               texttemplate="%{text}", xgap=2, ygap=2, colorbar=dict(title="% of passes", thickness=12),
                               hovertemplate="from %{y} to %{x}: %{z:.1f}%<extra></extra>"))
    fig.update_layout(title=f"{title}<br><sup>{len(p):,} completed passes · {fwd:.0%} move the ball into a more "
                            f"advanced third · lanes as seen attacking left → right</sup>",
                      xaxis_title="to zone", yaxis=dict(title="from zone", autorange="reversed"), height=560,
                      plot_bgcolor="white", margin=dict(l=120))
    return fig


def pass_destination_density(flags: pd.DataFrame, player_id: Any, title: str) -> go.Figure:
    """Kernel-style density contour of where a player's completed passes end."""
    p = flags[(flags["player_id"] == player_id) & (flags["passes_completed"] == 1)].dropna(subset=["end_x", "end_y"]) \
        if flags is not None and "player_id" in flags else None
    if p is None or p.empty:
        return _empty("No passes.", title)
    fig = go.Figure(go.Histogram2dContour(x=p["end_x"], y=p["end_y"], colorscale=HEAT_SCALE, ncontours=14,
                                          contours=dict(coloring="fill", showlines=False), showscale=False,
                                          xbins=dict(start=0, end=120, size=6), ybins=dict(start=0, end=80, size=6),
                                          hoverinfo="skip", opacity=0.9))
    draw_pitch(fig, lines_on_top=True)
    attack_arrow(fig)
    fig.update_layout(title=f"{title}<br><sup>{len(p):,} completed passes · density of end locations</sup>", height=520)
    return fig


def shot_density_pair(flags: pd.DataFrame, team_id: Any, match_ids: list, team: str) -> go.Figure:
    """Side-by-side density contours of shots taken and shots conceded (each in its own attacking frame)."""
    s = flags[(flags["type"] == "Shot") & flags["match_id"].isin(match_ids)].dropna(subset=["x", "y"]) \
        if flags is not None and "type" in flags else None
    if s is None or s.empty:
        return _empty("No shots.", "Shot density")
    fig = make_subplots(rows=1, cols=2, subplot_titles=(f"{team} shots", "Shots conceded"), horizontal_spacing=0.04)
    for col, sub in ((1, s[s["team_id"] == team_id]), (2, s[s["team_id"] != team_id])):
        fig.add_trace(go.Histogram2dContour(x=sub["x"], y=sub["y"], colorscale=HEAT_SCALE, ncontours=12,
                                            contours=dict(coloring="fill", showlines=False), showscale=False,
                                            xbins=dict(start=60, end=120, size=4), ybins=dict(start=0, end=80, size=4),
                                            hoverinfo="skip"), row=1, col=col)
        gl = sub[sub["outcome"] == "Goal"]
        fig.add_trace(go.Scatter(x=gl["x"], y=gl["y"], mode="markers", showlegend=False,
                                 marker=dict(symbol="star", size=9, color=AMBER, line=dict(color=INK, width=0.6)),
                                 text=gl["player_name"], hovertemplate="Goal: %{text}<extra></extra>"), row=1, col=col)
        draw_pitch(fig, row=1, col=col, half=True, lines_on_top=True)
    fig.update_layout(title=f"{team}: where shots come from — density of attempts, stars = goals", height=480)
    return fig


def heatmap_layer(ev: pd.DataFrame, bins: tuple[int, int] = (12, 8), row: int | None = None,
                  col: int | None = None, showscale: bool = True) -> go.Heatmap:
    """Zone-share heatmap trace (percent of actions per zone) on the 120 x 80 frame."""
    d = ev.dropna(subset=["x", "y"])
    h, xe, ye = np.histogram2d(d["x"].clip(0, 119.99), d["y"].clip(0, 79.99), bins=bins, range=[[0, 120], [0, 80]])
    share = h / max(h.sum(), 1) * 100
    return go.Heatmap(x=(xe[:-1] + xe[1:]) / 2, y=(ye[:-1] + ye[1:]) / 2, z=share.T, customdata=h.T,
                      colorscale=HEAT_SCALE, zmin=0, zsmooth="best", showscale=showscale,
                      colorbar=dict(title="% of<br>actions", thickness=12, len=0.6),
                      hovertemplate="zone centre x=%{x:.0f}, y=%{y:.0f}<br>%{z:.1f}% of actions "
                                    "(%{customdata:.0f})<extra></extra>")


def action_heatmap(ev: pd.DataFrame, title: str, bins: tuple[int, int] = (12, 8),
                   banner: str | None = None) -> go.Figure:
    """Where a player or team performs the selected actions (share of actions per zone)."""
    msg = _missing(ev, ["x", "y"])
    if msg or ev.dropna(subset=["x", "y"]).empty:
        return _empty(msg or "No located actions for this selection.", title)
    fig = go.Figure(heatmap_layer(ev, bins))
    draw_pitch(fig, lines_on_top=True)
    attack_arrow(fig)
    n = int(ev.dropna(subset=["x", "y"]).shape[0])
    fig.update_layout(title=f"{title}<br><sup>{n:,} located actions · {bins[0]}×{bins[1]} zones · colour = share "
                            f"of actions</sup>", height=520)
    return add_banner(fig, banner)


def pass_direction_rose(passes: pd.DataFrame, title: str, sectors: int = 16,
                        banner: str | None = None) -> go.Figure:
    """Polar histogram of pass directions (forward = up), coloured by completion rate."""
    msg = _missing(passes, ["x", "y", "end_x", "end_y", "outcome"])
    if msg:
        return _empty(msg, title)
    p = passes.dropna(subset=["x", "y", "end_x", "end_y"])
    if p.empty:
        return _empty("No located passes.", title)
    ang = np.degrees(np.arctan2(p["end_y"] - p["y"], p["end_x"] - p["x"])) % 360
    width = 360 / sectors
    sec = ((ang + width / 2) // width % sectors).astype(int)
    df = pd.DataFrame({"sec": sec, "ok": p["outcome"].isna().to_numpy()})
    g = df.groupby("sec").agg(n=("ok", "size"), comp=("ok", "mean")).reindex(range(sectors), fill_value=0)
    fig = go.Figure(go.Barpolar(r=g["n"], theta=g.index * width, width=[width * 0.95] * sectors,
                                marker=dict(color=g["comp"] * 100, colorscale=[[0, RED], [0.5, AMBER], [1, TEAL]],
                                            cmin=50, cmax=100, colorbar=dict(title="completion %", thickness=12),
                                            line=dict(color="white", width=1)),
                                customdata=g["comp"] * 100,
                                hovertemplate="%{theta}°: %{r} passes, %{customdata:.0f}% completed<extra></extra>"))
    fig.update_layout(title=f"{title}<br><sup>{len(p)} passes · forward = up, right flank = right</sup>",
                      polar=dict(bgcolor=PAPER, angularaxis=dict(rotation=90, direction="clockwise",
                                                                  tickvals=[0, 90, 180, 270],
                                                                  ticktext=["Forward", "Right", "Back", "Left"],
                                                                  gridcolor=GRID),
                                 radialaxis=dict(gridcolor=GRID, showticklabels=False)),
                      height=480, showlegend=False)
    return add_banner(fig, banner)
