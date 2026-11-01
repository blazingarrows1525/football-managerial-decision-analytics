"""Generate notebooks/Football_Managerial_Decision_Analytics.ipynb from cell definitions.

Run:  python scripts/build_notebook.py          (writes the un-executed notebook)
Then: python scripts/execute_notebook.py        (executes it top-to-bottom in a fresh kernel)
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "Football_Managerial_Decision_Analytics.ipynb"

CELLS: list[tuple[str, str]] = []


def md(text: str) -> None:
    CELLS.append(("md", text.strip("\n")))


def code(text: str) -> None:
    CELLS.append(("code", text.strip("\n")))


# =============================================================================
# 0. Cover
# =============================================================================
md(r"""
# Football Managerial Decision Intelligence
### Interactive Player Performance, Starting XI Optimisation and Substitution Analysis Using Match Data
*Big Data Visualization — mini-project notebook*

| | |
|---|---|
| **Student name** | `[enter your name]` |
| **Registration number** | `[enter]` |
| **Course / section** | `[enter]` |
| **Faculty / guide** | `[enter]` |
| **Institution** | `[enter]` |
| **Project review (D4)** | 2-Nov-2026 · **Demo & viva (D2)** | 12-Nov-2026 |

**Research question.** *How can historical football match events, player performance indicators, lineup records and
match-state context be transformed into interactive visual analytics that support evidence-based starting-lineup and
substitution decisions?*

**Objective.** Build a reproducible pipeline — provenance → validation → features → analysis → decision support →
evaluation — over real open event data, and expose it through interactive Plotly visuals.

**Modules.** ① data collection & provenance · ② quality audit · ③ canonical tables · ④ feature engineering ·
⑤ exploratory analysis · ⑥ player intelligence · ⑦ team & tactical intelligence · ⑧ starting-XI decision support ·
⑨ substitution intelligence · ⑩ managerial decision patterns · ⑪ gated modelling · ⑫ findings, export, viva.

> **Scope and disclaimer.** This is football *performance-analysis decision support*. It is **not** a betting,
> fantasy or player-rating product. Every recommendation is a transparent heuristic computed only from information
> available before the decision, shown with its data coverage. Associations are never presented as causal effects,
> and the coaching staff — who hold information this dataset does not — make the final decision.
""")

# =============================================================================
# 1. Environment
# =============================================================================
md(r"""
## 1 · Environment setup
Locates the project package (`src/football_analytics`), installs anything missing in Google Colab, fixes the
random seed, registers the plotting theme and enables widgets. In Colab, either set `PROJECT_REPO_URL` to your
GitHub copy of this repository, or upload `football_analytics_colab_bundle.zip` when prompted (see README).
""")
code(r"""
import os, sys, subprocess, zipfile, importlib, platform, time, warnings
from pathlib import Path

IN_COLAB = "google.colab" in sys.modules
HEADLESS = os.environ.get("FMA_HEADLESS") == "1"     # set by scripts/execute_notebook.py
PROJECT_REPO_URL = ""   # optional, e.g. "https://github.com/<you>/football-managerial-analytics.git"

def find_project_root():
    candidates = [Path.cwd(), Path.cwd().parent, Path("/content/football-managerial-analytics"),
                  Path("/content/project"), Path("/content/drive/MyDrive/football-managerial-analytics")]
    candidates += [p.parent for p in Path("/content").glob("*/src/football_analytics")] if Path("/content").exists() else []
    for c in candidates:
        if (c / "src" / "football_analytics" / "__init__.py").exists():
            return c.resolve()
    return None

ROOT = find_project_root()
if ROOT is None and IN_COLAB:
    if PROJECT_REPO_URL:
        subprocess.run(["git", "clone", "-q", PROJECT_REPO_URL, "/content/football-managerial-analytics"], check=True)
    else:
        from google.colab import files
        print("Upload football_analytics_colab_bundle.zip (created by scripts/make_colab_bundle.py)")
        up = files.upload()
        zipfile.ZipFile(next(iter(up)), "r").extractall("/content/football-managerial-analytics")
    ROOT = find_project_root()
assert ROOT is not None, "Project root not found: run the notebook from the repository (see README)."
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))

if IN_COLAB:  # Colab already ships pandas/numpy/plotly/sklearn/scipy; install only what is missing
    for mod, pkg in [("pyarrow", "pyarrow"), ("ipywidgets", "ipywidgets")]:
        if importlib.util.find_spec(mod) is None:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg], check=False)
    from google.colab import output
    output.enable_custom_widget_manager()

import numpy as np, pandas as pd
import plotly, plotly.io as pio
from IPython.display import display, Markdown, HTML
warnings.filterwarnings("ignore", category=FutureWarning)
pd.set_option("display.max_columns", 40); pd.set_option("display.width", 200)
pio.renderers.default = "colab" if IN_COLAB else "notebook_connected+plotly_mimetype"

try:
    import ipywidgets as W
    WIDGETS_OK = True
except Exception:
    WIDGETS_OK = False

import football_analytics as fa
from football_analytics import (config as fcfg, ingestion, parsing, validation, features, player_analysis as pa,
                                tactical_analysis as ta, lineup_optimizer as lo, substitution_analysis as sa,
                                manager_analysis as ma, modeling as mdl, visualizations as viz, reporting,
                                data_sources, pipeline)
SEED = 42
np.random.seed(SEED)
print(f"Project root : {ROOT}")
print(f"Runtime      : {'Google Colab' if IN_COLAB else 'local Jupyter'} | Python {platform.python_version()} | "
      f"pandas {pd.__version__} | plotly {plotly.__version__} | widgets {'on' if WIDGETS_OK else 'off'}")
print(f"Package      : football_analytics {fa.__version__}")
""")

# =============================================================================
# 2. Configuration
# =============================================================================
md(r"""
## 2 · Configuration
Every analytical choice lives here — nothing is hidden in later cells. Change a value and re-run from this cell.

* **Data mode** — `REAL_OPEN_DATA` (StatsBomb open data, default), `USER_DATA` (your own StatsBomb-format JSON in
  `data/external/user_statsbomb/`), or `DEMO_SYNTHETIC` (fictional league for offline testing; every chart then
  carries a red warning banner).
* **Competition / season** must be a pair that exists in the source catalogue shown in Section 3.
* `MATCH_LIMIT = None` analyses every published match; set e.g. `20` for a quick run (the truncation is reported).
* Thresholds, formation templates, weights, timing bands and substitution rules are editable dictionaries.
""")
code(r"""
DATA_MODE      = fcfg.REAL_OPEN_DATA     # REAL_OPEN_DATA | USER_DATA | DEMO_SYNTHETIC
COMPETITION_ID = 9                       # 1. Bundesliga
SEASON_ID      = 281                     # 2023/2024
MATCH_LIMIT    = None                    # None = all published matches for the selection
FOCUS_TEAM     = "Bayer Leverkusen"      # team analysed in XI / substitution / manager sections
MIN_MINUTES    = 180                     # per-90 & percentile eligibility
OFFLINE        = False                   # True = use cached raw files only (no network)

if DATA_MODE == fcfg.DEMO_SYNTHETIC:     # the synthetic league has its own ids and no fixed focus team
    COMPETITION_ID, SEASON_ID, FOCUS_TEAM, MIN_MINUTES = 9999, 9999, None, 90

