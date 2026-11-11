"""Player performance and scouting charts."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Any
from typing import TYPE_CHECKING

from src.config import ROLE_LABEL
from src.features.player_features import label, radar_metrics
from src.visualization.theme import AMBER, COLORWAY, DIV_SCALE, FAMILY_COLORS, GRID, INK, MUTED, NAVY, PAPER, PURPLE, RED, ROLE_ORDER, SEQ_SCALE, SLATE, TEAL, _empty, _missing, _rows, add_banner, source_note

if TYPE_CHECKING:
    from src.config import Config


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


def finishing_scatter(season_pct: pd.DataFrame, min_minutes: float, highlight_team: str | None = None) -> go.Figure:
    """Goals vs xG per player: who scored more (or less) than their chance quality suggests."""
    msg = _missing(season_pct, ["goals", "xg", "shots", "minutes_played", "player_name"])
    if msg:
        return _empty(msg, "Finishing")
    d = season_pct[(season_pct["minutes_played"] >= min_minutes) & (season_pct["shots"] > 0)].copy()
    if d.empty:
        return _empty("No shooters above the threshold.", "Finishing")
    mx = float(max(d["xg"].max(), d["goals"].max())) + 1
    is_hi = (d["team_name"] == highlight_team) if highlight_team else pd.Series(False, index=d.index)
    fig = go.Figure()
    fig.add_shape(type="path", path=f"M 0 0 L 0 {mx} L {mx} {mx} Z", fillcolor="rgba(42,157,143,0.07)",
                  line=dict(width=0), layer="below")
    fig.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines", line=dict(color=MUTED, dash="dot"),
                             name="goals = xG", hoverinfo="skip"))
    for flag, name, color in ((False, "Other teams", SLATE), (True, highlight_team or "", TEAL)):
        g = d[is_hi == flag]
        if g.empty:
            continue
        fig.add_trace(go.Scatter(x=g["xg"], y=g["goals"], mode="markers", name=name,
                                 marker=dict(size=7 + 3 * np.sqrt(g["shots"]), color=color, opacity=0.8,
                                             line=dict(color="white", width=1)),
                                 text=g["player_name"], customdata=np.stack([g["shots"], g["minutes_played"]], -1),
                                 hovertemplate="<b>%{text}</b><br>%{y} goals from %{x:.2f} xG<br>%{customdata[0]} "
                                               "shots · %{customdata[1]:.0f} min<extra></extra>"))
    d["diff"] = d["goals"] - d["xg"]
    for _, r in pd.concat([d.nlargest(3, "diff"), d.nsmallest(2, "diff")]).iterrows():
        fig.add_annotation(x=r["xg"], y=r["goals"], text=r["player_name"].split()[-1], showarrow=True, arrowhead=0,
                           ax=25, ay=-20, font=dict(size=11, color=INK))
    fig.update_layout(title=f"Finishing: goals vs expected goals (n={len(d)}; shaded = scored above xG; size = shots)",
                      xaxis=dict(title="xG (StatsBomb, incl. penalties)", range=[0, mx]),
                      yaxis=dict(title="goals", range=[0, mx]), height=520)
    return fig


def goal_involvement_bars(season_pct: pd.DataFrame, team: str, n: int = 15) -> go.Figure:
    """Goals and assists per player with expected involvement (xG + xA) overlaid."""
    s = _rows(season_pct, "team_name", team)
    msg = _missing(s, ["goals", "assists", "xg", "xa", "player_name"])
    if msg:
        return _empty(msg, f"Goal involvement — {team}")
    s = s.assign(gi=s["goals"] + s["assists"], xgi=s["xg"] + s["xa"])
    s = s[s["xgi"] > 0].sort_values(["gi", "xgi"], ascending=False).head(n).iloc[::-1]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=s["player_name"], x=s["goals"], orientation="h", name="Goals", marker_color=NAVY))
    fig.add_trace(go.Bar(y=s["player_name"], x=s["assists"], orientation="h", name="Assists", marker_color=TEAL))
    fig.add_trace(go.Scatter(y=s["player_name"], x=s["xgi"], mode="markers", name="xG + xA (expected)",
                             marker=dict(symbol="diamond", size=12, color=AMBER, line=dict(color=INK, width=1)),
                             hovertemplate="%{y}: %{x:.2f} xG+xA<extra></extra>"))
    fig.update_layout(barmode="stack", title=f"{team}: goal involvement vs expected involvement (top {len(s)})",
                      xaxis_title="count", height=520, margin=dict(l=200), legend=dict(orientation="h", y=-0.12))
    return fig


def chance_treemap(season_pct: pd.DataFrame, team: str) -> go.Figure:
    """Share of the team's chance creation (xG + xA) by role family and player."""
    s = _rows(season_pct, "team_name", team)
    msg = _missing(s, ["xg", "xa", "role_family", "player_name"])
    if msg:
        return _empty(msg, f"Chance contribution — {team}")
    s = s.assign(v=s["xg"] + s["xa"])
    s = s[(s["v"] > 0) & s["role_family"].notna()]
    ids, labels, parents, values, colors, cd = [], [], [], [], [], []
    for fam, g in s.groupby("role_family"):
        ids.append(fam); labels.append(fam); parents.append(""); values.append(g["v"].sum())
        colors.append(FAMILY_COLORS.get(fam, SLATE)); cd.append([g["xg"].sum(), g["xa"].sum()])
        for _, r in g.iterrows():
            ids.append(f"{fam}/{r['player_id']}"); labels.append(r["player_name"]); parents.append(fam)
            values.append(r["v"]); colors.append(FAMILY_COLORS.get(fam, SLATE)); cd.append([r["xg"], r["xa"]])
    fig = go.Figure(go.Treemap(ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
                               customdata=cd, marker=dict(colors=colors, line=dict(color="white", width=1)),
                               textinfo="label+percent root",
                               hovertemplate="<b>%{label}</b><br>xG %{customdata[0]:.2f} + xA %{customdata[1]:.2f}"
                                             "<br>%{percentRoot:.1%} of team chance creation<extra></extra>"))
    fig.update_layout(title=f"{team}: who creates the chances? (area = xG + xA)", height=520,
                      margin=dict(t=70, l=10, r=10, b=10))
    return fig


