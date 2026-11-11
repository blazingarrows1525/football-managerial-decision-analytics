"""Generate the research notebooks from one definition of chapters.

    python scripts/build_notebooks.py

Writes ``notebooks/00 … 06`` (one chapter each, advanced sections on) and
``notebooks/Football_Managerial_Analytics_Complete.ipynb`` (every cell of every chapter, advanced sections on,
plus an optional full chart atlas, in one runnable notebook). Notebooks are thin: each code cell calls the shared ``src`` package, which is the
same code the Streamlit dashboard uses. Execute them with ``python scripts/run_notebooks.py``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks"

SETUP = '''# Setup — locate (or fetch) the project code, import the shared package, load the workspace
import os, subprocess, sys, time
from pathlib import Path

REPO_URL = "https://github.com/blazingarrows1525/football-managerial-decision-analytics"
ROOT = next((p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "workspace.py").exists()), None)
if ROOT is None:  # opened on its own (e.g. Google Colab): fetch the project code once, next to this notebook
    ROOT = Path.cwd() / "football-managerial-decision-analytics"
    if not (ROOT / "src" / "workspace.py").exists():
        subprocess.run(["git", "clone", "--depth", "1", REPO_URL, str(ROOT)], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")], check=True)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("FMA_PROJECT_ROOT", str(ROOT))  # data cache and outputs live inside the project folder

import numpy as np
import pandas as pd
from IPython.display import Markdown, display

from src.reporting.notebook_tools import (catalogue, explorer, implication, interpret, limitation, show, start,
                                          timed, timings)

pd.set_option("display.max_columns", 40, "display.width", 200, "display.float_format", "{:.3f}".format)
RUN_ADVANCED_GALLERY = __ADVANCED__   # heavier, optional sections; the core story does not depend on them
SEED = 42                             # every resampling and model step takes this seed explicitly

ws = start(seed=SEED)                 # first run downloads and parses; later runs read the processed cache
B, T, FOCUS = ws.bundle, ws.tables, ws.focus
tm = ws.team_matches()                # the focus team's matches in date order
print(f"Advanced sections: {'on' if RUN_ADVANCED_GALLERY else 'off'} · Python {sys.version.split()[0]} · pandas {pd.__version__}")'''

ATTRIBUTION = ("> **Data.** StatsBomb Open Data (https://github.com/hudl/open-data), provided by StatsBomb / Hudl, "
               "used for educational, non-commercial research. Raw data are downloaded from the official "
               "repository at run time and are not redistributed here. Every figure carries its chart ID from "
               "`docs/VISUALIZATION_CATALOGUE.md`.")


def md(text: str, core: bool = True):
    return ("md", text.strip("\n"), core, False)


def code(text: str, core: bool = True, advanced: bool = False):
    return ("code", text.strip("\n"), core, advanced)


# =====================================================================================================
CH0 = ("00_Project_Research_And_Methodology", "Project, research design and methodology", [
    md("""
## A · Problem, objectives and scope

**Research question → data and method → chart → interpretation → managerial implication and limitation.**
Every chapter follows this sequence.

### Core question
How can real football event, lineup, player and match-state data be transformed into transparent and
interactive evidence to support starting-XI selection, role fit, tactical interpretation, substitution choices,
rotation analysis and the evaluation of observable managerial decisions?

The system is **decision support, not an oracle**: it states uncertainty and data limits and never claims that
a chart proves a tactical cause or a manager's quality.

### Objectives
1. Build a reproducible pipeline from the published source files to validated analytical tables.
2. Define every metric with its formula, denominator and caveat, and reuse the same definitions in the
   notebooks and in the dashboard.
3. Answer eight research questions with charts that state their sample and their limits.
4. Provide two transparent decision-support tools (starting XI, substitutions) and compare them with what
   actually happened.
5. Quantify uncertainty: effect sizes, bootstrap intervals, false-discovery control, statistical power.
6. Fit a predictive model only where the sample supports it, against a naive baseline, without leakage.
"""),
    md("""
### Hypotheses (stated before looking at the results; each is tested in the chapter named)

| # | Hypothesis | Where tested | How |
|---|---|---|---|
| H1 | Chance quality for and against is more strongly associated with goal difference than possession is | 05 | Spearman ρ with bootstrap CI and FDR control |
| H2 | Results ran ahead of shot-based expectation | 02 | points vs simulated expected points |
| H3 | Chance creation is concentrated in a few players | 02 | cumulative share and Gini of xG + xA |
| H4 | Build-up runs through a small number of hub players | 03 | PageRank and betweenness on pass networks |
| H5 | Past selection explains most starting decisions | 05 | time-ordered cross-validation against a baseline rule |
| H6 | Substitution timing differs by score state | 04 | timing distributions by state (descriptive) |

A hypothesis that the data cannot decide is reported as undecided, not as confirmed.
"""),
    code('''
# Scope of the loaded data — computed, not typed in
m = T["matches"]
scope = pd.DataFrame([
    ("Competition / season", f"{m.competition_name.iloc[0]} {m.season_name.iloc[0]} (competition {B.config.competition_id}, season {B.config.season_id})"),
    ("Matches analysed / published", f"{len(m)} / {B.matches_available}"),
    ("Date range", f"{m.match_date.min():%d %b %Y} – {m.match_date.max():%d %b %Y}"),
    ("Teams / players in match-day squads", f"{B.team_stats.team_name.nunique()} / {T['appearances'].player_id.nunique()}"),
    ("Events", f"{len(T['events']):,}"),
    ("Focus team and its matches", f"{FOCUS} · {len(tm)}"),
    ("Raw files / size", f"{len(B.manifest)} / {B.manifest.bytes.sum() / 1e6:.1f} MB"),
    ("Domain rules passed", f"{int((B.quality.status == 'PASS').sum())}/{len(B.quality)}"),
], columns=["item", "value"])
display(scope)
others = B.team_stats[B.team_stats.team_name != FOCUS].groupby("team_name").match_id.nunique()
times = f"{others.min()}" if others.min() == others.max() else f"{others.min()}–{others.max()}"
interpret(f"Every analysed match involves {FOCUS}; the other {len(others)} teams appear {times} times each. The sample is **team-centric**: it supports statements about {FOCUS} in these matches and "
          f"does not describe the league.")
'''),
    md("""
## Methodology

```
StatsBomb Open Data (JSON over HTTPS)                src/data/statsbomb_client.py   cached, hashed, retried
        │
        ▼
canonical tables: matches · managers · squads · events            src/data/parsers.py + validators.py
        │   minutes reconstructed from Starting XI / Substitution / sending-off events
        ▼
feature tables: event flags · player match & season (per 90, role percentiles) · team match stats
        │                                                         src/features/*
        ▼
analytics: descriptive · statistics · uncertainty · clustering · models · XI and substitution heuristics
        │                                                         src/analytics/*
        ▼
chart registry (one renderer + prerequisites + status per chart)  src/visualization/*
        │
        ├── research notebooks (this folder)        └── Streamlit dashboard (app.py, pages/)
```

