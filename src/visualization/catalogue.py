"""Chart catalogue: every chart concept of the project with its renderer, prerequisites and caveats.

IDs follow the numbering of the V3 chart atlas (families A-K, 001-244); family L holds additional project
charts and the composite dashboards. Importing this module registers every entry. Entries without a renderer
state why (unsupported data modality, no legitimate target, not justified at this sample size).
"""
from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd

from src.analytics import descriptive as desc
from src.analytics import player_comparison, statistical_tests, substitution_analysis, uncertainty
from src.analytics import lineup_optimizer as xi
from src.data.validators import dataset_scale, event_type_coverage
from src.features import network_features as nf
from src.features import substitution_features as sf
from src.features.event_features import select_events
from src.features.player_features import (label, player_profile, radar_metrics, rolling_form_series,
                                          strengths_weaknesses)
from src.features.team_features import cumulative_xg, formation_summary, match_timeline_events
from src.visualization import (audit, comparison, dashboards, distribution, inference, lineup, manager, match,
                               model, passing, pitch, player, scouting, spatial, static_pitch, statistical,
                               substitution, tactics, team)
from src.visualization import network as network_core
from src.visualization.registry import ChartSpec, register
from src.visualization.theme import _empty, table_figure
from src.workspace import EDA_METRICS, Params, Workspace

EV = {"events": ("event_id", "type", "x", "y")}
EVE = {"events": ("event_id", "type", "x", "y", "end_x", "end_y")}
SHOT = {"events": ("x", "y", "shot_xg", "outcome")}
TS = {"team_stats": ("match_id", "team_name", "xg", "xg_against", "result")}
SP = {"season_pct": ("player_id", "player_name", "minutes_played", "primary_role")}
PMS = {"pms": ("match_id", "player_id", "minutes_played")}
APP = {"appearances": ("match_id", "player_id", "is_starter", "minutes_played")}
SUBS = {"subs": ("match_id", "team_name", "minute", "game_state")}
MGR = {"managers": ("match_id", "team_id", "manager_name")}
FORM = {"formations": ("match_id", "team_id", "formation")}
SPELLS = {"spells": ("match_id", "player_id", "start", "end")}
GOALS = {"goals": ("match_id", "scoring_team_id", "elapsed_min")}
PASS = {"events": ("x", "y", "end_x", "end_y", "pass_recipient_id", "outcome")}


def add(chart_id: str, name: str, question: str, renderer: Callable[[Workspace, Params], Any] | None = None, *,
        req: dict | None = None, params: tuple[str, ...] = (), note: str = "", caveat: str = "",
        cost: str = "low", lib: str = "plotly", modality: str = "event", reason: str = "", min_matches: int = 1,
        min_players: int = 0, package: str | None = None, legacy: str = "") -> None:
    req = req or {}
    register(ChartSpec(chart_id=chart_id, name=name, category=chart_id[0], research_question=question,
                       required_tables=tuple(req), required_columns={k: tuple(v) for k, v in req.items()},
                       minimum_matches=min_matches, minimum_players=min_players, data_modality=modality,
                       renderer=renderer, library=lib, unavailable_reason=reason, methodology_note=note,
                       caveat=caveat, estimated_cost=cost, params=params, requires_package=package,
                       legacy_artifact=legacy))


# ----------------------------------------------------------------------------- selection helpers
def _t(ws: Workspace, p: Params) -> str:
    return p.team or ws.focus


def _tid(ws: Workspace, p: Params) -> Any:
    return ws.team_id(_t(ws, p))


def _mid(ws: Workspace, p: Params) -> Any:
    return p.match_id if p.match_id is not None else ws.default_match(_t(ws, p))


def _pid(ws: Workspace, p: Params) -> Any:
    return p.player_id if p.player_id is not None else ws.default_player(_t(ws, p))


def _mm(ws: Workspace, p: Params) -> float:
    return ws.cfg.min_minutes if p.min_minutes is None else p.min_minutes


def _el(ws: Workspace, p: Params) -> pd.DataFrame:
    return ws.eligible(_mm(ws, p))


def _pname(ws: Workspace, p: Params) -> str:
    return ws.player_name(_pid(ws, p))


def _ml(ws: Workspace, p: Params) -> str:
    return ws.match_label(_mid(ws, p))


def _team_ev(ws: Workspace, p: Params, kind: str, match: bool = False) -> pd.DataFrame:
    return select_events(ws.flags, kind, team_id=_tid(ws, p), match_ids=_mid(ws, p) if match else ws.match_ids(_t(ws, p)),
                         period=p.period)


def _player_ev(ws: Workspace, p: Params, kind: str) -> pd.DataFrame:
    return select_events(ws.flags, kind, player_id=_pid(ws, p), period=p.period)


def _opp_ev(ws: Workspace, p: Params, kind: str, match: bool = True) -> pd.DataFrame:
    ids = [_mid(ws, p)] if match else ws.match_ids(_t(ws, p))
    ev = select_events(ws.flags, kind, match_ids=ids, period=p.period)
    return ev[ev["team_id"] != _tid(ws, p)]


def _subs(ws: Workspace, p: Params) -> pd.DataFrame:
    s = ws.bundle.subs
    return s[s["team_name"] == _t(ws, p)]


def _squad_values(ws: Workspace, p: Params) -> pd.Series:
    s = ws.squad(_t(ws, p)).set_index("player_name")
    return s["xg"] + s["xa"]


def _match_net(ws: Workspace, p: Params) -> tuple[pd.DataFrame, pd.DataFrame, float | None]:
    return nf.pass_network(ws.flags, ws.tables["appearances"], _mid(ws, p), _tid(ws, p), min_passes=3)


def _families(ws: Workspace) -> pd.Series:
    return ws.bundle.season_pct.drop_duplicates("player_id").set_index("player_id")["role_family"]


def _role(ws: Workspace, p: Params) -> str | None:
    s = ws.bundle.season_pct
    r = s.loc[s["player_id"] == _pid(ws, p), "primary_role"]
    return r.iloc[0] if len(r) else None


def _sub_candidates(ws: Workspace, p: Params) -> tuple[dict, pd.DataFrame | None]:
    rec = ws.sub_scenario(_t(ws, p), _mid(ws, p), p.minute)
    if rec.get("status") != "ok":
        return rec, None
    inc = substitution_analysis.rank_incoming(rec["context"], rec["recommended_off"].get("role"), rec["intent"],
                                              ws.cfg)
    return rec, inc


def _state_networks(ws: Workspace, p: Params) -> Any:
    st = ws.event_state(_t(ws, p))
    fl = ws.flags[(ws.flags["team_id"] == _tid(ws, p)) & (ws.flags["type"] == "Pass")]
    a = fl[st.reindex(fl.index) == "leading"]
    b = fl[st.reindex(fl.index).isin(["drawing", "trailing"])]
    na, ea = nf.aggregate_network(a)
    nb, eb = nf.aggregate_network(b)
    return passing.network_compare(
        na, ea, nb, eb, "while leading", "while level or behind", f"{_t(ws, p)}: pass network by score state",
        "season aggregate over all analysed matches · node = mean pass origin of the 14 most involved players "
        "(they were not all on the pitch together) · score state changes who is on the pitch and how the opponent "
        "defends, so differences are not the effect of the scoreline alone")


def _sub_networks(ws: Workspace, p: Params) -> Any:
    mid, tid = _mid(ws, p), _tid(ws, p)
    ev = ws.flags[(ws.flags["match_id"] == mid) & (ws.flags["team_id"] == tid)]
    s = ev.loc[ev["type"] == "Substitution", "elapsed_min"]
    if s.empty:
        return _empty("This team made no substitution in the selected match.", "Network before / after substitution")
    cut = float(s.min())
    na, ea = nf.aggregate_network(ev[ev["elapsed_min"] < cut], min_passes=2)
    nb, eb = nf.aggregate_network(ev[ev["elapsed_min"] >= cut], min_passes=2)
    return passing.network_compare(
        na, ea, nb, eb, f"before the first substitution ({cut:.0f}')", "after it",
        f"{_t(ws, p)}: pass network before and after the first substitution — {_ml(ws, p)}",
        "one match · the two windows differ in length, score, fatigue and opponent changes, so this is a description "
        "of two periods, not the effect of the substitution")


def _player_shots(ws: Workspace, p: Params) -> pd.DataFrame:
    return select_events(ws.flags, "Shots", player_id=_pid(ws, p))


def _corr_matrix(ws: Workspace, p: Params, method: str) -> Any:
    el = _el(ws, p)
    cols = [c for c in EDA_METRICS if c in el.columns]
    r, n = statistical_tests.correlation_matrix(el, cols, method)
    return inference.correlation_matrix_chart(r, n, method, f"{len(el)} players with ≥ {_mm(ws, p):.0f} minutes")


def _pair(ws: Workspace, p: Params) -> tuple[pd.DataFrame, dict]:
    el = _el(ws, p)
    return el, statistical_tests.pair_correlation(el, p.metric, p.metric_y, seed=ws.seed)


def _partials(ws: Workspace, p: Params) -> list[dict]:
    tm = ws.team_matches(_t(ws, p)).assign(home=lambda d: (d["home_away"] == "home").astype(float))
    return [statistical_tests.partial_correlation(tm, v, "goal_diff", ["home"])
            for v in ("xg", "xg_against", "shots", "possession_proxy_pct", "ppda")]


def _bootstrap_metric(ws: Workspace, p: Params) -> Any:
    tm = ws.team_matches(_t(ws, p))
    v = tm[p.team_metric].dropna().to_numpy(float)
    b = uncertainty.bootstrap_distribution(v, n_boot=4000, seed=ws.seed)
    return inference.bootstrap_hist(b, float(np.mean(v)) if len(v) else np.nan,
                                    f"{_t(ws, p)}: bootstrap distribution of the mean {distribution.nice(p.team_metric)}",
                                    f"mean {distribution.nice(p.team_metric)} per match",
                                    f"n = {len(v)} matches resampled with replacement")


def _rate_intervals(ws: Workspace, p: Params) -> pd.DataFrame:
    sq = ws.squad(_t(ws, p))
    sq = sq[(sq["minutes_played"] >= 900) & (sq["primary_role"] != "GK")]
    num = p.metric[:-4] if p.metric.endswith("_p90") else "xg"
    num = num if num in ws.bundle.pms.columns else "xg"
    return uncertainty.bootstrap_rate_intervals(ws.bundle.pms, sq, num, seed=ws.seed).assign(numerator=num)


def _venue_perm(ws: Workspace, p: Params) -> Any:
    tm = ws.team_matches(_t(ws, p))
    res = statistical_tests.permutation_test(tm.loc[tm["home_away"] == "home", p.team_metric],
                                             tm.loc[tm["home_away"] == "away", p.team_metric], seed=ws.seed)
    return inference.permutation_chart(res, "home", "away", distribution.nice(p.team_metric))


def _posthoc(ws: Workspace, p: Params) -> Any:
    el = _el(ws, p)
    kw = statistical_tests.kruskal_groups(el, p.metric, p.group)
    post = statistical_tests.pairwise_posthoc(el, p.metric, p.group)
    return inference.posthoc_heatmap(post, kw, p.metric, p.group)


def _acf(ws: Workspace, p: Params) -> Any:
    tm = ws.team_matches(_t(ws, p))
    return inference.acf_chart(tm, statistical_tests.autocorrelation(tm[p.team_metric], 10), p.team_metric, _t(ws, p))


def _stability(ws: Workspace, p: Params) -> Any:
    tm = ws.team_matches(_t(ws, p))
    st = uncertainty.interval_width_by_sample(tm[p.team_metric].to_numpy(float), seed=ws.seed)
    return inference.stability_chart(st, f"{_t(ws, p)}: how the estimate of mean {distribution.nice(p.team_metric)} "
                                         f"settles as matches accumulate", f"mean {distribution.nice(p.team_metric)}")


def _report_card(ws: Workspace, p: Params) -> Any:
    sp = ws.bundle.season_pct
    pid = _pid(ws, p)
    prof = player_profile(sp, pid)
    if not prof:
        return _empty("Player not found.", "Player report card")
    sw = strengths_weaknesses(sp, pid, ws.cfg)
    rows = [(k.replace("_", " "), v) for k, v in prof.items()]
    for r in sw.itertuples():
        rows.append((r.type, f"{r.metric}: {r.value:.2f} (percentile {r.percentile:.0f})"))
    rows.append(("evidence not in the source", "age, height, injury history, physical load, contract, market value"))
    return table_figure(pd.DataFrame(rows, columns=["field", "value"]).astype(str),
                        f"{prof.get('player')}: report card", max_rows=30)


def _actual_vs_shortlist(ws: Workspace, p: Params) -> Any:
    res = ws.xi_result(_t(ws, p), _mid(ws, p), p.formation)
    cmp_, share = xi.compare_with_actual(res, ws.tables["appearances"], _mid(ws, p), _tid(ws, p))
    cmp_ = cmp_.assign(in_recommended=cmp_["in_recommended"].map({True: "yes", False: "—"}),
                       in_actual=cmp_["in_actual"].map({True: "yes", False: "—"}))
    return table_figure(cmp_.rename(columns={"in_recommended": "in pre-match shortlist", "in_actual": "actually started"}),
                        f"Shortlist vs actual XI — {_ml(ws, p)} ({share:.0%} of the actual XI also shortlisted; "
                        f"agreement is similarity, not quality)", max_rows=25)


def _alt_formations(ws: Workspace, p: Params) -> Any:
    comp = ws.formation_comparison(_t(ws, p), _mid(ws, p))
    forms = comp["formation"].tolist()
    a = p.formation if p.formation in forms else forms[0]
    b = next((f for f in forms if f != a), a)
    ra, rb = ws.xi_result(_t(ws, p), _mid(ws, p), a), ws.xi_result(_t(ws, p), _mid(ws, p), b)
    return tactics.alternative_xi_comparison(ra.lineup, rb.lineup, a, b)


