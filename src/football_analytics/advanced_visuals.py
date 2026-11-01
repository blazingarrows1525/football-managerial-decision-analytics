"""Additional presentation-grade charts: pitch heatmaps, squad matrices, momentum, phase profiles,
sunburst, pass-direction rose, style radar.

Same contract as :mod:`visualizations`: required columns are checked and an empty-state
figure is returned instead of an exception; nothing is imputed.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import ROLE_LABEL
from .features import assign_band
from .player_analysis import label
from .visualizations import (AMBER, DIV_SCALE, FAMILY_COLORS, GRID, INK, MUTED, NAVY, PAPER, RED,
                             RESULT_COLORS, SEQ_SCALE, SLATE, TEAL, _empty, _missing, _rows, add_banner,
                             attack_arrow, draw_pitch, source_note)

HEAT_SCALE = [[0.0, "rgba(238,242,236,0)"], [0.15, "#d7e8e1"], [0.4, "#8cc5b8"], [0.65, "#3f8f99"],
              [0.85, "#2b5f86"], [1.0, NAVY]]
ROLE_ORDER = ["GK", "CB", "FB", "WB", "DM", "CM", "AM", "WM", "W", "CF"]


def _match_label(row: pd.Series, team: str) -> str:
    opp = row["away_team"] if row["home_team"] == team else row["home_team"]
    ha = "H" if row["home_team"] == team else "A"
    return f"{row['match_date']:%d %b} {opp[:14]} ({ha})"


# ---------------------------------------------------------------------------
# Pitch heatmap
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Squad matrices
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Match / team flow
# ---------------------------------------------------------------------------
def match_momentum(flags: pd.DataFrame, goals: pd.DataFrame, match_id: Any, bucket: float = 5.0,
                   title: str = "Match momentum", banner: str | None = None) -> go.Figure:
    """xG per time bucket, team above / opponent below the axis, with final-third share line."""
    ev = _rows(flags, "match_id", match_id)
    msg = _missing(ev, ["elapsed_min", "team_name", "xg", "final_third_touches"])
    if msg:
        return _empty(msg, title)
    teams = list(dict.fromkeys(ev.dropna(subset=["team_name"])["team_name"]))[:2]
    if len(teams) < 2:
        return _empty("Both teams are needed.", title)
    ev = ev.assign(b=(ev["elapsed_min"] // bucket) * bucket)
    agg = ev.groupby(["b", "team_name"])[["xg", "final_third_touches", "shots"]].sum().unstack(fill_value=0)
    bx = agg.index.to_numpy() + bucket / 2
    a_xg, b_xg = agg["xg"].get(teams[0], 0), agg["xg"].get(teams[1], 0)
    ft = agg["final_third_touches"]
    share = ft.get(teams[0], 0) / (ft.get(teams[0], 0) + ft.get(teams[1], 0)).replace(0, np.nan) * 100
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=bx, y=a_xg, name=f"{teams[0]} xG", marker_color=NAVY, width=bucket * 0.85,
                         hovertemplate="%{x:.0f}': %{y:.2f} xG<extra>" + teams[0] + "</extra>"))
    fig.add_trace(go.Bar(x=bx, y=-b_xg, name=f"{teams[1]} xG", marker_color=RED, width=bucket * 0.85,
                         customdata=b_xg, hovertemplate="%{x:.0f}': %{customdata:.2f} xG<extra>" + teams[1]
                                                         + "</extra>"))
    fig.add_trace(go.Scatter(x=bx, y=share, name=f"{teams[0]} share of final-third actions", mode="lines",
                             line=dict(color=AMBER, width=2, shape="spline"), opacity=0.9), secondary_y=True)
    top = max(float(np.max(a_xg)) if np.size(a_xg) else 0, float(np.max(b_xg)) if np.size(b_xg) else 0, 0.3)
    g = goals[goals["match_id"] == match_id] if goals is not None else pd.DataFrame()
    team_ids = ev.dropna(subset=["team_id"]).drop_duplicates("team_name").set_index("team_name")["team_id"]
    for _, r in g.iterrows():
        up = r["scoring_team_id"] == team_ids.get(teams[0])
        fig.add_trace(go.Scatter(x=[r["elapsed_min"]], y=[top * 1.15 if up else -top * 1.15], mode="markers+text",
                                 text=[str(r["player_name"]).split()[-1]], textposition="top center" if up else
                                 "bottom center", marker=dict(symbol="star", size=15, color=AMBER,
                                                              line=dict(color=INK, width=1)),
                                 showlegend=False, hovertemplate=f"Goal: {r['player_name']}<extra></extra>"))
    fig.add_vline(x=float(ev.loc[ev["period"] == 2, "elapsed_min"].min() or 45), line=dict(color=MUTED, dash="dot"))
    fig.update_yaxes(title_text="xG per bucket (opponent below)", range=[-top * 1.4, top * 1.4], secondary_y=False)
    fig.update_yaxes(title_text="final-third share %", range=[0, 100], secondary_y=True, showgrid=False)
    fig.update_layout(title=f"{title}<br><sup>{bucket:.0f}-minute buckets of elapsed playing time · dotted line = "
                            f"second half</sup>", barmode="relative", height=420, legend=dict(orientation="h", y=-0.2),
                      xaxis_title="Elapsed playing time (min)")
    return add_banner(fig, banner)


def phase_profile(flags: pd.DataFrame, goals: pd.DataFrame, team_stats: pd.DataFrame, team: str,
                  phases: list[dict], banner: str | None = None) -> go.Figure:
    """Goals and xG for/against by match phase over the season (diverging heatmap)."""
    ts = _rows(team_stats, "team_name", team)
    msg = _missing(ts, ["match_id", "team_id"]) or _missing(flags, ["period", "minute", "xg", "team_id"])
    if msg:
        return _empty(msg, f"Phase profile — {team}")
    tid = ts["team_id"].iloc[0]
    ev = flags[flags["match_id"].isin(ts["match_id"]) & flags["xg"].gt(0)].copy()
    ev["phase"] = [assign_band(p, m, phases) for p, m in zip(ev["period"], ev["minute"])]
    g = goals[goals["match_id"].isin(ts["match_id"])].copy()
    g["phase"] = [assign_band(p, m, phases) for p, m in zip(g["period"], g["minute"])]
    order = [p["label"] for p in phases]
    rows = {"Goals for": g[g["scoring_team_id"] == tid].groupby("phase").size(),
            "xG for": ev[ev["team_id"] == tid].groupby("phase")["xg"].sum(),
            "xG against": ev[ev["team_id"] != tid].groupby("phase")["xg"].sum(),
            "Goals against": g[g["scoring_team_id"] != tid].groupby("phase").size()}
    vals = pd.DataFrame({k: v.reindex(order, fill_value=0) for k, v in rows.items()}).T
    vals = vals.loc[:, vals.sum(axis=0) > 0]  # e.g. drop extra time when no match went to extra time
    order = list(vals.columns)
    signed = vals.copy()
    signed.loc[["xG against", "Goals against"]] *= -1
    scale = signed.abs().max(axis=1).replace(0, 1)
    fig = go.Figure(go.Heatmap(z=(signed.T / scale).T.values, x=order, y=list(vals.index), zmin=-1, zmax=1,
                               colorscale=DIV_SCALE, text=vals.round(1).values, texttemplate="%{text}",
                               textfont=dict(size=13), showscale=False, xgap=2, ygap=2,
                               hovertemplate="%{y}, %{x}: %{text}<extra></extra>"))
    fig.update_layout(title=f"{team}: when goals and chances happen (season totals by match phase; blue = for, "
                            f"red = against, intensity scaled per row)", height=330, plot_bgcolor="white",
                      margin=dict(l=120),
                      xaxis_title="Match phase (clock minutes, stoppage counted)")
    return add_banner(fig, banner)


def dominance_scatter(team_stats: pd.DataFrame, team: str, banner: str | None = None) -> go.Figure:
    """Each match as xG for vs xG against, coloured by result: how dominant were performances?"""
    t = _rows(team_stats, "team_name", team)
    msg = _missing(t, ["xg", "xg_against", "result", "opponent", "goals_for", "goals_against"])
    if msg:
        return _empty(msg, f"Match dominance — {team}")
    mx = float(max(t["xg"].max(), t["xg_against"].max(), 1)) * 1.1
    fig = go.Figure()
    fig.add_shape(type="path", path=f"M 0 0 L {mx} 0 L {mx} {mx} Z", fillcolor="rgba(42,157,143,0.07)",
                  line=dict(width=0), layer="below")
    fig.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines", line=dict(color=MUTED, dash="dot"),
                             name="equal xG", hoverinfo="skip"))
    for res, g in t.groupby("result"):
        fig.add_trace(go.Scatter(
            x=g["xg"], y=g["xg_against"], mode="markers", name={"W": "Win", "D": "Draw", "L": "Loss"}[res],
            marker=dict(size=10 + 4 * g["goal_diff"].abs(), color=RESULT_COLORS[res], opacity=0.85,
                        line=dict(color="white", width=1)),
            customdata=np.stack([g["opponent"], g["goals_for"], g["goals_against"], g["match_date"].dt.strftime(
                "%d %b %Y")], axis=-1),
            hovertemplate="%{customdata[3]} vs %{customdata[0]}<br>%{customdata[1]}-%{customdata[2]}<br>"
                          "xG %{x:.2f} – %{y:.2f}<extra></extra>"))
    fig.add_annotation(x=mx * 0.85, y=mx * 0.1, text="out-created opponent", showarrow=False,
                       font=dict(color=TEAL, size=12))
    fig.add_annotation(x=mx * 0.15, y=mx * 0.9, text="out-created by opponent", showarrow=False,
                       font=dict(color=RED, size=12))
    share = (t["xg"] > t["xg_against"]).mean()
    fig.update_layout(title=f"{team}: match dominance — xG created vs conceded ({share:.0%} of matches above the "
                            f"line; size = goal margin)", xaxis=dict(title="xG for", range=[0, mx]),
                      yaxis=dict(title="xG against", range=[0, mx]), height=520)
    return add_banner(fig, banner)


def xg_distribution(flags: pd.DataFrame, team: str, match_ids: list, banner: str | None = None) -> go.Figure:
    """Shot-quality distribution for and against, with conversion annotations."""
    ok = flags is not None and {"type", "match_id"} <= set(flags.columns)
    sh = flags[(flags["type"] == "Shot") & flags["match_id"].isin(match_ids)] if ok else None
    msg = _missing(sh, ["shot_xg", "team_name", "outcome"])
    if msg:
        return _empty(msg, f"Shot quality — {team}")
    fig = go.Figure()
    notes = []
    for name, d, c in ((team, sh[sh["team_name"] == team], NAVY), ("Opponents", sh[sh["team_name"] != team], RED)):
        fig.add_trace(go.Histogram(x=d["shot_xg"], xbins=dict(start=0, end=1, size=0.04), name=f"{name} ({len(d)} "
                                   f"shots)", marker_color=c, opacity=0.65))
        g = int((d["outcome"] == "Goal").sum())
        notes.append(f"{name}: {g} goals from {d['shot_xg'].sum():.1f} xG, mean {d['shot_xg'].mean():.3f} xG/shot")
    fig.update_layout(barmode="overlay", title=f"Shot quality distribution<br><sup>{' · '.join(notes)}</sup>",
                      xaxis_title="StatsBomb xG per shot", yaxis_title="shots", height=400,
                      legend=dict(orientation="h", y=-0.2))
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


__all__ = ["action_heatmap", "heatmap_layer", "rotation_matrix", "lineup_similarity", "squad_percentile_heatmap",
           "minutes_sunburst", "match_momentum", "phase_profile", "dominance_scatter", "xg_distribution",
           "team_style_radar", "pass_direction_rose", "subs_team_band_heatmap"]