**Scale.** About 138 thousand events from one club-season: event-level sports analytics on a single machine.
pandas is the right tool at this volume; no distributed engine is used or claimed. The per-match file layout
would map directly onto a distributed map step if many seasons were added.

**What is not in the data** and is therefore never analysed: player age, height, injuries, fitness or GPS
load, optical tracking, post-shot xG, attendance, weather, market value. Chapter 01 verifies this from the
tables.
"""),
    code('''
# The chart catalogue: what exists, what is available for this data, and why some entries are not
cat = catalogue(ws)
display(cat.groupby(["category", "status"]).size().unstack(fill_value=0))
display(cat[cat.status != "implemented_and_available"][["chart_id", "name", "status", "reason"]])
n_ok = int((cat.status == "implemented_and_available").sum())
interpret(f"{n_ok} of {len(cat)} catalogue entries have a renderer whose prerequisites are met by the loaded data. "
          f"The rest are listed with the reason — an unsupported data modality (tracking), an optional file that "
          f"is not downloaded (360 frames), or no legitimate target. Nothing is filled in to make a chart possible.")
'''),
    code('''
# Chart explorer: search the catalogue and render one chart on demand.
# With ipywidgets in a live kernel this shows controls; in a headless run it shows the table and one example.
explorer(ws, default="C-042")
'''),
    md("""
## Reproducibility

- `pip install -r requirements.txt`, then run any notebook top to bottom in a fresh kernel.
- `python scripts/run_notebooks.py` executes all of them and writes an execution report.
- Seeds are explicit (`SEED = 42`); the global NumPy generator is never seeded.
- Warnings are not suppressed globally.
- The committed copies were executed with `FMA_STATIC=1`, which stores figures as static images so they are
  visible on GitHub; without it the same cells produce interactive Plotly figures.
"""),
    code('''
from src.reporting.report_builder import environment
display(pd.DataFrame(list(environment().items()), columns=["component", "version"]))
display(timings())
'''),
])

# =====================================================================================================
CH1 = ("01_Data_Audit_And_EDA", "Data source, provenance, quality audit and exploratory analysis", [
    md("""
## B · Data source, provenance and quality

**Research question.** Where do the data come from, under which terms, and can the parsed tables be trusted
for the analyses built on them?

**Data and method.** The download client records the URL, byte size, SHA-256 hash and write time of every raw
file. Parsed tables are checked against sixteen domain rules and fourteen table contracts (grain, key, required
fields).
"""),
    code('''
from src.data import provenance
from src.data.schemas import check_contracts

man = B.manifest
display(provenance.source_register()[["source", "role_in_project", "terms", "status"]])
display(man.groupby(["resource", "status"]).agg(files=("relative_path", "size"), MB=("bytes", lambda s: round(s.sum() / 1e6, 2))))
display(man[["relative_path", "bytes", "sha256", "file_written_utc"]].head(4))
print("Terms recorded from the source licence:")
for t in provenance.TERMS_SUMMARY:
    print(" -", t)
interpret(f"{len(man)} raw files ({man.bytes.sum() / 1e6:.1f} MB) were read with {int((man.status != 'ok').sum())} failures; "
          f"each has a SHA-256 hash in `data/manifest/source_manifest.json`. The user agreement allows research "
          f"use and public sharing of analysis but not redistribution of the data, so this repository contains "
          f"no raw or processed event tables.")
'''),
    code('''
show("A-001", ws)
contracts = check_contracts(B)
display(contracts[["table", "origin", "rows", "grain", "status", "duplicate_keys"]])
show("A-016", ws)
q = B.quality
interpret(f"{int((q.status == 'PASS').sum())} of {len(q)} domain rules and {int((contracts.status == 'PASS').sum())} of "
          f"{len(contracts)} table contracts pass: event IDs are unique, coordinates lie on the 120 × 80 pitch, xG is "
          f"within [0, 1] and attached only to shots, every team-match has eleven starters and one goalkeeper, "
          f"on-pitch spells do not overlap and the goals rebuilt from events equal the published scores.")
limitation("Passing validation shows internal consistency, not that the provider's event tagging is error-free.")
'''),
    md("""
### Missing values, duplicates and outliers

**Question.** Which gaps are structural, and are extreme values errors or football?
"""),
    code('''
show("A-003", ws)
show("A-005", ws)
ev = T["events"]
shots = ev[ev.type == "Shot"]
interpret(f"Most fields are sparse by design: `shot_xg` is present on {ev.shot_xg.notna().mean():.1%} of all events but on "
          f"{shots.shot_xg.notna().mean():.0%} of the {len(shots):,} shots; pass end locations exist for "
          f"{ev.loc[ev.type == 'Pass', 'end_x'].notna().mean():.0%} of passes. Missing values are kept as missing and "
          f"are never read as zero.")
'''),
    code('''
from src.visualization import audit
dups = audit.duplicate_audit_table(B)
show("A-006", ws)
show("A-010", ws)
interpret(f"{int(dups.full_row_duplicates.sum())} duplicated rows and {int(dups.key_duplicates.fillna(0).sum())} duplicated keys across "
          f"{len(dups)} tables. Values beyond 1.5 × IQR are real events (long passes, penalties, long stoppages) and are kept.")
'''),
    code('''
show("A-004", ws)
show("A-008", ws)
show("A-009", ws)
''', core=False, advanced=True),
    md("""
### What the data support, and what they do not

**Question.** Which analytical inputs exist? The answer is read from the tables, not assumed.
"""),
    code('''
show("A-012", ws)
show("A-011", ws)
fa = audit.feature_availability_table(B)
absent = fa[fa.status != "available"].feature.tolist()
interpret(f"{int((fa.status == 'available').sum())} of {len(fa)} input groups are present. Not available: "
          + "; ".join(absent) + ". None of these is imputed, and no chart that needs them is drawn.")
implication("Selection and substitution tools built on this data cannot know who is injured or tired; the analyst "
            "must supply availability.")
'''),
    code('''
# Optional 360 freeze frames: published by the source, downloaded per match only on request.
# When files are cached, check that their identifiers actually join to the event file before using them.
import json
d360 = B.config.raw_dir / "three-sixty"
rows = []
for p in sorted(d360.glob("*.json")) if d360.exists() else []:
    frames = json.loads(p.read_text(encoding="utf-8"))
    ids = set(ev.loc[ev.match_id == int(p.stem), "event_id"])
    rows.append({"match_id": int(p.stem), "frames": len(frames), "joined_to_events": len(ids & {f["event_uuid"] for f in frames})})
check360 = pd.DataFrame(rows)
if len(check360):
    display(check360)
    bad = check360[check360.joined_to_events == 0]
    interpret(f"{len(check360)} optional 360 file(s) are cached. " + (f"{len(bad)} of them share no identifier with their "
              f"event file — a source inconsistency; those frames are not used." if len(bad) else "All of them join to their events."))
else:
    print("No 360 file is cached; chart E-129 is reported as implemented_but_unavailable.")
show("A-014", ws)
'''),
    md("""
## C · Feature engineering and exploratory analysis

**Question.** After normalising for playing time and role, how are player metrics distributed and how do they
relate?

