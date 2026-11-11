# Visualization Catalogue

> Generated 2026-11-11 11:30 UTC by `scripts/build_reports.py` from `src/visualization/catalogue.py` (registry schema 1.0.0). Status is evaluated against the data loaded for this run: **1. Bundesliga 2023/2024, 34 matches, focus team Bayer Leverkusen**.

Every implemented renderer was executed once with default selections while this file was built; a renderer that raised would be listed as `failed_validation`.

## Status summary

| status | charts | meaning |
| --- | --- | --- |
| `implemented_and_available` | 273 | renderer exists, prerequisites met, rendered without error |
| `implemented_but_unavailable` | 0 | renderer exists but the loaded data or an optional package does not support it |
| `not_implemented` | 5 | catalogue concept with no renderer; reason stated |
| `failed_validation` | 0 | renderer raised during validation |
| **total** | **278** | |

The catalogue is open-ended: these counts describe what exists and rendered in this run, not every possible football chart.

## By family

| category | implemented_and_available | not_implemented |
| --- | --- | --- |
| Additional project charts and composite dashboards | 34 | 0 |
| Data audit and coverage | 16 | 0 |
| Descriptive and distribution analytics | 22 | 1 |
| Machine learning and diagnostic plots | 23 | 1 |
| Managerial intelligence | 13 | 0 |
| Match and team analysis | 27 | 0 |
| Passing networks and team structure | 12 | 0 |
| Pitch, spatial and event analytics | 25 | 3 |
| Player performance and scouting | 42 | 0 |
| Statistics, inference and uncertainty | 22 | 0 |
| Substitution and match-state analytics | 16 | 0 |
| Tactical, lineup and formation analytics | 21 | 0 |


## Entries that are not available

| chart_id | name | status | reason |
| --- | --- | --- | --- |
| B-038 | Bullet chart: target versus actual | not_implemented | No legitimate external target exists in the data. Expected points are shown as a model reference in chart L-262 instead of being presented as a target. |
| E-126 | Voronoi diagram | not_implemented | Needs every player's position at the same instant. Event data give one actor per event, and 360 freeze frames show only players inside the camera view, so a Voronoi partition would be invented space. |
| E-127 | Delaunay triangulation | not_implemented | Needs simultaneous positions of all team-mates (tracking data); not derivable from event locations. |
| E-128 | Pitch-control / space-control map | not_implemented | Needs positions and velocities of all 22 players (tracking). Never approximated from event x/y. |
| K-244 | Forecast residuals | not_implemented | Forecasting is not justified: 34 matches of one team give no temporal depth for a held-out forecast horizon, and no out-of-sample season exists in the data. |


## Existing gallery artefacts mapped to registry IDs

The 27 static figures and 6 HTML dashboards produced by the preserved enhanced notebook (`visualization_gallery/`) correspond to these registry entries (closest equivalent renderer):

| legacy_artifact | chart_id | name |
| --- | --- | --- |
| gallery/01_dataset_composition.png | A-001 | Dataset composition by table |
| gallery/02_missing_by_feature.png | A-003 | Missingness by field |
| gallery/03_missingness_matrix.png | A-004 | Missingness matrix |
| gallery/04_duplicates.png | A-006 | Duplicate full-row and primary-key counts |
| gallery/05_numeric_distributions.png | A-008 | Numeric field distributions |
| gallery/06_categorical_distributions.png | A-009 | Categorical frequency and rare categories |
| gallery/07_outliers.png | A-010 | Outlier distributions |
| gallery/08_before_after_cleaning.png | A-011 | Before / after refinement funnel |
| gallery/09_feature_availability.png | A-012 | Feature availability |
| gallery/10_kde_by_role.png | B-018 | KDE by role family |
| gallery/11_pair_plot.png | D-074 | Player pair plot |
| gallery/12_pass_origin_hexbin.png | E-113 | Pass-origin hexbin |
| gallery/13_match_level_views.png | C-056 | Match-by-match heatmap |
| gallery/14_network_centrality.png | F-139 | Network node centrality |
| gallery/15_player_consistency.png | D-102 | Consistency versus output quadrant |
| gallery/16_team_consistency_heatmap.png | C-064 | Team consistency heatmap |
| gallery/17_scoring_and_goalkeeping.png | L-253 | Shot-quality distribution for and against |
| gallery/18_correlation_forest.png | J-202 | Correlation forest plot with confidence intervals |
| gallery/19_group_comparisons.png | J-210 | Group comparison box / violin plots |
| gallery/20_bootstrap_player_intervals.png | D-079 | Bootstrap confidence intervals per player |
| gallery/21_pca_scree_loadings.png | K-237 | PCA scree plot |
| gallery/22_clustering_model_selection.png | K-240 | Cluster model selection |
| gallery/23_clustering_comparison.png | K-242 | Cluster stability / ARI comparison |
| gallery/24_cluster_profiles.png | K-241 | Cluster projection and profile |
| gallery/25_model_comparison.png | K-221 | Baseline model comparison |
| gallery/26_model_explainability.png | K-228 | Permutation feature importance |
| gallery/27_shap_summary.png | K-229 | SHAP summary |
| gallery/interactive/match_dashboard.html | L-272 | Match dashboard |
| gallery/interactive/player_dashboard.html | L-271 | Player dashboard |
| gallery/interactive/rotation_matrix.html | D-106 | Rotation / appearance calendar |
| gallery/interactive/season_dashboard.html | C-066 | Team season dashboard |
| gallery/interactive/starting_xi.html | G-149 | Starting XI pitch diagram |
| gallery/interactive/substitution_dashboard.html | L-273 | Substitution dashboard |


## Data audit and coverage

### A-001 · Dataset composition by table

- **Question.** How large is each table and which ones come straight from the source?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id
- **Method.** Row and column counts of every canonical and derived table; log scale.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[A-001]`

### A-002 · Row counts by match, team and player

- **Question.** Is the event volume balanced across matches?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: match_id; matches: match_id
- **Method.** Event rows per match in date order.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[A-002]`

### A-003 · Missingness by field

- **Question.** Which fields have gaps and how large are they?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id
- **Method.** Share of missing values per event field.
- **Caveat.** Most gaps are structural: a qualifier exists only for its event type.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[A-003]`

### A-004 · Missingness matrix

- **Question.** Do gaps cluster in particular rows or fields?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id
- **Method.** Nullity of a seeded random sample of 400 event rows.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[A-004]`

### A-005 · Missingness by event type

- **Question.** Is a missing value expected for that kind of event?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: type
- **Method.** Completeness of each field within each event type.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[A-005]`

### A-006 · Duplicate full-row and primary-key counts

- **Question.** Are there duplicated records or keys?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** events: event_id
- **Method.** Counts of duplicated full rows and duplicated primary keys per table.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[A-006]`

### A-007 · Duplicate-ID investigation table

- **Question.** Which key defines uniqueness in each table?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** events: event_id
- **Method.** Table of keys and duplicate counts.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[A-007]`

### A-008 · Numeric field distributions

- **Question.** What shape do the numeric event fields have?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: duration
- **Method.** Histograms with skewness; display clipped at the 99.5th percentile.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[A-008]`

### A-009 · Categorical frequency and rare categories

- **Question.** Which categories dominate and which are rare?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: play_pattern
- **Method.** Level frequencies on a log axis; levels under 0.5% flagged.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[A-009]`

### A-010 · Outlier distributions

- **Question.** Are extreme values errors or real events?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: duration, pass_length, shot_xg
- **Method.** Box plots with the count beyond 1.5 × IQR.
- **Caveat.** Flagged values are genuine events and are kept.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[A-010]`

### A-011 · Before / after refinement funnel

- **Question.** How many rows survive each processing step?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x; season: eligible
- **Method.** Row counts from raw events to eligible player-seasons.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[A-011]`

### A-012 · Feature availability

- **Question.** Which analytical inputs exist in the data and which do not?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x; squads: player_id
- **Method.** Verified from the loaded tables; absent modalities are listed, never imputed.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[A-012]`

### A-013 · Schema and field-type overview

- **Question.** What kinds of fields does each table hold?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id
- **Method.** Fields per table by data type.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[A-013]`

### A-014 · Time coverage and event-timeline gaps

- **Question.** Which dates are covered and are event timelines continuous?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: elapsed_min; matches: match_date
- **Method.** Events per match over the calendar and the longest within-period gap.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[A-014]`

