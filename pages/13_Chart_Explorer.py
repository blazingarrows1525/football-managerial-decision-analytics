"""Chart Explorer: search the whole catalogue, see prerequisites and render any available chart on demand."""
from __future__ import annotations

import streamlit as st

from src.dashboard import chart_explorer, layout

base, ws, tm = layout.start("Chart Explorer", "Which charts exist, what does each need, what can it not claim — and "
                            "show me one.", eyebrow="Evidence")
if layout.empty_scope(tm):
    st.stop()

chart_explorer.render(ws, tm)
if not layout.presentation():
    st.caption("To export every available chart at once, run `python scripts/export_gallery.py` (batch mode with "
               "progress and a limit). The dashboard never renders the whole catalogue by itself.")
layout.footer()
