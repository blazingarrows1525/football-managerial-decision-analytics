# Review 1 — Problem Definition and Data Collection

> Evidence template. Fields in `[To be completed after actual review]` must be filled in by the student with what
> actually happened. Nothing below states that a review took place or that anything was approved.

| Field | Entry |
|---|---|
| Project | Football Managerial Decision Intelligence |
| Student / registration no. | `[enter]` |
| Review date (actual) | `[To be completed after actual review]` |
| Reviewer(s) | `[To be completed after actual review]` |
| Rubric component | Review 1 (5 marks) and Dataset Collection (5 marks) |

## 1. Problem statement
Raw football event and lineup data are difficult to turn into consistent evidence for two recurring coaching
decisions — who starts and who comes on. The project builds a reproducible pipeline and interactive visual analytics
that make player, team, match-state and observable managerial patterns explainable, with explicit data limits.

## 2. Research questions
Main: *How can historical football match events, player performance indicators, lineup records and match-state
context be transformed into interactive visual analytics that support evidence-based starting-lineup and
substitution decisions?* Supporting RQ1-RQ8 as listed in `PROJECT_REPORT.md` §6.

## 3. Data sources identified and selection rationale
| Source | Role | Decision |
|---|---|---|
| StatsBomb Open Data | Events, lineups, matches incl. managers | **Primary** — open, documented, player-level events with xG, lineups with bench |
| API-Football | Coach/injury enrichment | Optional; needs own key; not used |
| Metrica sample data | Tracking demo | Not used (anonymised; cannot be merged with named players) |
| football-data.co.uk | Results | Not needed (scores available in StatsBomb) |
| Scraping FBref/Transfermarkt | — | Rejected (terms of use) |

Selected competition-season: **1. Bundesliga 2023/24** (competition 9, season 281) — chosen from the live catalogue
because every match carries manager metadata and the 34 matches cover one manager's full league season (rotation,
XI and substitution patterns), within the 20-50-match quick-run guideline.

## 4. Data collection status (from the executed run)
* 80 competition-seasons in the catalogue; 34 matches published and **34 downloaded and parsed** (no truncation).
* 70 raw JSON files, **120.05 MB**, cached unchanged in `data/raw/statsbomb/`; every file has a SHA-256 hash and UTC
  timestamp in `outputs/exports/source_manifest.csv`.
* 137,765 events · 1,353 matchday-squad rows · 460 players · 18 teams · 301 substitutions · 113 goals ·
  19 Aug 2023 – 18 May 2024.

## 5. Catalogue / metadata screenshot
`[Insert screenshot of notebook §3 catalogue table and §4 coverage cards]`

## 6. Schema preview
Canonical tables: matches (23 columns), managers, appearances (26), events (53), substitutions (39), goals,
formations — see `DATA_DICTIONARY.md`.

## 7. Data-quality findings
16 domain checks, **16 pass** on the real run (duplicates, coordinate ranges, xG range, XI size, one goalkeeper,
duplicate selection, substitution completeness, overlapping spells, event-to-score reconciliation for all 34 matches,
unresolved player references, unknown minutes). Key parsing finding: lineup-file position spells are not
chronological, so minutes are reconstructed from the event timeline (documented and unit-tested).

## 8. Initial chart prototypes
Coverage cards, missingness heatmap, match timeline, results overview (notebook §4, §5, §8).
`[Insert screenshots]`

## 9. Open issues at this stage
* Team-centric sample: opponents appear in only 1-2 matches.
* No cup/European fixtures: workload proxies will under-count.
* No injury/availability data.

## 10. Reviewer feedback and actions
| # | Feedback received | Action taken | Evidence / link | Status |
|---|---|---|---|---|
| 1 | `[To be completed after actual review]` | | | |
| 2 | `[To be completed after actual review]` | | | |

Reviewer remarks / marks: `[To be completed after actual review]`
