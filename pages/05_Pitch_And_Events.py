"""Pitch & Event Explorer: any event type, for a team, its opponents or one player, on the pitch."""
from __future__ import annotations

import streamlit as st

from src.dashboard import components as ui
from src.dashboard import filters, layout, state
from src.features.event_features import EVENT_KINDS, select_events
from src.visualization import pitch, spatial, static_pitch
from src.visualization.availability import package_installed
from src.visualization.theme import finalize
from src.visualization import registry

base, ws, tm = layout.start("Pitch & Event Explorer", "Where on the pitch do events of a chosen type happen, for "
                            "which side, and in which part of the match?", eyebrow="Performance")
if layout.empty_scope(tm):
    st.stop()

team = st.session_state["f_team"]
tid = ws.team_id(team)

with st.expander("Coordinate convention", expanded=False):
    st.markdown(
        "StatsBomb coordinates: the pitch is **120 × 80** units (roughly yards), the origin is the top-left corner "
        "and **each team's events are recorded attacking left to right in both halves**. No half-time flip is "
        "applied or needed. When a chart shows the opponent, it is in the opponent's own attacking frame unless "
        "the chart says it is mirrored. Lanes are named as seen attacking left to right (y = 0 is the left "
        "touchline). The transform is covered by `tests/test_features.py`.")

c1, c2, c3, c4 = st.columns(4)
side = c1.selectbox("Side", [team, "Opponents", "One player"], key="w_px_side")
with c2:
    kind = filters.kind_select("w_px_kind")
scope = c3.selectbox("Matches", ["All matches in scope", "One match"], key="w_px_scope")
period = c4.selectbox("Half", ["Both halves", "First half", "Second half"], key="w_px_period")
c5, c6, c7 = st.columns([0.3, 0.3, 0.4])
outcome = c5.selectbox("Outcome", ["All", "successful", "unsuccessful"], key="w_px_outcome")
mins = c6.slider("Minute range", 0, 100, (0, 100), key="w_px_minutes")
mid = None
pid = None
with c7:
    if scope == "One match":
        mid = filters.match_select(ws, tm, key="w_px_match")
    if side == "One player":
        pid = filters.player_select(ws, key="w_px_player")

per = {"Both halves": None, "First half": 1, "Second half": 2}[period]
ids = [mid] if mid is not None else tm["match_id"].tolist()
ev = select_events(ws.flags, kind, team_id=tid if side == team else None, player_id=pid, match_ids=ids, period=per,
                   minute_range=mins, outcome=None if outcome == "All" else outcome)
if side == "Opponents":
    ev = ev[ev["team_id"] != tid]
who = team if side == team else ("Opponents" if side == "Opponents" else ws.player_name(pid))
where = ws.match_label(mid) if mid is not None else f"{len(ids)} matches"
has_end = EVENT_KINDS[kind][1]
title = f"{who}: {kind.lower()} — {where}"
st.caption(f"**{len(ev):,} events** selected · {EVENT_KINDS[kind][0]} · {period.lower()} · minutes {mins[0]}–"
           f"{mins[1]} · outcome: {outcome.lower()}")

styles = ["Points", "Zone heatmap", "Zone grid 3×3", "Zone grid 5×5", "Density contours", "Event footprint (hull)",
          "By half"]
if has_end:
    styles += ["Arrows", "End-location density"]
if package_installed("mplsoccer"):
    styles += ["Hexbin (static)"] + (["Pass flow (static)"] if has_end else [])
style = filters.view_select("Map style", styles, key="w_px_style")

if ev.empty:
    st.info("No event matches this selection. Change the event type, side, half, outcome or minute range.")
else:
    if style == "Points":
        fig = spatial.event_points(ev, title, "outcome" if ev["outcome"].notna().any() else None)
    elif style == "Zone heatmap":
        fig = pitch.action_heatmap(ev, title)
    elif style == "Zone grid 3×3":
        fig = spatial.zone_grid(ev, title, 3, 3)
    elif style == "Zone grid 5×5":
        fig = spatial.zone_grid(ev, title, 5, 5)
    elif style == "Density contours":
        fig = spatial.density_contours(ev, title)
    elif style == "Event footprint (hull)":
        fig = spatial.convex_hull(ev, title)
    elif style == "By half":
        fig = spatial.period_split(ev, title)
    elif style == "Arrows":
        fig = spatial.arrow_map(ev, title)
    elif style == "End-location density":
        fig = spatial.density_contours(ev, title, end=True)
    elif style == "Hexbin (static)":
        fig = static_pitch.hexbin_map(ev, title)
    else:
        fig = static_pitch.pass_flow(ev, title)
    ui.show(finalize(fig, registry.scope_text(ws), synthetic=ws.synthetic, attribution=registry.attribution_text(ws)), key="px_map")
    st.caption("Maps with more than 4,000 points or 500 arrows draw a seeded random sample and say so in the "
               "subtitle. Density and heatmap shading between events is aggregation, not extra data. The event "
               "footprint is a hull of recorded on-ball events — not the area a player or team occupied.")
    with st.expander(f"Selected events as a table ({len(ev):,} rows)"):
        cols = ["match_id", "period", "minute", "second", "team_name", "player_name", "type", "outcome", "x", "y",
                "end_x", "end_y", "shot_xg", "play_pattern"]
        ui.table(ev[[c for c in cols if c in ev.columns]].head(5000), "selected_events", key="px_tbl", height=360)
        if len(ev) > 5000:
            st.caption("The table and its download are limited to the first 5,000 rows.")

st.divider()
extra = filters.view_select("More", ["Team vs opponent territory", "Possession sequence", "Expected Threat surface",
                                     "360 freeze frame", "Not available with event data"], key="w_px_extra")
pm = state.params(ws, match_id=mid if mid is not None else ws.default_match(team))
if extra == "Team vs opponent territory":
    ui.chart("E-131", ws, pm, key="px_pair")
elif extra == "Possession sequence":
    ui.chart("E-130", ws, pm, key="px_seq")
elif extra == "Expected Threat surface":
    ui.chart("L-263", ws, pm, key="px_xt")
elif extra == "360 freeze frame":
    st.markdown("StatsBomb 360 freeze frames are published for these matches as separate files of about 8 MB each. "
                "They are optional and are downloaded for one match only when requested.")
    target = pm.match_id
    if ws.frames_360(target) is None:
        if st.button(f"Download the 360 file for {ws.match_label(target)}", key="px_360_btn"):
            with st.spinner("Downloading from the source repository…"):
                ok = base.load_360(target)
            st.success("360 file cached.") if ok else st.error("The 360 file could not be downloaded (network "
                                                              "unavailable or not published for this match).")
    ui.chart("E-129", ws, pm, key="px_360")
else:
    for cid in ("E-126", "E-127", "E-128"):
        s = registry.get(cid)
        st.markdown(f"**{s.chart_id} · {s.name}** — not implemented. {s.unavailable_reason}")
layout.footer()
