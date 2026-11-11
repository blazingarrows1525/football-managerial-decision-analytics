"""Substitution Lab: historical substitution patterns and a labelled what-if shortlist at any minute of a match."""
from __future__ import annotations

import streamlit as st

from src.analytics import substitution_analysis as sa
from src.dashboard import components as ui
from src.dashboard import filters, layout, state
from src.visualization import manager, registry, substitution
from src.visualization.theme import finalize

base, ws, tm = layout.start("Substitution Lab", "When and in which situations are changes made, who replaces whom, "
                            "and which bench options does the evidence shortlist at a given moment?",
                            eyebrow="Decision support")
if layout.empty_scope(tm):
    st.stop()

team = st.session_state["f_team"]
subs = ws.bundle.subs[ws.bundle.subs["team_name"] == team]
p = state.params(ws)
scope = registry.scope_text(ws)

ui.kpi_row([
    ("Substitutions", f"{len(subs)}", "Substitution events of the team in the matches in scope."),
    ("Per match", f"{len(subs) / max(len(tm), 1):.2f}", None),
    ("Median minute", f"{subs['minute'].median():.0f}'" if len(subs) else "—", None),
    ("Made while leading", f"{(subs['game_state'] == 'leading').mean():.0%}" if len(subs) else "—",
     "Score state at the moment of the change, from the reconstructed goal timeline."),
    ("Like-for-like by role", f"{subs['like_for_like'].astype(bool).mean():.0%}" if len(subs) else "—", None),
    ("Tagged as injury", f"{int(subs['sub_reason'].astype(str).str.contains('Injury', case=False).sum())}"
     if len(subs) else "—", "Only substitutions the source tags as injury. No other availability data exist."),
])

view = filters.view_select("View", ["Historical patterns", "Scenario at a chosen minute", "Before / after windows",
                                    "Bench", "Backtest"], key="w_sub_view")

if view == "Historical patterns":
    if subs.empty:
        st.info("No substitutions in scope.")
    else:
        left, right = st.columns(2)
        with left:
            ui.chart("H-170", ws, p, key="sb_hist")
        with right:
            ui.chart("H-171", ws, p, key="sb_state")
        left, right = st.columns(2)
        with left:
            ui.chart("H-174", ws, p, key="sb_matrix")
        with right:
            ui.chart("H-172", ws, p, key="sb_role")
        ui.chart("H-173", ws, p, key="sb_sankey")
        layout.note("These are descriptive patterns. A team that usually leads makes most changes while leading "
                    "whatever its intent, and a substitution alone says nothing about injury or fatigue.")