### A-015 · Data provenance graph

- **Question.** How do source files become tables and outputs?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id
- **Method.** Lineage Sankey; link widths carry no meaning.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[A-015]`

### A-016 · Validation rule pass / fail panel

- **Question.** Which domain rules and table contracts hold?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** quality: check, status
- **Method.** Sixteen domain rules plus fourteen table contracts.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[A-016]`

## Descriptive and distribution analytics

### B-017 · Histogram with controlled bins

- **Question.** How is a per-90 metric distributed across players?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** metric, group, min_minutes
- **Method.** 30 equal-width bins shared by groups.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-017]`

### B-018 · KDE by role family

- **Question.** Do role families have differently shaped distributions?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** metric, group, min_minutes
- **Method.** Gaussian KDE, Scott bandwidth; rug of points.
- **Caveat.** Groups under 5 values are not drawn.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-018]`

### B-019 · ECDF comparison

- **Question.** What share of players sits below a given value?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** metric, group, min_minutes
- **Method.** No binning or smoothing.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-019]`

### B-020 · Box plot with individual points

- **Question.** Where are the quartiles and who are the outliers?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** metric, group, min_minutes
- **Method.** Quartile box with every player drawn.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-020]`

### B-021 · Violin plot

- **Question.** How does the density compare between groups?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** metric, group, min_minutes
- **Method.** Density clipped to the observed range.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-021]`

### B-022 · Raincloud plot

- **Question.** Shape, quartiles and raw values in one view?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** metric, group, min_minutes
- **Method.** Half-violin, box and points.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-022]`

### B-023 · Strip plot with overplot handling

- **Question.** Where does each individual player sit?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** metric, group, min_minutes
- **Method.** Deterministic jitter and transparency; medians marked.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-023]`

### B-024 · Ridgeline density plot

- **Question.** How do distributions shift across detailed roles?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** metric, min_minutes
- **Method.** One scaled KDE per primary role.
- **Caveat.** Ridges are scaled to equal height: compare shape, not area.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-024]`

### B-025 · Beeswarm chart

- **Question.** Density and individual values without overlap?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** metric, group, min_minutes
- **Method.** Greedy non-overlapping placement.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-025]`

### B-026 · Quantile plot

- **Question.** How do groups differ at each percentile?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** metric, group, min_minutes
- **Method.** 2nd to 98th percentile.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-026]`

### B-027 · Q-Q plot

- **Question.** Is a metric close enough to normal for parametric methods?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** metric, min_minutes
- **Method.** Normal Q-Q with Shapiro–Wilk.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-027]`

### B-028 · Rank / lollipop chart

- **Question.** Who leads a metric among eligible players?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** metric, min_minutes
- **Method.** Top 15 with the minutes threshold in the title.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-028]`

### B-029 · Pareto / concentration chart

- **Question.** How concentrated is chance creation in a few players?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: xg, xa, team_name
- **Selectors.** team
- **Method.** Sorted xG + xA with cumulative share.
- **Caveat.** xA is credited to the passer of a shot assist.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-029]`

### B-030 · Contribution treemap

- **Question.** Which role families and players create the chances?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: xg, xa
- **Selectors.** team
- **Method.** Area = xG + xA by role family and player.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-030]`

### B-031 · Sunburst of the shot taxonomy

- **Question.** How do shots break down by pattern, body part and outcome?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, shot_xg, outcome
- **Selectors.** team
- **Method.** Play pattern → body part → outcome.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-031]`

### B-032 · Waterfall of goal difference by month

- **Question.** How was the season's goal difference built up?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 4 matches
- **Selectors.** team
- **Method.** Monthly goal difference; the components add up exactly.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-032]`

### B-033 · Attacking funnel

- **Question.** How much possession turns into shots and goals?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team
- **Method.** Completed passes → final-third entries → box touches → shots → goals.
- **Caveat.** Stages are overlapping event counts, not a strict conversion sequence.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-033]`

### B-034 · Calendar heatmap

- **Question.** How did performance vary across the fixture calendar?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 4 matches
- **Selectors.** team
- **Method.** Week × weekday, coloured by xG difference.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-034]`

### B-035 · Bump chart of rank changes

- **Question.** How did the scoring-chance ranking inside the squad evolve?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** pms: xg, match_date · at least 5 matches
- **Selectors.** team
- **Method.** Rank by cumulative xG after each match.
- **Caveat.** Ranks hide the size of the gaps.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-035]`

### B-036 · Slope chart for two periods

- **Question.** Who changed between the first and second half of the season?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** pms: match_id, player_id, minutes_played · at least 8 matches
- **Selectors.** team
- **Method.** Per-90 value in each half of the season for regular players.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-036]`

### B-037 · Small-multiple plots

- **Question.** How do several metrics differ by role family at once?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** min_minutes
- **Method.** One box-plot panel per metric.
- **Caveat.** Each panel has its own scale.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-037]`

### B-038 · Bullet chart: target versus actual

- **Question.** Did the team meet a defined target?
- **Status.** `not_implemented` — No legitimate external target exists in the data. Expected points are shown as a model reference in chart L-262 instead of being presented as a target.
- **Library / modality / cost.** plotly · event · low

### B-039 · KPI gauges for bounded measures

- **Question.** Where do the season's bounded indicators stand?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** Win rate, points per match, xG share, possession proxy, field tilt.
- **Caveat.** Gauges are used only for measures with natural bounds; the tick marks the neutral value.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[B-039]`

## Match and team analysis

### C-040 · Results timeline

- **Question.** What was the sequence of results?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** Goal difference by match.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-040]`

### C-041 · Goals for and against over the season

- **Question.** How did goals and xG accumulate?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 3 matches
- **Selectors.** team
- **Method.** Cumulative goals and xG for / against.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-041]`

### C-042 · Rolling performance form

- **Question.** Is the underlying performance trending?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 6 matches
- **Selectors.** team
- **Method.** 5-match rolling xG difference with a ±1 SD band.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-042]`

### C-043 · Match-level xG for and against

- **Question.** How large was the chance-quality gap in each match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** Dumbbell per match.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-043]`

### C-044 · Goals versus xG

- **Question.** Which matches and which players ran ahead of chance quality?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: goals, xg
- **Selectors.** team, min_minutes
- **Method.** Goals against xG per player.
- **Caveat.** Finishing over- or under-performance regresses strongly.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-044]`

### C-045 · xG difference distribution

- **Question.** How often and by how much did the team out-create opponents?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** Histogram by result.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-045]`

### C-046 · Shot volume versus shot quality

- **Question.** Does dominance come from more shots or better shots?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** Shots vs mean xG per shot, team and opponents.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-046]`

### C-047 · Shot count and conversion by match

- **Question.** How many shots, on-target shots and goals per match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** Nested bars.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-047]`

### C-048 · Goal timing clock

- **Question.** When in a match are goals scored and conceded?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result; goals: match_id, scoring_team_id, elapsed_min
- **Selectors.** team
- **Method.** Polar histogram in 5-minute bins.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-048]`

### C-049 · Goal and event timeline of a match

- **Question.** What happened and when in the selected match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: type, elapsed_min; goals: match_id, scoring_team_id, elapsed_min
- **Selectors.** team, match
- **Method.** Goals, cards and substitutions on the elapsed clock.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-049]`

### C-050 · Score-state time share

- **Question.** How much of the time was spent leading, level or behind?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result; goals: match_id, scoring_team_id, elapsed_min
- **Selectors.** team
- **Method.** Minutes per state from the reconstructed goal timeline.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-050]`

### C-051 · Match-state timeline

- **Question.** How did the score state evolve within one match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result; goals: match_id, scoring_team_id, elapsed_min
- **Selectors.** team, match
- **Method.** State bands with goals marked.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-051]`

### C-052 · Team comparison radar

- **Question.** What is the team's style fingerprint?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** Percentile of team averages among the teams in the dataset.
- **Caveat.** Opponents appear twice (home and away), always against the focus team.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-052]`

### C-053 · Team metric percentile profile

- **Question.** Where does the team's typical match rank among all team-matches?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** Percentile of the median match within all team-match rows.
- **Caveat.** Reference set is the team and its opponents on the day — not a league benchmark.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-053]`