**Data and method.** Minutes are rebuilt from the event stream. Per-90 values are `value / minutes × 90` and
percentiles are computed within the player's role group among players above the minutes threshold.
"""),
    code('''
from src.features.player_features import metric_dictionary
from src.reporting.report_builder import DERIVED_METRICS
from src.workspace import EDA_METRICS

display(metric_dictionary().head(12))
display(pd.DataFrame(DERIVED_METRICS, columns=["metric", "formula", "inputs", "caveat"]).head(8))
s = B.season
print(f"{int(s.eligible.sum())} of {len(s)} player-team rows have at least {B.config.min_minutes:.0f} minutes; "
      f"{int((s.minutes_played >= 900).sum())} have at least 900.")
show("L-269", ws)
'''),
    code('''
from src.analytics import descriptive as desc
rm = desc.role_medians(B, ["xg_p90", "key_passes_p90", "progressive_passes_p90", "interceptions_p90", "pass_completion_pct"])
display(rm)
show("G-156", ws)
show("B-018", ws, metric="xg_p90")
fams = rm.drop(index="Goalkeeper", errors="ignore")
interpret(f"Role families separate clearly on some metrics: median xG/90 is highest for {fams.xg_p90.idxmax()}s "
          f"({fams.xg_p90.max():.2f}) and lowest for {fams.xg_p90.idxmin()}s ({fams.xg_p90.min():.2f}); interceptions/90 "
          f"peak for {fams.interceptions_p90.idxmax()}s ({fams.interceptions_p90.max():.2f}). Group sizes: "
          + ", ".join(f"{i} {int(n)}" for i, n in rm.players.items()) + ".")
implication("Compare players inside their role group. A raw leaderboard mostly re-discovers positions.")
'''),
    code('''
from src.analytics import statistical_tests as stt
el = ws.eligible()
r, n = stt.correlation_matrix(el, EDA_METRICS, "spearman")
show("J-200", ws)
pairs = r.where(np.triu(np.ones(r.shape, bool), 1)).stack().sort_values()
lo, hi = pairs.index[0], pairs.index[-1]
interpret(f"Among {len(el)} eligible players the strongest positive rank correlation is between {hi[0]} and {hi[1]} "
          f"(ρ = {pairs.iloc[-1]:.2f}) and the strongest negative between {lo[0]} and {lo[1]} (ρ = {pairs.iloc[0]:.2f}). "
          f"Pairwise n ranges from {int(n.values.min())} to {int(n.values.max())}.")
limitation("Players are nested in teams and opponents are observed only against the focus team; these are "
           "descriptive associations.")
'''),
    code('''
show("B-019", ws, metric="progressive_passes_p90")
show("B-022", ws, metric="pressures_p90")
show("D-074", ws)
show("L-246", ws)
''', core=False, advanced=True),
    code("display(timings().tail(12))", core=False),
])

# =====================================================================================================
CH2 = ("02_Player_Team_Match_Analytics", "Match, team and player performance", [
    md("""
## D · Match, team and player performance

**Research question.** How did the team perform, how much of it is explained by chance quality, and which
players drive it?

**Data and method.** Team match statistics (goals, StatsBomb xG, shots, pass-share possession proxy, field
tilt, PPDA) and player season tables with per-90 rates and role percentiles. Expected points simulate each shot
as a Bernoulli trial with its xG.
"""),
    code('''
from src.analytics import descriptive as desc
k = desc.season_kpis(B, FOCUS)
xp = ws.xpts(); xp = xp[xp.team_name == FOCUS]
display(pd.DataFrame([{"matches": k["matches"], "W-D-L": f"{k['wins']}-{k['draws']}-{k['losses']}", "points": k["points"],
                       "expected points": round(xp.xpts.sum(), 1), "goals": f"{k['goals_for']}-{k['goals_against']}",
                       "xG": f"{k['xg_for']:.1f}-{k['xg_against']:.1f}", "players used": k["players_used"]}]))
show("L-262", ws)
show("C-042", ws)
gap = k["points"] - xp.xpts.sum()
interpret(f"{FOCUS} took {k['points']:.0f} points from {k['matches']} matches against {xp.xpts.sum():.1f} expected from shot "
          f"quality — {abs(gap):.1f} {'more' if gap > 0 else 'fewer'} than the simulation — and scored {k['goals_for']} "
          f"goals from {k['xg_for']:.1f} xG. Mean xG difference per match: {tm.xg_diff.mean():+.2f}.")
implication("Judge performances on chances created and conceded; the points total alone flatters or punishes a "
            "team for finishing and goalkeeping variance.")
limitation("Expected points are a model output: shots are treated as independent and game state is ignored.")
'''),
    code('''
show("C-046", ws)
show("C-059", ws)
split = desc.shot_origin_split(B, FOCUS).set_index(["side", "origin"])
f = split.loc["for"]; a = split.loc["against"]
interpret(f"{FOCUS} took {int(f.shots.sum())} shots against {int(a.shots.sum())} for opponents; xG per shot was "
          f"{f.xg.sum() / f.shots.sum():.3f} against {a.xg.sum() / a.shots.sum():.3f}. The gap in **volume** is far larger than "
          f"the gap in **quality**. Possessions that began with a corner, free kick or throw-in produced "
          f"{int(f.loc['Restart-initiated', 'goals'])} of the team's goals from shots.")
'''),
    code('''
show("C-050", ws)
show("C-064", ws)
st_time = ws.state_time()
tot = st_time[["leading", "drawing", "trailing"]].sum()
z, cv = desc.team_consistency(B, FOCUS)
interpret(f"The team spent {tot.leading / tot.sum():.0%} of its minutes leading, {tot.drawing / tot.sum():.0%} level and "
          f"{tot.trailing / tot.sum():.0%} behind. The most stable match metrics are {cv.index[0]} (CV {cv.iloc[0]:.2f}) and "
          f"{cv.index[1]} ({cv.iloc[1]:.2f}); the most volatile are {cv.index[-1]} ({cv.iloc[-1]:.2f}) and {cv.index[-2]} ({cv.iloc[-2]:.2f}).")
implication("Swings in the volatile metrics are normal match-to-match noise; persistent change in the stable "
            "ones is the earlier warning sign.")
'''),
    code('''
show("C-043", ws)
show("C-047", ws)
show("C-055", ws)
show("C-063", ws)
''', core=False, advanced=True),
    md("""
### One match in detail

**Question.** What happened, in order, in a representative match? The default is the match with the median xG
difference — neither the best nor the worst.
"""),
    code('''
mid = ws.default_match()
print(ws.match_label(mid))
show("C-049", ws, match_id=mid)
show("L-248", ws, match_id=mid)
show("L-249", ws, match_id=mid)
limitation("The interval chart is xG per five minutes — a description of when chances occurred, not a validated "
           "momentum measure.")
'''),
    md("""
### Players

