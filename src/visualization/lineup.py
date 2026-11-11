"""Lineup, formation and squad-structure charts added in V3 (catalogue family G)."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.visualization.theme import (AMBER, FAMILY_COLORS, INK, NAVY, RED,
                                     SLATE, TEAL, _empty, _missing, heat, sub,
                                     table_figure)


def slot_suitability(long: pd.DataFrame | None, formation: str, top_players: int = 18) -> go.Figure:
    """Candidate score for every formation slot (blank where the player is not eligible for the slot role)."""
    msg = _missing(long, ["slot", "player_name", "score", "feasible"])
    if msg:
        return _empty(msg, "Formation slots and role suitability")
    d = long[long["feasible"].astype(bool)]
    if d.empty:
        return _empty("No eligible player-slot pair.", "Formation slots and role suitability")
    keep = d.groupby("player_name")["score"].max().sort_values(ascending=False).head(top_players).index
    slots = list(dict.fromkeys(long["slot"]))
    m = d[d["player_name"].isin(keep)].pivot_table(index="player_name", columns="slot", values="score").reindex(
        index=keep, columns=slots)
    fig = heat(m.to_numpy(float), slots, list(m.index), "", fmt=".0f", colorbar="score", zmin=0, zmax=100)
    fig.update_layout(title=sub(f"{formation}: candidate score by slot",
                                f"{len(keep)} highest-scoring candidates · score = weighted components × position "
                                f"compatibility (0–100) · blank = not eligible for that slot role · the assignment "
                                f"picks one player per slot to maximise the total"),
                      margin=dict(l=190))
    return fig


def role_occupancy(appearances: pd.DataFrame | None, team: str, min_minutes: float = 90) -> go.Figure:
    """Minutes of each player in each match role."""
    msg = _missing(appearances, ["team_name", "player_name", "match_role", "minutes_played"])
    if msg:
        return _empty(msg, "Role occupancy matrix")
    d = appearances[(appearances["team_name"] == team) & (appearances["minutes_played"] > 0)
                    & appearances["match_role"].notna()]
    if d.empty:
        return _empty("No appearances for this team.", "Role occupancy matrix")
    m = d.pivot_table(index="player_name", columns="match_role", values="minutes_played", aggfunc="sum")
    m = m[m.sum(axis=1) >= min_minutes]
    m = m.loc[m.sum(axis=1).sort_values(ascending=False).index]
    multi = int((m.notna().sum(axis=1) > 1).sum())
    fig = heat(m.to_numpy(float), list(m.columns), list(m.index), "", fmt=".0f", colorbar="minutes")
    fig.update_layout(title=sub(f"{team}: role occupancy — minutes by player and match role",
                                f"{len(m)} players with ≥ {min_minutes:.0f} minutes · {multi} played more than one "
                                f"role · role = position recorded for the player in that match · blank = never played "
                                f"there"),
                      margin=dict(l=190))
    return fig


def formation_transitions(formations: pd.DataFrame | None, team: str) -> go.Figure:
    """Recorded in-match formation changes (Starting XI to Tactical Shift) as a Sankey."""
    msg = _missing(formations, ["match_id", "team_name", "index", "formation", "type"])
    if msg:
        return _empty(msg, "Formation transitions")
    f = formations[formations["team_name"] == team].sort_values(["match_id", "index"])
    f = f.dropna(subset=["formation"])
    pairs = []
    for _, g in f.groupby("match_id"):
        seq = [x for i, x in enumerate(g["formation"].tolist()) if i == 0 or x != g["formation"].tolist()[i - 1]]
        pairs += list(zip(seq[:-1], seq[1:]))
    if not pairs:
        return _empty(f"No in-match formation change is recorded for {team}.", "Formation transitions")
    tab = pd.Series(pairs).value_counts()
    left = sorted({a for a, _ in tab.index})
    right = sorted({b for _, b in tab.index})
    fig = go.Figure(go.Sankey(
        node=dict(label=[f"from {x}" for x in left] + [f"to {x}" for x in right],
                  color=[NAVY] * len(left) + [TEAL] * len(right), pad=18, thickness=16),
        link=dict(source=[left.index(a) for a, _ in tab.index], target=[len(left) + right.index(b) for _, b in tab.index],
                  value=tab.values.tolist(), color="rgba(141,153,174,0.35)")))
    fig.update_layout(title=sub(f"{team}: recorded in-match formation changes",
                                f"{len(pairs)} changes in {f['match_id'].nunique()} matches · from Starting XI and "
                                f"Tactical Shift events · a recorded label change, not a full description of shape in "
                                f"and out of possession"), height=440)
    return fig


def role_metric_profile(medians: pd.DataFrame | None) -> go.Figure:
    """Median per-90 profile of each role family, as column-wise z-scores with the raw medians printed."""
    if medians is None or medians.empty:
        return _empty("No eligible players.", "Role metric profile")
    from src.visualization.distribution import nice

    vals = medians.drop(columns=["players"], errors="ignore")
    z = (vals - vals.mean()) / vals.std().replace(0, 1)
    fig = go.Figure(go.Heatmap(z=z.to_numpy(float), x=[nice(c) for c in vals.columns],
                               y=[f"{i} (n={int(medians.loc[i, 'players'])})" if "players" in medians else str(i)
                                  for i in vals.index],
                               colorscale=[[0, RED], [0.5, "#f7f5f0"], [1, NAVY]], zmid=0, xgap=2, ygap=2,
                               text=np.round(vals.to_numpy(float), 2), texttemplate="%{text}",
                               colorbar=dict(title="z across<br>role families", thickness=12)))
    fig.update_layout(title=sub("Position profile: median metric by role family",
                                "eligible players only · numbers = raw medians · colour = z-score of the median across "
                                "the role families shown"),
                      height=380, xaxis=dict(tickangle=-35), yaxis=dict(autorange="reversed"), margin=dict(l=170))
    return fig


def bench_composition(appearances: pd.DataFrame | None, matches: pd.DataFrame | None, team: str,
                      season_pct: pd.DataFrame | None) -> go.Figure:
    """Role-family make-up of the bench in every match (primary role of each bench player over the season)."""
    msg = _missing(appearances, ["team_name", "is_starter", "player_id", "match_id"])
    if msg:
        return _empty(msg, "Bench role composition")
    b = appearances[(appearances["team_name"] == team) & (~appearances["is_starter"].astype(bool))]
    if b.empty:
        return _empty("No bench players recorded for this team.", "Bench role composition")
    fam = season_pct.drop_duplicates("player_id").set_index("player_id")["role_family"] \
        if season_pct is not None else pd.Series(dtype=object)
    b = b.assign(family=b["player_id"].map(fam).fillna("No minutes this season")).merge(
        matches[["match_id", "match_date"]], on="match_id").sort_values("match_date")
    tab = pd.crosstab(b["match_date"], b["family"])
    order = [c for c in ("Goalkeeper", "Defender", "Midfielder", "Forward", "No minutes this season") if c in tab]
    fig = go.Figure()
    for c in order:
        fig.add_bar(x=tab.index, y=tab[c], name=c, marker_color=FAMILY_COLORS.get(c, "#d9d4c7"))
    fig.update_layout(barmode="stack", title=sub(f"{team}: bench composition by role family",
                                                 f"{len(tab)} matches · mean bench size {tab.sum(axis=1).mean():.1f} · "
                                                 f"family = the player's primary role this season (bench players have "
                                                 f"no recorded position on the day)"),
                      yaxis_title="players on the bench", height=420, legend=dict(orientation="h", y=-0.2))
    return fig


def co_start_network(counts: pd.DataFrame | None, team: str, min_together: int | None = None) -> go.Figure:
    """Players linked by how often they started together (circular layout; position carries no meaning)."""
    if counts is None or counts.empty:
        return _empty("No starting lineups for this team.", "Co-start network")
    names = list(counts.index)
    starts = np.diag(counts.to_numpy())
    n = len(names)
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    x, y = np.cos(ang), np.sin(ang)
    off = counts.to_numpy(float).copy()
    np.fill_diagonal(off, 0)
    thr = min_together if min_together is not None else max(3, int(np.quantile(off[off > 0], 0.6))) if (off > 0).any() else 1
    fig = go.Figure()
    mx = off.max() or 1
    for i in range(n):
        for j in range(i + 1, n):
            if off[i, j] >= thr:
                fig.add_trace(go.Scatter(x=[x[i], x[j]], y=[y[i], y[j]], mode="lines", hoverinfo="skip",
                                         line=dict(color=NAVY, width=0.5 + 5 * off[i, j] / mx),
                                         opacity=0.15 + 0.55 * off[i, j] / mx, showlegend=False))
    fig.add_trace(go.Scatter(x=x, y=y, mode="markers+text", text=[str(p).split()[-1] for p in names],
                             textposition=["middle right" if c >= 0 else "middle left" for c in x],
                             marker=dict(size=10 + 20 * starts / starts.max(), color=TEAL,
                                         line=dict(color="white", width=2)),
                             customdata=starts, hovertext=names,
                             hovertemplate="%{hovertext}: %{customdata} starts<extra></extra>", showlegend=False))
    fig.update_layout(title=sub(f"{team}: co-start network",
                                f"{n} players with ≥ 5 starts · node size = starts · link = started together at least "
                                f"{thr} times (width = count) · circular layout: positions carry no meaning"),
                      xaxis=dict(visible=False, range=[-1.6, 1.6]), yaxis=dict(visible=False, scaleanchor="x"),
                      height=560)
    return fig


def pairing_heatmap(matrix: pd.DataFrame | None, team: str) -> go.Figure:
    """Shared on-pitch minutes for each pair of players."""
    if matrix is None or matrix.empty:
        return _empty("No shared minutes for this selection.", "Player pairing minutes")
    m = matrix.copy().astype(float)
    arr = m.to_numpy()
    np.fill_diagonal(arr, np.nan)
    fig = heat(arr, [str(c).split()[-1] for c in m.columns], list(m.index), "", fmt=".0f", colorbar="minutes",
               hover="%{y} with %{x}: %{z:.0f} shared minutes<extra></extra>")
    fig.update_layout(title=sub(f"{team}: minutes on the pitch together",
                                f"{len(m)} players · from reconstructed on-pitch spells (validated: no overlapping "
                                f"spells, minutes reconcile with period lengths) · diagonal left blank"),
                      xaxis=dict(tickangle=-45), height=max(520, 28 * len(m) + 170), margin=dict(l=190))
    return fig


def formation_sensitivity(comparison: pd.DataFrame | None, team: str) -> go.Figure:
    """Total heuristic score of the best assignment under each formation template."""
    msg = _missing(comparison, ["formation", "total_score", "mean_compatibility", "warnings"])
    if msg:
        return _empty(msg, "Formation sensitivity")
    d = comparison.sort_values("total_score")
    fig = go.Figure(go.Bar(y=d["formation"], x=d["total_score"], orientation="h",
                           marker_color=[TEAL if w == d["warnings"].min() else SLATE for w in d["warnings"]],
                           text=[f"{s:.0f} · compat {c:.2f} · {int(w)} warning(s)" for s, c, w in
                                 zip(d["total_score"], d["mean_compatibility"], d["warnings"])],
                           textposition="outside", cliponaxis=False))
    spread = d["total_score"].max() - d["total_score"].min()
    fig.update_layout(title=sub(f"{team}: sensitivity of the shortlist to the formation template",
                                f"{len(d)} templates · best assignment under the current weights for each · spread "
                                f"{spread:.0f} points · totals are heuristic scores, comparable only within this "
                                f"scoring model"),
                      xaxis=dict(title="sum of slot scores (11 slots, 0–100 each)",
                                 range=[0, d["total_score"].max() * 1.35]),
                      height=max(380, 34 * len(d) + 130), margin=dict(l=90))
    return fig


def selection_frontier(long: pd.DataFrame | None, lineup: pd.DataFrame | None, x: str = "role_fit",
                       y: str = "recent_form") -> go.Figure:
    """Trade-off between two score components for each candidate at his best slot, with the Pareto front."""
    msg = _missing(long, ["player_name", "score", "feasible", x, y])
    if msg:
        return _empty(msg, "Candidate trade-off frontier")
    d = long[long["feasible"].astype(bool)].sort_values("score", ascending=False).drop_duplicates("player_name")
    d = d.dropna(subset=[x, y])
    if d.empty:
        return _empty("No candidate has both components.", "Candidate trade-off frontier")
    pts = d[[x, y]].to_numpy(float)
    front = np.array([not np.any((pts[:, 0] >= p[0]) & (pts[:, 1] >= p[1]) & ((pts[:, 0] > p[0]) | (pts[:, 1] > p[1])))
                      for p in pts])
    chosen = set(lineup["player_name"]) if lineup is not None and "player_name" in lineup else set()
    rng = np.random.default_rng(0)
    jit = rng.uniform(-1.2, 1.2, len(d))
    fig = go.Figure(go.Scatter(x=d[x], y=d[y] + jit, mode="markers+text",
                               text=d["player_name"].str.split().str[-1], textposition="top center",
                               textfont=dict(size=9),
                               marker=dict(size=13, color=[TEAL if p in chosen else SLATE for p in d["player_name"]],
                                           symbol=["diamond" if f else "circle" for f in front],
                                           line=dict(color=INK, width=[2 if f else 0.5 for f in front])),
                               hovertext=d["player_name"], customdata=d["slot"],
                               hovertemplate="%{hovertext} (best slot %{customdata})<br>" + x + " %{x:.0f}"
                                             "<extra></extra>"))
    fig.update_layout(title=sub(f"Candidate trade-off: {x.replace('_', ' ')} vs {y.replace('_', ' ')}",
                                f"{len(d)} eligible candidates at their best slot · teal = in the shortlisted XI · "
                                f"diamond with dark outline = Pareto-efficient (no candidate is better on both) · "
                                f"small vertical jitter separates tied points"),
                      xaxis_title=f"{x.replace('_', ' ')} (0–100)", yaxis_title=f"{y.replace('_', ' ')} (0–100)",
                      height=480)
    return fig


def feasibility_audit(result: Any, ctx: Any, formation: str) -> go.Figure:
    """Constraint checklist of a shortlisted XI: what was enforced and what evidence is missing."""
    if result is None or getattr(result, "lineup", None) is None or result.lineup.empty:
        return _empty("No lineup could be formed.", "Constraint feasibility audit")
    lu = result.lineup
    gk = int((lu["slot_role"] == "GK").sum())
    rows = [
        ("Eleven players selected", len(lu) == 11, f"{len(lu)} slots filled"),
        ("No player selected twice", lu["player_id"].is_unique, f"{lu['player_id'].nunique()} distinct players"),
        ("Exactly one goalkeeper", gk == 1, f"{gk} goalkeeper slot(s)"),
        ("Every pick eligible for his slot role", bool((lu["compatibility"] > 0).all()),
         f"minimum compatibility {lu['compatibility'].min():.2f}"),
        ("All picks from the squad pool", True, getattr(ctx, "pool_description", "pool as described in the context")),
        ("Natural-role picks", bool((lu["compatibility"] >= 1).all()),
         f"{int((lu['compatibility'] < 1).sum())} pick(s) out of primary role"),
        ("Picks with low evidence coverage", not lu["coverage_label"].astype(str).str.contains("low").any(),
         f"{int(lu['coverage_label'].astype(str).str.contains('low').sum())} pick(s) flagged low coverage"),
        ("Recent-form fallback used", not lu["form_fallback"].astype(bool).any(),
         f"{int(lu['form_fallback'].astype(bool).sum())} pick(s) scored on season value (no recent minutes)"),
        ("Injury / fitness availability checked", False, "NOT POSSIBLE: no availability data in the source — the "
                                                         "analyst must mark unavailable players manually"),
    ]
    for w in getattr(result, "warnings", []) or []:
        rows.append(("Optimiser warning", False, str(w)))
    d = pd.DataFrame(rows, columns=["constraint or evidence check", "satisfied", "detail"])
    d["satisfied"] = d["satisfied"].map({True: "yes", False: "no / attention"})
    return table_figure(d, f"{formation}: constraint feasibility and evidence audit", max_rows=20)


def xi_agreement_chart(agreement: pd.DataFrame | None, team: str) -> go.Figure:
    """Share of the actual starting XI that the heuristic also shortlisted, match by match."""
    msg = _missing(agreement, ["match_date", "opponent", "agreement_pct"])
    if msg:
        return _empty(msg, "Shortlist vs actual XI")
    d = agreement.sort_values("match_date")
    fig = go.Figure(go.Bar(x=[f"{dt:%d %b} {str(o)[:10]}" for dt, o in zip(d["match_date"], d["opponent"])],
                           y=d["agreement_pct"], marker_color=NAVY,
                           hovertemplate="%{x}: %{y:.0f}% of the actual XI<extra></extra>"))
    fig.add_hline(y=d["agreement_pct"].mean(), line=dict(color=AMBER, dash="dash"),
                  annotation_text=f"mean {d['agreement_pct'].mean():.1f}%")
    fig.update_layout(title=sub(f"{team}: overlap between the pre-match shortlist and the actual XI",
                                f"n = {len(d)} matches (first match has no history) · shortlist built only from "
                                f"information available before each match · agreement measures similarity to the "
                                f"manager's choice, NOT whether either choice was better"),
                      yaxis=dict(title="% of actual starters also shortlisted", range=[0, 105]), height=440,
                      xaxis=dict(tickangle=-60, tickfont=dict(size=9)))
    return fig