### C-054 · Home / away comparison

- **Question.** Does venue relate to chance creation?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 6 matches
- **Selectors.** team
- **Method.** Box plots by venue.
- **Caveat.** 17 matches per venue: low power.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-054]`

### C-055 · Opponent matrix

- **Question.** How did the team fare against each opponent?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 4 matches
- **Selectors.** team
- **Method.** Opponent × metric, average over meetings.
- **Caveat.** Two meetings per opponent.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-055]`

### C-056 · Match-by-match heatmap

- **Question.** What did every match look like across the key metrics?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** Raw values coloured within each column's range.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-056]`

### C-057 · Formation usage timeline

- **Question.** Which starting formation was used when?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: starting_formation, match_date
- **Selectors.** team
- **Method.** Recorded Starting XI formation by date.
- **Caveat.** A nominal label, not the shape in every phase.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-057]`

### C-058 · Formation outcome distribution

- **Question.** How did results differ by starting formation?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: starting_formation · at least 4 matches
- **Selectors.** team
- **Method.** Event metrics by starting formation.
- **Caveat.** Formation choice depends on opponent and availability.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-058]`

### C-059 · Set-piece versus open-play contribution

- **Question.** How do shots and goals originate?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: play_pattern, shot_xg
- **Selectors.** team
- **Method.** Shots, xG and goals by how the possession started.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-059]`

### C-060 · Possession and territory proxies

- **Question.** How much of the ball and of the final third did the team have?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: possession_proxy_pct, field_tilt_pct
- **Selectors.** team
- **Method.** Pass-share possession proxy and final-third touch share.
- **Caveat.** Not timed possession.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-060]`

### C-061 · Pass completion and progression profile

- **Question.** Is safe passing traded against progression?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: pass_completion_pct, progressive_passes
- **Selectors.** team
- **Method.** Completion % vs progressive passes per match.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-061]`

### C-062 · Defensive actions by match

- **Question.** How much defending was done in each match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** Tackles, interceptions, blocks, clearances, recoveries.
- **Caveat.** Not adjusted for opponent possession.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-062]`

### C-063 · Pressing proxy (PPDA) distribution

- **Question.** How intense was the pressing proxy?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: ppda
- **Selectors.** team
- **Method.** Opponent passes in their own 60% / the team's defensive actions there.
- **Caveat.** An event-based proxy; formula validated against event coverage.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-063]`

### C-064 · Team consistency heatmap

- **Question.** Which aspects of performance are stable from match to match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 6 matches
- **Selectors.** team
- **Method.** Within-season z-scores and coefficient of variation.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-064]`

### C-065 · Team style quadrant

- **Question.** Where do teams sit on possession and chance balance?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** Mean possession proxy vs mean xG difference per team.
- **Caveat.** Most teams have two matches here.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-065]`

### C-066 · Team season dashboard

- **Question.** What is the season at a glance?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** KPI tiles, form, xG trend and results.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[C-066]`

## Player performance and scouting

### D-067 · Player ranking bars

- **Question.** Who ranks highest on the selected metrics?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** metric, metric_y, min_minutes
- **Method.** Top 15 with the minutes threshold stated.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-067]`

### D-068 · Per-90 rankings

- **Question.** Who leads per 90 minutes among eligible players?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** metric, min_minutes
- **Method.** Per-90 = count / minutes × 90; null below the threshold.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-068]`

### D-069 · Percentile chart by role group

- **Question.** How does a player rank within his role group?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** team, player
- **Method.** Percentile within the benchmark group, with group size.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-069]`

### D-070 · Player radar

- **Question.** What is a player's role-specific percentile profile?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** team, player
- **Method.** Role metrics as percentiles; all axes higher = higher percentile.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-070]`

### D-071 · Multi-player radar comparison

- **Question.** How do two players of the same role compare?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** team, player, compare
- **Method.** Two percentile profiles on the same axes.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-071]`

### D-072 · Parallel coordinates

- **Question.** How do percentile profiles run across metrics within a role family?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** team, min_minutes
- **Method.** Percentile lines for midfielders.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-072]`

### D-073 · Player metric scatter

- **Question.** How do two metrics relate across players?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** team, metric, metric_y, min_minutes
- **Method.** Size = minutes; medians dotted.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-073]`

### D-074 · Player pair plot

- **Question.** How do several per-90 metrics relate pairwise?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** min_minutes
- **Method.** Scatter-plot matrix by role family.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-074]`

### D-075 · Player correlation matrix

- **Question.** Which player metrics move together?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** min_minutes
- **Method.** Spearman correlations among eligible players.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-075]`

### D-076 · Player-by-metric heatmap

- **Question.** Where is the squad strong and weak, player by player?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** team, min_minutes
- **Method.** Squad × metric percentile matrix.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-076]`

### D-077 · Role distribution violins

- **Question.** How do metrics distribute by role?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** metric, min_minutes
- **Method.** Violin per role with n per role.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-077]`

### D-078 · Match consistency plot

- **Question.** How variable is a player's output from match to match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** pms: xg, xa, minutes_played
- **Selectors.** team
- **Method.** Matches of at least 45 minutes.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-078]`

### D-079 · Bootstrap confidence intervals per player

- **Question.** How certain are per-90 rates?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** pms: match_id, player_id, minutes_played · at least 6 matches
- **Selectors.** team, metric
- **Method.** 2,000 bootstrap resamples of each player's matches.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-079]`

### D-080 · Player match-by-match trend

- **Question.** Is a player's form rising or falling?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** pms: match_id, player_id, minutes_played
- **Selectors.** team, player
- **Method.** Rolling per-90 over recent appearances.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-080]`

### D-081 · Player contribution decomposition

- **Question.** How do goals and assists compare with expected involvement?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: goals, assists, xg, xa
- **Selectors.** team
- **Method.** Goals + assists with xG + xA.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-081]`

### D-082 · Goal contribution timeline

- **Question.** How did goal involvement accumulate over the season?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** pms: goals, assists
- **Selectors.** team
- **Method.** Animated cumulative goals + assists.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-082]`

### D-083 · xG / xA contribution scatter

- **Question.** Who creates for himself and who for others?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: xg_p90, xa_p90
- **Selectors.** team, min_minutes
- **Method.** xG/90 against xA/90.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-083]`

### D-084 · Player shot map

- **Question.** Where does a player shoot from and with what quality?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, shot_xg, outcome
- **Selectors.** team, player
- **Method.** Marker size = StatsBomb xG.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-084]`

### D-085 · Shot map split by body part

- **Question.** Do shot locations differ by body part?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, shot_xg, shot_body_part
- **Selectors.** team
- **Method.** One half-pitch per body part.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-085]`

### D-086 · Shot xG density map

- **Question.** Where do shots for and against concentrate?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, shot_xg, outcome
- **Selectors.** team
- **Method.** Density of attempts for and against.
- **Caveat.** Smoothed density interpolates.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-086]`

### D-087 · Player pass map

- **Question.** Where does a player pass from and to?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team, player
- **Method.** Random sample of 600 when larger; completed vs incomplete.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-087]`

### D-088 · Progressive pass map

- **Question.** Where do a player's progressive passes go?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team, player
- **Method.** Completed, start x ≥ 48, ends ≥ 25% closer to goal.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-088]`

### D-089 · Carry map

- **Question.** Where does a player carry the ball?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y, end_x, end_y
- **Selectors.** team, player
- **Method.** Carries ending ≥ 25% closer to goal.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-089]`

### D-090 · Dribble map

- **Question.** Where does a player take opponents on and with what result?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team, player
- **Method.** Coloured by the recorded outcome.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-090]`

### D-091 · Defensive action map

- **Question.** Where does a player defend?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team, player
- **Method.** Tackles, interceptions, blocks, clearances, recoveries.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-091]`

### D-092 · Pressure map

- **Question.** Where does a player press?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team, player
- **Method.** Share of the player's pressure events per zone.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-092]`

### D-093 · Recovery, interception and tackle map

- **Question.** Where does a player win the ball back?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team, player
- **Method.** Three ball-winning event types.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-093]`

### D-094 · Player action heatmap

- **Question.** Where is a player active for a chosen action type?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team, player, kind
- **Method.** Share of actions per 12 × 8 zone.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-094]`

