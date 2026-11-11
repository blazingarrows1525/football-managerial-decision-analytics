# Implementation Baseline (V3)

Recorded on 10 November 2026, before any V3 file was created. Everything below was verified in this
environment; where the V3 brief stated something that could not be confirmed, the difference is noted.

## Repository state

| Item | Verified value |
|---|---|
| Working directory | repository root of `football-managerial-decision-analytics` |
| Remote | `origin` → `https://github.com/blazingarrows1525/football-managerial-decision-analytics.git` |
| Branch | `main` (only branch; `origin/main` in sync) |
| Latest commit | `289f910` "Update slider on release in live substitution controls" |
| Earlier history | `0c6b7f5` merge of PR #1 · `0c42f14` enhanced notebook and reports · `1dc45ed` · `8d8fa79` · `e5b9fa8` single notebook · `83b4439` and `ca8c15e` the original modular package (later inlined into the notebooks) |
| Uncommitted changes | 34 tracked files modified locally: both notebooks and every file in `visualization_gallery/` |

**The uncommitted changes are the owner's own local re-run of the notebooks** (outputs only; the code cells are
identical to `HEAD`). They were left exactly as found: V3 does not stage, overwrite, reset or regenerate them.

## Tracked files before V3

`.gitignore`, `README.md`, `ANALYSIS_REPORT.md`, `NOTEBOOK_EXECUTION_REPORT.md`, `requirements.txt`,
`Football_Managerial_Decision_Analytics.ipynb`, `football_managerial_analytics_enhanced.ipynb`,
`visualization_gallery/` (27 PNG, 6 HTML). No `src/`, tests, Streamlit app, CI or deployment configuration
existed on `main`.

## Notebooks

| Notebook | Cells | Code | Errors | Plotly outputs | PNG outputs | Kernel |
|---|---|---|---|---|---|---|
| `Football_Managerial_Decision_Analytics.ipynb` (working copy) | 51 | 34 | 0 | 95 | 0 | python3 (3.13.9 recorded) |
| `football_managerial_analytics_enhanced.ipynb` (working copy) | 74 | 47 | 0 | 95 | 26 (+5 widget outputs) | python3 (3.10.11) |

Both are self-contained: the whole pipeline (configuration, download client, parsers, validation, features,
decision support, charts) is inlined in code cells. The enhanced notebook holds about 340 top-level definitions
in 13 pipeline cells and a further 20 script cells that produce the static figures and interpretations.

## Baseline re-execution

The committed enhanced notebook (`git show HEAD:…`) was executed in a scratch folder outside the repository,
linked to the existing raw-data cache, so that no repository file was touched:

```
FMA_HEADLESS=1 python -m nbconvert --to notebook --execute --ExecutePreprocessor.timeout=1800 football_managerial_analytics_enhanced.ipynb
```

| Check | Result in this run | Documented in the repository |
|---|---|---|
| Exit status / runtime | 0 / 161 s | 0 errors / ≈146 s |
| Cells / code cells / cell errors | 74 / 47 / 0 | 74 / 47 / 0 |
| stderr outputs | 0 | 0 |
| Plotly / static figures | 95 / 27 | 95 / 27 |
| Gallery files written | 27 PNG + 6 HTML | 27 PNG + 6 HTML |
| Matches / events / players | 34 / 137,765 / 460 | 34 / 137,765 / 460 |
| Points / xPts / goals / xG | 90 / 74.8 / 89 / 72.7 | same |
| Strongest correlation | xG against ρ = −0.428 (CI −0.722 to −0.054, q = 0.093) | same |
| Clustering | k = 2, silhouette 0.318, 3 DBSCAN noise players | same |
| CV F1 (baseline / LR / RF / GB) | 0.775 / 0.811 / 0.789 / 0.782 | same |
| Hold-out ROC-AUC (LR) | 0.775 | same |
| XI agreement / substitution top-3 | 77.7% / 82.5% | same |

The README's figures are therefore reproduced in the present environment. One wording difference: the working
copy holds 26 PNG outputs where a headless run yields 27, because the owner's interactive run did not have SHAP
figure output in the same form; the committed version yields 27.

## Data

- `data/raw/statsbomb/` (git-ignored): `competitions.json`, `matches/9/281.json`, 34 event files and 34 lineup
  files — 70 files, 120.05 MB. No 360 files were cached at baseline.
- Source repository verified through the GitHub API: `statsbomb/open-data` now redirects to
  **`hudl/open-data`**; default branch `master`; latest commit `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`
  (7 September 2026). Both raw URL forms return the same files.
- The licence (`LICENSE.pdf`, StatsBomb Public Data User Agreement) was downloaded and read: research use and
  public sharing of analysis are allowed; **redistribution of the data is not**; published analysis must credit
  StatsBomb with its logo. This decided the hosting strategy (download at run time, never commit data).

## Environment

Windows 11 · Python 3.10.11 · pandas 2.1.4 · numpy 1.26.2 · scipy 1.15.3 · scikit-learn 1.3.2 · plotly 6.6.0 ·
matplotlib 3.10.8 · seaborn 0.13.2 · networkx 3.4.2 · shap 0.49.1 · streamlit 1.55.0 · pyarrow 23.0.1 ·
pytest 9.1.1 · nbconvert 7.17.1 · nbclient 0.11.0. Not installed at baseline: mplsoccer, statsmodels, kaleido
(mplsoccer 1.8.1 and kaleido 1.5.0 were installed during V3 and tested; statsmodels was not installed).

## Baseline issues and risks

1. All logic lived inside notebooks: nothing could be reused by an application or unit-tested.
2. No tests, CI, deployment configuration or provenance manifest on `main`.
3. Interactive figures are invisible on GitHub; only the 27 static PNGs render there.
4. The source repository had moved; the README still cited the old URL.
5. The data licence forbids redistribution, which rules out committing a processed dataset for hosting.
6. The owner's local notebook outputs are uncommitted and must not be disturbed.

## Files V3 intended to change or add

Unchanged: both existing notebooks, `visualization_gallery/`, `ANALYSIS_REPORT.md` (kept as the V2 record).
Edited: `.gitignore`, `README.md`, `requirements.txt`, `NOTEBOOK_EXECUTION_REPORT.md` (V3 section appended).
Added: `src/`, `app.py`, `pages/`, `notebooks/`, `tests/`, `scripts/`, `docs/`, `artifacts/`,
`data/manifest/`, `.streamlit/config.toml`, `.github/workflows/ci.yml`, `pyproject.toml`,
`requirements-dev.txt`, `requirements-optional.txt`.
