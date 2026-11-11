"""Substitution and managerial-pattern charts added in V3 (catalogue families H and I).

Substitution patterns are descriptive. Timing and score state are entangled with team strength (a dominant
team leads most matches), injuries are recorded only when the source tags a substitution as such, and nothing
here identifies the effect of a change.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.analytics.uncertainty import shrunk_proportion, wilson_interval
from src.visualization.theme import (AMBER, COLORWAY, FAMILY_COLORS, GRID, MUTED, NAVY, RED, SLATE, STATE_COLORS, TEAL, _empty, _missing, heat, low_sample, sub, table_figure)

STATE_ORDER = ["leading", "drawing", "trailing"]


def _subs(subs: pd.DataFrame | None, team: str | None) -> pd.DataFrame | None:
    if subs is None or "team_name" not in subs.columns:
        return None
    return subs if team is None else subs[subs["team_name"] == team]


def timing_by_group(subs: pd.DataFrame | None, team: str | None, by: str = "game_state") -> go.Figure:
    """Substitution minute distribution split by score state or by the role of the player leaving."""
    s = _subs(subs, team)
    title = f"Substitution timing by {by.replace('_', ' ')}"
    msg = _missing(s, ["minute", by])
    if msg:
        return _empty(msg, title)
    s = s.dropna(subset=[by, "minute"])
    keys = [k for k in STATE_ORDER if k in set(s[by])] if by == "game_state" else \
        s[by].value_counts()[lambda v: v >= 5].index.tolist()
    if not keys:
        return _empty("No group has at least 5 substitutions.", title)
    fig = go.Figure()
    for i, k in enumerate(keys):
        g = s[s[by] == k]
        fig.add_trace(go.Box(x=g["minute"], name=f"{k} (n={len(g)}, median {g['minute'].median():.0f}')",
                             boxpoints="all", jitter=0.5, pointpos=0, marker=dict(size=4, opacity=0.55),
                             line=dict(color=STATE_COLORS.get(k, COLORWAY[i % len(COLORWAY)])), orientation="h"))
    dropped = sorted(set(s[by]) - set(keys))
    fig.update_layout(title=sub(f"{team or 'All teams'}: {title.lower()}",
                                f"n = {int(s[by].isin(keys).sum())} substitutions · minute on the match clock (45+ and "
                                f"90+ keep counting)" + (f" · groups below 5 not shown: {', '.join(map(str, dropped))}"
                                                         if dropped else "")
                                + " · score state reflects team strength as much as intent"),
                      xaxis_title="match minute", height=max(360, 62 * len(keys) + 150), showlegend=False,
                      margin=dict(l=250))
    return fig


def role_matching_matrix(subs: pd.DataFrame | None, team: str | None) -> go.Figure:
    """Role of the player leaving (rows) against the role of the player entering (columns)."""
    s = _subs(subs, team)
    msg = _missing(s, ["off_role", "on_role"])
    if msg:
        return _empty(msg, "Substitution role matching")
    d = s.dropna(subset=["off_role", "on_role"])
    if d.empty:
        return _empty("No substitution has both roles recorded.", "Substitution role matching")
    tab = pd.crosstab(d["off_role"], d["on_role"])
    like = float(np.mean(d["off_role"] == d["on_role"]))
    fig = heat(tab.to_numpy(float), list(tab.columns), list(tab.index), "", fmt=".0f", colorbar="subs",
               hover="%{y} off → %{x} on: %{z:.0f}<extra></extra>")
    fig.update_layout(title=sub(f"{team or 'All teams'}: who replaces whom, by role",
                                f"n = {len(d)} substitutions with both roles known ({len(s) - len(d)} without) · "
                                f"{like:.0%} like-for-like · off role = position when leaving, on role = position "
                                f"taken up"),
                      xaxis_title="role of player coming on", yaxis=dict(title="role of player going off",
                                                                         autorange="reversed"), height=460)
    return fig


def bench_usage_chart(usage: pd.DataFrame | None, team: str) -> go.Figure:
    """Times named on the bench, split into used and unused, per player."""
    msg = _missing(usage, ["player_name", "bench_named", "used", "unused"])
    if msg:
        return _empty(msg, "Bench usage")
    d = usage.head(22).iloc[::-1]
    fig = go.Figure()
    fig.add_bar(y=d["player_name"], x=d["used"], orientation="h", name="came on", marker_color=TEAL)
    fig.add_bar(y=d["player_name"], x=d["unused"], orientation="h", name="unused substitute", marker_color="#d5dbe3")
    fig.update_layout(barmode="stack", title=sub(f"{team}: bench usage",
                                                 f"{len(usage)} players named on a bench at least once · overall "
                                                 f"{usage['used'].sum() / max(usage['bench_named'].sum(), 1):.0%} of "
                                                 f"bench places were used · the reason a player stayed on the bench "
                                                 f"(fitness, tactics, score) is not in the data"),
                      xaxis_title="matches named on the bench", height=max(420, 24 * len(d) + 130),
                      margin=dict(l=190), legend=dict(orientation="h", y=1.06))
    return fig


def bench_availability_timeline(appearances: pd.DataFrame | None, spells: pd.DataFrame | None, subs: pd.DataFrame | None,
                                match_id: Any, team_id: Any, season_pct: pd.DataFrame | None, title: str) -> go.Figure:
    """Remaining bench by role family after each substitution of one team in one match."""
    msg = _missing(appearances, ["match_id", "team_id", "is_starter", "player_id"]) or _missing(
        subs, ["match_id", "team_id", "elapsed_min", "player_on_id", "minute"])
    if msg:
        return _empty(msg, title)
    bench = appearances[(appearances["match_id"] == match_id) & (appearances["team_id"] == team_id)
                        & (~appearances["is_starter"].astype(bool))]
    if bench.empty:
        return _empty("No bench is recorded for this team in this match.", title)
    fam = season_pct.drop_duplicates("player_id").set_index("player_id")["role_family"] \
        if season_pct is not None else pd.Series(dtype=object)
    bench = bench.assign(family=bench["player_id"].map(fam).fillna("No minutes this season"))
    s = subs[(subs["match_id"] == match_id) & (subs["team_id"] == team_id)].sort_values("elapsed_min")
    steps = [("kick-off", set())]
    used: set = set()
    for r in s.itertuples():
        used = used | {r.player_on_id}
        steps.append((f"{int(r.minute)}' {str(r.player_on_name).split()[-1]} on", set(used)))
    fams = [f for f in ("Goalkeeper", "Defender", "Midfielder", "Forward", "No minutes this season")
            if f in set(bench["family"])]
    fig = go.Figure()
    for f in fams:
        ids = set(bench.loc[bench["family"] == f, "player_id"])
        fig.add_bar(x=[lab for lab, _ in steps], y=[len(ids - u) for _, u in steps], name=f,
                    marker_color=FAMILY_COLORS.get(f, "#d9d4c7"))
    fig.update_layout(barmode="stack", title=sub(title, f"bench of {len(bench)} · {len(s)} substitutions made · family "
                                                        f"= the bench player's primary role this season · availability "
                                                        f"here means 'named and not yet used'; fitness is unknown"),
                      yaxis_title="unused substitutes remaining", height=420, legend=dict(orientation="h", y=-0.25))
    return fig


def candidate_table(ranking: pd.DataFrame | None, title: str) -> go.Figure:
    """Substitute shortlist with scores, evidence and risks as a table."""
    if ranking is None or len(ranking) == 0:
        return _empty("No eligible bench candidate at this moment.", title)
    keep = [c for c in ("player_name", "role", "primary_role", "candidate_score", "role_compatibility", "intent_fit",
                        "recent_form", "sample_reliability", "evidence", "risks") if c in ranking.columns]
    return table_figure(ranking[keep], title, max_rows=10)


def scenario_comparison(rec: dict | None, actual_on: str | None = None) -> go.Figure:
    """Counterfactual simulation: heuristic shortlist at a chosen minute, with the actual change marked if any."""
    title = "Substitution scenario (counterfactual simulation)"
    if not rec or rec.get("status") != "ok":
        return _empty((rec or {}).get("status", "No scenario available.") if rec else "No scenario available.", title)
    alts = rec.get("alternatives")
    rows = [{"player_name": rec["recommended_on"]["player_name"],
             "candidate_score": rec["recommended_on"].get("candidate_score", np.nan), "kind": "top of shortlist"}]
    if isinstance(alts, pd.DataFrame) and len(alts):
        for r in alts.itertuples():
            rows.append({"player_name": r.player_name, "candidate_score": r.candidate_score, "kind": "alternative"})
    d = pd.DataFrame(rows).drop_duplicates("player_name").sort_values("candidate_score")
    colors = [AMBER if p == actual_on else (TEAL if k == "top of shortlist" else SLATE)
              for p, k in zip(d["player_name"], d["kind"])]
    fig = go.Figure(go.Bar(y=d["player_name"], x=d["candidate_score"], orientation="h", marker_color=colors,
                           text=[f"{v:.0f}" + ("  ← actually came on" if p == actual_on else "")
                                 for v, p in zip(d["candidate_score"], d["player_name"])],
                           textposition="outside", cliponaxis=False))
    c = rec["context"]
    fig.update_layout(title=sub(title, f"{c['team_name']} vs {c['opponent']}, elapsed {c['elapsed']:.0f}', score "
                                       f"{c['team_score']}-{c['opponent_score']} ({c['game_state']}) · intent "
                                       f"'{rec['intent']}' · off: {rec['recommended_off']['player_name']} · a heuristic "
                                       f"shortlist under stated weights — NOT a forecast of what would have happened"),
                      xaxis=dict(title="candidate score (0–100)", range=[0, 125]),
                      height=max(340, 46 * len(d) + 140), margin=dict(l=190))
    return fig


def manpower_chart(subs: pd.DataFrame | None, sending_offs: pd.DataFrame | None, team: str | None) -> go.Figure:
    """Substitutions by manpower state at the time (level, a player up, a player down)."""
    s = _subs(subs, team)
    msg = _missing(s, ["man_advantage", "minute"])
    if msg:
        return _empty(msg, "Manpower-state analysis")
    lab = s["man_advantage"].map(lambda v: "player up" if v > 0 else "player down" if v < 0 else "level")
    tab = lab.value_counts().reindex(["level", "player up", "player down"]).fillna(0)
    med = s.groupby(lab)["minute"].median()
    n_red = 0 if sending_offs is None else len(sending_offs)
    fig = go.Figure(go.Bar(x=tab.index, y=tab.values, marker_color=[SLATE, TEAL, RED],
                           text=[f"{int(v)} subs" + (f" · median {med.get(k, np.nan):.0f}'" if v else "")
                                 for k, v in tab.items()], textposition="outside"))
    fig.update_layout(title=sub(f"{team or 'All teams'}: substitutions by manpower state",
                                f"n = {len(s)} substitutions · {n_red} sending-offs in the whole dataset — the unequal "
                                f"states rest on very few matches" + low_sample(int(tab.iloc[1:].sum()), 20,
                                                                                "substitutions at unequal strength")),
                      yaxis=dict(title="substitutions", range=[0, max(tab.max() * 1.2, 1)]), height=400)
    return fig


def role_tendency(subs: pd.DataFrame | None, team: str | None) -> go.Figure:
    """Share of substitutions by the role of the player leaving, with Wilson intervals."""
    s = _subs(subs, team)
    msg = _missing(s, ["off_role"])
    if msg:
        return _empty(msg, "Role-specific substitution tendency")
    d = s.dropna(subset=["off_role"])
    if d.empty:
        return _empty("No substitution has the outgoing role recorded.", "Role-specific substitution tendency")
    c = d["off_role"].value_counts()
    lo, hi = wilson_interval(c.values, len(d))
    p = c.values / len(d)
    fig = go.Figure(go.Bar(x=c.index, y=p * 100, marker_color=NAVY,
                           error_y=dict(type="data", symmetric=False, array=(hi - p) * 100, arrayminus=(p - lo) * 100,
                                        color=MUTED), text=[f"{v}" for v in c.values], textposition="inside"))
    fig.update_layout(title=sub(f"{team or 'All teams'}: which roles are substituted off",
                                f"n = {len(d)} substitutions · bars = share by role of the player leaving, whiskers = "
                                f"95% Wilson interval, label = count · not adjusted for how many players of each role "
                                f"are on the pitch"),
                      yaxis_title="% of substitutions", xaxis_title="role going off", height=420)
    return fig


def bench_utilisation(subs: pd.DataFrame | None, team_stats: pd.DataFrame | None, team: str) -> go.Figure:
    """Number of substitutions used per match."""
    s = _subs(subs, team)
    msg = _missing(s, ["match_id"]) or _missing(team_stats, ["team_name", "match_id"])
    if msg:
        return _empty(msg, "Bench utilisation")
    ids = team_stats.loc[team_stats["team_name"] == team, "match_id"]
    per = s.groupby("match_id").size().reindex(ids).fillna(0).astype(int)
    c = per.value_counts().sort_index()
    limit = int(s["max_subs_allowed"].max()) if "max_subs_allowed" in s and len(s) else None
    fig = go.Figure(go.Bar(x=c.index.astype(str), y=c.values, marker_color=TEAL, text=c.values,
                           textposition="outside"))
    fig.update_layout(title=sub(f"{team}: substitutions used per match",
                                f"n = {len(per)} matches · mean {per.mean():.2f}"
                                + (f" of {limit} allowed (configured rule, verify against competition regulations)"
                                   if limit else "")),
                      xaxis_title="substitutions used in a match", yaxis_title="matches", height=380)
    return fig


def response_chart(response: pd.DataFrame | None, team: str) -> go.Figure:
    """Minutes from conceding a goal to the team's next substitution (censored when no further change was made)."""
    msg = _missing(response, ["team", "conceded_minute", "minutes_to_next_sub"])
    if msg:
        return _empty(msg, "Response after conceding")
    d = response[response["team"] == team]
    if d.empty:
        return _empty(f"{team} conceded no goals in the analysed matches.", "Response after conceding")
    done = d.dropna(subset=["minutes_to_next_sub"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=done["conceded_minute"], y=done["minutes_to_next_sub"], mode="markers",
                             name=f"substitution followed (n={len(done)})",
                             marker=dict(size=11, color=NAVY, line=dict(color="white", width=1))))
    none = d[d["minutes_to_next_sub"].isna()]
    if len(none):
        fig.add_trace(go.Scatter(x=none["conceded_minute"], y=[0] * len(none), mode="markers",
                                 name=f"no further substitution (n={len(none)})",
                                 marker=dict(size=11, color=RED, symbol="x")))
    med = f"median {done['minutes_to_next_sub'].median():.0f} min" if len(done) else "no following substitutions"
    fig.update_layout(title=sub(f"{team}: time from conceding to the next substitution",
                                f"n = {len(d)} goals conceded · {med} · the next change may have been planned anyway "
                                f"or forced by injury: this is a timing description, not a measured reaction"
                                + low_sample(len(d), 20, "goals conceded")),
                      xaxis_title="minute the goal was conceded", yaxis_title="minutes until the next substitution",
                      height=420, legend=dict(orientation="h", y=-0.2))
    return fig