def involvement_race(pms: pd.DataFrame, team: str, top: int = 10) -> go.Figure:
    """Animated race of cumulative goals + assists over the season (press ▶)."""
    p = _rows(pms, "team_name", team)
    msg = _missing(p, ["match_date", "player_name", "goals", "assists"])
    if msg:
        return _empty(msg, f"Goal-involvement race — {team}")
    p = p.assign(gi=p["goals"] + p["assists"])
    piv = p.pivot_table(index="match_date", columns="player_name", values="gi", aggfunc="sum").fillna(0).sort_index()
    cum = piv.cumsum()
    leaders = cum.iloc[-1].sort_values(ascending=False).head(top).index
    if cum.empty or cum.iloc[-1].max() == 0:
        return _empty("No goal involvements recorded.", f"Goal-involvement race — {team}")
    color = {pl: COLORWAY[i % len(COLORWAY)] for i, pl in enumerate(leaders)}
    xmax = float(cum[leaders].values.max()) * 1.15

    def bar(i):
        v = cum.iloc[i][leaders]
        return go.Bar(x=v.values, y=list(leaders), orientation="h", text=v.astype(int).values, textposition="outside",
                      marker_color=[color[pl] for pl in leaders], hovertemplate="%{y}: %{x:.0f}<extra></extra>")

    frames = [go.Frame(data=[bar(i)], name=str(i),
                       layout=go.Layout(title_text=f"{team}: cumulative goals + assists — after match {i + 1} "
                                                   f"({cum.index[i]:%d %b %Y})")) for i in range(len(cum))]
    fig = go.Figure(data=[bar(len(cum) - 1)], frames=frames)
    steps = [dict(method="animate", label=str(i + 1), args=[[str(i)], dict(mode="immediate", frame=dict(
        duration=0, redraw=True), transition=dict(duration=0))]) for i in range(len(cum))]
    fig.update_layout(title=f"{team}: cumulative goals + assists — full season (press ▶ to replay)",
                      xaxis=dict(range=[0, xmax], title="goals + assists"),
                      yaxis=dict(categoryorder="total ascending"), height=520, margin=dict(l=200, t=90),
                      updatemenus=[dict(type="buttons", x=0, y=-0.12, xanchor="left", direction="left", buttons=[
                          dict(label="▶ Play", method="animate", args=[None, dict(frame=dict(duration=350, redraw=True),
                                                                                  fromcurrent=True)]),
                          dict(label="❚❚ Pause", method="animate", args=[[None], dict(mode="immediate", frame=dict(
                              duration=0, redraw=False))])])],
                      sliders=[dict(active=len(cum) - 1, x=0.2, len=0.8, y=-0.08, steps=steps,
                                    currentvalue=dict(prefix="match "))])
    return fig