### D-095 · Player touch heatmap

- **Question.** Where does a player touch the ball?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team, player
- **Method.** On-ball events counted as touches.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-095]`

### D-096 · Player spatial KDE

- **Question.** Where is a player's on-ball activity densest?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team, player
- **Method.** Contours of a smoothed histogram.
- **Caveat.** Smoothing interpolates.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-096]`

### D-097 · Convex hull of touch locations

- **Question.** What is a player's observed event footprint?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team, player, match
- **Method.** Hull of the central 90% of touch locations in one match.
- **Caveat.** An event footprint, not the area the player occupied.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-097]`

### D-098 · Role comparison small multiples

- **Question.** How do typical values differ by detailed role?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** min_minutes
- **Method.** Median per primary role; roles under 5 players dropped.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-098]`

### D-099 · Player archetype clusters

- **Question.** Do statistical profiles form recognisable groups?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 20 eligible players
- **Selectors.** team
- **Method.** K-Means on standardised profiles; k by silhouette.
- **Caveat.** Descriptive grouping, validated in K-240 to K-242.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-099]`

### D-100 · PCA player projection

- **Question.** Where do players sit on the main axes of variation?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 20 eligible players
- **Selectors.** team
- **Method.** First two principal components by role family.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-100]`

### D-101 · Player similarity map

- **Question.** Which players have the closest statistical profile?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 20 eligible players
- **Selectors.** team, player, min_minutes
- **Method.** Euclidean distance on z-scores within the role family.
- **Caveat.** Depends on the metric set and the standardisation sample.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-101]`

### D-102 · Consistency versus output quadrant

- **Question.** Who combines volume with steadiness?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** pms: match_id, player_id, minutes_played · at least 10 matches
- **Selectors.** team
- **Method.** Mean progressive actions/90 vs coefficient of variation.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-102]`

### D-103 · Role-fit matrix

- **Question.** Which roles does the evidence support for each player?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** team
- **Method.** Weighted role percentiles, masked by position compatibility.
- **Caveat.** A transparent heuristic.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-103]`

### D-104 · Squad depth chart

- **Question.** Who has actually covered each role?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** appearances: match_role, minutes_played
- **Selectors.** team
- **Method.** Minutes by role and player.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-104]`

### D-105 · Minutes distribution and appearance bars

- **Question.** How is playing time shared?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season: minutes_played, starts
- **Selectors.** team
- **Method.** Minutes, starts and substitute appearances.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-105]`

### D-106 · Rotation / appearance calendar

- **Question.** Who played in which match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played
- **Selectors.** team
- **Method.** Player × match minutes matrix.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-106]`

### D-107 · Minutes-based exposure proxy

- **Question.** How many minutes did a player carry into each match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** workload: minutes_prev_7d, minutes_prev_28d
- **Selectors.** team, player
- **Method.** Minutes in the previous 7, 14 and 28 days.
- **Caveat.** An exposure proxy from league minutes only — not physical load or fatigue.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-107]`

### D-108 · Player report card

- **Question.** What does the evidence say about one player, and what is missing?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** team, player
- **Method.** Identity, exposure, strongest and weakest percentiles, missing evidence.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[D-108]`

## Pitch, spatial and event analytics

### E-109 · Standard pitch with team overlay

- **Question.** Where do the team's actions of a chosen type occur?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team, match, kind
- **Method.** Locations of the selected event kind in one match.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-109]`

### E-110 · Team shot map

- **Question.** Where did the team shoot from in a match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, shot_xg, outcome
- **Selectors.** team, match
- **Method.** Marker size = StatsBomb xG; star = goal.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-110]`

### E-111 · Pass map with arrows

- **Question.** How did the team move the ball in a match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team, match
- **Method.** Arrow heads at the end point; failed passes in red.
- **Caveat.** Random sample of 500 arrows when larger.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-111]`

### E-112 · Pass density heatmap

- **Question.** Where does the team pass from over the season?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team
- **Method.** Share of passes per zone.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-112]`

### E-113 · Pass-origin hexbin

- **Question.** Where do passes start, without smoothing?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** mplsoccer · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team
- **Method.** Hexagonal counts of start locations.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-113]`

### E-114 · Pass-end hexbin

- **Question.** Where do passes arrive?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** mplsoccer · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team
- **Method.** Hexagonal counts of end locations.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-114]`

### E-115 · Team carry map

- **Question.** Where does the team carry the ball forward?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y, end_x, end_y
- **Selectors.** team, match
- **Method.** Carries ending ≥ 25% closer to goal.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-115]`

### E-116 · Progressive action map

- **Question.** Where does the team progress the ball by pass and carry?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y, end_x, end_y
- **Selectors.** team, match
- **Method.** Project definitions stated in the subtitle.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-116]`

### E-117 · Pressure map

- **Question.** Where does the team apply pressure?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team
- **Method.** Share of pressure events per zone over the season.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-117]`

### E-118 · Defensive action zones

- **Question.** In which zones does the team defend?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team
- **Method.** 6 × 3 tactical zones.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-118]`

### E-119 · Touch map

- **Question.** Where does the team have the ball?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team, match
- **Method.** Share of touches per zone in one match.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-119]`

### E-120 · KDE event distribution

- **Question.** Where is a chosen action densest?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team, kind
- **Method.** Smoothed contours.
- **Caveat.** Shading between events is interpolation.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-120]`

### E-121 · Zone heatmaps (3×3, 5×5, tactical)

- **Question.** How are actions shared across tactical zones?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team, kind
- **Method.** Counts and shares per cell.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-121]`

### E-122 · Directional action arrows

- **Question.** In which directions does the team pass?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team
- **Method.** Polar histogram; forward = up; colour = completion rate.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-122]`

### E-123 · Cross and set-piece maps

- **Question.** Where do crosses and set-piece deliveries come from?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team, match
- **Method.** Source cross flag and set-piece pass types.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-123]`

### E-124 · Goalkeeper action map

- **Question.** Where does the goalkeeper act?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, goalkeeper_type
- **Selectors.** team
- **Method.** Goal Keeper events by recorded type.
- **Caveat.** Positions are recorded in the goalkeeper's own attacking frame.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-124]`

### E-125 · Convex hull event footprint

- **Question.** What area do the team's recorded actions of one kind cover?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team, match, kind
- **Method.** Hull of the central 90% of locations.
- **Caveat.** Event footprint, not occupied space.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-125]`

### E-126 · Voronoi diagram

- **Question.** Which player is closest to each point of the pitch?
- **Status.** `not_implemented` — Needs every player's position at the same instant. Event data give one actor per event, and 360 freeze frames show only players inside the camera view, so a Voronoi partition would be invented space.
- **Library / modality / cost.** plotly · tracking · low

### E-127 · Delaunay triangulation

- **Question.** How are team-mates connected spatially at one moment?
- **Status.** `not_implemented` — Needs simultaneous positions of all team-mates (tracking data); not derivable from event locations.
- **Library / modality / cost.** plotly · tracking · low

### E-128 · Pitch-control / space-control map

- **Question.** Which team controls which space?
- **Status.** `not_implemented` — Needs positions and velocities of all 22 players (tracking). Never approximated from event x/y.
- **Library / modality / cost.** plotly · tracking · low

### E-129 · 360 freeze-frame plot

- **Question.** Who was where, inside the camera view, at the moment of a shot?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · 360 · high
- **Requires.** frames_360: 
- **Selectors.** team, match
- **Method.** StatsBomb 360 frame of the match's highest-xG shot.
- **Caveat.** Only players in the camera view are recorded.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-129]`

### E-130 · Animated event sequence

- **Question.** How was the best chance of a match built?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** events: event_id, type, x, y, end_x, end_y
- **Selectors.** team, match
- **Method.** Ball path of the highest-xG possession ending in a shot.
- **Caveat.** Only the ball-carrier's events are known.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-130]`

### E-131 · Spatial comparison team versus opponent

- **Question.** Where did each side have the ball?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id, type, x, y
- **Selectors.** team, match
- **Method.** Zone shares side by side.
- **Caveat.** Shares are within-panel.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-131]`

### E-132 · Half-by-half location maps

- **Question.** Did the team's territory change after the interval?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, period
- **Selectors.** team, match
- **Method.** Both halves shown attacking left to right.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-132]`