**Question.** Who contributes what, relative to players of the same role, and how certain is it?
"""),
    code('''
sq = ws.squad()
display(sq[["player_name", "primary_position", "minutes_played", "starts", "goals", "xg", "assists", "xa", "xg_p90", "xa_p90",
            "progressive_passes_p90", "benchmark_group", "benchmark_n", "coverage_label"]].head(14))
show("C-044", ws)
show("B-029", ws)
conc = desc.concentration(sq.set_index("player_name").eval("xg + xa"))
interpret(f"The top three contributors ({', '.join(conc.label.head(3))}) account for {conc.share.head(3).sum():.0%} of the "
          f"squad's xG + xA; {int((conc.cumulative_share < 0.8).sum() + 1)} players are needed to reach 80%. "
          f"Gini coefficient {desc.gini(conc.value):.2f}.")
implication("Like-for-like cover and minutes management matter most for the few players who create the chances.")
'''),
    code('''
pid = ws.default_player()
print("Example player:", ws.player_name(pid))
show("D-069", ws, player_id=pid)
show("D-070", ws, player_id=pid)
show("D-101", ws, player_id=pid)
limitation("Similarity is distance in standardised per-90 space within this dataset; it is not a replacement "
           "recommendation.")
'''),
    code('''
from src.analytics import uncertainty as unc
reg = sq[(sq.minutes_played >= 900) & (sq.primary_role != "GK")]
ci = unc.bootstrap_rate_intervals(B.pms, reg, "xg", seed=SEED)
show("D-079", ws, metric="xg_p90")
show("D-102", ws)
top, second = ci.iloc[-1], ci.iloc[-2]
sep = "is clearly separated from" if second.hi < top.lo else "overlaps with"
cons = ws.consistency()
steady = cons[cons.prog_mean > cons.prog_mean.median()].sort_values("prog_cv").iloc[0]
interpret(f"{top.player} leads on xG per 90 ({top.rate_p90:.2f}, 95% bootstrap interval {top.lo:.2f}–{top.hi:.2f}), which {sep} "
          f"{second.player} ({second.lo:.2f}–{second.hi:.2f}). Among above-median progressors {steady.player_name} is the "
          f"steadiest (CV {steady.prog_cv:.2f} at {steady.prog_mean:.1f} progressive actions per 90).")
implication("Rank attackers in tiers. Inside overlapping intervals the order is not established by one season.")
'''),
    code('''
show("L-264", ws)
show("D-104", ws)
show("D-106", ws)
show("B-035", ws)
show("D-107", ws, player_id=ws.default_player())
''', core=False, advanced=True),
])

# =====================================================================================================
CH3 = ("03_Pitch_Tactical_Visualizations", "Pitch, spatial and tactical analysis", [
    md("""
## E · Pitch, spatial and tactical analysis

**Research question.** Where does the team play, how does it move the ball forward, and through whom?

**Data and method.** StatsBomb coordinates: a 120 × 80 pitch with the origin at the top-left corner, and
**every team recorded attacking left to right in both halves**. No per-half flip is applied. Maps that draw
more than 4,000 points or 500 arrows show a seeded random sample and say so.
"""),
    code('''
from src.features.event_features import EVENT_KINDS, select_events
from src.visualization import spatial

fl = ws.flags
tid = ws.team_id()
# Orientation check on the data: shots must cluster near x = 120 for both teams and in both halves
sh = fl[fl.type == "Shot"]
display(sh.assign(side=np.where(sh.team_id == tid, FOCUS, "opponents")).groupby(["side", "period"]).x.agg(["size", "median", "min"]).round(1))
m2 = spatial.mirror(sh.head(3)[["x", "y"]])
print("mirror() flips both axes:", sh.head(3)[["x", "y"]].round(1).values.tolist(), "→", m2.round(1).values.tolist())
interpret(f"Median shot location is x = {sh.x.median():.0f} for every team and half, confirming that the source records "
          f"each team attacking towards x = 120 throughout. The coordinate transform is covered by `tests/test_chart_renderers.py`.")
'''),
    code('''
mid = ws.default_match()
print(ws.match_label(mid))
show("E-110", ws, match_id=mid)
show("E-111", ws, match_id=mid)
show("E-131", ws, match_id=mid)
'''),
    code('''
from src.analytics import descriptive as desc
touches = select_events(fl, "Touches", team_id=tid)
zt = desc.zone_table(touches, 3, 1)
show("E-121", ws, kind="Touches")
show("E-133", ws)
show("E-134", ws)
share = (zt.iloc[0] / zt.values.sum())
prog = select_events(fl, "Progressive passes", team_id=tid)
lane = pd.Series(np.clip((prog.y / 80 * 5).astype(int), 0, 4)).map(dict(enumerate(spatial.LANES))).value_counts(normalize=True)
interpret(f"{share.iloc[2]:.0%} of the team's {len(touches):,} touches are in the attacking third and {share.iloc[0]:.0%} in "
          f"its own third. Of {len(prog):,} progressive passes, {lane.iloc[0]:.0%} start in the {lane.index[0].lower()} "
          f"and {lane.iloc[-1]:.0%} in the {lane.index[-1].lower()}.")
implication("The lanes used for progression show where an opponent's block is most often played through — and "
            "where the team's own access would suffer if that side were closed.")
limitation("Event locations are where the ball was; off-ball positioning is not in event data.")
'''),
    code('''
show("E-113", ws)
show("E-120", ws, kind="Pressures")
show("D-097", ws, player_id=ws.default_player(), match_id=mid)
show("E-132", ws, match_id=mid)
show("L-265", ws)
''', core=False, advanced=True),
    md("""
### Expected Threat (project-computed)

**Question.** Which areas carry the most threat in these matches, and who moves the ball into them?

**Method.** A 16 × 12 grid; moves are passes and carries; a failed pass passes on no value; the value of a shot
from a cell is the mean StatsBomb xG of shots taken there; the surface is the fixed point of
`xT(c) = P(shot|c)·value(c) + P(move|c)·Σ T(c→c')·xT(c')`. It is **fitted on the analysed matches themselves**
and is a derived project value, not a StatsBomb field.
"""),
    code('''
from src.features import values
g = ws.xt_grid()
display(values.xt_sanity(g))
show("L-263", ws)
show("L-264", ws)
px = ws.player_xt(); mine = px[px.team_name == FOCUS].head(3)
interpret(f"The grid was fitted on {g.n_moves:,} passes and carries and {g.n_shots:,} shots and converged in {g.iterations} "
          f"iterations; the highest cell is worth {g.grid.max():.3f}. {mine.player_name.iloc[0]} added the most threat "
          f"({mine.xt_total.iloc[0]:.1f}; {mine.xt_pass.iloc[0]:.1f} by passing, {mine.xt_carry.iloc[0]:.1f} by carrying).")
limitation("In-sample and descriptive: with 34 matches the surface is noisy cell by cell, and it credits only the "
           "player who moved the ball.")
'''),
    md("""
## F · Passing networks

**Question.** Who connects the team, and how dependent is the structure on individual players?

