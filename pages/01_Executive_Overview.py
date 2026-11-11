"""Executive Overview: the season at a glance for the matches in scope."""
from __future__ import annotations

import streamlit as st

from src.analytics import descriptive as desc
from src.dashboard import components as ui
from src.dashboard import layout, state
from src.reporting import insight_cards

base, ws, tm = layout.start(
    "Executive Overview",
    "How did the team perform, how much of it is explained by chance quality, and what does the evidence cover?",
    eyebrow="Football Managerial Decision Analytics")
if layout.empty_scope(tm):
    st.stop()

team = st.session_state["f_team"]
p = state.params(ws)
k = desc.season_kpis(ws.bundle, team)
m = ws.tables["matches"]
xp = ws.xpts()
xpts = float(xp.loc[xp["team_name"] == team, "xpts"].sum())

ui.kpi_row([
    ("Matches", f"{k['matches']}", "Matches of the selected team that satisfy the filters."),
    ("Record (W-D-L)", f"{k['wins']}-{k['draws']}-{k['losses']}", None),
    ("Points", f"{k['points']:.0f}", f"{k['points_per_match']:.2f} per match"),
    ("Expected points", f"{xpts:.1f}", "Each shot simulated with its StatsBomb xG (5,000 runs per match). A model "
                                       "output, not an observation."),
    ("Goals for / against", f"{k['goals_for']} / {k['goals_against']}", "From the reconciled goal timeline "
                                                                         "(own goals included)."),
    ("xG for / against", f"{k['xg_for']:.1f} / {k['xg_against']:.1f}", "Sum of StatsBomb xG (source field)."),
])
ui.kpi_row([
    ("Players used", f"{k['players_used']}", "Players with at least one minute in the matches in scope."),
    ("Events analysed", f"{k['events']:,}", "Event rows of the matches in scope, both teams."),
    ("Possession proxy", f"{k['possession_proxy_pct']:.1f}%", "Team passes / both teams' passes — not timed "
                                                               "possession."),
    ("Pass completion", f"{k['pass_completion_pct']:.1f}%", None),
], per_row=4)

published = base.bundle.matches_available
analysed = len(base.tables["matches"])
st.progress(min(1.0, len(tm) / max(analysed, 1)),
            text=f"Coverage: {len(tm)} matches in scope · {analysed} analysed · {published} published by the source "
                 f"for {m['competition_name'].iloc[0]} {m['season_name'].iloc[0]} · every analysed match involves "
                 f"{base.focus}")
layout.low_sample_note(len(tm), 8)

left, right = st.columns(2)
with left:
    ui.chart("C-042" if len(tm) >= 6 else "C-040", ws, p, key="ov_form")
with right:
    ui.chart("L-262", ws, p, key="ov_xpts")

left, right = st.columns(2)
with left:
    ui.chart("C-044", ws, p, key="ov_finish")
with right:
    ui.chart("B-029", ws, p, key="ov_pareto")

left, right = st.columns([0.55, 0.45])
with left:
    ui.chart("E-110", ws, p, key="ov_shots")
with right:
    ui.section("Evidence card", "Computed from the matches in scope.")
    cards = insight_cards.build_cards(ws, team, include_slow=False)
    if cards:
        ui.evidence_card(cards[0])
        if len(cards) > 1 and not layout.presentation():
            with st.expander(f"{len(cards) - 1} more evidence cards"):
                for c in cards[1:]:
                    ui.evidence_card(c)
    else:
        st.info("No evidence card can be computed for this scope.")

if not layout.presentation():
    st.caption("Deeper modules are in the navigation: Match Centre, Player Lab, Team Tactics, the decision-support "
               "labs and the Chart Explorer, which lists every chart with its prerequisites.")
layout.footer()