### E-133 · Pass progression lanes

- **Question.** Through which lanes does the team progress?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team
- **Method.** Five lanes × three thirds by pass origin.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-133]`

### E-134 · Event transition Sankey

- **Question.** Between which zones does the ball move?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team
- **Method.** Zone = third × (central | wide).
- **Caveat.** Small flows hidden; share shown stated.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-134]`

### E-135 · Pass-flow network

- **Question.** How does the ball flow between pitch zones?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team
- **Method.** Completed passes between thirds × lanes.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-135]`

### E-136 · Event sequence sunburst

- **Question.** How do possessions start and end?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** events: possession, play_pattern
- **Selectors.** team
- **Method.** Play pattern → reached final third → shot / goal.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[E-136]`

## Passing networks and team structure

### F-137 · Pass network by match

- **Question.** Who connected with whom in a match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team, match
- **Method.** Completed passes before the first substitution.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[F-137]`

### F-138 · Season-average pass network

- **Question.** What does the team's typical passing structure look like?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team
- **Method.** All matches pooled; 14 most involved players.
- **Caveat.** Pooled players were not all on the pitch together.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[F-138]`

### F-139 · Network node centrality

- **Question.** Who are the hubs and bridges of the passing game?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome · at least 5 matches
- **Selectors.** team
- **Method.** PageRank, betweenness and pass share averaged over match networks.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[F-139]`

### F-140 · Network with centrality-sized nodes

- **Question.** Which players carry the structure in one match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team, match
- **Method.** Node size and edge width defined in the subtitle.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[F-140]`

### F-141 · Network centrality comparison

- **Question.** Who is a hub and who is a bridge?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome · at least 5 matches
- **Selectors.** team
- **Method.** PageRank vs betweenness, size = pass share.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[F-141]`

### F-142 · Network with role colouring

- **Question.** How do role families connect?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team, match
- **Method.** Node colour = season role family.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[F-142]`

### F-143 · Passing lane direction and progression

- **Question.** Which links move the ball forward?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team, match
- **Method.** Link colour = direction between mean pass origins.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[F-143]`

### F-144 · Network change by score state

- **Question.** Does the passing structure differ when leading?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · high
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome; goals: match_id, scoring_team_id, elapsed_min · at least 5 matches
- **Selectors.** team
- **Method.** Season passes split by the team's score state.
- **Caveat.** Score state is confounded with personnel and opponent behaviour.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[F-144]`

### F-145 · Network before / after substitution

- **Question.** How did the structure look before and after the first change?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team, match
- **Method.** One match, two time windows.
- **Caveat.** Windows differ in length, score and opposition; descriptive only.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[F-145]`

### F-146 · Network robustness (remove-node simulation)

- **Question.** How dependent is the pass graph on each player?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team, match
- **Method.** Change in weighted global efficiency when a node is deleted.
- **Caveat.** A simulation on the recorded graph, not a match forecast.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[F-146]`

### F-147 · Role interaction matrix

- **Question.** Between which roles does the ball travel?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome; appearances: match_role
- **Selectors.** team
- **Method.** Passer role × recipient role.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[F-147]`

### F-148 · Player pair passing heatmap

- **Question.** Which pairs exchange the most passes?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team
- **Method.** Completed passes among the 14 most involved players.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[F-148]`

## Tactical, lineup and formation analytics

### G-149 · Starting XI pitch diagram

- **Question.** What does the evidence-based shortlist look like on the pitch?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role; appearances: match_id, player_id, is_starter, minutes_played · at least 2 matches
- **Selectors.** team, match, formation
- **Method.** Hungarian assignment of candidates to formation slots.
- **Caveat.** Best under the stated scoring model and constraints — a shortlist, not the optimal XI.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-149]`

### G-150 · Actual XI versus shortlisted XI

- **Question.** How similar is the heuristic shortlist to the manager's XI?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role; appearances: match_id, player_id, is_starter, minutes_played · at least 2 matches
- **Selectors.** team, match, formation
- **Method.** Overlap table with the share of the actual XI also shortlisted.
- **Caveat.** Agreement measures similarity, not which choice was better.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-150]`

### G-151 · Formation slots and role suitability

- **Question.** How well does each candidate suit each slot?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role; appearances: match_id, player_id, is_starter, minutes_played · at least 2 matches
- **Selectors.** team, match, formation
- **Method.** Score per candidate and slot; blank = not eligible.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-151]`

### G-152 · Team shape from event locations

- **Question.** Where do each player's actions centre in a match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, player_id
- **Selectors.** team, match
- **Method.** Median touch location per player.
- **Caveat.** Not simultaneous positions and not a formation.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-152]`

### G-153 · Formation frequency

- **Question.** Which formations were used and with what results?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: starting_formation
- **Selectors.** team
- **Method.** Matches and results per starting formation.
- **Caveat.** Small-sample formations are flagged.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-153]`

### G-154 · Role occupancy matrix

- **Question.** Which roles has each player filled?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** appearances: match_role, minutes_played
- **Selectors.** team
- **Method.** Minutes by player and match role.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-154]`

### G-155 · Formation transitions within matches

- **Question.** Which in-match formation changes were recorded?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** formations: formation, type, team_name
- **Selectors.** team
- **Method.** Starting XI → Tactical Shift formation labels.
- **Caveat.** Recorded label changes only.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-155]`

### G-156 · Position / role metric profile

- **Question.** What distinguishes the role families statistically?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Method.** Median metric by role family (z-coloured, raw values printed).
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-156]`

### G-157 · Team tactical radar

- **Question.** What is the team's tactical fingerprint?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** Style indicators as percentiles among teams in the dataset.
- **Caveat.** Opponents have two matches each.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-157]`

### G-158 · Match dominance scatter

- **Question.** How dominant was each performance?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** xG for vs xG against per match by result.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-158]`

### G-159 · Player-role fit heatmap

- **Question.** Where could each player be used on the evidence?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** team
- **Method.** Same matrix as D-103, in the tactical context.
- **Caveat.** A transparent heuristic.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-159]`

### G-160 · Squad depth by role

- **Question.** How many players cover each role and how much have they played there?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** appearances: match_role, minutes_played
- **Selectors.** team
- **Method.** Minutes by role and player.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-160]`

### G-161 · Bench role composition

- **Question.** What options were on the bench in each match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played
- **Selectors.** team
- **Method.** Bench players by season role family.
- **Caveat.** Bench players have no recorded position on the day.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-161]`

### G-162 · Continuity / rotation matrix

- **Question.** How stable was selection across the season?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played
- **Selectors.** team
- **Method.** Player × match minutes matrix.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-162]`

### G-163 · Lineup similarity matrix

- **Question.** Which matches shared the same starting XI?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 3 matches
- **Selectors.** team
- **Method.** Jaccard similarity of starting XIs.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-163]`

### G-164 · Co-start network

- **Question.** Which players usually start together?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 5 matches
- **Selectors.** team
- **Method.** Links = starts together.
- **Caveat.** Circular layout: positions carry no meaning.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-164]`

### G-165 · Player pairing minutes matrix

- **Question.** How long has each pair been on the pitch together?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** spells: match_id, player_id, start, end
- **Selectors.** team
- **Method.** Shared minutes from reconstructed, validated on-pitch spells.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-165]`

### G-166 · Starting XI score component breakdown

- **Question.** Why is each player in the shortlist?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role; appearances: match_id, player_id, is_starter, minutes_played · at least 2 matches
- **Selectors.** team, match, formation
- **Method.** Weighted components per pick.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-166]`

### G-167 · Formation sensitivity chart

- **Question.** How much does the shortlist depend on the formation template?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · high
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role; appearances: match_id, player_id, is_starter, minutes_played · at least 2 matches
- **Selectors.** team, match
- **Method.** Best total score under each template.
- **Caveat.** Heuristic totals, comparable only within this model.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-167]`

### G-168 · Candidate selection frontier

- **Question.** Which candidates are efficient on two competing criteria?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role; appearances: match_id, player_id, is_starter, minutes_played · at least 2 matches
- **Selectors.** team, match, formation
- **Method.** Role fit vs recent form with the Pareto front.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-168]`

