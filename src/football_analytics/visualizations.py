"""Plotly visualisations with a consistent editorial sports-analytics theme.

Every public function:
* checks its required columns and returns a readable "no data" figure instead of raising;
* never fills missing values with fabricated observations;
* uses StatsBomb 120 x 80 coordinates (y = 0 at the top touchline, attack left -> right).
"""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from .config import PITCH_LENGTH, PITCH_WIDTH, ROLE_LABEL
from .player_analysis import label

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
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


register_theme()


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


# ---------------------------------------------------------------------------
# Pitch
# ---------------------------------------------------------------------------
def draw_pitch(fig: go.Figure | None = None, length: float = PITCH_LENGTH, width: float = PITCH_WIDTH,
               row: int | None = None, col: int | None = None, half: bool = False) -> go.Figure:
    """Draw a StatsBomb-dimension pitch (120 x 80, y downwards) with standard markings."""
    fig = fig or go.Figure()
    lc = dict(color=PITCH_LINE, width=1.4)
    kw = dict(row=row, col=col) if row else {}
    sx, sy = length / 120, width / 80

    def rect(x0, y0, x1, y1, fill=None):
        fig.add_shape(type="rect", x0=x0 * sx, y0=y0 * sy, x1=x1 * sx, y1=y1 * sy, line=lc,
                      fillcolor=fill or "rgba(0,0,0,0)", layer="below", **kw)

    rect(0, 0, 120, 80, PITCH_FILL)
    fig.add_shape(type="line", x0=60 * sx, y0=0, x1=60 * sx, y1=80 * sy, line=lc, layer="below", **kw)
    fig.add_shape(type="circle", x0=50 * sx, y0=30 * sy, x1=70 * sx, y1=50 * sy, line=lc, layer="below", **kw)
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


# ---------------------------------------------------------------------------
# 1. Coverage cards
# ---------------------------------------------------------------------------
def coverage_cards(scale: pd.DataFrame, banner: str | None = None) -> go.Figure:
    msg = _missing(scale, ["measure", "value"])
    if msg:
        return _empty(msg, "Dataset coverage")
    wanted = ["Matches parsed", "Teams", "Players (unique IDs in squads)", "Events parsed", "Substitutions",
              "Goals (periods 1-4)", "Raw data size (MB)", "Raw JSON files"]
    d = scale.set_index("measure")["value"]
    items = [(w, d[w]) for w in wanted if w in d.index]
    n = len(items)
    cols = 4
    rows = int(np.ceil(n / cols))
    fig = make_subplots(rows=rows, cols=cols, specs=[[{"type": "indicator"}] * cols] * rows,
                        vertical_spacing=0.25)
    for i, (k, v) in enumerate(items):
        fig.add_trace(go.Indicator(mode="number", value=float(v), title=dict(text=k, font=dict(size=13, color=MUTED)),
                                   number=dict(font=dict(size=34, color=NAVY), valueformat=",.0f" if float(v) >= 100
                                               else ",.1f")), row=i // cols + 1, col=i % cols + 1)
    dr = d.get("Date range", "")
    fig.update_layout(title=f"Dataset coverage — {dr}", height=170 * rows + 80, margin=dict(t=90, b=20))
    return add_banner(fig, banner)


# ---------------------------------------------------------------------------
# 2. Match timeline and cumulative xG
# ---------------------------------------------------------------------------
def match_timeline(tl: pd.DataFrame, title: str = "Match timeline", banner: str | None = None) -> go.Figure:
    msg = _missing(tl, ["elapsed_min", "team_name", "event", "detail"])
    if msg:
        return _empty(msg, title)
    symbols = {"Goal": "star", "Yellow Card": "square", "Second Yellow": "square-x", "Red Card": "square-x",
               "Substitution": "triangle-up", "Tactical shift": "diamond-open"}
    colors = {"Goal": AMBER, "Yellow Card": "#e9c46a", "Second Yellow": RED, "Red Card": RED,
              "Substitution": TEAL, "Tactical shift": MUTED}
    fig = go.Figure()
    for ev, g in tl.groupby("event"):
        fig.add_trace(go.Scatter(x=g["elapsed_min"], y=g["team_name"], mode="markers", name=ev,
                                 marker=dict(symbol=symbols.get(ev, "circle"), size=15 if ev == "Goal" else 12,
                                             color=colors.get(ev, NAVY), line=dict(width=1, color="white")),
                                 customdata=np.stack([g["minute"], g["detail"]], axis=-1),
                                 hovertemplate="%{y}<br>clock %{customdata[0]}'<br>%{customdata[1]}<extra>" + ev
                                               + "</extra>"))
    fig.update_layout(title=title, height=330, xaxis_title="Elapsed playing time (min, incl. stoppage)",
                      yaxis_title="", legend=dict(orientation="h", y=-0.3))
    return add_banner(fig, banner)


def cumulative_xg_chart(cx: pd.DataFrame, title: str = "Cumulative xG", banner: str | None = None) -> go.Figure:
    msg = _missing(cx, ["team_name", "elapsed_min", "cum_xg"])
    if msg:
        return _empty(msg, title)
    fig = go.Figure()
    for i, (team, g) in enumerate(cx.groupby("team_name")):
        x = np.r_[0, g["elapsed_min"].values]
        y = np.r_[0, g["cum_xg"].values]
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line_shape="hv", name=team, line=dict(width=2.5,
                                 color=COLORWAY[i % len(COLORWAY)])))
        goals = g[g["outcome"] == "Goal"]
        fig.add_trace(go.Scatter(x=goals["elapsed_min"], y=goals["cum_xg"], mode="markers", showlegend=False,
                                 marker=dict(symbol="star", size=14, color=AMBER, line=dict(color=INK, width=1)),
                                 text=goals["player_name"], hovertemplate="Goal: %{text}<extra></extra>"))
    fig.update_layout(title=title, xaxis_title="Elapsed playing time (min)", yaxis_title="Cumulative StatsBomb xG",
                      height=360)
    return add_banner(fig, banner)