def _freeze(ws: Workspace, p: Params) -> Any:
    mid = _mid(ws, p)
    frames = ws.frames_360(mid)
    if not frames:
        return _empty(f"No 360 file is cached for this match ({_ml(ws, p)}). Load it from the Pitch & Event "
                      f"Explorer or with Workspace.load_360(match_id).", "StatsBomb 360 freeze frame")
    ev_ids = set(ws.flags.loc[ws.flags["match_id"] == mid, "event_id"])
    shared = len(ev_ids & set(frames))
    if shared == 0:
        return _empty(f"Source inconsistency: the published 360 file of this match shares 0 of {len(frames):,} "
                      f"frame identifiers with its event file, so frames cannot be attached to events. No frame "
                      f"is shown rather than guessing a match.", "StatsBomb 360 freeze frame")
    sh = ws.flags[(ws.flags["match_id"] == mid) & (ws.flags["type"] == "Shot")
                  & ws.flags["event_id"].isin(list(frames))].sort_values("shot_xg", ascending=False)
    if sh.empty:
        return _empty("No shot of this match has a 360 frame.", "StatsBomb 360 freeze frame")
    ev = sh.iloc[0]
    return spatial.freeze_frame(frames[ev["event_id"]], ev, f"360 freeze frame — highest-xG shot of {_ml(ws, p)}")


def _sequence(ws: Workspace, p: Params) -> Any:
    mid = _mid(ws, p)
    pl = spatial.possession_list(ws.flags, mid, _tid(ws, p))
    if pl.empty:
        return _empty("No possession of this team ends in a shot with enough recorded actions.",
                      "Possession sequence")
    return spatial.sequence_animation(ws.flags, mid, pl["possession"].iloc[0],
                                      f"{_t(ws, p)}: highest-xG possession — {_ml(ws, p)}")


def _possession_sunburst(ws: Workspace, p: Params) -> Any:
    import plotly.express as px
    from src.visualization.theme import COLORWAY, sub

    fl = ws.flags[ws.flags["match_id"].isin(ws.match_ids(_t(ws, p))) & (ws.flags["possession_team_id"] == _tid(ws, p))]
    g = fl.groupby(["match_id", "possession"]).agg(pattern=("play_pattern", "first"), shots=("shots", "sum"),
                                                   goals=("goals", "sum"), entered=("final_third_touches", "sum"))
    if g.empty:
        return _empty("No possessions for this team.", "Possession sequence sunburst")
    g["reach"] = np.where(g["entered"] > 0, "reached final third", "ended before final third")
    g["end"] = np.where(g["goals"] > 0, "goal", np.where(g["shots"] > 0, "shot, no goal", "no shot"))
    d = g.groupby(["pattern", "reach", "end"]).size().rename("possessions").reset_index()
    fig = px.sunburst(d, path=["pattern", "reach", "end"], values="possessions", color="pattern",
                      color_discrete_sequence=COLORWAY)
    fig.update_traces(hovertemplate="%{label}: %{value:,} possessions (%{percentParent:.0%} of parent)<extra></extra>")
    fig.update_layout(title=sub(f"{_t(ws, p)}: how possessions start and end",
                                f"{len(g):,} possessions (source possession id) · rings: play pattern at the start → "
                                f"reached the final third → ended with a shot / goal · explicit three-step sequence, "
                                f"not a causal chain"), height=560)
    return fig


def _team_scope(ws: Workspace, p: Params) -> str:
    return f"{_t(ws, p)}, {len(ws.match_ids(_t(ws, p)))} matches"


# ============================================================================= A · Data audit and coverage
add("A-001", "Dataset composition by table", "How large is each table and which ones come straight from the source?",
    lambda ws, p: audit.dataset_composition(ws.bundle), req={"events": ("event_id",)},
    note="Row and column counts of every canonical and derived table; log scale.", legacy="gallery/01_dataset_composition.png")
add("A-002", "Row counts by match, team and player", "Is the event volume balanced across matches?",
    lambda ws, p: audit.rows_by_entity(ws.bundle, "match"), req={"events": ("match_id",), "matches": ("match_id",)},
    note="Event rows per match in date order.")
add("A-003", "Missingness by field", "Which fields have gaps and how large are they?",
    lambda ws, p: audit.missingness_bar(ws.tables["events"], "events"), req={"events": ("event_id",)},
    note="Share of missing values per event field.", caveat="Most gaps are structural: a qualifier exists only for "
    "its event type.", legacy="gallery/02_missing_by_feature.png")
add("A-004", "Missingness matrix", "Do gaps cluster in particular rows or fields?",
    lambda ws, p: audit.nullity_matrix(ws.tables["events"], "events"), req={"events": ("event_id",)},
    note="Nullity of a seeded random sample of 400 event rows.", legacy="gallery/03_missingness_matrix.png")
add("A-005", "Missingness by event type", "Is a missing value expected for that kind of event?",
    lambda ws, p: statistical.missingness_heatmap(event_type_coverage(ws.tables["events"])),
    req={"events": ("type",)}, note="Completeness of each field within each event type.")
add("A-006", "Duplicate full-row and primary-key counts", "Are there duplicated records or keys?",
    lambda ws, p: audit.duplicate_audit(ws.bundle), req={"events": ("event_id",)}, cost="medium",
    note="Counts of duplicated full rows and duplicated primary keys per table.", legacy="gallery/04_duplicates.png")
add("A-007", "Duplicate-ID investigation table", "Which key defines uniqueness in each table?",
    lambda ws, p: audit.duplicate_table(ws.bundle), req={"events": ("event_id",)}, cost="medium",
    note="Table of keys and duplicate counts.")
add("A-008", "Numeric field distributions", "What shape do the numeric event fields have?",
    lambda ws, p: audit.numeric_distributions(ws.tables["events"]), req={"events": ("duration",)},
    note="Histograms with skewness; display clipped at the 99.5th percentile.",
    legacy="gallery/05_numeric_distributions.png")
add("A-009", "Categorical frequency and rare categories", "Which categories dominate and which are rare?",
    lambda ws, p: audit.categorical_frequency(ws.tables["events"], "play_pattern"), req={"events": ("play_pattern",)},
    note="Level frequencies on a log axis; levels under 0.5% flagged.", legacy="gallery/06_categorical_distributions.png")
add("A-010", "Outlier distributions", "Are extreme values errors or real events?",
    lambda ws, p: audit.outlier_boxes(ws.tables["events"]), req={"events": ("duration", "pass_length", "shot_xg")},
    note="Box plots with the count beyond 1.5 × IQR.", caveat="Flagged values are genuine events and are kept.",
    legacy="gallery/07_outliers.png")
add("A-011", "Before / after refinement funnel", "How many rows survive each processing step?",
    lambda ws, p: audit.refinement_funnel(ws.bundle), req={"events": ("x",), "season": ("eligible",)},
    note="Row counts from raw events to eligible player-seasons.", legacy="gallery/08_before_after_cleaning.png")
add("A-012", "Feature availability", "Which analytical inputs exist in the data and which do not?",
    lambda ws, p: audit.feature_availability(ws.bundle), req={"events": ("x",), "squads": ("player_id",)},
    note="Verified from the loaded tables; absent modalities are listed, never imputed.",
    legacy="gallery/09_feature_availability.png")
add("A-013", "Schema and field-type overview", "What kinds of fields does each table hold?",
    lambda ws, p: audit.schema_overview(ws.bundle), req={"events": ("event_id",)}, note="Fields per table by data type.")
add("A-014", "Time coverage and event-timeline gaps", "Which dates are covered and are event timelines continuous?",
    lambda ws, p: audit.time_coverage(ws.bundle), req={"events": ("elapsed_min",), "matches": ("match_date",)},
    note="Events per match over the calendar and the longest within-period gap.")
add("A-015", "Data provenance graph", "How do source files become tables and outputs?",
    lambda ws, p: audit.provenance_graph(ws.bundle), req={"events": ("event_id",)},
    note="Lineage Sankey; link widths carry no meaning.")
add("A-016", "Validation rule pass / fail panel", "Which domain rules and table contracts hold?",
    lambda ws, p: audit.validation_panel(ws.bundle.quality, ws.bundle), req={"quality": ("check", "status")},
    note="Sixteen domain rules plus fourteen table contracts.")

# ===================================================================== B · Descriptive and distribution analytics
_D = dict(req=SP, params=("metric", "group", "min_minutes"), min_players=10)
add("B-017", "Histogram with controlled bins", "How is a per-90 metric distributed across players?",
    lambda ws, p: distribution.histogram(_el(ws, p), p.metric, p.group), note="30 equal-width bins shared by groups.", **_D)
add("B-018", "KDE by role family", "Do role families have differently shaped distributions?",
    lambda ws, p: distribution.kde(_el(ws, p), p.metric, p.group), note="Gaussian KDE, Scott bandwidth; rug of points.",
    caveat="Groups under 5 values are not drawn.", legacy="gallery/10_kde_by_role.png", **_D)
add("B-019", "ECDF comparison", "What share of players sits below a given value?",
    lambda ws, p: distribution.ecdf(_el(ws, p), p.metric, p.group), note="No binning or smoothing.", **_D)
add("B-020", "Box plot with individual points", "Where are the quartiles and who are the outliers?",
    lambda ws, p: distribution.box_points(_el(ws, p), p.metric, p.group, hover="player_name"),
    note="Quartile box with every player drawn.", **_D)
add("B-021", "Violin plot", "How does the density compare between groups?",
    lambda ws, p: distribution.violin(_el(ws, p), p.metric, p.group), note="Density clipped to the observed range.", **_D)
add("B-022", "Raincloud plot", "Shape, quartiles and raw values in one view?",
    lambda ws, p: distribution.raincloud(_el(ws, p), p.metric, p.group), note="Half-violin, box and points.", **_D)
add("B-023", "Strip plot with overplot handling", "Where does each individual player sit?",
    lambda ws, p: distribution.strip(_el(ws, p), p.metric, p.group, hover="player_name", seed=ws.seed),
    note="Deterministic jitter and transparency; medians marked.", **_D)
add("B-024", "Ridgeline density plot", "How do distributions shift across detailed roles?",
    lambda ws, p: distribution.ridgeline(_el(ws, p), p.metric, "primary_role"),
    note="One scaled KDE per primary role.", caveat="Ridges are scaled to equal height: compare shape, not area.",
    req=SP, params=("metric", "min_minutes"), min_players=10)
add("B-025", "Beeswarm chart", "Density and individual values without overlap?",
    lambda ws, p: distribution.beeswarm(_el(ws, p), p.metric, p.group, hover="player_name"),
    note="Greedy non-overlapping placement.", **_D)
add("B-026", "Quantile plot", "How do groups differ at each percentile?",
    lambda ws, p: distribution.quantile_profile(_el(ws, p), p.metric, p.group), note="2nd to 98th percentile.", **_D)
add("B-027", "Q-Q plot", "Is a metric close enough to normal for parametric methods?",
    lambda ws, p: distribution.qq_plot(_el(ws, p), p.metric), note="Normal Q-Q with Shapiro–Wilk.",
    req=SP, params=("metric", "min_minutes"), min_players=10)
add("B-028", "Rank / lollipop chart", "Who leads a metric among eligible players?",
    lambda ws, p: player.lollipop(ws.bundle.season_pct, p.metric, _mm(ws, p)), req=SP,
    params=("metric", "min_minutes"), note="Top 15 with the minutes threshold in the title.")
add("B-029", "Pareto / concentration chart", "How concentrated is chance creation in a few players?",
    lambda ws, p: distribution.pareto(desc.concentration(_squad_values(ws, p)),
                                      f"{_t(ws, p)}: concentration of chance involvement (xG + xA)", "xG + xA"),
    req={"season_pct": ("xg", "xa", "team_name")}, params=("team",),
    note="Sorted xG + xA with cumulative share.", caveat="xA is credited to the passer of a shot assist.")
add("B-030", "Contribution treemap", "Which role families and players create the chances?",
    lambda ws, p: player.chance_treemap(ws.bundle.season_pct, _t(ws, p)), req={"season_pct": ("xg", "xa")},
    params=("team",), note="Area = xG + xA by role family and player.")
add("B-031", "Sunburst of the shot taxonomy", "How do shots break down by pattern, body part and outcome?",
    lambda ws, p: match.shot_sunburst(ws.flags, _t(ws, p)), req=SHOT, params=("team",),
    note="Play pattern → body part → outcome.")
add("B-032", "Waterfall of goal difference by month", "How was the season's goal difference built up?",
    lambda ws, p: match.monthly_waterfall(ws.bundle.team_stats, _t(ws, p)), req=TS, params=("team",),
    note="Monthly goal difference; the components add up exactly.", min_matches=4)
add("B-033", "Attacking funnel", "How much possession turns into shots and goals?",
    lambda ws, p: match.attack_funnel(ws.flags, _tid(ws, p), _t(ws, p)), req=EV, params=("team",),
    note="Completed passes → final-third entries → box touches → shots → goals.",
    caveat="Stages are overlapping event counts, not a strict conversion sequence.")
add("B-034", "Calendar heatmap", "How did performance vary across the fixture calendar?",
    lambda ws, p: match.calendar_heatmap(ws.bundle.team_stats, _t(ws, p)), req=TS, params=("team",),
    note="Week × weekday, coloured by xG difference.", min_matches=4)