### G-169 · Constraint feasibility audit

- **Question.** Which constraints were enforced and what evidence is missing?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role; appearances: match_id, player_id, is_starter, minutes_played · at least 2 matches
- **Selectors.** team, match, formation
- **Method.** Checklist of constraints and evidence gaps.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[G-169]`

## Substitution and match-state analytics

### H-170 · Substitution minute histogram

- **Question.** When are substitutions made?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** subs: match_id, team_name, minute, game_state
- **Selectors.** team
- **Method.** Share of substitutions per analytical timing band.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[H-170]`

### H-171 · Substitution timing by score state

- **Question.** Does timing differ when leading, level or behind?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** subs: match_id, team_name, minute, game_state
- **Selectors.** team
- **Method.** Minute distribution per score state.
- **Caveat.** Score state reflects team strength as much as intent.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[H-171]`

### H-172 · Substitution timing by role

- **Question.** Are some roles replaced earlier?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** subs: minute, off_role
- **Selectors.** team
- **Method.** Minute distribution by role going off.
- **Caveat.** Roles with fewer than 5 substitutions are not drawn.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[H-172]`

### H-173 · Incoming / outgoing role Sankey

- **Question.** Which roles replace which?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** subs: off_role, on_role
- **Selectors.** team
- **Method.** Role going off → role coming on.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[H-173]`

### H-174 · Substitution role-matching matrix

- **Question.** How often is a change like-for-like?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** subs: off_role, on_role
- **Selectors.** team
- **Method.** Off role × on role counts.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[H-174]`

### H-175 · Before / after substitution metrics

- **Question.** What did the team's output look like around changes?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · high
- **Requires.** subs: match_id, team_name, minute, game_state
- **Method.** Team xG per 15 minutes in the windows before and after substitution decisions.
- **Caveat.** Descriptive only: confounded by score, opponent changes, injuries and regression to the mean.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[H-175]`

### H-176 · Score state at substitution

- **Question.** In which score state are changes made?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** subs: match_id, team_name, minute, game_state
- **Selectors.** team
- **Method.** Substitutions by score state at the moment of the change.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[H-176]`

### H-177 · Substitution event timeline

- **Question.** When did each change happen in a match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** subs: match_id, team_name, minute, game_state
- **Selectors.** team, match
- **Method.** Both teams' substitutions on the elapsed clock.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[H-177]`

### H-178 · Bench usage

- **Question.** Which squad members are used from the bench?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played
- **Selectors.** team
- **Method.** Times named on the bench, split into used and unused.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[H-178]`

### H-179 · Remaining bench availability through a match

- **Question.** What options remained after each change?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played; subs: match_id, team_name, minute, game_state
- **Selectors.** team, match
- **Method.** Unused substitutes after each change.
- **Caveat.** Availability = named and not yet used; fitness is unknown.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[H-179]`

### H-180 · Candidate substitute comparison

- **Question.** Who are the bench options at a chosen moment?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played; season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** team, match, minute
- **Method.** Ranked bench candidates with evidence and risks.
- **Caveat.** Candidates are restricted to the match-day bench not yet used at that minute.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[H-180]`

### H-181 · Substitution candidate score decomposition

- **Question.** Why is a candidate ranked where he is?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played; season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** team, match, minute
- **Method.** Role compatibility, intent fit, recent form, sample reliability.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[H-181]`

### H-182 · Alternative substitution scenario

- **Question.** What would the heuristic shortlist at a chosen minute?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played; season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** team, match, minute
- **Method.** Counterfactual simulation at the selected minute.
- **Caveat.** A heuristic shortlist — never a claim about what would have happened.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[H-182]`

### H-183 · Substitution pattern by manager

- **Question.** What is the manager's substitution profile?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** subs: manager_name, minute · at least 10 matches
- **Selectors.** team
- **Method.** Timing bands × score state for the focus manager.
- **Caveat.** Requires at least 10 matches for the manager.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[H-183]`

### H-184 · Late / early substitution profile

- **Question.** Which teams change early and which late?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** subs: match_id, team_name, minute, game_state
- **Method.** Team × timing band share.
- **Caveat.** Opponents have two matches each.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[H-184]`

### H-185 · Manpower-state analysis

- **Question.** How do changes relate to red cards?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** subs: man_advantage
- **Selectors.** team
- **Method.** Substitutions at level, player-up and player-down.
- **Caveat.** Very few sending-offs in the dataset.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[H-185]`

## Managerial intelligence

### I-186 · Formation usage by manager

- **Question.** Which formations does the manager choose?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: manager_name, starting_formation
- **Selectors.** team
- **Method.** Observed starting formations and results.
- **Caveat.** Observable choices, not managerial ability.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[I-186]`

### I-187 · Starting XI continuity and rotation trend

- **Question.** How many changes between consecutive matches?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 3 matches
- **Selectors.** team
- **Method.** Lineup changes between consecutive analysed matches.
- **Caveat.** Cup and European matches between league games are not in the data.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[I-187]`

### I-188 · Substitution timing profile

- **Question.** When does the manager make changes?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** subs: timing_band, minute
- **Selectors.** team
- **Method.** Minute distribution by timing band.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[I-188]`

### I-189 · Score-state-specific substitution pattern

- **Question.** How do changes differ by score state?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** subs: match_id, team_name, minute, game_state
- **Selectors.** team
- **Method.** State → timing → role off → role on.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[I-189]`

### I-190 · Role-specific substitution tendency

- **Question.** Which roles are substituted off most?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** subs: off_role
- **Selectors.** team
- **Method.** Share by role with Wilson intervals.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[I-190]`

### I-191 · Bench utilisation

- **Question.** How many of the allowed changes are used?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** subs: match_id, team_name, minute, game_state
- **Selectors.** team
- **Method.** Substitutions used per match.
- **Caveat.** The limit is a configured rule.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[I-191]`

### I-192 · Response timeline after conceding

- **Question.** How soon after conceding is the next change made?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** subs: match_id, team_name, minute, game_state; goals: match_id, scoring_team_id, elapsed_min
- **Selectors.** team
- **Method.** Minutes from a goal conceded to the next substitution.
- **Caveat.** Timing description, not a measured reaction.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[I-192]`

### I-193 · Manager comparison small multiples

- **Question.** How does the focus manager compare with the pooled others?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** managers: match_id, team_id, manager_name · at least 10 matches
- **Selectors.** team
- **Method.** Indicators next to the pooled value of all other managers.
- **Caveat.** Other managers have two matches each, all against the focus team.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[I-193]`

### I-194 · Manager decision evidence cards

- **Question.** What do the observable decisions add up to?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · high
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** Evidence cards with scope and limitation.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[I-194]`

### I-195 · Manager pattern uncertainty intervals

- **Question.** How uncertain are per-manager proportions?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** managers: match_id, team_id, manager_name
- **Method.** Wilson intervals and beta-binomial shrinkage.
- **Caveat.** Small samples cannot be ranked.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[I-195]`

### I-196 · Manager by match

- **Question.** Who was the manager for each analysed match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: manager_name
- **Selectors.** team
- **Method.** Identity from the matches file.
- **Caveat.** Tenure outside the analysed matches is not in the data.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[I-196]`

### I-197 · Tactical change frequency

- **Question.** How often is the formation changed within matches?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: in_match_formation_changes
- **Selectors.** team
- **Method.** Recorded Tactical Shift changes.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[I-197]`

### I-198 · Managerial decision audit trail

- **Question.** What decisions were recorded in a match, in order?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** subs: match_id, team_name, minute, game_state; formations: match_id, team_id, formation
- **Selectors.** team, match
- **Method.** Substitutions and formation records with context.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[I-198]`

## Statistics, inference and uncertainty

### J-199 · Pearson correlation matrix

- **Question.** Which player metrics are linearly related?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** min_minutes
- **Method.** Pairwise-complete n in the hover.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-199]`

### J-200 · Spearman rank correlation matrix

- **Question.** Which player metrics are monotonically related?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** min_minutes
- **Method.** Rank-based; robust to skew.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-200]`

### J-201 · Kendall correlation matrix

- **Question.** Do the rank relations hold under Kendall's τ?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** min_minutes
- **Method.** Concordance-based.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-201]`

### J-202 · Correlation forest plot with confidence intervals

