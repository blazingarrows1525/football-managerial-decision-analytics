"""Team and match-level charts added in V3 (catalogue family C).

Metric definitions used in subtitles (all computed in ``src.features.team_features``):

* possession proxy = team passes / (team passes + opponent passes): a pass-share proxy, not timed possession;
* field tilt = team final-third touches / both teams' final-third touches;
* PPDA = opponent passes attempted in their own 60% of the pitch (x <= 72) / the team's tackles,
  interceptions, fouls and failed challenges in the same zone (lower = more intense pressing proxy).
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.visualization.distribution import nice
from src.visualization.theme import (AMBER, COLORWAY, DIV_SCALE, INK, MUTED, NAVY, RED, RESULT_COLORS,
                                     SEQ_SCALE, SLATE, STATE_COLORS, TEAL, _empty, _missing, _mlabel, _team, low_sample, sub)

STATE_ORDER = ["leading", "drawing", "trailing"]


def _labels(t: pd.DataFrame) -> list[str]:
    return [_mlabel(r) for _, r in t.iterrows()]


def xg_diff_distribution(team_stats: pd.DataFrame | None, team: str) -> go.Figure:
    """Histogram of per-match xG difference with the mean, median and the share of matches above zero."""
    t = _team(team_stats, team)
    msg = _missing(t, ["xg_diff", "result"])
    if msg:
        return _empty(msg, "xG difference distribution")
    fig = go.Figure()
    for res, name in (("W", "win"), ("D", "draw"), ("L", "loss")):
        g = t[t["result"] == res]
        if len(g):
            fig.add_trace(go.Histogram(x=g["xg_diff"], name=f"{name} ({len(g)})", marker_color=RESULT_COLORS[res],
                                       xbins=dict(size=0.5)))
    fig.add_vline(x=0, line=dict(color=INK, width=1))
    fig.add_vline(x=t["xg_diff"].mean(), line=dict(color=AMBER, dash="dash"),
                  annotation_text=f"mean {t['xg_diff'].mean():+.2f}", annotation_position="top")
    fig.update_layout(barmode="stack", bargap=0.05,
                      title=sub(f"{team}: distribution of xG difference per match",
                                f"n = {len(t)} matches · median {t['xg_diff'].median():+.2f} · "
                                f"{(t['xg_diff'] > 0).mean():.0%} of matches above zero · bins of 0.5 xG"
                                + low_sample(len(t), 20, "matches")),
                      xaxis_title="xG for − xG against (StatsBomb xG)", yaxis_title="matches", height=420)
    return fig


def shot_volume_quality(team_stats: pd.DataFrame | None, team: str) -> go.Figure:
    """Shots per match against mean xG per shot, for the team and for its opponents in the same matches."""
    t = _team(team_stats, team)
    msg = _missing(t, ["shots", "xg", "shots_against", "xg_against"])
    if msg:
        return _empty(msg, "Shot volume vs shot quality")
    lab = _labels(t)
    fig = go.Figure()
    for name, s, x, c in ((team, t["shots"], t["xg"], NAVY), ("Opponents", t["shots_against"], t["xg_against"], RED)):
        q = np.where(s > 0, x / s.replace(0, np.nan), np.nan)
        fig.add_trace(go.Scatter(x=s, y=q, mode="markers", name=f"{name} (mean {s.mean():.1f} shots, "
                                 f"{x.sum() / max(s.sum(), 1):.3f} xG/shot)",
                                 marker=dict(size=10, color=c, opacity=0.75, line=dict(color="white", width=1)),
                                 text=lab, hovertemplate="%{text}<br>%{x} shots · %{y:.3f} xG/shot<extra></extra>"))
    fig.update_layout(title=sub(f"{team}: shot volume vs shot quality, by match",
                                f"n = {len(t)} matches · each point is one side in one match · xG/shot = sum of "
                                f"StatsBomb xG / shots"),
                      xaxis_title="shots in the match", yaxis_title="mean xG per shot", height=440,
                      legend=dict(orientation="h", y=-0.2))
    return fig


def shots_conversion_by_match(team_stats: pd.DataFrame | None, team: str) -> go.Figure:
    """Shots and goals per match (bars) with the season conversion rate stated; no second axis."""
    t = _team(team_stats, team)
    msg = _missing(t, ["shots", "goals_for", "shots_on_target"])
    if msg:
        return _empty(msg, "Shots and conversion by match")
    lab = _labels(t)
    fig = go.Figure()
    fig.add_bar(x=lab, y=t["shots"], name="shots", marker_color="#c9d3df")
    fig.add_bar(x=lab, y=t["shots_on_target"], name="on target", marker_color=TEAL)
    fig.add_bar(x=lab, y=t["goals_for"], name="goals", marker_color=AMBER)
    conv = t["goals_for"].sum() / max(t["shots"].sum(), 1)
    fig.update_layout(barmode="overlay", title=sub(f"{team}: shots, shots on target and goals by match",
                                                   f"n = {len(t)} matches · season conversion {conv:.1%} "
                                                   f"({int(t['goals_for'].sum())} goals incl. own goals for / "
                                                   f"{int(t['shots'].sum())} shots) · bars are nested, not stacked"),
                      yaxis_title="count", height=460, xaxis=dict(tickangle=-60, tickfont=dict(size=9)),
                      legend=dict(orientation="h", y=1.08))
    return fig


def score_state_share(state_time: pd.DataFrame | None, team: str) -> go.Figure:
    """Share of match time spent leading, drawing and trailing, per match and overall."""
    msg = _missing(state_time, STATE_ORDER + ["opponent", "match_date"])
    if msg:
        return _empty(msg, "Score-state time share")
    d = state_time.sort_values("match_date")
    lab = [f"{dt:%d %b} {str(o)[:12]} ({r})" for dt, o, r in zip(d["match_date"], d["opponent"], d["result"])]
    tot = d[STATE_ORDER].sum()
    fig = go.Figure()
    for s in STATE_ORDER:
        fig.add_bar(y=lab, x=d[s], orientation="h", name=f"{s} ({tot[s] / tot.sum():.0%} of all minutes)",
                    marker_color=STATE_COLORS[s], hovertemplate="%{y}: %{x:.0f} min " + s + "<extra></extra>")
    fig.update_layout(barmode="stack", title=sub(f"{team}: minutes leading, drawing and trailing",
                                                 f"n = {len(d)} matches · {tot.sum():,.0f} minutes incl. stoppage · "
                                                 f"state from the reconstructed goal timeline"),
                      xaxis_title="minutes", yaxis=dict(autorange="reversed", tickfont=dict(size=9)),
                      height=max(420, 20 * len(d) + 150), margin=dict(l=190), legend=dict(orientation="h", y=1.05))
    return fig


def score_state_timeline(segments: pd.DataFrame | None, goals: pd.DataFrame | None, team: str, opponent: str,
                         team_id: Any) -> go.Figure:
    """Score state of one match over time with goals marked."""
    msg = _missing(segments, ["start", "end", "state", "goal_diff"])
    if msg:
        return _empty(msg, "Match-state timeline")
    fig = go.Figure()
    for r in segments.itertuples():
        fig.add_trace(go.Scatter(x=[r.start, r.end, r.end, r.start], y=[0, 0, 1, 1], fill="toself", mode="lines",
                                 fillcolor=STATE_COLORS[r.state], line=dict(width=0), showlegend=False,
                                 hovertemplate=f"{r.state} ({r.goal_diff:+d}) from {r.start:.0f}' to {r.end:.0f}'"
                                               "<extra></extra>"))
    if goals is not None and len(goals):
        for g in goals.itertuples():
            own = g.scoring_team_id == team_id
            fig.add_annotation(x=g.elapsed_min, y=1.02, text="⚽", showarrow=False, yanchor="bottom",
                               hovertext=f"{g.player_name} ({team if own else opponent}) {int(g.minute)}'")
            fig.add_vline(x=g.elapsed_min, line=dict(color=NAVY if own else RED, width=2))
    mins = segments.groupby("state")["minutes"].sum().reindex(STATE_ORDER).fillna(0)
    fig.update_layout(title=sub(f"{team} vs {opponent}: score state over the match",
                                " · ".join(f"{s} {mins[s]:.0f} min" for s in STATE_ORDER)
                                + " · elapsed playing minutes incl. stoppage · vertical lines = goals"),
                      xaxis_title="elapsed minutes", yaxis=dict(visible=False, range=[0, 1.25]), height=260)
    return fig


def team_percentile_profile(team_stats: pd.DataFrame | None, team: str, metrics: list[str] | None = None
                            ) -> go.Figure:
    """Where the team's median match sits among all team-match rows in the dataset, per metric.

    The reference set is every team-match in the analysed files. Because every match involves the focus team,
    this compares the team with its own opponents on the day, not with the league.
    """
    metrics = metrics or ["xg", "shots", "possession_proxy_pct", "field_tilt_pct", "pass_completion_pct",
                          "progressive_passes", "pressures", "ppda", "xg_against", "shots_against"]
    t = _team(team_stats, team)
    msg = _missing(t, metrics)
    if msg:
        return _empty(msg, "Team percentile profile")
    lower_better = {"ppda", "xg_against", "shots_against"}
    rows = []
    for m in metrics:
        allv = team_stats[m].dropna().to_numpy(float)
        med = float(t[m].median())
        pct = float((allv < med).mean() * 100)
        rows.append((m, 100 - pct if m in lower_better else pct, med))
    rows = rows[::-1]
    fig = go.Figure(go.Bar(y=[nice(m) + (" (lower = better)" if m in lower_better else "") for m, _, _ in rows],
                           x=[p for _, p, _ in rows], orientation="h",
                           marker_color=[TEAL if p >= 67 else SLATE if p >= 34 else AMBER for _, p, _ in rows],
                           text=[f"{p:.0f}  ·  median {v:.2f}" for _, p, v in rows], textposition="outside",
                           cliponaxis=False))
    fig.add_vline(x=50, line=dict(color=MUTED, dash="dot"))
    fig.update_layout(title=sub(f"{team}: percentile of the median match",
                                f"reference = all {len(team_stats)} team-match rows in the dataset (the team and its "
                                f"opponents on the day — not a league benchmark) · direction flipped where lower is "
                                f"better"),
                      xaxis=dict(title="percentile (favourable direction)", range=[0, 125]),
                      height=max(400, 30 * len(rows) + 130), margin=dict(l=250))
    return fig


def match_metric_heatmap(team_stats: pd.DataFrame | None, team: str, metrics: list[str] | None = None) -> go.Figure:
    """Raw match values, coloured by each column's own min-max range (values are printed)."""
    metrics = metrics or ["goals_for", "goals_against", "xg", "xg_against", "shots", "possession_proxy_pct",
                          "field_tilt_pct", "pass_completion_pct", "ppda"]
    t = _team(team_stats, team)
    msg = _missing(t, metrics)
    if msg:
        return _empty(msg, "Match-by-match heatmap")
    v = t[metrics].astype(float)
    rng = (v.max() - v.min()).replace(0, 1)
    z = ((v - v.min()) / rng).to_numpy()
    fig = go.Figure(go.Heatmap(z=z, x=[nice(m) for m in metrics], y=_labels(t), colorscale=SEQ_SCALE, xgap=2, ygap=2,
                               text=np.round(v.to_numpy(), 2), texttemplate="%{text}", textfont=dict(size=9),
                               showscale=False, hovertemplate="%{y}<br>%{x}: %{text}<extra></extra>"))
    fig.update_layout(title=sub(f"{team}: match-by-match metric table",
                                f"n = {len(t)} matches · colour = position within each column's own range (not "
                                f"comparable across columns) · numbers are the raw values"),
                      yaxis=dict(autorange="reversed", tickfont=dict(size=9)),
                      height=max(480, 21 * len(t) + 160), margin=dict(l=190))
    return fig