def archetype_map(res: dict | None, highlight_team: str | None = None) -> go.Figure:
    """PCA map of player profiles coloured by archetype, with metric loading arrows (biplot)."""
    if not res:
        return _empty("Not enough eligible players for archetypes.", "Player archetypes")
    d, ld = res["frame"], res["loadings"]
    fig = go.Figure()
    for i, (name, g) in enumerate(d.groupby("archetype")):
        hi = (g["team_name"] == highlight_team) if highlight_team else pd.Series(False, index=g.index)
        fig.add_trace(go.Scatter(x=g["pc1"], y=g["pc2"], mode="markers+text", name=name,
                                 text=[n.split()[-1] if h else "" for n, h in zip(g["player_name"], hi)],
                                 textposition="top center", textfont=dict(size=9),
                                 marker=dict(size=np.where(hi, 13, 9), color=COLORWAY[i % len(COLORWAY)], opacity=0.85,
                                             symbol=np.where(hi, "circle", "circle-open"), line=dict(width=1.5)),
                                 customdata=np.stack([g["player_name"], g["team_name"], g["primary_position"]], -1),
                                 hovertemplate="<b>%{customdata[0]}</b> (%{customdata[1]})<br>%{customdata[2]}"
                                               "<extra>" + name + "</extra>"))
    span = max(d["pc1"].abs().max(), d["pc2"].abs().max())
    top = ld.assign(n=np.hypot(ld["pc1"], ld["pc2"])).nlargest(6, "n")
    for m, r in top.iterrows():
        fig.add_annotation(x=r["pc1"] * span * 0.9, y=r["pc2"] * span * 0.9, ax=0, ay=0, xref="x", yref="y",
                           axref="x", ayref="y", showarrow=True, arrowhead=2, arrowcolor=MUTED, arrowwidth=1.2,
                           text=label(m), font=dict(size=10, color=MUTED))
    ev = res["explained"]
    fig.update_layout(title=f"Player archetypes — k={res['k']} chosen by silhouette ({res['silhouette'][res['k']]:.2f});"
                            f" n={len(d)} outfield players<br><sup>filled = {highlight_team}; arrows = metric "
                            f"directions (PCA loadings)</sup>",
                      xaxis_title=f"PC1 ({ev[0]:.0%} of variance)", yaxis_title=f"PC2 ({ev[1]:.0%} of variance)",
                      height=620, legend=dict(orientation="h", y=-0.15))
    return fig


def archetype_profile_heatmap(res: dict | None) -> go.Figure:
    if not res:
        return _empty("Not enough eligible players for archetypes.", "Archetype profiles")
    c = res["centers_z"]
    n = res["frame"]["archetype"].value_counts()
    fig = go.Figure(go.Heatmap(z=c.values, x=[label(m) for m in c.columns], y=[f"{i} (n={n.get(i, 0)})" for i in c.index],
                               zmid=0, colorscale=DIV_SCALE, text=c.round(1).values, texttemplate="%{text}",
                               xgap=2, ygap=2, colorbar=dict(title="z-score", thickness=12),
                               hovertemplate="%{y}<br>%{x}: %{z:.2f} SD from the sample mean<extra></extra>"))
    fig.update_layout(title="What defines each archetype (cluster centre, standard deviations from the mean)",
                      height=140 + 60 * len(c), xaxis=dict(tickangle=-35), margin=dict(l=330), plot_bgcolor="white")
    return fig