- **Question.** Which match variables are associated with goal difference?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 10 matches
- **Selectors.** team
- **Method.** Spearman ρ, 2,000 match-level bootstrap resamples, Benjamini–Hochberg.
- **Caveat.** One team-season: low power; association only.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-202]`

### J-203 · Pairwise scatter with regression and diagnostics

- **Question.** How do two player metrics relate, with residuals?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** metric, metric_y, min_minutes
- **Method.** OLS line, residual panel, three coefficients; LOESS when statsmodels is installed.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-203]`

### J-204 · Pair plot / scatter matrix

- **Question.** How do several metrics relate pairwise?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** min_minutes
- **Method.** Scatter-plot matrix by role family.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-204]`

### J-205 · Clustered correlation heatmap

- **Question.** Which metrics form correlated blocks?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** min_minutes
- **Method.** Spearman matrix reordered by hierarchical clustering.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-205]`

### J-206 · Partial correlation

- **Question.** Do associations with goal difference survive adjusting for venue?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 15 matches
- **Selectors.** team
- **Method.** Rank partial correlation given home / away.
- **Caveat.** One observed covariate; unobserved confounding remains.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-206]`

### J-207 · Bootstrap distribution

- **Question.** How uncertain is a season average?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 8 matches
- **Selectors.** team, team_metric
- **Method.** 4,000 resamples of matches.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-207]`

### J-208 · Confidence interval forest plot

- **Question.** Which players are separated once uncertainty is shown?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** pms: match_id, player_id, minutes_played · at least 6 matches
- **Selectors.** team
- **Method.** Match-level resampling.
- **Caveat.** Overlapping intervals are ties.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-208]`

### J-209 · Permutation test null distribution

- **Question.** Could the home / away gap arise by chance?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 8 matches
- **Selectors.** team, team_metric
- **Method.** 5,000 label permutations.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-209]`

### J-210 · Group comparison box / violin plots

- **Question.** How does a team metric differ by venue?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 6 matches
- **Selectors.** team, team_metric
- **Method.** Every match drawn.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-210]`

### J-211 · Effect-size plot

- **Question.** How large are the group differences, not just whether they are significant?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 8 matches
- **Selectors.** team
- **Method.** Cliff's δ with magnitude bands.
- **Caveat.** p-values shown are unadjusted.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-211]`

### J-212 · Kruskal–Wallis post-hoc comparisons

- **Question.** Which groups differ pairwise?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** metric, group, min_minutes
- **Method.** Pairwise Mann–Whitney with BH adjustment.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-212]`

### J-213 · Multiple-testing adjusted p-values

- **Question.** How many findings survive false-discovery control?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 10 matches
- **Selectors.** team
- **Method.** Raw p vs Benjamini–Hochberg q.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-213]`

### J-214 · Power / sensitivity curve

- **Question.** What size of association can this sample detect?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** Power of a two-sided correlation test by n.
- **Caveat.** Fisher z approximation.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-214]`

### J-215 · Missing-data sensitivity

- **Question.** Does a result depend on the minutes threshold?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** metric, metric_y
- **Method.** Correlation under six inclusion rules.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-215]`

### J-216 · Robust versus non-robust estimates

- **Question.** Do outliers drive any association?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 8 matches
- **Selectors.** team
- **Method.** Pearson vs Spearman.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-216]`

### J-217 · Time trend and autocorrelation

- **Question.** Is there a trend or run pattern in a team metric?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 12 matches
- **Selectors.** team, team_metric
- **Method.** Series, rolling mean and autocorrelation by lag.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-217]`

### J-218 · Partial dependence of the fitted model

- **Question.** How does the predicted start probability vary with a feature?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** PDP with ICE curves.
- **Caveat.** Only for the model that passed the sample gate.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-218]`

### J-219 · Bootstrap stability plot

- **Question.** How quickly does an estimate settle as matches accumulate?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 8 matches
- **Selectors.** team, team_metric
- **Method.** Estimate and interval using the first n matches.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-219]`

### J-220 · Reliability / calibration plot

- **Question.** Can the predicted probabilities be trusted as probabilities?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** Reliability diagram with bin sizes and Brier score.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[J-220]`

## Machine learning and diagnostic plots

### K-221 · Baseline model comparison

- **Question.** Do the models beat a simple rule?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** Expanding-window CV split by match; baseline = started previous match.
- **Caveat.** Target = start selection of the focus team; nothing generalises beyond this team-season.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-221]`

### K-222 · Confusion matrix

- **Question.** Which errors does the best model make?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** Top-11 decision rule on the hold-out.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-222]`

### K-223 · ROC curve

- **Question.** How well do the models rank starters?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** Chronological hold-out; baseline as a point.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-223]`

### K-224 · Precision–recall curve

- **Question.** What precision is achieved at each recall?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** With the positive-class rate as reference.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-224]`

### K-225 · Calibration curve

- **Question.** Are predicted probabilities calibrated?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** Five probability bins with n.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-225]`

### K-226 · Brier score comparison

- **Question.** Which model has the most accurate probabilities?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** Lower is better; base-rate reference shown.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-226]`

### K-227 · Threshold trade-off chart

- **Question.** How do precision and recall trade off?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** Precision, recall and F1 by threshold.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-227]`

### K-228 · Permutation feature importance

- **Question.** Which features does the model rely on?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** Drop in hold-out ROC-AUC, 30 repeats.
- **Caveat.** Describes the model, not causal levers.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-228]`

### K-229 · SHAP summary

- **Question.** How does each feature push individual predictions?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** TreeExplainer on gradient boosting, hold-out rows.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-229]`

### K-230 · SHAP dependence plot

- **Question.** How does a feature's contribution change with its value?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** Top feature by mean |SHAP|.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-230]`

### K-231 · Partial dependence / ICE

- **Question.** What is the average and individual effect of a feature?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** PDP over ICE curves.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-231]`

### K-232 · Residual distribution

- **Question.** How are the probability errors distributed?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** Actual − predicted probability, by outcome.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-232]`

### K-233 · Residual versus fitted plot

- **Question.** Is the model systematically off in some probability range?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** Binned residuals with ±1.96 SE.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-233]`

### K-234 · Error by subgroup

- **Question.** For which role families is the model worse?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** Error rate by role family.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-234]`

### K-235 · Learning curve

- **Question.** Would more matches help?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** Training and hold-out AUC by training matches.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-235]`

### K-236 · Cross-validation score distribution

- **Question.** How variable are the scores across folds?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · high
- **Requires.** appearances: match_id, player_id, is_starter, minutes_played · at least 15 matches
- **Selectors.** team
- **Method.** One point per time-ordered fold.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-236]`

### K-237 · PCA scree plot

- **Question.** How many dimensions do player profiles have?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 20 eligible players
- **Method.** Explained variance with cumulative curve.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-237]`

### K-238 · PCA loading plot

- **Question.** Which metrics define each component?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 20 eligible players
- **Method.** Loadings of the first four components.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-238]`

### K-239 · PCA player map

- **Question.** Where do players sit in the reduced space?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 20 eligible players
- **Selectors.** team
- **Method.** PC1 × PC2 by role family.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-239]`

### K-240 · Cluster model selection

- **Question.** How many clusters does the data support?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 20 eligible players
- **Method.** Elbow, silhouette, Davies–Bouldin, GMM BIC.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-240]`

### K-241 · Cluster projection and profile

- **Question.** What separates the clusters?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 20 eligible players
- **Method.** Sizes and ε² per metric.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-241]`

### K-242 · Cluster stability / ARI comparison

- **Question.** Do different algorithms and resamples agree?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 20 eligible players
- **Method.** Adjusted Rand index between four algorithms.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-242]`

### K-243 · Outlier / anomaly score chart

- **Question.** Which players have the most unusual profiles?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 20 eligible players
- **Method.** Isolation-forest score.
- **Caveat.** Unusual is not better or worse.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[K-243]`

### K-244 · Forecast residuals

- **Question.** How accurate is a forecast of future results?
- **Status.** `not_implemented` — Forecasting is not justified: 34 matches of one team give no temporal depth for a held-out forecast horizon, and no out-of-sample season exists in the data.
- **Library / modality / cost.** plotly · model output · low

## Additional project charts and composite dashboards

### L-245 · Dataset coverage cards

- **Question.** What is the real scale of the dataset?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: event_id; manifest: bytes, status
- **Method.** Rows, files and bytes actually read.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-245]`