def formation_timeline(team_stats: pd.DataFrame | None, team: str) -> go.Figure:
    """Starting formation of every match in date order, coloured by result, with in-match changes marked."""
    t = _team(team_stats, team)
    msg = _missing(t, ["starting_formation", "match_date", "result", "in_match_formation_changes"])
    if msg:
        return _empty(msg, "Formation timeline")
    t = t.dropna(subset=["starting_formation"])
    if t.empty:
        return _empty("No formation records for this team.", "Formation timeline")
    fig = go.Figure()
    for res, name in (("W", "win"), ("D", "draw"), ("L", "loss")):
        g = t[t["result"] == res]
        if len(g):
            fig.add_trace(go.Scatter(x=g["match_date"], y=g["starting_formation"], mode="markers", name=name,
                                     marker=dict(size=14, color=RESULT_COLORS[res], line=dict(color="white", width=1.5),
                                                 symbol=["diamond" if c else "circle"
                                                         for c in g["in_match_formation_changes"] > 0]),
                                     text=g["opponent"], customdata=g["in_match_formation_changes"],
                                     hovertemplate="%{x|%d %b %Y} vs %{text}<br>%{y} · %{customdata} in-match "
                                                   "change(s)<extra></extra>"))
    counts = t["starting_formation"].value_counts()
    fig.update_layout(title=sub(f"{team}: starting formation by match",
                                f"n = {len(t)} matches · {len(counts)} formations as recorded on the Starting XI event · "
                                f"diamond = at least one Tactical Shift later in the match · a recorded formation is a "
                                f"nominal label, not the shape in every phase"),
                      yaxis=dict(title="starting formation", categoryorder="array", categoryarray=counts.index[::-1]),
                      height=380, legend=dict(orientation="h", y=-0.2))
    return fig


