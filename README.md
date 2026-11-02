# Football Managerial Decision Analytics

**Big Data Visualization and Analytics** — an end-to-end, visualization-first analysis of how event data can support
football managerial decisions (starting XI, substitutions, rotation, tactics), built on real
[StatsBomb Open Data](https://github.com/statsbomb/open-data) for the 2023/24 1. Bundesliga (all 34 published matches).

## Repository contents

| File / folder | What it is |
|---|---|
| `football_managerial_analytics_enhanced.ipynb` | **Main deliverable.** Parts A–H: introduction, data quality, EDA, football analytics, statistics, clustering & models, managerial insights, conclusions. 74 cells · 95 interactive (Plotly) + 27 static (Matplotlib/Seaborn) figures, executed with outputs. |
| `Football_Managerial_Decision_Analytics.ipynb` | The original single notebook (preserved unchanged): pipeline, decision support and 95 interactive figures. |
| `visualization_gallery/` | 27 static PNG figures and 6 interactive HTML dashboards exported by the enhanced notebook. |
| `ANALYSIS_REPORT.md` | Written analytical report with every key number from the executed run. |
| `NOTEBOOK_EXECUTION_REPORT.md` | Environment, commands, execution results, fixes and unresolved items. |
| `requirements.txt` | Python dependencies. |

Data are **not** stored in the repository: the notebooks download the StatsBomb JSON (70 files, ≈120 MB) from GitHub
on first run and cache it in `data/raw/` (git-ignored).

## Run it

**Google Colab (no setup):** open
`https://colab.research.google.com/github/blazingarrows1525/football-managerial-decision-analytics/blob/main/football_managerial_analytics_enhanced.ipynb`
and choose *Runtime → Run all* (≈3–4 minutes including the first download).

**Locally:**
```bash
pip install -r requirements.txt
```
```bash
python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 football_managerial_analytics_enhanced.ipynb
```
Or open the notebook in Jupyter / VS Code and *Run All*. Live ipywidgets controls appear when a kernel is attached;
set the environment variable `FMA_HEADLESS=1` to replace them with notes (every view also has a static default).

## Notebook structure (enhanced)

| Part | Content |
|---|---|
| A | Problem, objectives, scope, tools, methodology; environment; configuration; visual design system (Plotly + static theme, pitch) |
| B | Source catalogue & provenance manifest, parsing, 16 domain-rule checks, **data-quality visual audit** (composition, missingness bars and matrix, duplicates, distributions, categorical imbalance, outliers, refinement funnel, verified feature availability) |
| C | EDA: season dashboard, distributions, correlations, team trends, KDEs by role, pair plot, 33k-pass hexbin, match-level views, gauges, funnel, waterfall, calendar, polar goal clock, opponent matrix |
| D | Player intelligence, archetypes, team & tactical maps, pass-network centrality (NetworkX), consistency with bootstrap CIs, scoring & goalkeeping, starting-XI optimiser, substitution intelligence, manager patterns |
| E | Pearson/Spearman/Kendall with bootstrap CIs and FDR control, group tests with effect sizes, bootstrap player intervals, PCA |
| F | Clustering comparison (K-Means, Ward, GMM, DBSCAN; elbow, silhouette, BIC, ARI), gated start-selection model, time-series CV of three models, ROC/PR, permutation importance, partial dependence, SHAP |
| G | Seven evidence-based managerial insight cards (evidence, why it matters, decision, limitation) |
| H | Conclusions, limitations, future research, viva question bank, machine-readable results |

## Headline results (from the executed run)
- 34 matches · 137,765 events · 460 players · 16/16 data-quality checks pass.
- 90 points vs 74.8 shot-based expected points; 89 goals from 72.7 xG.
- Top three players produce 40% of the squad's xG + xA; Granit Xhaka is the season's main passing hub (highest PageRank and betweenness).
- No match variable survives false-discovery control against goal difference at n = 34 (strongest: xG against, ρ = −0.43, 95% CI −0.72 to −0.05).
- Start-selection: logistic regression F1 0.81 vs 0.78 for "started last match" in time-series CV.

## Data attribution and scope
Data: StatsBomb Open Data (Hudl), used for educational, non-commercial research with attribution. Decision support
only — not a betting, fantasy or player-rating product; associations are not causal effects; no injury, fitness,
tracking or age data exist in the source and none are implied.
