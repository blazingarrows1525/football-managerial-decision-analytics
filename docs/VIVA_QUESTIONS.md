# Viva Question Bank

Answers are grounded in what this project actually does and found. Numbers come from the final run
(`artifacts/tables/results.json`); re-check them there if the data or the code change.

## A. Problem and data

**1. What problem does the project address?**
Turning football event, lineup and match-state data into transparent evidence for managerial decisions —
selection, role fit, tactics, substitutions, rotation — while stating what the data cannot show.

**2. Which dataset is used and why?**
StatsBomb Open Data for the 1. Bundesliga 2023/24: 34 matches, 137,765 events, 460 squad players. It has event
coordinates, pass recipients, provider xG, formations, full match-day squads with benches and manager names,
which the decision-support tools need.

**3. Is this "big data"?**
Not in volume: about 120 MB of JSON. It is event-level data with variety (nested, type-specific fields) and a
pipeline designed to scale — files are independent per match, so parsing is a parallel map. pandas is the
right tool at this size; a distributed engine would be decoration.

**4. What is the main limitation of the sample?**
It is team-centric: every match involves Bayer Leverkusen, and opponents appear twice (home and away). Nothing can be
said about the league or about other teams' seasons.

**5. Under which terms is the data used?**
The StatsBomb Public Data User Agreement: research use and public sharing of analysis are allowed,
redistribution of the data is not, and published analysis must credit StatsBomb with its logo. So the
repository holds no data; the pipeline downloads it at run time.

**6. Which data are missing, and how do you handle that?**
Age, height, injuries, fitness or GPS load, tracking, post-shot xG, attendance, weather, market value. They are
listed as unavailable (chart A-012), never imputed, and charts needing them are marked not implemented.

## B. Processing and quality

**7. How are minutes played calculated?**
From the event stream: Starting XI, Substitution and sending-off events on a period-aware clock, giving
on-pitch spells. The lineup file's position spells are not chronological, so they are not used.

**8. How do you know the parsed data are correct?**
Sixteen domain rules pass — for example goals rebuilt from events equal the published score in all 34 matches,
every team-match has eleven starters and one goalkeeper, and no spells overlap — plus fourteen table contracts.

**9. Why are there so many missing values?**
They are structural: `shot_xg` exists on 0.7% of all events but on 100% of shots. Missing is kept as missing
and never read as zero.

**10. Did the audit find any real problem?**
One: the optional 360 file of one match shares no identifiers with its event file. Those frames are not used
rather than matched by guesswork.

**11. How is the coordinate system handled?**
StatsBomb records every team attacking left to right in both halves on a 120 × 80 pitch with the origin
top-left. No half-time flip is needed; a test checks the orientation and the mirror transform.

## C. Metrics

**12. What is a per-90 metric and when is it unreliable?**
Value divided by minutes times 90. With few minutes it is unstable, so players below the threshold (default
180 minutes) are flagged and kept out of benchmark pools; the threshold is adjustable and its effect is shown.

**13. Why percentiles within role groups?**
Raw leaderboards mostly rediscover positions. Comparing within the role group (with the group size shown) is
like-for-like.

**14. What is your possession figure?**
A proxy: the team's share of both teams' passes. It is labelled as such — it is not timed possession.

**15. How is PPDA defined here?**
Opponent passes in their own 60% of the pitch divided by the team's tackles, interceptions, fouls and failed
challenges in that zone. Lower means more defensive actions per opponent pass. It is an event proxy for
pressing, not a measure of pressing quality.

**16. What are expected points?**
For each match every shot is simulated as a Bernoulli trial with its xG, 5,000 times; the mean points are the
expected points. It assumes independent shots and ignores game state — a model reference, not an observation.

**17. Did you compute Expected Threat?**
Yes, as a project-computed value: a 16 × 12 grid solved by value iteration, with passes and carries as moves
and mean provider xG as shot value. It is fitted in-sample on these 34 matches, so it is descriptive.

## D. Visualization

**18. How many charts are there?**
The registry lists 278 entries; 273 have a renderer. For the real dataset 272 are available by default (273
when an optional 360 file has been downloaded) and 5 are deliberately not implemented. The count describes
what exists and rendered, not every possible football chart.

**19. Why are some charts not implemented?**
Voronoi, Delaunay and pitch control need simultaneous positions of all players (tracking). A bullet chart
needs a legitimate target, and forecasting needs temporal depth. Drawing them from event data would invent
information.

