# Implementation Progress Ledger (V3)

Evidence for each phase, in the order the work was done. Numbers are copied from the actual runs; nothing
here is a plan or a promise.

## Phase 0 — Reconnaissance (10 Nov 2026)

- Git state, history, remote, tracked files and both notebooks inspected; the owner's uncommitted local
  notebook outputs identified and left untouched. Details: `docs/IMPLEMENTATION_BASELINE.md`.
- The committed enhanced notebook re-executed outside the repository: exit 0, 161 s, 0 cell errors, 95
  interactive + 27 static figures; every documented headline number reproduced.
- Source verified through the GitHub API (`hudl/open-data`, commit `4b73468`); licence read.

## Phase 1 — Shared core

- About 290 top-level definitions moved verbatim from the executed notebook's pipeline cells into `src/`
  (`data`, `features`, `analytics`, `visualization`) by an AST-based splitter that derived the imports; no
  import cycles.
- Added: `pipeline.py`, `workspace.py`, Parquet cache keyed by raw files and code versions, table contracts,
  memory-bounded per-match loading, provenance manifest.
- **Bug found and fixed:** cache file names containing a dot overwrote each other; round-trip now verified
  table by table.
- **Equivalence check:** the shared package reproduces the baseline exactly — 34 matches, 137,765 events,
  16/16 rules, 74.8 xPts, ρ(xG against) = −0.4275 (CI −0.722 to −0.054, q = 0.093), venue δ 0.336 / p 0.098,
  k = 2 / silhouette 0.318, CV F1 0.775 / 0.811 / 0.789 / 0.782, hold-out AUC 0.775, XI agreement 77.7%,
  substitution top-3 82.5%. Encoded as `tests/test_decision_support.py::test_real_data_results_match_the_documented_baseline`.

## Phase 2 — Analytics and chart registry

- New analytics: effect sizes, permutation tests, partial and robust correlation, power, autocorrelation,
  Wilson intervals and shrinkage, bootstrap rate intervals, clustering comparison and stability, outlier
  scores, a model comparison with learning curve and subgroup errors, explainability, Expected Threat.
- **Bug found and fixed:** clustering failed when a metric was constant in the sample (fixture data).
- Registry of 278 chart specs (atlas IDs 001–244 plus 34 additional project charts) with an availability
  checker returning one of four statuses with the exact reason.
- **Source inconsistency found:** the published 360 file of match 3895158 shares 0 of 3,318 frame identifiers
  with its event file; the freeze-frame chart reports this instead of guessing a join. The 360 file of match
  3895052 joins correctly and renders.

## Phase 3 — Visual quality

- Charts rendered to PNG and inspected in montages; fixed: titles clipped at half width, attribution colliding
  with axis titles, legends overlapping x-axis titles, crowded Pareto labels, an unexplained empty column on
  the progression-lanes chart.

## Phase 4 — Streamlit dashboard

- `app.py` with `st.navigation` and 13 pages; global filters rebuild every table on the matches in scope
  (`pipeline.subset_bundle`); presentation mode; per-chart HTML export; CSV downloads.
- **Bug found by the tests and fixed:** filter selections were lost on page change; widget state is now
  persisted.
- Checked in the browser at 1400 px: no horizontal overflow, no console errors.

## Phase 5 — Tests and CI

| Command | Result |
|---|---|
| `ruff check src pages app.py scripts tests` | all checks passed |
| `pytest` (all suites, real data cached) | **521 passed**, 0 failed, 274.6 s |

Suites: data loading and parsing, minutes, validation, features, lineup constraints, substitution logic,
statistics, decision support and documents, registry, every renderer (fixture, empty, missing field, single
group, no mutation, watermark, export), Streamlit `AppTest` of every page and view on synthetic and on real
data, repository hygiene. Tests marked `real_data` skip automatically when the raw cache is absent (as in CI).

`.github/workflows/ci.yml` runs lint, the suite, a notebook smoke run and a report build on the synthetic
fixture for Python 3.10 and 3.12 (results below).

## Phase 6 — Clean-environment install

A fresh virtual environment installed `requirements.txt` without errors and resolved newer versions
(streamlit 1.65.0, pandas 2.3.3, numpy 2.2.6, scikit-learn 1.7.2, plotly 6.9.0, matplotlib 3.10.9). Every chart
was validated there: **271 available, 2 unavailable (the SHAP charts — `shap` is an optional extra), 5 not
implemented, 0 failed.**

### First CI run and the fixes it led to

The first GitHub Actions run (commit `5e83fc6`) **failed** on both Python versions. CI installs newer
packages than the local environment, and two portability problems surfaced:

1. pandas 2.3 deprecates silent downcasting in `fillna` on object columns; three lines in
   `src/data/parsers.py` triggered it, and the test configuration turns such warnings into errors. Fixed with
   dtype-safe fills; every result is unchanged (460 players, 90 points, 74.8 xPts, F1 0.811, 77.7%, 82.5%).
2. Streamlit 1.65 discards widget values when the page changes, so global filters reset on navigation. The
   filters now live in plain session keys and the widgets are bound to them through shadow keys.

After the fixes, the full suite passes on both stacks:

| Environment | Command | Result |
|---|---|---|
| local: Python 3.10.11, streamlit 1.55, pandas 2.1.4, numpy 1.26 | `pytest` | **521 passed** |
| clean venv: streamlit 1.65, pandas 2.3.3, numpy 2.2.6, scikit-learn 1.7.2 | `FMA_DATA_MODE=DEMO_SYNTHETIC pytest` | **521 passed** |

Second CI run (commit `63ed82b`, run 43019875163): **passed** on Python 3.10 and 3.12 — lint, the full suite
on the synthetic fixture, the notebook smoke run and the offline report build.

## Phase 7 — Notebooks and documents

- `scripts/build_notebooks.py` generates seven chapters and the main notebook; `scripts/run_notebooks.py`
  executes them in fresh kernels. Results: `NOTEBOOK_EXECUTION_REPORT.md` (V3 section) and
  `artifacts/reports/notebook_execution.json`.
- `scripts/build_reports.py` (final run): 273 available, 0 unavailable, 5 not implemented, 0 failed
  (E-129 is available because a joinable 360 file is cached locally; on a fresh checkout it is unavailable
  until a 360 file is downloaded). Wrote the manifest, data dictionary, provenance page, catalogue, results
  snapshot, evidence cards and `artifacts/reports/ANALYSIS_REPORT_V3.md`.
- Docs: architecture, methodology, deployment, review evidence templates (no review outcomes recorded), demo
  walk-through, viva question bank.

## Not done / not verified

- **Deployment** to Streamlit Community Cloud: not performed (needs the owner's account). Steps:
  `docs/DEPLOYMENT_STREAMLIT_CLOUD.md`.
- Hosted memory use not measured (local process with the full workspace: about 0.5 GB).
- The notebooks were not run in Google Colab.
- `statsmodels` (LOESS line) was not installed; the regression chart says so.
- Dashboard screenshots are not committed; the app was inspected locally only.
