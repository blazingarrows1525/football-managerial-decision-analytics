# Viva Preparation, Presentation Outline and Demo Sequence

Numbers below come from the executed default run (StatsBomb 1. Bundesliga 2023/24). Re-check notebook §17
("Numbers to quote") if you change the configuration.

## A. Likely questions with answer prompts

1. **What is the problem statement?** Event and lineup data are rich but hard to use consistently for XI and
   substitution decisions; the project makes them auditable, role-aware, time-aware and interactive, with limits shown.
2. **Why is football analytics suitable for Big Data Visualization?** High-volume, high-dimensional, spatio-temporal
   event streams (≈4,000 events per match, x/y coordinates, nested qualifiers) that only become interpretable through
   aggregation and interactive visuals. Honest scale: 137,765 events, 120 MB raw — a scalable pipeline case study,
   not "massive" data.
3. **Raw event data vs aggregated match statistics?** Events are time-stamped on-ball actions with location, player
   and qualifiers; aggregates (shots, possession) are sums over events. Events allow per-90, spatial, match-state and
   before/after analysis that aggregates cannot.
4. **Which dataset and why?** StatsBomb Open Data (public, documented, lineups with bench, managers, xG). Bundesliga
   2023/24: 34 matches with manager metadata covering one manager's whole season.
5. **How many competitions, matches, events, teams, players?** 1 competition-season, 34 matches, 137,765 events,
   18 teams, 460 players in matchday squads (377 appeared), 301 substitutions, 113 goals.
6. **How did you collect the data?** HTTPS download of raw JSON from the repository via `DataStore`: timeout,
   retries with back-off, cache, SHA-256 manifest with UTC timestamps; raw files never modified.
7. **What does a lineup record contain?** Per team: player id/name, jersey, country, cards and position spells with
   start/end reasons; unused substitutes have no positions — that is how the bench is identified.
8. **How did you calculate minutes?** From the event stream: Starting XI → substitutions → red/second-yellow cards,
   converted to elapsed playing time per period (Half Start/End), so stoppage time counts and first-half stoppage
   never overlaps the second half. Treatment breaks (Player Off/On) ignored. Lineup spells were rejected because they
   are not chronological (example: a second yellow at 47:30 of the first half listed after a 45:00 second-half entry).
9. **Per-90 and why?** count ÷ minutes × 90 — compares players with different playing time; NaN for zero minutes;
   minimum-minutes threshold with a sensitivity table (84 eligible at 180 min, 17 at 900).
10. **Why within position groups?** A centre-back's interceptions and a forward's xG are not comparable; percentiles
    within role (≥8 players) or role family, labelled with the group size.
11. **What is xG and where did it come from?** Probability a shot is scored, from StatsBomb's model
    (`shot.statsbomb_xg`); we never compute or alter it.
12. **How does the XI recommendation work?** Per player-slot score = Σ weights × (role fit, recent form, sample
    reliability, workload suitability, continuity) × position compatibility; Hungarian assignment maximises the total.
13. **What constraints?** 11 distinct players, one goalkeeper, each slot filled once, compatibility > 0, unavailable
    excluded, players without pre-decision data excluded, empty slot + warning if depth is insufficient — all unit-tested.
14. **How does the substitution recommendation use score state?** State from the team's perspective just before the
    decision sets the intent (trailing → attack metrics, leading → protect, drawing → balance); user can override.
15. **How do you know who was on the pitch at a minute?** Spells from the event timeline; `on_pitch_at` / `bench_at`;
    a replaced player cannot return (tested).
16. **Substitution timing profile?** Distribution of substitution minutes across configurable bands and by score
    state. Alonso: 4.18 subs/match, median minute 79, first-sub median 63.5'.
17. **Can the system determine leadership skills?** No — event data contain no valid measurement instrument; we report
    observable decision patterns only.
18. **Correlation vs causation in substitution impact?** Pre/post windows are associations: 71 % of decision windows
    contain a goal, red card or another own decision, and opponents also changed in most; score effects and regression
    to the mean remain.
19. **How did you avoid leakage?** Every decision uses only earlier matches (`asof` filters) or events before the
    decision minute; model features audited; chronological split.
20. **How did you evaluate?** XI: descriptive agreement with actual XIs (77.7 % mean). Substitutions: actual incoming in
    top-3 82 % vs 43 % random. Start model: F1 0.745 vs baseline 0.711, ROC-AUC 0.775, Brier 0.197.
21. **Major data limitations?** One club's season (opponents 1-2 matches), no cup fixtures, no injuries/fitness/
    tracking, user-configured substitution rules, xG is a model.
22. **How would you scale?** Raw files are independent per match → parallel parsing (Spark/Dask `flatMap`), Parquet
    partitioned by competition/season/match, `groupBy` aggregations; switch `MATCH_LIMIT=None` across many seasons.
23. **Why Plotly and interactive filtering?** Hover provenance (minutes, percentile, coverage), dropdowns that survive
    HTML export, consistent theme, accessible zoom/pan; widgets for live what-if analysis.
24. **What would tracking data add?** Off-ball runs, defensive shape, pressing intensity, physical load — better
    workload proxies and role descriptors.
25. **What should a coach do with a recommendation?** Treat it as a structured second opinion: check the evidence and
    coverage, add information we lack (fitness, opponent plan), then decide.

## B. 5–7 minute presentation outline
| Time | Content | Notebook |
|---|---|---|
| 0:00-0:30 | Problem and objective; disclaimer | §0 |
| 0:30-1:15 | Dataset and collection: catalogue, manifest, 34 matches / 137,765 events / 120 MB, attribution | §3-4 |
| 1:15-2:00 | Architecture and preprocessing: minutes reconstruction, 16/16 quality checks | §5-6 |
| 2:00-3:00 | Player intelligence: leaderboard dropdown, radar, scatter; tactical: shot map, pass network | §9-10 |
| 3:00-4:00 | Starting XI: pitch, score decomposition, omissions, vs actual XI, rotation what-if | §11 |
| 4:00-5:00 | Substitution scenario: live context, intent, ranked candidates, recommendation card | §12 |
| 5:00-5:30 | Manager decision patterns: timing heatmap, rotation | §13 |
| 5:30-6:00 | Findings, limitations, causality note, conclusion | §15, §17 |

## C. Live-demo sequence (works offline once cached)
1. Open the executed notebook (outputs already present) — no network required to show results.
2. If time allows a fresh run: set `OFFLINE = True` (cache in `data/raw/statsbomb/`), *Run all* (~1 min).
3. Leaderboard → switch metric in the dropdown; scatter → change x/y axes; hover a point (minutes, percentile).
4. Player selector widget → choose another Leverkusen player → radar + form update.
5. XI widget → change formation to 4-2-3-1, mark two players unavailable → pitch and warnings update.
6. Substitution widget → pick a match, slide minute to 70, set intent "attack" → recommendation updates.
7. Fallback if anything fails: `python scripts/execute_notebook.py --mode DEMO_SYNTHETIC --out notebooks/demo_synthetic_run.ipynb`
   (clearly labelled synthetic) or open `outputs/figures/*.html`.
