# Football Managerial Decision Intelligence: Interactive Player Performance, Starting XI Optimisation, and Substitution Analysis Using Match Data

## 1. Title page
| | |
|---|---|
| Student name | `[enter]` |
| Registration number | `[enter]` |
| Course / programme | `[enter]` — Big Data Visualization (mini-project) |
| Faculty / guide | `[enter]` |
| Institution | `[enter]` |
| Submission date | `[enter]` |

All results in this report come from the executed notebook
`notebooks/Football_Managerial_Decision_Analytics.ipynb` on real StatsBomb Open Data (data mode `REAL_OPEN_DATA`).

## 2. Abstract
Football clubs make two recurring selection decisions — the starting XI and in-match substitutions — under time
pressure and incomplete information. This project builds a reproducible pipeline that turns StatsBomb open event
data (1. Bundesliga 2023/24: 34 matches, 137,765 events, 460 players, 301 substitutions) into audited tables,
role-aware player metrics, interactive Plotly visual analytics and two transparent decision-support modules. Minutes
are reconstructed from the event timeline; 16 domain-rule checks pass, including reconciliation of goal events with
all 34 published scores. A Hungarian-assignment XI optimiser, using only pre-match information, agrees with the
coach's actual XI on 77.7 % of players on average across 33 matches. A substitution heuristic restricted to
pre-decision information places the actual incoming player in its top-3 for 82 % of 137 non-injury substitutions
(random top-3 ≈ 43 %). A gated, leakage-audited logistic regression of starting selection reaches F1 0.745
against 0.711 for a "started previous match" baseline (ROC-AUC 0.775). Observable managerial patterns are
profiled without personality scores, and before/after substitution windows are presented strictly as associations.

## 3. Introduction and background
Event data record every on-ball action with time, location, player and qualifiers (StatsBomb, 2024). Compared with
aggregated match statistics, they allow per-90 normalisation, role comparisons, spatial views and reconstruction
of the match state at any moment. Prior work has modelled substitution timing with Markov models (Hirotsu & Wright,
2002) and proposed empirical substitution decision rules (Myers, 2012). Lineup selection can be cast as an
assignment problem solved exactly by the Hungarian method (Kuhn, 1955). This project combines these ideas in an
explainable, visual, reproducible notebook.

## 4. Problem statement
Raw football event and lineup data are difficult to interpret consistently for lineup and substitution planning:
they are nested, team-perspective dependent, time-ordered, and full of structural blanks. Naive aggregation leaks
future information, compares players across incompatible roles, and invites causal over-claims.

## 5. Aim and objectives
**Aim:** a reproducible, interactive football decision-intelligence notebook.
Objectives: (1) collect real data with provenance; (2) validate and normalise it; (3) engineer documented,
role-normalised features; (4) visualise players, teams, tactics, substitutions and managers interactively;
(5) build constrained, explainable XI and substitution decision support using pre-decision information only;
(6) evaluate descriptively and, where justified, with a time-aware model; (7) document limits.

## 6. Research questions
Main: *How can historical football match events, player performance indicators, lineup records and match-state
context be transformed into interactive visual analytics that support evidence-based starting-lineup and
substitution decisions?*
RQ1 role-distinguishing attributes · RQ2 per-90 and role normalisation · RQ3 formations and outcomes ·
RQ4 substitution timing by score state, competition and team · RQ5 substitute matching using pre-decision evidence ·
RQ6 rotation vs minutes, rest and continuity · RQ7 observable manager decision patterns · RQ8 limits to causal
interpretation.

## 7. Scope and assumptions
In scope: one competition-season selected from the live StatsBomb catalogue (default Bundesliga 2023/24), player,
team, formation, XI, substitution and manager-proxy analysis. Assumptions: StatsBomb events are the ground truth
for actions; matchday squads approximate availability; substitution rules are user-configured (default: five
substitutes in three in-play windows, IFAB Law 3 option); weights are analyst choices exposed for change.
Out of scope: betting, fantasy, valuation, medical or injury decisions.

