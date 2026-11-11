"""Model Evaluation: the one supervised target the data support, evaluated against a baseline with leakage controls."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analytics import models
from src.dashboard import components as ui
from src.dashboard import filters, layout, state

base, ws, tm = layout.start("Model Evaluation", "Is any predictive model justified by this data — and if so, does "
                            "it beat a simple rule on held-out matches?", eyebrow="Evidence")
if layout.empty_scope(tm):
    st.stop()

team = st.session_state["f_team"]
p = state.params(ws)

st.markdown("#### What is modelled, and what is not")
left, right = st.columns([0.5, 0.5])
with left:
    st.markdown(f"**Supported target — start selection.** {models.TARGET_DEFINITION}")
    st.markdown("**Positive class:** started the match. **Baseline:** the player started the team's previous "
                "match. **Split:** by match, in date order — training matches always precede test matches, so no "
                "future information reaches a prediction and no squad member of a test match is seen in training "
                "for that match.")
with right:
    st.markdown("**Targets that are not modelled**")
    st.dataframe(pd.DataFrame(models.UNSUPPORTED_TARGETS, columns=["target", "why not"]), hide_index=True,
                 width="stretch")

section = filters.view_select("Section", ["Supervised: start selection", "Unsupervised: player profiles"],
                              key="w_model_section")

if section == "Supervised: start selection":
    st.caption("Fitting three classifiers under time-ordered cross-validation takes about five seconds.")
    if not st.toggle("Fit and evaluate the models", key="w_model_fit"):
        st.info("Switch the toggle on to fit the models on the matches in scope.")
        layout.footer()
        st.stop()
    with st.spinner("Fitting models with expanding-window cross-validation…"):
        res = ws.models(team)
    g = res["gate"]
    ui.kpi_row([
        ("Rows (squad member × match)", f"{g['rows']}", f"minimum {g['min_rows']}"),
        ("Matches", f"{g['matches']}", f"minimum {g['min_matches']}"),
        ("Starters", f"{g['class_balance_starter_pct']}%", "Share of the positive class."),
        ("Sample gate", "passed" if res["fitted"] else "NOT met", None),
    ], per_row=4)
    if not res["fitted"]:
        st.warning(f"Not statistically supportable: {res['reason']} Widen the filters or use the full season. "
                   f"Descriptive analysis remains available on the other pages.")
        layout.footer()
        st.stop()
    s = res["split"]
    st.caption(f"Chronological hold-out: train on {s['train_matches']} matches up to {s['train_until']:%d %b %Y} "
               f"({s['train_rows']} rows), test on {s['test_matches']} matches from {s['test_from']:%d %b %Y} "
               f"({s['test_rows']} rows, {s['test_positive_rate']:.0%} starters). Best model on the hold-out: "
               f"**{res['best']}**.")
    view = filters.view_select("View", ["Comparison", "Discrimination", "Calibration and errors", "Explainability",
                                        "Learning curve", "Leakage audit"], key="w_model_view")
    if view == "Comparison":
        left, right = st.columns(2)
        with left:
            ui.chart("K-221", ws, p, key="mo_cmp")
        with right:
            ui.chart("K-236", ws, p, key="mo_cv")
        cs = res["cv_summary"].copy()
        cs.columns = [f"{a} ({b})" for a, b in cs.columns]
        ui.table(cs.reset_index(), "cv_summary", key="mo_cv_tbl", decimals=3)
        ui.table(res["holdout"], "holdout_metrics", key="mo_hold_tbl", decimals=3)
        st.caption("Scores are means across five time-ordered folds; with so few folds, differences smaller than "
                   "the fold-to-fold spread are not meaningful.")
    elif view == "Discrimination":
        left, right = st.columns(2)
        with left:
            ui.chart("K-223", ws, p, key="mo_roc")
        with right:
            ui.chart("K-224", ws, p, key="mo_pr")
        left, right = st.columns(2)
        with left:
            ui.chart("K-222", ws, p, key="mo_cm")
        with right:
            ui.chart("K-227", ws, p, key="mo_thr")
    elif view == "Calibration and errors":
        left, right = st.columns(2)
        with left:
            ui.chart("K-225", ws, p, key="mo_cal")
        with right:
            ui.chart("K-226", ws, p, key="mo_brier")
        left, right = st.columns(2)
        with left:
            ui.chart("K-232", ws, p, key="mo_res")
        with right:
            ui.chart("K-233", ws, p, key="mo_resfit")
        ui.chart("K-234", ws, p, key="mo_sub")
    elif view == "Explainability":
        layout.note("Explanations describe how the fitted model uses its features. Correlated features share "
                    "credit, and nothing here is a causal lever a manager could pull.")
        left, right = st.columns(2)
        with left:
            ui.chart("K-228", ws, p, key="mo_perm")
        with right:
            ui.chart("K-231", ws, p, key="mo_pdp")
        left, right = st.columns(2)
        with left:
            ui.chart("K-229", ws, p, key="mo_shap")
        with right:
            ui.chart("K-230", ws, p, key="mo_shapdep")
    elif view == "Learning curve":
        ui.chart("K-235", ws, p, key="mo_lc")
        ui.table(res["learning_curve"], "learning_curve", key="mo_lc_tbl", decimals=3)
    else:
        st.markdown("Every feature is computed from matches **before** the one being predicted:")
        st.dataframe(res["leakage_audit"], hide_index=True, width="stretch")
else:
    st.caption("Unsupervised structure of per-90 player profiles for outfield players above the minutes threshold "
               "configured for the analysis. Clustering takes a few seconds.")
    if not st.toggle("Run PCA and the clustering comparison", key="w_model_unsup"):
        st.info("Switch the toggle on to compute the projections and clusters.")
        layout.footer()
        st.stop()
    view = filters.view_select("View", ["PCA", "Cluster selection", "Algorithm agreement", "Stability and outliers"],
                               key="w_unsup_view")
    if view == "PCA":
        left, right = st.columns(2)
        with left:
            ui.chart("K-237", ws, p, key="mo_scree")
        with right:
            ui.chart("K-238", ws, p, key="mo_load")
        ui.chart("K-239", ws, p, key="mo_pcamap")
    elif view == "Cluster selection":
        ui.chart("K-240", ws, p, key="mo_sel")
        ui.chart("K-241", ws, p, key="mo_prof")
    elif view == "Algorithm agreement":
        ui.chart("L-277", ws, p, key="mo_proj")
        ui.chart("K-242", ws, p, key="mo_ari")
    else:
        left, right = st.columns(2)
        with left:
            ui.chart("L-278", ws, p, key="mo_stab")
        with right:
            ui.chart("K-243", ws, p, key="mo_out")
layout.footer()