def origin_split_chart(split: pd.DataFrame | None, team: str) -> go.Figure:
    """Shots, xG and goals by how the possession started, for and against."""
    msg = _missing(split, ["side", "origin", "shots", "xg", "goals"])
    if msg:
        return _empty(msg, "Set-piece vs open-play contribution")
    fig = make_subplots(rows=1, cols=3, subplot_titles=["Shots", "xG (StatsBomb)", "Goals"])
    origins = list(split["origin"].unique())
    for c, col in enumerate(("shots", "xg", "goals"), 1):
        for i, o in enumerate(origins):
            d = split[split["origin"] == o].set_index("side").reindex(["for", "against"])
            fig.add_bar(x=[f"{team[:14]}", "Opponents"], y=d[col], name=o, marker_color=COLORWAY[i],
                        showlegend=c == 1, legendgroup=o, text=[f"{v:.1f}" if col == "xg" else f"{v:.0f}"
                                                               for v in d[col].fillna(0)],
                        textposition="inside", row=1, col=c)
    fig.update_layout(barmode="stack", title=sub(f"{team}: how shots originate",
                                                 "restart-initiated = possession began with a corner, free kick or "
                                                 "throw-in (source play_pattern; includes open play that follows the "
                                                 "restart) · penalties shown separately · own goals are not shots"),
                      height=440, legend=dict(orientation="h", y=-0.12))
    return fig