add("B-035", "Bump chart of rank changes", "How did the scoring-chance ranking inside the squad evolve?",
    lambda ws, p: comparison.bump_chart(comparison.cumulative_rank_table(ws.bundle.pms, ws.tables["matches"],
                                                                         _t(ws, p), "xg"),
                                        f"{_t(ws, p)}: rank by cumulative xG through the season", "cumulative xG"),
    req={"pms": ("xg", "match_date")}, params=("team",), min_matches=5,
    note="Rank by cumulative xG after each match.", caveat="Ranks hide the size of the gaps.")
add("B-036", "Slope chart for two periods", "Who changed between the first and second half of the season?",
    lambda ws, p: player.slope_chart(ws.bundle.pms, _t(ws, p), "progressive_passes"), req=PMS, params=("team",),
    min_matches=8, note="Per-90 value in each half of the season for regular players.")
add("B-037", "Small-multiple plots", "How do several metrics differ by role family at once?",
    lambda ws, p: distribution.small_multiples(_el(ws, p), [m for m in EDA_METRICS[:8]], "role_family"),
    req=SP, params=("min_minutes",), min_players=10, note="One box-plot panel per metric.",
    caveat="Each panel has its own scale.")
add("B-038", "Bullet chart: target versus actual", "Did the team meet a defined target?",
    reason="No legitimate external target exists in the data. Expected points are shown as a model reference in "
           "chart L-262 instead of being presented as a target.")
add("B-039", "KPI gauges for bounded measures", "Where do the season's bounded indicators stand?",
    lambda ws, p: match.kpi_gauges(ws.bundle.team_stats, _t(ws, p)), req=TS, params=("team",),
    note="Win rate, points per match, xG share, possession proxy, field tilt.",
    caveat="Gauges are used only for measures with natural bounds; the tick marks the neutral value.")

# ================================================================================ C · Match and team analysis
_T = dict(req=TS, params=("team",))
add("C-040", "Results timeline", "What was the sequence of results?",
    lambda ws, p: match.results_overview(ws.bundle.team_stats, _t(ws, p)), note="Goal difference by match.", **_T)
add("C-041", "Goals for and against over the season", "How did goals and xG accumulate?",
    lambda ws, p: match.cumulative_area(ws.bundle.team_stats, _t(ws, p)), note="Cumulative goals and xG for / against.",
    min_matches=3, **_T)
add("C-042", "Rolling performance form", "Is the underlying performance trending?",
    lambda ws, p: match.rolling_band(ws.bundle.team_stats, _t(ws, p)), min_matches=6,
    note="5-match rolling xG difference with a ±1 SD band.", **_T)
add("C-043", "Match-level xG for and against", "How large was the chance-quality gap in each match?",
    lambda ws, p: match.xg_dumbbell(ws.bundle.team_stats, _t(ws, p)), note="Dumbbell per match.", **_T)
add("C-044", "Goals versus xG", "Which matches and which players ran ahead of chance quality?",
    lambda ws, p: player.finishing_scatter(ws.bundle.season_pct, _mm(ws, p), _t(ws, p)),
    req={"season_pct": ("goals", "xg")}, params=("team", "min_minutes"),
    note="Goals against xG per player.", caveat="Finishing over- or under-performance regresses strongly.")
add("C-045", "xG difference distribution", "How often and by how much did the team out-create opponents?",
    lambda ws, p: team.xg_diff_distribution(ws.bundle.team_stats, _t(ws, p)), note="Histogram by result.", **_T)
add("C-046", "Shot volume versus shot quality", "Does dominance come from more shots or better shots?",
    lambda ws, p: team.shot_volume_quality(ws.bundle.team_stats, _t(ws, p)),
    note="Shots vs mean xG per shot, team and opponents.", **_T)
add("C-047", "Shot count and conversion by match", "How many shots, on-target shots and goals per match?",
    lambda ws, p: team.shots_conversion_by_match(ws.bundle.team_stats, _t(ws, p)), note="Nested bars.", **_T)
add("C-048", "Goal timing clock", "When in a match are goals scored and conceded?",
    lambda ws, p: match.goal_clock(ws.tables["goals"], ws.bundle.team_stats, _t(ws, p)), req={**TS, **GOALS},
    params=("team",), note="Polar histogram in 5-minute bins.")
add("C-049", "Goal and event timeline of a match", "What happened and when in the selected match?",
    lambda ws, p: match.match_timeline(match_timeline_events(ws.tables["events"], ws.tables["goals"], _mid(ws, p)),
                                       f"Match timeline — {_ml(ws, p)}"),
    req={"events": ("type", "elapsed_min"), **GOALS}, params=("team", "match"),
    note="Goals, cards and substitutions on the elapsed clock.")
add("C-050", "Score-state time share", "How much of the time was spent leading, level or behind?",
    lambda ws, p: team.score_state_share(ws.state_time(_t(ws, p)), _t(ws, p)), req={**TS, **GOALS}, params=("team",),
    note="Minutes per state from the reconstructed goal timeline.", cost="medium")
add("C-051", "Match-state timeline", "How did the score state evolve within one match?",
    lambda ws, p: team.score_state_timeline(
        desc.score_state_segments(ws.bundle, _mid(ws, p), _tid(ws, p)),
        ws.tables["goals"][ws.tables["goals"]["match_id"] == _mid(ws, p)], _t(ws, p),
        ws.team_matches(_t(ws, p)).set_index("match_id").loc[_mid(ws, p), "opponent"], _tid(ws, p)),
    req={**TS, **GOALS}, params=("team", "match"), note="State bands with goals marked.")
add("C-052", "Team comparison radar", "What is the team's style fingerprint?",
    lambda ws, p: tactics.team_style_radar(ws.bundle.team_stats, _t(ws, p)), **_T,
    note="Percentile of team averages among the teams in the dataset.",
    caveat="Opponents appear twice (home and away), always against the focus team.")
add("C-053", "Team metric percentile profile", "Where does the team's typical match rank among all team-matches?",
    lambda ws, p: team.team_percentile_profile(ws.bundle.team_stats, _t(ws, p)), **_T,
    note="Percentile of the median match within all team-match rows.",
    caveat="Reference set is the team and its opponents on the day — not a league benchmark.")
add("C-054", "Home / away comparison", "Does venue relate to chance creation?",
    lambda ws, p: match.venue_boxes(ws.bundle.team_stats, _t(ws, p)), min_matches=6, **_T,
    note="Box plots by venue.", caveat="17 matches per venue: low power.")
add("C-055", "Opponent matrix", "How did the team fare against each opponent?",
    lambda ws, p: match.opponent_matrix(ws.bundle.team_stats, _t(ws, p)), min_matches=4, **_T,
    note="Opponent × metric, average over meetings.", caveat="Two meetings per opponent.")
add("C-056", "Match-by-match heatmap", "What did every match look like across the key metrics?",
    lambda ws, p: team.match_metric_heatmap(ws.bundle.team_stats, _t(ws, p)), **_T,
    note="Raw values coloured within each column's range.", legacy="gallery/13_match_level_views.png")
add("C-057", "Formation usage timeline", "Which starting formation was used when?",
    lambda ws, p: team.formation_timeline(ws.bundle.team_stats, _t(ws, p)),
    req={"team_stats": ("starting_formation", "match_date")}, params=("team",),
    note="Recorded Starting XI formation by date.", caveat="A nominal label, not the shape in every phase.")
add("C-058", "Formation outcome distribution", "How did results differ by starting formation?",
    lambda ws, p: tactics.formation_comparison(formation_summary(ws.bundle.team_stats, _t(ws, p)), _t(ws, p)),
    req={"team_stats": ("starting_formation",)}, params=("team",), min_matches=4,
    note="Event metrics by starting formation.", caveat="Formation choice depends on opponent and availability.")
add("C-059", "Set-piece versus open-play contribution", "How do shots and goals originate?",
    lambda ws, p: team.origin_split_chart(desc.shot_origin_split(ws.bundle, _t(ws, p)), _t(ws, p)),
    req={"events": ("play_pattern", "shot_xg")}, params=("team",),
    note="Shots, xG and goals by how the possession started.")
add("C-060", "Possession and territory proxies", "How much of the ball and of the final third did the team have?",
    lambda ws, p: team.territory_proxies(ws.bundle.team_stats, _t(ws, p)),
    req={"team_stats": ("possession_proxy_pct", "field_tilt_pct")}, params=("team",),
    note="Pass-share possession proxy and final-third touch share.", caveat="Not timed possession.")
add("C-061", "Pass completion and progression profile", "Is safe passing traded against progression?",
    lambda ws, p: team.pass_progression_profile(ws.bundle.team_stats, _t(ws, p)),
    req={"team_stats": ("pass_completion_pct", "progressive_passes")}, params=("team",),
    note="Completion % vs progressive passes per match.")
add("C-062", "Defensive actions by match", "How much defending was done in each match?",
    lambda ws, p: team.defensive_actions_by_match(ws.flags, ws.bundle.team_stats, _t(ws, p)), **_T,
    note="Tackles, interceptions, blocks, clearances, recoveries.", caveat="Not adjusted for opponent possession.")
add("C-063", "Pressing proxy (PPDA) distribution", "How intense was the pressing proxy?",
    lambda ws, p: team.ppda_distribution(ws.bundle.team_stats, _t(ws, p)), req={"team_stats": ("ppda",)},
    params=("team",), note="Opponent passes in their own 60% / the team's defensive actions there.",
    caveat="An event-based proxy; formula validated against event coverage.")
add("C-064", "Team consistency heatmap", "Which aspects of performance are stable from match to match?",
    lambda ws, p: team.team_consistency_chart(*desc.team_consistency(ws.bundle, _t(ws, p)), _t(ws, p)), **_T,
    min_matches=6, note="Within-season z-scores and coefficient of variation.",
    legacy="gallery/16_team_consistency_heatmap.png")
add("C-065", "Team style quadrant", "Where do teams sit on possession and chance balance?",
    lambda ws, p: team.team_style_quadrant(ws.bundle.team_stats, _t(ws, p)), **_T,
    note="Mean possession proxy vs mean xG difference per team.", caveat="Most teams have two matches here.")
add("C-066", "Team season dashboard", "What is the season at a glance?",
    lambda ws, p: dashboards.season_dashboard(ws.bundle.team_stats, ws.xpts(), _t(ws, p)), **_T, cost="medium",
    note="KPI tiles, form, xG trend and results.", legacy="gallery/interactive/season_dashboard.html")

# ====================================================================== D · Player performance and scouting
add("D-067", "Player ranking bars", "Who ranks highest on the selected metrics?",
    lambda ws, p: player.leaderboard_chart(ws.bundle.season_pct, [p.metric, p.metric_y], _mm(ws, p)), req=SP,
    params=("metric", "metric_y", "min_minutes"), note="Top 15 with the minutes threshold stated.")
add("D-068", "Per-90 rankings", "Who leads per 90 minutes among eligible players?",
    lambda ws, p: player.lollipop(ws.bundle.season_pct, p.metric, _mm(ws, p), 20), req=SP,
    params=("metric", "min_minutes"), note="Per-90 = count / minutes × 90; null below the threshold.")
add("D-069", "Percentile chart by role group", "How does a player rank within his role group?",
    lambda ws, p: comparison.percentile_bars(ws.bundle.season_pct, _pid(ws, p), radar_metrics(_role(ws, p), ws.cfg)),
    req=SP, params=("team", "player"), note="Percentile within the benchmark group, with group size.")
add("D-070", "Player radar", "What is a player's role-specific percentile profile?",
    lambda ws, p: player.player_radar(ws.bundle.season_pct, _pid(ws, p), radar_metrics(_role(ws, p), ws.cfg)),
    req=SP, params=("team", "player"), note="Role metrics as percentiles; all axes higher = higher percentile.")
add("D-071", "Multi-player radar comparison", "How do two players of the same role compare?",
    lambda ws, p: player.player_radar(ws.bundle.season_pct, _pid(ws, p), radar_metrics(_role(ws, p), ws.cfg),
                                      compare_id=p.compare_id),
    req=SP, params=("team", "player", "compare"), note="Two percentile profiles on the same axes.")
add("D-072", "Parallel coordinates", "How do percentile profiles run across metrics within a role family?",
    lambda ws, p: player.role_parallel(ws.bundle.season_pct, "Midfielder", EDA_METRICS[:7], _mm(ws, p), _t(ws, p)),
    req=SP, params=("team", "min_minutes"), min_players=10, note="Percentile lines for midfielders.")
add("D-073", "Player metric scatter", "How do two metrics relate across players?",
    lambda ws, p: player.comparison_scatter(ws.bundle.season_pct, [p.metric, p.metric_y], _mm(ws, p), x=p.metric,
                                            y=p.metric_y, highlight_team=_t(ws, p)),
    req=SP, params=("team", "metric", "metric_y", "min_minutes"), note="Size = minutes; medians dotted.")
add("D-074", "Player pair plot", "How do several per-90 metrics relate pairwise?",
    lambda ws, p: player.metric_splom(ws.bundle.season_pct, EDA_METRICS[:5], _mm(ws, p)), req=SP,
    params=("min_minutes",), min_players=10, cost="medium", note="Scatter-plot matrix by role family.",
    legacy="gallery/11_pair_plot.png")
add("D-075", "Player correlation matrix", "Which player metrics move together?",
    lambda ws, p: statistical.correlation_heatmap(_el(ws, p), EDA_METRICS), req=SP, params=("min_minutes",),
    min_players=10, note="Spearman correlations among eligible players.")
add("D-076", "Player-by-metric heatmap", "Where is the squad strong and weak, player by player?",
    lambda ws, p: player.squad_percentile_heatmap(ws.bundle.season_pct, _t(ws, p), EDA_METRICS, _mm(ws, p)), req=SP,
    params=("team", "min_minutes"), note="Squad × metric percentile matrix.")
