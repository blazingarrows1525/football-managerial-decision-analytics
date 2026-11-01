# Review 2 — Analysis, Visualization and Decision-Support Prototypes

> Evidence template. Fill the `[To be completed after actual review]` fields with what actually happened.
> Status statements below describe the code and the executed run, not a review outcome.

| Field | Entry |
|---|---|
| Student / registration no. | `[enter]` |
| Review date (actual) | `[To be completed after actual review]` |
| Reviewer(s) | `[To be completed after actual review]` |
| Rubric component | Review 2 (5 marks) |

## 1. Cleaned dataset status
Canonical tables built and validated (16/16 checks pass). Processed tables exported to `data/processed/` (CSV +
Parquet); events 137,765 rows (Parquet).

## 2. Feature-engineering status
45 defined metrics (`DATA_DICTIONARY.md`), per-90 for players with minutes > 0, role/role-family percentiles,
5-appearance form, workload proxies, team style (possession proxy, field tilt, PPDA approximation), match state.
84 of 377 players are eligible at 180 minutes (17 at 900) — sensitivity table in notebook §7.

## 3. Interactive visualizations implemented
38 figures in the executed notebook (catalogue: `VISUALIZATION_CATALOG.md`); Plotly dropdowns for leaderboard,
scatter axes, distributions; ipywidgets for player, formation/availability and substitution scenario.
`[Insert screenshots]`

## 4. Player analysis
Leaderboards, radar vs benchmark group, strengths/weaknesses, rolling form, minutes/workload (notebook §9).

## 5. Lineup-selection prototype
Hungarian-assignment XI with explained components, constraints and omission reasons. Re-run before each of 33
Leverkusen matches with prior data only: mean **77.7 %** overlap with the actual XI (median 82 %) — descriptive
agreement, not a quality score.

## 6. Substitution-analysis prototype
Live context at any minute, outgoing/incoming ranking with evidence and risks. Re-run 1 second before 137
non-injury Leverkusen substitutions: actual incoming player in the heuristic's top-3 **82 %** of the time (random
top-3 ≈ 43 %); outgoing in top-3 57 %.

## 7. Manager-analysis coverage
Manager identity for 34/34 matches from source metadata. Xabi Alonso (34 matches) profiled; 21 opposing managers
with ≤ 2 matches shown as descriptive only, pooled as a labelled reference.

## 8. Validation / test evidence
`python -m pytest -q` → **91 passed** (parsing, minutes edge cases incl. red cards / half-time / extra time,
features, XI constraints, substitution eligibility & game state, validation, empty-state charts, end-to-end synthetic
integration). Notebook executed top-to-bottom in a fresh kernel: 46 code cells, 0 errors.

## 9. Limitations and next actions
Limitations in `PROJECT_REPORT.md` §19. Next actions: `[To be completed after actual review]`.

## 10. Reviewer feedback and actions
| # | Feedback received | Action taken | Evidence / link | Status |
|---|---|---|---|---|
| 1 | `[To be completed after actual review]` | | | |
| 2 | `[To be completed after actual review]` | | | |

Reviewer remarks / marks: `[To be completed after actual review]`
