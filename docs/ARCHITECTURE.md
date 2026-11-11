# Architecture

One shared analytics package (`src/`) feeds two front-ends: the research notebooks and the Streamlit
dashboard. A metric or a chart is defined once; neither front-end re-implements it.

```
                        StatsBomb Open Data (github.com/hudl/open-data)
                                        │  JSON over HTTPS, downloaded once
                                        ▼
 ┌──────────────────────────────── src/data ────────────────────────────────┐
 │ statsbomb_client  cached, retried downloads; one match in memory at a time │
 │ parsers           raw JSON → canonical tables; minutes from the event clock│
 │ validators        16 domain rules, coverage and missingness profiles       │
 │ schemas           Bundle container + 14 table contracts (grain, key, cols) │
 │ provenance        source register, licence terms, manifest with SHA-256    │
 │ cache             Parquet cache keyed by raw files + code versions         │
 │ synthetic         generated fixture league for tests (watermarked)         │
 └────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
 ┌────────────────────────────── src/features ──────────────────────────────┐
 │ event_features  flags + EVENT_KINDS / select_events (shared event filter)  │
 │ player_features per-90, role percentiles, role fit, form                   │
 │ team_features   team match stats, formations, expected points              │
 │ match_state · lineup_features · substitution_features · network_features   │
 │ values          project-computed Expected Threat grid                      │
 └────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
 ┌────────────────────────────── src/analytics ─────────────────────────────┐
 │ descriptive · statistical_tests · uncertainty · player_comparison          │
 │ clustering · models · explainability                                       │
 │ lineup_optimizer · substitution_analysis · manager_patterns                │
 └────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
        src/pipeline.build_bundle()  →  src/workspace.Workspace (bundle + memoised results)
                                      ▼
 ┌─────────────────────────── src/visualization ────────────────────────────┐
 │ registry      ChartSpec, render(), status_table(), search()                │
 │ availability  prerequisites → one of four statuses, with the reason        │
 │ catalogue     278 entries: renderer + required tables/columns + caveats    │
 │ theme · pitch · spatial · match · team · player · scouting · tactics ·     │
 │ lineup · passing · network · manager · substitution · statistical ·        │
 │ inference · model · distribution · comparison · audit · static_pitch       │
 └───────────────┬───────────────────────────────────────────┬───────────────┘
                 ▼                                           ▼
     src/reporting (notebook_tools,                 src/dashboard (state, filters,
     insight_cards, report_builder, exports)        layout, components, chart_explorer)
                 ▼                                           ▼
     notebooks/ 00–06 + Main                        app.py + pages/ 01–13
     scripts/build_reports.py → docs/, artifacts/
```

## Rules the code follows

- **Thin entry point.** `app.py` configures the page and the navigation and contains no data work
  (enforced by `tests/test_repository_hygiene.py`).
- **Direction of imports.** `data → features → analytics → visualization → dashboard / reporting`. No module
  imports "upwards"; a test imports every module on its own to catch cycles.
- **One renderer per chart.** A chart is a function returning a Plotly (or Matplotlib) figure. The catalogue
  binds it to an ID, its required tables and columns, minimum sample, method note and caveat.
- **Honest status.** `availability.check` returns `implemented_and_available`,
  `implemented_but_unavailable`, `not_implemented` or `failed_validation` with the exact reason.
- **Empty states, not fake data.** Every renderer checks its inputs and returns a labelled empty figure when
  rows or fields are missing.
- **Provenance on every figure.** `registry.render` adds the source and scope line, and a watermark when the
  data are synthetic.
- **Filters recompute.** The dashboard's global filters select matches; `pipeline.subset_bundle` rebuilds
  every feature table on that subset, so no number is merely hidden.
- **Read-only shared data.** The workspace is cached once per server process; a test verifies that rendering
  every chart leaves the shared tables unchanged.
- **Determinism.** Resampling and models take an explicit seed; the global NumPy generator is never seeded.
- **Versioning.** `SCHEMA_VERSION`, `PARSER_VERSION`, `FEATURE_VERSION` and the registry schema version are
  part of the cache fingerprint and the manifest.

## Key objects

| Object | Where | Purpose |
|---|---|---|
| `Config` | `src/config.py` | every threshold, weight, template and path; data mode (real / user / synthetic) |
| `Bundle` | `src/data/schemas.py` | canonical tables (`.tables`) and analytical tables for one run |
| `Workspace` | `src/workspace.py` | bundle + memoised results (xPts, xT, networks, models, backtests) + default selections |
| `Params` | `src/workspace.py` | the selections a chart may need (team, match, player, metric, …) |
| `ChartSpec` | `src/visualization/registry.py` | one catalogue entry |

## Data modes

| Mode | Source | Used by |
|---|---|---|
| `REAL_OPEN_DATA` | downloaded StatsBomb files in `data/raw/statsbomb/` | notebooks, dashboard, reports |
| `USER_DATA` | StatsBomb-format files supplied by the user in `data/external/` | optional |
| `DEMO_SYNTHETIC` | generated fixture league in `data/raw/synthetic/` | tests and CI only; watermarked everywhere |

Synthetic runs write to `artifacts/synthetic/` and `data/manifest/synthetic/` and never touch real outputs
(tested).

## Scale

About 138 thousand events and 120 MB of JSON: single-machine, vectorised pandas. The cold build takes about
12 seconds from the raw cache and under a second from the Parquet cache. Raw files are independent per match,
so the parse step is an embarrassingly parallel map if many seasons are added; no distributed engine is used
or claimed today.