# ---------------------------------------------------------------------------
# 3. Results overview / 10. Team trend
# ---------------------------------------------------------------------------
def results_overview(team_stats: pd.DataFrame, team: str, banner: str | None = None) -> go.Figure:
    t = _rows(team_stats, "team_name", team)
    msg = _missing(t, ["match_date", "goal_diff", "result", "opponent"])
    if msg:
        return _empty(msg, f"Results — {team}")
    t = t.sort_values("match_date")
    rec = t["result"].value_counts().reindex(["W", "D", "L"], fill_value=0)
    fig = go.Figure(go.Bar(x=t["match_date"], y=t["goal_diff"], marker_color=t["result"].map(RESULT_COLORS),
                           customdata=np.stack([t["opponent"], t["goals_for"], t["goals_against"], t["result"],
                                                t["home_away"]], axis=-1),
                           hovertemplate="%{x|%d %b %Y} vs %{customdata[0]} (%{customdata[4]})<br>"
                                         "%{customdata[1]}-%{customdata[2]} (%{customdata[3]})<extra></extra>"))
    fig.update_layout(title=f"{team}: goal difference by match — W{rec['W']} D{rec['D']} L{rec['L']}",
                      yaxis_title="Goal difference", xaxis_title="", height=340, bargap=0.25)
    return add_banner(fig, banner)


def team_trend(team_stats: pd.DataFrame, team: str, rolling: int = 5, banner: str | None = None) -> go.Figure:
    t = _rows(team_stats, "team_name", team)
    msg = _missing(t, ["match_date", "xg", "xg_against", "goals_for", "goals_against"])
    if msg:
        return _empty(msg, f"Team trend — {team}")
    t = t.sort_values("match_date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t["match_date"], y=t["xg"].rolling(rolling, min_periods=1).mean(), name="xG for "
                             f"({rolling}-match rolling)", line=dict(color=NAVY, width=3)))
    fig.add_trace(go.Scatter(x=t["match_date"], y=t["xg_against"].rolling(rolling, min_periods=1).mean(),
                             name=f"xG against ({rolling}-match rolling)", line=dict(color=RED, width=3)))
    fig.add_trace(go.Scatter(x=t["match_date"], y=t["goals_for"], mode="markers", name="Goals for (match)",
                             marker=dict(color=NAVY, size=7, opacity=0.5), text=t["opponent"],
                             hovertemplate="%{x|%d %b} vs %{text}: %{y} goals<extra></extra>"))
    fig.add_trace(go.Scatter(x=t["match_date"], y=t["goals_against"], mode="markers", name="Goals against (match)",
                             marker=dict(color=RED, size=7, opacity=0.5, symbol="x"), text=t["opponent"],
                             hovertemplate="%{x|%d %b} vs %{text}: %{y} conceded<extra></extra>"))
    fig.update_layout(title=f"{team}: chance creation and concession over the season", yaxis_title="per match",
                      height=380, legend=dict(orientation="h", y=-0.2))
    return add_banner(fig, banner)


# ---------------------------------------------------------------------------
# 4. Leaderboard (Plotly dropdown -> works in static HTML)
# ---------------------------------------------------------------------------
def leaderboard_chart(season_pct: pd.DataFrame, metrics: list[str], min_minutes: float, n: int = 15,
                      role_family: str | None = None, banner: str | None = None) -> go.Figure:
    msg = _missing(season_pct, ["player_name", "minutes_played"] + metrics[:1])
    if msg:
        return _empty(msg, "Player contribution leaderboard")
    s = season_pct[season_pct["minutes_played"] >= min_minutes]
    if role_family and role_family != "All":
        s = s[s["role_family"] == role_family]
    metrics = [m for m in metrics if m in s.columns]
    if s.empty or not metrics:
        return _empty("No players meet the filter (try a lower minutes threshold).", "Player contribution leaderboard")
    fig = go.Figure()
    for i, m in enumerate(metrics):
        top = s.dropna(subset=[m]).nlargest(n, m).iloc[::-1]
        fig.add_trace(go.Bar(x=top[m], y=top["player_name"] + " · " + top["team_name"].str.slice(0, 14),
                             orientation="h", visible=(i == 0), name=label(m),
                             marker_color=top["role_family"].map(FAMILY_COLORS).fillna(SLATE),
                             customdata=np.stack([top["minutes_played"].round(0), top["primary_position"].fillna("?"),
                                                  top.get(f"{m}_pct", pd.Series(np.nan, index=top.index)).round(0)],
                                                 axis=-1),
                             hovertemplate="%{y}<br>" + label(m) + ": %{x:.2f}<br>%{customdata[1]}<br>"
                                           "minutes %{customdata[0]}<br>percentile in benchmark %{customdata[2]}"
                                           "<extra></extra>"))
    buttons = [dict(label=label(m), method="update",
                    args=[{"visible": [j == i for j in range(len(metrics))]},
                          {"title": f"Top {n}: {label(m)} (min {min_minutes:.0f} minutes)"}])
               for i, m in enumerate(metrics)]
    fig.update_layout(title=f"Top {n}: {label(metrics[0])} (min {min_minutes:.0f} minutes)", height=560,
                      updatemenus=[dict(buttons=buttons, x=1.0, xanchor="right", y=1.12, direction="down")],
                      showlegend=False, xaxis_title="per 90 minutes / rate", margin=dict(l=230))
    source_note(fig, "Colour = role family (navy defender, teal midfielder, amber forward, purple GK). "
                     "Per-90 uses actual playing time incl. stoppage.")
    return add_banner(fig, banner)


