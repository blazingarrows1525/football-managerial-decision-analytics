"""Page chrome shared by every dashboard page: styling, header, scope line, attribution footer."""
from __future__ import annotations


import pandas as pd
import streamlit as st

from src.data.provenance import ATTRIBUTION_REQUIREMENT, SOURCE_REPOSITORY_URL, STATSBOMB_ATTRIBUTION
from src.dashboard import filters, state
from src.visualization.theme import AMBER, INK, MUTED, NAVY, RED, SYNTHETIC_WATERMARK, TEAL
from src.workspace import Workspace

APP_TITLE = "Football Managerial Decision Analytics"
# Official StatsBomb logo served from the source repository (the user agreement asks for it on published analysis).
LOGO_URL = "https://raw.githubusercontent.com/hudl/open-data/master/img/SB%20-%20Icon%20Lockup%20-%20Colour%20positive.png"

CSS = f"""
<style>
  .block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1400px; }}
  h1, h2, h3 {{ color: {INK}; letter-spacing: -0.01em; }}
  .fma-eyebrow {{ font-size: 0.74rem; letter-spacing: 0.12em; text-transform: uppercase; color: {TEAL};
                  font-weight: 700; margin-bottom: 0.1rem; }}
  .fma-sub {{ color: {MUTED}; font-size: 0.98rem; margin-top: -0.4rem; margin-bottom: 0.6rem; }}
  .fma-scope {{ background: #f1efe8; border-left: 4px solid {NAVY}; padding: 0.5rem 0.8rem; border-radius: 4px;
                font-size: 0.88rem; color: {INK}; margin: 0.3rem 0 1rem 0; }}
  .fma-card {{ background: white; border: 1px solid #e3dfd3; border-radius: 10px; padding: 0.9rem 1.1rem;
               margin-bottom: 0.8rem; }}
  .fma-card h4 {{ margin: 0 0 0.35rem 0; font-size: 1.0rem; color: {NAVY}; }}
  .fma-card p {{ margin: 0.15rem 0; font-size: 0.9rem; line-height: 1.45; }}
  .fma-tag {{ display: inline-block; background: #e8f3f1; color: #1c6f66; border-radius: 999px;
              padding: 0.05rem 0.55rem; font-size: 0.74rem; font-weight: 600; margin-right: 0.3rem; }}
  .fma-warn {{ background: #fdf3df; border-left: 4px solid {AMBER}; padding: 0.5rem 0.8rem; border-radius: 4px;
               font-size: 0.88rem; margin: 0.3rem 0 0.8rem 0; }}
  .fma-synth {{ background: {RED}; color: white; font-weight: 700; padding: 0.55rem 0.9rem; border-radius: 6px;
                text-align: center; margin-bottom: 0.8rem; letter-spacing: 0.03em; }}
  .fma-foot {{ color: {MUTED}; font-size: 0.8rem; border-top: 1px solid #e3dfd3; margin-top: 2.2rem;
               padding-top: 0.8rem; line-height: 1.5; }}
  div[data-testid="stMetric"] {{ background: white; border: 1px solid #e3dfd3; border-radius: 10px;
                                 padding: 0.7rem 0.9rem; }}
  div[data-testid="stMetricLabel"] p {{ font-size: 0.8rem; color: {MUTED}; }}
  @media (max-width: 760px) {{ .block-container {{ padding-left: 0.8rem; padding-right: 0.8rem; }} }}
</style>
"""
PRESENTATION_CSS = """
<style>
  section[data-testid="stSidebar"] { display: none; }
  .block-container { max-width: 1500px; }
  h1 { font-size: 2.5rem; }
  div[data-testid="stMetricValue"] { font-size: 2.3rem; }
  .fma-sub, .fma-scope { font-size: 1.05rem; }
</style>
"""


def configure_page() -> None:
    """Call once per run, before any other Streamlit command."""
    st.set_page_config(page_title=APP_TITLE, page_icon=":material/sports_soccer:", layout="wide",
                       initial_sidebar_state="expanded")


def presentation() -> bool:
    return bool(st.session_state.get("f_presentation"))


def start(title: str, subtitle: str, eyebrow: str = "") -> tuple[Workspace, Workspace, pd.DataFrame]:
    """Render the page header and return ``(base workspace, scoped workspace, matches in scope)``."""
    st.markdown(CSS, unsafe_allow_html=True)
    filters.sidebar(state.base_workspace())
    base, ws, tm = state.current_workspace()
    if presentation():
        st.markdown(PRESENTATION_CSS, unsafe_allow_html=True)
    if base.synthetic:
        st.markdown(f'<div class="fma-synth">{SYNTHETIC_WATERMARK}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([0.8, 0.2], vertical_alignment="bottom")
    with c1:
        if eyebrow:
            st.markdown(f'<div class="fma-eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
        st.title(title)
        st.markdown(f'<div class="fma-sub">{subtitle}</div>', unsafe_allow_html=True)
    with c2:
        st.toggle("Presentation mode", key="f_presentation",
                  help="Hides the sidebar and technical panels and enlarges labels for a demo.")
    st.markdown(f'<div class="fma-scope">Scope: {state.filter_summary(base, tm)} · historical data, not a live '
                f'feed</div>', unsafe_allow_html=True)
    return base, ws, tm


def empty_scope(tm: pd.DataFrame) -> bool:
    """Show a helpful empty state when the filters select no match. Returns True when the page should stop."""
    if len(tm):
        return False
    st.warning("No match satisfies the current filters. Widen the venue, result, opponent or date filters in the "
               "sidebar, or press **Reset filters**.")
    footer()
    return True


def low_sample_note(n: int, minimum: int, what: str = "matches") -> None:
    if n < minimum:
        st.markdown(f'<div class="fma-warn"><b>Low sample.</b> Only {n} {what} in scope (fewer than {minimum}). '
                    f'Charts are shown for inspection; do not read differences as reliable.</div>',
                    unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f'<div class="fma-warn">{text}</div>', unsafe_allow_html=True)


def footer() -> None:
    if state.base_workspace().synthetic:
        st.markdown(f'<div class="fma-foot"><b>{SYNTHETIC_WATERMARK}.</b> This session runs on a generated '
                    f'fixture league used for automated tests and layout checks. No number on these pages '
                    f'describes a real team, player or match.</div>', unsafe_allow_html=True)
        return
    cols = st.columns([0.14, 0.86], vertical_alignment="center")
    with cols[0]:
        try:
            st.image(LOGO_URL, width=120)
        except Exception:  # the logo is fetched from the source repository; fall back to text when offline
            st.caption("StatsBomb")
    with cols[1]:
        st.markdown(f'<div class="fma-foot">{STATSBOMB_ATTRIBUTION} {ATTRIBUTION_REQUIREMENT} '
                    f'<a href="{SOURCE_REPOSITORY_URL}">Source repository</a>. Decision support only: associations '
                    f'are not causal effects, heuristic scores are valid only under their stated weights, and no '
                    f'injury, fitness, tracking or age data exist in the source.</div>', unsafe_allow_html=True)