## 8. Dataset sources and collection methodology
Primary source: StatsBomb Open Data (https://github.com/statsbomb/open-data). The catalogue
(`competitions.json`, 80 competition-seasons) was read first; competition 9 / season 281 was selected because its
34 matches carry manager metadata and cover a full league season of one club. For each match the event and lineup
files were downloaded over HTTPS by `ingestion.DataStore` (60 s timeout, four retries with exponential back-off,
404 handled), cached unchanged in `data/raw/statsbomb/`, and logged in a manifest with URL, UTC timestamp, bytes,
SHA-256 and status (`outputs/exports/source_manifest.csv`). Optional sources (API-Football, Metrica, football-data.co.uk)
were assessed and not needed; scraping of sites with restrictive terms was rejected. A `DEMO_SYNTHETIC` mode generates
a clearly labelled fictional league for offline testing only.

## 9. Dataset size, coverage and data dictionary summary
| Measure | Value |
|---|---|
| Matches (published = analysed) | 34 / 34 |
| Date range | 19 Aug 2023 – 18 May 2024 |
| Events parsed | 137,765 |
| Matchday-squad rows | 1,353 (748 starters, 301 used substitutes, 304 unused) |
| Players / teams | 460 / 18 |
| Substitutions / goals | 301 (17 injury-coded) / 113 |
| Raw files / size | 70 JSON / 120.05 MB |
| Manager metadata | 34/34 matches |
| Attendance, weather, injuries | not provided — not analysed |

Full field-level definitions, types and measured missingness: `reports/DATA_DICTIONARY.md`; provenance and
coverage: `reports/DATASET_CARD.md` (both generated from the run).

## 10. Data preprocessing and quality checks
* **Flattening:** schema-aware accessors tolerate missing keys; malformed records are logged and excluded, never
  crash the pipeline.
* **Time:** StatsBomb's continuous clock restarts the second half at 45:00 while first-half stoppage continues to
  47-52'. Elapsed playing time is computed per period from Half Start/End events and accumulated, so the two never
  overlap.
* **Minutes:** the lineup file's position spells were found to be non-chronological (e.g. a first-half second yellow
  at 47:30 listed after a 45:00 second-half entry), so on-pitch spells are rebuilt from Starting XI → Substitution →
  sending-off events; treatment breaks are ignored; unknown timing is flagged, never assumed.
* **Checks (16/16 pass):** duplicate events/squad rows; coordinates within 120×80; xG in [0,1]; non-negative minutes;
  ordered event index and clock; exactly 11 starters and one goalkeeper per team-match; no duplicate selection;
  complete substitution records; no overlapping spells; event goals reconcile with the published score in all 34
  matches; every event player resolves to the matchday squad; no unknown minutes. A quality-action log records any
  flagged/excluded record (none on this run).

## 11. Analytical methodology
Pipeline: provenance → validation → features → analysis → decision support → evaluation
(`src/football_analytics/`). Pandas is used because the volume (≈ 10⁵ events, 120 MB) is processed in under 10 s;
the design is per-match independent and maps to Spark/Dask (`flatMap` over files, `groupBy` aggregations, Parquet
partitioned by competition/season/match) when many seasons are added. Spark was not added as decoration.

## 12. Feature engineering and metric definitions
45 metrics with numerator, denominator, unit and source fields (data dictionary). Highlights: per-90 = count ÷
minutes × 90 (NaN for zero minutes); pass completion; long-pass completion (≥ 30 yards); key passes, assists and
xA (xG of assisted shots, via `pass.assisted_shot_id`); **project-defined** progressive passes (completed open play,
starting outside the defending 40 %, ending ≥ 25 % closer to goal) and carries; box/final-third touches; tackles won,
interceptions, recoveries, pressures, aerials; goalkeeper saves/claims. Team metrics: possession proxy (pass share),
field tilt (final-third action share) and a labelled PPDA approximation. Percentiles are computed within role
(≥ 8 eligible players) or role family; 234 player rows are benchmarked at role level and 143 at role-family level.
Eligibility: 84 of 377 players at 180 minutes, 17 at 900 (sensitivity table and chart, notebook §7). Form: role
composite over the last five appearances. Workload proxies: minutes in previous 7/14/28 days, rest days, consecutive
starts — dataset matches only.

## 13. Visualization methodology and chart justification
57 Plotly figures (including four composite dashboards and a one-page HTML presentation dashboard) in one editorial theme (neutral background, navy/teal/amber/red palette, sequential and diverging
scales where ordered). Each chart answers a research question and checks its inputs (empty-state figures instead of
errors). Interaction: hover provenance (minutes, percentile, coverage), in-chart dropdowns (survive HTML export),
ipywidgets for player, formation/availability and substitution scenarios. Pitch charts use the StatsBomb 120×80
frame with standard markings and equal aspect. Catalogue: `reports/VISUALIZATION_CATALOG.md`.