cfg = fcfg.Config(project_root=ROOT, data_mode=DATA_MODE, competition_id=COMPETITION_ID, season_id=SEASON_ID,
                  match_limit=MATCH_LIMIT, focus_team=FOCUS_TEAM, min_minutes=MIN_MINUTES,
                  min_group_size=3 if DATA_MODE == fcfg.DEMO_SYNTHETIC else 8)
BANNER = fcfg.SYNTHETIC_WARNING if cfg.is_synthetic else None

def status_badge():
    color = "#c8553d" if cfg.is_synthetic else "#2a9d8f"
    text = (f"DATA MODE: {cfg.data_mode} — {fcfg.SYNTHETIC_WARNING}" if cfg.is_synthetic else
            f"DATA MODE: {cfg.data_mode} — real StatsBomb open data (competition {cfg.competition_id}, "
            f"season {cfg.season_id})")
    display(HTML(f'<div style="background:{color};color:white;padding:8px 14px;border-radius:6px;'
                 f'font-weight:600;font-family:sans-serif">{text}</div>'))
status_badge()
display(pd.DataFrame({"setting": ["min_minutes", "min_group_size", "form_window", "reliability_full_minutes",
                                  "min_manager_matches", "impact_window_minutes"],
                      "value": [cfg.min_minutes, cfg.min_group_size, cfg.form_window, cfg.reliability_full_minutes,
                                cfg.min_manager_matches, cfg.impact_window_minutes]}))
""")
code(r"""
display(Markdown("**Starting-XI score weights** (components scaled 0-100, then × position compatibility)"))
display(pd.DataFrame([cfg.xi_score_weights]))
display(Markdown("**Substitution rules** — " + cfg.sub_rules["source"]))
display(pd.DataFrame([{k: v for k, v in cfg.sub_rules.items() if k != "source"}]))
display(Markdown("**Substitution timing bands** (clock minutes; stoppage time keeps counting, e.g. 45+2 = 47)"))
display(pd.DataFrame(cfg.sub_timing_bands))
display(Markdown("**Formation templates available:** " + ", ".join(cfg.formation_templates)))
""")

# =============================================================================
# 3. Data collection
# =============================================================================
md(r"""
## 3 · Data collection
**Source:** [StatsBomb Open Data](https://github.com/statsbomb/open-data) (Hudl) — competitions, matches (with
managers, referee, stadium), lineups and event files, fetched as raw JSON over HTTPS. Files are cached unchanged in
`data/raw/`, every read is logged in a manifest (URL, UTC timestamp, bytes, SHA-256, status), and downloads use
timeouts, retries with back-off and graceful failure. Re-runs read from cache, so the notebook also works offline.

The catalogue below is what the source *actually* publishes; the competition/season in Section 2 must be one of
these rows.
""")
code(r"""
if cfg.is_synthetic:
    ingestion.prepare_synthetic(cfg)
store = ingestion.DataStore(cfg, offline=OFFLINE)
catalogue = store.competitions()
print(f"Catalogue: {len(catalogue)} competition-seasons, {catalogue['competition_name'].nunique()} competitions")
sel = catalogue[(catalogue.competition_id == cfg.competition_id) & (catalogue.season_id == cfg.season_id)]
assert len(sel) == 1, "Selected competition/season not in catalogue — pick a row from the table below."
display(sel)
display(catalogue[["competition_id", "season_id", "competition_name", "season_name", "competition_gender",
                   "country_name", "match_available_360"]].head(80))
""")
code(r"""
if WIDGETS_OK and not HEADLESS:
    opts = [(f"{r.competition_name} — {r.season_name}", (r.competition_id, r.season_id)) for r in catalogue.itertuples()]
    pick = W.Dropdown(options=opts, value=(cfg.competition_id, cfg.season_id), description="Competition",
                      layout=W.Layout(width="520px"))
    out = W.Output()
    def _on(change):
        with out:
            out.clear_output()
            c, s = change["new"]
            print(f"Set COMPETITION_ID = {c}, SEASON_ID = {s} in Section 2 and re-run from there.")
    pick.observe(_on, names="value")
    display(pick, out)
else:
    print("Live competition picker available when running interactively (Colab/Jupyter).")
""")
code(r"""
t0 = time.perf_counter()
matches_raw = store.matches_raw(cfg.competition_id, cfg.season_id)
selected = ingestion.select_matches(matches_raw, cfg.match_limit, cfg.focus_team)
print(f"Matches published for this competition-season: {len(matches_raw)}")
print(f"Matches selected for analysis: {len(selected)}"
      + (f" (focus team filter: {cfg.focus_team})" if cfg.focus_team else "")
      + (f" (limited to first {cfg.match_limit} chronologically)" if cfg.match_limit else " (no truncation)"))
files = store.match_files([m["match_id"] for m in selected], include_360=cfg.include_360)
manifest = store.manifest_frame()
print(f"Acquisition time: {time.perf_counter() - t0:.1f}s")
display(manifest.groupby(["resource", "status", "from_cache"]).agg(files=("relative_path", "size"),
                                                                   MB=("bytes", lambda b: round(b.sum() / 1e6, 2))))
display(manifest[["resource", "relative_path", "bytes", "sha256", "retrieved_utc", "status"]].head(6))
""")

# =============================================================================
# 4. Inventory
# =============================================================================
md(r"""
## 4 · Dataset inventory and collection evidence
Actual dimensions of what was collected and parsed (Dataset-collection rubric). Parsing turns nested JSON into
canonical tables; the figures below are computed, never typed in.
""")
code(r"""
t0 = time.perf_counter()
bundle = pipeline.Bundle(config=cfg, store=store, catalogue=catalogue, matches_available=len(matches_raw))
pipeline.build_tables(bundle, selected, files)
T = bundle.tables
parse_seconds = time.perf_counter() - t0
scale = validation.dataset_scale(T, manifest, parse_seconds)
display(scale)
viz.coverage_cards(scale, banner=BANNER).show()
""")
code(r"""
inv = ingestion.raw_inventory(cfg.raw_dir)
display(inv.groupby("folder").agg(files=("file", "size"), MB=("bytes", lambda b: round(b.sum() / 1e6, 2))))
m = T["matches"]
print(f"Date coverage: {m.match_date.min():%Y-%m-%d} → {m.match_date.max():%Y-%m-%d} "
      f"({m.match_date.dt.to_period('M').nunique()} calendar months)")