def manager_reference(pooled: pd.DataFrame | None, manager: str) -> go.Figure:
    """Focus manager's indicators next to the pooled value of all other managers (small multiples)."""
    if pooled is None or pooled.empty or pooled.shape[1] < 3:
        return _empty("No pooled reference available.", "Manager comparison")
    ind, a, b = pooled.columns[0], pooled.columns[1], pooled.columns[2]
    d = pooled.dropna(subset=[a, b])
    cols = 4
    rows = int(np.ceil(len(d) / cols))
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=[str(x).replace("_", " ") for x in d[ind]])
    for i, r in enumerate(d.itertuples(index=False)):
        fig.add_trace(go.Bar(x=[manager.split()[-1], "pooled others"], y=[r[1], r[2]], marker_color=[NAVY, SLATE],
                             text=[f"{r[1]:.1f}", f"{r[2]:.1f}"], textposition="outside", showlegend=False),
                      i // cols + 1, i % cols + 1)
    fig.update_yaxes(showticklabels=False)
    fig.update_layout(title=sub(f"{manager} against the pooled reference",
                                f"{b} · the other managers each have two matches, all against the focus team, so the "
                                f"pooled bar is a description of this fixture list — not a peer benchmark"),
                      height=230 * rows + 120)
    return fig


def manager_uncertainty(profiles: pd.DataFrame | None, min_matches: int = 2) -> go.Figure:
    """Share of substitutions made while trailing per manager: raw, Wilson interval and shrunk estimate."""
    msg = _missing(profiles, ["manager", "matches", "substitutions", "subs_when_trailing_pct"])
    if msg:
        return _empty(msg, "Manager pattern uncertainty")
    d = profiles[(profiles["matches"] >= min_matches) & (profiles["substitutions"] > 0)].copy()
    if d.empty:
        return _empty("No manager has enough matches.", "Manager pattern uncertainty")
    k = (d["subs_when_trailing_pct"] / 100 * d["substitutions"]).round()
    n = d["substitutions"]
    lo, hi = wilson_interval(k, n)
    prior = float(k.sum() / n.sum())
    d["raw"], d["lo"], d["hi"] = k / n * 100, lo * 100, hi * 100
    d["shrunk"] = shrunk_proportion(k, n, prior, 20) * 100
    d = d.sort_values("matches")
    lab = [f"{m} ({int(g)} m, {int(s)} subs)" for m, g, s in zip(d["manager"], d["matches"], d["substitutions"])]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["raw"], y=lab, mode="markers", name="raw share", marker=dict(color=NAVY, size=9),
                             error_x=dict(type="data", symmetric=False, array=d["hi"] - d["raw"],
                                          arrayminus=d["raw"] - d["lo"], color=GRID, thickness=4, width=0)))
    fig.add_trace(go.Scatter(x=d["shrunk"], y=lab, mode="markers", name="shrunk towards pooled share",
                             marker=dict(color=AMBER, size=9, symbol="diamond")))
    fig.add_vline(x=prior * 100, line=dict(color=MUTED, dash="dot"), annotation_text="pooled")
    fig.update_layout(title=sub("Share of substitutions made while trailing, by manager",
                                f"{len(d)} managers with ≥ {min_matches} matches · bar = 95% Wilson interval · diamond "
                                f"= beta-binomial shrinkage with 20 pseudo-substitutions · wide intervals mean the "
                                f"managers cannot be ranked on this"),
                      xaxis=dict(title="% of substitutions made while trailing", range=[0, 100]),
                      height=max(420, 26 * len(d) + 150), margin=dict(l=280), legend=dict(orientation="h", y=1.06))
    return fig