def territory_proxies(team_stats: pd.DataFrame | None, team: str) -> go.Figure:
    """Possession proxy (pass share) and field tilt (final-third touch share) by match."""
    t = _team(team_stats, team)
    msg = _missing(t, ["possession_proxy_pct", "field_tilt_pct"])
    if msg:
        return _empty(msg, "Possession and territory proxies")
    lab = _labels(t)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=lab, y=t["possession_proxy_pct"], mode="lines+markers", name="possession proxy "
                             f"(mean {t['possession_proxy_pct'].mean():.1f}%)", line=dict(color=NAVY, width=2)))
    fig.add_trace(go.Scatter(x=lab, y=t["field_tilt_pct"], mode="lines+markers", name="field tilt "
                             f"(mean {t['field_tilt_pct'].mean():.1f}%)", line=dict(color=TEAL, width=2)))
    fig.add_hline(y=50, line=dict(color=MUTED, dash="dot"))
    fig.update_layout(title=sub(f"{team}: pass-share possession proxy and field tilt",
                                f"n = {len(t)} matches · possession proxy = passes / both teams' passes (not timed "
                                f"possession) · field tilt = final-third touches / both teams' final-third touches"),
                      yaxis=dict(title="% share", range=[20, 90]), height=440,
                      xaxis=dict(tickangle=-60, tickfont=dict(size=9)), legend=dict(orientation="h", y=1.08))
    return fig


