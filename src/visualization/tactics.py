"""Formation, lineup and tactical charts."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.config import ROLE_LABEL
from src.visualization.pitch import attack_arrow, draw_pitch
from src.visualization.theme import AMBER, COLORWAY, GRID, INK, MUTED, NAVY, PAPER, RED, SEQ_SCALE, SLATE, TEAL, _empty, _match_label, _missing, _rows, add_banner


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


def rotation_matrix(appearances: pd.DataFrame, matches: pd.DataFrame, team: str,
                    banner: str | None = None) -> go.Figure:
    """Player × match minutes matrix: the whole season's selection story in one view."""
    a = _rows(appearances, "team_name", team)
    msg = _missing(a, ["match_id", "player_id", "player_name", "minutes_played", "squad_status"])
    if msg:
        return _empty(msg, f"Squad rotation — {team}")
    a = a.merge(matches[["match_id", "match_date", "home_team", "away_team"]], on="match_id")
    order = a[["match_id", "match_date", "home_team", "away_team"]].drop_duplicates().sort_values("match_date")
    labels = [_match_label(r, team) for _, r in order.iterrows()]
    mins = a.pivot_table(index="player_name", columns="match_id", values="minutes_played", aggfunc="sum")
    stat = a.pivot_table(index="player_name", columns="match_id", values="squad_status", aggfunc="first")
    mins = mins.reindex(columns=order["match_id"])
    stat = stat.reindex(index=mins.index, columns=order["match_id"])
    keep = mins.sum(axis=1).sort_values(ascending=False).index
    mins, stat = mins.loc[keep], stat.loc[keep]
    sym = stat.replace({"starter": "●", "used_substitute": "▲", "unused_substitute": "·"}).fillna("")
    hover = np.where(stat.isna(), "not in matchday squad", stat.fillna("").replace(
        {"starter": "started", "used_substitute": "came on", "unused_substitute": "unused substitute"}))
    fig = go.Figure(go.Heatmap(
        z=mins.values, x=labels, y=list(mins.index), colorscale=[[0, "#f1efe8"], [0.01, "#d7e8e1"], [0.5, "#5aa697"],
                                                                 [1, NAVY]],
        zmin=0, zmax=float(np.nanmax(mins.values)) if np.isfinite(np.nanmax(mins.values)) else 100,
        text=sym.values, texttemplate="%{text}", textfont=dict(size=9, color="white"),
        customdata=hover, xgap=1, ygap=1, colorbar=dict(title="minutes", thickness=12),
        hovertemplate="%{y}<br>%{x}<br>%{customdata} · %{z:.0f} min<extra></extra>"))
    fig.update_layout(title=f"{team}: who played when — minutes per match (● started, ▲ came on, · unused, blank = "
                            f"not in squad)", height=max(420, 20 * len(mins) + 180),
                      xaxis=dict(tickangle=-60, tickfont=dict(size=9), showgrid=False),
                      yaxis=dict(autorange="reversed", tickfont=dict(size=10), showgrid=False),
                      margin=dict(l=180, b=140), plot_bgcolor="white")
    return add_banner(fig, banner)


def lineup_similarity(appearances: pd.DataFrame, matches: pd.DataFrame, team: str,
                      banner: str | None = None) -> go.Figure:
    """Jaccard similarity of starting XIs between every pair of matches (rotation blocks)."""
    a = _rows(appearances, "team_name", team)
    msg = _missing(a, ["match_id", "player_id", "is_starter"])
    if msg:
        return _empty(msg, f"Lineup similarity — {team}")
    st = a[a["is_starter"]].merge(matches[["match_id", "match_date", "home_team", "away_team"]], on="match_id")
    order = st[["match_id", "match_date", "home_team", "away_team"]].drop_duplicates().sort_values("match_date")
    sets = [set(st.loc[st["match_id"] == m, "player_id"]) for m in order["match_id"]]
    n = len(sets)
    if n < 2:
        return _empty("Need at least two matches.", f"Lineup similarity — {team}")
    jac = np.array([[len(sets[i] & sets[j]) / len(sets[i] | sets[j]) for j in range(n)] for i in range(n)])
    shared = np.array([[len(sets[i] & sets[j]) for j in range(n)] for i in range(n)])
    labels = [_match_label(r, team) for _, r in order.iterrows()]
    fig = go.Figure(go.Heatmap(z=jac, x=labels, y=labels, zmin=0, zmax=1, colorscale=SEQ_SCALE, customdata=shared,
                               colorbar=dict(title="Jaccard", thickness=12),
                               hovertemplate="%{y}<br>vs %{x}<br>%{customdata} of 11 starters shared<extra></extra>"))
    fig.update_layout(title=f"{team}: starting-XI similarity between matches (dark blocks = stable XI periods)",
                      height=720, xaxis=dict(tickangle=-60, tickfont=dict(size=8)),
                      yaxis=dict(autorange="reversed", tickfont=dict(size=8)), margin=dict(l=140, b=140))
    return add_banner(fig, banner)


def team_style_radar(team_stats: pd.DataFrame, team: str, banner: str | None = None) -> go.Figure:
    """Team-average style indicators as percentiles among all teams in the dataset."""
    msg = _missing(_rows(team_stats, "team_name", team), ["possession_proxy_pct", "field_tilt_pct", "xg"])
    if msg:
        return _empty(msg, f"Team style — {team}")
    metrics = {"possession_proxy_pct": ("Possession proxy", 1), "field_tilt_pct": ("Field tilt", 1),
               "xg": ("xG for", 1), "shots": ("Shots", 1), "pass_completion_pct": ("Pass completion", 1),
               "progressive_passes": ("Progressive passes", 1), "pressures": ("Pressures", 1),
               "ppda": ("Pressing intensity (low PPDA)", -1), "xg_against": ("Low xG against", -1),
               "set_piece_shots": ("Set-piece shots", 1)}
    avg = team_stats.groupby("team_name")[list(metrics)].mean()
    pct = pd.DataFrame({m: (sign * avg[m]).rank(pct=True) * 100 for m, (_, sign) in metrics.items()})
    theta = [v[0] for v in metrics.values()]
    r = pct.loc[team].tolist()
    raw = avg.loc[team].tolist()
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[50] * (len(r) + 1), theta=theta + theta[:1], name="median team",
                                  line=dict(color=MUTED, dash="dot"), hoverinfo="skip"))
    fig.add_trace(go.Scatterpolar(r=r + r[:1], theta=theta + theta[:1], fill="toself", name=team,
                                  line=dict(color=TEAL, width=2.5), fillcolor="rgba(42,157,143,0.25)",
                                  customdata=raw + raw[:1],
                                  hovertemplate="%{theta}: %{r:.0f}th pct (avg %{customdata:.2f})<extra></extra>"))
    fig.update_layout(title=f"{team}: style fingerprint vs the {len(avg)} teams in this dataset<br><sup>percentile "
                            f"of per-match averages; opponents are measured only in matches against the focus team"
                            f"</sup>", polar=dict(radialaxis=dict(range=[0, 100], gridcolor=GRID),
                                                  angularaxis=dict(gridcolor=GRID), bgcolor=PAPER),
                      height=520, legend=dict(orientation="h", y=-0.1))
    return add_banner(fig, banner)