def manager_timeline(team_stats: pd.DataFrame | None, team: str) -> go.Figure:
    """Manager recorded for each match of the team (identity as published in the matches file)."""
    from src.visualization.theme import RESULT_COLORS, _team

    t = _team(team_stats, team)
    msg = _missing(t, ["manager_name", "match_date", "result"])
    if msg:
        return _empty(msg, "Manager by match")
    t = t.dropna(subset=["manager_name"])
    if t.empty:
        return _empty("No manager identity is recorded for this team.", "Manager by match")
    fig = go.Figure(go.Scatter(x=t["match_date"], y=t["manager_name"], mode="markers",
                               marker=dict(size=13, color=[RESULT_COLORS[r] for r in t["result"]],
                                           line=dict(color="white", width=1.5)),
                               text=t["opponent"], hovertemplate="%{x|%d %b %Y} vs %{text}<extra></extra>"))
    counts = t["manager_name"].value_counts()
    fig.update_layout(title=sub(f"{team}: manager recorded for each match",
                                " · ".join(f"{m}: {n} matches" for m, n in counts.items())
                                + " · source: managers field of the matches file · tenure outside these matches is "
                                  "not in the data · colour = result"),
                      height=280, yaxis_title="")
    return fig


def tactical_change_frequency(team_stats: pd.DataFrame | None, team: str) -> go.Figure:
    """Recorded in-match formation changes per match."""
    from src.visualization.theme import RESULT_COLORS, _mlabel, _team

    t = _team(team_stats, team)
    msg = _missing(t, ["in_match_formation_changes", "result"])
    if msg:
        return _empty(msg, "Tactical change frequency")
    fig = go.Figure(go.Bar(x=[_mlabel(r) for _, r in t.iterrows()], y=t["in_match_formation_changes"],
                           marker_color=[RESULT_COLORS[r] for r in t["result"]]))
    share = float((t["in_match_formation_changes"] > 0).mean())
    fig.update_layout(title=sub(f"{team}: recorded formation changes within matches",
                                f"n = {len(t)} matches · a change was recorded in {share:.0%} of them · counts "
                                f"Tactical Shift events whose formation differs from the previous record · colour = "
                                f"result"),
                      yaxis=dict(title="formation changes", dtick=1), height=420,
                      xaxis=dict(tickangle=-60, tickfont=dict(size=9)))
    return fig