display(Markdown("**Source register and attribution**"))
display(data_sources.source_register()[["source", "role_in_project", "status"]])
display(Markdown(f"> {data_sources.STATSBOMB_ATTRIBUTION}" if not cfg.is_synthetic else f"> **{BANNER}**"))
""")
md(r"""
**Big-data honesty.** The cards report the real scale: tens of MB of JSON and ~10⁵ events for one club-season —
a *scalable football-analytics pipeline / Big Data Visualization case study*, not "massive big data". Pandas is the
right tool at this volume (parsing + feature building take seconds). The same per-match design maps directly onto a
distributed engine: raw files are independent per `match_id`, so parsing is an embarrassingly parallel map
(e.g. Spark `binaryFiles` → `flatMap`), and every aggregation in Section 7 is a `groupBy` on `(match_id, team_id,
player_id)`. Spark is deliberately *not* added here because it would be decoration at this size — see the
processing times above and the scaling notes in the report.
""")

# =============================================================================
# 5. Quality
# =============================================================================
md(r"""
## 5 · Data cleaning and quality audit
Domain rules are tested explicitly; nothing is dropped silently. Key parsing decisions (documented in
`parsing.py`): StatsBomb's lineup-file position spells are **not** reliably chronological, so on-pitch time is
rebuilt from the event stream (Starting XI → Substitution → sending-off), period-aware so first-half stoppage time
never overlaps the second half. Temporary "Player Off/On" treatment breaks are ignored.
""")
code(r"""
bundle.quality, bundle.quality_log = validation.quality_checks(T)
display(bundle.quality)
n_flag = int((bundle.quality.status != "PASS").sum())
print(f"{len(bundle.quality) - n_flag}/{len(bundle.quality)} checks pass; {n_flag} flagged.")
display(Markdown("**Quality-action log** (retained / corrected / excluded / flagged records)"))
display(bundle.quality_log if len(bundle.quality_log) else pd.DataFrame({"action": ["no records excluded or corrected"]}))
display(Markdown("**Parser issue log**"))
display(T["parse_issues"] if len(T["parse_issues"]) else pd.DataFrame({"issue": ["none"]}))
""")
code(r"""
display(validation.coverage_summary(T))
viz.missingness_heatmap(validation.event_type_coverage(T["events"]), banner=BANNER).show()
""")
code(r"""
# Minutes reconstruction audit for one match: period bounds and every player's spell.
demo_mid = T["matches"]["match_id"].iloc[0]
display(T["period_bounds"][T["period_bounds"].match_id == demo_mid])
a = T["appearances"][T["appearances"].match_id == demo_mid]
display(a[["team_name", "player_name", "squad_status", "match_position", "minutes_played", "sub_on_minute",
           "sub_off_minute", "end_reason", "minutes_flag"]].sort_values(["team_name", "squad_status"]).round(1))
""")

# =============================================================================
# 6. Canonical tables
# =============================================================================
md(r"""
## 6 · Canonical tables
Source-native IDs are kept (never merged on names). Scores and match state are always computed from the team's
perspective; coordinates stay in one declared system (`statsbomb_120x80_attack_left_to_right`).
""")
code(r"""
teams = pd.concat([T["matches"][["home_team_id", "home_team"]].set_axis(["team_id", "team_name"], axis=1),
                   T["matches"][["away_team_id", "away_team"]].set_axis(["team_id", "team_name"], axis=1)]
                  ).drop_duplicates().sort_values("team_name").reset_index(drop=True)
players = (T["appearances"].groupby(["player_id"]).agg(player_name=("player_name", "last"),
           team=("team_name", "last"), squads=("match_id", "nunique")).reset_index())
canon = {"competitions/seasons": catalogue[(catalogue.competition_id == cfg.competition_id)],
         "matches": T["matches"], "teams": teams, "players": players, "appearances (matchday squads)": T["appearances"],
         "events": T["events"], "substitutions": T["substitutions_raw"], "managers": T["managers"]}
display(pd.DataFrame([{"table": k, "rows": len(v), "columns": v.shape[1]} for k, v in canon.items()]))
display(T["matches"][["match_id", "match_date", "home_team", "home_score", "away_score", "away_team", "stadium",
                      "referee"]].head())
display(T["events"][["match_id", "period", "minute", "second", "elapsed_min", "type", "team_name", "player_name",
                     "x", "y", "end_x", "end_y", "outcome", "shot_xg"]].sample(6, random_state=SEED))
display(T["managers"].drop_duplicates(["team_name", "manager_name"]).head(8))
""")

# =============================================================================
# 7. Features
# =============================================================================
md(r"""
## 7 · Feature engineering
Every metric has a definition, numerator/denominator, unit and source field (table below, exported to the data
dictionary). Rules applied:
* **Per-90** = count ÷ minutes × 90, only where minutes > 0 (no division by zero). Minutes are *actual playing time
  including stoppage*, so per-90 values are slightly lower than "nominal 90" conventions — consistently.
* **Role normalisation** — percentiles are computed within the player's role (if ≥ `min_group_size` eligible
  players) or role family otherwise, against the pool of players above `MIN_MINUTES`.
* **Project-defined approximations** (progressive pass/carry, possession proxy, field tilt, PPDA approximation) are
  labelled as such. xT, packing and tracking-based running metrics are **not** computed — the data cannot support them.
* **Workload proxies** (minutes in previous 7/14/28 days, rest days) count only matches in the dataset — they are not
  medical fatigue measures.
""")
code(r"""
pipeline.build_features(bundle)
B = bundle
FOCUS = cfg.focus_team or B.team_stats["team_name"].value_counts().index[0]
print(f"Feature tables built in {B.timings['features_s']:.1f}s | player-match rows {len(B.pms)} | "
      f"player-season rows {len(B.season)} | team-match rows {len(B.team_stats)} | focus team: {FOCUS}")
display(features.metric_dictionary().head(45))
""")
code(r"""
cols = ["player_name", "team_name", "primary_position", "primary_role", "appearances", "starts", "minutes_played",
        "goals", "xg", "xg_p90", "xa_p90", "key_passes_p90", "progressive_passes_p90", "pressures_p90",
        "pass_completion_pct", "benchmark_group", "benchmark_n", "coverage_label"]
display(B.season_pct[B.season_pct.team_name == FOCUS][cols].round(2).head(20))
display(Markdown("**Minimum-minutes sensitivity** — how the xG/90 leaderboard changes with the threshold"))
display(pa.threshold_sensitivity(B.season, "xg_p90"))
viz.threshold_sensitivity_chart(B.season, banner=BANNER).show()
""")
code(r"""
display(Markdown("**Workload proxies (pre-match, dataset matches only)** — focus team, latest match"))
last_mid = B.team_stats[B.team_stats.team_name == FOCUS].sort_values("match_date")["match_id"].iloc[-1]
w = B.workload[B.workload.match_id == last_mid].merge(
    T["appearances"][["match_id", "player_id", "player_name", "squad_status"]], on=["match_id", "player_id"])
display(w[["player_name", "squad_status", "minutes_prev_7d", "minutes_prev_14d", "minutes_prev_28d", "rest_days",
           "started_prev_match", "consecutive_starts_before", "start_share_before"]].round(2)
        .sort_values("start_share_before", ascending=False).head(12))
display(Markdown("**Team style indicators** (averages per analysed match)"))
display(ta.team_style_summary(B.team_stats).head(10))
""")

# =============================================================================
# 8. EDA
# =============================================================================
md(r"""
## 8 · Exploratory data analysis
Distributions first (what is typical, what is extreme), then position-group differences (RQ1), relationships
(correlation is association only), and temporal team trends.
""")
code(r"""
eda_metrics = ["xg_p90", "key_passes_p90", "progressive_passes_p90", "progressive_carries_p90", "pressures_p90",
               "interceptions_p90", "tackles_won_p90", "pass_completion_pct", "box_touches_p90", "aerials_won_p90"]