**Method.** One directed graph per match from completed passes before the first substitution, so every node
shared the pitch. Node position = mean pass origin; PageRank is weighted by pass count; betweenness uses
1 / passes as distance.
"""),
    code('''
show("F-140", ws, match_id=mid)
show("F-139", ws)
show("F-141", ws)
cs = ws.centrality_summary()
hub, bridge = cs.iloc[-1], cs.sort_values("betweenness").iloc[-1]
who = (f"{hub.player} has both the highest mean PageRank ({hub.pagerank:.3f}) and the highest mean betweenness "
       f"({bridge.betweenness:.3f})" if hub.player == bridge.player else
       f"{hub.player} has the highest mean PageRank ({hub.pagerank:.3f}) and {bridge.player} the highest mean "
       f"betweenness ({bridge.betweenness:.3f})")
interpret(f"Across {ws.centrality().match_id.nunique()} match networks {who}. "
          f"The four highest-PageRank players are {', '.join(cs.player.tail(4)[::-1])}.")
implication("A structure that runs through one or two players is efficient and exposed: plan the build-up for "
            "matches in which the hub is pressed or absent.")
limitation("Centrality describes the recorded pass graph; it is not a measure of player quality.")
'''),
    code('''
show("F-146", ws, match_id=mid)
show("F-144", ws)
show("F-148", ws)
show("F-147", ws)
''', core=False, advanced=True),
    md("""
### Formations and what cannot be drawn

A formation here is the label recorded on the Starting XI or Tactical Shift event — a nominal description, not
the team's shape in and out of possession.
"""),
    code('''
from src.features.team_features import formation_summary
from src.visualization import registry
fs = formation_summary(B.team_stats, FOCUS)
display(fs)
show("C-057", ws)
show("G-152", ws, match_id=mid)
interpret(f"{FOCUS} started in {len(fs)} formations; {fs.starting_formation.iloc[0]} in {int(fs.matches.iloc[0])} of {len(tm)} "
          f"matches. Differences in results between formations are confounded by opponent and availability.")
for cid in ("E-126", "E-127", "E-128"):
    s = registry.get(cid)
    print(f"{cid} {s.name}: not implemented — {s.unavailable_reason}")
show("E-129", ws, match_id=int(tm.match_id.iloc[0]))
'''),
])

# =====================================================================================================
CH4 = ("04_Starting_XI_And_Substitutions", "Starting XI and substitution decision support", [
    md("""
## F · Starting XI decision support

**Research question.** Which eleven does the evidence available *before* a match shortlist for a formation, why
is each player in it, and how sensitive is that to the weights?

**Data and method.** Candidates are players seen in recent match-day squads before the decision point. Each
candidate–slot score is

`(0.40·role fit + 0.20·recent form + 0.15·evidence volume + 0.15·minutes-based exposure + 0.10·continuity) × position compatibility`

with components on 0–100. Players are assigned to slots with the Hungarian algorithm under hard constraints
(eleven distinct players, one goalkeeper, eligibility, squad membership). **It is a transparent heuristic:
"best" means best under these weights and constraints.**
"""),
    code('''
from src.analytics import lineup_optimizer as xi
mid = ws.default_match()
p = ws.params()
ctx = ws.xi_context(FOCUS, mid)
res = ws.xi_result(FOCUS, mid, p.formation)
print(f"Decision point: before {ws.match_label(mid)} · formation {p.formation}")
print("Pool:", ctx.pool_description)
display(pd.DataFrame([B.config.xi_score_weights]))
show("G-149", ws, match_id=mid)
show("G-166", ws, match_id=mid)
display(res.lineup[["slot", "player_name", "primary_role", "compatibility", "role_fit", "recent_form", "sample_reliability",
                    "workload_suitability", "lineup_continuity", "score", "coverage_label"]].round(1))
print("Optimiser warnings:", res.warnings or "none")
'''),
    code('''
cmp_, share = xi.compare_with_actual(res, T["appearances"], mid, ws.team_id())
show("G-150", ws, match_id=mid)
show("G-169", ws, match_id=mid)
only_model = cmp_[cmp_.in_recommended & ~cmp_.in_actual].player_name.tolist()
only_actual = cmp_[~cmp_.in_recommended & cmp_.in_actual].player_name.tolist()
interpret(f"{share:.0%} of the players who actually started are in the shortlist. Shortlisted but not selected: "
          f"{', '.join(only_model) or 'none'}; selected but not shortlisted: {', '.join(only_actual) or 'none'}.")
limitation("Agreement measures similarity to the manager's choice, not whether either was better. The source has "
           "no injury, fitness or training information, so a player the manager could not pick may still be shortlisted.")
'''),
    code('''
# Sensitivity: does the shortlist change when the weights change?
import dataclasses
base_ids = set(res.lineup.player_id)
rows = []
for name, w in {"configured": B.config.xi_score_weights,
                "role fit only": {"role_fit": 1, "recent_form": 0, "sample_reliability": 0, "workload_suitability": 0, "lineup_continuity": 0},
                "form-led": {"role_fit": .2, "recent_form": .5, "sample_reliability": .1, "workload_suitability": .1, "lineup_continuity": .1},
                "continuity-led": {"role_fit": .2, "recent_form": .1, "sample_reliability": .1, "workload_suitability": .1, "lineup_continuity": .5},
                "rotation-led": {"role_fit": .3, "recent_form": .1, "sample_reliability": .1, "workload_suitability": .5, "lineup_continuity": 0}}.items():
    r2 = xi.optimize_xi(ctx, p.formation, dataclasses.replace(B.config, xi_score_weights=w))
    ids = set(r2.lineup.player_id)
    rows.append({"weighting": name, "players kept from configured XI": len(ids & base_ids), "total score": round(r2.total_score, 1),
                 "new players": ", ".join(r2.lineup[~r2.lineup.player_id.isin(base_ids)].player_name) or "—"})
sens = pd.DataFrame(rows)
display(sens)
show("G-167", ws, match_id=mid)
interpret(f"Across five weightings between {sens['players kept from configured XI'].min()} and 11 players stay the same. "
          f"The slots that change are the ones where the evidence does not separate the candidates.")
implication("The tool is most useful as a way to see which slots are genuinely open and what each weighting "
            "assumes — not as a single answer.")
'''),
    code('''
show("G-151", ws, match_id=mid)
show("G-168", ws, match_id=mid)
show("D-103", ws)
show("G-165", ws)
''', core=False, advanced=True),
    code('''
# Backtest: rebuild the shortlist before every match from earlier matches only, compare with the actual XI
with timed("XI backtest"):
    ag = ws.xi_agreement()
show("L-267", ws)
interpret(f"Over {len(ag)} matches the shortlist shares {ag.agreement_pct.mean():.1f}% of the actual XI on average "
          f"(minimum {ag.agreement_pct.min():.0f}%, maximum {ag.agreement_pct.max():.0f}%).")
limitation("High agreement reflects a stable core that any sensible rule would pick; it is not evidence of "
           "decision quality.")
'''),
    md("""
## Substitution intelligence

**Research question.** When and in which situations are changes made, who replaces whom, and which bench
options does the evidence shortlist at a given moment?

