# Football Managerial Decision Intelligence

**Interactive player performance, starting-XI optimisation and substitution analysis using match data**
— a Big Data Visualization mini-project built on real StatsBomb open event data.

> Decision support, not prediction hype: every recommendation is a transparent heuristic, computed only from
> information available before the decision, shown with its data coverage. Not a betting, fantasy or rating product.

## What is in the box

| Deliverable | Path |
|---|---|
| Main notebook (executed, 68 cells, ~38 interactive charts) | `notebooks/Football_Managerial_Decision_Analytics.ipynb` |
| Python package (ingestion → parsing → validation → features → decisions → charts → reports) | `src/football_analytics/` |
| Tests (91, offline) | `tests/` |
| Build / execute / Colab-bundle scripts | `scripts/` |
| Project report, review templates, viva prep, visualisation catalogue | `reports/` |
| Auto-generated dataset card + data dictionary (from the executed run) | `reports/DATASET_CARD.md`, `reports/DATA_DICTIONARY.md` |
| Processed tables / run config / manifest / chart HTML | `data/processed/`, `outputs/exports/`, `outputs/figures/` |
| Build log (what was done, tested, fixed, still limited) | `BUILD_LOG.md` |

## Dataset (default run)
StatsBomb Open Data — **1. Bundesliga 2023/24** (competition 9, season 281): the 34 published matches
(all Bayer Leverkusen league matches, 19 Aug 2023 – 18 May 2024), **137,765 events**, 1,353 matchday-squad rows,
460 players, 18 teams, 301 substitutions, 70 raw JSON files (120 MB). Manager names come from the source's match
metadata. Any other competition-season in the StatsBomb catalogue can be selected in the notebook's configuration
cell. Data: StatsBomb Open Data (https://github.com/statsbomb/open-data), cited as required for educational use.

## Quick start (local)
```bash
pip install -r requirements.txt
```
```bash
python -m pytest -q
```
```bash
python scripts/build_notebook.py
```
```bash
python scripts/execute_notebook.py
```
Or open the notebook in Jupyter / VS Code and *Run All*. The first run downloads ~120 MB from GitHub (≈1 min);
later runs read the cache (`OFFLINE = True` works with no network). Offline demo without any download:
`python scripts/execute_notebook.py --mode DEMO_SYNTHETIC --out notebooks/demo_synthetic_run.ipynb`.

## Running in Google Colab
1. Either push this folder to GitHub and set `PROJECT_REPO_URL` in the notebook's first code cell, **or** run
   `python scripts/make_colab_bundle.py` locally and keep `dist/football_analytics_colab_bundle.zip`.
2. Upload `notebooks/Football_Managerial_Decision_Analytics.ipynb` to Colab (File → Upload notebook).
3. *Runtime → Run all*. If no repo URL is set, the setup cell asks you to upload the bundle zip; it is extracted to
   `/content/football-managerial-analytics`. Colab already provides pandas/plotly/scikit-learn; the cell installs
   only what is missing and enables the widget manager.
4. No secrets are needed. (API-Football is listed only as an optional enrichment; if you add it, read the key from
   Colab *Secrets* / an environment variable — never paste it into the notebook.)
5. The export cell zips `outputs/` and offers it for download.

## Architecture
```
StatsBomb raw JSON ──► ingestion.DataStore (cache, retries, SHA-256 manifest)
                         │
                         ▼
                   parsing.parse_all ── events (flattened, period-aware elapsed time)
                         │              squads, appearances (minutes from event timeline), goals, cards, formations
                         ▼
                   validation.quality_checks ── 16 domain rules + quality-action log
                         ▼
                   features ── event flags → player-match → player-season (per-90, role percentiles)
                         │      form, workload proxies, team-match style, match state
                         ▼
   ┌──────────────┬──────────────┬───────────────────┬────────────────────┬──────────────┐
   player_analysis tactical_     lineup_optimizer     substitution_         manager_       modeling
                   analysis      (Hungarian XI)       analysis (live ctx)   analysis       (gated)
   └──────────────┴──────────────┴─────────┬─────────┴────────────────────┴──────────────┘
                                           ▼
                      visualizations (Plotly, empty-state safe) · reporting (exports, dataset card)
```
`pipeline.build_bundle(config)` runs everything; the notebook calls the same steps one section at a time.

## Key methodological choices
* **Minutes** are reconstructed from Starting XI → Substitution → sending-off events with period-aware elapsed
  time (StatsBomb lineup position spells are not chronological). Minutes include stoppage time.
* **Per-90** only where minutes > 0; eligibility threshold configurable (default 180) with a sensitivity table.
* **Role normalisation**: percentiles within role (≥ 8 eligible players) or role family, labelled.
* **XI**: weighted, explained component scores × position compatibility; exact Hungarian assignment; one GK, no
  duplicates, unavailable players excluded, empty slot + warning on insufficient depth.
* **Substitutions**: context strictly before the decision minute; outgoing judged against each player's own
  pre-match baseline; intent rule (trailing → attack, leading → protect, drawing → balance) is a prompt, not a law.
* **Causality**: pre/post windows are associations; contamination (goals, cards, other decisions, opponent changes)
  is reported.
* **Managers**: observable decision patterns only; no leadership or "skill" scores; small samples never ranked.
* **Modelling**: one gated, leakage-audited logistic regression (who starts?) with a chronological split.

## Assessment rubric mapping
| Criterion | Evidence |
|---|---|
| Dataset collection (5) | Notebook §3-4 (catalogue, manifest with SHA-256, counts), `reports/DATASET_CARD.md`, `reports/DATA_DICTIONARY.md`, `data/README.md`, `outputs/exports/source_manifest.csv`, source register & attribution |
| Review 1 (5) | `reports/REVIEW_1_DATA_COLLECTION.md` (problem, RQs, source rationale, audit, quality report, prototypes, feedback template); notebook §1-6 |
| Review 2 (5) | `reports/REVIEW_2_ANALYSIS_AND_VISUALIZATION.md`; notebook §7-14; `tests/` (91 passing) |
| Presentation (3) | 7-minute outline in `reports/VIVA_PREPARATION.md`; narrative order of the notebook |
| Demo (3) | Fresh-runtime execution (`scripts/execute_notebook.py`), Plotly dropdowns + live widgets (player, formation/availability, substitution scenario), offline cache / synthetic fallback |
| Report (2) | `reports/PROJECT_REPORT.md` (22 sections, cited, results from the executed run) |
| Viva (2) | `reports/VIVA_PREPARATION.md` (25 questions with answer prompts), notebook §17 |

## Limitations (short)
One club's league season (team-centric sample; opponents appear 1-2 times); no cup/European fixtures (workload
proxies under-count); no injury, fitness, tracking or training data; substitution rules user-configured; xG is a
provider model output. See `reports/PROJECT_REPORT.md` §19.