def pass_progression_profile(team_stats: pd.DataFrame | None, team: str) -> go.Figure:
    """Pass completion against progressive passes per match, coloured by result."""
    t = _team(team_stats, team)
    msg = _missing(t, ["pass_completion_pct", "progressive_passes", "passes", "result"])
    if msg:
        return _empty(msg, "Pass completion and progression")
    fig = go.Figure()
    for res, name in (("W", "win"), ("D", "draw"), ("L", "loss")):
        g = t[t["result"] == res]
        if len(g):
            fig.add_trace(go.Scatter(x=g["pass_completion_pct"], y=g["progressive_passes"], mode="markers", name=name,
                                     marker=dict(size=6 + g["passes"] / g["passes"].max() * 14,
                                                 color=RESULT_COLORS[res], opacity=0.8,
                                                 line=dict(color="white", width=1)),
                                     text=[_mlabel(r) for _, r in g.iterrows()],
                                     hovertemplate="%{text}<br>%{x:.1f}% completed · %{y} progressive"
                                                   "<extra></extra>"))
    fig.update_layout(title=sub(f"{team}: pass completion vs progressive passes by match",
                                f"n = {len(t)} matches · marker size = pass attempts · progressive = completed, starts "
                                f"at x ≥ 48 and ends ≥ 25% closer to goal (project definition)"),
                      xaxis_title="pass completion %", yaxis_title="progressive passes", height=440)
    return fig


def defensive_actions_by_match(flags: pd.DataFrame | None, team_stats: pd.DataFrame | None, team: str) -> go.Figure:
    """Defensive actions by type in every match."""
    t = _team(team_stats, team)
    cols = ["tackles", "interceptions", "blocks", "clearances", "ball_recoveries"]
    msg = _missing(t, ["match_id", "team_id"]) or _missing(flags, cols + ["match_id", "team_id"])
    if msg:
        return _empty(msg, "Defensive actions by match")
    tid = t["team_id"].iloc[0]
    agg = flags[flags["team_id"] == tid].groupby("match_id")[cols].sum().reindex(t["match_id"]).fillna(0)
    lab = _labels(t)
    fig = go.Figure()
    for i, c in enumerate(cols):
        fig.add_bar(x=lab, y=agg[c].to_numpy(), name=f"{nice(c)} (mean {agg[c].mean():.1f})",
                    marker_color=COLORWAY[i])
    fig.update_layout(barmode="stack", title=sub(f"{team}: defensive actions by match",
                                                 f"n = {len(t)} matches · event counts, not adjusted for opponent "
                                                 f"possession (a team with the ball defends less)"),
                      yaxis_title="actions", height=460, xaxis=dict(tickangle=-60, tickfont=dict(size=9)),
                      legend=dict(orientation="h", y=1.1))
    return fig


def ppda_distribution(team_stats: pd.DataFrame | None, team: str) -> go.Figure:
    """PPDA per match for the team and for its opponents, as box plots with points."""
    t = _team(team_stats, team)
    msg = _missing(t, ["ppda", "match_id"])
    if msg:
        return _empty(msg, "PPDA distribution")
    opp = team_stats[team_stats["match_id"].isin(t["match_id"]) & (team_stats["team_name"] != team)]
    fig = go.Figure()
    for name, d, c in ((team, t, NAVY), ("Opponents (same matches)", opp, RED)):
        v = d["ppda"].dropna()
        fig.add_trace(go.Box(y=v, name=f"{name} (n={len(v)}, median {v.median():.1f})", boxpoints="all", jitter=0.4,
                             pointpos=-1.6, marker=dict(color=c, size=6, opacity=0.7), line=dict(color=c),
                             text=[_mlabel(r) for _, r in d.dropna(subset=["ppda"]).iterrows()],
                             hovertemplate="%{text}<br>PPDA %{y:.1f}<extra></extra>"))
    fig.update_layout(title=sub("Pressing proxy: PPDA per match",
                                "PPDA = opponent passes in their own 60% of the pitch / the team's tackles, "
                                "interceptions, fouls and failed challenges there · lower = more defensive actions per "
                                "opponent pass · a proxy built from events, not a measure of pressing quality"),
                      yaxis_title="PPDA (lower = more intense)", height=440, showlegend=False)
    return fig