# ---------------------------------------------------------------------------
# 5. Radar
# ---------------------------------------------------------------------------
def player_radar(season_pct: pd.DataFrame, player_id: Any, metrics: list[str], compare_id: Any = None,
                 banner: str | None = None) -> go.Figure:
    s = _rows(season_pct, "player_id", player_id)
    msg = _missing(s, ["player_name"])
    if msg:
        return _empty(msg, "Player radar")
    pcols = [f"{m}_pct" for m in metrics if f"{m}_pct" in s.columns]
    if not pcols:
        return _empty("No percentile metrics available for this role.", "Player radar")
    r = s.sort_values("minutes_played", ascending=False).iloc[0]
    theta = [label(c[:-4]) for c in pcols]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[50] * len(pcols) + [50], theta=theta + theta[:1], name="Benchmark median (50th)",
                                  line=dict(color=MUTED, dash="dot"), fill=None, hoverinfo="skip"))
    vals = [r[c] if pd.notna(r[c]) else 0 for c in pcols]
    raw = [r[c[:-4]] for c in pcols]
    fig.add_trace(go.Scatterpolar(r=vals + vals[:1], theta=theta + theta[:1], fill="toself", name=r["player_name"],
                                  line=dict(color=NAVY, width=2.5), fillcolor="rgba(29,53,87,0.25)",
                                  customdata=np.array(raw + raw[:1], dtype=float),
                                  hovertemplate="%{theta}: %{r:.0f}th pct (value %{customdata:.2f})<extra></extra>"))
    if compare_id is not None:
        c = season_pct[season_pct["player_id"] == compare_id]
        if not c.empty:
            c = c.iloc[0]
            v2 = [c[x] if pd.notna(c[x]) else 0 for x in pcols]
            fig.add_trace(go.Scatterpolar(r=v2 + v2[:1], theta=theta + theta[:1], fill="toself", name=c["player_name"],
                                          line=dict(color=AMBER, width=2), fillcolor="rgba(233,162,59,0.2)"))
    bench = f"{r.get('benchmark_group')} ({r.get('benchmark_level')}, n={int(r['benchmark_n'])} eligible)" \
        if pd.notna(r.get("benchmark_n")) else "n/a"
    fig.update_layout(title=f"{r['player_name']} — percentile profile vs {bench}<br><sup>{r['minutes_played']:.0f} "
                            f"minutes · {r['coverage_label']}</sup>",
                      polar=dict(radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75, 100], gridcolor=GRID),
                                 angularaxis=dict(gridcolor=GRID), bgcolor=PAPER),
                      height=520, legend=dict(orientation="h", y=-0.1))
    return add_banner(fig, banner)


# ---------------------------------------------------------------------------
# 6. Comparison scatter with x/y dropdowns
# ---------------------------------------------------------------------------
def comparison_scatter(season_pct: pd.DataFrame, metrics: list[str], min_minutes: float, x: str | None = None,
                       y: str | None = None, role_family: str | None = None, highlight_team: str | None = None,
                       banner: str | None = None) -> go.Figure:
    msg = _missing(season_pct, ["player_name", "minutes_played"])
    if msg:
        return _empty(msg, "Player comparison")
    s = season_pct[season_pct["minutes_played"] >= min_minutes]
    if role_family and role_family != "All":
        s = s[s["role_family"] == role_family]
    metrics = [m for m in metrics if m in s.columns]
    if s.empty or len(metrics) < 2:
        return _empty("Not enough players/metrics for this filter.", "Player comparison")
    x, y = x or metrics[0], y or metrics[1]
    colors = s["role_family"].map(FAMILY_COLORS).fillna(SLATE)
    sizes = 6 + 14 * (s["minutes_played"] / s["minutes_played"].max())
    lines = np.where(s["team_name"] == highlight_team, 2, 0.5) if highlight_team else 0.5
    fig = go.Figure(go.Scatter(
        x=s[x], y=s[y], mode="markers", marker=dict(color=colors, size=sizes, opacity=0.8,
                                                     line=dict(color=INK, width=lines)),
        text=s["player_name"], customdata=np.stack([s["team_name"], s["primary_position"].fillna("?"),
                                                    s["minutes_played"].round(0)], axis=-1),
        hovertemplate="<b>%{text}</b> (%{customdata[0]})<br>%{customdata[1]} · %{customdata[2]} min<br>"
                      "x: %{x:.2f}<br>y: %{y:.2f}<extra></extra>"))
    fig.add_vline(x=s[x].median(), line=dict(color=MUTED, dash="dot", width=1))
    fig.add_hline(y=s[y].median(), line=dict(color=MUTED, dash="dot", width=1))
    bx = [dict(label=label(m), method="update", args=[{"x": [s[m]]}, {"xaxis.title.text": label(m)}]) for m in metrics]
    by = [dict(label=label(m), method="update", args=[{"y": [s[m]]}, {"yaxis.title.text": label(m)}]) for m in metrics]
    fig.update_layout(title=f"Player comparison (min {min_minutes:.0f} min; size = minutes; dotted = median)",
                      xaxis_title=label(x), yaxis_title=label(y), height=560,
                      updatemenus=[dict(buttons=bx, x=0.0, xanchor="left", y=1.13, direction="down"),
                                   dict(buttons=by, x=0.32, xanchor="left", y=1.13, direction="down")],
                      annotations=[dict(text="x-axis", x=0.0, y=1.19, xref="paper", yref="paper", showarrow=False,
                                        font=dict(size=10, color=MUTED)),
                                   dict(text="y-axis", x=0.32, y=1.19, xref="paper", yref="paper", showarrow=False,
                                        font=dict(size=10, color=MUTED))],
                      margin=dict(t=110))
    return add_banner(fig, banner)