add("D-077", "Role distribution violins", "How do metrics distribute by role?",
    lambda ws, p: player.role_distribution(ws.bundle.season_pct, [p.metric], _mm(ws, p)), req=SP,
    params=("metric", "min_minutes"), min_players=10, note="Violin per role with n per role.")
add("D-078", "Match consistency plot", "How variable is a player's output from match to match?",
    lambda ws, p: distribution.box_points(
        ws.bundle.pms[(ws.bundle.pms["team_name"] == _t(ws, p)) & (ws.bundle.pms["minutes_played"] >= 45)]
        .assign(involvement_p90=lambda d: (d["xg"] + d["xa"]) / d["minutes_played"] * 90)
        .pipe(lambda d: d[d["player_name"].isin(d["player_name"].value_counts().head(10).index)]),
        "involvement_p90", "player_name", title=f"{_t(ws, p)}: match-level xG + xA per 90 (10 most-used players)"),
    req={"pms": ("xg", "xa", "minutes_played")}, params=("team",), note="Matches of at least 45 minutes.")
add("D-079", "Bootstrap confidence intervals per player", "How certain are per-90 rates?",
    lambda ws, p: scouting.interval_chart(_rate_intervals(ws, p), f"{_t(ws, p)}: per-90 rate with bootstrap intervals "
                                          f"(players ≥ 900 minutes)", "rate per 90 minutes"),
    req=PMS, params=("team", "metric"), cost="medium", min_matches=6,
    note="2,000 bootstrap resamples of each player's matches.", legacy="gallery/20_bootstrap_player_intervals.png")
add("D-080", "Player match-by-match trend", "Is a player's form rising or falling?",
    lambda ws, p: player.form_trend(rolling_form_series(ws.bundle.pms, _pid(ws, p), ["xg", "key_passes"],
                                                        ws.cfg.form_window), ["xg", "key_passes"], _pname(ws, p),
                                    ws.cfg.form_window),
    req=PMS, params=("team", "player"), note="Rolling per-90 over recent appearances.")
add("D-081", "Player contribution decomposition", "How do goals and assists compare with expected involvement?",
    lambda ws, p: player.goal_involvement_bars(ws.bundle.season_pct, _t(ws, p)),
    req={"season_pct": ("goals", "assists", "xg", "xa")}, params=("team",), note="Goals + assists with xG + xA.")
add("D-082", "Goal contribution timeline", "How did goal involvement accumulate over the season?",
    lambda ws, p: player.involvement_race(ws.bundle.pms, _t(ws, p)), req={"pms": ("goals", "assists")},
    params=("team",), cost="medium", note="Animated cumulative goals + assists.")
add("D-083", "xG / xA contribution scatter", "Who creates for himself and who for others?",
    lambda ws, p: player.comparison_scatter(ws.bundle.season_pct, ["xg_p90", "xa_p90"], _mm(ws, p), x="xg_p90",
                                            y="xa_p90", highlight_team=_t(ws, p)),
    req={"season_pct": ("xg_p90", "xa_p90")}, params=("team", "min_minutes"), note="xG/90 against xA/90.")
add("D-084", "Player shot map", "Where does a player shoot from and with what quality?",
    lambda ws, p: pitch.shot_map(_player_shots(ws, p), f"{_pname(ws, p)}: shots"), req=SHOT,
    params=("team", "player"), note="Marker size = StatsBomb xG.")
add("D-085", "Shot map split by body part", "Do shot locations differ by body part?",
    lambda ws, p: spatial.shot_facets(_team_ev(ws, p, "Shots"), "shot_body_part", f"{_t(ws, p)}: shots by body part"),
    req={"events": ("x", "y", "shot_xg", "shot_body_part")}, params=("team",), note="One half-pitch per body part.")
add("D-086", "Shot xG density map", "Where do shots for and against concentrate?",
    lambda ws, p: pitch.shot_density_pair(ws.flags, _tid(ws, p), ws.match_ids(_t(ws, p)), _t(ws, p)), req=SHOT,
    params=("team",), note="Density of attempts for and against.", caveat="Smoothed density interpolates.")
add("D-087", "Player pass map", "Where does a player pass from and to?",
    lambda ws, p: pitch.pass_map(_player_ev(ws, p, "Passes"), f"{_pname(ws, p)}: passes"), req=PASS,
    params=("team", "player"), note="Random sample of 600 when larger; completed vs incomplete.")
add("D-088", "Progressive pass map", "Where do a player's progressive passes go?",
    lambda ws, p: spatial.arrow_map(_player_ev(ws, p, "Progressive passes"),
                                    f"{_pname(ws, p)}: progressive passes"), req=PASS, params=("team", "player"),
    note="Completed, start x ≥ 48, ends ≥ 25% closer to goal.")
add("D-089", "Carry map", "Where does a player carry the ball?",
    lambda ws, p: spatial.arrow_map(_player_ev(ws, p, "Progressive carries"),
                                    f"{_pname(ws, p)}: progressive carries", color="#2a9d8f"), req=EVE,
    params=("team", "player"), note="Carries ending ≥ 25% closer to goal.")
add("D-090", "Dribble map", "Where does a player take opponents on and with what result?",
    lambda ws, p: spatial.event_points(_player_ev(ws, p, "Dribbles"), f"{_pname(ws, p)}: take-ons", "outcome"),
    req=EV, params=("team", "player"), note="Coloured by the recorded outcome.")
add("D-091", "Defensive action map", "Where does a player defend?",
    lambda ws, p: spatial.event_points(_player_ev(ws, p, "Defensive actions"),
                                       f"{_pname(ws, p)}: defensive actions", "type"), req=EV,
    params=("team", "player"), note="Tackles, interceptions, blocks, clearances, recoveries.")
add("D-092", "Pressure map", "Where does a player press?",
    lambda ws, p: spatial.zone_grid(_player_ev(ws, p, "Pressures"), f"{_pname(ws, p)}: pressures by zone"), req=EV,
    params=("team", "player"), note="Share of the player's pressure events per zone.")
add("D-093", "Recovery, interception and tackle map", "Where does a player win the ball back?",
    lambda ws, p: spatial.event_points(pd.concat([_player_ev(ws, p, k) for k in ("Ball recoveries", "Interceptions",
                                                                                "Tackles")]),
                                       f"{_pname(ws, p)}: ball-winning actions", "type"), req=EV,
    params=("team", "player"), note="Three ball-winning event types.")
add("D-094", "Player action heatmap", "Where is a player active for a chosen action type?",
    lambda ws, p: pitch.action_heatmap(_player_ev(ws, p, p.kind), f"{_pname(ws, p)}: {p.kind.lower()}"), req=EV,
    params=("team", "player", "kind"), note="Share of actions per 12 × 8 zone.")
add("D-095", "Player touch heatmap", "Where does a player touch the ball?",
    lambda ws, p: pitch.action_heatmap(_player_ev(ws, p, "Touches"), f"{_pname(ws, p)}: touches"), req=EV,
    params=("team", "player"), note="On-ball events counted as touches.")
add("D-096", "Player spatial KDE", "Where is a player's on-ball activity densest?",
    lambda ws, p: spatial.density_contours(_player_ev(ws, p, "Touches"), f"{_pname(ws, p)}: touch density"), req=EV,
    params=("team", "player"), note="Contours of a smoothed histogram.", caveat="Smoothing interpolates.")
add("D-097", "Convex hull of touch locations", "What is a player's observed event footprint?",
    lambda ws, p: spatial.convex_hull(select_events(ws.flags, "Touches", player_id=_pid(ws, p), match_ids=_mid(ws, p)),
                                      f"{_pname(ws, p)}: event footprint — {_ml(ws, p)}"), req=EV,
    params=("team", "player", "match"), note="Hull of the central 90% of touch locations in one match.",
    caveat="An event footprint, not the area the player occupied.")
add("D-098", "Role comparison small multiples", "How do typical values differ by detailed role?",
    lambda ws, p: scouting.role_small_multiples(ws.bundle.season_pct, EDA_METRICS[:8], _mm(ws, p)), req=SP,
    params=("min_minutes",), min_players=10, note="Median per primary role; roles under 5 players dropped.")
add("D-099", "Player archetype clusters", "Do statistical profiles form recognisable groups?",
    lambda ws, p: player.archetype_map(ws.archetypes(), _t(ws, p)), req=SP, params=("team",), min_players=20,
    cost="medium", note="K-Means on standardised profiles; k by silhouette.",
    caveat="Descriptive grouping, validated in K-240 to K-242.")
add("D-100", "PCA player projection", "Where do players sit on the main axes of variation?",
    lambda ws, p: model.pca_map(ws.pca(), _t(ws, p)), req=SP, params=("team",), min_players=20,
    note="First two principal components by role family.")
add("D-101", "Player similarity map", "Which players have the closest statistical profile?",
    lambda ws, p: scouting.similar_players_chart(
        player_comparison.similar_players(ws.bundle.season_pct, _pid(ws, p), min_minutes=_mm(ws, p)), _pname(ws, p)),
    req=SP, params=("team", "player", "min_minutes"), min_players=20,
    note="Euclidean distance on z-scores within the role family.",
    caveat="Depends on the metric set and the standardisation sample.")
add("D-102", "Consistency versus output quadrant", "Who combines volume with steadiness?",
    lambda ws, p: scouting.consistency_quadrant(ws.consistency(_t(ws, p)), _t(ws, p)), req=PMS, params=("team",),
    min_matches=10, note="Mean progressive actions/90 vs coefficient of variation.",
    legacy="gallery/15_player_consistency.png")
add("D-103", "Role-fit matrix", "Which roles does the evidence support for each player?",
    lambda ws, p: scouting.role_fit_heatmap(player_comparison.role_fit_matrix(ws.bundle.season_pct, _t(ws, p), ws.cfg),
                                            _t(ws, p)), req=SP, params=("team",),
    note="Weighted role percentiles, masked by position compatibility.", caveat="A transparent heuristic.")
add("D-104", "Squad depth chart", "Who has actually covered each role?",
    lambda ws, p: scouting.squad_depth_chart(desc.squad_depth(ws.bundle, _t(ws, p)), _t(ws, p)),
    req={"appearances": ("match_role", "minutes_played")}, params=("team",), note="Minutes by role and player.")
add("D-105", "Minutes distribution and appearance bars", "How is playing time shared?",
    lambda ws, p: player.workload_bars(ws.bundle.season, _t(ws, p)), req={"season": ("minutes_played", "starts")},
    params=("team",), note="Minutes, starts and substitute appearances.")
add("D-106", "Rotation / appearance calendar", "Who played in which match?",
    lambda ws, p: tactics.rotation_matrix(ws.tables["appearances"], ws.tables["matches"], _t(ws, p)), req=APP,
    params=("team",), note="Player × match minutes matrix.", legacy="gallery/interactive/rotation_matrix.html")
add("D-107", "Minutes-based exposure proxy", "How many minutes did a player carry into each match?",
    lambda ws, p: scouting.exposure_timeline(ws.bundle.workload, ws.tables["appearances"], ws.tables["matches"],
                                             _pid(ws, p), _pname(ws, p)),
    req={"workload": ("minutes_prev_7d", "minutes_prev_28d")}, params=("team", "player"),
    note="Minutes in the previous 7, 14 and 28 days.", caveat="An exposure proxy from league minutes only — not "
    "physical load or fatigue.")
add("D-108", "Player report card", "What does the evidence say about one player, and what is missing?",
    _report_card, req=SP, params=("team", "player"), note="Identity, exposure, strongest and weakest percentiles, "
    "missing evidence.")

# =================================================================== E · Pitch, spatial and event analytics
add("E-109", "Standard pitch with team overlay", "Where do the team's actions of a chosen type occur?",
    lambda ws, p: spatial.event_points(_team_ev(ws, p, p.kind, match=True), f"{_t(ws, p)}: {p.kind.lower()} — "
                                       f"{_ml(ws, p)}"), req=EV, params=("team", "match", "kind"),
    note="Locations of the selected event kind in one match.")
add("E-110", "Team shot map", "Where did the team shoot from in a match?",
    lambda ws, p: pitch.shot_map(_team_ev(ws, p, "Shots", match=True), f"{_t(ws, p)}: shots — {_ml(ws, p)}"),
    req=SHOT, params=("team", "match"), note="Marker size = StatsBomb xG; star = goal.")
add("E-111", "Pass map with arrows", "How did the team move the ball in a match?",
    lambda ws, p: spatial.arrow_map(_team_ev(ws, p, "Passes", match=True), f"{_t(ws, p)}: passes — {_ml(ws, p)}"),
    req=PASS, params=("team", "match"), note="Arrow heads at the end point; failed passes in red.",
    caveat="Random sample of 500 arrows when larger.")
add("E-112", "Pass density heatmap", "Where does the team pass from over the season?",
    lambda ws, p: pitch.action_heatmap(_team_ev(ws, p, "Passes"), f"{_t(ws, p)}: pass origins"), req=PASS,
    params=("team",), note="Share of passes per zone.")
add("E-113", "Pass-origin hexbin", "Where do passes start, without smoothing?",
    lambda ws, p: static_pitch.hexbin_map(_team_ev(ws, p, "Completed passes"), f"{_t(ws, p)}: completed-pass origins"),
    req=PASS, params=("team",), lib="mplsoccer", package="mplsoccer",
    note="Hexagonal counts of start locations.", legacy="gallery/12_pass_origin_hexbin.png")
add("E-114", "Pass-end hexbin", "Where do passes arrive?",
    lambda ws, p: static_pitch.hexbin_map(_team_ev(ws, p, "Completed passes"),
                                          f"{_t(ws, p)}: completed-pass destinations", end=True),
    req=PASS, params=("team",), lib="mplsoccer", package="mplsoccer", note="Hexagonal counts of end locations.")
