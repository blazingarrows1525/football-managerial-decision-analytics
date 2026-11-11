"""Managerial Intelligence: observable decisions — formations, rotation, substitutions — with their uncertainty."""
from __future__ import annotations

import streamlit as st

from src.dashboard import components as ui
from src.dashboard import filters, layout, state
from src.reporting import insight_cards

base, ws, tm = layout.start("Managerial Intelligence", "What do the recorded decisions show about selection, "
                            "formation and substitution habits — and how much of that is certain?",
                            eyebrow="Decision support")
if layout.empty_scope(tm):
    st.stop()

team = st.session_state["f_team"]
p = state.params(ws)
mgr = ws.focus_manager(team)
layout.note("This page describes <b>observable decisions</b> recorded in the data. It does not measure a manager's "
            "ability, intentions or anything said in the dressing room, and it cannot separate the manager from "
            "the squad he has.")

prof = ws.manager_profiles()
row = prof[(prof["manager"] == mgr) & (prof["team"] == team)] if mgr and len(prof) else prof.iloc[:0]
if mgr is None or row.empty:
    st.warning("No manager identity is recorded for this team in the matches in scope.")
else:
    r = row.iloc[0]
    ui.kpi_row([
        ("Manager (as recorded)", mgr, f"Source: {ws.bundle.manager_source}"),
        ("Matches", f"{int(r['matches'])}", r["sample_status"]),
        ("Formations used", f"{int(r['formations_used'])}", f"most used: {r['most_used_formation']} "
                                                             f"({r['most_used_share_pct']:.0f}%)"),
        ("XI changes per match", f"{r['mean_lineup_changes']:.2f}", "Between consecutive analysed matches."),
        ("Substitutions per match", f"{r['subs_per_match']:.2f}", None),
        ("Median first change", f"{r['median_first_sub_minute']:.0f}'", None),
    ])
    layout.low_sample_note(int(r["matches"]), ws.cfg.min_manager_matches, "matches for this manager")

view = filters.view_select("View", ["Formations", "Rotation", "Substitutions", "After conceding",
                                    "Comparison and uncertainty", "Decision audit trail", "Evidence cards"],
                           key="w_mgr_view")

if view == "Formations":
    ui.chart("I-186", ws, p, key="mg_form")
    left, right = st.columns(2)
    with left:
        ui.chart("I-197", ws, p, key="mg_changes")
    with right:
        ui.chart("G-155", ws, p, key="mg_trans")
    ui.chart("I-196", ws, p, key="mg_who")
elif view == "Rotation":
    ui.chart("I-187", ws, p, key="mg_rot")
    left, right = st.columns(2)
    with left:
        ui.chart("G-163", ws, p, key="mg_sim")
    with right:
        ui.chart("G-164", ws, p, key="mg_costart")
    st.caption("Rotation is measured between consecutive analysed league matches. Cup and European fixtures played "
               "in between are not in the data, so true rotation is understated.")
elif view == "Substitutions":
    left, right = st.columns(2)
    with left:
        ui.chart("I-188", ws, p, key="mg_timing")
    with right:
        ui.chart("I-190", ws, p, key="mg_roles")
    ui.chart("I-189", ws, p, key="mg_parcats")
    ui.chart("H-183", ws, p, key="mg_profile")
elif view == "After conceding":
    ui.chart("I-192", ws, p, key="mg_resp")
    resp = ws.response()
    ui.table(resp[resp["team"] == team], "response_after_conceding", key="mg_resp_tbl")
elif view == "Comparison and uncertainty":
    layout.note("Every other manager in this dataset has two matches, all against the focus team. "
                "Comparisons are a description of this fixture list, not a peer benchmark; intervals and shrinkage "
                "show how little the small samples support.")
    ui.chart("I-193", ws, p, key="mg_pool")
    ui.chart("I-195", ws, p, key="mg_unc")
    with st.expander("Manager profile table (all managers in scope)"):
        ui.table(prof, "manager_profiles", key="mg_prof_tbl")
elif view == "Decision audit trail":
    mid = filters.match_select(ws, tm, key="w_mgr_match")
    ui.chart("I-198", ws, state.params(ws, match_id=mid), key="mg_audit", export=False)
    ui.chart("H-177", ws, state.params(ws, match_id=mid), key="mg_audit_tl")
else:
    st.caption("Each card states the finding, the metric behind it, its scope, the supporting chart, why it may "
               "matter and what it cannot tell us. The last two cards need the clustering and model results and "
               "take a few seconds.")
    slow = st.toggle("Include the model-based cards", key="w_mgr_slow")
    for c in insight_cards.build_cards(ws, team, include_slow=slow):
        ui.evidence_card(c)
layout.footer()