elig = B.season_pct[B.season_pct.eligible]
viz.feature_distributions(elig, eda_metrics, title=f"Feature distributions (eligible players, n={len(elig)})",
                          banner=BANNER).show()
viz.role_distribution(B.season_pct, eda_metrics, cfg.min_minutes, banner=BANNER).show()
""")
code(r"""
rd = elig.groupby("role_family")[["xg_p90", "progressive_passes_p90", "interceptions_p90", "pass_completion_pct",
                                   "pressures_p90"]].median().round(2)
rd.insert(0, "players", elig.groupby("role_family").size())
display(Markdown("**Observation (computed): median per-90 profile by role family**"))
display(rd)
top_role = rd["xg_p90"].idxmax(); top_int = rd["interceptions_p90"].idxmax()
display(Markdown(f"In this sample, **{top_role}s** have the highest median xG/90 ({rd.loc[top_role, 'xg_p90']}) and "
                 f"**{top_int}s** the highest median interceptions/90 ({rd.loc[top_int, 'interceptions_p90']}) — "
                 "which is why raw totals are never compared across roles."))
viz.correlation_heatmap(elig, eda_metrics, banner=BANNER).show()
""")
code(r"""
viz.results_overview(B.team_stats, FOCUS, banner=BANNER).show()
viz.team_trend(B.team_stats, FOCUS, banner=BANNER).show()
""")
code(r"""
# Match timeline and cumulative xG for the focus team's highest-xG match
fm = B.team_stats[B.team_stats.team_name == FOCUS].sort_values("xg", ascending=False).iloc[0]
mrow = T["matches"].set_index("match_id").loc[fm.match_id]
MATCH_LABEL = f"{mrow.match_date:%d %b %Y}: {mrow.home_team} {mrow.home_score}-{mrow.away_score} {mrow.away_team}"
viz.match_timeline(ta.match_timeline_events(T["events"], T["goals"], fm.match_id), title=f"Timeline — {MATCH_LABEL}",
                   banner=BANNER).show()
viz.cumulative_xg_chart(ta.cumulative_xg(B.flags, fm.match_id), title=f"Cumulative xG — {MATCH_LABEL}",
                        banner=BANNER).show()
""")

# =============================================================================
# 9. Player intelligence
# =============================================================================
md(r"""
## 9 · Player intelligence centre
Role-aware leaderboards and comparisons (use the dropdowns inside each chart — they work in exported HTML too),
then a profile of one player against his benchmark group. Percentiles are relative to the eligible pool of *this
dataset*; with one club's season, opponents contribute only 1-2 matches each, so benchmarks for the focus squad are
partly internal (the radar title states the benchmark group and its size).
""")
code(r"""
lb_metrics = ["xg_p90", "npxg_p90", "xa_p90", "key_passes_p90", "progressive_passes_p90", "progressive_carries_p90",
              "dribbles_completed_p90", "box_touches_p90", "pressures_p90", "interceptions_p90", "tackles_won_p90",
              "ball_recoveries_p90", "aerials_won_p90"]
viz.leaderboard_chart(B.season_pct, lb_metrics, min_minutes=max(cfg.min_minutes, 450), banner=BANNER).show()
viz.comparison_scatter(B.season_pct, lb_metrics + ["pass_completion_pct"], cfg.min_minutes, x="xg_p90",
                       y="xa_p90", highlight_team=FOCUS, banner=BANNER).show()
""")
code(r"""
DEFAULT_PLAYER = "Florian Wirtz"
fs = B.season_pct[(B.season_pct.team_name == FOCUS)]
hit = fs[fs.player_name.str.contains(DEFAULT_PLAYER, case=False, na=False)]
P = (hit if len(hit) else fs[fs.primary_role != "GK"]).sort_values("minutes_played", ascending=False).iloc[0]

def player_view(player_id, team_id=None):
    prof = pa.player_profile(B.season_pct, player_id, team_id)
    display(pd.DataFrame([prof]))
    row = B.season_pct[B.season_pct.player_id == player_id].iloc[0]
    viz.player_radar(B.season_pct, player_id, pa.radar_metrics(row.primary_role, cfg), banner=BANNER).show()
    display(Markdown("**Observed relative strengths / weaknesses** (percentiles of role-fit metrics; not a rating)"))
    display(pa.strengths_weaknesses(B.season_pct, player_id, cfg, team_id))
    metrics = [m for m in pa.radar_metrics(row.primary_role, cfg) if m.endswith("_p90")][:3]
    viz.form_trend(pa.rolling_form_series(B.pms, player_id, metrics, cfg.form_window), metrics, row.player_name,
                   cfg.form_window, banner=BANNER).show()

player_view(P.player_id, P.team_id)
""")
code(r"""
if WIDGETS_OK and not HEADLESS:
    opts = [(f"{r.player_name} ({r.primary_position}, {r.minutes_played:.0f} min)", r.player_id)
            for r in B.season_pct[B.season_pct.team_name == FOCUS].sort_values("minutes_played", ascending=False).itertuples()]
    W.interact(lambda player: player_view(player), player=W.Dropdown(options=opts, value=P.player_id,
                                                                     layout=W.Layout(width="480px")))
else:
    print("Live player selector available when running interactively (Colab/Jupyter).")
""")
code(r"""
viz.workload_bars(B.season_pct, FOCUS, banner=BANNER).show()
""")

# =============================================================================
# 10. Team & tactical
# =============================================================================
md(r"""
## 10 · Team and tactical intelligence
Formation use and outcomes (descriptive — opponent strength and squad availability confound them), team style,
and spatial views on a 120 × 80 pitch (attacking left → right for the team in question).
""")
code(r"""
fsum = ta.formation_summary(B.team_stats, FOCUS)
display(fsum)
viz.formation_frequency(fsum, FOCUS, banner=BANNER).show()
viz.formation_comparison(fsum, FOCUS, banner=BANNER).show()
""")
code(r"""
shots = B.flags[(B.flags.team_name == FOCUS) & (B.flags.type == "Shot")]
viz.shot_map(shots, f"{FOCUS}: all shots, season", banner=BANNER).show()
opp_shots = B.flags[(B.flags.match_id.isin(B.team_stats[B.team_stats.team_name == FOCUS].match_id))
                    & (B.flags.team_name != FOCUS) & (B.flags.type == "Shot")]
viz.shot_map(opp_shots, f"Opponents' shots against {FOCUS}", banner=BANNER).show()
""")
code(r"""
pp = B.flags[(B.flags.match_id == fm.match_id) & (B.flags.player_id == P.player_id) & (B.flags.type == "Pass")]
viz.pass_map(pp, f"{P.player_name}: passes — {MATCH_LABEL}", banner=BANNER).show()
team_id_focus = B.team_stats[B.team_stats.team_name == FOCUS].team_id.iloc[0]
nodes, edges, cut = ta.pass_network(B.flags, T["appearances"], fm.match_id, team_id_focus)
viz.pass_network_chart(nodes, edges, f"{FOCUS} pass network — {MATCH_LABEL}", cut, banner=BANNER).show()
prog = B.flags[(B.flags.player_id == P.player_id)]
viz.progressive_actions_map(prog, f"{P.player_name}: progressive passes and carries (season)", banner=BANNER).show()
""")

# =============================================================================
# 11. Starting XI
# =============================================================================
md(r"""
## 11 · Starting XI decision support
**Decision time:** before kick-off of a selected historical match. **Information used:** only matches *before*
that date. **Candidate pool:** that match's announced matchday squad.