**20. How do you stop a chart from misleading?**
Subtitles state sample and method; large maps disclose sampling; density charts say shading is interpolation;
event footprints are not called playing areas; median event locations are not called formations; gauges are
used only for bounded measures.

**21. What is the chart registry for?**
One specification per chart: renderer, required tables and columns, minimum sample, method note, caveat and a
status computed against the loaded data. The notebooks and the dashboard both render from it.

**22. How does the dashboard avoid rendering everything?**
Pages draw only the selected view; heavy analyses are behind toggles; the Chart Explorer renders one chart on
demand; results are memoised in a cached workspace.

## E. Statistics

**23. Which variables relate to goal difference?**
The largest rank correlation is with xG against (ρ = −0.43, 95% CI −0.72 to −0.05), then xG for. After
Benjamini–Hochberg control none of the eleven variables is significant at n = 34.

**24. Why is nothing significant?**
Power. With 34 matches a correlation test has 80% power only for |r| ≥ 0.46. A non-significant result is not
evidence of no relationship.

**25. Why Spearman rather than Pearson?**
The metrics are skewed and have outliers; rank correlation is robust to both. Pearson and Kendall are shown
next to it and agree in sign.

**26. Is there a home advantage?**
Home minus away xG difference is +0.56 per match; Cliff's δ = 0.34 (medium) but p = 0.098 and the interval
includes zero. Suggestive, not established.

**27. Why bootstrap matches rather than events?**
Events within a match are dependent. Resampling the independent unit — the match — gives honest intervals.

**28. What did the clustering show?**
Weak structure: the best silhouette is 0.32 at k = 2, the mixture-model BIC prefers k = 9, and DBSCAN finds
one dense group with three outliers. Player profiles form a continuum.

## F. Models

**29. What do you predict and why only that?**
Whether a squad member starts. It is the only target with enough observations (660 rows from 33 matches).
Match results (no losses in 34 matches), goals, injuries and market value are not modelled.

**30. How do you prevent leakage?**
Every feature uses only earlier matches; folds are split by match in date order; the hold-out is the last 30%
of matches.

**31. Does the model beat a baseline?**
Slightly: cross-validated F1 0.811 for logistic regression against 0.775 for "started the previous match".
Selection is dominated by a stable core.

**32. What do the explanations show?**
Minutes share before the match and starting the previous match carry the model. That describes the model, not
a causal lever.

## G. Decision support

**33. How is the starting XI shortlist built?**
A weighted score (role fit, recent form, evidence volume, minutes-based exposure, continuity) times position
compatibility, assigned to formation slots with the Hungarian algorithm under hard constraints.

**34. Is it the best XI?**
Only under the stated weights and constraints. It agrees with 77.7% of the actual XI on average, which measures
similarity to the manager, not quality.

**35. How are substitute candidates restricted?**
To players named on the bench and not yet used at that minute, with substitutions and windows remaining under
a configured five-and-three rule.

**36. Can you say a different substitution would have changed the result?**
No. The scenario view is a counterfactual simulation. Before/after windows are confounded by score, opponent
changes and fatigue; 71% of them contain a goal, a red card or another own change.

**37. What can you say about the manager?**
Observable patterns only: three starting formations with one used in about three quarters of matches, about
two changes to the XI between league matches, late substitutions mostly made while leading. Other managers
have two matches, so no comparison is meaningful.

## H. Engineering

**38. How do the notebook and the dashboard stay consistent?**
Both call the same `src` package. A test reproduces the earlier notebook's documented numbers from that
package.

**39. How is the project tested?**
Unit tests for parsing, minutes, features, statistics and decision logic; a parametrised test for every
renderer; registry and availability tests; `AppTest` runs of every dashboard page and view on synthetic and
real data; repository hygiene checks.

**40. What is synthetic data used for?**
Only automated tests and layout checks. It is generated, clearly named, written to separate folders and
watermarked on every figure and page.

**41. How would this scale to many seasons?**
Parse matches in parallel, store canonical tables as partitioned Parquet, query with DuckDB or Spark, and keep
the same feature definitions.

**42. Is the dashboard deployed?**
It runs locally and passes its tests. Deployment to Streamlit Community Cloud needs the owner's account; the
steps are in `docs/DEPLOYMENT_STREAMLIT_CLOUD.md`.

## I. Limits

**43. What is the single biggest threat to your conclusions?**
One team-season: low power and no independent benchmark.

**44. What would you do next?**
Add complete league seasons, the team's other competitions, authorised availability data and tracking or 360
data; then re-test the venue and correlation findings.