elif view == "Scenario at a chosen minute":
    layout.note("<b>Counterfactual simulation.</b> The shortlist below is what a transparent heuristic would "
                "suggest at the chosen minute. It is not a historical fact and not a forecast of what would have "
                "happened.")
    a, b, c = st.columns([0.5, 0.25, 0.25])
    with a:
        mid = filters.match_select(ws, tm, key="w_sub_match")
    minute = b.slider("Elapsed minute", 46, 88, 65, key="w_sub_minute")
    intent = c.selectbox("Tactical intent", ["auto", "attack", "protect", "balance"], key="w_sub_intent",
                         help="auto = trailing → attack, leading → protect, level → balance")
    rec = ws.sub_scenario(team, mid, float(minute), None if intent == "auto" else intent)
    cx = rec["context"]
    ui.kpi_row([
        ("Score", f"{cx['team_score']}-{cx['opponent_score']}", f"{cx['game_state']} vs {cx['opponent']}"),
        ("Manpower", "level" if cx["man_advantage"] == 0 else f"{cx['man_advantage']:+d}",
         "From recorded sending-offs."),
        ("Substitutions used", f"{cx['subs_used']}", f"{cx['subs_remaining']} remaining under the configured rule"),
        ("Windows used", f"{cx['windows_used']}", f"{cx['windows_remaining']} remaining"),
        ("Intent applied", rec["intent"], rec.get("intent_reason", "")),
    ], per_row=5)
    st.caption(f"Rule source: {cx['rule_source']}")
    if rec.get("status") != "ok":
        st.warning(f"No shortlist at this moment: {rec.get('status')}")
    else:
        left, right = st.columns(2)
        with left:
            st.markdown("**On the pitch — who might come off**")
            ui.table(rec["outgoing_ranking"][["player_name", "role", "minutes_so_far", "booked",
                                              "involvement_vs_baseline", "outgoing_score", "reasons"]],
                     "outgoing_ranking", key="sb_out")
        with right:
            inc = sa.rank_incoming(cx, rec["recommended_off"].get("role"), rec["intent"], ws.cfg)
            st.markdown(f"**Bench — who could replace {rec['recommended_off']['player_name']}**")
            ui.table(inc[["player_name", "role", "candidate_score", "role_compatibility", "intent_fit", "recent_form",
                          "sample_reliability", "risks"]], "incoming_ranking", key="sb_in")
        actual = ws.bundle.subs[(ws.bundle.subs["match_id"] == mid) & (ws.bundle.subs["team_name"] == team)]
        nxt = actual[actual["elapsed_min"] >= minute].sort_values("elapsed_min")
        actual_on = nxt["player_on_name"].iloc[0] if len(nxt) else None
        left, right = st.columns(2)
        with left:
            ui.show(finalize(substitution.scenario_comparison(rec, actual_on), scope, synthetic=ws.synthetic, attribution=registry.attribution_text(ws)),
                    key="sb_scen")
        with right:
            fig = manager.candidate_comparison(inc, ws.cfg.sub_candidate_weights,
                                               f"Candidate score components at {minute}'")
            ui.show(finalize(fig, scope, synthetic=ws.synthetic, attribution=registry.attribution_text(ws)), key="sb_decomp")
        if actual_on:
            r0 = nxt.iloc[0]
            st.caption(f"Next actual change in this match: {r0['player_off_name']} off, {actual_on} on at "
                       f"{int(r0['minute'])}'. Candidates are limited to players named on the bench and not yet "
                       f"used at the chosen minute; fitness is unknown ({rec['recommended_on'].get('injury_status')}).")
        st.caption(rec.get("human_note", ""))
elif view == "Before / after windows":
    layout.note("<b>Descriptive only.</b> Windows before and after a substitution differ in score, opponent "
                "changes, fatigue and regression to the mean. The deltas below are not effects of the change.")
    imp = ws.impact()
    imp_t = imp[imp["team_name"] == team]
    if imp_t.empty:
        st.info("No substitution decisions in scope.")
    else:
        metric = st.selectbox("Metric", ["xg", "shots", "final_third_touches", "progressive_passes", "pressures"],
                              key="w_sub_metric")
        ui.show(finalize(manager.impact_chart(imp_t, metric), scope, synthetic=ws.synthetic, attribution=registry.attribution_text(ws)), key="sb_impact")
        c1, c2, c3 = st.columns(3)
        c1.metric("Decision windows", f"{len(imp_t)}")
        c2.metric("Contaminated windows", f"{imp_t['contaminated'].mean():.0%}",
                  help="A goal, a red card or another own substitution falls inside the window.")
        c3.metric("Opponent also changed", f"{imp_t['opponent_changed_in_window'].mean():.0%}")
        ui.table(sa.impact_summary(imp_t), "impact_summary", key="sb_imp_tbl")
elif view == "Bench":
    left, right = st.columns(2)
    with left:
        ui.chart("H-178", ws, p, key="sb_bench")
    with right:
        mid = filters.match_select(ws, tm, key="w_bench_match")
        ui.chart("H-179", ws, state.params(ws, match_id=mid), key="sb_bench_tl")
    ui.chart("I-191", ws, p, key="sb_used")
else:
    st.caption("For every non-injury substitution, the shortlist is rebuilt at the minute of the change and "
               "checked against the player who actually came on. This takes about thirty seconds.")
    if st.toggle("Run the substitution backtest", key="w_sub_backtest"):
        ag = ws.sub_agreement(team)
        if ag.empty:
            st.info("No substitutions to backtest.")
        else:
            rnd = float((3 / ag["bench_size"].clip(lower=3)).mean())
            c1, c2, c3 = st.columns(3)
            c1.metric("Substitutions tested", f"{len(ag)}")
            c2.metric("Actual incoming player in the top 3", f"{ag['on_in_top_k'].mean():.1%}")
            c3.metric("Random pick of 3 from the bench", f"{rnd:.0%}")
            st.caption("Agreement shows the heuristic resembles observed choices more than chance does. It does "
                       "not show the choices were right.")
            ui.table(ag, "substitution_backtest", key="sb_bt")
layout.footer()