# ---------------------------------------------------------------------------
# 7. Form trend / 8. Workload / 9. Role distribution
# ---------------------------------------------------------------------------
def form_trend(series: pd.DataFrame, metrics: list[str], player_name: str, window: int,
               banner: str | None = None) -> go.Figure:
    cols = [f"roll_{m[:-4]}_p90" for m in metrics if m.endswith("_p90")]
    cols = [c for c in cols if series is not None and c in series.columns]
    msg = _missing(series, ["match_date"] + cols[:1])
    if msg or not cols:
        return _empty(msg or "No rolling metrics available.", f"Form — {player_name}")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=series["match_date"], y=series["minutes_played"], name="Minutes (match)",
                         marker_color="#d9d4c7", opacity=0.6), secondary_y=True)
    for i, c in enumerate(cols):
        fig.add_trace(go.Scatter(x=series["match_date"], y=series[c], name=f"{label(c[5:])} ({window}-app rolling)",
                                 mode="lines+markers", line=dict(width=2.5, color=COLORWAY[i % len(COLORWAY)])),
                      secondary_y=False)
    fig.update_yaxes(title_text="rolling per 90", secondary_y=False)
    fig.update_yaxes(title_text="minutes", secondary_y=True, showgrid=False)
    fig.update_layout(title=f"{player_name}: rolling form over appearances (window {window}) — small windows are noisy",
                      height=400, legend=dict(orientation="h", y=-0.2))
    return add_banner(fig, banner)


def workload_bars(season: pd.DataFrame, team: str, banner: str | None = None) -> go.Figure:
    s = _rows(season, "team_name", team)
    msg = _missing(s, ["player_name", "minutes_played", "starts", "sub_appearances"])
    if msg:
        return _empty(msg, f"Minutes — {team}")
    s = s.sort_values("minutes_played", ascending=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(y=s["player_name"], x=s["minutes_played"], orientation="h", name="Minutes",
                         marker_color=s["role_family"].map(FAMILY_COLORS).fillna(SLATE),
                         customdata=np.stack([s["starts"], s["sub_appearances"], s["unused_sub_count"]], axis=-1),
                         text=[f"{a}S / {b}sub" for a, b in zip(s["starts"], s["sub_appearances"])],
                         textposition="outside",
                         hovertemplate="%{y}: %{x:.0f} min<br>starts %{customdata[0]}, sub apps %{customdata[1]}, "
                                       "unused sub %{customdata[2]}<extra></extra>"))
    fig.update_layout(title=f"{team}: minutes, starts and substitute appearances", height=max(380, 22 * len(s)),
                      xaxis_title="Minutes played (actual playing time)", showlegend=False, margin=dict(l=200))
    return add_banner(fig, banner)


def role_distribution(season_pct: pd.DataFrame, metrics: list[str], min_minutes: float,
                      banner: str | None = None) -> go.Figure:
    msg = _missing(season_pct, ["primary_role", "minutes_played"])
    if msg:
        return _empty(msg, "Distribution by role")
    s = season_pct[(season_pct["minutes_played"] >= min_minutes) & season_pct["primary_role"].notna()]
    metrics = [m for m in metrics if m in s.columns]
    if s.empty or not metrics:
        return _empty("No eligible players.", "Distribution by role")
    order = [r for r in ["GK", "CB", "FB", "WB", "DM", "CM", "AM", "WM", "W", "CF"] if r in set(s["primary_role"])]
    fig = go.Figure()
    for i, m in enumerate(metrics):
        fig.add_trace(go.Box(x=s["primary_role"], y=s[m], visible=(i == 0), name=label(m), boxpoints="all",
                             jitter=0.4, pointpos=0, marker=dict(size=5, color=TEAL, opacity=0.6),
                             line=dict(color=NAVY), fillcolor="rgba(42,157,143,0.15)", text=s["player_name"],
                             hovertemplate="%{text}<br>%{y:.2f}<extra></extra>"))
    buttons = [dict(label=label(m), method="update", args=[{"visible": [j == i for j in range(len(metrics))]},
                                                           {"yaxis.title.text": label(m)}])
               for i, m in enumerate(metrics)]
    n_by = s["primary_role"].value_counts()
    fig.update_layout(title=f"Metric distribution by role (min {min_minutes:.0f} min) — n per role: "
                            + ", ".join(f"{r}={n_by.get(r, 0)}" for r in order),
                      xaxis=dict(categoryorder="array", categoryarray=order), yaxis_title=label(metrics[0]),
                      updatemenus=[dict(buttons=buttons, x=1, xanchor="right", y=1.13)], height=440, showlegend=False)
    return add_banner(fig, banner)


# ---------------------------------------------------------------------------
# 11-12. Formations
# ---------------------------------------------------------------------------
def formation_frequency(fs: pd.DataFrame, team: str, banner: str | None = None) -> go.Figure:
    msg = _missing(fs, ["starting_formation", "wins", "draws", "losses"])
    if msg:
        return _empty(msg, f"Formations — {team}")
    fig = go.Figure()
    for k, c in (("wins", TEAL), ("draws", SLATE), ("losses", RED)):
        fig.add_trace(go.Bar(x=fs["starting_formation"], y=fs[k], name=k.title(), marker_color=c))
    for _, r in fs.iterrows():
        fig.add_annotation(x=r["starting_formation"], y=r["matches"], text=f"{r['points_per_match']:.2f} ppm"
                           + (" *" if r["sample_warning"] else ""), showarrow=False, yshift=12,
                           font=dict(size=11, color=INK))
    fig.update_layout(barmode="stack", title=f"{team}: starting formations and results (* small sample)",
                      yaxis_title="Matches", height=380)
    return add_banner(fig, banner)


