"""Statistical Explorer: correlations, group tests, uncertainty and power — with sample sizes on everything."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analytics import statistical_tests as stt
from src.dashboard import components as ui
from src.dashboard import filters, layout, state

base, ws, tm = layout.start("Statistical Explorer", "Which relationships are in the data, how large are they, and "
                            "how much of that could be chance?", eyebrow="Evidence")
if layout.empty_scope(tm):
    st.stop()

team = st.session_state["f_team"]
threshold = float(st.session_state["f_min_minutes"])
layout.note("<b>Correlation is not causation.</b> Player-level results use the players above the minutes threshold "
            "(each player once); match-level results use the team's matches in scope (each match once). Events are "
            "never treated as independent observations.")
layout.low_sample_note(len(tm), 10)

view = filters.view_select("View", ["Metric pair", "Correlation matrices", "Match-level associations", "Group tests",
                                    "Uncertainty", "Power and sensitivity"], key="w_stat_view")

if view == "Metric pair":
    a, b, c = st.columns(3)
    with a:
        x = filters.metric_select("w_stat_x", "X metric", default="xg_p90")
    with b:
        y = filters.metric_select("w_stat_y", "Y metric", default="key_passes_p90")
    cohort = c.selectbox("Cohort", ["All eligible players", "Defender", "Midfielder", "Forward"], key="w_stat_cohort")
    el = ws.eligible(threshold)
    if cohort != "All eligible players":
        el = el[el["role_family"] == cohort]
    res = stt.pair_correlation(el, x, y, seed=ws.seed)
    if res.get("status") != "ok":
        st.warning(f"{res.get('status')} — n = {res['n']} complete pairs in this cohort.")
    else:
        ui.kpi_row([
            ("Complete pairs (n)", f"{res['n']}", "Players with both metrics present; missing values change n."),
            ("Pearson r", f"{res['pearson_r']:.2f}", f"p = {res['pearson_p']:.3f} · linear association"),
            ("Spearman ρ", f"{res['spearman_rho']:.2f}", f"p = {res['spearman_p']:.3f} · rank association"),
            ("95% CI for ρ", f"{res['rho_ci_low']:.2f} to {res['rho_ci_high']:.2f}", "2,000 bootstrap resamples of "
                                                                                     "players."),
            ("Kendall τ", f"{res['kendall_tau']:.2f}", f"p = {res['kendall_p']:.3f}"),
        ], per_row=5)
        from src.visualization import inference, registry
        from src.visualization.theme import finalize

        fig = inference.regression_scatter(el, x, y, res, f"{cohort.lower()} with ≥ {threshold:.0f} minutes",
                                           hover="player_name", lowess=True)
        ui.show(finalize(fig, registry.scope_text(ws), synthetic=ws.synthetic, attribution=registry.attribution_text(ws)), key="st_pair")
        left, right = st.columns(2)
        with left:
            fig = inference.bootstrap_hist(res["boot"], res["spearman_rho"], "Bootstrap distribution of Spearman ρ",
                                           "Spearman ρ", f"n = {res['n']} players resampled")
            ui.show(finalize(fig, registry.scope_text(ws), synthetic=ws.synthetic, attribution=registry.attribution_text(ws)), key="st_pair_boot")
        with right:
            ui.chart("J-215", ws, state.params(ws, metric=x, metric_y=y), key="st_sens")
elif view == "Correlation matrices":
    method = st.selectbox("Method", ["spearman", "pearson", "kendall"], key="w_stat_method",
                          help="Pearson: linear. Spearman and Kendall: rank-based, robust to skew and outliers.")
    ids = {"pearson": "J-199", "spearman": "J-200", "kendall": "J-201"}
    ui.chart(ids[method], ws, state.params(ws), key="st_matrix")
    left, right = st.columns(2)
    with left:
        ui.chart("J-205", ws, state.params(ws), key="st_cluster")
    with right:
        st.markdown("**Normality diagnostics** (guides the choice of method)")
        from src.workspace import EDA_METRICS

        ui.table(stt.normality_table(ws.eligible(threshold), EDA_METRICS), "normality", key="st_norm", decimals=3)
    if st.toggle("Show the scatter-plot matrix (heavier chart)", key="w_stat_splom"):
        ui.chart("J-204", ws, state.params(ws), key="st_splom")
elif view == "Match-level associations":
    corr = ws.correlations(team)
    if corr.empty:
        st.info("At least six matches with varying values are needed.")
    else:
        ui.chart("J-202", ws, state.params(ws), key="st_forest")
        left, right = st.columns(2)
        with left:
            ui.chart("J-213", ws, state.params(ws), key="st_fdr")
        with right:
            ui.chart("L-276", ws, state.params(ws), key="st_methods")
        left, right = st.columns(2)
        with left:
            ui.chart("J-216", ws, state.params(ws), key="st_robust")
        with right:
            ui.chart("J-206", ws, state.params(ws), key="st_partial")
        ui.table(corr, "match_level_correlations", key="st_corr_tbl", decimals=3)
elif view == "Group tests":
    a, b = st.columns(2)
    with a:
        tmetric = filters.metric_select("w_stat_tmetric", "Team metric (per match)", filters.TEAM_METRICS)
    pt = state.params(ws, team_metric=tmetric)
    left, right = st.columns(2)
    with left:
        ui.chart("J-210", ws, pt, key="st_box")
    with right:
        ui.chart("J-209", ws, pt, key="st_perm")
    ui.chart("J-211", ws, pt, key="st_effect")
    tests = ws.group_tests(team)
    if tests:
        ui.table(pd.DataFrame(tests), "group_tests", key="st_tests_tbl", decimals=3)
    st.markdown("**Across role families** (player level)")
    with b:
        pmetric = filters.metric_select("w_stat_pmetric", "Player metric", default="progressive_passes_p90")
    ui.chart("J-212", ws, state.params(ws, metric=pmetric, group="role_family"), key="st_posthoc")
elif view == "Uncertainty":
    tmetric = filters.metric_select("w_unc_tmetric", "Team metric (per match)", filters.TEAM_METRICS)
    pt = state.params(ws, team_metric=tmetric)
    left, right = st.columns(2)
    with left:
        ui.chart("J-207", ws, pt, key="st_boot")
    with right:
        ui.chart("J-219", ws, pt, key="st_stab")
    ui.chart("J-208", ws, state.params(ws), key="st_ci")
else:
    left, right = st.columns(2)
    with left:
        ui.chart("J-214", ws, state.params(ws), key="st_power")
    with right:
        tmetric = filters.metric_select("w_acf_tmetric", "Team metric (per match)", filters.TEAM_METRICS)
        ui.chart("J-217", ws, state.params(ws, team_metric=tmetric), key="st_acf")
    n = len(tm)
    if n > 3:
        mdr = float(stt.min_detectable_correlation(n))
        st.markdown(f"With **n = {n}** matches, a two-sided test at α = 0.05 detects a true correlation of "
                    f"**|r| ≥ {mdr:.2f}** with 80% power. Weaker real associations will usually be missed, so a "
                    f"non-significant result here is not evidence of no relationship.")
layout.footer()
