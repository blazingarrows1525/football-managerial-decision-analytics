# Analysis Report — Football Managerial Decision Analytics

*Big Data Visualization and Analytics.* All numbers come from the executed notebook
`football_managerial_analytics_enhanced.ipynb` (fresh-kernel run, see `NOTEBOOK_EXECUTION_REPORT.md`); figure codes
(B1, C3, …) refer to the notebook and to `visualization_gallery/`.

## 1. Question and approach
How can match events, lineups and match state be turned into visual evidence that supports managerial decisions —
who starts, who comes on, how the team plays — without overstating what the data show? Each analysis follows
*question → analysis → visualization → interpretation → managerial implication*, with uncertainty stated.

## 2. Data
| Item | Value |
|---|---|
| Source | StatsBomb Open Data (Hudl), 1. Bundesliga 2023/24 (competition 9, season 281) |
| Coverage | all 34 published matches (every match involves Bayer Leverkusen), 19 Aug 2023 – 18 May 2024 |
| Volume | 70 raw JSON files, 120.05 MB; 137,765 events; 1,353 matchday-squad rows; 460 players; 18 teams |
| Present (verified, B9) | event x/y (100% of on-ball events), pass end location (100%), recipient (98%), StatsBomb xG (100% of shots), formations, full squads incl. bench, manager identity, referee, stadium |
| Absent (not analysed) | player age/height/salary, injuries/fitness, optical tracking, attendance/weather; 360 frames published but not loaded |

## 3. Data quality (Part B)
- 16/16 domain-rule checks pass (unique IDs, on-pitch coordinates, xG in [0, 1], 11 starters and one GK per team-match, no overlapping spells, goal events reconcile with all 34 published scores).
- 0 full-row and 0 primary-key duplicates across seven tables (B4).
- Missingness is structural, not random (B2, B3): type-specific qualifiers exist only for their event types. Scoping each field to its event type raises completeness, e.g. xG from 0.7% of all events to 100% of shots (B8).
- Strongly right-skewed fields — duration (skew 4.3), pass length (1.8), shot xG (3.0) — motivate medians and rank-based statistics (B5). IQR "outliers" are genuine (long passes, penalties, full matches) and were retained (B7).
- Cleaning removes nothing from the raw data; analysis excludes only shoot-out / non-play rows and minutes are rebuilt from the event timeline because the lineup file's position spells are not chronological.

## 4. Exploratory findings (Part C)
- Role families occupy different regions of metric space: median xG/90 0.32 (forwards) vs 0.02 (defenders); interceptions/90 1.40 vs 0.08 (C1). 8 of 10 per-90 metrics are right-skewed.
- Pressing volume is unrelated to chance creation (pressures vs key passes ρ = −0.02), while xG and key passes co-vary (ρ = 0.37) (C2).
- Territorial dominance over 33,332 completed passes: 21,351 by the focus team, with density mass high and central; opponents' passes concentrate deep (C3).
- Season gauges: 82% win rate, 2.65 points per match, 72% share of match xG.

## 5. Football performance findings (Part D)
- **Passing structure.** Granit Xhaka has the highest season-average PageRank (0.140) and betweenness (0.211); the four highest-PageRank players are Xhaka, Palacios (DMs), Tapsoba and Hincapié (CBs) — build-up runs through deep hubs (D1).
- **Consistency.** Among above-median progressors, Florian Wirtz combines 11.9 progressive actions/90 with the lowest match-to-match variability (CV 0.35); bootstrap intervals for chance involvement are wide (D2).
- **Team stability.** Pass completion (CV 0.04) and possession proxy (0.16) are the most stable match metrics; xG against (0.72) and PPDA (0.53) the most volatile (D3).
- **Scoring.** 89 scored / 24 conceded; 49% of goals came in possessions that began with a corner, free kick or throw-in (StatsBomb play pattern) (D4).
- **Decision support (from the original pipeline).** Starting-XI optimiser agreement with the actual XI: 77.7% mean over 33 matches; substitution heuristic contains the actual incoming player in its top 3 for 82.5% of non-injury changes (random ≈ 43%).