def role_parallel(season_pct: pd.DataFrame, family: str, metrics: list[str], min_minutes: float,
                  highlight_team: str | None = None) -> go.Figure:
    """Parallel coordinates of percentile profiles within one role family."""
    d = season_pct[(season_pct["role_family"] == family) & (season_pct["minutes_played"] >= min_minutes)]
    cols = [f"{m}_pct" for m in metrics if f"{m}_pct" in season_pct.columns]
    d = d.dropna(subset=cols)
    if len(d) < 3:
        return _empty("Not enough players.", f"Parallel coordinates — {family}")
    flag = (d["team_name"] == highlight_team).astype(int) if highlight_team else np.zeros(len(d))
    fig = go.Figure(go.Parcoords(line=dict(color=flag, colorscale=[[0, "#c9ced6"], [1, TEAL]], cmin=0, cmax=1),
                                 dimensions=[dict(label=label(c[:-4]), values=d[c], range=[0, 100]) for c in cols]))
    fig.update_layout(title=f"{family}s: percentile profiles across metrics (teal = {highlight_team}; drag on an axis "
                            f"to filter; n={len(d)})", height=460, margin=dict(l=60, r=60, t=90))
    return fig

GALLERY_ACTIONS = {
    "Creating & finishing": ["shots_p90", "key_passes_p90", "dribbles_completed_p90", "box_touches_p90"],
    "Progressing": ["progressive_passes_p90", "progressive_carries_p90", "final_third_passes_p90"],
    "Defending": ["tackles_won_p90", "interceptions_p90", "ball_recoveries_p90", "pressures_p90", "clearances_p90"],
}


def metric_splom(season_pct: pd.DataFrame, metrics: list[str], min_minutes: float) -> go.Figure:
    """Scatter-plot matrix of several per-90 metrics coloured by role family."""
    d = season_pct[(season_pct["minutes_played"] >= min_minutes) & season_pct["role_family"].notna()]
    metrics = [m for m in metrics if m in d.columns]
    if len(d) < 5 or len(metrics) < 3:
        return _empty("Not enough data.", "Scatter-plot matrix")
    fig = go.Figure(go.Splom(dimensions=[dict(label=label(m), values=d[m]) for m in metrics], text=d["player_name"],
                             marker=dict(size=5, color=d["role_family"].map(FAMILY_COLORS).fillna(SLATE), opacity=0.7,
                                         line=dict(color="white", width=0.4)),
                             diagonal=dict(visible=False), showupperhalf=False,
                             hovertemplate="%{text}<extra></extra>"))
    fig.update_layout(title=f"Scatter-plot matrix of per-90 metrics (n={len(d)}; colour = role family)",
                      height=760, dragmode="select", font=dict(size=10))
    return fig


def marginal_scatter(season_pct: pd.DataFrame, x: str, y: str, min_minutes: float) -> go.Figure:
    """Scatter with marginal histogram and box plot, by role family."""
    d = season_pct[(season_pct["minutes_played"] >= min_minutes) & season_pct["role_family"].notna()]
    if d.empty or x not in d or y not in d:
        return _empty("Not enough data.", "Marginal scatter")
    fig = px.scatter(d, x=x, y=y, color="role_family", color_discrete_map=FAMILY_COLORS, hover_name="player_name",
                     marginal_x="histogram", marginal_y="box", opacity=0.8,
                     labels={x: label(x), y: label(y), "role_family": "role family"})
    fig.update_layout(title=f"{label(x)} vs {label(y)} with marginal distributions (n={len(d)})", height=560)
    return fig