**Method.** Each substitution is enriched with the score state from the reconstructed goal timeline, the
manpower state from sending-offs, a timing band, the roles of both players and the substitution window under a
configured five-substitutes / three-windows rule. Historical patterns are **descriptive**; scenario shortlists
are **counterfactual simulations**.
"""),
    code('''
S = B.subs; mine = S[S.team_name == FOCUS]; others = S[S.team_name != FOCUS]
show("H-171", ws)
show("H-174", ws)
show("H-173", ws)
interpret(f"{FOCUS} made {len(mine)} substitutions ({len(mine) / len(tm):.2f} per match) at a median minute of {mine.minute.median():.0f}; "
          f"{(mine.game_state == 'leading').mean():.0%} came while leading and {mine.like_for_like.astype(bool).mean():.0%} were "
          f"like-for-like by role. Opponents: median minute {others.minute.median():.0f}, {(others.game_state == 'trailing').mean():.0%} while trailing.")
limitation("Score state is driven by team strength: a team that usually leads makes most changes while leading "
           "whatever its intent. A substitution alone says nothing about injury or fatigue.")
'''),
    code('''
from src.analytics import substitution_analysis as sa
minute = 65.0
rec = ws.sub_scenario(FOCUS, mid, minute)
cx = rec["context"]
print(f"{ws.match_label(mid)} at {minute:.0f}': {cx['team_score']}-{cx['opponent_score']} ({cx['game_state']}), "
      f"{cx['subs_used']} substitutions used, {cx['subs_remaining']} remaining · intent '{rec['intent']}' ({rec.get('intent_reason', '')})")
print("Rule source:", cx["rule_source"])
show("H-180", ws, match_id=mid, minute=minute)
show("H-181", ws, match_id=mid, minute=minute)
show("H-182", ws, match_id=mid, minute=minute)
if rec["status"] == "ok":
    on = rec["recommended_on"]
    interpret(f"The heuristic would take off {rec['recommended_off']['player_name']} ({rec['recommended_off']['reasons']}) and shortlist "
              f"{on['player_name']} (score {on['candidate_score']:.0f}; {on['evidence']}). Availability: {on['injury_status']}.")
limitation("A counterfactual shortlist under stated weights. It is not a forecast and cannot say a different "
           "change would have altered the result.")
'''),
    code('''
imp = ws.impact(); imp_t = imp[imp.team_name == FOCUS]
show("H-175", ws)
display(sa.impact_summary(imp_t))
interpret(f"Of {len(imp_t)} substitution decisions, {imp_t.contaminated.mean():.0%} have a goal, a red card or another own "
          f"change inside the before/after window and the opponent also changed in {imp_t.opponent_changed_in_window.mean():.0%}. "
          f"The median change in team xG per window is {imp_t.delta_team_xg.median():+.3f}.")
limitation("Before/after differences are confounded by score, opponent changes, fatigue and regression to the "
           "mean. They are not effects of the substitution.")
'''),
    code('''
with timed("substitution backtest"):
    sb = ws.sub_agreement()
rnd = (3 / sb.bench_size.clip(lower=3)).mean()
display(sb.head(8))
interpret(f"For {len(sb)} non-injury substitutions the player who actually came on was in the heuristic's top three "
          f"{sb.on_in_top_k.mean():.1%} of the time; picking three bench players at random would manage about {rnd:.0%}.")
show("H-178", ws)
show("H-179", ws, match_id=mid)
'''),
])

# =====================================================================================================
CH5 = ("05_Statistics_And_Models", "Statistical inference, uncertainty, clustering and models", [
    md("""
## G · Statistical inference and uncertainty

**Research question.** Which relationships are in the data, how large are they, and how much could be chance?

**Method.** Rank-based statistics by default (the metrics are skewed), effect sizes and bootstrap intervals
next to every p-value, Benjamini–Hochberg control across a family of tests, and resampling at the level of the
independent unit — matches for team questions, players for player questions. Events are never treated as
independent observations.
"""),
    code('''
from src.analytics import statistical_tests as stt
corr = ws.correlations()
display(corr.round(3))
show("J-202", ws)
show("J-213", ws)
top = corr.iloc[0]; poss = corr.set_index("variable").loc["possession_proxy_pct"]
n_sig = int((corr.spearman_q_BH < 0.05).sum())
interpret(f"Of {len(corr)} match variables, {n_sig} remain associated with goal difference after false-discovery control "
          f"(n = {int(top.n)} matches). The strongest is {top.variable} (ρ = {top.spearman_rho:.2f}, 95% CI {top.rho_ci_low:.2f} to "
          f"{top.rho_ci_high:.2f}, q = {top.spearman_q_BH:.3f}); possession proxy shows ρ = {poss.spearman_rho:.2f} (q = {poss.spearman_q_BH:.3f}).")
'''),
    code('''
show("J-214", ws)
show("L-276", ws)
mdr = float(stt.min_detectable_correlation(len(tm)))
interpret(f"With n = {len(tm)} a two-sided test at α = 0.05 has 80% power only for |r| ≥ {mdr:.2f}. Weaker real "
          f"associations will usually be missed, so a non-significant result here is not evidence of no relationship. "
          f"H1 (chance quality matters more than possession) is supported in direction and "
          + ("in significance." if n_sig else "undecided in significance at this sample size."))
limitation("One team-season: opponents and venues are not randomised, and nothing here is a causal estimate.")
'''),
    code('''
tests = ws.group_tests()
display(pd.DataFrame(tests)[["comparison", "n_a", "n_b", "mean_a", "mean_b", "mean_diff", "diff_ci_low", "diff_ci_high",
                             "p_value", "effect_size", "magnitude"]].round(3))
show("J-211", ws)
show("J-209", ws, team_metric="xg_diff")
v = tests[0]
interpret(f"Home minus away xG difference is {v['mean_diff']:+.2f} (95% CI {v['diff_ci_low']:+.2f} to {v['diff_ci_high']:+.2f}), "
          f"Cliff's δ = {v['effect_size']:.2f} ({v['magnitude']}), p = {v['p_value']:.3f} — "
          + ("statistically significant." if v['p_value'] < 0.05 else "suggestive but not established; the interval includes zero."))
implication("Not strong enough to justify a different game model by venue on this evidence.")
'''),
    code('''
show("J-212", ws, metric="progressive_passes_p90", group="role_family")
show("J-207", ws, team_metric="xg_diff")
show("J-219", ws, team_metric="xg_diff")
show("J-215", ws, metric="xg_p90", metric_y="key_passes_p90")
show("J-216", ws)
show("J-217", ws, team_metric="xg_diff")
''', core=False, advanced=True),
    md("""
## H · Unsupervised structure: PCA and clustering

**Question.** Do player profiles form distinct types, or a continuum?

**Method.** Fourteen per-90 metrics, standardised, for outfield players above the minutes threshold. Four
algorithms (K-Means, Ward, Gaussian mixture, DBSCAN) and four selection criteria, plus a bootstrap stability
check — so the conclusion does not rest on one method.
"""),
    code('''
pca = ws.pca(); cl = ws.clusters()
show("K-237", ws)
show("K-240", ws)
show("L-277", ws)
show("K-242", ws)
stab = ws.cluster_stability()
interpret(f"PC1 and PC2 explain {pca['explained'][0]:.0%} and {pca['explained'][1]:.0%} of the variance across {pca['n_players']} "
          f"players; {pca['components_for_80pct']} components are needed for 80%. Silhouette is best at k = {cl['k_best']} "
          f"({cl['silhouette_best']:.2f}) while the mixture-model BIC prefers k = {cl['k_bic']}; DBSCAN finds "
          f"{cl['dbscan_clusters']} dense group(s) and {cl['dbscan_noise']} outlying players. Bootstrap stability of the "
          f"K-Means partition: mean ARI {stab.ari.mean():.2f}.")
implication("Use role-specific metric profiles for squad planning; cluster labels are a vocabulary, not fixed "
            "player types.")
limitation("Opponent players are observed only in their two matches against the focus team.")
'''),
    code('''
show("K-238", ws)
show("K-239", ws)
show("K-241", ws)
show("L-278", ws)
show("K-243", ws)
''', core=False, advanced=True),
    md("""