## 6. Statistical analysis (Part E)
| Analysis | n | Result | Interpretation |
|---|---|---|---|
| Spearman correlation with goal difference (11 variables, bootstrap CI, Benjamini–Hochberg) | 34 matches | strongest xG against ρ = −0.43 (95% CI −0.72 to −0.05), q = 0.093; xG for ρ = 0.37; possession proxy ρ = 0.12; **0 variables with q < 0.05** | Direction favours chance quality over possession; not significant after FDR at this n |
| Home vs away xG difference (Mann–Whitney, Cliff's δ) | 17 vs 17 | +0.56 (95% CI −0.18 to +1.23), δ = 0.34 (medium), p = 0.098 | Suggestive, not significant |
| First vs second half of season | 17 vs 17 | −0.13, δ = −0.07 (negligible), p = 0.731 | No change in dominance |
| Progressive passes/90 across role families (Kruskal–Wallis) | 70 players | H = 2.9, ε² = 0.01, p = 0.239 | Weak role differences |
| Shot quality, focus vs opponents (KS, Mann–Whitney) | 623 vs 293 shots | mean xG/shot 0.117 vs 0.095 (diff CI +0.003 to +0.040); KS p = 0.134; MW p = 0.079, δ = 0.07 | Dominance comes mainly from shot volume |
| Bootstrap per-90 xG intervals | players ≥ 900 min | Boniface 0.87 (0.64–1.13) clearly separated from the runner-up (Schick 0.25–0.64) | Only broad tiers are statistically clear |
| PCA of 14 per-90 metrics | 70 players | PC1 35%, PC2 17%; 6 components for 80% | Profiles are multi-dimensional |

Pearson, Spearman and Kendall coefficients agree in sign for every variable (E1b).

## 7. Advanced analytics (Part F)
- **Clustering.** K-Means silhouette peaks at k = 2 (0.32, weak structure); Gaussian-mixture BIC prefers k = 9; ARI K-Means–Ward 0.87, K-Means–GMM 0.52, Ward–GMM 0.62; DBSCAN finds one dense cluster with 3 noise players. Playing styles look continuous rather than discrete (F1).
- **Selection model.** Feasibility: match outcome rejected (28 W, 6 D, 0 L), goals rejected (n = 34), starting selection accepted (660 rows, 33 matches). Expanding-window CV (5 folds): F1 — baseline 0.775, logistic regression 0.811, random forest 0.789, gradient boosting 0.782; ROC-AUC 0.838 / 0.829 / 0.816. Hold-out (chronological): logistic regression AUC 0.775 (F2).
- **Explainability.** Permutation importance: minutes share before the match (0.099 AUC) and started previous match (0.031). SHAP (gradient boosting): start share (1.26) and minutes share (0.83) in log-odds units. Selection is explained by continuity, not workload or rest.

## 8. Managerial insights (Part G)
1. **Chance creation is concentrated** — top three players produce 40% of xG + xA → secure like-for-like cover; manage their minutes.
2. **Results ran ahead of chance quality** — 90 points vs 74.8 xPts → anchor expectations and staff evaluation on xG for/against.
3. **Build-up runs through identifiable hubs** — Xhaka (PageRank and betweenness) → rehearse alternative routes; protect hub availability.
4. **A stable core, rotation at the margins** — 7 players started ≥ 25 matches, 2.2 XI changes per match → focus evidence on the 2–3 rotation slots.
5. **Late, game-state-driven substitutions** — median 79', 79% while leading → pre-plan role-compatible replacement pairs.
6. **A home edge is suggestive but unproven** — δ = 0.34, p = 0.098 → keep one game model; re-test with more data.
7. **Profiles are continuous** — silhouette 0.32; DBSCAN one core → recruit on role-specific metric profiles, not cluster labels.

## 9. Limitations
Team-centric sample (opponents appear 1–2 times, always against the same team); no cup/European fixtures (workload
under-stated); no injury, fitness, tracking or age data; xG and xPts are model outputs; n = 34 matches limits
statistical power; every relationship is an association, not a causal effect.

## 10. Future research
Multiple full league seasons for independent benchmarks; post-shot xG for goalkeeper evaluation; 360 and tracking
data for off-ball and pressing analysis; matched-window designs for substitution effects; manager-tenure data across
clubs.