**Score per (player, slot)** = Σ wᵢ·componentᵢ (+2 side-preference tie-breaker) × position compatibility, where the
components (0-100) are: role fit (weighted percentiles of the slot role's metrics), recent form (same composite over
the last 5 appearances; season value if none), sample reliability (minutes/900), workload suitability (penalises
>180 min in the previous 7 days or <3 rest days) and lineup continuity (started previous match).
**Optimiser:** the Hungarian algorithm assigns 11 distinct players to the 11 slots maximising the total — exact,
deterministic, and constrained (one goalkeeper, no duplicates, compatibility > 0, unavailable players excluded,
empty slot + warning when depth is insufficient). Scores are *not* probabilities.
""")
code(r"""
focus_matches = B.team_stats[B.team_stats.team_name == FOCUS].sort_values("match_date").reset_index(drop=True)
XI_MATCH_INDEX = min(24, len(focus_matches) - 1)      # editable: which focus-team match to analyse
xm = focus_matches.iloc[XI_MATCH_INDEX]
XI_FORMATION = xm.starting_formation if xm.starting_formation in cfg.formation_templates else "4-3-3"
UNAVAILABLE = []                                      # e.g. [player_id, ...] marked unavailable by the user
ctx = lo.decision_context(B, FOCUS, match_id=xm.match_id)
xi = lo.optimize_xi(ctx, XI_FORMATION, cfg, unavailable=UNAVAILABLE)
print(f"Match: {xm.match_date:%d %b %Y} vs {xm.opponent} ({xm.home_away}) | formation used: {XI_FORMATION} "
      f"(actual {xm.starting_formation}) | candidates: {len(ctx.candidates)} | pool: {ctx.pool_description}")
viz.xi_pitch(xi.lineup, f"Recommended {XI_FORMATION} XI — decision date {ctx.asof:%Y-%m-%d} "
             f"(total score {xi.total_score:.0f})", banner=BANNER).show()
viz.score_decomposition(xi.lineup, cfg.xi_score_weights, "Explainable score decomposition per selected player",
                        banner=BANNER).show()
display(Markdown("**Warnings:** " + ("; ".join(xi.warnings) if xi.warnings else "none")))
""")
code(r"""
cmp, agree = lo.compare_with_actual(xi, T["appearances"], xm.match_id, ctx.team_id)
display(Markdown(f"**Recommended vs actual XI** — descriptive agreement {agree:.0%} "
                 "(agreement is not proof of quality; disagreement is not proof the coach was wrong)."))
display(cmp)
display(Markdown("**Why each squad player was not selected**"))
display(xi.omitted)
display(Markdown("**Squad depth by slot** (candidates with compatibility ≥ 0.8)"))
display(xi.depth)
""")
code(r"""
display(Markdown("**Formation comparison** (same pool and date)"))
display(lo.compare_formations(ctx, cfg, UNAVAILABLE))
# Alternative "rotation" XI: rest the three selected outfield players with the most minutes in the previous 14 days
load = ctx.candidates.set_index("player_id")["minutes_prev_14d"].fillna(0)
rest = list(xi.lineup[xi.lineup.slot_role != "GK"].assign(l=lambda d: d.player_id.map(load))
            .nlargest(3, "l").player_id)
alt = lo.optimize_xi(ctx, XI_FORMATION, cfg, unavailable=UNAVAILABLE + rest)
viz.alternative_xi_comparison(xi.lineup, alt.lineup, "Recommended XI", "Rotation XI (3 highest-load rested)",
                              banner=BANNER).show()
print(f"Total score: recommended {xi.total_score:.1f} vs rotation {alt.total_score:.1f} "
      f"(Δ {alt.total_score - xi.total_score:+.1f})")
""")
code(r"""
# What-if: force the best-scoring unselected player into his best slot and re-optimise
cand_scores = xi.score_matrix[xi.score_matrix.feasible & ~xi.score_matrix.player_id.isin(xi.lineup.player_id)]
if len(cand_scores):
    best = cand_scores.sort_values("score", ascending=False).iloc[0]
    wi, delta = lo.what_if(ctx, xi, best.slot, best.player_id, cfg, UNAVAILABLE)
    display(Markdown(f"**What-if:** pin **{best.player_name}** at **{best.slot}** → total score change "
                     f"**{delta:+.1f}** (the optimiser's choice is optimal under the stated weights, so Δ ≤ 0)."))
    display(wi.lineup[["slot", "player_name", "score", "forced"]].round(1))
""")
code(r"""
if WIDGETS_OK and not HEADLESS:
    names = ctx.candidates.set_index("player_id")["player_name"].to_dict()
    def xi_live(formation, unavailable):
        r = lo.optimize_xi(ctx, formation, cfg, unavailable=list(unavailable))
        viz.xi_pitch(r.lineup, f"{formation} — total {r.total_score:.0f}", banner=BANNER).show()
        print("Warnings:", r.warnings or "none")
    W.interact(xi_live, formation=W.Dropdown(options=list(cfg.formation_templates), value=XI_FORMATION),
               unavailable=W.SelectMultiple(options=[(v, k) for k, v in names.items()], rows=8,
                                            description="Unavailable"))
else:
    print("Live formation / availability controls available when running interactively (Colab/Jupyter).")
""")
code(r"""
t0 = time.perf_counter()
hist_xi = lo.historical_agreement(B, FOCUS)
print(f"Re-ran the optimiser before each of {len(hist_xi)} matches using only prior data "
      f"({time.perf_counter() - t0:.1f}s). Mean descriptive agreement with the actual XI: "
      f"{hist_xi.agreement_pct.mean():.1f}% (median {hist_xi.agreement_pct.median():.0f}%).")
display(hist_xi.tail(8))
# Hypothetical next fixture (4 days after last analysed match)
ctx_next = lo.decision_context(B, FOCUS)
xi_next = lo.optimize_xi(ctx_next, XI_FORMATION, cfg)
viz.xi_pitch(xi_next.lineup, f"Hypothetical next-fixture XI ({XI_FORMATION}), decision date "
             f"{ctx_next.asof:%Y-%m-%d}", banner=BANNER).show()
""")

# =============================================================================
# 12. Substitutions
# =============================================================================
md(r"""
## 12 · Substitution intelligence
Historical substitutions enriched with the **team-perspective score at the moment of the change**, timing band,
roles, window usage (rules user-configured) and manager. Then a live scenario: everything the bench could have known
at the decision minute — and nothing after it.
""")
code(r"""
S = B.subs
display(S[["match_date", "team_name", "minute", "player_off_name", "off_role", "player_on_name", "on_role",
           "sub_reason", "game_state", "team_score", "opponent_score", "timing_band", "window_number",
           "manager_name"]].head(10))
print(f"{len(S)} substitutions in {S.match_id.nunique()} matches; identity check: "
      f"{(S.identity_check == 'ok').mean():.0%} resolved against matchday squads; "
      f"injury-coded: {(S.sub_reason == 'Injury').sum()}")