add("E-115", "Team carry map", "Where does the team carry the ball forward?",
    lambda ws, p: spatial.arrow_map(_team_ev(ws, p, "Progressive carries", match=True),
                                    f"{_t(ws, p)}: progressive carries — {_ml(ws, p)}", color="#2a9d8f"), req=EVE,
    params=("team", "match"), note="Carries ending ≥ 25% closer to goal.")
add("E-116", "Progressive action map", "Where does the team progress the ball by pass and carry?",
    lambda ws, p: pitch.progressive_actions_map(ws.flags[(ws.flags["match_id"] == _mid(ws, p))
                                                         & (ws.flags["team_id"] == _tid(ws, p))],
                                                f"{_t(ws, p)}: progressive actions — {_ml(ws, p)}"),
    req=EVE, params=("team", "match"), note="Project definitions stated in the subtitle.")
add("E-117", "Pressure map", "Where does the team apply pressure?",
    lambda ws, p: spatial.zone_grid(_team_ev(ws, p, "Pressures"), f"{_t(ws, p)}: pressures by zone"), req=EV,
    params=("team",), note="Share of pressure events per zone over the season.")
add("E-118", "Defensive action zones", "In which zones does the team defend?",
    lambda ws, p: spatial.zone_grid(_team_ev(ws, p, "Defensive actions"), f"{_t(ws, p)}: defensive actions by zone",
                                    nx=6, ny=3), req=EV, params=("team",), note="6 × 3 tactical zones.")
add("E-119", "Touch map", "Where does the team have the ball?",
    lambda ws, p: pitch.action_heatmap(_team_ev(ws, p, "Touches", match=True), f"{_t(ws, p)}: touches — {_ml(ws, p)}"),
    req=EV, params=("team", "match"), note="Share of touches per zone in one match.")
add("E-120", "KDE event distribution", "Where is a chosen action densest?",
    lambda ws, p: spatial.density_contours(_team_ev(ws, p, p.kind), f"{_t(ws, p)}: density of {p.kind.lower()}"),
    req=EV, params=("team", "kind"), note="Smoothed contours.", caveat="Shading between events is interpolation.")
add("E-121", "Zone heatmaps (3×3, 5×5, tactical)", "How are actions shared across tactical zones?",
    lambda ws, p: spatial.zone_grid(_team_ev(ws, p, p.kind), f"{_t(ws, p)}: {p.kind.lower()} on a 5 × 5 grid", nx=5,
                                    ny=5), req=EV, params=("team", "kind"), note="Counts and shares per cell.")
add("E-122", "Directional action arrows", "In which directions does the team pass?",
    lambda ws, p: pitch.pass_direction_rose(_team_ev(ws, p, "Passes"), f"{_t(ws, p)}: pass directions"), req=PASS,
    params=("team",), note="Polar histogram; forward = up; colour = completion rate.")
add("E-123", "Cross and set-piece maps", "Where do crosses and set-piece deliveries come from?",
    lambda ws, p: spatial.arrow_map(pd.concat([_team_ev(ws, p, "Crosses", match=True),
                                               _team_ev(ws, p, "Set-piece passes", match=True)]).drop_duplicates(
        "event_id"), f"{_t(ws, p)}: crosses and set-piece passes — {_ml(ws, p)}"), req=PASS, params=("team", "match"),
    note="Source cross flag and set-piece pass types.")
add("E-124", "Goalkeeper action map", "Where does the goalkeeper act?",
    lambda ws, p: spatial.event_points(_team_ev(ws, p, "Goalkeeper actions"), f"{_t(ws, p)}: goalkeeper events",
                                       "goalkeeper_type"), req={"events": ("x", "y", "goalkeeper_type")},
    params=("team",), note="Goal Keeper events by recorded type.",
    caveat="Positions are recorded in the goalkeeper's own attacking frame.")
add("E-125", "Convex hull event footprint", "What area do the team's recorded actions of one kind cover?",
    lambda ws, p: spatial.convex_hull(_team_ev(ws, p, p.kind, match=True), f"{_t(ws, p)}: footprint of "
                                      f"{p.kind.lower()} — {_ml(ws, p)}"), req=EV, params=("team", "match", "kind"),
    note="Hull of the central 90% of locations.", caveat="Event footprint, not occupied space.")
add("E-126", "Voronoi diagram", "Which player is closest to each point of the pitch?", modality="tracking",
    reason="Needs every player's position at the same instant. Event data give one actor per event, and 360 freeze "
           "frames show only players inside the camera view, so a Voronoi partition would be invented space.")
add("E-127", "Delaunay triangulation", "How are team-mates connected spatially at one moment?", modality="tracking",
    reason="Needs simultaneous positions of all team-mates (tracking data); not derivable from event locations.")
add("E-128", "Pitch-control / space-control map", "Which team controls which space?", modality="tracking",
    reason="Needs positions and velocities of all 22 players (tracking). Never approximated from event x/y.")
add("E-129", "360 freeze-frame plot", "Who was where, inside the camera view, at the moment of a shot?", _freeze,
    req={"frames_360": ()}, params=("team", "match"), modality="360", cost="high",
    note="StatsBomb 360 frame of the match's highest-xG shot.", caveat="Only players in the camera view are recorded.")
add("E-130", "Animated event sequence", "How was the best chance of a match built?", _sequence, req=EVE,
    params=("team", "match"), cost="medium", note="Ball path of the highest-xG possession ending in a shot.",
    caveat="Only the ball-carrier's events are known.")
add("E-131", "Spatial comparison team versus opponent", "Where did each side have the ball?",
    lambda ws, p: spatial.pair_heatmaps(_team_ev(ws, p, "Touches", match=True), _opp_ev(ws, p, "Touches"), _t(ws, p),
                                        "Opponent", f"Touch territory — {_ml(ws, p)}"), req=EV,
    params=("team", "match"), note="Zone shares side by side.", caveat="Shares are within-panel.")
add("E-132", "Half-by-half location maps", "Did the team's territory change after the interval?",
    lambda ws, p: spatial.period_split(_team_ev(ws, p, "Touches", match=True), f"{_t(ws, p)}: touches by half — "
                                       f"{_ml(ws, p)}"), req={"events": ("x", "y", "period")},
    params=("team", "match"), note="Both halves shown attacking left to right.")
add("E-133", "Pass progression lanes", "Through which lanes does the team progress?",
    lambda ws, p: spatial.progression_lanes(_team_ev(ws, p, "Progressive passes"),
                                            f"{_t(ws, p)}: progressive passes by lane and third"), req=PASS,
    params=("team",), note="Five lanes × three thirds by pass origin.")
add("E-134", "Event transition Sankey", "Between which zones does the ball move?",
    lambda ws, p: spatial.zone_transitions(_team_ev(ws, p, "Completed passes"),
                                           f"{_t(ws, p)}: completed-pass transitions between zones"), req=PASS,
    params=("team",), note="Zone = third × (central | wide).", caveat="Small flows hidden; share shown stated.")
add("E-135", "Pass-flow network", "How does the ball flow between pitch zones?",
    lambda ws, p: pitch.pass_flow_matrix(ws.flags[ws.flags["match_id"].isin(ws.match_ids(_t(ws, p)))], _tid(ws, p),
                                         f"{_t(ws, p)}: pass flow between nine zones"), req=PASS, params=("team",),
    note="Completed passes between thirds × lanes.")
add("E-136", "Event sequence sunburst", "How do possessions start and end?", _possession_sunburst,
    req={"events": ("possession", "play_pattern")}, params=("team",), cost="medium",
    note="Play pattern → reached final third → shot / goal.")

# =================================================================== F · Passing networks and team structure
add("F-137", "Pass network by match", "Who connected with whom in a match?",
    lambda ws, p: network_core.pass_network_chart(*_match_net(ws, p)[:2], f"{_t(ws, p)}: pass network — {_ml(ws, p)}",
                                                  _match_net(ws, p)[2]), req=PASS, params=("team", "match"),
    note="Completed passes before the first substitution.")
add("F-138", "Season-average pass network", "What does the team's typical passing structure look like?",
    lambda ws, p: passing.network_chart(*nf.aggregate_network(_team_ev(ws, p, "Passes")),
                                        f"{_t(ws, p)}: season-aggregate pass network", _team_scope(ws, p)), req=PASS,
    params=("team",), cost="medium", note="All matches pooled; 14 most involved players.",
    caveat="Pooled players were not all on the pitch together.")
add("F-139", "Network node centrality", "Who are the hubs and bridges of the passing game?",
    lambda ws, p: passing.centrality_bars(ws.centrality_summary(_t(ws, p)), _t(ws, p)), req=PASS, params=("team",),
    cost="medium", min_matches=5, note="PageRank, betweenness and pass share averaged over match networks.",
    legacy="gallery/14_network_centrality.png")
add("F-140", "Network with centrality-sized nodes", "Which players carry the structure in one match?",
    lambda ws, p: passing.network_chart(*_match_net(ws, p)[:2], f"{_t(ws, p)}: pass network sized by betweenness — "
                                        f"{_ml(ws, p)}", "until the first substitution",
                                        size_by=ws.centrality(_t(ws, p)).pipe(lambda d: d[d["match_id"] == _mid(ws, p)])
                                        .set_index("player_id")["betweenness"], size_label="betweenness centrality"),
    req=PASS, params=("team", "match"), cost="medium", note="Node size and edge width defined in the subtitle.")
add("F-141", "Network centrality comparison", "Who is a hub and who is a bridge?",
    lambda ws, p: passing.centrality_scatter(ws.centrality_summary(_t(ws, p)), _t(ws, p)), req=PASS, params=("team",),
    cost="medium", min_matches=5, note="PageRank vs betweenness, size = pass share.")
add("F-142", "Network with role colouring", "How do role families connect?",
    lambda ws, p: passing.network_chart(*_match_net(ws, p)[:2], f"{_t(ws, p)}: pass network by role family — "
                                        f"{_ml(ws, p)}", "until the first substitution", color_by=_families(ws)),
    req=PASS, params=("team", "match"), note="Node colour = season role family.")
add("F-143", "Passing lane direction and progression", "Which links move the ball forward?",
    lambda ws, p: passing.progression_network(*_match_net(ws, p)[:2], f"{_t(ws, p)}: forward and backward pass links "
                                              f"— {_ml(ws, p)}", "until the first substitution"), req=PASS,
    params=("team", "match"), note="Link colour = direction between mean pass origins.")
add("F-144", "Network change by score state", "Does the passing structure differ when leading?", _state_networks,
    req={**PASS, **GOALS}, params=("team",), cost="high", min_matches=5,
    note="Season passes split by the team's score state.", caveat="Score state is confounded with personnel and "
    "opponent behaviour.")
add("F-145", "Network before / after substitution", "How did the structure look before and after the first change?",
    _sub_networks, req=PASS, params=("team", "match"), note="One match, two time windows.",
    caveat="Windows differ in length, score and opposition; descriptive only.")
add("F-146", "Network robustness (remove-node simulation)", "How dependent is the pass graph on each player?",
    lambda ws, p: passing.robustness_chart(nf.remove_node_scenario(nf.match_pass_graph(ws.flags, _mid(ws, p),
                                                                                      _tid(ws, p)), ws.names()),
                                           f"{_t(ws, p)}: remove-one-player simulation — {_ml(ws, p)}",
                                           "completed passes before the first substitution"), req=PASS,
    params=("team", "match"), note="Change in weighted global efficiency when a node is deleted.",
    caveat="A simulation on the recorded graph, not a match forecast.")
add("F-147", "Role interaction matrix", "Between which roles does the ball travel?",
    lambda ws, p: passing.role_matrix(nf.role_interaction_matrix(_team_ev(ws, p, "Completed passes"),
                                                                 ws.tables["appearances"]),
                                      f"{_t(ws, p)}: passes between roles", _team_scope(ws, p)),
    req={**PASS, "appearances": ("match_role",)}, params=("team",), cost="medium", note="Passer role × recipient role.")
add("F-148", "Player pair passing heatmap", "Which pairs exchange the most passes?",
    lambda ws, p: passing.pair_heatmap(nf.pair_pass_matrix(_team_ev(ws, p, "Completed passes")),
                                       f"{_t(ws, p)}: passer → recipient matrix", _team_scope(ws, p)), req=PASS,
    params=("team",), note="Completed passes among the 14 most involved players.")

# ============================================================ G · Tactical, lineup and formation analytics
_X = dict(req={**SP, **APP}, params=("team", "match", "formation"), cost="medium", min_matches=2)
add("G-149", "Starting XI pitch diagram", "What does the evidence-based shortlist look like on the pitch?",
    lambda ws, p: tactics.xi_pitch(ws.xi_result(_t(ws, p), _mid(ws, p), p.formation).lineup,
                                   f"{_t(ws, p)}: pre-match shortlist in {p.formation} — {_ml(ws, p)}"),
    note="Hungarian assignment of candidates to formation slots.",
    caveat="Best under the stated scoring model and constraints — a shortlist, not the optimal XI.",
    legacy="gallery/interactive/starting_xi.html", **_X)
add("G-150", "Actual XI versus shortlisted XI", "How similar is the heuristic shortlist to the manager's XI?",
    _actual_vs_shortlist, note="Overlap table with the share of the actual XI also shortlisted.",
    caveat="Agreement measures similarity, not which choice was better.", **_X)
add("G-151", "Formation slots and role suitability", "How well does each candidate suit each slot?",
    lambda ws, p: lineup.slot_suitability(ws.xi_scores(_t(ws, p), _mid(ws, p), p.formation), p.formation),
    note="Score per candidate and slot; blank = not eligible.", **_X)
