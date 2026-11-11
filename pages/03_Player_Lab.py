"""Player Lab: one player's evidence — profile, like-for-like comparison, distributions, consistency and maps."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analytics import player_comparison
from src.dashboard import components as ui
from src.dashboard import filters, layout, state
from src.features.player_features import radar_metrics
from src.reporting import exports

base, ws, tm = layout.start("Player Lab", "What does the event evidence say about one player, relative to players "
                            "of the same role, and how certain is it?", eyebrow="Performance")
if layout.empty_scope(tm):
    st.stop()

team = st.session_state["f_team"]
sq = ws.squad(team)
if sq.empty:
    st.warning("No player of this team has minutes in the matches in scope.")
    layout.footer()
    st.stop()

c1, c2 = st.columns([0.5, 0.5])
with c1:
    pid = filters.player_select(ws)
r = sq[sq["player_id"] == pid].iloc[0]
threshold = float(st.session_state["f_min_minutes"])
p = state.params(ws, player_id=pid)

ui.kpi_row([
    ("Minutes", f"{r['minutes_played']:.0f}", "Reconstructed from events, stoppage time included."),
    ("Appearances / starts", f"{int(r['appearances'])} / {int(r['starts'])}", None),
    ("Primary position", str(r["primary_position"]), "Position with the most minutes in the matches in scope."),
    ("Goals / xG", f"{int(r['goals'])} / {r['xg']:.1f}", "Goals and StatsBomb xG."),
    ("Assists / xA", f"{int(r['assists'])} / {r['xa']:.1f}", "xA = xG of the shots the player's passes assisted."),
    ("Benchmark group", f"{r.get('benchmark_group', '—')}", f"{r.get('benchmark_n', 0):.0f} players in the group "
                                                             f"used for percentiles."),
])
if r["minutes_played"] < threshold:
    layout.note(f"<b>Below the minutes threshold.</b> {r['player_name']} has {r['minutes_played']:.0f} minutes "
                f"(threshold {threshold:.0f}). Per-90 values and percentiles are not shown as reliable evidence; "
                f"lower the threshold in the sidebar to inspect them.")
if bool(r.get("small_benchmark_warning", False)) is True:
    layout.note(f"<b>Small benchmark group.</b> Only {r.get('benchmark_n', 0):.0f} eligible players in "
                f"{r.get('benchmark_group')}; percentiles within such a small group are coarse.")

view = filters.view_select("View", ["Profile", "Compare", "Distributions", "Consistency", "Maps", "Similar players",
                                    "Exposure"], key="w_player_view")

if view == "Profile":
    left, right = st.columns(2)
    with left:
        ui.chart("D-070", ws, p, key="pl_radar")
    with right:
        ui.chart("D-069", ws, p, key="pl_pct")
    ui.chart("D-108", ws, p, key="pl_card", export=False)
    card = pd.DataFrame([r[["player_name", "team_name", "primary_position", "primary_role", "minutes_played",
                            "appearances", "starts", "goals", "xg", "assists", "xa"]
                           + [m for m in radar_metrics(r["primary_role"], ws.cfg) if m in r.index]]])
    st.download_button("Download this player's season row (CSV)", exports.table_csv(card),
                       file_name=f"{exports.slug(r['player_name'])}_season.csv", mime="text/csv", key="pl_csv",
                       on_click="ignore", icon=":material/download:")
    st.caption("A PDF player report is not offered: no PDF backend is installed or tested in this project.")
elif view == "Compare":
    with c2:
        cid = filters.player_select(ws, key="sel_compare", label_text="Compare with", exclude=pid)
    if cid is None:
        st.info("No second player available for comparison.")
    else:
        other = sq[sq["player_id"] == cid].iloc[0]
        if other["primary_role"] != r["primary_role"]:
            layout.note(f"<b>Different roles.</b> {r['player_name']} ({r['primary_role']}) and "
                        f"{other['player_name']} ({other['primary_role']}) are benchmarked against different role "
                        f"groups; percentiles are not like-for-like.")
        pc = state.params(ws, player_id=pid, compare_id=cid)
        ui.chart("D-071", ws, pc, key="pl_cmp")
        metrics = radar_metrics(r["primary_role"], ws.cfg)
        tbl = player_comparison.comparison_table(ws.bundle.season_pct, [pid, cid], metrics)
        if len(tbl):
            wide = tbl.pivot_table(index="metric", columns="player", values=["value", "percentile"]).round(2)
            wide.columns = [f"{b} · {a}" for a, b in wide.columns]
            ui.table(wide.reset_index(), "player_comparison", key="pl_cmp_tbl")
elif view == "Distributions":
    a, b, c = st.columns(3)
    with a:
        metric = filters.metric_select("w_dist_metric")
    with b:
        group = filters.group_select("w_dist_group")
    with c:
        kind = st.selectbox("Chart", ["Box with points", "Violin", "Strip", "ECDF", "KDE", "Raincloud", "Beeswarm"],
                            key="w_dist_kind")
    ids = {"Box with points": "B-020", "Violin": "B-021", "Strip": "B-023", "ECDF": "B-019", "KDE": "B-018",
           "Raincloud": "B-022", "Beeswarm": "B-025"}
    pd_ = state.params(ws, player_id=pid, metric=metric, group=group)
    n = len(ws.eligible(threshold))
    st.caption(f"{n} players in the dataset have at least {threshold:.0f} minutes in the matches in scope. "
               f"{r['player_name']}: {r.get(metric, float('nan')):.2f}"
               + (f" (percentile {r.get(metric + '_pct'):.0f} in {r.get('benchmark_group')})"
                  if pd.notna(r.get(metric + "_pct", float("nan"))) else ""))
    ui.chart(ids[kind], ws, pd_, key="pl_dist")
elif view == "Consistency":
    ui.chart("D-080", ws, p, key="pl_form")
    left, right = st.columns(2)
    with left:
        ui.chart("D-102", ws, p, key="pl_quad")
    with right:
        ui.chart("D-079", ws, state.params(ws, player_id=pid, metric="xg_p90"), key="pl_boot")
    st.caption("The coefficient of variation is reported only where the mean is clearly above zero; bootstrap "
               "intervals resample matches, not events.")
elif view == "Maps":
    a, b = st.columns(2)
    with a:
        kind = filters.kind_select("w_map_kind")
    with b:
        style = st.selectbox("Map", ["Zone heatmap", "Density contours", "Shot map", "Pass map", "Progressive passes",
                                     "Carries", "Defensive actions", "Event footprint (one match)"], key="w_map_style")
    pm = state.params(ws, player_id=pid, kind=kind)
    ids = {"Zone heatmap": "D-094", "Density contours": "D-096", "Shot map": "D-084", "Pass map": "D-087",
           "Progressive passes": "D-088", "Carries": "D-089", "Defensive actions": "D-091",
           "Event footprint (one match)": "D-097"}
    if style == "Event footprint (one match)":
        pm.match_id = filters.match_select(ws, tm, key="w_map_match")
    ui.chart(ids[style], ws, pm, key="pl_map")
    st.caption("All maps use StatsBomb coordinates (120 × 80, the team always attacks left to right). The event-type "
               "selector applies to the zone heatmap; the other maps have a fixed event type.")
elif view == "Similar players":
    ui.chart("D-101", ws, p, key="pl_sim")
    sim = player_comparison.similar_players(ws.bundle.season_pct, pid, min_minutes=threshold)
    ui.table(sim, "similar_players", key="pl_sim_tbl")
else:
    ui.chart("D-107", ws, p, key="pl_exposure")
    st.caption("Career and age trends are not shown: the source has no date of birth and only the analysed season.")
layout.footer()
