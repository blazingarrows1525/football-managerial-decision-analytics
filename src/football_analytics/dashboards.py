"""Composite one-screen dashboards (KPI cards + linked panels) for presentation and the demo.

Each dashboard is a single Plotly figure built from the same tables as the individual
charts, so every number is traceable. Missing inputs return an empty-state figure.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .advanced_visuals import heatmap_layer
from .config import Config, ROLE_LABEL
from .player_analysis import label, radar_metrics
from .visualizations import (AMBER, GRID, INK, MUTED, NAVY, PAPER, RED, RESULT_COLORS, SHOT_COLORS, SLATE,
                             STATE_COLORS, TEAL, _empty, _missing, _rows, add_banner, draw_pitch)

KPI_NUM = dict(font=dict(size=30, color=NAVY))
KPI_TITLE = dict(font=dict(size=12, color=MUTED))


def _kpi(fig: go.Figure, value: float, title: str, row: int, col: int, fmt: str = ",.0f", prefix: str = "",
         suffix: str = "") -> None:
    if fmt.startswith("+"):  # the indicator ignores d3's sign flag: add "+" ourselves
        fmt = fmt[1:]
        if pd.notna(value) and value > 0:
            prefix = "+" + prefix
    fig.add_trace(go.Indicator(mode="number", value=float(value) if pd.notna(value) else None,
                               number=dict(valueformat=fmt, prefix=prefix, suffix=suffix, **KPI_NUM),
                               title=dict(text=title, **KPI_TITLE)), row=row, col=col)


# ---------------------------------------------------------------------------
# Season dashboard
# ---------------------------------------------------------------------------
def season_dashboard(team_stats: pd.DataFrame, xpts: pd.DataFrame, team: str, banner: str | None = None
                     ) -> go.Figure:
    """KPIs, points vs expected-points race, and match-by-match xG bars."""
    t = _rows(team_stats, "team_name", team)
    msg = _missing(t, ["match_date", "points", "goals_for", "goals_against", "xg", "xg_against", "result"])
    if msg:
        return _empty(msg, f"Season dashboard — {team}")
    t = t.sort_values("match_date").reset_index(drop=True)
    x = _rows(xpts, "team_name", team)
    x = x.sort_values("match_date") if x is not None and len(x) else None
    rec = t["result"].value_counts().reindex(["W", "D", "L"], fill_value=0)
    fig = make_subplots(rows=3, cols=5, row_heights=[0.16, 0.44, 0.40], vertical_spacing=0.1,
                        specs=[[{"type": "indicator"}] * 5, [{"colspan": 5}, None, None, None, None],
                               [{"colspan": 5, "secondary_y": True}, None, None, None, None]],
                        subplot_titles=["", "", "", "", "", "Points race: actual vs shot-based expected points",
                                        "Chance creation and concession per match"])
    _kpi(fig, t["points"].sum(), f"Points · W{rec['W']} D{rec['D']} L{rec['L']}", 1, 1)
    _kpi(fig, t["goals_for"].sum() - t["goals_against"].sum(),
         f"Goal difference ({t['goals_for'].sum()}-{t['goals_against'].sum()})", 1, 2, "+,.0f")
    _kpi(fig, t["xg"].mean() - t["xg_against"].mean(), "xG difference per match", 1, 3, "+.2f")
    _kpi(fig, t["possession_proxy_pct"].mean(), "Possession proxy", 1, 4, ".1f", suffix="%")
    if x is not None:
        _kpi(fig, t["points"].sum() - x["xpts"].sum(), f"Points vs xPts ({x['xpts'].sum():.1f})", 1, 5, "+.1f")
    else:
        _kpi(fig, t["field_tilt_pct"].mean(), "Field tilt", 1, 5, ".1f", suffix="%")
    md = np.arange(1, len(t) + 1)
    fig.add_trace(go.Scatter(x=md, y=t["points"].cumsum(), name="Actual points", mode="lines+markers",
                             line=dict(color=NAVY, width=3), marker=dict(color=t["result"].map(RESULT_COLORS), size=8,
                                                                         line=dict(color="white", width=1)),
                             customdata=np.stack([t["opponent"], t["goals_for"], t["goals_against"]], axis=-1),
                             hovertemplate="match %{x} vs %{customdata[0]} (%{customdata[1]}-%{customdata[2]})<br>"
                                           "%{y} points<extra></extra>"), row=2, col=1)
    if x is not None:
        fig.add_trace(go.Scatter(x=md, y=x["xpts"].cumsum().values, name="Expected points (xPts)", mode="lines",
                                 line=dict(color=AMBER, width=2.5, dash="dash"),
                                 hovertemplate="match %{x}: %{y:.1f} xPts<extra></extra>"), row=2, col=1)
    fig.add_trace(go.Scatter(x=md, y=md * 2, name="2 points/match pace", mode="lines",
                             line=dict(color=MUTED, width=1, dash="dot"), hoverinfo="skip"), row=2, col=1)
    fig.add_trace(go.Bar(x=md, y=t["xg"], name="xG for", marker_color=NAVY, opacity=0.85,
                         hovertemplate="match %{x}: %{y:.2f} xG for<extra></extra>"), row=3, col=1)
    fig.add_trace(go.Bar(x=md, y=-t["xg_against"], name="xG against", marker_color=RED, opacity=0.8,
                         customdata=t["xg_against"], hovertemplate="match %{x}: %{customdata:.2f} xG against"
                                                                   "<extra></extra>"), row=3, col=1)
    fig.add_trace(go.Scatter(x=md, y=t["goal_diff"], name="Goal difference", mode="markers",
                             marker=dict(symbol="diamond", size=9, color=AMBER, line=dict(color=INK, width=1))),
                  row=3, col=1, secondary_y=True)
    fig.update_xaxes(title_text="Match number (chronological)", row=3, col=1)
    fig.update_yaxes(title_text="cumulative points", row=2, col=1)
    fig.update_yaxes(title_text="xG (against below 0)", row=3, col=1, secondary_y=False)
    fig.update_yaxes(title_text="goal difference", row=3, col=1, secondary_y=True, showgrid=False)
    fig.update_layout(title=f"<b>{team}</b> — season dashboard ({len(t)} matches, "
                            f"{t['match_date'].min():%b %Y} – {t['match_date'].max():%b %Y})",
                      barmode="relative", height=900, legend=dict(orientation="h", y=-0.06),
                      margin=dict(t=110))
    return add_banner(fig, banner)


# ---------------------------------------------------------------------------
# Player dashboard
# ---------------------------------------------------------------------------
def player_dashboard(season_pct: pd.DataFrame, pms: pd.DataFrame, flags: pd.DataFrame, player_id: Any,
                     config: Config, banner: str | None = None) -> go.Figure:
    """Player card: KPIs, percentile radar, action heatmap and per-match output."""
    s = _rows(season_pct, "player_id", player_id)
    msg = _missing(s, ["player_name", "minutes_played", "primary_role"])
    if msg:
        return _empty(msg, "Player dashboard")
    r = s.sort_values("minutes_played", ascending=False).iloc[0]
    games = pms[pms["player_id"] == player_id].sort_values("match_date")
    fig = make_subplots(rows=3, cols=4, row_heights=[0.14, 0.50, 0.36], vertical_spacing=0.09,
                        horizontal_spacing=0.06,
                        specs=[[{"type": "indicator"}] * 4,
                               [{"type": "polar", "colspan": 2}, None, {"colspan": 2}, None],
                               [{"colspan": 4, "secondary_y": True}, None, None, None]],
                        subplot_titles=["", "", "", "", "Percentile profile vs benchmark", "Where he acts (on-ball "
                                        "actions)", "Match by match: minutes and attacking output"])
    _kpi(fig, r["minutes_played"], f"Minutes · {int(r['starts'])} starts / {int(r['appearances'])} apps", 1, 1)
    _kpi(fig, r["goals"], f"Goals (xG {r['xg']:.1f})", 1, 2)
    _kpi(fig, r["assists"], f"Assists (xA {r['xa']:.1f})", 1, 3)
    _kpi(fig, r.get("key_passes_p90", np.nan), "Key passes per 90", 1, 4, ".2f")
    metrics = [m for m in radar_metrics(r["primary_role"], config) if f"{m}_pct" in s.columns]
    theta = [label(m) for m in metrics]
    vals = [float(r[f"{m}_pct"]) if pd.notna(r[f"{m}_pct"]) else 0.0 for m in metrics]
    fig.add_trace(go.Scatterpolar(r=[50] * (len(vals) + 1), theta=theta + theta[:1], showlegend=False,
                                  line=dict(color=MUTED, dash="dot"), hoverinfo="skip"), row=2, col=1)
    fig.add_trace(go.Scatterpolar(r=vals + vals[:1], theta=theta + theta[:1], fill="toself", showlegend=False,
                                  line=dict(color=NAVY, width=2.5), fillcolor="rgba(29,53,87,0.25)",
                                  hovertemplate="%{theta}: %{r:.0f}th pct<extra></extra>"), row=2, col=1)
    ev = flags[(flags["player_id"] == player_id) & flags["touches"].astype(bool)]
    if len(ev):
        fig.add_trace(heatmap_layer(ev, (12, 8), showscale=False), row=2, col=3)
    draw_pitch(fig, row=2, col=3, lines_on_top=True)
    if len(games):
        lab = [f"{d:%d %b} {o[:10]}" for d, o in zip(games["match_date"], games["opponent"])]
        fig.add_trace(go.Bar(x=lab, y=games["minutes_played"], name="Minutes", marker_color="#d9d4c7",
                             hovertemplate="%{x}: %{y:.0f} min<extra></extra>"), row=3, col=1)
        fig.add_trace(go.Scatter(x=lab, y=games["xg"] + games["xa"], name="xG + xA", mode="lines+markers",
                                 line=dict(color=TEAL, width=2.5),
                                 hovertemplate="%{x}: %{y:.2f} xG+xA<extra></extra>"), row=3, col=1, secondary_y=True)
        g = games[games["goals"] > 0]
        fig.add_trace(go.Scatter(x=[f"{d:%d %b} {o[:10]}" for d, o in zip(g["match_date"], g["opponent"])],
                                 y=g["xg"] + g["xa"], mode="markers", name="Scored", marker=dict(
                                     symbol="star", size=13, color=AMBER, line=dict(color=INK, width=1))),
                      row=3, col=1, secondary_y=True)
    fig.update_xaxes(tickangle=-60, tickfont=dict(size=8), row=3, col=1)
    fig.update_yaxes(title_text="minutes", row=3, col=1, secondary_y=False)
    fig.update_yaxes(title_text="xG + xA", row=3, col=1, secondary_y=True, showgrid=False)
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75], gridcolor=GRID),
                                 angularaxis=dict(gridcolor=GRID, tickfont=dict(size=10)), bgcolor=PAPER),
                      title=f"<b>{r['player_name']}</b> — {r['team_name']} · {r.get('primary_position')} "
                            f"({ROLE_LABEL.get(r['primary_role'], r['primary_role'])}) · {r['coverage_label']} · "
                            f"benchmark {r.get('benchmark_group')} (n={int(r['benchmark_n'])})",
                      height=980, legend=dict(orientation="h", y=-0.12), margin=dict(t=110))
    return add_banner(fig, banner)


# ---------------------------------------------------------------------------
# Match dashboard
# ---------------------------------------------------------------------------
def match_dashboard(flags: pd.DataFrame, goals: pd.DataFrame, matches: pd.DataFrame, match_id: Any,
                    bucket: float = 5.0, banner: str | None = None) -> go.Figure:
    """Score header, momentum, cumulative xG and both teams' shot maps for one match."""
    m = _rows(matches, "match_id", match_id)
    ev = _rows(flags, "match_id", match_id)
    msg = _missing(m, ["home_team", "away_team", "home_score", "away_score"]) or _missing(
        ev, ["elapsed_min", "team_name", "xg"])
    if msg:
        return _empty(msg, "Match dashboard")
    m = m.iloc[0]
    home, away = m["home_team"], m["away_team"]
    fig = make_subplots(rows=3, cols=2, row_heights=[0.3, 0.3, 0.4], vertical_spacing=0.1, horizontal_spacing=0.05,
                        specs=[[{"colspan": 2}, None], [{"colspan": 2}, None], [{}, {}]],
                        subplot_titles=[f"Momentum: xG per {bucket:.0f} min ({home} up, {away} down)",
                                        "Cumulative xG", f"{home} shots", f"{away} shots"])
    ev = ev.assign(b=(ev["elapsed_min"] // bucket) * bucket)
    agg = ev.groupby(["b", "team_name"])["xg"].sum().unstack(fill_value=0)
    bx = agg.index.to_numpy() + bucket / 2
    for team, sign, c in ((home, 1, NAVY), (away, -1, RED)):
        y = agg[team] if team in agg else pd.Series(0, index=agg.index)
        fig.add_trace(go.Bar(x=bx, y=sign * y, marker_color=c, name=team, width=bucket * 0.85, customdata=y,
                             hovertemplate="%{x:.0f}': %{customdata:.2f} xG<extra>" + team + "</extra>"), row=1, col=1)
    shots = ev[ev["type"] == "Shot"].sort_values("elapsed_min")
    for team, c in ((home, NAVY), (away, RED)):
        s = shots[shots["team_name"] == team]
        fig.add_trace(go.Scatter(x=np.r_[0, s["elapsed_min"]], y=np.r_[0, s["shot_xg"].fillna(0).cumsum()],
                                 mode="lines", line_shape="hv", line=dict(color=c, width=2.5), showlegend=False,
                                 hovertemplate="%{x:.0f}': %{y:.2f} cumulative xG<extra>" + team + "</extra>"),
                      row=2, col=1)
        gl = s[s["outcome"] == "Goal"]
        fig.add_trace(go.Scatter(x=gl["elapsed_min"], y=s["shot_xg"].fillna(0).cumsum()[gl.index], mode="markers",
                                 marker=dict(symbol="star", size=14, color=AMBER, line=dict(color=INK, width=1)),
                                 text=gl["player_name"], hovertemplate="Goal: %{text}<extra></extra>",
                                 showlegend=False), row=2, col=1)
    for col, team in ((1, home), (2, away)):
        draw_pitch(fig, row=3, col=col, half=True)
        s = shots[shots["team_name"] == team].dropna(subset=["x", "y"])
        fig.add_trace(go.Scatter(x=s["x"], y=s["y"], mode="markers", showlegend=False,
                                 marker=dict(size=6 + 40 * s["shot_xg"].fillna(0.02),
                                             color=[SHOT_COLORS.get(o, SLATE) for o in s["outcome"]],
                                             symbol=["star" if o == "Goal" else "circle" for o in s["outcome"]],
                                             line=dict(color="white", width=1), opacity=0.9),
                                 customdata=np.stack([s["player_name"], s["shot_xg"].round(3), s["outcome"]], axis=-1)
                                 if len(s) else None,
                                 hovertemplate="%{customdata[0]}<br>xG %{customdata[1]} · %{customdata[2]}"
                                               "<extra></extra>"), row=3, col=col)
    xg = ev.groupby("team_name")["xg"].sum()
    fig.update_xaxes(title_text="Elapsed playing time (min)", row=2, col=1)
    fig.update_layout(title=f"<b>{home} {int(m['home_score'])} – {int(m['away_score'])} {away}</b> · "
                            f"{m['match_date']:%d %b %Y} · xG {xg.get(home, 0):.2f} – {xg.get(away, 0):.2f}"
                            + (f" · {m['stadium']}" if pd.notna(m.get("stadium")) else ""),
                      barmode="relative", height=1080, legend=dict(orientation="h", y=1.04, x=1, xanchor="right"),
                      margin=dict(t=120))
    return add_banner(fig, banner)


# ---------------------------------------------------------------------------
# Substitution dashboard
# ---------------------------------------------------------------------------
def substitution_dashboard(subs: pd.DataFrame, team: str, bands: list[dict], banner: str | None = None
                           ) -> go.Figure:
    """KPIs, timing × game state, most-used substitutes, and every change on a minute × score grid."""
    s = _rows(subs, "team_name", team)
    msg = _missing(s, ["minute", "timing_band", "game_state", "player_on_name", "goal_diff", "match_id"])
    if msg:
        return _empty(msg, f"Substitution dashboard — {team}")
    order = [b["label"] for b in bands]
    first = s.sort_values("index").groupby("match_id").first() if "index" in s else s.groupby("match_id").first()
    fig = make_subplots(rows=3, cols=4, row_heights=[0.16, 0.42, 0.42], vertical_spacing=0.11,
                        horizontal_spacing=0.08,
                        specs=[[{"type": "indicator"}] * 4, [{"colspan": 2}, None, {"colspan": 2}, None],
                               [{"colspan": 4}, None, None, None]],
                        subplot_titles=["", "", "", "", "Timing band × game state", "Most-used substitutes",
                                        "Every substitution: minute vs score difference at the change"])
    _kpi(fig, len(s) / s["match_id"].nunique(), "Substitutions per match", 1, 1, ".2f")
    _kpi(fig, s["minute"].median(), "Median substitution minute", 1, 2, ".0f", suffix="'")
    _kpi(fig, first["minute"].median(), "Median first substitution", 1, 3, ".0f", suffix="'")
    _kpi(fig, 100 * s["like_for_like"].mean() if "like_for_like" in s else np.nan, "Like-for-like role changes",
         1, 4, ".0f", suffix="%")
    for st in ["leading", "drawing", "trailing"]:
        c = s[s["game_state"] == st]["timing_band"].value_counts().reindex(order, fill_value=0)
        fig.add_trace(go.Bar(x=order, y=c.values, name=st, marker_color=STATE_COLORS[st],
                             hovertemplate="%{x}: %{y} subs while " + st + "<extra></extra>"), row=2, col=1)
    on_col = "player_on_display" if "player_on_display" in s else "player_on_name"
    off_col = "player_off_display" if "player_off_display" in s else "player_off_name"
    top = s[on_col].value_counts().head(10).iloc[::-1]
    fig.add_trace(go.Bar(y=list(top.index), x=top.values, orientation="h",
                         marker_color=TEAL, showlegend=False, text=top.values, textposition="outside",
                         customdata=top.index, hovertemplate="%{customdata}: %{x} times<extra></extra>"),
                  row=2, col=3)
    rng = np.random.default_rng(0)
    jit = rng.uniform(-0.18, 0.18, len(s))
    fig.add_trace(go.Scatter(x=s["minute"], y=s["goal_diff"] + jit, mode="markers", showlegend=False,
                             marker=dict(size=9, color=s["game_state"].map(STATE_COLORS), opacity=0.75,
                                         symbol=np.where(s.get("sub_reason", "") == "Injury", "x", "circle"),
                                         line=dict(color="white", width=0.5)),
                             customdata=np.stack([s[off_col], s[on_col],
                                                  s.get("sub_reason", pd.Series("", index=s.index))], axis=-1),
                             hovertemplate="%{x}': OFF %{customdata[0]} → ON %{customdata[1]} (%{customdata[2]})"
                                           "<extra></extra>"), row=3, col=1)
    fig.update_yaxes(title_text="goal difference (team view)", dtick=1, row=3, col=1)
    fig.update_xaxes(title_text="clock minute (× = injury change)", row=3, col=1)
    fig.update_layout(title=f"<b>{team}</b> — substitution dashboard ({len(s)} changes in "
                            f"{s['match_id'].nunique()} matches)", barmode="stack", height=950,
                      legend=dict(orientation="v", x=0.01, y=0.72, yanchor="top", bgcolor="rgba(255,255,255,0.8)"),
                      margin=dict(t=110))
    return add_banner(fig, banner)