def formation_comparison(fs: pd.DataFrame, team: str, banner: str | None = None) -> go.Figure:
    msg = _missing(fs, ["starting_formation", "xg_for", "xg_against"])
    if msg:
        return _empty(msg, f"Formation comparison — {team}")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=fs["starting_formation"], y=fs["xg_for"], name="xG for / match", marker_color=NAVY))
    fig.add_trace(go.Bar(x=fs["starting_formation"], y=fs["xg_against"], name="xG against / match", marker_color=RED))
    fig.add_trace(go.Scatter(x=fs["starting_formation"], y=fs["field_tilt_pct"] / 100 * max(fs["xg_for"].max(), 1),
                             mode="markers", name="Field tilt (scaled)", marker=dict(size=12, color=AMBER,
                                                                                    symbol="diamond"),
                             text=fs["field_tilt_pct"].round(1), hovertemplate="field tilt %{text}%<extra></extra>"))
    for _, r in fs.iterrows():
        fig.add_annotation(x=r["starting_formation"], y=0, text=f"n={r['matches']}", showarrow=False, yshift=-28,
                           font=dict(size=11, color=MUTED))
    fig.update_layout(barmode="group", title=f"{team}: event metrics by starting formation (descriptive; "
                                             f"opponent and squad confound these)", height=400)
    return add_banner(fig, banner)


# ---------------------------------------------------------------------------
# 13-14. Starting XI
# ---------------------------------------------------------------------------
def xi_pitch(lineup: pd.DataFrame, title: str, banner: str | None = None) -> go.Figure:
    msg = _missing(lineup, ["x", "y", "player_name", "slot", "score"])
    if msg:
        return _empty(msg, title)
    fig = draw_pitch()
    hover = [f"<b>{r.player_name}</b><br>slot {r.slot} ({ROLE_LABEL.get(r.slot_role, r.slot_role)})<br>"
             f"score {r.score:.1f} · compatibility {r.compatibility:.2f}<br>role fit {r.role_fit:.0f} · form "
             f"{r.recent_form:.0f}{' (season fallback)' if r.form_fallback else ''}<br>reliability "
             f"{r.sample_reliability:.0f} · workload {r.workload_suitability:.0f} · continuity "
             f"{r.lineup_continuity:.0f}<br>{r.coverage_label}" for r in lineup.itertuples()]
    fig.add_trace(go.Scatter(x=lineup["x"], y=lineup["y"], mode="markers+text", text=lineup["slot"],
                             textfont=dict(color="white", size=10), marker=dict(size=34, color=lineup["score"],
                             colorscale=SEQ_SCALE, cmin=40, cmax=95, line=dict(color="white", width=2),
                             colorbar=dict(title="slot<br>score", thickness=12, len=0.6)),
                             hovertext=hover, hoverinfo="text", showlegend=False))
    fig.add_trace(go.Scatter(x=lineup["x"], y=lineup["y"] + 6.5, mode="text",
                             text=[str(n).split()[-1] for n in lineup["player_name"]],
                             textfont=dict(size=11, color=INK), hoverinfo="skip", showlegend=False))
    attack_arrow(fig)
    fig.update_layout(title=title, height=560, margin=dict(l=10, r=10, t=80, b=30))
    return add_banner(fig, banner)


def score_decomposition(lineup: pd.DataFrame, weights: dict[str, float], title: str = "Score decomposition",
                        banner: str | None = None) -> go.Figure:
    comps = list(weights)
    msg = _missing(lineup, ["player_name", "compatibility"] + comps)
    if msg:
        return _empty(msg, title)
    fig = go.Figure()
    names = lineup["slot"] + " · " + lineup["player_name"]
    for i, c in enumerate(comps):
        vals = weights[c] * lineup[c].fillna(0) * lineup["compatibility"]
        fig.add_trace(go.Bar(y=names, x=vals, orientation="h", name=f"{c.replace('_', ' ')} (w={weights[c]:.2f})",
                             marker_color=COLORWAY[i % len(COLORWAY)],
                             hovertemplate="%{y}<br>" + c + ": %{x:.1f} weighted points<extra></extra>"))
    fig.update_layout(barmode="stack", title=title, height=480, xaxis_title="Weighted points (x compatibility)",
                      legend=dict(orientation="h", y=-0.15), margin=dict(l=220), yaxis=dict(autorange="reversed"))
    return add_banner(fig, banner)


def alternative_xi_comparison(a: pd.DataFrame, b: pd.DataFrame, label_a: str, label_b: str,
                              banner: str | None = None) -> go.Figure:
    msg = _missing(a, ["slot", "player_name", "score"]) or _missing(b, ["slot", "player_name", "score"])
    if msg:
        return _empty(msg, "Alternative XI comparison")
    m = a[["slot", "player_name", "score"]].merge(b[["slot", "player_name", "score"]], on="slot", how="outer",
                                                  suffixes=("_a", "_b"))
    fig = go.Figure()
    fig.add_trace(go.Bar(x=m["slot"], y=m["score_a"], name=label_a, marker_color=NAVY, text=m["player_name_a"],
                         hovertemplate="%{x}: %{text} (%{y:.1f})<extra></extra>"))
    fig.add_trace(go.Bar(x=m["slot"], y=m["score_b"], name=label_b, marker_color=AMBER, text=m["player_name_b"],
                         hovertemplate="%{x}: %{text} (%{y:.1f})<extra></extra>"))
    changed = m[m["player_name_a"] != m["player_name_b"]]
    fig.update_layout(barmode="group", title=f"{label_a} vs {label_b}: slot scores ({len(changed)} slot(s) differ)",
                      yaxis_title="Slot score", height=400)
    return add_banner(fig, banner)