def decision_audit_trail(subs: pd.DataFrame | None, formations: pd.DataFrame | None, match_id: Any, team: str
                         ) -> go.Figure:
    """Chronological log of one team's recorded decisions in one match: substitutions and formation changes."""
    rows = []
    if subs is not None and len(subs):
        for r in subs[(subs["match_id"] == match_id) & (subs["team_name"] == team)].itertuples():
            rows.append({"minute": r.minute, "decision": "Substitution",
                         "detail": f"{r.player_off_name} off, {r.player_on_name} on",
                         "score state": r.game_state, "score": f"{r.team_score}-{r.opponent_score}",
                         "roles": f"{r.off_role or '?'} → {r.on_role or '?'}",
                         "source tag": r.sub_reason if isinstance(r.sub_reason, str) else "—"})
    if formations is not None and len(formations):
        f = formations[(formations["match_id"] == match_id) & (formations["team_name"] == team)]
        for r in f.itertuples():
            rows.append({"minute": r.minute, "decision": r.type, "detail": f"formation {r.formation}",
                         "score state": "", "score": "", "roles": "",
                         "source tag": "changed" if getattr(r, "formation_changed", False) else "—"})
    if not rows:
        return _empty("No recorded decisions for this team in this match.", "Decision audit trail")
    d = pd.DataFrame(rows).sort_values("minute").reset_index(drop=True)
    return table_figure(d, f"{team}: recorded decision audit trail", max_rows=30)


def evidence_cards_table(cards: list[dict] | None) -> go.Figure:
    """Evidence cards as a table (finding, evidence, scope, chart, limitation)."""
    if not cards:
        return _empty("No evidence cards were generated.", "Decision evidence cards")
    d = pd.DataFrame([{"finding": c.get("finding"), "evidence": c.get("evidence"), "scope": c.get("scope"),
                       "chart": c.get("chart_id"), "cannot tell us": c.get("limitation")} for c in cards])
    return table_figure(d, "Decision evidence cards", max_rows=12)
