"""Starting XI Lab: a constraint-aware, transparent shortlist built only from information available before a match."""
from __future__ import annotations

import dataclasses

import streamlit as st

from src.analytics import lineup_optimizer as xi
from src.dashboard import components as ui
from src.dashboard import filters, layout, state
from src.visualization import lineup, registry, tactics
from src.visualization.theme import finalize

base, ws, tm = layout.start("Starting XI Lab", "Which eleven does the available evidence shortlist for a formation, "
                            "why is each player in it, and how sensitive is that to the weights?",
                            eyebrow="Decision support")
if layout.empty_scope(tm):
    st.stop()

team = st.session_state["f_team"]
layout.note("<b>Analyst-assisted shortlist, not an optimal XI.</b> The score is a transparent heuristic: the "
            "result is best only under the weights and constraints shown here. The source has no injury, fitness "
            "or training data — mark unavailable players yourself.")

c1, c2 = st.columns([0.6, 0.4])
with c1:
    mid = filters.match_select(ws, tm, key="w_xi_match", label_text="Decision point: before this match")
row = tm[tm["match_id"] == mid].iloc[0]
default_form = row["starting_formation"] if row["starting_formation"] in ws.cfg.formation_templates else None
with c2:
    formation = filters.formation_select(ws, "w_xi_formation", default_form)

ctx = ws.xi_context(team, mid)
names = ctx.candidates.set_index("player_id")["player_name"].to_dict()

with st.expander("Weights and availability", expanded=not layout.presentation()):
    st.caption("Components are scaled 0–100 and the weights are normalised to sum to 1. Each slot score is then "
               "multiplied by the position compatibility of the player's primary role for that slot.")
    cols = st.columns(5)
    labels = {"role_fit": "Role fit", "recent_form": "Recent form", "sample_reliability": "Evidence volume",
              "workload_suitability": "Minutes-based exposure", "lineup_continuity": "Continuity"}
    raw = {k: cols[i].slider(labels[k], 0.0, 1.0, float(v), 0.05, key=f"w_xi_w_{k}")
           for i, (k, v) in enumerate(ws.cfg.xi_score_weights.items())}
    total = sum(raw.values())
    weights = {k: (v / total if total else 1 / len(raw)) for k, v in raw.items()}
    unavailable = st.multiselect("Players to treat as unavailable (your knowledge — not in the data)",
                                 list(names), format_func=lambda i: names[i], key="w_xi_unavailable")
    st.caption("Normalised weights: " + " · ".join(f"{labels[k]} {v:.2f}" for k, v in weights.items()))

cfg = dataclasses.replace(ws.cfg, xi_score_weights=weights)
result = xi.optimize_xi(ctx, formation, cfg, unavailable=list(unavailable))
long, _ = xi.score_candidates(ctx, formation, cfg, unavailable=list(unavailable))
scope = registry.scope_text(ws)

if result.lineup is None or result.lineup.empty:
    st.error("No lineup satisfies the constraints with the current pool. Remove some unavailability flags or "
             "choose another formation.")
    layout.footer()
    st.stop()

cmp_, share = xi.compare_with_actual(result, ws.tables["appearances"], mid, ws.team_id(team))
ui.kpi_row([
    ("Total heuristic score", f"{result.total_score:.0f}", "Sum of the eleven slot scores (0–100 each)."),
    ("Mean slot score", f"{result.total_score / 11:.1f}", None),
    ("Overlap with the actual XI", f"{share:.0%}", "Share of the players who actually started this match that the "
                                                   "shortlist also contains. Similarity, not quality."),
    ("Candidates in the pool", f"{len(ctx.candidates)}", ctx.pool_description),
    ("Optimiser warnings", f"{len(result.warnings or [])}", "; ".join(result.warnings or []) or "none"),
], per_row=5)

view = filters.view_select("View", ["Shortlist", "Why these players", "Versus the actual XI", "Alternatives",
                                    "Constraints", "Season backtest"], key="w_xi_view")

if view == "Shortlist":
    left, right = st.columns([0.55, 0.45])
    with left:
        fig = tactics.xi_pitch(result.lineup, f"{team}: shortlist in {formation} before {ws.match_label(mid)}")
        ui.show(finalize(fig, scope, synthetic=ws.synthetic, attribution=registry.attribution_text(ws)), key="xi_pitch")
        st.caption("Slot positions are template coordinates for the chosen formation, not tracked positions. "
                   "Shirt numbers are not shown on the pitch; they are in the squad table of the source.")
    with right:
        cols_ = ["slot", "player_name", "primary_role", "compatibility", "role_fit", "recent_form",
                 "sample_reliability", "workload_suitability", "lineup_continuity", "score", "coverage_label"]
        ui.table(result.lineup[cols_], "starting_xi_shortlist", key="xi_tbl", height=440)