# ---------------------------------------------------------------------------
# 15-18. Spatial: shots, passes, network, progressive actions
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 19-23. Substitutions
# ---------------------------------------------------------------------------
def substitution_timeline(subs: pd.DataFrame, title: str, banner: str | None = None) -> go.Figure:
    msg = _missing(subs, ["elapsed_min", "team_name", "player_on_name", "player_off_name"])
    if msg:
        return _empty(msg, title)
    fig = go.Figure()
    for i, (team, g) in enumerate(subs.groupby("team_name")):
        fig.add_trace(go.Scatter(
            x=g["elapsed_min"], y=[team] * len(g), mode="markers+text", name=team,
            text=g["player_on_name"].str.split().str[-1], textposition="top center",
            marker=dict(symbol="triangle-up", size=14, color=COLORWAY[i % len(COLORWAY)]),
            customdata=np.stack([g["minute"], g["player_off_name"], g["player_on_name"], g["game_state"],
                                 g["sub_reason"]], axis=-1),
            hovertemplate="%{customdata[0]}': OFF %{customdata[1]} → ON %{customdata[2]}<br>state: %{customdata[3]}"
                          " · %{customdata[4]}<extra></extra>"))
    fig.update_layout(title=title, xaxis_title="Elapsed playing time (min)", height=300, showlegend=False,
                      xaxis=dict(range=[0, max(100, subs["elapsed_min"].max() + 5)]))
    return add_banner(fig, banner)


def sub_timing_histogram(subs: pd.DataFrame, bands: list[dict], group: str | None = None,
                         banner: str | None = None) -> go.Figure:
    msg = _missing(subs, ["timing_band", "minute"])
    if msg:
        return _empty(msg, "Substitution timing")
    order = [b["label"] for b in bands]
    fig = go.Figure()
    groups = [(None, subs)] if not group else list(subs.groupby(group))
    for i, (g, d) in enumerate(groups):
        counts = d["timing_band"].value_counts().reindex(order, fill_value=0)
        share = counts / max(counts.sum(), 1) * 100
        fig.add_trace(go.Bar(x=order, y=share, name=str(g) if g is not None else "All",
                             marker_color=COLORWAY[i % len(COLORWAY)], customdata=counts.values,
                             hovertemplate="%{x}: %{y:.1f}% (%{customdata} subs)<extra></extra>"))
    fig.update_layout(title=f"Substitution timing by analytical band (share of substitutions, n={len(subs)})",
                      yaxis_title="% of substitutions", xaxis_title="Band (clock minutes, stoppage counted)",
                      barmode="group", height=380)
    return add_banner(fig, banner)


def subs_by_state(subs: pd.DataFrame, by: str | None = None, banner: str | None = None) -> go.Figure:
    msg = _missing(subs, ["game_state", "minute"])
    if msg:
        return _empty(msg, "Substitutions by score state")
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Share of substitutions", "Minute distribution"))
    counts = subs["game_state"].value_counts().reindex(["leading", "drawing", "trailing"], fill_value=0)
    fig.add_trace(go.Bar(x=counts.index, y=counts / counts.sum() * 100, marker_color=[STATE_COLORS[k] for k in
                                                                                     counts.index],
                         customdata=counts.values, hovertemplate="%{x}: %{y:.1f}% (%{customdata})<extra></extra>",
                         showlegend=False), row=1, col=1)
    for st in ["leading", "drawing", "trailing"]:
        d = subs[subs["game_state"] == st]
        if len(d):
            fig.add_trace(go.Box(y=d["minute"], name=st, marker_color=STATE_COLORS[st], boxpoints="all", jitter=0.4,
                                 pointpos=0, marker=dict(size=4), showlegend=False), row=1, col=2)
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="clock minute", row=1, col=2)
    fig.update_layout(title=f"Substitutions by game state at the moment of the change (n={len(subs)})", height=400)
    return add_banner(fig, banner)


def role_flow_sankey(flow: pd.DataFrame, title: str = "Substitution role flow", banner: str | None = None
                     ) -> go.Figure:
    msg = _missing(flow, ["off_role", "on_role", "count"])
    if msg:
        return _empty(msg, title)
    left = sorted(flow["off_role"].unique())
    right = sorted(flow["on_role"].unique())
    labels = [f"OFF {r}" for r in left] + [f"ON {r}" for r in right]
    src = [left.index(r) for r in flow["off_role"]]
    tgt = [len(left) + right.index(r) for r in flow["on_role"]]
    same = flow["off_role"] == flow["on_role"]
    fig = go.Figure(go.Sankey(
        node=dict(label=labels, pad=14, thickness=16, color=[NAVY] * len(left) + [TEAL] * len(right)),
        link=dict(source=src, target=tgt, value=flow["count"],
                  color=np.where(same, "rgba(141,153,174,0.45)", "rgba(233,162,59,0.55)"))))
    fig.update_layout(title=f"{title} (grey = like-for-like role, amber = role change)", height=460)
    return add_banner(fig, banner)