S_grp = S.assign(group=np.where(S.team_name == FOCUS, FOCUS, "Opponents (pooled)"))
viz.sub_timing_histogram(S_grp, cfg.sub_timing_bands, group="group", banner=BANNER).show()
viz.subs_by_state(S, banner=BANNER).show()
display(sa.state_profile(S_grp, by="group"))
""")
code(r"""
viz.role_flow_sankey(sa.role_flow(S), banner=BANNER).show()
viz.substitution_timeline(S[S.match_id == fm.match_id], f"Substitutions — {MATCH_LABEL}", banner=BANNER).show()
""")
md(r"""
### Live scenario
The scenario is picked automatically as the first focus-team match in which the team was **not winning** at
~65 minutes of playing time (falls back to any match). Intent is inferred by a transparent rule — trailing → attack,
leading → protect, drawing → balance — and can be overridden. Outgoing candidates are judged on minutes played *in
this match*, booking risk, and in-match role actions relative to **their own pre-match per-90 baseline** (role
context, never a raw low count). Incoming candidates are bench players who have not yet appeared.
""")
code(r"""
SCENARIO_MINUTE = 65.0
INTENT_OVERRIDE = None          # "attack" | "protect" | "balance" | None (rule-based)
scen = None
for r in focus_matches.itertuples():
    opp_id = r.opponent_id
    tg, og = features.score_at(T["goals"], r.match_id, r.team_id, opp_id, elapsed=SCENARIO_MINUTE)
    if tg <= og:
        scen = r; break
scen = scen or focus_matches.iloc[0]
rec = sa.recommend_substitution(B, scen.match_id, FOCUS, SCENARIO_MINUTE, intent=INTENT_OVERRIDE)
c = rec["context"]
display(Markdown(f"**Scenario:** {scen.match_date:%d %b %Y}, {FOCUS} vs {c['opponent']} ({c['home_away']}) at "
                 f"**{SCENARIO_MINUTE:.0f}'** of playing time — score **{c['team_score']}-{c['opponent_score']}** "
                 f"({c['game_state']}), numerical state {c['man_advantage']:+d}, substitutions remaining "
                 f"**{c['subs_remaining']}**, windows remaining **{c['windows_remaining']}** · rules: {c['rule_source']}"))
display(pd.DataFrame([c["team_live"], c["opponent_live"]], index=[FOCUS, c["opponent"]]))
display(Markdown(f"**Intent:** `{rec['intent']}` — {rec['intent_reason']}"))
display(Markdown("**Outgoing-candidate ranking** (data up to the decision minute + pre-match baselines)"))
display(rec["outgoing_ranking"][["player_name", "role", "minutes_so_far", "booked", "involvement_vs_baseline",
                                 "outgoing_score", "reasons"]])
""")
code(r"""
if rec["status"] == "ok":
    off, on = rec["recommended_off"], rec["recommended_on"]
    inc = sa.rank_incoming(c, off["role"], rec["intent"], cfg)
    viz.candidate_comparison(inc, cfg.sub_candidate_weights, f"Incoming candidates for {off['player_name']} "
                             f"({off['role']}) — intent '{rec['intent']}'", banner=BANNER).show()
    card = pd.DataFrame({"field": ["Recommended OFF", "Recommended ON", "Suggested decision window",
                                   "Tactical objective", "Evidence (incoming)", "Evidence (outgoing)",
                                   "Risks / trade-offs", "Rule allowance", "Data coverage", "Injury status",
                                   "Final decision"],
                         "value": [f"{off['player_name']} ({off['role']})", f"{on['player_name']} ({on['role']})",
                                   rec["decision_window"], rec["tactical_objective"], on["evidence"], off["reasons"],
                                   on["risks"], rec["rule_status"], rec["coverage"], on["injury_status"],
                                   rec["human_note"]]})
    display(card.style.hide(axis="index").set_properties(**{"text-align": "left", "white-space": "pre-wrap"}))
    display(Markdown("**Alternatives**"))
    display(rec["alternatives"])
else:
    print("Recommendation status:", rec["status"])
""")
code(r"""
if WIDGETS_OK and not HEADLESS:
    mopts = [(f"{r.match_date:%d %b} vs {r.opponent}", r.match_id) for r in focus_matches.itertuples()]
    def sub_live(match_id, minute, intent):
        r = sa.recommend_substitution(B, match_id, FOCUS, float(minute), intent=None if intent == "auto" else intent)
        cc = r["context"]
        print(f"{cc['team_score']}-{cc['opponent_score']} ({cc['game_state']}) at {minute}' | intent {r['intent']} | "
              f"status {r['status']}")
        if r["status"] == "ok":
            print(f"OFF {r['recommended_off']['player_name']} → ON {r['recommended_on']['player_name']}")
            print("Evidence:", r["recommended_on"]["evidence"]); print("Risks:", r["recommended_on"]["risks"])
    W.interact(sub_live, match_id=W.Dropdown(options=mopts, value=scen.match_id, description="Match"),
               minute=W.IntSlider(value=65, min=46, max=88, step=1), intent=["auto", "attack", "protect", "balance"])
else:
    print("Live substitution scenario controls available when running interactively (Colab/Jupyter).")
""")
code(r"""
t0 = time.perf_counter()
agree_subs = sa.historical_agreement(B, FOCUS, top_k=3)
print(f"Heuristic re-run 1 second before each of {len(agree_subs)} non-injury {FOCUS} substitutions "
      f"({time.perf_counter() - t0:.1f}s), pre-decision data only.")
summary = pd.DataFrame({
    "measure": ["actual incoming player in heuristic top-3", "actual outgoing player in heuristic top-3",
                "median bench size", "random top-3 baseline for incoming (3 / bench size, mean)"],
    "value": [f"{agree_subs.on_in_top_k.mean():.0%}", f"{agree_subs.off_in_top_k.mean():.0%}",
              f"{agree_subs.bench_size.median():.0f}", f"{(3 / agree_subs.bench_size.clip(lower=3)).mean():.0%}"]})
display(summary)
display(Markdown("Agreement describes how often the transparent heuristic points where the coach went; it does not "
                 "measure decision quality (selection bias: we only observe the chosen option's outcome)."))
""")
code(r"""
imp = sa.impact_windows(B)
display(Markdown(f"**Pre/post windows** (±{cfg.impact_window_minutes:.0f} min, rates per 15 min). Unit = a team's "
                 f"substitution *decision* (simultaneous changes grouped): {len(imp)} decisions with ≥3 min on both "
                 f"sides. {imp.contaminated.mean():.0%} contain a goal, red card or another own decision "
                 f"(goal {imp.goal_in_window.mean():.0%}, own other decision {imp.other_own_decision_in_window.mean():.0%}); "
                 f"the opponent also changed in {imp.opponent_changed_in_window.mean():.0%}."))