## 14. Starting XI decision-support methodology
For a selected match, the candidate pool is the announced matchday squad and all statistics use only earlier
matches. Each (player, slot) score = Σ wᵢ·componentᵢ (+2 side tie-breaker) × compatibility(primary role, slot role)
with components on 0-100: role fit (0.40), recent form (0.20), sample reliability (0.15), workload suitability
(0.15), lineup continuity (0.10). The Hungarian algorithm (`scipy.optimize.linear_sum_assignment`) returns the exact
maximum-total assignment. Constraints: 11 distinct players, one goalkeeper, compatibility > 0, unavailable players
excluded, players without pre-decision data excluded, empty slot + warning on insufficient depth. Outputs: pitch view,
score decomposition, omission reasons, squad depth, formation comparison, rotation alternative and what-if pins.

## 15. Substitution decision-support methodology
At decision minute *t*, the context contains only events with elapsed time < *t*: team-perspective score, numerical
state, substitutions and windows remaining (user-configured rules), live team indicators, on-pitch players and the
eligible bench (matchday squad minus anyone who has already appeared). Intent rule: trailing → attack, leading →
protect, drawing → balance (overridable). Outgoing score = 0.35 minutes played + 0.30 low involvement (in-match
role-action rate vs the player's own pre-match per-90) + 0.15 booking + 0.20 intent mismatch. Incoming score =
0.35 role compatibility + 0.35 intent-metric percentile + 0.15 recent form + 0.15 sample reliability. Output: off/on
pair, decision window, objective, evidence, alternatives, risks, rule status, coverage, injury status "unknown", and
the human-decision note.

## 16. Managerial decision-pattern methodology
Per manager-team spell: formations used and diversity (normalised entropy), in-match formation changes, lineup changes
between consecutive dataset matches, substitutions per match, median (first) substitution minute, early/late shares,
multi-change windows, score-state shares, like-for-like share, response time after conceding. Comparisons require
≥ 10 matches; smaller samples are labelled descriptive and pooled only as a reference.

## 17. Results and observations (executed real-data run)
**Team context.** Leverkusen: 28 W, 6 D, 0 L, 90 points, goals 89-24, xG 72.7-27.8, possession proxy 61.7 %, field
tilt 67.6 %. A shot-based expected-points model (each match simulated 5,000 times from shot xG) gives 74.8 xPts,
so the team out-performed its chance quality by about 15 points — attributable to finishing, goalkeeping,
game-state management and chance, not to luck alone. 57 % of its pressures were applied in the opponent half
(pressure heatmap, notebook §10). Starting formations: 3-4-2-1 in 25 matches (2.84 points per match, xG 2.05 for / 0.74 against), 3-4-3
in 8 (2.00 ppm), 3-4-1-2 once.

**RQ1.** Median per-90 profiles differ sharply by role family: forwards have the highest median xG/90 (0.32),
defenders the highest interceptions/90 (1.4), midfielders the highest pass completion (84.8 %).

**RQ2.** Leaderboards depend on the minutes threshold: at 180 min, 84 players are eligible; at 900 only 17. Among
eligible players the top progressive passers per 90 are Wirtz (7.15), Xhaka (4.89) and Palacios (4.62); top xG/90 is
Boniface (0.87).

**RQ3.** The 3-4-3 starts coincided with fewer points per match than 3-4-2-1 but higher xG for (2.44 vs 2.05) and
against (1.10 vs 0.74) — descriptive only, as opponent and availability drive formation choice.

**RQ4.** Leverkusen's median substitution came at 79' with 79 % made while leading; opponents (pooled) substituted
earlier (median 72') and 70 % of their changes came while trailing.

**RQ5.** Re-running the substitution heuristic one second before each of 137 non-injury Leverkusen substitutions, the
actual incoming player was in the top-3 82 % of the time (random ≈ 43 % for a median bench of 7) and the actual
outgoing player in the top-3 57 % of the time.

**Starting XI.** Before each of 33 matches (pre-match data only), the optimiser's XI overlapped the actual XI on
77.7 % of players on average (median 82 %). Example (10 Mar 2024 vs Wolfsburg, 3-4-2-1): 91 % overlap; the rotation
alternative resting the three highest-load players lowered the total score by 90 points.

**RQ6.** Mean 2.2 starting-XI changes between consecutive matches. Start model (660 squad rows, 33 matches; train to
3 Mar 2024, test from 10 Mar): precision 0.745, recall 0.745, F1 0.745 vs baseline F1 0.711; ROC-AUC 0.775; Brier
0.197. Largest standardised coefficients: season minutes share (+1.36), goalkeeper (+0.92), started previous match
(+0.53).

**RQ7.** Xabi Alonso (34 matches): 4.18 substitutions per match, median first substitution 63.5', 61 % of changes at
75'+, formation diversity 0.61, 0.5 in-match formation changes per match. Compared with the pooled opposing managers
(34 matches, 21 managers, each ≤ 2 matches) his changes came later (median 79' vs 71') — a labelled reference, not
a ranking.

**RQ8.** Of 189 substitution decisions with ≥ 3 minutes on both sides (±10-minute windows), 71 % contain a goal,
sending-off or another decision by the same team, and the opponent also changed in 79 %. Median post-minus-pre
changes are small and inconsistent across states; they are reported as associations only.

## 18. Evaluation and validation
* 111 unit/integration tests pass (`python -m pytest -q`), covering parsing with missing keys, substitution
  direction, ID preservation, coordinate order, minutes for starters/subs/red cards/half-time/extra time/unknown
  timing, per-90 and zero-minute protection, role normalisation, XI constraints and determinism, substitution
  eligibility, team-perspective game state, configurable rules, validation rules and empty-state charts.
* The notebook executes top-to-bottom in a fresh kernel (51 code cells, 0 errors, ≈ 1 minute with cached data).
* XI and substitution evaluations are *descriptive agreement* with observed decisions; historical decisions are not
  treated as optimal labels (selection bias).
* The model uses a chronological split, a domain-constrained decision rule (top 11 per match) and a leakage audit.

## 19. Limitations, bias, confounding and ethical considerations
* **Team-centric sample:** the season release covers one club; opponents appear in 1-2 matches each, against the same
  strong opponent, so their per-90 values are small-sample and context-biased; benchmarks for the focus squad are
  partly internal.
* **Missing fixtures:** cup and European matches are absent, so workload and rest proxies under-state real load.
* **Missing data types:** no injuries, suspensions, training load, fitness, tracking or tactical instructions;
  injury status is always shown as unknown.
* **Model outputs as inputs:** xG is StatsBomb's model; progressive actions, possession proxy, field tilt and PPDA are
  project approximations.
* **Confounding:** formation and substitution comparisons are confounded by opponent strength, score effects, squad
  availability and time remaining; no causal identification strategy is implemented.
* **Rules:** substitution allowances are user-configured, not read from competition regulations.
* **Ethics:** player data are used for educational performance analysis only; no personal attributes beyond the
  source's football metadata; no leadership or personality claims about managers; StatsBomb attribution retained.

## 20. Conclusion
The project shows that open event data, handled with provenance, period-aware time reconstruction, role
normalisation and strict pre-decision information, can support explainable lineup and substitution analysis. The
interactive views make every recommendation traceable to definitions, weights and data coverage. The descriptive
agreement with an elite coach's choices (≈ 78 % XI overlap; 82 % top-3 substitute agreement) indicates the
features capture much of observable selection logic, while the remaining gaps point to information the data do not
contain.

## 21. Future scope
Multiple complete league seasons (e.g. StatsBomb's complete 2015/16 leagues) for independent role benchmarks; cup
fixtures for workload; licensed injury/availability feeds; 360/tracking data for off-ball and pressing metrics;
action-value models such as VAEP (Decroos et al., 2019) as additional role-fit inputs; matched-window designs for
substitution effects; manager-tenure tables; a distributed (Spark) ingestion path once the volume justifies it.

## 22. References and data attribution
* StatsBomb (Hudl). *StatsBomb Open Data* and *Open Data Specification* (repository `doc/`).
  https://github.com/statsbomb/open-data. Data used for educational, non-commercial research with attribution.
* Decroos, T., Bransen, L., Van Haaren, J., & Davis, J. (2019). Actions speak louder than goals: Valuing player
  actions in soccer. *Proceedings of KDD '19*, 1851–1861.
* Hernán, M. A., & Robins, J. M. (2020). *Causal Inference: What If*. Chapman & Hall/CRC.
* Hirotsu, N., & Wright, M. (2002). Using a Markov process model of an association football match to determine the
  optimal timing of substitution and tactical decisions. *Journal of the Operational Research Society*, 53(1), 88–96.
* IFAB. *Laws of the Game*, Law 3 — The Players (substitution provisions).
* Kuhn, H. W. (1955). The Hungarian method for the assignment problem. *Naval Research Logistics Quarterly*, 2(1-2),
  83–97.
* McKinney, W. (2010). Data structures for statistical computing in Python. *Proceedings of the 9th Python in
  Science Conference*, 56–61.
* Myers, B. R. (2012). A proposed decision rule for the timing of soccer substitutions. *Journal of Quantitative
  Analysis in Sports*, 8(1).
* Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research*, 12,
  2825–2830.
* Plotly Technologies Inc. (2015). *Collaborative data science*. https://plot.ly
* Virtanen, P., et al. (2020). SciPy 1.0: Fundamental algorithms for scientific computing in Python. *Nature
  Methods*, 17, 261–272.