add("G-152", "Team shape from event locations", "Where do each player's actions centre in a match?",
    lambda ws, p: spatial.centroid_shape(_team_ev(ws, p, "Touches", match=True),
                                         f"{_t(ws, p)}: median event locations — {_ml(ws, p)}"),
    req={"events": ("x", "y", "player_id")}, params=("team", "match"), note="Median touch location per player.",
    caveat="Not simultaneous positions and not a formation.")
add("G-153", "Formation frequency", "Which formations were used and with what results?",
    lambda ws, p: tactics.formation_frequency(formation_summary(ws.bundle.team_stats, _t(ws, p)), _t(ws, p)),
    req={"team_stats": ("starting_formation",)}, params=("team",), note="Matches and results per starting formation.",
    caveat="Small-sample formations are flagged.")
add("G-154", "Role occupancy matrix", "Which roles has each player filled?",
    lambda ws, p: lineup.role_occupancy(ws.tables["appearances"], _t(ws, p)),
    req={"appearances": ("match_role", "minutes_played")}, params=("team",), note="Minutes by player and match role.")
add("G-155", "Formation transitions within matches", "Which in-match formation changes were recorded?",
    lambda ws, p: lineup.formation_transitions(ws.tables["formations"], _t(ws, p)),
    req={"formations": ("formation", "type", "team_name")}, params=("team",),
    note="Starting XI → Tactical Shift formation labels.", caveat="Recorded label changes only.")
add("G-156", "Position / role metric profile", "What distinguishes the role families statistically?",
    lambda ws, p: lineup.role_metric_profile(desc.role_medians(ws.bundle, EDA_METRICS)), req=SP, min_players=10,
    note="Median metric by role family (z-coloured, raw values printed).")
add("G-157", "Team tactical radar", "What is the team's tactical fingerprint?",
    lambda ws, p: tactics.team_style_radar(ws.bundle.team_stats, _t(ws, p)), req=TS, params=("team",),
    note="Style indicators as percentiles among teams in the dataset.", caveat="Opponents have two matches each.")
add("G-158", "Match dominance scatter", "How dominant was each performance?",
    lambda ws, p: match.dominance_scatter(ws.bundle.team_stats, _t(ws, p)), req=TS, params=("team",),
    note="xG for vs xG against per match by result.")
add("G-159", "Player-role fit heatmap", "Where could each player be used on the evidence?",
    lambda ws, p: scouting.role_fit_heatmap(player_comparison.role_fit_matrix(ws.bundle.season_pct, _t(ws, p), ws.cfg),
                                            _t(ws, p)), req=SP, params=("team",),
    note="Same matrix as D-103, in the tactical context.", caveat="A transparent heuristic.")
add("G-160", "Squad depth by role", "How many players cover each role and how much have they played there?",
    lambda ws, p: scouting.squad_depth_chart(desc.squad_depth(ws.bundle, _t(ws, p)), _t(ws, p)),
    req={"appearances": ("match_role", "minutes_played")}, params=("team",), note="Minutes by role and player.")
add("G-161", "Bench role composition", "What options were on the bench in each match?",
    lambda ws, p: lineup.bench_composition(ws.tables["appearances"], ws.tables["matches"], _t(ws, p),
                                           ws.bundle.season_pct), req=APP, params=("team",),
    note="Bench players by season role family.", caveat="Bench players have no recorded position on the day.")
add("G-162", "Continuity / rotation matrix", "How stable was selection across the season?",
    lambda ws, p: tactics.rotation_matrix(ws.tables["appearances"], ws.tables["matches"], _t(ws, p)), req=APP,
    params=("team",), note="Player × match minutes matrix.")
add("G-163", "Lineup similarity matrix", "Which matches shared the same starting XI?",
    lambda ws, p: tactics.lineup_similarity(ws.tables["appearances"], ws.tables["matches"], _t(ws, p)), req=APP,
    params=("team",), min_matches=3, note="Jaccard similarity of starting XIs.")
add("G-164", "Co-start network", "Which players usually start together?",
    lambda ws, p: lineup.co_start_network(desc.co_start_counts(ws.bundle, _t(ws, p)), _t(ws, p)), req=APP,
    params=("team",), min_matches=5, note="Links = starts together.", caveat="Circular layout: positions carry no "
    "meaning.")
add("G-165", "Player pairing minutes matrix", "How long has each pair been on the pitch together?",
    lambda ws, p: lineup.pairing_heatmap(desc.pairing_minutes(ws.bundle, _t(ws, p)), _t(ws, p)), req=SPELLS,
    params=("team",), cost="medium", note="Shared minutes from reconstructed, validated on-pitch spells.")
add("G-166", "Starting XI score component breakdown", "Why is each player in the shortlist?",
    lambda ws, p: tactics.score_decomposition(ws.xi_result(_t(ws, p), _mid(ws, p), p.formation).lineup,
                                              ws.cfg.xi_score_weights), note="Weighted components per pick.", **_X)
add("G-167", "Formation sensitivity chart", "How much does the shortlist depend on the formation template?",
    lambda ws, p: lineup.formation_sensitivity(ws.formation_comparison(_t(ws, p), _mid(ws, p)), _t(ws, p)),
    req={**SP, **APP}, params=("team", "match"), cost="high", min_matches=2,
    note="Best total score under each template.", caveat="Heuristic totals, comparable only within this model.")
add("G-168", "Candidate selection frontier", "Which candidates are efficient on two competing criteria?",
    lambda ws, p: lineup.selection_frontier(ws.xi_scores(_t(ws, p), _mid(ws, p), p.formation),
                                            ws.xi_result(_t(ws, p), _mid(ws, p), p.formation).lineup),
    note="Role fit vs recent form with the Pareto front.", **_X)
add("G-169", "Constraint feasibility audit", "Which constraints were enforced and what evidence is missing?",
    lambda ws, p: lineup.feasibility_audit(ws.xi_result(_t(ws, p), _mid(ws, p), p.formation),
                                           ws.xi_context(_t(ws, p), _mid(ws, p)), p.formation),
    note="Checklist of constraints and evidence gaps.", **_X)

# ============================================================== H · Substitution and match-state analytics
add("H-170", "Substitution minute histogram", "When are substitutions made?",
    lambda ws, p: manager.sub_timing_histogram(_subs(ws, p), ws.cfg.sub_timing_bands), req=SUBS, params=("team",),
    note="Share of substitutions per analytical timing band.")
add("H-171", "Substitution timing by score state", "Does timing differ when leading, level or behind?",
    lambda ws, p: substitution.timing_by_group(ws.bundle.subs, _t(ws, p), "game_state"), req=SUBS, params=("team",),
    note="Minute distribution per score state.", caveat="Score state reflects team strength as much as intent.")
add("H-172", "Substitution timing by role", "Are some roles replaced earlier?",
    lambda ws, p: substitution.timing_by_group(ws.bundle.subs, _t(ws, p), "off_role"),
    req={"subs": ("minute", "off_role")}, params=("team",), note="Minute distribution by role going off.",
    caveat="Roles with fewer than 5 substitutions are not drawn.")
add("H-173", "Incoming / outgoing role Sankey", "Which roles replace which?",
    lambda ws, p: manager.role_flow_sankey(sf.role_flow(_subs(ws, p))), req={"subs": ("off_role", "on_role")},
    params=("team",), note="Role going off → role coming on.")
add("H-174", "Substitution role-matching matrix", "How often is a change like-for-like?",
    lambda ws, p: substitution.role_matching_matrix(ws.bundle.subs, _t(ws, p)), req={"subs": ("off_role", "on_role")},
    params=("team",), note="Off role × on role counts.")
add("H-175", "Before / after substitution metrics", "What did the team's output look like around changes?",
    lambda ws, p: manager.impact_chart(ws.impact(), "xg"), req=SUBS, cost="high",
    note="Team xG per 15 minutes in the windows before and after substitution decisions.",
    caveat="Descriptive only: confounded by score, opponent changes, injuries and regression to the mean.")
add("H-176", "Score state at substitution", "In which score state are changes made?",
    lambda ws, p: manager.subs_by_state(_subs(ws, p)), req=SUBS, params=("team",),
    note="Substitutions by score state at the moment of the change.")
add("H-177", "Substitution event timeline", "When did each change happen in a match?",
    lambda ws, p: manager.substitution_timeline(ws.bundle.subs[ws.bundle.subs["match_id"] == _mid(ws, p)],
                                                f"Substitutions — {_ml(ws, p)}"), req=SUBS, params=("team", "match"),
    note="Both teams' substitutions on the elapsed clock.")
add("H-178", "Bench usage", "Which squad members are used from the bench?",
    lambda ws, p: substitution.bench_usage_chart(desc.bench_usage(ws.bundle, _t(ws, p)), _t(ws, p)), req=APP,
    params=("team",), note="Times named on the bench, split into used and unused.")
add("H-179", "Remaining bench availability through a match", "What options remained after each change?",
    lambda ws, p: substitution.bench_availability_timeline(ws.tables["appearances"], ws.tables["spells"],
                                                           ws.bundle.subs, _mid(ws, p), _tid(ws, p),
                                                           ws.bundle.season_pct,
                                                           f"{_t(ws, p)}: unused bench by role family — {_ml(ws, p)}"),
    req={**APP, **SUBS}, params=("team", "match"), note="Unused substitutes after each change.",
    caveat="Availability = named and not yet used; fitness is unknown.")
add("H-180", "Candidate substitute comparison", "Who are the bench options at a chosen moment?",
    lambda ws, p: substitution.candidate_table(_sub_candidates(ws, p)[1], f"{_t(ws, p)}: bench shortlist at "
                                               f"{p.minute:.0f}' — {_ml(ws, p)}"), req={**APP, **SP},
    params=("team", "match", "minute"), cost="medium", note="Ranked bench candidates with evidence and risks.",
    caveat="Candidates are restricted to the match-day bench not yet used at that minute.")
add("H-181", "Substitution candidate score decomposition", "Why is a candidate ranked where he is?",
    lambda ws, p: (manager.candidate_comparison(_sub_candidates(ws, p)[1], ws.cfg.sub_candidate_weights,
                                                f"{_t(ws, p)}: candidate score components at {p.minute:.0f}' — "
                                                f"{_ml(ws, p)}")
                   if _sub_candidates(ws, p)[1] is not None else
                   _empty(str(_sub_candidates(ws, p)[0].get("status")), "Candidate score decomposition")),
    req={**APP, **SP}, params=("team", "match", "minute"), cost="medium",
    note="Role compatibility, intent fit, recent form, sample reliability.")
add("H-182", "Alternative substitution scenario", "What would the heuristic shortlist at a chosen minute?",
    lambda ws, p: substitution.scenario_comparison(_sub_candidates(ws, p)[0]), req={**APP, **SP},
    params=("team", "match", "minute"), cost="medium", note="Counterfactual simulation at the selected minute.",
    caveat="A heuristic shortlist — never a claim about what would have happened.")
add("H-183", "Substitution pattern by manager", "What is the manager's substitution profile?",
    lambda ws, p: manager.manager_sub_profile(ws.bundle.subs, ws.focus_manager(_t(ws, p)) or "",
                                              ws.cfg.sub_timing_bands), req={"subs": ("manager_name", "minute")},
    params=("team",), min_matches=10,
    note="Timing bands × score state for the focus manager.", caveat="Requires at least 10 matches for the manager.")
add("H-184", "Late / early substitution profile", "Which teams change early and which late?",
    lambda ws, p: manager.subs_team_band_heatmap(ws.bundle.subs, ws.cfg.sub_timing_bands), req=SUBS,
    note="Team × timing band share.", caveat="Opponents have two matches each.")
add("H-185", "Manpower-state analysis", "How do changes relate to red cards?",
    lambda ws, p: substitution.manpower_chart(ws.bundle.subs, ws.tables["sending_offs"], _t(ws, p)),
    req={"subs": ("man_advantage",)}, params=("team",), note="Substitutions at level, player-up and player-down.",
    caveat="Very few sending-offs in the dataset.")

# ========================================================================= I · Managerial intelligence
add("I-186", "Formation usage by manager", "Which formations does the manager choose?",
    lambda ws, p: manager.manager_formation_distribution(ws.bundle.team_stats, ws.focus_manager(_t(ws, p)) or ""),
    req={"team_stats": ("manager_name", "starting_formation")}, params=("team",),
    note="Observed starting formations and results.", caveat="Observable choices, not managerial ability.")
add("I-187", "Starting XI continuity and rotation trend", "How many changes between consecutive matches?",
    lambda ws, p: manager.rotation_trend(ws.continuity()[ws.continuity()["team_id"] == _tid(ws, p)], _t(ws, p)),
    req=APP, params=("team",), min_matches=3, note="Lineup changes between consecutive analysed matches.",
    caveat="Cup and European matches between league games are not in the data.")
add("I-188", "Substitution timing profile", "When does the manager make changes?",
    lambda ws, p: substitution.timing_by_group(ws.bundle.subs, _t(ws, p), "timing_band"),
    req={"subs": ("timing_band", "minute")}, params=("team",), note="Minute distribution by timing band.")
add("I-189", "Score-state-specific substitution pattern", "How do changes differ by score state?",
    lambda ws, p: manager.subs_parcats(ws.bundle.subs, _t(ws, p)), req=SUBS, params=("team",),
    note="State → timing → role off → role on.")
add("I-190", "Role-specific substitution tendency", "Which roles are substituted off most?",
    lambda ws, p: substitution.role_tendency(ws.bundle.subs, _t(ws, p)), req={"subs": ("off_role",)},
    params=("team",), note="Share by role with Wilson intervals.")
add("I-191", "Bench utilisation", "How many of the allowed changes are used?",
    lambda ws, p: substitution.bench_utilisation(ws.bundle.subs, ws.bundle.team_stats, _t(ws, p)), req=SUBS,
    params=("team",), note="Substitutions used per match.", caveat="The limit is a configured rule.")
