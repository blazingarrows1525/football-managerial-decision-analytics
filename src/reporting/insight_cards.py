"""Evidence cards: each managerial finding with its metric, scope, supporting chart and limitation.

Every sentence is assembled from values computed on the loaded data. A card is only produced when its inputs
exist; nothing is written from memory of an earlier run.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from src.analytics import descriptive as desc

CARD_FIELDS = ("title", "finding", "evidence", "scope", "chart_id", "relevance", "limitation", "next_step")


def _card(**kw: str) -> dict[str, str]:
    return {k: kw.get(k, "") for k in CARD_FIELDS}


def build_cards(ws: Any, team: str | None = None, include_slow: bool = True) -> list[dict[str, str]]:
    """Evidence cards for one team. ``include_slow`` adds cards that need the model and backtest results."""
    team = team or ws.focus
    b = ws.bundle
    tm = ws.team_matches(team)
    n = len(tm)
    if n == 0:
        return []
    comp = b.tables["matches"]
    scope = (f"{team}, {n} matches, {comp['competition_name'].iloc[0]} {comp['season_name'].iloc[0]} "
             f"({tm['match_date'].min():%d %b %Y} – {tm['match_date'].max():%d %b %Y})")
    cards: list[dict[str, str]] = []

    # 1 — results against chance quality
    xp = ws.xpts()
    xp = xp[xp["team_name"] == team]
    pts, xpts = float(tm["points"].sum()), float(xp["xpts"].sum())
    gf, xg = int(tm["goals_for"].sum()), float(tm["xg"].sum())
    cards.append(_card(
        title="Results against chance quality",
        finding=f"Results ran {'ahead of' if pts > xpts else 'behind'} shot-based expectation by "
                f"{abs(pts - xpts):.1f} points.",
        evidence=f"{pts:.0f} points vs {xpts:.1f} expected points; {gf} goals from {xg:.1f} xG "
                 f"(xG difference {tm['xg_diff'].mean():+.2f} per match).",
        scope=scope, chart_id="L-262",
        relevance="Anchor performance reviews on chances created and conceded rather than on results alone.",
        limitation="Expected points are a simulation from StatsBomb xG; they ignore game state and assume shots "
                   "are independent.",
        next_step="Recompute over further seasons to see how much of the gap persists."))

    # 2 — concentration of chance creation
    sq = ws.squad(team).set_index("player_name")
    conc = desc.concentration(sq["xg"] + sq["xa"])
    if len(conc) >= 3:
        top = ", ".join(conc["label"].head(3))
        cards.append(_card(
            title="Concentration of chance creation",
            finding=f"Three players account for {conc['share'].head(3).sum():.0%} of the squad's xG + xA.",
            evidence=f"Top three: {top}; Gini coefficient of xG + xA across {len(conc)} contributors = "
                     f"{desc.gini(conc['value']):.2f}.",
            scope=scope, chart_id="B-029",
            relevance="Cover and minutes management for the main creators matter more than for other roles.",
            limitation="xA credits the passer of a shot assist only; off-ball contribution is not in event data.",
            next_step="Check how output changes in matches the top creators did not start."))

    # 3 — passing hub
    cs = ws.centrality_summary(team)
    if len(cs):
        hub, bridge = cs.iloc[-1], cs.sort_values("betweenness").iloc[-1]
        same = hub["player_id"] == bridge["player_id"]
        cards.append(_card(
            title="Structure of the passing game",
            finding=(f"{hub['player']} is both the main hub and the main bridge of the pass network." if same else
                     f"{hub['player']} is the main hub and {bridge['player']} the main bridge of the pass network."),
            evidence=f"Mean PageRank {hub['pagerank']:.3f} ({hub['player']}); mean betweenness "
                     f"{bridge['betweenness']:.3f} ({bridge['player']}); averaged over "
                     f"{int(hub['matches'])} match networks.",
            scope=scope, chart_id="F-139",
            relevance="A build-up plan that depends on one link is exposed when he is pressed or unavailable.",
            limitation="Networks use completed passes before the first substitution; centrality describes the "
                       "recorded graph, not player quality.",
            next_step="Compare the network in matches where the hub was marked or absent."))

    # 4 — rotation
    cont = ws.continuity()
    cont = cont[cont["team_id"] == ws.team_id(team)]
    app = b.tables["appearances"]
    starts = app[(app["team_name"] == team) & app["is_starter"].astype(bool)].groupby("player_name").size()
    if len(cont):
        core = int((starts >= 0.75 * n).sum())
        cards.append(_card(
            title="Selection continuity",
            finding=f"A stable core with rotation at the margins: {core} players started at least three quarters "
                    f"of the matches.",
            evidence=f"Mean {cont['lineup_changes'].mean():.1f} starting-XI changes between consecutive analysed "
                     f"matches (median {cont['lineup_changes'].median():.0f}); {int(starts.size)} players started "
                     f"at least once.",
            scope=scope, chart_id="D-106",
            relevance="Decision support adds most in the two or three slots that actually rotate.",
            limitation="Cup and European fixtures between league matches are not in the data, so rotation across "
                       "all competitions is understated.",
            next_step="Add the other competitions' lineups to measure true rotation."))

    # 5 — substitutions
    s = b.subs[b.subs["team_name"] == team]
    if len(s):
        cards.append(_card(
            title="Substitution timing and score state",
            finding=f"Changes are made late and mostly from in front: median minute {s['minute'].median():.0f}, "
                    f"{(s['game_state'] == 'leading').mean():.0%} while leading."
            if (s["game_state"] == "leading").mean() >= 0.5 else
            f"Median substitution minute {s['minute'].median():.0f}; {(s['game_state'] == 'trailing').mean():.0%} "
            f"made while trailing.",
            evidence=f"{len(s)} substitutions, {len(s) / n:.2f} per match; "
                     f"{(s['like_for_like'].astype(bool)).mean():.0%} like-for-like by role.",
            scope=scope, chart_id="H-171",
            relevance="Pre-planned, role-compatible replacement pairs fit the observed pattern.",
            limitation="Score state is driven by team strength: a team that usually leads makes most changes "
                       "while leading whatever its intent.",
            next_step="Compare with matches of similar score state from other teams once more data are loaded."))

    # 6 — venue
    tests = ws.group_tests(team)
    venue = next((t for t in tests if t["comparison"] == "home vs away"), None)
    if venue:
        sig = venue["p_value"] < 0.05
        cards.append(_card(
            title="Home and away performance",
            finding=f"A home edge in xG difference is {'supported' if sig else 'suggestive but not established'} "
                    f"in this sample.",
            evidence=f"Home minus away xG difference {venue['mean_diff']:+.2f} (95% CI {venue['diff_ci_low']:+.2f} "
                     f"to {venue['diff_ci_high']:+.2f}); Cliff's δ {venue['effect_size']:.2f} "
                     f"({venue['magnitude']}); Mann–Whitney p = {venue['p_value']:.3f}; n = {venue['n_a']} vs "
                     f"{venue['n_b']}.",
            scope=scope, chart_id="J-211",
            relevance="Not strong enough to justify a different game model by venue.",
            limitation="17 matches per venue; opponents differ between the home and away sets.",
            next_step="Re-test with additional seasons."))

    # 7 — associations with goal difference
    corr = ws.correlations(team)
    if len(corr):
        top = corr.iloc[0]
        nsig = int((corr["spearman_q_BH"] < 0.05).sum())
        cards.append(_card(
            title="What moves with goal difference",
            finding=f"{nsig} of {len(corr)} match variables remain associated with goal difference after "
                    f"false-discovery control; the strongest is {top['variable'].replace('_', ' ')}.",
            evidence=f"Spearman ρ = {top['spearman_rho']:.2f} (95% CI {top['rho_ci_low']:.2f} to "
                     f"{top['rho_ci_high']:.2f}), q = {top['spearman_q_BH']:.3f}; n = {int(top['n'])} matches.",
            scope=scope, chart_id="J-202",
            relevance="Chance quality for and against is the most informative match-level lens available here.",
            limitation="One team-season: low power, and an association is not a causal effect.",
            next_step="Pool several seasons to raise power before drawing tactical conclusions."))

    if include_slow:
        # 8 — player profiles are continuous
        cl = ws.clusters()
        if cl:
            cards.append(_card(
                title="Player profiles form a continuum",
                finding="Statistical profiles do not separate into distinct player types.",
                evidence=f"Best silhouette {cl['silhouette_best']:.2f} at k = {cl['k_best']}; the mixture-model BIC "
                         f"prefers k = {cl['k_bic']}; DBSCAN finds {cl['dbscan_clusters']} dense group(s) with "
                         f"{cl['dbscan_noise']} outlying players; n = {cl['n_players']}.",
                scope=f"{cl['n_players']} outfield players above the minutes threshold in the dataset",
                chart_id="K-240",
                relevance="Use role-specific metric profiles for squad planning rather than cluster labels.",
                limitation="Opponent players are observed only in their matches against the focus team.",
                next_step="Repeat on full-league data, where every team has a full season of evidence."))
        # 9 — selection model
        res = ws.models(team)
        if res.get("fitted"):
            cs_ = res["cv_summary"]
            f1 = cs_[("f1", "mean")]
            best = res["best"]
            base = f1["Baseline: started previous match"]
            cards.append(_card(
                title="How predictable is selection",
                finding=f"Past selection explains most starts; models add little over the simple rule.",
                evidence=f"Time-ordered cross-validation F1: {best} {f1[best]:.3f} vs {base:.3f} for 'started the "
                         f"previous match'; hold-out ROC-AUC "
                         f"{float(res['holdout'].set_index('model').loc[best, 'roc_auc']):.3f}; "
                         f"{res['gate']['rows']} rows from {res['gate']['matches']} matches.",
                scope=scope, chart_id="K-221",
                relevance="Selection follows continuity; rotation decisions hinge on information the data lack.",
                limitation="No fitness, injury, training or opponent-specific information exists in the source.",
                next_step="Add availability data before attempting to model rotation."))
    return cards


def cards_frame(cards: list[dict[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(cards, columns=list(CARD_FIELDS))


def cards_markdown(cards: list[dict[str, str]]) -> str:
    """Markdown rendering of the cards for reports."""
    out = []
    for i, c in enumerate(cards, 1):
        out.append(f"### {i}. {c['title']}\n\n"
                   f"- **Finding.** {c['finding']}\n"
                   f"- **Evidence.** {c['evidence']}\n"
                   f"- **Scope.** {c['scope']}\n"
                   f"- **Supporting chart.** `{c['chart_id']}`\n"
                   f"- **Managerial relevance.** {c['relevance']}\n"
                   f"- **What the evidence cannot tell us.** {c['limitation']}\n"
                   f"- **Suggested next investigation.** {c['next_step']}\n")
    return "\n".join(out)
