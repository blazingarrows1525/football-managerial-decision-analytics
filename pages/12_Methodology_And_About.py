"""Methodology & About: questions, definitions, assumptions, boundaries and how to reproduce every number."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import FEATURE_VERSION, PARSER_VERSION, SCHEMA_VERSION
from src.dashboard import components as ui
from src.dashboard import filters, layout
from src.data import provenance
from src.reporting import exports, report_builder
from src.visualization import registry

base, _, tm = layout.start("Methodology & About", "What is this project, how is each number produced and where "
                           "does the evidence stop?", eyebrow="Reference")
ws = base
m = ws.tables["matches"]

view = filters.view_select("View", ["Research design", "Metrics and formulas", "Decision-support methods",
                                    "Boundaries and limitations", "Reproduce", "Versions"], key="w_about_view")

if view == "Research design":
    st.markdown(
        "#### Core question\n"
        "How can real football event, lineup, player and match-state data be turned into transparent, interactive "
        "evidence that supports starting-XI selection, role fit, tactical interpretation, substitution choices, "
        "rotation analysis and the review of observable managerial decisions?\n\n"
        "#### What kind of analysis this is\n"
        f"A **static analysis of a historical dataset**: {m['competition_name'].iloc[0]} "
        f"{m['season_name'].iloc[0]}, {len(m)} matches from {m['match_date'].min():%d %B %Y} to "
        f"{m['match_date'].max():%d %B %Y}, every one involving {ws.focus}. Nothing in this application is live or "
        "real-time, and nothing is refreshed on a schedule.\n\n"
        "#### Research questions\n"
        "1. Which attributes distinguish roles, and how should players be compared like-for-like?\n"
        "2. How do results relate to chance quality, and how certain is that?\n"
        "3. How does the team build play, and through whom?\n"
        "4. Which eleven does the pre-match evidence shortlist, and how close is that to observed selections?\n"
        "5. When and in which situations are substitutions made, and who replaces whom?\n"
        "6. Which managerial patterns are observable, and how much do small samples support?\n"
        "7. Which statistical claims survive effect sizes, intervals and multiple-testing control?\n"
        "8. Is any predictive model justified at this sample size?\n\n"
        "#### How every chapter is structured\n"
        "Research question → data and method → chart → interpretation → managerial implication and limitation. "
        "The same shared code (`src/`) produces the numbers in the notebooks and in this dashboard.")
elif view == "Metrics and formulas":
    st.markdown("Count metrics are defined in the metric dictionary (Data Quality & Sources → Schema and "
                "dictionary). Derived metrics and scores:")
    ui.table(pd.DataFrame(report_builder.DERIVED_METRICS, columns=["metric", "formula", "denominator / inputs",
                                                                   "interpretation and caveat"]),
             "derived_metrics", key="ab_metrics", height=560)
    st.markdown(
        "#### Normalisation rules\n"
        "- **Per 90** = value / minutes × 90, where minutes are reconstructed from the event stream. Values are "
        "null below the minimum-minutes threshold in the sidebar.\n"
        "- **Percentiles** are computed inside the player's role group (falling back to the role family when the "
        "group is too small, and flagged).\n"
        "- **Team rates** such as pass completion are weighted (sum of numerators / sum of denominators), not "
        "averages of match percentages, unless a chart says 'mean per match'.\n"
        "- **Coordinates** are StatsBomb's 120 × 80 frame; every team attacks left to right in both halves.")
elif view == "Decision-support methods":
    st.markdown(
        "#### Starting XI shortlist\n"
        "Candidates are the squad members seen in recent match-day squads before the decision point. For each "
        "formation slot a candidate's score is\n\n"
        "`(w₁·role fit + w₂·recent form + w₃·evidence volume + w₄·minutes-based exposure + w₅·continuity) × "
        "position compatibility`\n\n"
        "with every component on 0–100 and the weights adjustable in the lab. The assignment of players to slots "
        "maximises the total with the Hungarian algorithm under hard constraints: eleven distinct players, one "
        "goalkeeper, every pick eligible for his slot role, all from the squad pool. It is a transparent "
        "heuristic — *best under the stated weights and constraints* — not a validated optimum.\n\n"
        "#### Substitution shortlist\n"
        "At a chosen minute the context is rebuilt from the event chronology: score, manpower, substitutions and "
        "windows used, who is on the pitch and who is on the bench and unused. Outgoing candidates are ranked by "
        "minutes played, a yellow card and involvement relative to the player's own baseline; incoming candidates "
        "by role compatibility, fit to the tactical intent, recent form and evidence volume. Scenarios are "
        "**counterfactual simulations**, never statements about what would have happened.\n\n"
        "#### Backtests\n"
        "Both tools are compared with what actually happened (share of the actual XI also shortlisted; whether the "
        "actual incoming player was in the top three). Agreement measures similarity to observed decisions, not "
        "their quality.\n\n"
        "#### Statistics\n"
        "Rank-based methods by default (Spearman, Mann–Whitney, Kruskal–Wallis) because the metrics are skewed; "
        "effect sizes (Cliff's δ, ε²) and bootstrap intervals next to every p-value; Benjamini–Hochberg control "
        "when a family of tests is run; resampling at the level of the independent unit (matches or players).\n\n"
        "#### Models\n"
        "One supervised target passes the sample gate: start selection. It is evaluated against a naive baseline "
        "with splits by match in date order. Match-result, goals, injury and value models are not attempted.")
elif view == "Boundaries and limitations":
    st.markdown("#### What the data contain and do not contain")
    from src.visualization import audit

    ui.table(audit.feature_availability_table(ws.bundle), "feature_availability", key="ab_feat")
    st.markdown("#### Limitations")
    for t in provenance.DATA_LIMITATIONS:
        st.markdown(f"- {t}")
    st.markdown(
        "- Thirty-four matches of one team: low statistical power, and nothing generalises to other teams or "
        "seasons.\n"
        "- xG, expected points and Expected Threat are model outputs.\n"
        "- Every relationship shown is an association. No causal design is available.\n"
        "- A pandas pipeline is the right tool at this volume (about 138 thousand events). No distributed engine "
        "is used or claimed.")
    st.markdown("#### Charts that cannot be built from this data")
    table = registry.status_table(ws)
    na = table[table["status"] != registry.IMPLEMENTED_AVAILABLE][["chart_id", "name", "status", "reason"]]
    ui.table(na, "unavailable_charts", key="ab_na")
elif view == "Reproduce":
    st.markdown(
        "```bash\n"
        "pip install -r requirements.txt\n"
        "streamlit run app.py                      # this dashboard\n"
        "python scripts/build_reports.py           # manifest, catalogue, data dictionary, report\n"
        "python scripts/build_notebooks.py         # regenerate the research notebooks\n"
        "python scripts/run_notebooks.py           # execute them in a clean kernel\n"
        "pytest                                    # test suite (synthetic fixtures; real data when cached)\n"
        "```\n"
        "The first run downloads 70 JSON files (about 120 MB) from the official StatsBomb repository into "
        "`data/raw/` and caches the parsed tables as Parquet under `data/processed/`. Both folders are "
        "git-ignored: the licence does not allow redistribution.\n\n"
        "#### Where to read more\n"
        "- `notebooks/` — seven research chapters and one complete combined notebook, built on the same `src/` package\n"
        "- `football_managerial_analytics_enhanced.ipynb` — the preserved, self-contained notebook from the "
        "previous version\n"
        "- `docs/` — architecture, methodology, data dictionary, provenance, visualization catalogue, deployment, "
        "review evidence and viva questions\n"
        "- `artifacts/reports/ANALYSIS_REPORT_V3.md` — the written report generated from the current data")
    st.markdown("#### Attribution")
    st.markdown(f"{provenance.STATSBOMB_ATTRIBUTION} {provenance.ATTRIBUTION_REQUIREMENT}")
else:
    env = report_builder.environment()
    left, right = st.columns(2)
    with left:
        st.markdown("#### Package versions in this environment")
        st.dataframe(pd.DataFrame(list(env.items()), columns=["component", "version"]), hide_index=True,
                     width="stretch")
    with right:
        st.markdown("#### Data-model versions")
        st.dataframe(pd.DataFrame([("parser", PARSER_VERSION), ("schema", SCHEMA_VERSION),
                                   ("features", FEATURE_VERSION),
                                   ("chart registry schema", registry.REGISTRY_SCHEMA_VERSION)],
                                  columns=["component", "version"]), hide_index=True, width="stretch")
        st.markdown("#### Export capabilities (checked)")
        cap = exports.capabilities()
        st.dataframe(pd.DataFrame([(k, str(v)) for k, v in cap.items()], columns=["capability", "value"]),
                     hide_index=True, width="stretch")
layout.footer()