def minutes_ecdf(season: pd.DataFrame, team: str) -> go.Figure:
    """Empirical CDF of minutes played: focus squad vs everyone else."""
    if season is None or "minutes_played" not in season:
        return _empty("No data.", "Minutes ECDF")
    d = season[season["minutes_played"] > 0].assign(group=lambda s: np.where(s["team_name"] == team, team, "Opponents"))
    fig = px.ecdf(d, x="minutes_played", color="group", color_discrete_map={team: TEAL, "Opponents": SLATE},
                  markers=True, labels={"minutes_played": "minutes played"})
    fig.update_layout(title="Distribution of playing time (ECDF): opponents rarely exceed two matches in this sample",
                      yaxis_title="share of players ≤ x minutes", height=400)
    return fig


def split_violin(season_pct: pd.DataFrame, metric: str, team: str, min_minutes: float) -> go.Figure:
    """Violin per role family, split focus squad (left) vs others (right)."""
    d = season_pct[(season_pct["minutes_played"] >= min_minutes) & season_pct["role_family"].notna()]
    if d.empty or metric not in d:
        return _empty("Not enough data.", "Violins")
    fig = go.Figure()
    for grp, side, c in ((team, "negative", TEAL), ("Others", "positive", SLATE)):
        g = d[(d["team_name"] == team) == (grp == team)]
        fig.add_trace(go.Violin(x=g["role_family"], y=g[metric], name=grp, side=side, line_color=c,
                                fillcolor=c, opacity=0.55, points="all", pointpos=-0.4 if side == "negative" else 0.4,
                                jitter=0.2, marker=dict(size=4), text=g["player_name"], meanline_visible=True,
                                hovertemplate="%{text}: %{y:.2f}<extra></extra>"))
    fig.update_layout(violinmode="overlay", title=f"{label(metric)} by role family — {team} (left) vs others (right)",
                      yaxis_title=label(metric), height=440, xaxis=dict(categoryorder="array", categoryarray=[
                          "Defender", "Midfielder", "Forward"]))
    return fig


def player_dendrogram(season_pct: pd.DataFrame, team: str, metrics: list[str], min_minutes: float) -> go.Figure:
    """Hierarchical clustering of the squad's per-90 profiles (who plays like whom)."""
    import plotly.figure_factory as ff
    d = season_pct[(season_pct["team_name"] == team) & (season_pct["minutes_played"] >= min_minutes)
                   & (season_pct["primary_role"] != "GK")].dropna(subset=metrics)
    if len(d) < 4:
        return _empty("Not enough players.", "Squad dendrogram")
    X = ((d[metrics] - d[metrics].mean()) / d[metrics].std(ddof=0).replace(0, 1)).values
    names = [f"{n} ({r})" for n, r in zip(d["player_name"], d["primary_role"])]
    fig = ff.create_dendrogram(X, orientation="left", labels=names, colorscale=[NAVY, TEAL, AMBER, RED, PURPLE, SLATE])
    fig.update_layout(title=f"{team}: squad similarity tree (complete-linkage clustering of standardised per-90 profiles)",
                      height=40 + 26 * len(d), margin=dict(l=260), xaxis_title="distance (lower = more similar)",
                      plot_bgcolor=PAPER, paper_bgcolor=PAPER)
    return fig


def lollipop(season_pct: pd.DataFrame, metric: str, min_minutes: float, n: int = 15) -> go.Figure:
    d = season_pct[season_pct["minutes_played"] >= min_minutes].dropna(subset=[metric])
    if d.empty:
        return _empty("No data.", "Lollipop")
    d = d.nlargest(n, metric).iloc[::-1]
    fig = go.Figure()
    for _, r in d.iterrows():
        fig.add_trace(go.Scatter(x=[0, r[metric]], y=[r["player_name"]] * 2, mode="lines", showlegend=False,
                                 line=dict(color=GRID, width=3), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=d[metric], y=d["player_name"], mode="markers+text", text=d[metric].round(2),
                             textposition="middle right", showlegend=False,
                             marker=dict(size=14, color=d["role_family"].map(FAMILY_COLORS).fillna(SLATE),
                                         line=dict(color="white", width=1.5)),
                             customdata=d["team_name"], hovertemplate="%{y} (%{customdata}): %{x:.2f}<extra></extra>"))
    fig.update_layout(title=f"Top {len(d)}: {label(metric)} (min {min_minutes:.0f} min)", height=520,
                      xaxis_title=label(metric), margin=dict(l=200))
    return fig