display(Markdown("All windows:")); display(sa.impact_summary(imp))
display(Markdown("Clean windows only:")); display(sa.impact_summary(imp, clean_only=True))
viz.impact_chart(imp, "xg", banner=BANNER).show()
""")
md(r"""
> **Causal-inference rule.** These are *observed associations*. Teams that are trailing push forward anyway
> (score effects), opponents change too, fatigue accumulates, time remaining differs and extreme pre-windows regress
> to the mean. Nothing here shows that a substitution *caused* a change. A defensible causal design would need, e.g.,
> matched comparison windows without substitutions in the same game state, which is outside this project's scope.
""")

# =============================================================================
# 13. Managers
# =============================================================================
md(r"""
## 13 · Managerial decision profile
Measured: **observed tactical flexibility** (formation diversity, in-match shifts), **rotation tendency** (lineup
changes), **substitution timing profile** and **game-state response profile**. Not measured — because no valid
instrument exists in event data — leadership, motivation, man-management or "managerial skill". Manager identity
comes from the source's match metadata; managers with fewer than `min_manager_matches` matches are shown as
descriptive only and are never ranked.
""")
code(r"""
display(Markdown(f"**Manager identity source:** {B.manager_source} · coverage "
                 f"{T['managers'].match_id.nunique()}/{len(T['matches'])} matches"))
prof = ma.manager_profiles(B)
display(prof)
FOCUS_MANAGER = B.team_stats[B.team_stats.team_name == FOCUS].manager_name.mode().iloc[0] \
    if B.team_stats.manager_name.notna().any() else None
if FOCUS_MANAGER:
    display(Markdown(f"**{FOCUS_MANAGER} vs pooled small-sample managers** — a reference, not a ranking "
                     "(all pooled managers faced the same opponent, so context differs)."))
    display(ma.pooled_reference(prof, FOCUS_MANAGER, cfg))
""")
code(r"""
if FOCUS_MANAGER:
    viz.manager_formation_distribution(B.team_stats, FOCUS_MANAGER, banner=BANNER).show()
    cont = ma.lineup_continuity(T["appearances"], T["matches"])
    viz.rotation_trend(cont[cont.team_id == team_id_focus], FOCUS, banner=BANNER).show()
    viz.manager_sub_profile(S, FOCUS_MANAGER, cfg.sub_timing_bands, banner=BANNER).show()
    resp = ma.response_after_conceding(B)
    r = resp[resp.manager == FOCUS_MANAGER]
    display(Markdown(f"**Response after conceding ({FOCUS_MANAGER}):** {len(r)} goals conceded; median "
                     f"{r.minutes_to_next_sub.median():.1f} min to the next substitution where one followed "
                     f"({r.minutes_to_next_sub.notna().sum()} cases) — confounded by when goals happen."))
""")

# =============================================================================
# 14. Modelling
# =============================================================================
md(r"""
## 14 · Optional modelling (data-gated): who starts?
| | |
|---|---|
| Prediction unit | player in the focus team's matchday squad, per match |
| Target | named in the Starting XI (1/0) |
| Prediction time | before kick-off |
| Features | only from earlier matches: started previous match, consecutive starts, start share, minutes share, minutes in previous 7/14 days, rest days, goalkeeper flag |
| Split | chronological by match date (first 70 % of matches train, rest test) — never random |
| Baseline | "started the previous match" |
| Gate | ≥ 300 rows and ≥ 15 matches, otherwise no model is fitted |

This models what the coaching staff *did* (observed selection behaviour), not what was optimal.
""")
code(r"""
model = mdl.fit_start_model(B, FOCUS)
display(pd.DataFrame([model["gate"]]))
if model["fitted"]:
    print(model["split"], f"| train rows {model['train_rows']} | test rows {model['test_rows']}")
    display(model["metrics"])
    display(model["coefficients"])
    display(Markdown("**Leakage audit**")); display(model["leakage_audit"])
    viz.confusion_matrix_chart(model["confusion_matrix"], banner=BANNER).show()
    viz.roc_chart(model["roc"], float(model["metrics"].roc_auc.dropna().iloc[0]), banner=BANNER).show()
    viz.calibration_chart(model["calibration"], banner=BANNER).show()
else:
    display(Markdown(f"**No model fitted:** {model['reason']} More matches for one team (e.g. a full season with "
                     "cup fixtures) would be required."))