### L-246 · Event taxonomy treemap

- **Question.** What is the event stream made of?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: type
- **Method.** Events by family and type.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-246]`

### L-247 · Event volume per match

- **Question.** How many events of each family does a match produce?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: type
- **Method.** Stacked event counts per match.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-247]`

### L-248 · Cumulative xG of a match

- **Question.** How did chance quality accumulate in a match?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, shot_xg, outcome
- **Selectors.** team, match
- **Method.** Step chart of StatsBomb xG by team.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-248]`

### L-249 · Match xG-by-interval chart

- **Question.** In which spells of the match were chances created?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, shot_xg, outcome; goals: match_id, scoring_team_id, elapsed_min
- **Selectors.** team, match
- **Method.** xG per 5-minute bucket for each side, with final-third touch share.
- **Caveat.** This is xG per interval, not a validated momentum measure.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-249]`

### L-250 · On-pitch Gantt chart

- **Question.** Who was on the pitch when?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** spells: match_id, player_id, start, end; goals: match_id, scoring_team_id, elapsed_min
- **Selectors.** team, match
- **Method.** Reconstructed on-pitch spells with goals marked.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-250]`

### L-251 · Goals and chances by match phase

- **Question.** In which phases of matches are goals and chances concentrated?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, shot_xg, outcome; goals: match_id, scoring_team_id, elapsed_min
- **Selectors.** team
- **Method.** Season totals by 15-minute phase.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-251]`

### L-252 · Opponent bubbles

- **Question.** Against whom were chances created and conceded?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result
- **Selectors.** team
- **Method.** xG for vs against per opponent.
- **Caveat.** Two meetings per opponent.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-252]`

### L-253 · Shot-quality distribution for and against

- **Question.** How does shot quality compare for and against?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, shot_xg, outcome
- **Selectors.** team
- **Method.** xG-per-shot distributions with conversion.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-253]`

### L-254 · Squad similarity dendrogram

- **Question.** Which squad members have similar statistical profiles?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** team
- **Method.** Complete-linkage clustering of standardised profiles.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-254]`

### L-255 · Action-mix ternary plot

- **Question.** What mix of creating, progressing and defending does each player have?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** team, min_minutes
- **Method.** Share of per-90 actions in three families.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-255]`

### L-256 · Player × match contribution matrix

- **Question.** In which matches did each player contribute chances?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** pms: xg, xa
- **Selectors.** team
- **Method.** xG + xA by player and match.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-256]`

### L-257 · Minutes sunburst

- **Question.** How is playing time distributed across roles and players?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season: minutes_played
- **Selectors.** team
- **Method.** Role family → role → player by minutes.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-257]`

### L-258 · Split violin: squad versus others

- **Question.** How does the squad compare with the other players in the data?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** team, metric, min_minutes
- **Method.** Squad (left) vs others (right) by role family.
- **Caveat.** Others are observed only in their matches against the focus team.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-258]`

### L-259 · Scatter with marginal distributions

- **Question.** How do two metrics relate, with their distributions?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 10 eligible players
- **Selectors.** metric, metric_y, min_minutes
- **Method.** Marginal histogram and box plot.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-259]`

### L-260 · Key-pass map

- **Question.** Where do the passes that lead to shots come from?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team
- **Method.** Pass origin → shot location; amber = assist.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-260]`

### L-261 · Pass destination density

- **Question.** Where do a player's completed passes end?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team, player
- **Method.** Density of end locations.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-261]`

### L-262 · Points versus expected points

- **Question.** Did results run ahead of or behind chance quality?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result; events: x, y, shot_xg, outcome
- **Selectors.** team
- **Method.** Shot-level Bernoulli simulation (5,000 runs per match).
- **Caveat.** xPts is a model output.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-262]`

### L-263 · Expected Threat surface

- **Question.** Which areas of the pitch carry the most threat in these matches?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · medium
- **Requires.** events: event_id, type, x, y, end_x, end_y
- **Method.** Project-computed xT, 16 × 12 grid, value iteration.
- **Caveat.** Fitted in-sample on the analysed matches; not a StatsBomb field.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-263]`

### L-264 · xT added by player

- **Question.** Who moves the ball into more threatening areas?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · model output · medium
- **Requires.** events: event_id, type, x, y, end_x, end_y
- **Selectors.** team
- **Method.** xT(end) − xT(start) of completed passes and carries.
- **Caveat.** Derived project value on an in-sample grid.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-264]`

### L-265 · Pass-flow map

- **Question.** What is the typical pass direction from each zone?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** mplsoccer · event · low
- **Requires.** events: x, y, end_x, end_y, pass_recipient_id, outcome
- **Selectors.** team
- **Method.** Mean pass direction per zone.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-265]`

### L-266 · Percentile pizza chart

- **Question.** What is a player's percentile profile in a compact form?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** mplsoccer · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** team, player
- **Method.** Role-group percentiles; all slices higher = higher percentile.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-266]`

### L-267 · Shortlist versus actual XI over the season

- **Question.** How close is the pre-match shortlist to the manager's choices?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · high
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role; appearances: match_id, player_id, is_starter, minutes_played · at least 4 matches
- **Selectors.** team
- **Method.** Share of the actual XI also shortlisted, per match.
- **Caveat.** Agreement is similarity, not quality.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-267]`

### L-268 · Two formation shortlists compared

- **Question.** How does the shortlist change under another formation?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · high
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role; appearances: match_id, player_id, is_starter, minutes_played · at least 2 matches
- **Selectors.** team, match, formation
- **Method.** Slot scores under two templates.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-268]`

### L-269 · Minimum-minutes sensitivity

- **Question.** How many players survive each minutes threshold?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season: minutes_played
- **Method.** Eligible players by threshold.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-269]`

### L-270 · Key players radar grid

- **Question.** What do the most-used players look like at a glance?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** team
- **Method.** Role-specific percentile radars for six players.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-270]`

### L-271 · Player dashboard

- **Question.** What is one player's complete evidence view?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role
- **Selectors.** team, player
- **Method.** Composite of profile, form and maps.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-271]`

### L-272 · Match dashboard

- **Question.** What is one match's complete evidence view?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** events: x, y, shot_xg, outcome; goals: match_id, scoring_team_id, elapsed_min
- **Selectors.** team, match
- **Method.** Composite of shots, xG and territory.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-272]`

### L-273 · Substitution dashboard

- **Question.** What is the team's substitution behaviour at a glance?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** subs: match_id, team_name, minute, game_state
- **Selectors.** team
- **Method.** Composite of timing, state and role flow.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-273]`

### L-274 · Goals scored and conceded by origin

- **Question.** How are goals scored and conceded?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** goals: match_id, scoring_team_id, elapsed_min; events: play_pattern, shot_body_part
- **Selectors.** team
- **Method.** By play pattern and body part.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-274]`

### L-275 · Goalkeeping reference

- **Question.** How do goalkeepers compare on shots faced?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · low
- **Requires.** events: shot_xg, outcome; appearances: match_role
- **Method.** Pre-shot xG of on-target shots faced minus goals conceded.
- **Caveat.** No post-shot xG exists in the source: a crude reference on small samples.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-275]`

### L-276 · Three correlation methods compared

- **Question.** Do Pearson, Spearman and Kendall agree?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** team_stats: match_id, team_name, xg, xg_against, result · at least 10 matches
- **Selectors.** team
- **Method.** Three coefficients per variable.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-276]`

### L-277 · Four clustering algorithms projected

- **Question.** Do different algorithms find the same groups?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · medium
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 20 eligible players
- **Method.** K-Means, Ward, GMM and DBSCAN labels in PCA space.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-277]`

### L-278 · Cluster stability under resampling

- **Question.** Does the grouping survive resampling of players?
- **Status.** `implemented_and_available`
- **Library / modality / cost.** plotly · event · high
- **Requires.** season_pct: player_id, player_name, minutes_played, primary_role · at least 20 eligible players
- **Method.** ARI of 40 bootstrap refits against the full-sample partition.
- **Test.** `tests/test_chart_renderers.py::test_renderer_on_fixture[L-278]`