def slope_chart(pms: pd.DataFrame, team: str, base_metric: str, min_half_minutes: float = 400) -> go.Figure:
    """First half vs second half of the season, per 90, for each regular."""
    p = _rows(pms, "team_name", team)
    msg = _missing(p, ["match_date", "minutes_played", base_metric, "player_name"])
    if msg:
        return _empty(msg, "Slope chart")
    cut = p["match_date"].sort_values().unique()
    cut = cut[len(cut) // 2]
    p = p.assign(half=np.where(p["match_date"] < cut, "First half", "Second half"))
    g = p.groupby(["player_name", "half"])[[base_metric, "minutes_played"]].sum().reset_index()
    g["p90"] = g[base_metric] / g["minutes_played"] * 90
    w = g.pivot(index="player_name", columns="half", values="p90")
    mins = g.pivot(index="player_name", columns="half", values="minutes_played")
    w = w[(mins >= min_half_minutes).all(axis=1)].dropna()
    if w.empty:
        return _empty("No player with enough minutes in both halves.", "Slope chart")
    fig = go.Figure()
    for name, r in w.iterrows():
        up = r["Second half"] >= r["First half"]
        fig.add_trace(go.Scatter(x=["First half", "Second half"], y=[r["First half"], r["Second half"]],
                                 mode="lines+markers+text", text=["", name.split()[-1]], textposition="middle right",
                                 line=dict(color=TEAL if up else RED, width=2), marker=dict(size=8), showlegend=False,
                                 hovertemplate=name + ": %{y:.2f}<extra></extra>"))
    fig.update_layout(title=f"{team}: {label(base_metric + '_p90')} — first vs second half of the season "
                            f"(teal = up, red = down; ≥{min_half_minutes:.0f} min in each half)",
                      yaxis_title="per 90", height=520, margin=dict(r=140))
    return fig


def radar_grid(season_pct: pd.DataFrame, player_ids: list, config: Config) -> go.Figure:
    """Small-multiple radars (role-specific metrics) for up to six players."""
    s = season_pct[season_pct["player_id"].isin(player_ids)].drop_duplicates("player_id")
    if s.empty:
        return _empty("No players.", "Radar grid")
    present = set(s["player_id"])
    s = s.set_index("player_id").loc[[p for p in player_ids if p in present]].reset_index().head(6)
    rows = int(np.ceil(len(s) / 3))
    fig = make_subplots(rows=rows, cols=3, specs=[[{"type": "polar"}] * 3] * rows,
                        subplot_titles=[f"{r['player_name']} ({r['primary_role']})" for _, r in s.iterrows()],
                        vertical_spacing=0.12)
    for i, (_, r) in enumerate(s.iterrows()):
        ms = [m for m in radar_metrics(r["primary_role"], config) if f"{m}_pct" in s.columns]
        th = [label(m) for m in ms]
        v = [float(r[f"{m}_pct"]) if pd.notna(r[f"{m}_pct"]) else 0 for m in ms]
        fig.add_trace(go.Scatterpolar(r=v + v[:1], theta=th + th[:1], fill="toself", showlegend=False,
                                      line=dict(color=COLORWAY[i % len(COLORWAY)], width=2),
                                      hovertemplate="%{theta}: %{r:.0f}th pct<extra></extra>"),
                      row=i // 3 + 1, col=i % 3 + 1)
    fig.update_polars(radialaxis=dict(range=[0, 100], showticklabels=False, gridcolor=GRID),
                      angularaxis=dict(tickfont=dict(size=8), gridcolor=GRID), bgcolor=PAPER)
    fig.update_layout(title="Key players at a glance — role-specific percentile radars", height=420 * rows,
                      margin=dict(t=110))
    return fig


def action_ternary(season_pct: pd.DataFrame, min_minutes: float, team: str | None = None) -> go.Figure:
    """Ternary plot of each player's action mix: creating/finishing vs progressing vs defending."""
    d = season_pct[(season_pct["minutes_played"] >= min_minutes) & (season_pct["primary_role"] != "GK")].copy()
    if d.empty:
        return _empty("No data.", "Action mix")
    for k, ms in GALLERY_ACTIONS.items():
        d[k] = d[[m for m in ms if m in d]].fillna(0).sum(axis=1)
    tot = d[list(GALLERY_ACTIONS)].sum(axis=1).replace(0, np.nan)
    a, b, c = (d[k] / tot * 100 for k in GALLERY_ACTIONS)
    hi = (d["team_name"] == team) if team else pd.Series(False, index=d.index)
    fig = go.Figure(go.Scatterternary(a=a, b=b, c=c, mode="markers+text",
                                      text=[n.split()[-1] if h else "" for n, h in zip(d["player_name"], hi)],
                                      textposition="top center", textfont=dict(size=8),
                                      marker=dict(size=np.where(hi, 11, 7), color=d["role_family"].map(FAMILY_COLORS).fillna(SLATE),
                                                  opacity=0.8, line=dict(color="white", width=0.6)),
                                      customdata=np.stack([d["player_name"], d["team_name"]], -1),
                                      hovertemplate="%{customdata[0]} (%{customdata[1]})<br>create %{a:.0f}% · progress "
                                                    "%{b:.0f}% · defend %{c:.0f}%<extra></extra>"))
    fig.update_layout(title=f"Action mix of every outfield player (share of per-90 actions; n={len(d)}; labels = {team})",
                      ternary=dict(sum=100, aaxis=dict(title="Creating & finishing"), baxis=dict(title="Progressing"),
                                   caxis=dict(title="Defending"), bgcolor=PAPER), height=600)
    return fig


def contribution_matrix(pms: pd.DataFrame, matches: pd.DataFrame, team: str) -> go.Figure:
    """Player × match heatmap of xG + xA: where the chances came from, match by match."""
    p = _rows(pms, "team_name", team)
    msg = _missing(p, ["xg", "xa", "player_name", "match_id"])
    if msg:
        return _empty(msg, "Contribution matrix")
    p = p.assign(v=p["xg"] + p["xa"])
    piv = p.pivot_table(index="player_name", columns="match_id", values="v", aggfunc="sum")
    order = matches[matches["match_id"].isin(piv.columns)].sort_values("match_date")
    piv = piv.reindex(columns=order["match_id"])
    piv = piv.loc[piv.sum(axis=1).sort_values(ascending=False).index]
    piv = piv[piv.sum(axis=1) > 0.3]
    lab = [f"{d:%d %b} {(a if h == team else h)[:10]}" for d, h, a in zip(order["match_date"], order["home_team"],
                                                                        order["away_team"])]
    fig = go.Figure(go.Heatmap(z=piv.values, x=lab, y=list(piv.index), colorscale=SEQ_SCALE, xgap=1, ygap=1,
                               colorbar=dict(title="xG+xA", thickness=12),
                               hovertemplate="%{y}<br>%{x}: %{z:.2f} xG+xA<extra></extra>"))
    fig.update_layout(title=f"{team}: chance contribution per player per match (xG + xA; blank = did not play)",
                      height=max(420, 22 * len(piv) + 180), xaxis=dict(tickangle=-60, tickfont=dict(size=8)),
                      yaxis=dict(autorange="reversed"), margin=dict(l=190, b=120), plot_bgcolor="white")
    return fig


def squad_percentile_heatmap(season_pct: pd.DataFrame, team: str, metrics: list[str], min_minutes: float,
                             banner: str | None = None) -> go.Figure:
    """Squad × metric percentile matrix (benchmark group stated in the hover)."""
    s = _rows(season_pct, "team_name", team)
    cols = [f"{m}_pct" for m in metrics]
    msg = _missing(s, ["player_name", "primary_role", "minutes_played"] + cols)
    if msg:
        return _empty(msg, f"Squad percentile profile — {team}")
    s = s[(s["minutes_played"] >= min_minutes) & (s["primary_role"] != "GK")].copy()
    if s.empty:
        return _empty("No eligible outfield players.", f"Squad percentile profile — {team}")
    s["role_rank"] = s["primary_role"].map({r: i for i, r in enumerate(ROLE_ORDER)})
    s = s.sort_values(["role_rank", "minutes_played"], ascending=[True, False])
    ylab = [f"{n} ({r})" for n, r in zip(s["player_name"], s["primary_role"])]
    raw = s[metrics].to_numpy(dtype=float)
    fig = go.Figure(go.Heatmap(
        z=s[cols].to_numpy(dtype=float), x=[label(m) for m in metrics], y=ylab, zmin=0, zmax=100, colorscale=DIV_SCALE,
        zmid=50, text=np.round(s[cols].to_numpy(dtype=float)), texttemplate="%{text:.0f}", textfont=dict(size=9),
        customdata=np.dstack([raw, np.repeat(s["benchmark_group"].to_numpy()[:, None], len(metrics), axis=1)]),
        xgap=1, ygap=1, colorbar=dict(title="percentile", thickness=12),
        hovertemplate="%{y}<br>%{x}: %{z:.0f}th pct<br>value %{customdata[0]:.2f} · vs %{customdata[1]}"
                      "<extra></extra>"))
    fig.update_layout(title=f"{team}: squad profile — percentile per metric (blue = high, red = low; min "
                            f"{min_minutes:.0f} min)", height=max(420, 24 * len(s) + 200),
                      xaxis=dict(tickangle=-35, side="top"), yaxis=dict(autorange="reversed"),
                      margin=dict(l=230, t=230), title_y=0.99, plot_bgcolor="white")
    return add_banner(fig, banner)


def minutes_sunburst(season: pd.DataFrame, team: str, banner: str | None = None) -> go.Figure:
    """Role family → role → player, sized by minutes: how playing time is distributed."""
    s = _rows(season, "team_name", team)
    msg = _missing(s, ["player_name", "primary_role", "role_family", "minutes_played"])
    if msg:
        return _empty(msg, f"Minutes distribution — {team}")
    s = s[(s["minutes_played"] > 0) & s["primary_role"].notna()]
    ids, labels, parents, values, colors = [], [], [], [], []
    for fam, gf in s.groupby("role_family"):
        ids.append(fam); labels.append(fam); parents.append(""); values.append(gf["minutes_played"].sum())
        colors.append(FAMILY_COLORS.get(fam, SLATE))
        for role, gr in gf.groupby("primary_role"):
            rid = f"{fam}/{role}"
            ids.append(rid); labels.append(ROLE_LABEL.get(role, role)); parents.append(fam)
            values.append(gr["minutes_played"].sum()); colors.append(FAMILY_COLORS.get(fam, SLATE))
            for _, p in gr.iterrows():
                ids.append(f"{rid}/{p['player_id']}"); labels.append(p["player_name"]); parents.append(rid)
                values.append(p["minutes_played"]); colors.append(FAMILY_COLORS.get(fam, SLATE))
    fig = go.Figure(go.Sunburst(ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
                                marker=dict(colors=colors, line=dict(color="white", width=1)),
                                insidetextorientation="radial",
                                hovertemplate="<b>%{label}</b><br>%{value:,.0f} minutes<br>%{percentRoot:.1%} of "
                                              "team minutes<extra></extra>"))
    fig.update_layout(title=f"{team}: distribution of playing time (role family → role → player; click to zoom)",
                      height=620, margin=dict(t=70, l=10, r=10, b=10))
    return add_banner(fig, banner)