""")

# =============================================================================
# 15. Findings
# =============================================================================
md(r"""
## 15 · Findings and research interpretation
Answers are generated from the executed data (re-running with another competition updates them). They are
descriptive statements about this sample, with the main alternative explanation alongside.
""")
code(r"""
fam = rd
fs_ = ta.formation_summary(B.team_stats, FOCUS)
fsub = S[S.team_name == FOCUS]
osub = S[S.team_name != FOCUS]
cont_f = ma.lineup_continuity(T["appearances"], T["matches"]).query("team_id == @team_id_focus")
rows = [
 ("RQ1 Role-distinguishing attributes",
  f"Median xG/90 peaks for {fam['xg_p90'].idxmax()}s ({fam['xg_p90'].max()}), interceptions/90 for "
  f"{fam['interceptions_p90'].idxmax()}s, pass completion for {fam['pass_completion_pct'].idxmax()}s "
  f"({fam['pass_completion_pct'].max()}%).", "Role labels are event-position based; tactical roles vary within labels."),
 ("RQ2 Per-90 and role normalisation",
  f"{int(B.season.eligible.sum())} of {len(B.season)} players pass {cfg.min_minutes:.0f} min; raising the threshold "
  f"to 900 leaves {(B.season.minutes_played >= 900).sum()} — leaderboards change (sensitivity table, §7).",
  "Small minutes inflate per-90 extremes."),
 ("RQ3 Formations and outcomes",
  f"{FOCUS} used {len(fs_)} starting formations; most used {fs_.iloc[0]['starting_formation']} "
  f"({fs_.iloc[0]['matches']} matches, {fs_.iloc[0]['points_per_match']} ppm, xG diff "
  f"{fs_.iloc[0]['xg_for'] - fs_.iloc[0]['xg_against']:+.2f}/match).",
  "Formation choice depends on opponent and availability — not a causal comparison."),
 ("RQ4 Substitution timing by state",
  f"{FOCUS}: median sub minute {fsub.minute.median():.0f}', {(fsub.game_state == 'leading').mean():.0%} made while "
  f"leading. Opponents: median {osub.minute.median():.0f}', {(osub.game_state == 'trailing').mean():.0%} while trailing.",
  "Score state is itself driven by team strength (the focus team led most matches)."),
 ("RQ5 Substitute matching",
  f"Heuristic top-3 contained the actual incoming player in {agree_subs.on_in_top_k.mean():.0%} of non-injury subs "
  f"(random ≈ {(3 / agree_subs.bench_size.clip(lower=3)).mean():.0%}).", "Agreement ≠ quality; bench composition varies."),
 ("RQ6 Rotation, minutes and rest",
  f"Mean {cont_f.lineup_changes.mean():.1f} starting-XI changes between consecutive dataset matches; "
  f"pre-match start model F1 {model['metrics'].f1.iloc[1]:.2f} vs 'started previous match' baseline "
  f"{model['metrics'].f1.iloc[0]:.2f} (ROC-AUC {model['metrics'].roc_auc.dropna().iloc[0]:.2f})." if model.get("fitted") else
  f"Mean {cont_f.lineup_changes.mean():.1f} lineup changes; model gate not met.",
  "Cup/European fixtures are missing, so rest days are over-estimated."),
 ("RQ7 Observable manager patterns",
  f"{FOCUS_MANAGER}: {prof.iloc[0]['subs_per_match']} subs/match, first sub median "
  f"{prof.iloc[0]['median_first_sub_minute']:.0f}', formation diversity {prof.iloc[0]['formation_diversity_index']}."
  if FOCUS_MANAGER else "Manager identity unavailable.", "Other managers have ≤2 matches — descriptive only."),
 ("RQ8 Limits to causal claims",
  f"{imp.contaminated.mean():.0%} of pre/post substitution-decision windows contain a goal, red card or another "
  f"own decision, and the opponent also changed in {imp.opponent_changed_in_window.mean():.0%}; deltas are "
  "associations only.", "Score effects, opponent changes, fatigue, regression to the mean."),
]
findings = pd.DataFrame(rows, columns=["research question", "observed answer (this dataset)", "main caveat"])
display(findings.style.hide(axis="index").set_properties(**{"text-align": "left", "white-space": "pre-wrap"}))
""")
md(r"""
**Recommendations for further data collection.** (1) All competitions a team plays (cups, Europe) for valid
workload/rotation proxies; (2) injury/availability feeds from a licensed provider; (3) several full league seasons
(e.g. StatsBomb's complete 2015/16 leagues) for role benchmarks independent of one club; (4) tracking or 360 data
for off-ball and pressing metrics; (5) a manager-tenure table to separate team and manager effects.
""")

# =============================================================================
# 16. Export
# =============================================================================
md(r"""
## 16 · Export and reproducibility
Writes processed tables (`data/processed/`), the run configuration and source manifest (`outputs/exports/`), the
auto-generated **dataset card** and **data dictionary** (`reports/`), a results summary, and interactive HTML copies
of key charts (`outputs/figures/`, PNG too if `kaleido` is installed). In `DEMO_SYNTHETIC` mode everything goes to
`synthetic/` sub-folders and the cards to `outputs/exports/synthetic/`, so synthetic results never overwrite real ones.
""")
code(r"""
inv_out = reporting.export_tables(B)
display(inv_out)
paths = [reporting.write_run_config(B, {"focus_team": FOCUS, "xi_match_id": int(xm.match_id),
                                       "scenario_match_id": int(scen.match_id)}),
         reporting.write_manifest(B),
         reporting.write_dataset_card(B, cfg.reports_dir / "DATASET_CARD.md"),
         reporting.write_data_dictionary(B, cfg.reports_dir / "DATA_DICTIONARY.md"),
         reporting.write_results_summary(B, {"Dataset scale": scale, "Quality checks": B.quality,
                                             "Findings": findings, "Recommended XI": xi.lineup[
                                                 ["slot", "player_name", "score", "coverage_label"]].round(1),
                                             "Manager profiles": prof})]
for p in paths:
    print("written:", Path(p).relative_to(ROOT))
""")
code(r"""
export_figs = {
    "01_coverage_cards": viz.coverage_cards(scale, banner=BANNER),
    "04_leaderboard": viz.leaderboard_chart(B.season_pct, lb_metrics, max(cfg.min_minutes, 450), banner=BANNER),
    "05_player_radar": viz.player_radar(B.season_pct, P.player_id, pa.radar_metrics(P.primary_role, cfg), banner=BANNER),
    "06_comparison_scatter": viz.comparison_scatter(B.season_pct, lb_metrics, cfg.min_minutes, x="xg_p90",
                                                    y="xa_p90", highlight_team=FOCUS, banner=BANNER),
    "13_xi_pitch": viz.xi_pitch(xi.lineup, f"Recommended {XI_FORMATION} XI ({ctx.asof:%Y-%m-%d})", banner=BANNER),
    "15_shot_map": viz.shot_map(shots, f"{FOCUS}: shots", banner=BANNER),
    "17_pass_network": viz.pass_network_chart(nodes, edges, f"{FOCUS} pass network", cut, banner=BANNER),
    "20_sub_timing": viz.sub_timing_histogram(S_grp, cfg.sub_timing_bands, group="group", banner=BANNER),
    "22_role_flow": viz.role_flow_sankey(sa.role_flow(S), banner=BANNER),
    "23_impact": viz.impact_chart(imp, "xg", banner=BANNER),
}
for name, fig in export_figs.items():
    res = viz.export_figure(fig, str(cfg.figures_dir / f"{name}.html"), str(cfg.figures_dir / f"{name}.png"))
print(f"{len(export_figs)} interactive HTML charts written to outputs/figures/ (PNG: {res.get('png')})")
if IN_COLAB:
    import shutil
    from google.colab import files as _f
    shutil.make_archive("/content/football_outputs", "zip", ROOT / "outputs")
    _f.download("/content/football_outputs.zip")
""")

# =============================================================================
# 17. Conclusion & viva
# =============================================================================
md(r"""
## 17 · Conclusion and viva preparation
**Plain-language summary.** The notebook turns StatsBomb event and lineup files into audited tables, role-aware
player metrics and interactive views, and uses them for two decisions coaches actually make — who starts and who comes
on — with every number traceable to a definition and every recommendation limited to information available at the
time.

| The system **can** | The system **cannot** |
|---|---|
| Rank squad players for formation slots with transparent, editable weights | Know fitness, injuries, training, tactics instructions or dressing-room context |
| Enforce lineup constraints and explain omissions | Prove a lineup or substitution is optimal or caused a result |
| Reconstruct who was on the pitch and the score at any minute | Measure leadership, motivation or "managerial skill" |
| Describe managers' observable timing / rotation / formation patterns | Rank managers from 1-2 matches |
| Fit a leakage-free, gated model of observed selection behaviour | Forecast results or player value |

**Key terms.** *Event data* (time-stamped on-ball actions) vs *aggregated statistics*; *per-90*; *percentile
within role*; *xG* (StatsBomb model probability that a shot is scored — provider output); *game state*; *data leakage*;
*chronological split*; *association vs causation*; *Hungarian assignment*.

Full viva question bank with answer prompts: `reports/VIVA_PREPARATION.md`. Presentation outline and live-demo
sequence: same file. Review evidence templates: `reports/REVIEW_1_DATA_COLLECTION.md`,
`reports/REVIEW_2_ANALYSIS_AND_VISUALIZATION.md`.
""")
code(r"""
facts = {"Competition": f"{T['matches'].competition_name.iloc[0]} {T['matches'].season_name.iloc[0]}",
         "Matches analysed": len(T["matches"]), "Events": len(T["events"]), "Teams": len(teams),
         "Players (squads)": T["appearances"].player_id.nunique(), "Substitutions": len(S),
         "Quality checks passed": f"{int((B.quality.status == 'PASS').sum())}/{len(B.quality)}",
         "Total pipeline time (s)": round(parse_seconds + B.timings['features_s'], 1)}
display(Markdown("**Numbers to quote in the viva (from this run)**"))
display(pd.DataFrame(list(facts.items()), columns=["fact", "value"]))
status_badge()
""")


def build() -> Path:
    nb = nbf.v4.new_notebook()
    nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                   "language_info": {"name": "python"},
                   "colab": {"provenance": [], "toc_visible": True}}
    nb.cells = [nbf.v4.new_markdown_cell(t) if k == "md" else nbf.v4.new_code_cell(t) for k, t in CELLS]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, OUT)
    return OUT


if __name__ == "__main__":
    p = build()
    print(f"wrote {p} ({len(CELLS)} cells)")
