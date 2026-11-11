"""Match Centre: one match in detail — timeline, shots and xG, team comparison, events and time on pitch."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.dashboard import components as ui
from src.dashboard import filters, layout, state
from src.features.event_features import EVENT_KINDS, select_events

base, ws, tm = layout.start("Match Centre", "What happened in one match, in order, and how do the two sides compare?",
                            eyebrow="Performance")
if layout.empty_scope(tm):
    st.stop()

team = st.session_state["f_team"]
mid = filters.match_select(ws, tm)
p = state.params(ws, match_id=mid)
row = tm[tm["match_id"] == mid].iloc[0]
meta = ws.tables["matches"].set_index("match_id").loc[mid]
mgr = ws.tables["managers"]
mgr = mgr[mgr["match_id"] == mid].set_index("team_name")["manager_name"] if len(mgr) else pd.Series(dtype=object)

c1, c2, c3 = st.columns([0.38, 0.24, 0.38], vertical_alignment="center")
c1.markdown(f"### {meta['home_team']}")
c1.caption(f"Manager: {mgr.get(meta['home_team'], 'not recorded')}")
c2.markdown(f"<h1 style='text-align:center;margin:0'>{int(meta['home_score'])} – {int(meta['away_score'])}</h1>",
            unsafe_allow_html=True)
c3.markdown(f"<h3 style='text-align:right'>{meta['away_team']}</h3>", unsafe_allow_html=True)
c3.markdown(f"<div style='text-align:right;color:#6b7280;font-size:0.85rem'>Manager: "
            f"{mgr.get(meta['away_team'], 'not recorded')}</div>", unsafe_allow_html=True)
bits = [f"{meta['match_date']:%A %d %B %Y}", f"{meta['competition_name']} {meta['season_name']}"]
for label_, col in (("matchweek", "match_week"), ("stadium", "stadium"), ("referee", "referee")):
    if col in meta.index and pd.notna(meta[col]):
        bits.append(f"{label_}: {meta[col]}")
st.caption(" · ".join(bits) + " · metadata as published in the source matches file")

view = filters.view_select("View", ["Timeline", "Shots & xG", "Team comparison", "Events", "Time on pitch"],
                           key="w_match_view")

if view == "Timeline":
    ui.chart("C-049", ws, p, key="mc_tl")
    ui.chart("C-051", ws, p, key="mc_state")
    ui.chart("H-177", ws, p, key="mc_subs")
elif view == "Shots & xG":
    left, right = st.columns(2)
    with left:
        ui.chart("E-110", ws, p, key="mc_shots")
    with right:
        ui.chart("L-248", ws, p, key="mc_cumxg")
    ui.chart("L-249", ws, p, key="mc_intervals")
    layout.note("The interval chart shows xG per 5-minute bucket and the share of final-third touches. It is a "
                "description of when chances occurred, <b>not</b> a validated momentum measure.")
elif view == "Team comparison":
    ts = ws.bundle.team_stats
    both = ts[ts["match_id"] == mid].set_index("team_name")
    rows = [("Goals", "goals_for", "{:.0f}"), ("xG (StatsBomb)", "xg", "{:.2f}"), ("Shots", "shots", "{:.0f}"),
            ("Shots on target", "shots_on_target", "{:.0f}"), ("Passes attempted", "passes", "{:.0f}"),
            ("Pass completion %", "pass_completion_pct", "{:.1f}"),
            ("Possession proxy % (pass share)", "possession_proxy_pct", "{:.1f}"),
            ("Field tilt % (final-third touch share)", "field_tilt_pct", "{:.1f}"),
            ("Progressive passes", "progressive_passes", "{:.0f}"), ("Pressures", "pressures", "{:.0f}"),
            ("PPDA (lower = more intense)", "ppda", "{:.1f}"), ("Fouls committed", "fouls_committed", "{:.0f}"),
            ("Starting formation", "starting_formation", "{}")]
    comp = pd.DataFrame([{"metric": name, **{t: (fmt.format(both.loc[t, col]) if pd.notna(both.loc[t, col]) else "—")
                                             for t in both.index}} for name, col, fmt in rows if col in both])
    ui.table(comp, f"team_comparison_{mid}", key="mc_comp")
    st.caption("PPDA = opponent passes in their own 60% of the pitch / the team's tackles, interceptions, fouls and "
               "failed challenges there. Possession proxy is a pass share, not timed possession.")
    ui.chart("E-131", ws, p, key="mc_territory")
elif view == "Events":
    fl = ws.flags[ws.flags["match_id"] == mid]
    c1, c2, c3, c4 = st.columns(4)
    side = c1.selectbox("Team", ["Both teams"] + sorted(fl["team_name"].dropna().unique()), key="w_ev_team")
    kind = c2.selectbox("Event type", ["All events"] + list(EVENT_KINDS), key="w_ev_kind")
    period = c3.selectbox("Half", ["Both halves", 1, 2], key="w_ev_period")
    mins = c4.slider("Minute range", 0, int(fl["minute"].max()), (0, int(fl["minute"].max())), key="w_ev_min")
    ev = fl if kind == "All events" else select_events(fl, kind)
    if side != "Both teams":
        ev = ev[ev["team_name"] == side]
    if period != "Both halves":
        ev = ev[ev["period"] == period]
    ev = ev[ev["minute"].between(*mins)]
    cols = ["period", "minute", "second", "team_name", "player_name", "type", "outcome", "play_pattern", "x", "y",
            "end_x", "end_y", "shot_xg", "pass_recipient_name", "under_pressure"]
    st.caption(f"{len(ev):,} of {len(fl):,} events of this match match the filters"
               + (f" · {kind}: {EVENT_KINDS[kind][0]}" if kind != "All events" else ""))
    ui.table(ev[[c for c in cols if c in ev.columns]].sort_values(["period", "minute", "second"]),
             f"events_{mid}", key="mc_events", height=460)
else:
    ui.chart("L-250", ws, p, key="mc_gantt")
    app = ws.tables["appearances"]
    a = app[(app["match_id"] == mid) & (app["team_name"] == team)]
    ui.table(a[["player_name", "squad_status", "match_position", "minutes_played", "sub_on_minute", "sub_off_minute",
                "end_reason"]].sort_values(["squad_status", "minutes_played"], ascending=[True, False]),
             f"appearances_{mid}", key="mc_app")
    st.caption("Minutes are reconstructed from Starting XI, Substitution and sending-off events on the period-aware "
               "clock; stoppage time is included.")
layout.footer()
