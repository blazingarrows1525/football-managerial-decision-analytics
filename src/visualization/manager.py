"""Substitution and managerial-pattern charts."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import ROLE_FAMILY
from src.visualization.theme import AMBER, COLORWAY, GRID, INK, NAVY, RED, RESULT_COLORS, SEQ_SCALE, SLATE, STATE_COLORS, TEAL, _empty, _missing, _rows, add_banner, source_note


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


def subs_parcats(subs: pd.DataFrame, team: str) -> go.Figure:
    """Parallel categories: game state → timing band → role change of each substitution."""
    s = _rows(subs, "team_name", team)
    msg = _missing(s, ["game_state", "timing_band", "off_role", "on_role"])
    if msg:
        return _empty(msg, "Substitution pathways")
    s = s.dropna(subset=["off_role", "on_role"])
    fam = {r: ROLE_FAMILY.get(r, r) for r in ROLE_FAMILY}
    s = s.assign(off=s["off_role"].map(fam), on=s["on_role"].map(fam))
    code = s["game_state"].map({"leading": 0, "drawing": 1, "trailing": 2})
    fig = go.Figure(go.Parcats(
        dimensions=[dict(label="Game state", values=s["game_state"]), dict(label="Timing band", values=s["timing_band"]),
                    dict(label="Off (role family)", values=s["off"]), dict(label="On (role family)", values=s["on"])],
        line=dict(color=code, colorscale=[[0, TEAL], [0.5, SLATE], [1, RED]], shape="hspline"),
        hoveron="color", arrangement="freeform"))
    fig.update_layout(title=f"{team}: substitution pathways — state → timing → who goes off → who comes on "
                            f"({len(s)} changes; teal = leading, grey = drawing, red = trailing)", height=520,
                      margin=dict(l=80, r=80))
    return fig


def subs_team_band_heatmap(subs: pd.DataFrame, bands: list[dict], banner: str | None = None) -> go.Figure:
    """Team × timing band share of substitutions (sorted by median substitution minute)."""
    msg = _missing(subs, ["team_name", "timing_band", "minute"])
    if msg:
        return _empty(msg, "Substitution timing by team")
    order = [b["label"] for b in bands]
    ct = pd.crosstab(subs["team_name"], subs["timing_band"]).reindex(columns=order, fill_value=0)
    teams = subs.groupby("team_name")["minute"].median().sort_values().index
    ct = ct.reindex(teams)
    share = ct.div(ct.sum(axis=1), axis=0) * 100
    n = ct.sum(axis=1)
    fig = go.Figure(go.Heatmap(z=share.values, x=order, y=[f"{t} (n={n[t]})" for t in ct.index], colorscale=SEQ_SCALE,
                               zmin=0, text=ct.values, texttemplate="%{text}", xgap=2, ygap=2,
                               colorbar=dict(title="% of team's<br>subs", thickness=12),
                               hovertemplate="%{y}<br>%{x}: %{z:.0f}% (%{text} subs)<extra></extra>"))
    fig.update_layout(title="When each team substitutes (rows sorted earliest → latest median minute; numbers = "
                            "substitutions)", height=max(420, 26 * len(ct) + 160), margin=dict(l=230),
                      yaxis=dict(autorange="reversed"), plot_bgcolor="white")
    source_note(fig, "Opponents appear in 1-2 matches each and always faced the focus team — descriptive only.")
    return add_banner(fig, banner)