def impact_chart(impact: pd.DataFrame, metric: str = "xg", banner: str | None = None) -> go.Figure:
    col = f"delta_team_{metric}"
    msg = _missing(impact, [col, "game_state", "contaminated"])
    if msg:
        return _empty(msg, "Pre/post substitution windows")
    fig = go.Figure()
    for st in ["leading", "drawing", "trailing"]:
        for clean, op in ((True, 0.9), (False, 0.45)):
            d = impact[(impact["game_state"] == st) & (impact["contaminated"] != clean)]
            if len(d):
                fig.add_trace(go.Box(y=d[col], x=[st] * len(d), name=("clean window" if clean else "contaminated"),
                                     marker_color=STATE_COLORS[st], opacity=op, boxpoints="all", jitter=0.5,
                                     pointpos=0, legendgroup=str(clean), showlegend=(st == "leading"),
                                     marker=dict(size=4)))
    fig.add_hline(y=0, line=dict(color=INK, width=1))
    fig.update_layout(boxmode="group", title=f"Change in team {metric} per 15 min after vs before substitution decisions — "
                                             f"OBSERVED ASSOCIATION, not causal effect", yaxis_title="post − pre",
                      height=420)
    source_note(fig, "Confounders: score changes, opponent substitutions, fatigue, time left, red cards, regression "
                     "to the mean. 'Contaminated' = goal, red card or another own decision in the window.")
    return add_banner(fig, banner)


def candidate_comparison(cands: pd.DataFrame, weights: dict[str, float], title: str,
                         banner: str | None = None) -> go.Figure:
    comps = list(weights)
    msg = _missing(cands, ["player_name"] + comps)
    if msg:
        return _empty(msg, title)
    c = cands.head(6)
    fig = go.Figure()
    for i, k in enumerate(comps):
        fig.add_trace(go.Bar(y=c["player_name"], x=weights[k] * c[k].fillna(0), orientation="h",
                             name=f"{k.replace('_', ' ')} (w={weights[k]:.2f})", marker_color=COLORWAY[i]))
    fig.update_layout(barmode="stack", title=title, xaxis_title="Weighted points", height=360,
                      yaxis=dict(autorange="reversed"), legend=dict(orientation="h", y=-0.25), margin=dict(l=200))
    return add_banner(fig, banner)


# ---------------------------------------------------------------------------
# 24-26. Manager
# ---------------------------------------------------------------------------
def manager_formation_distribution(team_stats: pd.DataFrame, manager: str, banner: str | None = None) -> go.Figure:
    t = _rows(team_stats, "manager_name", manager)
    msg = _missing(t, ["match_date", "starting_formation"])
    if msg:
        return _empty(msg, f"Formations — {manager}")
    t = t.sort_values("match_date")
    fig = make_subplots(rows=1, cols=2, column_widths=[0.35, 0.65], specs=[[{"type": "domain"}, {"type": "xy"}]],
                        subplot_titles=("Share of starts", "Formation by match (stability)"))
    vc = t["starting_formation"].value_counts()
    fig.add_trace(go.Pie(labels=vc.index, values=vc.values, hole=0.55, marker=dict(colors=COLORWAY),
                         textinfo="label+percent", showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=t["match_date"], y=t["starting_formation"], mode="markers+lines",
                             line=dict(color=GRID, width=1), marker=dict(size=11, color=t["result"].map(RESULT_COLORS)),
                             text=t["opponent"], hovertemplate="%{x|%d %b} vs %{text}: %{y}<extra></extra>",
                             showlegend=False), row=1, col=2)
    fig.update_layout(title=f"{manager}: observed formation choices (n={len(t)} matches; colour = result)",
                      height=380)
    return add_banner(fig, banner)


def rotation_trend(cont: pd.DataFrame, team: str, banner: str | None = None) -> go.Figure:
    msg = _missing(cont, ["match_date", "lineup_changes", "days_since_prev_dataset_match"])
    if msg:
        return _empty(msg, f"Rotation — {team}")
    c = cont.sort_values("match_date")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=c["match_date"], y=c["lineup_changes"], name="Changes to starting XI",
                         marker_color=TEAL), secondary_y=False)
    fig.add_trace(go.Scatter(x=c["match_date"], y=c["days_since_prev_dataset_match"], name="Days since previous "
                             "(dataset) match", mode="lines+markers", line=dict(color=AMBER)), secondary_y=True)
    fig.update_yaxes(title_text="starters changed", secondary_y=False)
    fig.update_yaxes(title_text="days", secondary_y=True, showgrid=False)
    fig.update_layout(title=f"{team}: lineup rotation between consecutive analysed matches "
                            f"(mean {c['lineup_changes'].mean():.1f} changes)", height=380,
                      legend=dict(orientation="h", y=-0.2))
    source_note(fig, "Only matches in the analysed dataset are visible — cup/European fixtures in between are not.")
    return add_banner(fig, banner)


def manager_sub_profile(subs: pd.DataFrame, manager: str, bands: list[dict], banner: str | None = None
                        ) -> go.Figure:
    s = _rows(subs, "manager_name", manager)
    msg = _missing(s, ["timing_band", "game_state"])
    if msg:
        return _empty(msg, f"Substitution profile — {manager}")
    order = [b["label"] for b in bands]
    states = ["trailing", "drawing", "leading"]
    ct = pd.crosstab(s["game_state"], s["timing_band"]).reindex(index=states, columns=order, fill_value=0)
    fig = go.Figure(go.Heatmap(z=ct.values, x=order, y=states, colorscale=SEQ_SCALE, text=ct.values,
                               texttemplate="%{text}", hovertemplate="%{y}, %{x}: %{z} subs<extra></extra>",
                               colorbar=dict(title="subs")))
    fig.update_layout(title=f"{manager}: substitution timing × game state (n={len(s)} substitutions)",
                      height=340, xaxis_title="Timing band", yaxis_title="Game state")
    return add_banner(fig, banner)


