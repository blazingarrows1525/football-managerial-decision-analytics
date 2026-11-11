# Project Review 1 — Evidence Pack (dataset collection and data understanding)

> This is an evidence template prepared from the executed project. It does not record that a review took place
> or what a reviewer said. Fields in square brackets are to be completed by the student after the actual review.

| Field | Value |
|---|---|
| Course | Big Data Visualization and Analytics |
| Project title | Football Managerial Decision Analytics |
| Student name / roll number | [To be completed by the student] |
| Faculty reviewer | [To be completed after actual review] |
| Review date | [To be completed after actual review] |
| Reviewer comments | [To be completed after actual review] |
| Marks awarded | [To be completed after actual review] |

## 1. Problem statement

How can real football event, lineup, player and match-state data be transformed into transparent and
interactive evidence that supports starting-XI selection, role fit, tactical interpretation, substitution
choices, rotation analysis and the evaluation of observable managerial decisions?

## 2. Dataset collection evidence (rubric: Dataset collection, 5 marks)

| Evidence | Where to show it |
|---|---|
| Source, publisher, licence terms and attribution | `docs/DATA_PROVENANCE.md`; dashboard → Data Quality & Sources → Source and manifest |
| Source log: 70 files, URL, bytes, SHA-256, write time for each | `data/manifest/source_manifest.json` |
| Collection method: cached, retried HTTPS download from the official repository | `src/data/statsbomb_client.py`; notebook `01`, first section |
| Scope: 1. Bundesliga 2023/24, 34 matches, 137,765 events, 460 squad players, 18 teams | notebook `00` scope table; `artifacts/tables/results.json` |
| Why this dataset: event coordinates, pass recipients, xG, formations, full squads, managers | notebook `01` feature-availability chart (A-012) |
| What is not available (age, injuries, tracking, …) and how that is handled | same chart; `docs/METHODOLOGY.md` §10 |
| Data dictionary with measured types and missingness | `docs/DATA_DICTIONARY.md` |
| Licence compliance: data not redistributed, attribution on every figure | `.gitignore`; chart footers; `docs/DATA_PROVENANCE.md` |

## 3. Cleaning and validation steps

1. Parse nested JSON to flat canonical tables — no raw row deleted.
2. Build a period-aware elapsed clock; rebuild minutes from Starting XI / Substitution / sending-off events.
3. Run 16 domain rules (unique IDs, coordinates on the pitch, xG in range and only on shots, eleven starters,
   one goalkeeper, no overlapping spells, goals equal to the published score, …) — **16 of 16 pass**.
4. Check 14 table contracts (grain, key, required fields) — **14 of 14 pass**.
5. Profile missingness per field and per event type; gaps are structural and are kept as missing.
6. Audit duplicates (0 full-row, 0 key duplicates) and outliers (retained: they are real events).
7. Note one source inconsistency found during the audit: the optional 360 file of one match shares no
   identifiers with its event file, so its frames are not used.

Charts for this section: A-001, A-003, A-004, A-005, A-006, A-010, A-011, A-012, A-014, A-016.

## 4. Architecture

`docs/ARCHITECTURE.md` (diagram and rules). Summary: one shared package → notebooks and dashboard; a chart
registry with an auditable status for every chart; filters that recompute; synthetic fixtures only for tests.

## 5. Planned analysis presented at this stage

Eight research questions and six hypotheses (notebook `00`), the metric conventions (per 90, role percentiles),
and the two decision-support tools with their constraints.

## 6. Suggested five-minute walk-through for the review

1. Notebook `00`: question, scope table, catalogue status.
2. Notebook `01`: source register and manifest → validation panel → missingness by event type → feature
   availability.
3. Dashboard → Data Quality & Sources: the same evidence, interactive; download the manifest.
4. State the limits: team-centric sample, no injury or tracking data, licence terms.

## 7. Questions a reviewer may ask at this stage

See `docs/VIVA_QUESTIONS.md`, sections A and B.
