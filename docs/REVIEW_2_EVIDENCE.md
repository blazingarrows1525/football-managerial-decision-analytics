# Project Review 2 — Evidence Pack (analysis, visualization and decision support)

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

## 1. What was built since Review 1

| Deliverable | Evidence |
|---|---|
| Shared analytics package | `src/` — data, features, analytics, visualization, dashboard, reporting |
| Research notebooks | `notebooks/00`–`06` and the single combined `Football_Managerial_Analytics_Complete.ipynb`, executed with outputs |
| Streamlit dashboard | `app.py` + 13 pages; `streamlit run app.py` |
| Chart registry | 278 entries with status; `docs/VISUALIZATION_CATALOGUE.md` |
| Tests | `tests/` — data, features, statistics, registry, every renderer, decision support, every dashboard page |
| Reports | `artifacts/reports/ANALYSIS_REPORT_V3.md`, generated from the run |

Exact counts (charts by status, tests passed, notebook cells and runtimes) are in
`docs/IMPLEMENTATION_PROGRESS.md`; they are copied from the actual runs.

## 2. Selected charts to show (one per family)

| Family | Chart | What it shows |
|---|---|---|
| Data audit | A-016 | every validation rule and table contract with its status |
| Distribution | B-022 raincloud | shape, quartiles and raw values of a per-90 metric by role |
| Match and team | L-262, C-046 | points vs expected points; shot volume vs quality |
| Player | D-069, D-079 | role percentiles; per-90 rates with bootstrap intervals |
| Pitch | E-133, L-263 | progression lanes; the Expected Threat surface |
| Network | F-140, F-139 | a match pass network sized by betweenness; season centrality |
| Lineup | G-149, G-166 | the shortlisted XI and why each player is in it |
| Substitution | H-171, H-182 | timing by score state; a labelled counterfactual shortlist |
| Manager | I-195 | proportions per manager with Wilson intervals and shrinkage |
| Statistics | J-202, J-214 | correlation forest with FDR control; power for n = 34 |
| Models | K-221, K-225 | models vs the baseline rule; calibration |

## 3. Findings recomputed in the final run

Taken from `artifacts/tables/results.json` (focus team: Bayer Leverkusen, 34 matches):

- 90 points against 74.8 shot-based expected points; 89 goals from 72.7 xG; 24 conceded from 27.8 xG against.
- Three players account for 40% of the squad's xG + xA.
- Granit Xhaka has the highest mean PageRank and betweenness in the pass networks.
- No match variable is associated with goal difference after false-discovery control at n = 34; the strongest
  is xG against (ρ = −0.43, 95% CI −0.72 to −0.05, q = 0.093).
- Home minus away xG difference: Cliff's δ = 0.34 (medium), p = 0.098 — suggestive, not established.
- Player profiles form a continuum (best silhouette 0.32 at k = 2; BIC prefers k = 9).
- Start-selection model: time-ordered CV F1 0.811 (logistic regression) against 0.775 for "started the previous
  match"; hold-out ROC-AUC 0.775.
- The pre-match shortlist shares 77.7% of the actual XI on average; the substitution shortlist's top three
  contains the actual substitute in 82.5% of 137 non-injury changes (random: about 43%).

Each statement is an association in one team-season; none is a causal claim.

## 4. Decision-support modules

| Module | Constraints enforced | Honest limits stated in the tool |
|---|---|---|
| Starting XI Lab | 11 distinct players, one goalkeeper, role eligibility, squad pool, pre-match information only | heuristic weights; no injury or fitness data; agreement ≠ quality |
| Substitution Lab | candidate on the bench and unused at that minute; substitutions and windows remaining under a configured rule | counterfactual simulation; before/after windows are confounded |

## 5. Quality evidence

- Renderer tests: valid fixture, empty input, missing fields, single group, no mutation of shared tables,
  watermark on synthetic data, source line on real data.
- Dashboard tests: every page and every view rendered with `AppTest` on synthetic and on real data; filters
  change the numbers; selections persist across pages.
- A test reproduces the documented results of the earlier enhanced notebook from the new shared package.

## 6. Suggested ten-minute demo for the review

See `docs/DEMO_WALKTHROUGH.md`.

## 7. Known limitations to state proactively

Team-centric sample; league matches only; no injury, fitness, tracking or age data; low statistical power;
model outputs (xG, xPts, xT) are not observations; the dashboard has not been deployed to a public URL by the
implementation session.