add("I-192", "Response timeline after conceding", "How soon after conceding is the next change made?",
    lambda ws, p: substitution.response_chart(ws.response(), _t(ws, p)), req={**SUBS, **GOALS}, params=("team",),
    note="Minutes from a goal conceded to the next substitution.", caveat="Timing description, not a measured "
    "reaction.")
add("I-193", "Manager comparison small multiples", "How does the focus manager compare with the pooled others?",
    lambda ws, p: (substitution.manager_reference(ws.pooled_reference(_t(ws, p)), ws.focus_manager(_t(ws, p)) or "")
                   if ws.pooled_reference(_t(ws, p)) is not None else _empty("Manager identity unavailable.",
                                                                               "Manager comparison")),
    req=MGR, params=("team",), min_matches=10, note="Indicators next to the pooled value of all other managers.",
    caveat="Other managers have two matches each, all against the focus team.")
add("I-194", "Manager decision evidence cards", "What do the observable decisions add up to?",
    lambda ws, p: substitution.evidence_cards_table(__import__("src.reporting.insight_cards", fromlist=["x"])
                                                    .build_cards(ws, _t(ws, p))), req=TS, params=("team",),
    cost="high", note="Evidence cards with scope and limitation.")
add("I-195", "Manager pattern uncertainty intervals", "How uncertain are per-manager proportions?",
    lambda ws, p: substitution.manager_uncertainty(ws.manager_profiles()), req=MGR,
    note="Wilson intervals and beta-binomial shrinkage.", caveat="Small samples cannot be ranked.")
add("I-196", "Manager by match", "Who was the manager for each analysed match?",
    lambda ws, p: substitution.manager_timeline(ws.bundle.team_stats, _t(ws, p)),
    req={"team_stats": ("manager_name",)}, params=("team",), note="Identity from the matches file.",
    caveat="Tenure outside the analysed matches is not in the data.")
add("I-197", "Tactical change frequency", "How often is the formation changed within matches?",
    lambda ws, p: substitution.tactical_change_frequency(ws.bundle.team_stats, _t(ws, p)),
    req={"team_stats": ("in_match_formation_changes",)}, params=("team",), note="Recorded Tactical Shift changes.")
add("I-198", "Managerial decision audit trail", "What decisions were recorded in a match, in order?",
    lambda ws, p: substitution.decision_audit_trail(ws.bundle.subs, ws.tables["formations"], _mid(ws, p), _t(ws, p)),
    req={**SUBS, **FORM}, params=("team", "match"), note="Substitutions and formation records with context.")

# =============================================================== J · Statistics, inference and uncertainty
_S = dict(req=SP, params=("min_minutes",), min_players=10)
add("J-199", "Pearson correlation matrix", "Which player metrics are linearly related?",
    lambda ws, p: _corr_matrix(ws, p, "pearson"), note="Pairwise-complete n in the hover.", **_S)
add("J-200", "Spearman rank correlation matrix", "Which player metrics are monotonically related?",
    lambda ws, p: _corr_matrix(ws, p, "spearman"), note="Rank-based; robust to skew.", **_S)
add("J-201", "Kendall correlation matrix", "Do the rank relations hold under Kendall's τ?",
    lambda ws, p: _corr_matrix(ws, p, "kendall"), note="Concordance-based.", **_S)
add("J-202", "Correlation forest plot with confidence intervals", "Which match variables are associated with goal "
    "difference?", lambda ws, p: inference.forest_chart(ws.correlations(_t(ws, p)), "goal_diff",
                                                         _team_scope(ws, p)), req=TS, params=("team",), cost="medium",
    min_matches=10, note="Spearman ρ, 2,000 match-level bootstrap resamples, Benjamini–Hochberg.",
    caveat="One team-season: low power; association only.", legacy="gallery/18_correlation_forest.png")
add("J-203", "Pairwise scatter with regression and diagnostics", "How do two player metrics relate, with residuals?",
    lambda ws, p: inference.regression_scatter(_pair(ws, p)[0], p.metric, p.metric_y, _pair(ws, p)[1],
                                               f"players with ≥ {_mm(ws, p):.0f} minutes", hover="player_name",
                                               lowess=True),
    req=SP, params=("metric", "metric_y", "min_minutes"), min_players=10, cost="medium",
    note="OLS line, residual panel, three coefficients; LOESS when statsmodels is installed.")
add("J-204", "Pair plot / scatter matrix", "How do several metrics relate pairwise?",
    lambda ws, p: player.metric_splom(ws.bundle.season_pct, EDA_METRICS[:5], _mm(ws, p)), cost="medium",
    note="Scatter-plot matrix by role family.", **_S)
add("J-205", "Clustered correlation heatmap", "Which metrics form correlated blocks?",
    lambda ws, p: statistical.clustered_correlation(ws.bundle.season_pct, EDA_METRICS, _mm(ws, p)),
    note="Spearman matrix reordered by hierarchical clustering.", **_S)
add("J-206", "Partial correlation", "Do associations with goal difference survive adjusting for venue?",
    lambda ws, p: inference.partial_chart(_partials(ws, p), _team_scope(ws, p)), req=TS, params=("team",),
    min_matches=15, note="Rank partial correlation given home / away.",
    caveat="One observed covariate; unobserved confounding remains.")
add("J-207", "Bootstrap distribution", "How uncertain is a season average?", _bootstrap_metric, req=TS,
    params=("team", "team_metric"), min_matches=8, note="4,000 resamples of matches.")
add("J-208", "Confidence interval forest plot", "Which players are separated once uncertainty is shown?",
    lambda ws, p: scouting.interval_chart(_rate_intervals(ws, p), f"{_t(ws, p)}: xG per 90 with 95% bootstrap "
                                          f"intervals", "xG per 90"), req=PMS, params=("team",), cost="medium",
    min_matches=6, note="Match-level resampling.", caveat="Overlapping intervals are ties.")
add("J-209", "Permutation test null distribution", "Could the home / away gap arise by chance?", _venue_perm, req=TS,
    params=("team", "team_metric"), min_matches=8, cost="medium", note="5,000 label permutations.")
add("J-210", "Group comparison box / violin plots", "How does a team metric differ by venue?",
    lambda ws, p: distribution.box_points(ws.team_matches(_t(ws, p)), p.team_metric, "home_away",
                                          title=f"{_t(ws, p)}: {distribution.nice(p.team_metric)} by venue",
                                          hover="opponent"), req=TS, params=("team", "team_metric"), min_matches=6,
    note="Every match drawn.", legacy="gallery/19_group_comparisons.png")
add("J-211", "Effect-size plot", "How large are the group differences, not just whether they are significant?",
    lambda ws, p: inference.effect_size_chart(ws.group_tests(_t(ws, p))), req=TS, params=("team",), cost="medium",
    min_matches=8, note="Cliff's δ with magnitude bands.", caveat="p-values shown are unadjusted.")
add("J-212", "Kruskal–Wallis post-hoc comparisons", "Which groups differ pairwise?", _posthoc, req=SP,
    params=("metric", "group", "min_minutes"), min_players=10, note="Pairwise Mann–Whitney with BH adjustment.")
add("J-213", "Multiple-testing adjusted p-values", "How many findings survive false-discovery control?",
    lambda ws, p: inference.pvalue_adjust_chart(ws.correlations(_t(ws, p)), _team_scope(ws, p)), req=TS,
    params=("team",), cost="medium", min_matches=10, note="Raw p vs Benjamini–Hochberg q.")
add("J-214", "Power / sensitivity curve", "What size of association can this sample detect?",
    lambda ws, p: inference.power_curve_chart(len(ws.team_matches(_t(ws, p)))), req=TS, params=("team",),
    note="Power of a two-sided correlation test by n.", caveat="Fisher z approximation.")
add("J-215", "Missing-data sensitivity", "Does a result depend on the minutes threshold?",
    lambda ws, p: inference.sensitivity_chart(statistical_tests.sample_sensitivity(
        ws.bundle.season_pct, p.metric, p.metric_y, seed=ws.seed), p.metric, p.metric_y), req=SP,
    params=("metric", "metric_y"), min_players=10, cost="medium", note="Correlation under six inclusion rules.")
add("J-216", "Robust versus non-robust estimates", "Do outliers drive any association?",
    lambda ws, p: inference.robust_chart(statistical_tests.robust_comparison(
        ws.team_matches(_t(ws, p)), "goal_diff", [c for c in ("xg", "xg_against", "shots", "shots_against",
                                                              "possession_proxy_pct", "field_tilt_pct", "ppda")]),
        "goal_diff", _team_scope(ws, p)), req=TS, params=("team",), min_matches=8, note="Pearson vs Spearman.")
add("J-217", "Time trend and autocorrelation", "Is there a trend or run pattern in a team metric?", _acf, req=TS,
    params=("team", "team_metric"), min_matches=12, note="Series, rolling mean and autocorrelation by lag.")
add("J-218", "Partial dependence of the fitted model", "How does the predicted start probability vary with a "
    "feature?", lambda ws, p: model.pdp_ice_chart(ws.pdp(_t(ws, p)), ws.models(_t(ws, p))), req=APP,
    params=("team",), cost="high", min_matches=15, modality="model output", note="PDP with ICE curves.",
    caveat="Only for the model that passed the sample gate.")
add("J-219", "Bootstrap stability plot", "How quickly does an estimate settle as matches accumulate?", _stability,
    req=TS, params=("team", "team_metric"), min_matches=8, note="Estimate and interval using the first n matches.")
add("J-220", "Reliability / calibration plot", "Can the predicted probabilities be trusted as probabilities?",
    lambda ws, p: model.calibration_multi(ws.models(_t(ws, p))), req=APP, params=("team",), cost="high",
    min_matches=15, modality="model output", note="Reliability diagram with bin sizes and Brier score.")

# ============================================================ K · Machine learning and diagnostic plots
_M = dict(req=APP, params=("team",), cost="high", min_matches=15, modality="model output")
add("K-221", "Baseline model comparison", "Do the models beat a simple rule?",
    lambda ws, p: model.model_comparison_bars(ws.models(_t(ws, p)), "f1"),
    note="Expanding-window CV split by match; baseline = started previous match.",
    caveat="Target = start selection of the focus team; nothing generalises beyond this team-season.",
    legacy="gallery/25_model_comparison.png", **_M)
add("K-222", "Confusion matrix", "Which errors does the best model make?",
    lambda ws, p: model.confusion_chart(ws.models(_t(ws, p))), note="Top-11 decision rule on the hold-out.", **_M)
add("K-223", "ROC curve", "How well do the models rank starters?",
    lambda ws, p: model.roc_multi(ws.models(_t(ws, p))), note="Chronological hold-out; baseline as a point.", **_M)
add("K-224", "Precision–recall curve", "What precision is achieved at each recall?",
    lambda ws, p: model.pr_multi(ws.models(_t(ws, p))), note="With the positive-class rate as reference.", **_M)
add("K-225", "Calibration curve", "Are predicted probabilities calibrated?",
    lambda ws, p: model.calibration_multi(ws.models(_t(ws, p))), note="Five probability bins with n.", **_M)
add("K-226", "Brier score comparison", "Which model has the most accurate probabilities?",
    lambda ws, p: model.brier_bars(ws.models(_t(ws, p))), note="Lower is better; base-rate reference shown.", **_M)
add("K-227", "Threshold trade-off chart", "How do precision and recall trade off?",
    lambda ws, p: model.threshold_chart(ws.models(_t(ws, p))), note="Precision, recall and F1 by threshold.", **_M)
add("K-228", "Permutation feature importance", "Which features does the model rely on?",
    lambda ws, p: model.permutation_chart(ws.permutation(_t(ws, p)), ws.models(_t(ws, p))),
    note="Drop in hold-out ROC-AUC, 30 repeats.", caveat="Describes the model, not causal levers.",
    legacy="gallery/26_model_explainability.png", **_M)
add("K-229", "SHAP summary", "How does each feature push individual predictions?",
    lambda ws, p: model.shap_beeswarm(ws.shap(_t(ws, p))), package="shap",
    note="TreeExplainer on gradient boosting, hold-out rows.", legacy="gallery/27_shap_summary.png", **_M)
add("K-230", "SHAP dependence plot", "How does a feature's contribution change with its value?",
    lambda ws, p: model.shap_dependence(ws.shap(_t(ws, p))), package="shap", note="Top feature by mean |SHAP|.", **_M)
add("K-231", "Partial dependence / ICE", "What is the average and individual effect of a feature?",
    lambda ws, p: model.pdp_ice_chart(ws.pdp(_t(ws, p)), ws.models(_t(ws, p))), note="PDP over ICE curves.", **_M)
add("K-232", "Residual distribution", "How are the probability errors distributed?",
    lambda ws, p: model.residual_hist(ws.models(_t(ws, p))), note="Actual − predicted probability, by outcome.", **_M)
add("K-233", "Residual versus fitted plot", "Is the model systematically off in some probability range?",
    lambda ws, p: model.residual_vs_fitted(ws.models(_t(ws, p))), note="Binned residuals with ±1.96 SE.", **_M)
add("K-234", "Error by subgroup", "For which role families is the model worse?",
    lambda ws, p: model.subgroup_error_chart(ws.models(_t(ws, p))), note="Error rate by role family.", **_M)
add("K-235", "Learning curve", "Would more matches help?",
    lambda ws, p: model.learning_curve_chart(ws.models(_t(ws, p))), note="Training and hold-out AUC by training "
    "matches.", **_M)
add("K-236", "Cross-validation score distribution", "How variable are the scores across folds?",
    lambda ws, p: model.cv_distribution_chart(ws.models(_t(ws, p)), "f1"), note="One point per time-ordered fold.", **_M)