def team_consistency_chart(z: pd.DataFrame | None, cv: pd.Series | None, team: str) -> go.Figure:
    """Within-season z-scores per match (left) and the coefficient of variation of each metric (right)."""
    if z is None or z.empty or cv is None or cv.empty:
        return _empty("No team-match rows for this selection.", "Team consistency")
    fig = make_subplots(rows=1, cols=2, column_widths=[0.68, 0.32], horizontal_spacing=0.12,
                        subplot_titles=["z-score per match (blue = favourable)", "coefficient of variation"])
    fig.add_trace(go.Heatmap(z=z.to_numpy(), x=[nice(c) for c in z.columns], y=list(z.index), colorscale=DIV_SCALE,
                             zmid=0, zmin=-2.5, zmax=2.5, xgap=1, ygap=1, colorbar=dict(title="z", thickness=10, x=0.6),
                             hovertemplate="%{y}<br>%{x}: z = %{z:.2f}<extra></extra>"), 1, 1)
    fig.add_trace(go.Bar(y=[nice(c) for c in cv.index], x=cv.values, orientation="h", marker_color=TEAL,
                         text=[f"{v:.2f}" for v in cv.values], textposition="outside", showlegend=False), 1, 2)
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=9), row=1, col=1)
    fig.update_layout(title=sub(f"{team}: match-to-match consistency",
                                f"n = {len(z)} matches · z-scores are within this team-season; sign flipped for xG "
                                f"against and PPDA so blue is always favourable · CV = SD / |mean| of the raw values"),
                      height=max(520, 20 * len(z) + 170), margin=dict(l=190))
    return fig


def xpts_chart(xpts: pd.DataFrame | None, team: str) -> go.Figure:
    """Cumulative points against cumulative expected points from shot-level simulation."""
    msg = _missing(xpts, ["team_name", "match_date", "xpts", "points"])
    if msg:
        return _empty(msg, "Points vs expected points")
    d = xpts[xpts["team_name"] == team].sort_values("match_date")
    if d.empty:
        return _empty("No matches for this team.", "Points vs expected points")
    md = np.arange(1, len(d) + 1)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=md, y=d["points"].cumsum(), mode="lines+markers", name="actual points",
                             line=dict(color=NAVY, width=3)))
    fig.add_trace(go.Scatter(x=md, y=d["xpts"].cumsum(), mode="lines+markers", name="expected points (xPts)",
                             line=dict(color=AMBER, width=3, dash="dash")))
    fig.update_layout(title=sub(f"{team}: cumulative points vs expected points",
                                f"n = {len(d)} matches · {d['points'].sum():.0f} points vs {d['xpts'].sum():.1f} xPts · "
                                f"xPts = each shot simulated as a Bernoulli trial with its StatsBomb xG; a model "
                                f"output, not an observation"),
                      xaxis_title="matchday (chronological)", yaxis_title="cumulative points", height=440,
                      legend=dict(orientation="h", y=-0.2))
    return fig