## Supervised modelling — only where the data support it

**Question.** Can the starting decision be predicted from information available before kick-off, and does a
model beat a simple rule?

**Target.** One row per match-day squad member of the focus team; y = 1 if he started. **Baseline:** he started
the previous match. **Split:** by match in date order (expanding-window cross-validation and a final
chronological hold-out) so no future information reaches a prediction.

**Not modelled:** match results (34 matches, no losses), goals, injuries, fitness, market value — the data do
not support them.
"""),
    code('''
from src.analytics import models
with timed("model comparison"):
    res = ws.models()
display(pd.DataFrame([res["gate"]]))
display(pd.DataFrame(models.UNSUPPORTED_TARGETS, columns=["target not modelled", "why"]))
if res["fitted"]:
    display(res["leakage_audit"])
    cs = res["cv_summary"]; display(cs.round(3))
    show("K-221", ws); show("K-236", ws)
    f1 = cs[("f1", "mean")]; auc = cs[("roc_auc", "mean")].dropna()
    interpret(f"Time-ordered cross-validation on {res['gate']['rows']} rows from {res['gate']['matches']} matches: F1 "
              + ", ".join(f"{m} {v:.3f}" for m, v in f1.items())
              + f". ROC-AUC ranges from {auc.min():.3f} to {auc.max():.3f}. The best model improves on the baseline rule by "
              f"{f1.drop(models.BASELINE_NAME).max() - f1[models.BASELINE_NAME]:.3f} F1.")
else:
    interpret(f"No model is fitted: {res['reason']}")
'''),
    code('''
if res["fitted"]:
    s = res["split"]; hold = res["holdout"].set_index("model")
    print(f"Hold-out: train {s['train_matches']} matches to {s['train_until']:%d %b %Y}, test {s['test_matches']} matches from {s['test_from']:%d %b %Y}")
    display(res["holdout"].round(3))
    show("K-223", ws); show("K-225", ws); show("K-228", ws)
    perm = ws.permutation()
    interpret(f"On the chronological hold-out {res['best']} ranks starters best (ROC-AUC {hold.loc[res['best'], 'roc_auc']:.3f}, "
              f"Brier {hold.loc[res['best'], 'brier']:.3f}). Shuffling {perm.feature.iloc[-1]} costs {perm.importance_mean.iloc[-1]:.3f} AUC "
              f"and {perm.feature.iloc[-2]} {perm.importance_mean.iloc[-2]:.3f}: selection follows past selection.")
    implication("A rule plus season minutes share explains most selections. Analytics adds value in the rotation "
                "margin — where the missing availability data matter most.")
    limitation("Describes this team-season only; importance is conditional on correlated features and is not a "
               "causal lever.")
'''),
    code('''
if res["fitted"]:
    for cid in ("K-224", "K-222", "K-226", "K-227", "K-232", "K-233", "K-234", "K-231", "K-229", "K-235"):
        show(cid, ws)
''', core=False, advanced=True),
])

# =====================================================================================================
CH6 = ("06_Managerial_Insights_And_Report", "Managerial patterns, evidence cards and conclusions", [
    md("""
## I · Managerial patterns

**Research question.** What do the recorded decisions show about selection, formation and substitution habits,
and how much of it is certain?

**Scope note.** This describes **observable decisions**. It does not measure a manager's ability or intentions
and cannot separate the manager from the squad he has. Every other manager in the data has two matches,
all against the focus team.
"""),
    code('''
prof = ws.manager_profiles()
mgr = ws.focus_manager()
print("Manager identity source:", B.manager_source)
display(prof[prof.manager == mgr].T)
show("I-186", ws)
show("I-187", ws)
r = prof[prof.manager == mgr].iloc[0]
interpret(f"{mgr} ({int(r.matches)} matches): {int(r.formations_used)} starting formations, {r.most_used_formation} in "
          f"{r.most_used_share_pct:.0f}% of matches; {r.mean_lineup_changes:.2f} changes to the XI between consecutive "
          f"analysed matches; {r.subs_per_match:.2f} substitutions per match with the first at a median of minute "
          f"{r.median_first_sub_minute:.0f}.")
limitation("Rotation is measured between league matches only; cup and European fixtures in between are missing.")
'''),
    code('''
show("I-192", ws)
show("I-193", ws)
show("I-195", ws)
small = prof[prof.matches < B.config.min_manager_matches]
interpret(f"{len(small)} of {len(prof)} managers have fewer than {B.config.min_manager_matches} matches. Their Wilson intervals "
          f"span most of the scale and shrinkage pulls them to the pooled value — they cannot be ranked or compared "
          f"with {mgr} as peers.")
'''),
    code('''
mid = ws.default_match()
show("I-198", ws, match_id=mid)
show("I-190", ws)
show("I-197", ws)
show("G-163", ws)
''', core=False, advanced=True),
    md("""
## Evidence cards

Each card states the finding, the metric and value behind it, the scope, the supporting chart, why it may
matter and what the evidence cannot tell us. The text is assembled from computed values.
"""),
    code('''
from src.reporting import insight_cards
cards = insight_cards.build_cards(ws)
display(Markdown(insight_cards.cards_markdown(cards)))
'''),
    md("## J · Answers to the research questions and hypotheses"),
    code('''
from src.analytics import descriptive as desc
from src.reporting.report_builder import results_snapshot
snap = results_snapshot(ws)
corr = ws.correlations().set_index("variable")
xg_side = corr.loc[["xg", "xg_against"], "spearman_rho"].abs().max()
answers = pd.DataFrame([
    ("H1 chance quality vs possession", f"|ρ| up to {xg_side:.2f} for xG for/against vs {abs(corr.loc['possession_proxy_pct', 'spearman_rho']):.2f} for possession proxy; "
     f"{snap['corr_significant_after_fdr']} of {len(corr)} variables significant after FDR", "direction supported; significance undecided at n = 34"),
    ("H2 results vs expectation", f"{snap['points']:.0f} points vs {snap['xpts']} expected points", "supported (model-based reference)"),
    ("H3 concentration of chance creation", f"top three = {snap['top3_chance_share']:.0%} of xG + xA", "supported"),
    ("H4 hub players", f"highest PageRank: {snap['hub_pagerank']}; highest betweenness: {snap['hub_betweenness']}", "supported (descriptive)"),
    ("H5 selection follows past selection", f"CV F1 {snap['cv_f1'][snap['best_model']]:.3f} vs {snap['cv_f1']['Baseline: started previous match']:.3f} baseline"
     if snap.get("model_fitted") else "model gate not met", "supported: small gain over the rule" if snap.get("model_fitted") else "not testable"),
    ("H6 substitution timing by score state", f"shortlist top-3 contains the actual substitute in {snap['sub_top3_share']:.0%} of cases", "descriptive only; confounded by team strength"),
], columns=["hypothesis", "evidence from this run", "verdict"])
display(answers)
'''),
    md("""
