"""Match and season-level charts."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Any

from src.features.event_features import event_family
from src.features.match_state import assign_band
from src.visualization.theme import AMBER, COLORWAY, DIV_SCALE, EVENT_FAMILY_COLORS, GRID, INK, MUTED, NAVY, PAPER, RED, RESULT_COLORS, SHOT_COLORS, SLATE, TEAL, _empty, _missing, _mlabel, _rows, _team, add_banner


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


def event_type_treemap(events: pd.DataFrame, title: str = "Anatomy of the event stream") -> go.Figure:
    """Treemap of every parsed event by family and type: what the 'big data' actually is."""
    msg = _missing(events, ["type"])
    if msg:
        return _empty(msg, title)
    vc = events["type"].value_counts()
    fam = pd.Series([event_family(t) for t in vc.index], index=vc.index)
    ids, labels, parents, values, colors = [], [], [], [], []
    for f, idx in fam.groupby(fam).groups.items():
        ids.append(f); labels.append(f); parents.append(""); values.append(int(vc[idx].sum()))
        colors.append(EVENT_FAMILY_COLORS[f])
        for t in idx:
            ids.append(f"{f}/{t}"); labels.append(t); parents.append(f); values.append(int(vc[t]))
            colors.append(EVENT_FAMILY_COLORS[f])
    fig = go.Figure(go.Treemap(ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
                               marker=dict(colors=colors, line=dict(color="white", width=1)),
                               textinfo="label+value+percent root",
                               hovertemplate="<b>%{label}</b><br>%{value:,} events<br>%{percentRoot:.1%} of all"
                                             "<extra></extra>"))
    fig.update_layout(title=f"{title} — {len(events):,} events, {vc.size} event types (click to zoom)", height=560,
                      margin=dict(t=70, l=10, r=10, b=10))
    return fig


def events_per_match_chart(events: pd.DataFrame, matches: pd.DataFrame) -> go.Figure:
    """Stacked event volume per match by family."""
    msg = _missing(events, ["type", "match_id"])
    if msg:
        return _empty(msg, "Events per match")
    e = events.assign(family=[event_family(t) for t in events["type"]])
    ct = pd.crosstab(e["match_id"], e["family"])
    m = matches.set_index("match_id").loc[ct.index]
    lab = [f"{d:%d %b} {h[:10]}–{a[:10]}" for d, h, a in zip(m["match_date"], m["home_team"], m["away_team"])]
    fig = go.Figure()
    for f in EVENT_FAMILY_COLORS:
        if f in ct:
            fig.add_trace(go.Bar(x=lab, y=ct[f], name=f, marker_color=EVENT_FAMILY_COLORS[f],
                                 hovertemplate="%{x}<br>" + f + ": %{y:,}<extra></extra>"))
    fig.update_layout(barmode="stack", title=f"Event volume per match (mean {ct.sum(axis=1).mean():,.0f} events/match)",
                      xaxis=dict(tickangle=-60, tickfont=dict(size=8)), yaxis_title="events", height=440,
                      legend=dict(orientation="h", y=1.08), margin=dict(b=130))
    return fig


def shot_sunburst(flags: pd.DataFrame, team: str) -> go.Figure:
    """Shots by play pattern → body part → outcome."""
    s = flags[(flags["type"] == "Shot") & (flags["team_name"] == team)] if flags is not None and "type" in flags else None
    msg = _missing(s, ["play_pattern", "shot_body_part", "outcome"])
    if msg:
        return _empty(msg, f"Shot anatomy — {team}")
    s = s.fillna({"play_pattern": "Unknown", "shot_body_part": "Unknown", "outcome": "Unknown"})
    ids, labels, parents, values, colors = [], [], [], [], []
    for pp, g1 in s.groupby("play_pattern"):
        ids.append(pp); labels.append(pp); parents.append(""); values.append(len(g1)); colors.append(NAVY)
        for bp, g2 in g1.groupby("shot_body_part"):
            i2 = f"{pp}/{bp}"
            ids.append(i2); labels.append(bp); parents.append(pp); values.append(len(g2)); colors.append(TEAL)
            for oc, g3 in g2.groupby("outcome"):
                ids.append(f"{i2}/{oc}"); labels.append(oc); parents.append(i2); values.append(len(g3))
                colors.append(SHOT_COLORS.get(oc, SLATE))
    fig = go.Figure(go.Sunburst(ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
                                marker=dict(colors=colors, line=dict(color="white", width=1)),
                                hovertemplate="<b>%{label}</b><br>%{value} shots (%{percentParent:.0%} of parent)"
                                              "<extra></extra>"))
    fig.update_layout(title=f"{team}: shot anatomy — play pattern → body part → outcome ({len(s)} shots; outer ring "
                            f"amber = goal)", height=560, margin=dict(t=70, l=10, r=10, b=10))
    return fig


def kpi_gauges(team_stats: pd.DataFrame, team: str) -> go.Figure:
    """Five gauges: win rate, points per match, xG share, possession proxy, field tilt."""
    t = _team(team_stats, team)
    msg = _missing(t, ["result", "points", "xg", "xg_against", "possession_proxy_pct", "field_tilt_pct"])
    if msg:
        return _empty(msg, "Season gauges")
    vals = [("Win rate", 100 * (t["result"] == "W").mean(), 100, "%"), ("Points / match", t["points"].mean(), 3, ""),
            ("xG share", 100 * t["xg"].sum() / (t["xg"].sum() + t["xg_against"].sum()), 100, "%"),
            ("Possession proxy", t["possession_proxy_pct"].mean(), 100, "%"),
            ("Field tilt", t["field_tilt_pct"].mean(), 100, "%")]
    fig = make_subplots(rows=1, cols=5, specs=[[{"type": "indicator"}] * 5])
    for i, (name, v, mx, suf) in enumerate(vals, 1):
        fig.add_trace(go.Indicator(
            mode="gauge+number", value=float(v), number=dict(suffix=suf, valueformat=".2f" if mx == 3 else ".0f",
                                                              font=dict(size=26, color=NAVY)),
            title=dict(text=name, font=dict(size=13, color=MUTED)),
            gauge=dict(axis=dict(range=[0, mx], tickfont=dict(size=9)), bar=dict(color=TEAL, thickness=0.35),
                       bgcolor="white", borderwidth=0,
                       steps=[dict(range=[0, mx * 0.5], color="#f1efe8"), dict(range=[mx * 0.5, mx * 0.75],
                                                                               color="#e3ece8")],
                       threshold=dict(line=dict(color=AMBER, width=3), value=mx * 0.5))), row=1, col=i)
    fig.update_layout(title=f"{team}: season gauges (amber tick = 50% / 1.5 points)", height=270,
                      margin=dict(t=80, b=10))
    return fig


def attack_funnel(flags: pd.DataFrame, team_id: Any, team: str) -> go.Figure:
    """Approximate attacking funnel from completed passes to goals (stages are overlapping event counts)."""
    f = _rows(flags, "team_id", team_id)
    msg = _missing(f, ["passes_completed", "final_third_passes", "carries_into_final_third", "box_passes",
                       "carries_into_box", "shots", "shots_on_target", "goals"])
    if msg:
        return _empty(msg, "Attacking funnel")
    stages = [("Completed passes", f["passes_completed"].sum()),
              ("Final-third entries", f["final_third_passes"].sum() + f["carries_into_final_third"].sum()),
              ("Box entries", f["box_passes"].sum() + f["carries_into_box"].sum()),
              ("Shots", f["shots"].sum()), ("Shots on target", f["shots_on_target"].sum()), ("Goals", f["goals"].sum())]
    fig = go.Figure(go.Funnel(y=[s[0] for s in stages], x=[int(s[1]) for s in stages], textinfo="value+percent previous",
                              marker=dict(color=[NAVY, "#2b5f86", "#3f8f99", TEAL, AMBER, RED]),
                              connector=dict(line=dict(color=GRID))))
    fig.update_layout(title=f"{team}: attacking funnel — how possession turns into goals (season)", height=420,
                      margin=dict(l=160))
    return fig


def monthly_waterfall(team_stats: pd.DataFrame, team: str) -> go.Figure:
    """Goal difference built up month by month."""
    t = _team(team_stats, team)
    msg = _missing(t, ["match_date", "goal_diff"])
    if msg:
        return _empty(msg, "Goal-difference waterfall")
    m = t.groupby(t["match_date"].dt.to_period("M"))["goal_diff"].sum()
    x = [p.strftime("%b %Y") for p in m.index] + ["Season"]
    fig = go.Figure(go.Waterfall(x=x, y=list(m.values) + [0], measure=["relative"] * len(m) + ["total"],
                                 text=[f"{v:+d}" for v in m.values] + [f"{m.sum():+d}"], textposition="outside",
                                 increasing=dict(marker=dict(color=TEAL)), decreasing=dict(marker=dict(color=RED)),
                                 totals=dict(marker=dict(color=NAVY)), connector=dict(line=dict(color=GRID))))
    fig.update_layout(title=f"{team}: goal difference built month by month", yaxis_title="goal difference",
                      height=420, showlegend=False)
    return fig


def calendar_heatmap(team_stats: pd.DataFrame, team: str) -> go.Figure:
    """Fixture calendar (week × weekday) coloured by xG difference."""
    t = _team(team_stats, team)
    msg = _missing(t, ["match_date", "xg_diff", "result", "opponent"])
    if msg:
        return _empty(msg, "Fixture calendar")
    start = t["match_date"].min() - pd.Timedelta(days=t["match_date"].min().weekday())
    weeks = pd.date_range(start, t["match_date"].max(), freq="7D")
    z = np.full((7, len(weeks)), np.nan)
    txt = np.full((7, len(weeks)), "", dtype=object)
    hov = np.full((7, len(weeks)), "no match", dtype=object)
    for _, r in t.iterrows():
        w = (r["match_date"] - start).days // 7
        d = r["match_date"].weekday()
        z[d, w] = r["xg_diff"]
        txt[d, w] = r["result"]
        hov[d, w] = f"{r['match_date']:%a %d %b %Y} vs {r['opponent']} — {r['goals_for']}-{r['goals_against']}, " \
                    f"xG diff {r['xg_diff']:+.2f}"
    fig = go.Figure(go.Heatmap(z=z, x=[f"{w:%d %b}" for w in weeks], y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                               colorscale=DIV_SCALE, zmid=0, text=txt, texttemplate="%{text}", customdata=hov,
                               xgap=3, ygap=3, colorbar=dict(title="xG diff", thickness=12),
                               hovertemplate="%{customdata}<extra></extra>"))
    fig.update_layout(title=f"{team}: fixture calendar — every league match by week and weekday (colour = xG "
                            f"difference, letter = result)", height=330, xaxis=dict(tickangle=-60, tickfont=dict(size=8)),
                      yaxis=dict(autorange="reversed"), plot_bgcolor="white")
    return fig


def xg_dumbbell(team_stats: pd.DataFrame, team: str) -> go.Figure:
    """Dumbbell per match: xG for vs xG against."""
    t = _team(team_stats, team)
    msg = _missing(t, ["xg", "xg_against", "opponent", "home_away"])
    if msg:
        return _empty(msg, "xG dumbbell")
    lab = [_mlabel(r) for _, r in t.iterrows()]
    fig = go.Figure()
    for i, r in t.iterrows():
        fig.add_trace(go.Scatter(x=[r["xg_against"], r["xg"]], y=[lab[i]] * 2, mode="lines",
                                 line=dict(color=RESULT_COLORS[r["result"]], width=3), showlegend=False,
                                 hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=t["xg_against"], y=lab, mode="markers", name="xG against",
                             marker=dict(size=10, color=RED, line=dict(color="white", width=1))))
    fig.add_trace(go.Scatter(x=t["xg"], y=lab, mode="markers", name="xG for",
                             marker=dict(size=10, color=NAVY, line=dict(color="white", width=1)),
                             customdata=np.stack([t["goals_for"], t["goals_against"]], -1),
                             hovertemplate="%{y}: xG %{x:.2f} · score %{customdata[0]}-%{customdata[1]}<extra></extra>"))
    fig.update_layout(title=f"{team}: xG for vs against in every match (bar colour = result)", height=900,
                      yaxis=dict(autorange="reversed", tickfont=dict(size=9)), xaxis_title="xG",
                      legend=dict(orientation="h", y=1.03), margin=dict(l=170))
    return fig


def cumulative_area(team_stats: pd.DataFrame, team: str) -> go.Figure:
    """Cumulative goals and xG for/against as area charts."""
    t = _team(team_stats, team)
    msg = _missing(t, ["xg", "xg_against", "goals_for", "goals_against"])
    if msg:
        return _empty(msg, "Cumulative season")
    n = np.arange(1, len(t) + 1)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=n, y=t["xg"].cumsum(), name="xG for", fill="tozeroy", line=dict(color=NAVY),
                             fillcolor="rgba(29,53,87,0.25)"))
    fig.add_trace(go.Scatter(x=n, y=t["xg_against"].cumsum(), name="xG against", fill="tozeroy",
                             line=dict(color=RED), fillcolor="rgba(200,85,61,0.25)"))
    fig.add_trace(go.Scatter(x=n, y=t["goals_for"].cumsum(), name="Goals for", mode="lines",
                             line=dict(color=NAVY, dash="dot", width=2.5)))
    fig.add_trace(go.Scatter(x=n, y=t["goals_against"].cumsum(), name="Goals against", mode="lines",
                             line=dict(color=RED, dash="dot", width=2.5)))
    fig.update_layout(title=f"{team}: cumulative goals and xG — the gap between areas is the season's dominance",
                      xaxis_title="match number", yaxis_title="cumulative", height=420,
                      legend=dict(orientation="h", y=-0.2))
    return fig


def rolling_band(team_stats: pd.DataFrame, team: str, window: int = 5) -> go.Figure:
    """Rolling xG difference with a ±1 SD band."""
    t = _team(team_stats, team)
    msg = _missing(t, ["xg_diff"])
    if msg:
        return _empty(msg, "Rolling xG difference")
    n = np.arange(1, len(t) + 1)
    mu = t["xg_diff"].rolling(window, min_periods=2).mean()
    sd = t["xg_diff"].rolling(window, min_periods=2).std()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=np.r_[n, n[::-1]], y=np.r_[mu + sd, (mu - sd)[::-1]], fill="toself",
                             fillcolor="rgba(42,157,143,0.18)", line=dict(width=0), name="±1 SD", hoverinfo="skip"))
    fig.add_trace(go.Bar(x=n, y=t["xg_diff"], name="match xG difference", marker_color=t["result"].map(RESULT_COLORS),
                         opacity=0.45))
    fig.add_trace(go.Scatter(x=n, y=mu, name=f"{window}-match rolling mean", line=dict(color=TEAL, width=3)))
    fig.add_hline(y=0, line=dict(color=INK, width=1))
    fig.update_layout(title=f"{team}: performance trend — rolling xG difference with variability band",
                      xaxis_title="match number", yaxis_title="xG for − against", height=400,
                      legend=dict(orientation="h", y=-0.2))
    return fig


def goal_clock(goals: pd.DataFrame, team_stats: pd.DataFrame, team: str, bin_min: int = 5) -> go.Figure:
    """Polar 'clock' of goals scored and conceded by match minute."""
    t = _team(team_stats, team)
    msg = _missing(t, ["match_id", "team_id"]) or _missing(goals, ["minute", "scoring_team_id", "match_id"])
    if msg:
        return _empty(msg, "Goal clock")
    tid = t["team_id"].iloc[0]
    g = goals[goals["match_id"].isin(t["match_id"])]
    edges = np.arange(0, 100, bin_min)
    fig = go.Figure()
    for name, sub, c in (("Scored", g[g["scoring_team_id"] == tid], NAVY), ("Conceded", g[g["scoring_team_id"] != tid], RED)):
        cnt = pd.cut(sub["minute"].clip(upper=99), np.r_[edges, 100], right=False).value_counts(sort=False)
        fig.add_trace(go.Barpolar(r=cnt.values, theta=(edges + bin_min / 2) * 360 / 100, width=[bin_min * 3.6 * 0.9] * len(edges),
                                  name=f"{name} ({len(sub)})", marker_color=c, opacity=0.8,
                                  customdata=[f"{a}-{a + bin_min - 1}'" for a in edges],
                                  hovertemplate="%{customdata}: %{r} goals<extra>" + name + "</extra>"))
    fig.update_layout(title=f"{team}: goal clock — when goals are scored and conceded ({bin_min}-minute slices)",
                      polar=dict(angularaxis=dict(rotation=90, direction="clockwise", tickvals=[0, 54, 108, 162, 216, 270, 324],
                                                  ticktext=["0'", "15'", "30'", "45'", "60'", "75'", "90'"], gridcolor=GRID),
                                 radialaxis=dict(gridcolor=GRID), bgcolor=PAPER),
                      height=500, legend=dict(orientation="h", y=-0.08))
    return fig


def venue_boxes(team_stats: pd.DataFrame, team: str) -> go.Figure:
    """Box plots of xG for/against and possession by venue."""
    t = _team(team_stats, team)
    msg = _missing(t, ["home_away", "xg", "xg_against", "possession_proxy_pct"])
    if msg:
        return _empty(msg, "Home vs away")
    fig = make_subplots(rows=1, cols=3, subplot_titles=("xG for", "xG against", "Possession proxy %"))
    for i, col in enumerate(["xg", "xg_against", "possession_proxy_pct"], 1):
        for venue, c in (("home", NAVY), ("away", AMBER)):
            d = t[t["home_away"] == venue]
            fig.add_trace(go.Box(y=d[col], name=venue, marker_color=c, boxpoints="all", jitter=0.4, pointpos=0,
                                 showlegend=(i == 1), legendgroup=venue, text=d["opponent"],
                                 hovertemplate="%{text}: %{y:.2f}<extra></extra>"), row=1, col=i)
    fig.update_layout(title=f"{team}: home vs away (each dot is a match)", height=400)
    return fig


def opponent_matrix(team_stats: pd.DataFrame, team: str) -> go.Figure:
    """Opponent × metric matrix (average over meetings; colour standardised per column)."""
    t = _team(team_stats, team)
    msg = _missing(t, ["opponent", "goals_for", "goals_against", "xg", "xg_against"])
    if msg:
        return _empty(msg, "Opponent matrix")
    cols = {"points": "Points", "goals_for": "Goals for", "goals_against": "Goals against", "xg": "xG for",
            "xg_against": "xG against", "possession_proxy_pct": "Possession %", "field_tilt_pct": "Field tilt %",
            "ppda": "PPDA"}
    m = t.groupby("opponent")[list(cols)].mean()
    m = m.loc[m["points"].sort_values().index]
    sign = pd.Series({c: (-1 if c in ("goals_against", "xg_against", "ppda") else 1) for c in cols})
    z = ((m - m.mean()) / m.std(ddof=0).replace(0, 1)) * sign
    fig = go.Figure(go.Heatmap(z=z.values, x=list(cols.values()), y=list(m.index), zmid=0, colorscale=DIV_SCALE,
                               text=m.round(2).values, texttemplate="%{text}", xgap=2, ygap=2, showscale=False,
                               hovertemplate="%{y} · %{x}: %{text}<extra></extra>"))
    fig.update_layout(title=f"{team} vs each opponent (average over meetings; blue = favourable for {team})",
                      height=140 + 28 * len(m), margin=dict(l=190), plot_bgcolor="white", xaxis=dict(side="top"))
    return fig


def opponent_bubbles(team_stats: pd.DataFrame, team: str) -> go.Figure:
    """Bubble chart per opponent: chances created vs conceded, size = goals scored, colour = points."""
    t = _team(team_stats, team)
    msg = _missing(t, ["opponent", "xg", "xg_against", "goals_for", "points"])
    if msg:
        return _empty(msg, "Opponent bubbles")
    m = t.groupby("opponent").agg(xg=("xg", "mean"), xga=("xg_against", "mean"), gf=("goals_for", "sum"),
                                  ppm=("points", "mean"), n=("match_id", "size")).reset_index()
    fig = go.Figure(go.Scatter(x=m["xga"], y=m["xg"], mode="markers+text", text=m["opponent"].str.slice(0, 12),
                               textposition="top center", textfont=dict(size=9),
                               marker=dict(size=12 + 5 * m["gf"], color=m["ppm"], colorscale=[[0, RED], [0.5, AMBER],
                                                                                              [1, TEAL]],
                                           cmin=0, cmax=3, colorbar=dict(title="points/<br>match", thickness=12),
                                           line=dict(color="white", width=1), opacity=0.85),
                               customdata=np.stack([m["gf"], m["n"]], -1),
                               hovertemplate="%{text}<br>xG for %{y:.2f} / against %{x:.2f}<br>%{customdata[0]} goals in "
                                             "%{customdata[1]} meetings<extra></extra>"))
    fig.update_layout(title=f"{team}: opponents by chances created and conceded (bubble = goals scored)",
                      xaxis_title="xG conceded per meeting", yaxis_title="xG created per meeting", height=520)
    return fig


def on_pitch_gantt(spells: pd.DataFrame, goals: pd.DataFrame, match_id: Any, team_id: Any, title: str) -> go.Figure:
    """Gantt chart of every player's time on the pitch in one match, with goals marked."""
    s = spells[(spells["match_id"] == match_id) & (spells["team_id"] == team_id)] if spells is not None else None
    msg = _missing(s, ["start", "end", "player_name", "start_reason"])
    if msg:
        return _empty(msg, title)
    s = s.sort_values(["start", "player_name"]).iloc[::-1]
    color = np.where(s["start_reason"] == "starting_xi", NAVY, TEAL)
    fig = go.Figure(go.Bar(y=s["player_name"], x=s["end"] - s["start"], base=s["start"], orientation="h",
                           marker_color=color, customdata=np.stack([s["start"], s["end"], s["end_reason"]], -1),
                           hovertemplate="%{y}: %{customdata[0]:.0f}' → %{customdata[1]:.0f}' (%{customdata[2]})"
                                         "<extra></extra>", showlegend=False))
    for _, g in goals[goals["match_id"] == match_id].iterrows():
        mine = g["scoring_team_id"] == team_id
        fig.add_vline(x=g["elapsed_min"], line=dict(color=TEAL if mine else RED, dash="dot", width=1.5))
        fig.add_annotation(x=g["elapsed_min"], y=1.02, yref="paper", text="⚽" if mine else "✕", showarrow=False,
                           font=dict(color=TEAL if mine else RED))
    fig.update_layout(title=f"{title}<br><sup>navy = starter, teal = substitute · dotted lines = goals for (teal) / "
                            f"against (red)</sup>", xaxis_title="elapsed playing time (min)",
                      height=40 + 26 * len(s) + 120, margin=dict(l=190), bargap=0.25)
    return fig


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
