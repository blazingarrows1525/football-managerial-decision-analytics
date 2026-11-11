# Football Managerial Decision Analytics

**Big Data Visualization and Analytics** — an evidence-first study of how football event data can support
managerial decisions (starting XI, role fit, tactics, substitutions, rotation), built on real
[StatsBomb Open Data](https://github.com/hudl/open-data) for the 2023/24 1. Bundesliga: the 34 published
matches, all involving Bayer Leverkusen.

Two connected deliverables share one analytics package:

- **Research notebooks** — the detailed record of data, methods, statistics and findings.
- **Streamlit dashboard** — a 13-page interactive application built on the same code.

Decision support, not an oracle: every result states its sample, method and limits, and nothing here is a
causal claim.

## Quick start

```bash
pip install -r requirements.txt
```

```bash
streamlit run app.py
```

The first run downloads 70 JSON files (about 120 MB) from the official StatsBomb repository into `data/raw/`
and caches the parsed tables; later runs start in about a second. For notebooks and tests:

```bash
pip install -r requirements-dev.txt
```

```bash
python scripts/run_notebooks.py
```

```bash
pytest
```

## Repository map

| Path | What it is |
|---|---|
| `app.py`, `pages/` | Streamlit entry point and 13 pages |
| `src/` | shared package: `data`, `features`, `analytics`, `visualization`, `dashboard`, `reporting` |
| `notebooks/` | seven research chapters (`00`–`06`) and **`Football_Managerial_Analytics_Complete.ipynb` — everything in one notebook**, executed with outputs |
| `tests/` | data, feature, statistics, chart-registry, renderer, decision-support, dashboard and hygiene tests |
| `scripts/` | `build_notebooks.py`, `run_notebooks.py`, `build_reports.py`, `export_gallery.py` |
| `docs/` | architecture, methodology, data dictionary, provenance, visualization catalogue, deployment, review evidence, viva questions, baseline and progress ledger |
| `artifacts/` | generated report, results snapshot, chart status table, evidence cards, notebook execution summary |
| `data/manifest/source_manifest.json` | provenance manifest: every raw file with size and SHA-256 (no data) |
| `football_managerial_analytics_enhanced.ipynb` | **preserved** self-contained notebook from the previous version (Parts A–H, 95 interactive + 27 static figures) |
| `Football_Managerial_Decision_Analytics.ipynb` | **preserved** original single notebook |
| `visualization_gallery/` | **preserved** 27 static figures and 6 HTML dashboards exported by the enhanced notebook |
| `ANALYSIS_REPORT.md`, `NOTEBOOK_EXECUTION_REPORT.md` | reports of the previous version, with a V3 section appended to the execution report |

Raw and processed data are **not** in the repository: the StatsBomb user agreement does not allow
redistribution. The pipeline downloads them from the official source at run time.

## The dashboard

| Section | Pages |
|---|---|
| Overview | Executive Overview |
| Performance | Match Centre · Player Lab · Team Tactics · Pitch & Event Explorer |
| Decision support | Starting XI Lab · Substitution Lab · Managerial Intelligence |
| Evidence | Statistical Explorer · Model Evaluation · Chart Explorer |
| Reference | Data Quality & Sources · Methodology & About |

- Global filters (team, venue, result, opponent, dates, minimum minutes) **recompute** every table on the
  matches in scope; the active scope is printed on every page.
- Each page draws only the selected view; heavier analyses sit behind toggles.
- Every chart carries its ID, method note, caveat, source line and an HTML export.
- Presentation mode hides the sidebar and technical panels for a demo.
- The data are historical: nothing is live, polled or refreshed.

Deployment steps for Streamlit Community Cloud are in
[docs/DEPLOYMENT_STREAMLIT_CLOUD.md](docs/DEPLOYMENT_STREAMLIT_CLOUD.md). **The app has not been deployed to a
public URL yet** — that step needs the repository owner's Streamlit account.

## The notebooks

**One notebook for everything:** `notebooks/Football_Managerial_Analytics_Complete.ipynb`. Open it in Jupyter
inside the repository and choose *Run All*, or open it in Google Colab, where its first cell fetches the project
code and installs the requirements itself:
https://colab.research.google.com/github/blazingarrows1525/football-managerial-decision-analytics/blob/main/notebooks/Football_Managerial_Analytics_Complete.ipynb

| Notebook | Content |
|---|---|
| `00_Project_Research_And_Methodology` | question, objectives, hypotheses, scope, methodology, chart catalogue and explorer |
| `01_Data_Audit_And_EDA` | source and provenance, validation, missingness, duplicates, feature availability, exploratory analysis |
| `02_Player_Team_Match_Analytics` | season, match and player performance with uncertainty |
| `03_Pitch_Tactical_Visualizations` | pitch maps, zones, progression, Expected Threat, pass networks, formations |
| `04_Starting_XI_And_Substitutions` | constraint-aware shortlist, sensitivity, backtests, substitution patterns and scenarios |
| `05_Statistics_And_Models` | correlations with FDR control, group tests, power, PCA, clustering, the gated selection model |
| `06_Managerial_Insights_And_Report` | managerial patterns, evidence cards, answers to the hypotheses, conclusions |
| **`Football_Managerial_Analytics_Complete`** | **all seven chapters with every section in one notebook, plus an optional full chart atlas; runs inside the repository or on its own in Colab (it fetches the code itself)** |

Each chapter follows *research question → data and method → chart → interpretation → managerial implication
and limitation*; interpretations are generated from the computed values. The notebooks are produced by
`scripts/build_notebooks.py` and call the shared package — they contain no analysis logic of their own. The
committed copies store figures as static images (visible on GitHub); running them yourself gives interactive
Plotly figures.

## Visualization catalogue

`src/visualization/catalogue.py` registers every chart with its renderer, prerequisites, method note and
caveat; `docs/VISUALIZATION_CATALOGUE.md` lists the status of each for the loaded data.

| Status | Charts |
|---|---|
| implemented and available | 272 by default (273 when an optional StatsBomb 360 file has been downloaded) |
| implemented but unavailable | 1 by default (the 360 freeze-frame chart) |
| not implemented, reason stated | 5 (Voronoi, Delaunay, pitch control, target bullet chart, forecast residuals) |
| failed validation | 0 |

These counts describe what exists and rendered in the documented run. The catalogue is open-ended; it is not a
claim that every possible football chart has been built.

## Headline results (recomputed by the shared package)

- 34 matches · 137,765 events · 460 squad players · 16/16 data-quality rules and 14/14 table contracts pass.
- 90 points against 74.8 shot-based expected points; 89 goals from 72.7 xG.
- Three players account for 40% of the squad's xG + xA; Granit Xhaka is the main hub of the pass network.
- No match variable is associated with goal difference after false-discovery control at n = 34 (strongest:
  xG against, ρ = −0.43, 95% CI −0.72 to −0.05). With 34 matches only |r| ≥ 0.46 is detectable with 80% power.
- Start-selection model: time-ordered cross-validation F1 0.811 against 0.775 for "started the previous match".
- The pre-match shortlist shares 77.7% of the actual XI on average — similarity to the manager's choices, not
  evidence of quality.

Full report: [artifacts/reports/ANALYSIS_REPORT_V3.md](artifacts/reports/ANALYSIS_REPORT_V3.md).

## Reproduce everything

```bash
python scripts/build_reports.py
```

```bash
python scripts/build_notebooks.py
```

```bash
python scripts/run_notebooks.py
```

```bash
pytest
```

`build_reports.py` rewrites the manifest, the data dictionary, the provenance page, the catalogue, the results
snapshot and the report from the current data. Test, notebook and chart counts from the last run are recorded
in [docs/IMPLEMENTATION_PROGRESS.md](docs/IMPLEMENTATION_PROGRESS.md).

Optional extras (`requirements-optional.txt`): `shap` for SHAP charts, `kaleido` for static image export,
`statsmodels` for a LOESS line, and `seaborn` / `jinja2` for the two preserved notebooks. Features that need a
missing extra say so instead of failing.

## Scope and limits

Team-centric sample (opponents appear twice (home and away), always against the focus team); league matches only; no
injury, fitness, tracking, age or market data; xG, expected points and Expected Threat are model outputs; low
statistical power; associations, not causal effects. Synthetic data are used only by the automated tests and
are watermarked wherever shown.

## Data attribution

Data: StatsBomb Open Data (https://github.com/hudl/open-data), provided by StatsBomb / Hudl, used for
educational, non-commercial research under the StatsBomb Public Data User Agreement. Published analysis based
on the data should credit StatsBomb with its logo. Not a betting, fantasy or player-rating product.