# ---------------------------------------------------------------------------
# 27-30. EDA, coverage, model
# ---------------------------------------------------------------------------
def correlation_heatmap(df: pd.DataFrame, cols: list[str], title: str = "Correlation (Spearman)",
                        banner: str | None = None) -> go.Figure:
    cols = [c for c in cols if c in (df.columns if df is not None else [])]
    if df is None or len(df) < 5 or len(cols) < 2:
        return _empty("Not enough rows/columns for a correlation matrix.", title)
    c = df[cols].corr(method="spearman")
    lab = [label(x) for x in cols]
    fig = go.Figure(go.Heatmap(z=c.values, x=lab, y=lab, zmin=-1, zmax=1, colorscale=DIV_SCALE,
                               text=c.round(2).values, texttemplate="%{text}", textfont=dict(size=9),
                               colorbar=dict(title="ρ")))
    fig.update_layout(title=f"{title} — n={len(df)}; association only, shared minutes/role drive many pairs",
                      height=620, xaxis=dict(tickangle=-45), margin=dict(l=170, b=150))
    return add_banner(fig, banner)


def feature_distributions(df: pd.DataFrame, metrics: list[str], title: str = "Feature distributions",
                          banner: str | None = None) -> go.Figure:
    metrics = [m for m in metrics if df is not None and m in df.columns]
    if not metrics or df is None or df.empty:
        return _empty("No data for distributions.", title)
    fig = go.Figure()
    for i, m in enumerate(metrics):
        fig.add_trace(go.Histogram(x=df[m].dropna(), nbinsx=30, visible=(i == 0), name=label(m), marker_color=TEAL,
                                   marker_line=dict(color="white", width=0.5)))
    buttons = [dict(label=label(m), method="update", args=[{"visible": [j == i for j in range(len(metrics))]},
                                                           {"xaxis.title.text": label(m)}])
               for i, m in enumerate(metrics)]
    fig.update_layout(title=title, xaxis_title=label(metrics[0]), yaxis_title="players", height=380,
                      updatemenus=[dict(buttons=buttons, x=1, xanchor="right", y=1.15)], showlegend=False)
    return add_banner(fig, banner)


def missingness_heatmap(cov: pd.DataFrame, title: str = "Field completeness by event type (%)",
                        banner: str | None = None) -> go.Figure:
    if cov is None or cov.empty:
        return _empty("No coverage table.", title)
    fig = go.Figure(go.Heatmap(z=cov.values, x=list(cov.columns), y=list(cov.index), zmin=0, zmax=100,
                               colorscale=SEQ_SCALE, text=cov.values.round(0), texttemplate="%{text}",
                               colorbar=dict(title="% present")))
    fig.update_layout(title=title + " — blanks are structural (e.g. pressures have no outcome), not errors",
                      height=520, margin=dict(l=140))
    return add_banner(fig, banner)


def confusion_matrix_chart(cm: np.ndarray, title: str = "Confusion matrix (test period)",
                           banner: str | None = None) -> go.Figure:
    if cm is None:
        return _empty("No fitted model.", title)
    lab = ["did not start", "started"]
    fig = go.Figure(go.Heatmap(z=cm, x=[f"pred: {x}" for x in lab], y=[f"actual: {x}" for x in lab],
                               colorscale=SEQ_SCALE, text=cm, texttemplate="%{text}", showscale=False))
    fig.update_layout(title=title, height=340, yaxis=dict(autorange="reversed"))
    return add_banner(fig, banner)


def roc_chart(roc: pd.DataFrame, auc: float, banner: str | None = None) -> go.Figure:
    msg = _missing(roc, ["fpr", "tpr"])
    if msg:
        return _empty(msg, "ROC curve")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=roc["fpr"], y=roc["tpr"], mode="lines", name=f"Logistic regression (AUC {auc:.3f})",
                             line=dict(color=NAVY, width=3)))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Chance", line=dict(color=MUTED, dash="dot")))
    fig.update_layout(title="ROC — chronological hold-out", xaxis_title="False positive rate",
                      yaxis_title="True positive rate", height=380)
    return add_banner(fig, banner)


def calibration_chart(cal: pd.DataFrame, banner: str | None = None) -> go.Figure:
    msg = _missing(cal, ["mean_pred", "observed_rate", "n"])
    if msg:
        return _empty(msg, "Calibration")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cal["mean_pred"], y=cal["observed_rate"], mode="lines+markers+text", text=cal["n"],
                             textposition="top center", name="model", marker=dict(size=10, color=TEAL)))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="perfect calibration",
                             line=dict(color=MUTED, dash="dot")))
    fig.update_layout(title="Calibration (labels = rows per bin)", xaxis_title="mean predicted probability",
                      yaxis_title="observed start rate", height=360)
    return add_banner(fig, banner)


def threshold_sensitivity_chart(season: pd.DataFrame, thresholds: list[float] | None = None,
                                banner: str | None = None) -> go.Figure:
    thresholds = thresholds or [0, 90, 180, 270, 450, 900, 1350]
    msg = _missing(season, ["minutes_played"])
    if msg:
        return _empty(msg, "Minutes threshold")
    n = [int((season["minutes_played"] >= t).sum()) for t in thresholds]
    fig = go.Figure(go.Scatter(x=thresholds, y=n, mode="lines+markers+text", text=n, textposition="top center",
                               line=dict(color=NAVY, width=3)))
    fig.update_layout(title="Eligible players vs minimum-minutes threshold", xaxis_title="minimum minutes",
                      yaxis_title="players eligible", height=320)
    return add_banner(fig, banner)


def export_figure(fig: go.Figure, path_html: str, path_png: str | None = None) -> dict[str, str]:
    """Write HTML (always, Plotly JS from CDN) and PNG if kaleido is installed."""
    out = {"html": path_html}
    fig.write_html(path_html, include_plotlyjs="cdn", full_html=True)
    if path_png:
        try:
            fig.write_image(path_png, scale=2)
            out["png"] = path_png
        except Exception as exc:  # kaleido missing or no Chrome
            out["png"] = f"skipped ({type(exc).__name__})"
    return out