## Conclusions, limitations and next steps

**What the evidence supports.** The focus team's results rest on a large and consistent advantage in chance
volume; the points total ran ahead of shot-based expectation; chance creation and build-up are concentrated in
a few players; selection is dominated by a stable core; substitutions are late and mostly made from in front.

**What it does not support.** Any causal claim; any statement about the league or other teams' seasons; any
ranking of managers; any conclusion about fitness, injuries or fatigue.

**Limitations.** One team-season of league matches; opponents seen twice; no injury, fitness, tracking,
age or market data; xG, expected points and Expected Threat are model outputs; heuristic scores are valid only
under their stated weights.

**Next steps.** (1) Add several complete league seasons for benchmarks independent of one club. (2) Add the
other competitions the team played to measure real rotation. (3) Obtain availability data from an authorised
source before modelling rotation. (4) Use tracking or 360 data for off-ball questions. (5) Re-test the venue and
correlation findings with more matches.
"""),
    code('''
# Machine-readable results of this run (the same numbers the reports are built from)
import json
print(json.dumps({k: v for k, v in snap.items() if k != "chart_status"}, indent=1, default=str, ensure_ascii=False))
display(timings().sort_values("seconds", ascending=False).head(10))
'''),
])

CHAPTERS = [CH0, CH1, CH2, CH3, CH4, CH5, CH6]
COMPLETE_NAME = "Football_Managerial_Analytics_Complete.ipynb"

ATLAS_MD = """---
# Part 07 · Full chart atlas (optional)

Every chart of the catalogue that the loaded data support, grouped by family, each with its ID, question,
method note and caveat. Charts that cannot be drawn are listed with the reason instead.

This renders roughly 270 figures, so it is **off by default**: set `RUN_FULL_ATLAS = True` below to run it
(several minutes; the notebook grows by tens of megabytes). To look at single charts instead, use
`show("<chart_id>", ws)` or the chart explorer in Part 00, or the Streamlit dashboard."""

ATLAS_CODE = '''RUN_FULL_ATLAS = False   # set to True to render every available chart

from src.visualization import registry

table = catalogue(ws)
display(table.groupby(["category", "status"]).size().unstack(fill_value=0))
if RUN_FULL_ATLAS:
    with timed("full chart atlas"):
        for family, group in table.groupby("category", sort=False):
            display(Markdown(f"## {family}"))
            for row in group.itertuples():
                if row.status == "implemented_and_available":
                    display(Markdown(f"### {row.chart_id} · {row.name}"))
                    display(Markdown(row.research_question))
                    show(row.chart_id, ws)
                else:
                    display(Markdown(f"> **{row.chart_id} · {row.name}** — {row.status.replace('_', ' ')}: {row.reason}"))
else:
    print("Atlas skipped. Set RUN_FULL_ATLAS = True to render every available chart.")
display(timings().sort_values("seconds", ascending=False).head(15))'''


def _cells(items, setup_advanced: bool, core_only: bool, with_setup: bool = True):
    cells = []
    if with_setup:
        cells.append(nbf.v4.new_code_cell(SETUP.replace("__ADVANCED__", str(setup_advanced))))
    for kind, text, core, advanced in items:
        if core_only and not core:
            continue
        if kind == "md":
            cells.append(nbf.v4.new_markdown_cell(text))
        elif advanced:
            body = "\n".join("    " + line if line else line for line in text.split("\n"))
            cells.append(nbf.v4.new_code_cell("# Optional, heavier section — set RUN_ADVANCED_GALLERY = True in the setup "
                                              "cell to run it\nif RUN_ADVANCED_GALLERY:\n" + body))
        else:
            cells.append(nbf.v4.new_code_cell(text))
    return cells


def _notebook(cells):
    nb = nbf.v4.new_notebook()
    nb.cells = cells
    nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                   "language_info": {"name": "python"}}
    return nb


def build() -> list[Path]:
    OUT.mkdir(exist_ok=True)
    written = []
    for i, (name, title, items) in enumerate(CHAPTERS):
        head = nbf.v4.new_markdown_cell(
            f"# Football Managerial Decision Analytics — Chapter {i:02d}\n## {title}\n\n{ATTRIBUTION}\n\n"
            f"This notebook is one chapter of the research record. All logic lives in the shared `src/` package; "
            f"the cells call it. The same charts are available interactively in the Streamlit dashboard "
            f"(`streamlit run app.py`).")
        nb = _notebook([head] + _cells(items, setup_advanced=True, core_only=False))
        path = OUT / f"{name}.ipynb"
        nbf.write(nb, path)
        written.append(path)
    head = nbf.v4.new_markdown_cell(
        "# Football Managerial Decision Analytics — Complete notebook\n"
        "## From event data to evidence for managerial decisions\n\n" + ATTRIBUTION + "\n\n"
        "**Everything in one notebook:** all seven chapters in order, including the advanced sections, and an "
        "optional full chart atlas at the end. Run it top to bottom (*Run All*).\n\n"
        "- **Inside the repository** it uses the local `src/` package directly.\n"
        "- **Opened on its own (e.g. Google Colab)** the first cell downloads the project code from GitHub and "
        "installs the requirements; the StatsBomb data (about 120 MB) is then downloaded on first use.\n"
        "- Expect about 8–10 minutes for a first run (download and parsing included) and less afterwards.\n"
        "- The chapter notebooks `00`–`06` in `notebooks/` contain the same cells, one chapter each.\n\n"
        "| Part | Content |\n|---|---|\n"
        + "\n".join(f"| {i:02d} | {t} |" for i, (_, t, _) in enumerate(CHAPTERS))
        + "\n| 07 | Full chart atlas (optional — every available chart of the catalogue) |")
    cells = [head]
    for i, (name, title, items) in enumerate(CHAPTERS):
        cells.append(nbf.v4.new_markdown_cell(f"---\n# Part {i:02d} · {title}"))
        cells += _cells(items, setup_advanced=True, core_only=False, with_setup=(i == 0))
    cells += [nbf.v4.new_markdown_cell(ATLAS_MD), nbf.v4.new_code_cell(ATLAS_CODE)]
    path = OUT / COMPLETE_NAME
    nbf.write(_notebook(cells), path)
    written.append(path)
    old = OUT / "Football_Managerial_Research_Main.ipynb"
    if old.exists():
        old.unlink()  # superseded by the complete notebook
    return written


if __name__ == "__main__":
    for p in build():
        nb = nbf.read(p, as_version=4)
        n_code = sum(c.cell_type == "code" for c in nb.cells)
        print(f"{p.relative_to(ROOT)}: {len(nb.cells)} cells ({n_code} code)")
    sys.exit(0)
