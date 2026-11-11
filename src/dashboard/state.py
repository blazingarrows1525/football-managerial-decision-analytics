"""Dashboard state: the cached workspace, the match scope implied by the global filters and the selections.

The base workspace is a shared, read-only resource (``st.cache_resource``). A filtered scope is rebuilt from
the selected matches and cached by the tuple of match ids, so every KPI and chart is computed on the filtered
data. Pages never mutate frames they receive.
"""
from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.config import default_config
from src.pipeline import subset_bundle
from src.workspace import Params, Workspace

DEFAULTS: dict[str, Any] = {
    "f_team": None, "f_venue": "All", "f_results": [], "f_opponents": [], "f_dates": None,
    "f_min_minutes": None, "f_presentation": False,
}
VENUES = ["All", "home", "away"]


@st.cache_resource(show_spinner=False)
def _base_workspace(data_mode: str) -> Workspace:
    """Build (or load from the processed cache) the full workspace once per server process."""
    return Workspace.load(default_config(data_mode=data_mode))


def base_workspace() -> Workspace:
    cfg = default_config()
    with st.spinner("Loading the dataset — the first run downloads the open data and parses it "
                    "(about a minute); later runs read the local cache."):
        return _base_workspace(cfg.data_mode)


@st.cache_resource(show_spinner=False, max_entries=8)
def _scoped_workspace(data_mode: str, match_ids: tuple) -> Workspace:
    base = _base_workspace(data_mode)
    return Workspace(subset_bundle(base.bundle, match_ids), seed=base.seed)


PERSISTED_PREFIXES = ("f_", "sel_", "w_", "explorer_")


def persist_widget_state() -> None:
    """Keep filter and selector values when the user moves to another page.

    Streamlit discards the state of a widget that is not drawn in a run, which would reset every selection on
    navigation. Re-assigning a key to itself at the start of each run turns it into ordinary session state that
    survives. Only value widgets use these prefixes (buttons cannot be assigned and never use them).
    """
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith(PERSISTED_PREFIXES):
            st.session_state[key] = st.session_state[key]


def bound(key: str) -> dict[str, Any]:
    """Keyword arguments that bind a widget to the canonical session value ``key``.

    The widget uses a shadow key (``_w`` + key) that is refreshed from the canonical value on every run, and a
    change callback copies the widget value back. Canonical keys are ordinary session state, so they survive page
    changes whatever the Streamlit version does with the state of widgets that belong to another page.
    """
    shadow = "_w" + key
    st.session_state[shadow] = st.session_state.get(key)

    def _copy() -> None:
        st.session_state[key] = st.session_state[shadow]

    return {"key": shadow, "on_change": _copy}


def init_state(ws: Workspace) -> None:
    """Fill session state with defaults once; widget keys stay stable across pages."""
    for k, v in DEFAULTS.items():
        st.session_state.setdefault(k, v)
    if st.session_state["f_team"] not in ws.teams():
        st.session_state["f_team"] = ws.focus
    if st.session_state["f_min_minutes"] is None:
        st.session_state["f_min_minutes"] = int(ws.cfg.min_minutes)


def reset_filters(ws: Workspace) -> None:
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    st.session_state["f_team"] = ws.focus
    st.session_state["f_min_minutes"] = int(ws.cfg.min_minutes)
    for k in list(st.session_state):
        if k.startswith(("sel_", "w_")):
            del st.session_state[k]


def scope_matches(ws: Workspace) -> pd.DataFrame:
    """Matches of the selected team that satisfy the global filters."""
    s = st.session_state
    tm = ws.team_matches(s["f_team"])
    if s["f_venue"] in ("home", "away"):
        tm = tm[tm["home_away"] == s["f_venue"]]
    if s["f_results"]:
        tm = tm[tm["result"].isin(s["f_results"])]
    if s["f_opponents"]:
        tm = tm[tm["opponent"].isin(s["f_opponents"])]
    d = s["f_dates"]
    if d and len(d) == 2:
        tm = tm[(tm["match_date"].dt.date >= d[0]) & (tm["match_date"].dt.date <= d[1])]
    return tm


def current_workspace() -> tuple[Workspace, Workspace, pd.DataFrame]:
    """``(base workspace, scoped workspace, matches in scope)`` for the current filters."""
    base = base_workspace()
    init_state(base)
    tm = scope_matches(base)
    all_ids = base.team_matches(st.session_state["f_team"])["match_id"].tolist()
    if len(tm) == len(all_ids) and st.session_state["f_team"] == base.focus:
        return base, base, tm
    if tm.empty:
        return base, base, tm
    ids = tuple(sorted(int(i) for i in tm["match_id"]))
    with st.spinner(f"Recomputing every table on the {len(ids)} matches in scope…"):
        scoped = _scoped_workspace(base.cfg.data_mode, ids)
    return base, scoped, tm


def params(ws: Workspace, **overrides: Any) -> Params:
    """Chart parameters from the global filters plus page-level selections."""
    p = ws.params(team=st.session_state.get("f_team") if st.session_state.get("f_team") in ws.teams() else None)
    p.min_minutes = float(st.session_state.get("f_min_minutes") or ws.cfg.min_minutes)
    for k, v in overrides.items():
        if v is not None:
            setattr(p, k, v)
    return p


def filter_summary(base: Workspace, tm: pd.DataFrame) -> str:
    """One-line description of the active scope, shown above the content of every page."""
    s = st.session_state
    total = len(base.team_matches(s["f_team"]))
    parts = [f"<b>{s['f_team']}</b>", f"{len(tm)} of {total} matches"]
    if s["f_venue"] in ("home", "away"):
        parts.append(f"venue: {s['f_venue']}")
    if s["f_results"]:
        parts.append("results: " + "/".join(s["f_results"]))
    if s["f_opponents"]:
        parts.append(f"{len(s['f_opponents'])} opponent(s)")
    if len(tm):
        parts.append(f"{tm['match_date'].min():%d %b %Y} – {tm['match_date'].max():%d %b %Y}")
    parts.append(f"min {int(s['f_min_minutes'])} minutes for per-90 comparisons")
    return " · ".join(parts)
