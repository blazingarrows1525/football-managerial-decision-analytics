"""Team Tactics: style, formations, passing structure, progression, defending and set pieces."""
from __future__ import annotations

import streamlit as st

from src.dashboard import components as ui
from src.dashboard import filters, layout, state
from src.features.team_features import formation_summary

base, ws, tm = layout.start("Team Tactics", "How does the team play — with the ball, without it and from restarts — "
                            "as far as event data can show?", eyebrow="Performance")
if layout.empty_scope(tm):
    st.stop()

team = st.session_state["f_team"]
p = state.params(ws)
layout.low_sample_note(len(tm), 8)

view = filters.view_select("View", ["Style", "Formations", "Passing network", "Progression", "Defending",
                                    "Set pieces", "Opponents"], key="w_tactics_view")

if view == "Style":
    left, right = st.columns(2)
    with left:
        ui.chart("C-052", ws, p, key="tt_radar")
    with right:
        ui.chart("C-053", ws, p, key="tt_pct")
    ui.chart("C-060", ws, p, key="tt_terr")
    left, right = st.columns(2)
    with left:
        ui.chart("C-063", ws, p, key="tt_ppda")
    with right:
        ui.chart("E-122", ws, p, key="tt_rose")
    with st.expander("Formulas used on this page"):
        st.markdown(
            "- **Possession proxy** = team passes / (team passes + opponent passes). A pass share, not timed "
            "possession.\n"
            "- **Field tilt** = team final-third touches / both teams' final-third touches.\n"
            "- **PPDA** = opponent passes with x ≤ 72 / the team's tackles, interceptions, fouls and failed "
            "challenges with x ≥ 48 (lower = more defensive actions per opponent pass).\n"
            "- **Directness** is shown through pass directions and progressive passes; width through lanes on the "
            "Progression view.")
elif view == "Formations":
    ui.chart("C-057", ws, p, key="tt_form_tl")
    left, right = st.columns(2)
    with left:
        ui.chart("G-153", ws, p, key="tt_form_freq")
    with right:
        ui.chart("G-155", ws, p, key="tt_form_trans")
    ui.table(formation_summary(ws.bundle.team_stats, team), "formation_summary", key="tt_form_tbl")
    layout.note("A formation here is the label recorded on the Starting XI or Tactical Shift event. It is a nominal "
                "description, not the team's shape in and out of possession, and differences in results between "
                "formations are confounded by opponent and availability.")
elif view == "Passing network":
    mid = filters.match_select(ws, tm, key="w_net_match")
    pm = state.params(ws, match_id=mid)
    style = filters.view_select("Network", ["By volume", "By betweenness", "By role", "Direction", "Season aggregate"],
                                key="w_net_style")
    ids = {"By volume": "F-137", "By betweenness": "F-140", "By role": "F-142", "Direction": "F-143",
           "Season aggregate": "F-138"}
    ui.chart(ids[style], ws, pm, key="tt_net")
    left, right = st.columns(2)
    with left:
        ui.chart("F-139", ws, p, key="tt_cent")
    with right:
        ui.chart("F-141", ws, p, key="tt_cent_sc")
    with st.expander("More network views (computed on request)"):
        extra = st.selectbox("View", ["Passer → recipient matrix", "Passes between roles",
                                      "Remove-one-player simulation", "Network by score state",
                                      "Before / after the first substitution"], key="w_net_extra")
        ids2 = {"Passer → recipient matrix": "F-148", "Passes between roles": "F-147",
                "Remove-one-player simulation": "F-146", "Network by score state": "F-144",
                "Before / after the first substitution": "F-145"}
        ui.chart(ids2[extra], ws, pm, key="tt_net_extra")
elif view == "Progression":
    left, right = st.columns(2)
    with left:
        ui.chart("E-133", ws, p, key="tt_lanes")
    with right:
        ui.chart("E-135", ws, p, key="tt_flow")
    ui.chart("E-134", ws, p, key="tt_sankey")
    left, right = st.columns(2)
    with left:
        ui.chart("L-263", ws, p, key="tt_xt")
    with right:
        ui.chart("L-264", ws, p, key="tt_xt_players")
elif view == "Defending":
    left, right = st.columns(2)
    with left:
        ui.chart("E-118", ws, p, key="tt_def_zone")
    with right:
        ui.chart("E-117", ws, p, key="tt_press_zone")
    ui.chart("C-062", ws, p, key="tt_def_match")
elif view == "Set pieces":
    ui.chart("C-059", ws, p, key="tt_origin")
    left, right = st.columns(2)
    with left:
        ui.chart("L-274", ws, p, key="tt_goals")
    with right:
        mid = filters.match_select(ws, tm, key="w_sp_match")
        ui.chart("E-123", ws, state.params(ws, match_id=mid), key="tt_cross")
else:
    layout.note("Opponents appear twice (home and away) in this dataset, always against the focus team. These views "
                "describe those meetings; they are not a ranking of the opponents' seasons.")
    ui.chart("C-055", ws, p, key="tt_opp")
    left, right = st.columns(2)
    with left:
        ui.chart("C-065", ws, p, key="tt_quad")
    with right:
        ui.chart("L-252", ws, p, key="tt_bubbles")
layout.footer()