def team_style_quadrant(team_stats: pd.DataFrame | None, focus: str | None = None, min_matches: int = 1
                        ) -> go.Figure:
    """Mean possession proxy against mean xG difference for every team in the dataset (size = matches)."""
    msg = _missing(team_stats, ["team_name", "possession_proxy_pct", "xg_diff", "match_id"])
    if msg:
        return _empty(msg, "Team style quadrant")
    g = team_stats.groupby("team_name").agg(matches=("match_id", "nunique"),
                                            possession=("possession_proxy_pct", "mean"), xg_diff=("xg_diff", "mean"),
                                            ppda=("ppda", "mean")).reset_index()
    g = g[g["matches"] >= min_matches]
    fig = go.Figure(go.Scatter(x=g["possession"], y=g["xg_diff"], mode="markers+text",
                               text=g["team_name"].str[:14], textposition="top center", textfont=dict(size=9),
                               marker=dict(size=8 + 3 * np.sqrt(g["matches"]) * 3,
                                           color=[AMBER if t == focus else NAVY for t in g["team_name"]],
                                           opacity=0.8, line=dict(color="white", width=1)),
                               customdata=np.stack([g["matches"], g["ppda"].round(1)], -1),
                               hovertemplate="%{text}<br>%{customdata[0]} match(es) · PPDA %{customdata[1]}"
                                             "<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=MUTED, dash="dot"))
    fig.add_vline(x=50, line=dict(color=MUTED, dash="dot"))
    one_two = int((g["matches"] <= 2).sum())
    fig.update_layout(title=sub("Team style quadrant: possession proxy vs xG difference",
                                f"{len(g)} teams · marker size = matches in the dataset · {one_two} teams have only "
                                f"two matches, all against the focus team — their position reflects that fixture, "
                                f"not their season"),
                      xaxis_title="mean possession proxy % (pass share)", yaxis_title="mean xG difference per match",
                      height=520)
    return fig


def goal_origin_bars(goals: pd.DataFrame | None, team: str) -> go.Figure:
    """Goals scored and conceded by play pattern and by body part."""
    msg = _missing(goals, ["side", "how", "body"])
    if msg:
        return _empty(msg, "Goals by origin")
    fig = make_subplots(rows=1, cols=2, subplot_titles=["by play pattern", "by body part"], horizontal_spacing=0.2)
    for c, col in enumerate(("how", "body"), 1):
        tab = pd.crosstab(goals[col], goals["side"]).reindex(columns=["scored", "conceded"], fill_value=0)
        tab = tab.sort_values("scored")
        for name, color in (("scored", NAVY), ("conceded", RED)):
            fig.add_bar(y=tab.index, x=tab[name], orientation="h", name=name, marker_color=color,
                        showlegend=c == 1, legendgroup=name, row=1, col=c)
    n_s, n_c = int((goals["side"] == "scored").sum()), int((goals["side"] == "conceded").sum())
    fig.update_layout(barmode="group", title=sub(f"{team}: goals scored and conceded",
                                                 f"{n_s} scored · {n_c} conceded · play pattern = how the possession "
                                                 f"started (source field); own goals have no shot attributes"),
                      height=440, legend=dict(orientation="h", y=-0.12))
    return fig


def goalkeeping_chart(gk: pd.DataFrame | None) -> go.Figure:
    """Goalkeeper shot-stopping reference: pre-shot xG of on-target shots faced minus goals conceded."""
    msg = _missing(gk, ["keeper", "on_target", "xg_on_target", "conceded", "prevented_proxy"])
    if msg:
        return _empty(msg, "Goalkeeping reference")
    fig = go.Figure(go.Bar(y=gk["keeper"], x=gk["prevented_proxy"], orientation="h",
                           marker_color=np.where(gk["prevented_proxy"] >= 0, TEAL, RED),
                           text=[f"n={n}" for n in gk["on_target"]], textposition="outside", cliponaxis=False,
                           customdata=np.stack([gk["xg_on_target"].round(2), gk["conceded"]], -1),
                           hovertemplate="%{y}<br>xG faced %{customdata[0]} · conceded %{customdata[1]}"
                                         "<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=INK, width=1))
    fig.update_layout(title=sub("Goalkeeping reference: on-target xG faced minus goals conceded",
                                f"{len(gk)} keepers with enough on-target shots · n = on-target shots faced · uses "
                                f"PRE-shot xG because the open data contain no post-shot model — a crude reference on "
                                f"small samples, not a goals-prevented measure"),
                      xaxis_title="pre-shot xG of on-target shots − goals conceded",
                      height=max(400, 24 * len(gk) + 140), margin=dict(l=170))
    return fig
