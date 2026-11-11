# Deployment — Streamlit Community Cloud

**Status: not deployed by the implementation session.** Deploying needs the repository owner's Streamlit
account (sign-in and authorisation of the GitHub app), which cannot be done on the owner's behalf. The app was
validated locally (see "Verification before deploying"); the steps below are what remains.

## What is in the repository for deployment

| File | Role |
|---|---|
| `app.py` | entry point (`streamlit run app.py`) |
| `pages/` | the 13 pages registered through `st.navigation` |
| `src/` | shared package used by the app and the notebooks |
| `requirements.txt` | runtime dependencies only (11 packages) |
| `.streamlit/config.toml` | theme and server settings |
| `.gitignore` | excludes `data/raw/`, `data/processed/`, `.streamlit/secrets.toml` |

No secrets are needed: the data source is a public GitHub repository. `st.secrets` is not used anywhere (a
test enforces this).

## Steps

1. Push `main` to GitHub (the repository is public).
2. Go to https://share.streamlit.io and sign in with the GitHub account that owns the repository.
3. **Create app → Deploy a public app from GitHub.**
   - Repository: `blazingarrows1525/football-managerial-decision-analytics`
   - Branch: `main`
   - Main file path: `app.py`
4. **Advanced settings → Python version:** 3.10 (the version the project was tested on locally; CI also runs
   3.12). No secrets to add.
5. **Deploy.** The first start installs the requirements and then loads the data (next section).
6. Open the app URL, wait for the first load and run the smoke check below. Only then record the URL in the
   README.

## Data on the hosted app

The StatsBomb user agreement does not allow redistributing the data, so no raw or processed tables are in the
repository. On first load the app:

1. downloads 70 JSON files (about 120 MB) from `raw.githubusercontent.com/hudl/open-data` with a timeout and
   four retries per file;
2. parses them one match at a time (bounded memory) — about 12 seconds on a laptop once downloaded;
3. writes a Parquet cache (about 10 MB) under `data/processed/`;
4. keeps the workspace in memory for all sessions (`st.cache_resource`).

A cold start therefore takes roughly one to two minutes depending on network speed; later sessions are
immediate. Community Cloud's disk is ephemeral: after the app sleeps or restarts it downloads again. This is
acceptable for a historical season — there is nothing to refresh, so **no scheduled workflow and no polling
are used**.

If a download fails, the affected match is skipped and reported in the parser issue log (Data Quality page);
if the catalogue itself cannot be fetched the app shows the error instead of an empty dashboard.

Optional StatsBomb 360 files (about 8 MB per match) are downloaded only when a user presses the button on the
Pitch & Event Explorer page.

### Resource note

Measured locally: the event table takes about 172 MB and the event-flag table about 198 MB in pandas, and a
Python process with the full workspace loaded used about 0.5 GB. One match of raw JSON is held during parsing.
This should fit Community Cloud's limits, but it has **not been measured on the hosted platform**. If the app
is stopped for memory, the simplest fix is to drop unused columns in `src/pipeline.build_features` before
caching.

## Verification before deploying (done locally)

```bash
pip install -r requirements-dev.txt
pytest                              # includes AppTest runs of every page and view
streamlit run app.py                # manual check at http://localhost:8501
```

## Smoke check after deploying (to be done by the owner)

- [ ] The Executive Overview shows 34 matches, record 28-6-0, 90 points.
- [ ] Every page in the navigation opens without a red error box.
- [ ] Changing **Venue** to *home* changes the match count to 17 on every page.
- [ ] Match Centre → Shots & xG shows a shot map; Player Lab → Maps shows a heatmap.
- [ ] Data Quality & Sources → Source and manifest lists 70 files and offers the manifest download.
- [ ] The footer shows the StatsBomb attribution and logo.

## Local alternatives

- `streamlit run app.py --server.port 8501` on any machine with Python 3.10+.
- Synthetic layout check without network: `FMA_DATA_MODE=DEMO_SYNTHETIC streamlit run app.py` (every page is
  watermarked as synthetic).

## Health and troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| Long first load | cold start download | wait; watch the spinner text |
| "No match satisfies the current filters" | filters exclude everything | Reset filters |
| A chart shows "implemented but unavailable" | prerequisite missing for the scope | the message names the missing field or sample size |
| `ModuleNotFoundError: src` | app started from another folder | run from the repository root |
| SHAP charts unavailable | optional package | add `shap` to `requirements.txt` if wanted |
