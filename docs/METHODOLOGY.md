# Methodology

## 1. Question and stance

*How can real football event, lineup, player and match-state data be transformed into transparent and
interactive evidence to support starting-XI selection, role fit, tactical interpretation, substitution choices,
rotation analysis and the evaluation of observable managerial decisions?*

The project is decision support. It reports associations with their uncertainty, labels heuristics as
heuristics and never states that a chart proves a tactical cause or a manager's quality.

## 2. Data

StatsBomb Open Data, 1. Bundesliga 2023/24 (competition 9, season 281): the 34 published matches, all
involving Bayer Leverkusen. Details, hashes and licence terms: `docs/DATA_PROVENANCE.md`. Field-level
definitions: `docs/DATA_DICTIONARY.md`.

**Unit of analysis.** Matches for team questions (n = 34), players above a minutes threshold for player
questions, squad member × match for the selection model. Events are never treated as independent observations.

**Sampling caveat.** The sample is team-centric. Opponents appear twice (home and away) and only against the focus
team, so nothing is said about the league or about other teams' seasons.

## 3. Processing

1. **Acquisition.** Files are downloaded once from the official repository, cached unchanged and recorded with
   URL, size, SHA-256 and write time. One match is parsed at a time to keep memory bounded.
2. **Parsing.** Nested JSON becomes flat canonical tables. No raw row is deleted.
3. **Time.** A period-aware elapsed-minute clock is built from Half Start / Half End events (stoppage time
   keeps counting).
4. **Minutes.** On-pitch spells are reconstructed from Starting XI, Substitution and sending-off events. The
   lineup file's position spells are not chronological and are not used for this.
5. **Validation.** Sixteen domain rules and fourteen table contracts (see chapter 01).
6. **Features.** Event flags → player-match → player-season (per 90, role percentiles) and team-match tables.
7. **Coordinates.** StatsBomb's 120 × 80 frame, origin top-left, every team attacking left to right in both
   halves. No per-half flip is applied.

## 4. Metric conventions

- **Per 90** = value / minutes × 90; null for zero minutes; players below the minimum-minutes threshold are
  flagged "low data coverage" and are excluded from every benchmark pool.
- **Percentiles** are within the player's role group; when a role has fewer eligible players than the minimum
  group size the role family is used and the fallback is flagged.
- **Team rates** are weighted (sum of numerators / sum of denominators) unless a chart says "mean per match".
- **Project definitions** (progressive pass, progressive carry, possession proxy, field tilt, PPDA, role fit,
  scores, xT) are spelled out in the data dictionary and in chart subtitles. They are not provider fields.

## 5. Statistical methods

| Need | Method | Reported with |
|---|---|---|
| Association | Spearman ρ (default), Pearson r, Kendall τ | pairwise n, bootstrap 95% CI, Benjamini–Hochberg q |
| Two groups | Mann–Whitney U, permutation test | Cliff's δ with magnitude label, bootstrap CI of the mean difference |
| Several groups | Kruskal–Wallis with pairwise Mann–Whitney | ε², BH-adjusted q |
| Uncertainty of a rate | bootstrap over matches | 95% percentile interval |
| Proportions in small samples | Wilson interval, beta-binomial shrinkage | interval and shrunk value |
| Sample adequacy | power of a correlation test (Fisher z) | minimum detectable \|r\| at 80% power |
| Structure | PCA; K-Means, Ward, Gaussian mixture, DBSCAN | silhouette, Davies–Bouldin, BIC, ARI, bootstrap stability |

Rank-based methods are the default because the per-90 metrics are right-skewed. Seeds are explicit.

## 6. Decision-support methods

**Starting XI.** For each candidate and formation slot:
`(w₁·role fit + w₂·recent form + w₃·evidence volume + w₄·minutes-based exposure + w₅·continuity) × position
compatibility`, components on 0–100, default weights 0.40 / 0.20 / 0.15 / 0.15 / 0.10. The Hungarian algorithm
assigns players to slots under hard constraints (eleven distinct players, one goalkeeper, eligibility, squad
pool). Only information dated before the match is used. "Best" means best under these weights and constraints.

**Substitutions.** At a chosen minute the context is rebuilt from the chronology (score, manpower, changes
and windows used, who is on the pitch, who is on the bench and unused). Outgoing players are ranked by minutes,
a booking and involvement relative to their own baseline; incoming players by role compatibility, fit to the
tactical intent (trailing → attack, leading → protect, level → balance), recent form and evidence volume.
Shortlists are counterfactual simulations.

**Backtests.** The shortlist is compared with what happened (share of the actual XI also shortlisted; whether
the actual substitute was in the top three). Agreement is similarity to observed decisions, not quality.

**Before/after windows** around substitutions are descriptive and flagged as contaminated when a goal, a red
card or another change falls inside the window.

## 7. Modelling

One supervised target passes the sample gate (≥ 300 rows and ≥ 15 matches): **start selection**. Features use
only earlier matches (leakage audit in chapter 05). Evaluation: expanding-window cross-validation split by
match, a final chronological hold-out, a naive baseline ("started the previous match"), a top-eleven decision
rule, discrimination and calibration metrics, permutation importance, partial dependence and SHAP when
installed. Match results, goals, injuries, fitness and market value are not modelled: the data do not support
them.

## 8. Expected Threat

A 16 × 12 grid; moves are passes and carries; failed passes pass on no value; shot value is the mean StatsBomb
xG per cell; value iteration to a fixed point. Fitted in-sample on the analysed matches and checked for
convergence, bounds and monotonicity towards goal. A derived project value, never presented as a provider
field.

## 9. Visualization

Every chart answers one question, states its sample and scope in the subtitle, carries the source line and has
an empty state. Large maps draw a seeded sample and say so. Charts that would need absent data (Voronoi,
pitch control, forecasts, targets) are listed as not implemented with the reason. Full list:
`docs/VISUALIZATION_CATALOGUE.md`.

## 10. Limits of inference

One team-season; 34 matches; opponents not randomised; no injury, fitness, tracking, age or market data; xG,
expected points and xT are model outputs. With n = 34 a correlation test has 80% power only for |r| ≥ 0.46.
Nothing in this project is a causal estimate.
