# Build Log

Environment: Windows 11, Python 3.10.11, pandas 2.1.4, numpy 1.26.2, scipy 1.15.3, scikit-learn 1.3.2,
plotly 6.6.0, pyarrow 23.0.1, ipywidgets 8.1.8, nbclient 0.11.0, pytest 9.1.1. Network access to GitHub raw: available.
Workspace at start: empty folder, not a Git repository (no files to preserve).

## Stages
| # | Stage | Result |
|---|---|---|
| A | Requirement + workspace discovery | Empty workspace → layout from the brief; defaults recorded in `config.py` |
| B | Source discovery | StatsBomb catalogue read (80 competition-seasons). Real event/lineup/match files inspected before writing parsers. Default: 1. Bundesliga 2023/24 (34 matches, manager metadata, 360 available) |
| C | Canonical model + quality | 16 checks; all pass on the real data (incl. score reconciliation for 34/34 matches) |
| D | Features | 45 defined metrics, per-90, role percentiles, form, workload proxies, team style, match state |
| E | Visualisation | 35 chart functions, 38 figures in the executed notebook, empty-state safe |
| F | Decision support | Hungarian XI optimiser; live substitution context + ranking; leakage controls via `asof` / elapsed cut-offs |
| G | Modelling | Gated logistic regression "who starts?" — gate passed (660 rows, 33 matches), chronological split |
| H | Delivery | Tests, notebook execution (real + synthetic), reports, dataset card / dictionary generated from the run |

## Tests and executions (final state)
* `python -m pytest -q` → **91 passed** (≈11 s, offline).
* `python scripts/execute_notebook.py` (REAL_OPEN_DATA, fresh kernel) → 46 code cells, **0 errors**, ≈58 s with
  cached data (first download of 70 files / 120 MB ≈ 45 s).
* `python scripts/execute_notebook.py --mode DEMO_SYNTHETIC` → 46 code cells, **0 errors**, ≈20 s; synthetic banner
  present on every chart (73 occurrences in outputs).

## Failures encountered and fixes
| # | Symptom | Root cause | Fix |
|---|---|---|---|
| 1 | `UnicodeDecodeError` reading JSON | Windows default cp1252 | All reads decode UTF-8 explicitly |
| 2 | Lineup spells out of time order (second yellow at 47:30 P1 listed after 45:00 P2) | StatsBomb lineup `positions` sorted by clock string | Minutes rebuilt from the event stream (Starting XI → Substitution → sending-off), period-aware elapsed time; tested |
| 3 | `KeyError: 'duration'` | Period-bounds merge collided with event `duration` | Renamed bound columns before merge |
| 4 | `KeyError: 'yellow_cards'` | Lineup-file card count collided with event-derived count | Renamed to `lineup_yellow_cards` |
| 5 | Synthetic data failed QC (3,129 out-of-pitch coordinates; clock steps backwards) | Generator mirrored only x; random in-minute seconds | `_mirror` flips both axes; monotonic seconds. QC caught it — checks working as intended |
| 6 | 8 test failures on first run | Charts filtered columns before checking them; empty-history season table indexed by object dtype; empty candidate list sorted | `_rows` helper; dtype-safe `eligible` filters; empty guards |
| 7 | Notebook build `SyntaxError` | Triple-quoted f-string inside raw cell source | Rewritten as single-line f-strings |
| 8 | Notebook cell error in substitution agreement (first match) | No pre-match history → empty table → boolean index treated as column list | `astype(bool)` on all eligibility filters; positional-key FutureWarning removed |
| 9 | 99 % of pre/post windows "contaminated" | Simultaneous changes in one window contaminated each other | Unit = team substitution *decision*; contamination by type; opponent changes reported separately; window 10 min |
| 10 | Centre-backs assigned to the wrong side | Identical slot roles → arbitrary assignment | +2 side-preference tie-breaker (documented) |
| 11 | Goalkeeper topped progressive passes/90 | Goal kicks met the "25 % closer" rule | Progressive passes must start outside the defending 40 % (x ≥ 48) |
| 12 | Synthetic run overwrote real `reports/DATASET_CARD.md` and processed tables | Shared output folders | Mode-specific `synthetic/` folders; synthetic cards → `outputs/exports/synthetic/`; regression test added |
| 13 | Dataset card showed cache-read time as "retrieval" | Manifest only had read timestamps | Added `file_written_utc` (actual download time) |
| 14 | PNG export skipped | `kaleido` not installed | HTML export always works; PNG optional (documented in requirements) |

## Not verified here (be explicit in the viva)
* The notebook was executed with Jupyter/nbclient locally, **not inside Google Colab**. The Colab-only branch of the
  setup cell (clone/upload bundle, `enable_custom_widget_manager`) has not been run.
* ipywidgets controls were not clicked in a live kernel: in headless execution they print a note. The functions they
  call (player view, XI optimiser, substitution recommender) are executed in static cells and covered by tests.
* API-Football enrichment is documented as optional and is not implemented beyond the source register.

## Remaining limitations
Team-centric season sample; no cup/European fixtures; no injury/fitness/tracking data; user-configured substitution
rules; xG and project-defined metrics are model outputs/approximations. See `reports/PROJECT_REPORT.md` §19.
