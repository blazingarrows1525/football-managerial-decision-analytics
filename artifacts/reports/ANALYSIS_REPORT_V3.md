# Analysis Report (V3) — Football Managerial Decision Analytics

> Generated 2026-11-11 11:29 UTC by `scripts/build_reports.py`. Every number below is computed from the data loaded in that run; chart IDs refer to `docs/VISUALIZATION_CATALOGUE.md`.

## 1. Executive summary

Bayer Leverkusen played 34 analysed matches (28 wins, 6 draws, 0 losses): 90 points against 74.8 shot-based expected points, 89 goals from 72.7 xG, 24 conceded from 27.8 xG against. The findings are descriptive associations in one team-season and are presented with their uncertainty.

## 2. Research question and scope

How can event, lineup and match-state data be turned into transparent evidence that supports starting-XI selection, role fit, tactical interpretation, substitution choices and the review of observable managerial decisions?

- **Data.** Data: StatsBomb Open Data (https://github.com/hudl/open-data), provided by StatsBomb / Hudl. Used for educational, non-commercial research.
- **Scope.** 1. Bundesliga 2023/2024; 34 matches (19 Aug 2023 – 18 May 2024); 137,765 events; 460 players in match-day squads; 18 teams.
- **Sample caveat.** Every analysed match involves Bayer Leverkusen; opponents appear twice (home and away).

## 3. Data quality

- Domain rules passed: 16/16; table contracts: 14/14.
- Raw files: 70 (120.05 MB), each with a SHA-256 hash in the manifest.
- Missing values are structural (qualifiers exist only for their event type); nothing is imputed.
- One published 360 file was found whose frame identifiers do not match its event file; 360 frames are optional and are shown only when they can be joined to events.

## 4. Team performance

| indicator | value |
| --- | --- |
| Points per match | 2.65 |
| xG difference per match | +1.32 |
| Possession proxy (pass share) | 61.7% |
| Field tilt | 67.6% |
| Pass completion | 87.6% |
| PPDA (median) | 15.4 |
| Top-three share of xG + xA | 40% |


## 5. Statistical inference

Spearman correlation of 11 match variables with goal difference (n = 34 matches, 2,000 bootstrap resamples, Benjamini–Hochberg):

| variable | n | pearson_r | spearman_rho | rho_ci_low | rho_ci_high | kendall_tau | spearman_p | spearman_q_BH |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| xg_against | 34 | -0.445 | -0.428 | -0.722 | -0.054 | -0.341 | 0.012 | 0.093 |
| shots_against | 34 | -0.385 | -0.396 | -0.678 | -0.062 | -0.311 | 0.020 | 0.093 |
| xg | 34 | 0.480 | 0.374 | -0.032 | 0.655 | 0.257 | 0.029 | 0.093 |
| pass_completion_pct | 34 | 0.333 | 0.365 | 0.011 | 0.652 | 0.269 | 0.034 | 0.093 |
| ppda | 34 | 0.290 | 0.233 | -0.141 | 0.577 | 0.173 | 0.184 | 0.405 |
| possession_proxy_pct | 34 | 0.069 | 0.120 | -0.234 | 0.492 | 0.094 | 0.499 | 0.900 |
| set_piece_shots | 34 | -0.077 | -0.069 | -0.416 | 0.276 | -0.060 | 0.699 | 0.900 |
| shots | 34 | 0.030 | 0.065 | -0.305 | 0.427 | 0.053 | 0.714 | 0.900 |
| progressive_passes | 34 | -0.131 | -0.060 | -0.420 | 0.338 | -0.024 | 0.737 | 0.900 |
| pressures | 34 | 0.086 | 0.007 | -0.386 | 0.369 | -0.036 | 0.969 | 1.000 |
| field_tilt_pct | 34 | -0.049 | 0.000 | -0.358 | 0.375 | 0.006 | 1.000 | 1.000 |


0 of 11 variables have q < 0.05. With n = 34, only |r| of roughly 0.46 or more is detectable with 80% power (chart J-214).

Group comparisons (Mann–Whitney U, Cliff's δ, bootstrap CI of the mean difference):

| comparison | n_a | n_b | mean_a | mean_b | mean_diff | diff_ci_low | diff_ci_high | p_value | effect_size | magnitude |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| home vs away | 17 | 17 | 1.599 | 1.041 | 0.558 | -0.178 | 1.228 | 0.098 | 0.336 | medium |
| first half of season vs second half | 17 | 17 | 1.254 | 1.387 | -0.133 | -0.915 | 0.632 | 0.731 | -0.073 | negligible |
| Bayer Leverkusen shot xG vs opponent shot xG | 623 | 293 | 0.117 | 0.095 | 0.022 | 0.003 | 0.040 | 0.079 | 0.072 | negligible |


## 6. Models and unsupervised structure

Target: start selection (does a match-day squad member start?). 660 rows from 33 matches; expanding-window cross-validation split by match.

| model | cv_f1 | cv_roc_auc |
| --- | --- | --- |
| Baseline: started previous match | 0.775 |  |
| Gradient boosting | 0.782 | 0.816 |
| Logistic regression | 0.811 | 0.838 |
| Random forest | 0.789 | 0.829 |


Best on the chronological hold-out: Logistic regression (ROC-AUC 0.775, Brier 0.197). Match-result, goals, injury and market-value models are **not** fitted: the data do not support them (see the Model Evaluation page).

Player profiles: PC1 35%, PC2 17% of variance (70 players, 6 components for 80%). Clustering: silhouette-best k = 2 (0.318), BIC prefers k = 9, DBSCAN finds 1 dense group(s) and 3 outlying players — profiles form a continuum.

Expected Threat (project-computed): 16x12 grid fitted on 71,583 passes and carries and 916 shots; value iteration converged in 79 iterations; maximum cell value 0.293. In-sample and descriptive.

## 7. Decision support

- **Starting XI.** The pre-match shortlist shares 77.7% of the actual XI on average over 33 matches. This is similarity to the manager's choice, not evidence that either was better.
- **Substitutions.** The heuristic's top three contains the player who actually came on in 82.5% of 137 non-injury substitutions (a random pick of three from the bench: about 43%).
- Both tools are transparent heuristics with stated weights and constraints; no injury or fitness information exists in the source, so availability must be supplied by the analyst.

## 8. Managerial evidence cards

### 1. Results against chance quality

- **Finding.** Results ran ahead of shot-based expectation by 15.2 points.
- **Evidence.** 90 points vs 74.8 expected points; 89 goals from 72.7 xG (xG difference +1.32 per match).
- **Scope.** Bayer Leverkusen, 34 matches, 1. Bundesliga 2023/2024 (19 Aug 2023 – 18 May 2024)
- **Supporting chart.** `L-262`
- **Managerial relevance.** Anchor performance reviews on chances created and conceded rather than on results alone.
- **What the evidence cannot tell us.** Expected points are a simulation from StatsBomb xG; they ignore game state and assume shots are independent.
- **Suggested next investigation.** Recompute over further seasons to see how much of the gap persists.

### 2. Concentration of chance creation

- **Finding.** Three players account for 40% of the squad's xG + xA.
- **Evidence.** Top three: Victor Boniface, Florian Wirtz, Álex Grimaldo; Gini coefficient of xG + xA across 22 contributors = 0.52.
- **Scope.** Bayer Leverkusen, 34 matches, 1. Bundesliga 2023/2024 (19 Aug 2023 – 18 May 2024)
- **Supporting chart.** `B-029`
- **Managerial relevance.** Cover and minutes management for the main creators matter more than for other roles.
- **What the evidence cannot tell us.** xA credits the passer of a shot assist only; off-ball contribution is not in event data.
- **Suggested next investigation.** Check how output changes in matches the top creators did not start.

### 3. Structure of the passing game

- **Finding.** Granit Xhaka is both the main hub and the main bridge of the pass network.
- **Evidence.** Mean PageRank 0.140 (Granit Xhaka); mean betweenness 0.211 (Granit Xhaka); averaged over 32 match networks.
- **Scope.** Bayer Leverkusen, 34 matches, 1. Bundesliga 2023/2024 (19 Aug 2023 – 18 May 2024)
- **Supporting chart.** `F-139`
- **Managerial relevance.** A build-up plan that depends on one link is exposed when he is pressed or unavailable.
- **What the evidence cannot tell us.** Networks use completed passes before the first substitution; centrality describes the recorded graph, not player quality.
- **Suggested next investigation.** Compare the network in matches where the hub was marked or absent.

### 4. Selection continuity

- **Finding.** A stable core with rotation at the margins: 7 players started at least three quarters of the matches.
- **Evidence.** Mean 2.2 starting-XI changes between consecutive analysed matches (median 2); 22 players started at least once.
- **Scope.** Bayer Leverkusen, 34 matches, 1. Bundesliga 2023/2024 (19 Aug 2023 – 18 May 2024)
- **Supporting chart.** `D-106`
- **Managerial relevance.** Decision support adds most in the two or three slots that actually rotate.
- **What the evidence cannot tell us.** Cup and European fixtures between league matches are not in the data, so rotation across all competitions is understated.
- **Suggested next investigation.** Add the other competitions' lineups to measure true rotation.

### 5. Substitution timing and score state

- **Finding.** Changes are made late and mostly from in front: median minute 79, 79% while leading.
- **Evidence.** 142 substitutions, 4.18 per match; 77% like-for-like by role.
- **Scope.** Bayer Leverkusen, 34 matches, 1. Bundesliga 2023/2024 (19 Aug 2023 – 18 May 2024)
- **Supporting chart.** `H-171`
- **Managerial relevance.** Pre-planned, role-compatible replacement pairs fit the observed pattern.
- **What the evidence cannot tell us.** Score state is driven by team strength: a team that usually leads makes most changes while leading whatever its intent.
- **Suggested next investigation.** Compare with matches of similar score state from other teams once more data are loaded.

### 6. Home and away performance

- **Finding.** A home edge in xG difference is suggestive but not established in this sample.
- **Evidence.** Home minus away xG difference +0.56 (95% CI -0.18 to +1.23); Cliff's δ 0.34 (medium); Mann–Whitney p = 0.098; n = 17 vs 17.
- **Scope.** Bayer Leverkusen, 34 matches, 1. Bundesliga 2023/2024 (19 Aug 2023 – 18 May 2024)
- **Supporting chart.** `J-211`
- **Managerial relevance.** Not strong enough to justify a different game model by venue.
- **What the evidence cannot tell us.** 17 matches per venue; opponents differ between the home and away sets.
- **Suggested next investigation.** Re-test with additional seasons.

### 7. What moves with goal difference

- **Finding.** 0 of 11 match variables remain associated with goal difference after false-discovery control; the strongest is xg against.
- **Evidence.** Spearman ρ = -0.43 (95% CI -0.72 to -0.05), q = 0.093; n = 34 matches.
- **Scope.** Bayer Leverkusen, 34 matches, 1. Bundesliga 2023/2024 (19 Aug 2023 – 18 May 2024)
- **Supporting chart.** `J-202`
- **Managerial relevance.** Chance quality for and against is the most informative match-level lens available here.
- **What the evidence cannot tell us.** One team-season: low power, and an association is not a causal effect.
- **Suggested next investigation.** Pool several seasons to raise power before drawing tactical conclusions.

### 8. Player profiles form a continuum

- **Finding.** Statistical profiles do not separate into distinct player types.
- **Evidence.** Best silhouette 0.32 at k = 2; the mixture-model BIC prefers k = 9; DBSCAN finds 1 dense group(s) with 3 outlying players; n = 70.
- **Scope.** 70 outfield players above the minutes threshold in the dataset
- **Supporting chart.** `K-240`
- **Managerial relevance.** Use role-specific metric profiles for squad planning rather than cluster labels.
- **What the evidence cannot tell us.** Opponent players are observed only in their matches against the focus team.
- **Suggested next investigation.** Repeat on full-league data, where every team has a full season of evidence.

### 9. How predictable is selection

- **Finding.** Past selection explains most starts; models add little over the simple rule.
- **Evidence.** Time-ordered cross-validation F1: Logistic regression 0.811 vs 0.775 for 'started the previous match'; hold-out ROC-AUC 0.775; 660 rows from 33 matches.
- **Scope.** Bayer Leverkusen, 34 matches, 1. Bundesliga 2023/2024 (19 Aug 2023 – 18 May 2024)
- **Supporting chart.** `K-221`
- **Managerial relevance.** Selection follows continuity; rotation decisions hinge on information the data lack.
- **What the evidence cannot tell us.** No fitness, injury, training or opponent-specific information exists in the source.
- **Suggested next investigation.** Add availability data before attempting to model rotation.

## 9. Visualization inventory

- implemented and available: **273**
- implemented but unavailable: **0**
- not implemented (reason stated): **5**
- failed validation: **0**

## 10. Limitations

Team-centric sample; league matches only; no injury, fitness, tracking, age or market data; xG, xPts and xT are model outputs; 34 matches limit statistical power; every relationship is an association, not a causal effect; heuristic scores are 'best' only under their stated weights.

## 11. Reproducibility

| component | version |
| --- | --- |
| python | 3.10.11 |
| platform | Windows-10-10.0.26300-SP0 |
| pandas | 2.1.4 |
| numpy | 1.26.2 |
| scipy | 1.15.3 |
| sklearn | 1.3.2 |
| plotly | 6.6.0 |
| matplotlib | 3.10.8 |
| seaborn | 0.13.2 |
| networkx | 3.4.2 |
| streamlit | 1.55.0 |
| mplsoccer | 1.8.1 |
| shap | 0.49.1 |
| pyarrow | 23.0.1 |
| nbconvert | 7.17.1 |
| pytest | 9.1.1 |


## 12. Attribution

Data: StatsBomb Open Data (https://github.com/hudl/open-data), provided by StatsBomb / Hudl. Used for educational, non-commercial research. State StatsBomb as the data source and use the StatsBomb logo (Media Pack) when publishing analysis based on the data. Terms: https://github.com/hudl/open-data/blob/master/LICENSE.pdf
