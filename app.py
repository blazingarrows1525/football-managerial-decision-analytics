"""Football Managerial Decision Analytics — Streamlit entry point.

Run from the repository root:

    streamlit run app.py

The entry point only configures the page and the navigation. Data loading, analytics and charts live in
``src/`` and are shared with the notebooks.
"""
from __future__ import annotations

import streamlit as st

from src.dashboard import layout, state

layout.configure_page()
state.persist_widget_state()  # selections survive navigation between pages

PAGES = {
    "Overview": [
        st.Page("pages/01_Executive_Overview.py", title="Executive Overview", icon=":material/dashboard:",
                default=True),
    ],
    "Performance": [
        st.Page("pages/02_Match_Centre.py", title="Match Centre", icon=":material/scoreboard:"),
        st.Page("pages/03_Player_Lab.py", title="Player Lab", icon=":material/person_search:"),
        st.Page("pages/04_Team_Tactics.py", title="Team Tactics", icon=":material/hub:"),
        st.Page("pages/05_Pitch_And_Events.py", title="Pitch & Event Explorer", icon=":material/stadium:"),
    ],
    "Decision support": [
        st.Page("pages/06_Starting_XI_Lab.py", title="Starting XI Lab", icon=":material/groups:"),
        st.Page("pages/07_Substitution_Lab.py", title="Substitution Lab", icon=":material/swap_horiz:"),
        st.Page("pages/08_Managerial_Intelligence.py", title="Managerial Intelligence",
                icon=":material/psychology:"),
    ],
    "Evidence": [
        st.Page("pages/09_Statistical_Explorer.py", title="Statistical Explorer", icon=":material/query_stats:"),
        st.Page("pages/10_Model_Evaluation.py", title="Model Evaluation", icon=":material/model_training:"),
        st.Page("pages/13_Chart_Explorer.py", title="Chart Explorer", icon=":material/search:"),
    ],
    "Reference": [
        st.Page("pages/11_Data_Quality_And_Sources.py", title="Data Quality & Sources", icon=":material/fact_check:"),
        st.Page("pages/12_Methodology_And_About.py", title="Methodology & About", icon=":material/menu_book:"),
    ],
}

st.navigation(PAGES).run()
