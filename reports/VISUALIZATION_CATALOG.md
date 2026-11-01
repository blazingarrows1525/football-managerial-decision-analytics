# Visualization Catalogue

All charts are Plotly figures from `src/football_analytics/visualizations.py`, rendered in the executed notebook
(57 figures in the default run). Every function checks its required columns and returns a readable "no data"
figure instead of failing (tested in `tests/test_visualization_empty_states.py`). In `DEMO_SYNTHETIC` mode every
chart carries a red "Illustrative synthetic data" banner. Status ✅ = implemented and executed on the real
StatsBomb run.

Interaction types: **H** hover details · **D** in-chart Plotly dropdown (works in exported HTML) · **W** notebook
ipywidgets control (live Colab/Jupyter) · **Z** zoom/pan/legend toggling (all charts).

| # | Chart (function) | Notebook § | Research question | Source columns | Interaction | How to read it | Limitations | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | Dataset coverage cards (`coverage_cards`) | 4 | Dataset collection evidence | `dataset_scale` output | H | Actual matches, teams, players, events, subs, goals, MB, files | Counts describe the selected sample only | ✅ |
| 2 | Match timeline (`match_timeline`) | 8 | Context for decisions | goals, cards, substitutions, tactical shifts, `elapsed_min` | H | Markers on elapsed playing time per team | Clock vs elapsed time differ in stoppage | ✅ |
| 2b | Cumulative xG (`cumulative_xg_chart`) | 8 | Match flow | shot `elapsed_min`, `shot_xg` | H | Step lines; stars = goals | xG is StatsBomb's model output | ✅ |
| 3 | Results overview (`results_overview`) | 8 | Team performance | `team_match_stats` goal diff, result | H | Bar per match coloured W/D/L | Results reconcile with published scores (QC) | ✅ |
| 4 | Contribution leaderboard (`leaderboard_chart`) | 9 | RQ2 | season per-90, minutes, percentile | D, H | Top 15 for selected metric; colour = role family | Threshold-dependent (see #31) | ✅ |
| 5 | Player radar (`player_radar`) | 9 | RQ1/RQ2 | `*_pct` role metrics | H, W (player) | Percentile vs benchmark group; dotted = 50th | Benchmark group may be role family (labelled) | ✅ |
| 6 | Comparison scatter (`comparison_scatter`) | 9 | RQ2 | any two per-90 metrics | D (x and y), H | Size = minutes; dotted lines = medians | Association only | ✅ |
| 7 | Form trend (`form_trend`) | 9 | RQ6 | `player_match_stats` rolling per-90 | H, W | Rolling 5-appearance per-90 + minutes bars | Short windows are noisy | ✅ |
| 8 | Minutes / workload (`workload_bars`) | 9 | RQ6 | minutes, starts, sub/unused counts | H | Horizontal bars, text = starts/sub apps | Dataset matches only (no cups) | ✅ |
| 9 | Role distribution (`role_distribution`) | 8 | RQ1 | per-90 by `primary_role` | D, H | Box + points per role; n in title | Small groups for some roles | ✅ |
| 10 | Team trend (`team_trend`) | 8 | Team performance | xG for/against, goals | H | Rolling xG lines + match goals | Opponent order confounds | ✅ |
| 11 | Formation frequency (`formation_frequency`) | 10 | RQ3 | starting formation, result, ppm | H | Stacked W/D/L; * = small sample | Formation from source Starting XI | ✅ |
| 12 | Formation comparison (`formation_comparison`) | 10 | RQ3 | xG for/against, field tilt by formation | H | Grouped bars with n | Descriptive; opponent/squad confounding | ✅ |
| 13 | Starting XI pitch (`xi_pitch`) | 11 | XI decision support | optimiser lineup, slot x/y, components | H, W (formation, unavailable) | Marker colour = slot score; hover = all components | Scores are not probabilities | ✅ |
| 13b | Score decomposition (`score_decomposition`) | 11 | Explainability | weighted components × compatibility | H | Stacked contribution per player | Weights are analyst choices | ✅ |
| 14 | Alternative XI comparison (`alternative_xi_comparison`) | 11 | What-if | two lineups' slot scores | H | Grouped bars per slot; title counts changes | Rotation rule is illustrative | ✅ |
| 15 | Shot map (`shot_map`) | 10 | Team tactics | shot x/y, outcome, xG | H, legend toggle | Half pitch; size = xG; star = goal | Open-play/set-piece mixed | ✅ |
| 16 | Pass map (`pass_map`) | 10 | Player/team tactics | pass start/end, outcome, recipient | H | Lines navy = completed, red = incomplete | Sampled above 600 passes (stated) | ✅ |
| 17 | Pass network (`pass_network_chart`) | 10 | Team structure | completed passer→recipient, average origin | H | Node = avg pass origin; edge width = passes | Until first substitution only | ✅ |
| 18 | Progressive actions (`progressive_actions_map`) | 10 | Player profile | progressive pass/carry flags | H | Navy passes, amber dotted carries | Project definition, not provider metric | ✅ |
| 19 | Substitution timeline (`substitution_timeline`) | 12 | RQ4 | subs elapsed, players, state | H | Triangles labelled with incoming player | — | ✅ |
| 20 | Substitution timing histogram (`sub_timing_histogram`) | 12 | RQ4 | `timing_band` | H | Share of subs per band; focus vs opponents | Bands are configurable analytical choices | ✅ |
| 21 | Subs by score state (`subs_by_state`) | 12 | RQ4 | `game_state`, minute | H | Share + minute box per state | State driven by team strength | ✅ |
| 22 | Role flow Sankey (`role_flow_sankey`) | 12 | RQ5 | off_role → on_role | H | Grey = like-for-like, amber = role change | Roles from event positions | ✅ |
| 23 | Pre/post substitution windows (`impact_chart`) | 12 | RQ8 | decision windows, team rates | H, legend | Post − pre per 15 min by state; clean vs contaminated | **Association, not causal effect** | ✅ |
| 23b | Incoming-candidate decomposition (`candidate_comparison`) | 12 | RQ5 | candidate component scores | H, W (match/minute/intent) | Stacked weighted points per bench player | Pre-match evidence only | ✅ |
| 24 | Manager formation distribution (`manager_formation_distribution`) | 13 | RQ7 | formations by match, result | H | Donut share + formation-by-match strip | Team-level proxy for manager choice | ✅ |
| 25 | Manager rotation trend (`rotation_trend`) | 13 | RQ6/RQ7 | starters retained, days between matches | H | Bars = XI changes, line = days gap | Missing cup matches | ✅ |
| 26 | Manager substitution profile (`manager_sub_profile`) | 13 | RQ7 | timing band × game state | H | Heatmap of counts | Sample size in title | ✅ |
| 27 | Correlation heatmap (`correlation_heatmap`) | 8 | EDA | selected per-90 metrics | H | Spearman ρ, diverging scale | Shared minutes/role drive many pairs | ✅ |
| 28 | Feature distributions (`feature_distributions`) | 8 | EDA | per-90 metrics | D, H | Histogram per metric | Eligible players only | ✅ |
| 29 | Coverage heatmap (`missingness_heatmap`) | 5 | Data quality | field completeness by event type | H | % present; blanks often structural | — | ✅ |
| 30 | Model evaluation (`confusion_matrix_chart`, `roc_chart`, `calibration_chart`) | 14 | RQ6 | chronological hold-out predictions | H | Top-11 rule confusion matrix, ROC, calibration bins | Small test set (200 rows) | ✅ |
| 31 | Minutes-threshold sensitivity (`threshold_sensitivity_chart`) | 7 | RQ2 | minutes | H | Eligible players vs threshold | — | ✅ |

### Dashboards and advanced visuals (`dashboards.py`, `advanced_visuals.py`)
| # | Chart (function) | Notebook § | Research question | Source columns | Interaction | How to read it | Limitations | Status |
|---|---|---|---|---|---|---|---|---|
| D1 | **Season dashboard** (`season_dashboard`) | 8 | Team performance | team-match stats, xPts | H | KPI cards; cumulative points vs expected points vs 2-ppm pace; xG for (up) / against (down) with goal-difference diamonds | xPts assumes independent shots | ✅ |
| D2 | **Player dashboard** (`player_dashboard`) | 9 | RQ1/RQ2 | season percentiles, player-match stats, located touches | H, W (player) | KPI cards, percentile radar, on-ball heatmap, per-match minutes + xG+xA (stars = scored) | Benchmark group stated in title | ✅ |
| D3 | **Match dashboard** (`match_dashboard`) | 8 | Match flow | events of one match | H | Momentum (5-min xG), cumulative xG, both teams' shot maps | Single match | ✅ |
| D4 | **Substitution dashboard** (`substitution_dashboard`) | 12 | RQ4/RQ5 | enriched substitutions | H | KPI cards, timing band × state, most-used substitutes, every change on minute × score grid | Focus team only | ✅ |
| 32 | Pitch action heatmap (`action_heatmap`) — touches, pressures, defensive actions, opponents' touches | 9, 10 | Player/team tactics | located events | H | Share of actions per 10×10 zone; lines drawn above the heat | Zones are fixed bins | ✅ |
| 33 | Squad rotation matrix (`rotation_matrix`) | 13 | RQ6 | appearances | H | Player × match minutes; ● started, ▲ came on, · unused, blank = not in squad | Dataset matches only | ✅ |
| 34 | Starting-XI similarity (`lineup_similarity`) | 13 | RQ6/RQ7 | starters per match | H | Jaccard of XIs between every pair of matches; dark blocks = stable periods | — | ✅ |
| 35 | Squad percentile matrix (`squad_percentile_heatmap`) | 9 | RQ1/RQ2 | `*_pct` | H | Player × metric percentile, diverging around the 50th | Min 450 minutes | ✅ |
| 36 | Minutes sunburst (`minutes_sunburst`) | 9 | RQ6 | minutes by role | H, click-to-zoom | Role family → role → player area = minutes | Role = primary role | ✅ |
| 37 | Match momentum (`match_momentum`) | 8 | Match flow | xG and final-third actions per 5 min | H | Diverging xG bars, amber line = final-third share | Buckets of elapsed time | ✅ |
| 38 | Phase profile (`phase_profile`) | 8 | RQ4 context | goals, xG by match phase | H | Diverging heatmap: blue = for, red = against | Season totals | ✅ |
| 39 | Match dominance (`dominance_scatter`) | 8 | Team performance | xG for/against per match | H | Points below the diagonal = out-created opponent; size = goal margin | — | ✅ |
| 40 | Shot-quality distribution (`xg_distribution`) | 8 | Team performance | shot xG | H | Overlaid histograms for/against with conversion notes | xG is a model output | ✅ |
| 41 | Team style fingerprint (`team_style_radar`) | 8 | RQ3 | team-match averages | H | Percentile among the dataset's teams; PPDA and xG against inverted | Opponents measured only vs focus team | ✅ |
| 42 | Pass-direction rose (`pass_direction_rose`) | 9 | Player profile | pass start/end | H | 16 sectors, forward = up; colour = completion % | Direction from coordinates | ✅ |
| 43 | Substitution timing by team (`subs_team_band_heatmap`) | 12 | RQ4 | timing band per team | H | Share of each team's subs per band, sorted by median minute | 1-2 matches per opponent | ✅ |
| 44 | **One-page presentation dashboard** (`reporting.write_dashboard_html`) | 16 | Presentation / demo | 9 key figures | H, D, section links | `outputs/dashboard.html` — opens in any browser | Needs internet for Plotly JS (CDN) | ✅ |

Total figures in the executed default notebook: **57**.

Removed / not implemented by design: xT, packing, PPDA-on-tracking and running-distance charts — the event data do
not contain the observations they require. 360 freeze-frame charts are possible (`include_360=True`) but are not
part of the core analysis.