_C = dict(req=SP, min_players=20, cost="medium")
add("K-237", "PCA scree plot", "How many dimensions do player profiles have?",
    lambda ws, p: model.scree_chart(ws.pca()), note="Explained variance with cumulative curve.",
    legacy="gallery/21_pca_scree_loadings.png", **_C)
add("K-238", "PCA loading plot", "Which metrics define each component?",
    lambda ws, p: model.loadings_heatmap(ws.pca()), note="Loadings of the first four components.", **_C)
add("K-239", "PCA player map", "Where do players sit in the reduced space?",
    lambda ws, p: model.pca_map(ws.pca(), _t(ws, p)), params=("team",), note="PC1 × PC2 by role family.", **_C)
add("K-240", "Cluster model selection", "How many clusters does the data support?",
    lambda ws, p: model.cluster_selection_chart(ws.clusters()), note="Elbow, silhouette, Davies–Bouldin, GMM BIC.",
    legacy="gallery/22_clustering_model_selection.png", **_C)
add("K-241", "Cluster projection and profile", "What separates the clusters?",
    lambda ws, p: model.cluster_profile_chart(ws.clusters()), note="Sizes and ε² per metric.",
    legacy="gallery/24_cluster_profiles.png", **_C)
add("K-242", "Cluster stability / ARI comparison", "Do different algorithms and resamples agree?",
    lambda ws, p: model.ari_heatmap(ws.clusters()), note="Adjusted Rand index between four algorithms.",
    legacy="gallery/23_clustering_comparison.png", **_C)
add("K-243", "Outlier / anomaly score chart", "Which players have the most unusual profiles?",
    lambda ws, p: model.outlier_chart(ws.outliers()), note="Isolation-forest score.",
    caveat="Unusual is not better or worse.", **_C)
add("K-244", "Forecast residuals", "How accurate is a forecast of future results?", modality="model output",
    reason="Forecasting is not justified: 34 matches of one team give no temporal depth for a held-out forecast "
           "horizon, and no out-of-sample season exists in the data.")

# ============================================= L · Additional project charts and composite dashboards
add("L-245", "Dataset coverage cards", "What is the real scale of the dataset?",
    lambda ws, p: match.coverage_cards(dataset_scale(ws.tables, ws.bundle.manifest
                                                     if ws.bundle.manifest is not None else pd.DataFrame())),
    req={"events": ("event_id",), "manifest": ("bytes", "status")}, note="Rows, files and bytes actually read.")
add("L-246", "Event taxonomy treemap", "What is the event stream made of?",
    lambda ws, p: match.event_type_treemap(ws.tables["events"]), req={"events": ("type",)},
    note="Events by family and type.")
add("L-247", "Event volume per match", "How many events of each family does a match produce?",
    lambda ws, p: match.events_per_match_chart(ws.tables["events"], ws.tables["matches"]), req={"events": ("type",)},
    note="Stacked event counts per match.")
add("L-248", "Cumulative xG of a match", "How did chance quality accumulate in a match?",
    lambda ws, p: match.cumulative_xg_chart(cumulative_xg(ws.flags, _mid(ws, p)), f"Cumulative xG — {_ml(ws, p)}"),
    req=SHOT, params=("team", "match"), note="Step chart of StatsBomb xG by team.")
add("L-249", "Match xG-by-interval chart", "In which spells of the match were chances created?",
    lambda ws, p: match.match_momentum(ws.flags, ws.tables["goals"], _mid(ws, p),
                                       title=f"xG by 5-minute interval — {_ml(ws, p)}"), req={**SHOT, **GOALS},
    params=("team", "match"), note="xG per 5-minute bucket for each side, with final-third touch share.",
    caveat="This is xG per interval, not a validated momentum measure.")
add("L-250", "On-pitch Gantt chart", "Who was on the pitch when?",
    lambda ws, p: match.on_pitch_gantt(ws.tables["spells"], ws.tables["goals"], _mid(ws, p), _tid(ws, p),
                                       f"{_t(ws, p)}: time on pitch — {_ml(ws, p)}"), req={**SPELLS, **GOALS},
    params=("team", "match"), note="Reconstructed on-pitch spells with goals marked.")
add("L-251", "Goals and chances by match phase", "In which phases of matches are goals and chances concentrated?",
    lambda ws, p: match.phase_profile(ws.flags, ws.tables["goals"], ws.bundle.team_stats, _t(ws, p),
                                      ws.cfg.match_phases), req={**SHOT, **GOALS}, params=("team",),
    note="Season totals by 15-minute phase.")
add("L-252", "Opponent bubbles", "Against whom were chances created and conceded?",
    lambda ws, p: match.opponent_bubbles(ws.bundle.team_stats, _t(ws, p)), req=TS, params=("team",),
    note="xG for vs against per opponent.", caveat="Two meetings per opponent.")
add("L-253", "Shot-quality distribution for and against", "How does shot quality compare for and against?",
    lambda ws, p: match.xg_distribution(ws.flags, _t(ws, p), ws.match_ids(_t(ws, p))), req=SHOT, params=("team",),
    note="xG-per-shot distributions with conversion.", legacy="gallery/17_scoring_and_goalkeeping.png")
add("L-254", "Squad similarity dendrogram", "Which squad members have similar statistical profiles?",
    lambda ws, p: player.player_dendrogram(ws.bundle.season_pct, _t(ws, p), EDA_METRICS, 450), req=SP,
    params=("team",), note="Complete-linkage clustering of standardised profiles.")
add("L-255", "Action-mix ternary plot", "What mix of creating, progressing and defending does each player have?",
    lambda ws, p: player.action_ternary(ws.bundle.season_pct, _mm(ws, p), _t(ws, p)), req=SP,
    params=("team", "min_minutes"), note="Share of per-90 actions in three families.")
add("L-256", "Player × match contribution matrix", "In which matches did each player contribute chances?",
    lambda ws, p: player.contribution_matrix(ws.bundle.pms, ws.tables["matches"], _t(ws, p)),
    req={"pms": ("xg", "xa")}, params=("team",), note="xG + xA by player and match.")
add("L-257", "Minutes sunburst", "How is playing time distributed across roles and players?",
    lambda ws, p: player.minutes_sunburst(ws.bundle.season, _t(ws, p)), req={"season": ("minutes_played",)},
    params=("team",), note="Role family → role → player by minutes.")
add("L-258", "Split violin: squad versus others", "How does the squad compare with the other players in the data?",
    lambda ws, p: player.split_violin(ws.bundle.season_pct, p.metric, _t(ws, p), _mm(ws, p)), req=SP,
    params=("team", "metric", "min_minutes"), min_players=10, note="Squad (left) vs others (right) by role family.",
    caveat="Others are observed only in their matches against the focus team.")
add("L-259", "Scatter with marginal distributions", "How do two metrics relate, with their distributions?",
    lambda ws, p: player.marginal_scatter(ws.bundle.season_pct, p.metric, p.metric_y, _mm(ws, p)), req=SP,
    params=("metric", "metric_y", "min_minutes"), min_players=10, note="Marginal histogram and box plot.")
add("L-260", "Key-pass map", "Where do the passes that lead to shots come from?",
    lambda ws, p: pitch.key_pass_map(ws.flags[ws.flags["match_id"].isin(ws.match_ids(_t(ws, p)))], _tid(ws, p),
                                     f"{_t(ws, p)}: key passes"), req=PASS, params=("team",),
    note="Pass origin → shot location; amber = assist.")
add("L-261", "Pass destination density", "Where do a player's completed passes end?",
    lambda ws, p: pitch.pass_destination_density(ws.flags, _pid(ws, p), f"{_pname(ws, p)}: where his completed "
                                                 f"passes end"), req=PASS, params=("team", "player"),
    note="Density of end locations.")
add("L-262", "Points versus expected points", "Did results run ahead of or behind chance quality?",
    lambda ws, p: team.xpts_chart(ws.xpts(), _t(ws, p)), req={**TS, **SHOT}, params=("team",), cost="medium",
    note="Shot-level Bernoulli simulation (5,000 runs per match).", caveat="xPts is a model output.")
add("L-263", "Expected Threat surface", "Which areas of the pitch carry the most threat in these matches?",
    lambda ws, p: spatial.xt_surface(ws.xt_grid()), req=EVE, cost="medium", modality="model output",
    note="Project-computed xT, 16 × 12 grid, value iteration.", caveat="Fitted in-sample on the analysed matches; "
    "not a StatsBomb field.")
add("L-264", "xT added by player", "Who moves the ball into more threatening areas?",
    lambda ws, p: scouting.xt_bars(ws.player_xt(), _t(ws, p)), req=EVE, params=("team",), cost="medium",
    modality="model output", note="xT(end) − xT(start) of completed passes and carries.",
    caveat="Derived project value on an in-sample grid.")
add("L-265", "Pass-flow map", "What is the typical pass direction from each zone?",
    lambda ws, p: static_pitch.pass_flow(_team_ev(ws, p, "Passes"), f"{_t(ws, p)}: pass flow"), req=PASS,
    params=("team",), lib="mplsoccer", package="mplsoccer", note="Mean pass direction per zone.")
add("L-266", "Percentile pizza chart", "What is a player's percentile profile in a compact form?",
    lambda ws, p: static_pitch.pizza(ws.bundle.season_pct, _pid(ws, p), radar_metrics(_role(ws, p), ws.cfg),
                                     [label(m) for m in radar_metrics(_role(ws, p), ws.cfg)]), req=SP,
    params=("team", "player"), lib="mplsoccer", package="mplsoccer", note="Role-group percentiles; all slices "
    "higher = higher percentile.")
add("L-267", "Shortlist versus actual XI over the season", "How close is the pre-match shortlist to the manager's "
    "choices?", lambda ws, p: lineup.xi_agreement_chart(ws.xi_agreement(_t(ws, p)), _t(ws, p)), req={**SP, **APP},
    params=("team",), cost="high", min_matches=4, note="Share of the actual XI also shortlisted, per match.",
    caveat="Agreement is similarity, not quality.")
add("L-268", "Two formation shortlists compared", "How does the shortlist change under another formation?",
    _alt_formations, req={**SP, **APP}, params=("team", "match", "formation"), cost="high", min_matches=2,
    note="Slot scores under two templates.")
add("L-269", "Minimum-minutes sensitivity", "How many players survive each minutes threshold?",
    lambda ws, p: statistical.threshold_sensitivity_chart(ws.bundle.season), req={"season": ("minutes_played",)},
    note="Eligible players by threshold.")
add("L-270", "Key players radar grid", "What do the most-used players look like at a glance?",
    lambda ws, p: player.radar_grid(ws.bundle.season_pct, ws.squad(_t(ws, p)).pipe(
        lambda d: d[d["primary_role"] != "GK"])["player_id"].head(6).tolist(), ws.cfg), req=SP, params=("team",),
    note="Role-specific percentile radars for six players.")
add("L-271", "Player dashboard", "What is one player's complete evidence view?",
    lambda ws, p: dashboards.player_dashboard(ws.bundle.season_pct, ws.bundle.pms, ws.flags, _pid(ws, p), ws.cfg),
    req=SP, params=("team", "player"), cost="medium", note="Composite of profile, form and maps.",
    legacy="gallery/interactive/player_dashboard.html")
add("L-272", "Match dashboard", "What is one match's complete evidence view?",
    lambda ws, p: dashboards.match_dashboard(ws.flags, ws.tables["goals"], ws.tables["matches"], _mid(ws, p)),
    req={**SHOT, **GOALS}, params=("team", "match"), cost="medium", note="Composite of shots, xG and territory.",
    legacy="gallery/interactive/match_dashboard.html")
add("L-273", "Substitution dashboard", "What is the team's substitution behaviour at a glance?",
    lambda ws, p: dashboards.substitution_dashboard(ws.bundle.subs, _t(ws, p), ws.cfg.sub_timing_bands), req=SUBS,
    params=("team",), cost="medium", note="Composite of timing, state and role flow.",
    legacy="gallery/interactive/substitution_dashboard.html")
add("L-274", "Goals scored and conceded by origin", "How are goals scored and conceded?",
    lambda ws, p: team.goal_origin_bars(desc.goals_breakdown(ws.bundle, _t(ws, p)), _t(ws, p)),
    req={**GOALS, "events": ("play_pattern", "shot_body_part")}, params=("team",), note="By play pattern and body "
    "part.")
add("L-275", "Goalkeeping reference", "How do goalkeepers compare on shots faced?",
    lambda ws, p: team.goalkeeping_chart(desc.goalkeeping_proxy(ws.bundle)),
    req={"events": ("shot_xg", "outcome"), "appearances": ("match_role",)},
    note="Pre-shot xG of on-target shots faced minus goals conceded.",
    caveat="No post-shot xG exists in the source: a crude reference on small samples.")
add("L-276", "Three correlation methods compared", "Do Pearson, Spearman and Kendall agree?",
    lambda ws, p: inference.method_agreement_heatmap(ws.correlations(_t(ws, p)), "goal_diff", _team_scope(ws, p)),
    req=TS, params=("team",), cost="medium", min_matches=10, note="Three coefficients per variable.")
add("L-277", "Four clustering algorithms projected", "Do different algorithms find the same groups?",
    lambda ws, p: model.cluster_projection_chart(ws.clusters()), req=SP, min_players=20, cost="medium",
    note="K-Means, Ward, GMM and DBSCAN labels in PCA space.")
add("L-278", "Cluster stability under resampling", "Does the grouping survive resampling of players?",
    lambda ws, p: model.stability_hist(ws.cluster_stability(), ws.clusters()["k_best"]) if ws.clusters() else
    _empty("Too few eligible players for clustering.", "Cluster stability"), req=SP, min_players=20, cost="high",
    note="ARI of 40 bootstrap refits against the full-sample partition.")
