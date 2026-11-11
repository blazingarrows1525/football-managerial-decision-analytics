"""Global sidebar filters and page-level selectors with stable widget keys."""
from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard import state
from src.features.event_features import EVENT_KINDS
from src.workspace import Workspace

PLAYER_METRICS = ["xg_p90", "npxg_p90", "xa_p90", "goals_p90", "shots_p90", "key_passes_p90",
                  "progressive_passes_p90", "progressive_carries_p90", "final_third_passes_p90",
                  "dribbles_completed_p90", "box_touches_p90", "pressures_p90", "tackles_won_p90",
                  "interceptions_p90", "clearances_p90", "aerials_won_p90", "ball_recoveries_p90",
                  "pass_completion_pct"]
TEAM_METRICS = ["xg_diff", "xg", "xg_against", "shots", "shots_against", "goal_diff", "possession_proxy_pct",
                "field_tilt_pct", "pass_completion_pct", "progressive_passes", "pressures", "ppda"]
GROUPS = {"role_family": "Role family", "primary_role": "Primary role", "team_name": "Team"}


def sidebar(base: Workspace) -> None:
    """Global filters. Every control changes the match scope (and therefore every number on the page)."""
    state.init_state(base)
    with st.sidebar:
        st.markdown("#### Global filters")
        teams = base.teams()
        st.selectbox("Team", teams, key="f_team",
                     help="Every analysed match involves the focus team; other teams have two matches.")
        tm_all = base.team_matches(st.session_state["f_team"])
        st.segmented_control("Venue", state.VENUES, key="f_venue")
        st.multiselect("Result", ["W", "D", "L"], key="f_results", placeholder="All results")
        st.multiselect("Opponent", sorted(tm_all["opponent"].unique()), key="f_opponents",
                       placeholder="All opponents")
        if len(tm_all):
            lo, hi = tm_all["match_date"].min().date(), tm_all["match_date"].max().date()
            if not st.session_state.get("f_dates"):
                st.session_state["f_dates"] = (lo, hi)
            st.date_input("Match dates", key="f_dates", min_value=lo, max_value=hi)
        st.slider("Minimum minutes (per-90 and percentile comparisons)", 0, 1500, step=30, key="f_min_minutes",
                  help="Players below the threshold are excluded from rankings and distributions.")
        tm = state.scope_matches(base)
        st.caption(f"{len(tm)} of {len(tm_all)} matches in scope")
        st.button("Reset filters", on_click=state.reset_filters, args=(base,), width="stretch")
        st.divider()
        st.caption("Historical StatsBomb Open Data. Static analysis — nothing here is live or real-time.")


def match_select(ws: Workspace, tm: pd.DataFrame, key: str = "sel_match", label_text: str = "Match") -> Any:
    """Match selector limited to the matches in scope (most recent first)."""
    if tm.empty:
        return None
    d = tm.sort_values("match_date", ascending=False)
    opts = d["match_id"].tolist()
    labels = {r.match_id: f"{r.match_date:%d %b %Y} · {'vs' if r.home_away == 'home' else 'at'} {r.opponent} · "
                          f"{int(r.goals_for)}-{int(r.goals_against)} ({r.result})" for r in d.itertuples()}
    if st.session_state.get(key) not in opts:
        default = ws.default_match(st.session_state["f_team"])
        st.session_state[key] = default if default in opts else opts[0]
    return st.selectbox(label_text, opts, format_func=lambda m: labels[m], key=key)


def player_select(ws: Workspace, key: str = "sel_player", label_text: str = "Player", exclude: Any = None,
                  outfield_only: bool = False) -> Any:
    """Player selector for the team in scope, ordered by minutes."""
    sq = ws.squad(st.session_state["f_team"])
    if outfield_only:
        sq = sq[sq["primary_role"] != "GK"]
    if exclude is not None:
        sq = sq[sq["player_id"] != exclude]
    if sq.empty:
        return None
    opts = sq["player_id"].tolist()
    labels = {r.player_id: f"{r.player_name} · {r.primary_role or '?'} · {r.minutes_played:.0f} min"
              for r in sq.itertuples()}
    if st.session_state.get(key) not in opts:
        st.session_state[key] = opts[0]
    return st.selectbox(label_text, opts, format_func=lambda p: labels[p], key=key)


def metric_select(key: str = "sel_metric", label_text: str = "Metric", options: list[str] | None = None,
                  default: str | None = None) -> str:
    options = options or PLAYER_METRICS
    if st.session_state.get(key) not in options:
        st.session_state[key] = default if default in options else options[0]
    return st.selectbox(label_text, options, format_func=_nice, key=key)


def _nice(m: str) -> str:
    from src.visualization.distribution import nice

    return nice(m)


def group_select(key: str = "sel_group") -> str:
    opts = ["role_family", "primary_role"]
    if st.session_state.get(key) not in opts:
        st.session_state[key] = "role_family"
    return st.selectbox("Group by", opts, format_func=lambda g: GROUPS[g], key=key)


def kind_select(key: str = "sel_kind", default: str = "Touches") -> str:
    opts = list(EVENT_KINDS)
    if st.session_state.get(key) not in opts:
        st.session_state[key] = default
    return st.selectbox("Event type", opts, key=key, help="Hover the chart subtitle for the definition.")


def formation_select(ws: Workspace, key: str = "sel_formation", default: str | None = None) -> str:
    opts = list(ws.cfg.formation_templates)
    if st.session_state.get(key) not in opts:
        st.session_state[key] = default if default in opts else opts[0]
    return st.selectbox("Formation template", opts, key=key)


def view_select(label_text: str, options: list[str], key: str) -> str:
    """Single-choice view switch. Only the chosen view is rendered, so heavy charts are built on demand."""
    if st.session_state.get(key) not in options:
        st.session_state[key] = options[0]
    choice = st.segmented_control(label_text, options, key=key, label_visibility="collapsed")
    return choice or options[0]