elif view == "Why these players":
    fig = tactics.score_decomposition(result.lineup, weights, f"{formation}: score components per pick")
    ui.show(finalize(fig, scope, synthetic=ws.synthetic, attribution=registry.attribution_text(ws)), key="xi_decomp")
    left, right = st.columns(2)
    with left:
        ui.show(finalize(lineup.slot_suitability(long, formation), scope, synthetic=ws.synthetic, attribution=registry.attribution_text(ws)), key="xi_slots")
    with right:
        ui.show(finalize(lineup.selection_frontier(long, result.lineup), scope, synthetic=ws.synthetic, attribution=registry.attribution_text(ws)),
                key="xi_frontier")
    om = xi.explain_omissions(long, result.lineup, ctx, list(unavailable))
    st.markdown("**Players not shortlisted and why**")
    ui.table(om, "xi_omissions", key="xi_omit")
elif view == "Versus the actual XI":
    st.markdown(f"**{share:.0%}** of the players who actually started are also in the shortlist. Agreement means the "
                f"heuristic resembles the manager's choice; it does not show that either choice was better.")
    show = cmp_.assign(in_recommended=cmp_["in_recommended"].map({True: "yes", False: "—"}),
                       in_actual=cmp_["in_actual"].map({True: "yes", False: "—"}))
    ui.table(show.rename(columns={"in_recommended": "in shortlist", "in_actual": "actually started"}),
             "xi_vs_actual", key="xi_cmp")
    act = xi.actual_xi(ws.tables["appearances"], mid, ws.team_id(team))
    st.markdown("**Actual starting XI (positions recorded in the match)**")
    ui.table(act, "actual_xi", key="xi_actual")
elif view == "Alternatives":
    comp = xi.compare_formations(ctx, cfg, unavailable=list(unavailable))
    ui.show(finalize(lineup.formation_sensitivity(comp, team), scope, synthetic=ws.synthetic, attribution=registry.attribution_text(ws)), key="xi_sens")
    other = st.selectbox("Compare the shortlist with another formation",
                         [f for f in ws.cfg.formation_templates if f != formation], key="w_xi_other")
    alt = xi.optimize_xi(ctx, other, cfg, unavailable=list(unavailable))
    ui.show(finalize(tactics.alternative_xi_comparison(result.lineup, alt.lineup, formation, other), scope,
                     synthetic=ws.synthetic, attribution=registry.attribution_text(ws)), key="xi_alt")
    st.markdown("**What-if: force one player into a slot**")
    a, b = st.columns(2)
    slot = a.selectbox("Slot", result.lineup["slot"].tolist(), key="w_xi_slot")
    elig = long[(long["slot"] == slot) & long["feasible"].astype(bool)].sort_values("score", ascending=False)
    if elig.empty:
        st.info("No eligible candidate for this slot.")
    else:
        who = b.selectbox("Player", elig["player_id"].tolist(), format_func=lambda i: names.get(i, str(i)),
                          key="w_xi_force")
        forced, delta = xi.what_if(ctx, result, slot, who, cfg, unavailable=list(unavailable))
        st.metric("Change in total score", f"{delta:+.1f}",
                  help="Total score with the forced pick minus the unconstrained shortlist.")
        ui.table(forced.lineup[["slot", "player_name", "score", "forced"]], "xi_what_if", key="xi_force_tbl")
elif view == "Constraints":
    ui.show(lineup.feasibility_audit(result, ctx, formation), key="xi_audit")
    st.markdown("**Candidate pool before this match**")
    pool = ctx.candidates[["player_name", "primary_position", "primary_role", "minutes_played", "appearances",
                           "starts", "form_score", "minutes_prev_7d", "rest_days", "coverage_label"]]
    ui.table(pool.sort_values("minutes_played", ascending=False), "xi_pool", key="xi_pool")
    for n in ctx.notes or []:
        st.caption(n)
else:
    st.caption("For every match after the first, the shortlist is rebuilt from information available before that "
               "match and compared with the XI the manager actually picked. This takes about ten seconds.")
    if st.toggle("Run the season backtest", key="w_xi_backtest"):
        ui.chart("L-267", ws, state.params(ws), key="xi_agree")
        ui.table(ws.xi_agreement(team), "xi_agreement", key="xi_agree_tbl")
layout.footer()
