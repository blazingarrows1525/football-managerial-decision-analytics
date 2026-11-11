# Data Dictionary

> Generated 2026-11-11 11:30 UTC from the loaded data (schema 3.0.0, parser 3.0.0, features 3.0.0). Types, missingness and distinct counts are measured, not assumed.

## Tables and contracts

| table | origin | rows | grain | key | status | description |
| --- | --- | --- | --- | --- | --- | --- |
| matches | source | 34 | one row per match | match_id | PASS | Match metadata from matches/<competition>/<season>.json. |
| managers | source | 68 | one row per match and team | match_id, team_id | PASS | Manager identity as published in the matches file. |
| events | source | 137765 | one row per event | event_id | PASS | Flattened event stream from events/<match_id>.json plus an elapsed-time clock. |
| squads | source | 1353 | one row per match, team and squad player | match_id, team_id, player_id | PASS | Match-day squads (starters and bench) from lineups/<match_id>.json. |
| appearances | derived | 1353 | one row per match and squad player | match_id, player_id | PASS | Minutes reconstructed from Starting XI, Substitution and sending-off events. |
| spells | derived | 1049 | one row per continuous on-pitch spell | match_id, player_id, start | PASS | On-pitch intervals used for minutes, bench state and pairing analysis. |
| goals | derived | 113 | one row per goal | match_id, index | PASS | Goal timeline (shots with outcome Goal and own goals) reconciled with the scoreline. |
| formations | source | 195 | one row per formation record | match_id, team_id, index | PASS | Formations recorded on Starting XI and Tactical Shift events. |
| flags | derived | 137765 | one row per event | event_id | PASS | Events with boolean analysis flags (progressive pass, key pass, box touch, ...). |
| pms | derived | 1049 | one row per player and match | match_id, player_id | PASS | Player match statistics (event counts joined to reconstructed minutes). |
| season_pct | derived | 377 | one row per player and team | player_id, team_id | PASS | Player season totals, per-90 rates and role-group percentiles. |
| team_stats | derived | 68 | one row per team and match | match_id, team_id | PASS | Team match statistics with opponent values and result. |
| workload | derived | 1353 | one row per player and match | match_id, player_id | PASS | Pre-match minutes-based exposure features (no physical-load data exists). |
| subs | derived | 301 | one row per substitution | match_id, event_id | PASS | Substitutions enriched with score state, timing band and roles. |


`origin = source` means the fields are parsed from StatsBomb files; `derived` means computed by this project from those fields.

## Metric definitions (player and team counts)

| metric | definition | numerator | denominator | unit | source_fields |
| --- | --- | --- | --- | --- | --- |
| minutes_played | Actual playing time on pitch incl. stoppage (periods 1-4) from Starting XI/substitution/sending-off events | sum of spell lengths | - | minutes | events: Starting XI, Substitution, Foul Committed/Bad Behaviour cards, Half Start/End |
| goals | Shots with outcome Goal in periods 1-4 (shoot-out excluded) | count | - | goals | shot.outcome |
| npxg | Sum of StatsBomb xG on non-penalty shots | sum xG | - | xG | shot.statsbomb_xg, shot.type |
| xg | Sum of StatsBomb xG on all shots (periods 1-4) | sum xG | - | xG | shot.statsbomb_xg |
| xa | xG of shots assisted by the player's passes (pass.assisted_shot_id) | sum xG | - | xG | pass.assisted_shot_id, shot.statsbomb_xg |
| shots | Shot events (periods 1-4) | count | - | shots | type=Shot |
| shots_on_target | Shots with outcome Goal / Saved / Saved To Post | count | - | shots | shot.outcome |
| assists | Passes flagged goal_assist by StatsBomb | count | - | assists | pass.goal_assist |
| key_passes | Passes flagged shot_assist or goal_assist | count | - | passes | pass.shot_assist, pass.goal_assist |
| passes | Pass attempts | count | - | passes | type=Pass |
| passes_completed | Passes with no outcome (StatsBomb: no outcome = complete) | count | - | passes | pass.outcome |
| pass_completion_pct | Completed / attempted passes | passes_completed | passes | % | pass.outcome |
| long_pass_completion_pct | Completion of passes >= 30 units (yards) | completed long | long passes | % | pass.length, pass.outcome |
| progressive_passes | PROJECT DEFINITION: completed open-play pass starting outside the defending 40% (x >= 48) and ending >=25% closer to the opponent goal centre | count | - | passes | location, pass.end_location, pass.type, pass.outcome |
| final_third_passes | Completed passes from x<80 ending x>=80 | count | - | passes | location, end_location |
| box_passes | Completed passes ending in the penalty area from outside it | count | - | passes | location, end_location |
| crosses_completed | Completed passes flagged cross | count | - | passes | pass.cross, pass.outcome |
| through_balls | Passes with technique Through Ball | count | - | passes | pass.technique |
| progressive_carries | PROJECT DEFINITION: carry ending >=25% closer to goal centre, end x >= 48 and >=5 units forward | count | - | carries | location, carry.end_location |
| carries_into_final_third | Carries from x<80 ending x>=80 | count | - | carries | carry.end_location |
| carries_into_box | Carries ending in the penalty area from outside it | count | - | carries | carry.end_location |
| dribbles | Dribble (take-on) attempts | count | - | dribbles | type=Dribble |
| dribbles_completed | Dribbles with outcome Complete | count | - | dribbles | dribble.outcome |
| touches | On-ball actions (pass, receipt, carry, shot, dribble, clearance, interception, recovery, block, ...) | count | - | actions | type, location |
| box_touches | On-ball actions located in the opponent penalty area | count | - | actions | location |
| final_third_touches | On-ball actions with x >= 80 | count | - | actions | location |
| tackles | Duels of type Tackle | count | - | tackles | duel.type |
| tackles_won | Tackles with outcome Won / Success / Success In Play / Success Out | count | - | tackles | duel.outcome |
| interceptions | Interception events | count | - | actions | type=Interception |
| blocks | Block events | count | - | actions | type=Block |
| clearances | Clearance events | count | - | actions | type=Clearance |
| ball_recoveries | Ball Recovery events without recovery_failure | count | - | actions | ball_recovery |
| pressures | Pressure events | count | - | actions | type=Pressure |
| counterpressures | Pressure events flagged counterpress | count | - | actions | counterpress |
| aerials_won | aerial_won flag on pass/shot/clearance/miscontrol | count | - | duels | *.aerial_won |
| aerials_lost | Duels of type Aerial Lost | count | - | duels | duel.type |
| defensive_actions | tackles + interceptions + blocks + clearances + ball recoveries | sum | - | actions | derived |
| fouls_committed | Foul Committed events | count | - | fouls | type |
| fouls_won | Foul Won events | count | - | fouls | type |
| yellow_cards | Yellow cards (foul_committed/bad_behaviour card) | count | - | cards | card |
| red_cards | Red or second-yellow cards | count | - | cards | card |
| turnovers | Dispossessed + Miscontrol events | count | - | actions | type |
| gk_saves | Goal Keeper events whose type is a save | count | - | saves | goalkeeper.type |
| gk_claims | Goal Keeper collected / punch / sweeper / smother actions | count | - | actions | goalkeeper.type |
| gk_goals_conceded | Goal Keeper events of type Goal Conceded | count | - | goals | goalkeeper.type |


## Derived metrics and scores

| metric | formula | denominator / inputs | interpretation and caveat |
| --- | --- | --- | --- |
| per-90 rate | count or value / minutes played × 90 | minutes reconstructed from events | null below the minimum-minutes threshold; never computed for zero minutes |
| role percentile | percentile rank of a per-90 value within the player's role (or role family) group | eligible players of the same role group | group size is reported; groups under the minimum fall back to the role family and are flagged |
| possession_proxy_pct | team passes / (team passes + opponent passes) × 100 | pass attempts of both teams | a pass-share proxy, not timed possession |
| field_tilt_pct | team final-third touches / both teams' final-third touches × 100 | touches with x ≥ 80 | territory proxy from on-ball events |
| ppda | opponent passes with x ≤ 72 / team tackles + interceptions + fouls + failed challenges with x ≥ 48 | defensive actions in the opponent's build-up zone | lower = more defensive actions per opponent pass; an event proxy, not pressing quality |
| xg_diff | sum of StatsBomb xG for − against in a match | — | xG is the provider's model output |
| expected points (xPts) | mean points over 5,000 simulations in which every shot scores with probability equal to its xG | per match | assumes independent shots; ignores game state |
| progressive pass | completed pass starting at x ≥ 48 that ends at least 25% closer to the goal centre | — | project definition; other providers use different thresholds |
| progressive carry | carry ending at least 25% closer to the goal centre, ending at x ≥ 48 and gaining ≥ 5 units | — | project definition |
| Expected Threat (xT) | fixed point of xT(c) = P(shot\|c)·value(shot\|c) + P(move\|c)·Σ T(c→c')·xT(c') on a 16 × 12 grid | passes + carries (moves), shots | project-computed and fitted in-sample on the analysed matches; shot value = mean StatsBomb xG per cell |
| role fit | weighted mean of the role's metric percentiles (weights in config.ROLE_METRIC_WEIGHTS) | weights actually available | transparent heuristic; completeness of the weight set is reported |
| starting-XI slot score | (0.40 role fit + 0.20 recent form + 0.15 sample reliability + 0.15 workload suitability + 0.10 lineup continuity) × position compatibility | 0–100 components | heuristic; 'best' only under these weights and constraints |
| substitute candidate score | 0.35 role compatibility + 0.35 intent fit + 0.15 recent form + 0.15 sample reliability | bench players not yet used | no fitness or injury information exists in the source |
| minutes-based exposure | minutes played in the previous 7 / 14 / 28 days in the analysed matches | — | league minutes only; NOT physical load or fatigue |
| Cliff's delta | P(a > b) − P(a < b), from the Mann–Whitney U | two independent samples | \|δ\| < 0.147 negligible, < 0.33 small, < 0.474 medium, otherwise large |
| epsilon squared | (H − k + 1) / (n − k) from the Kruskal–Wallis H | k groups, n observations | < 0.08 small, < 0.26 medium, otherwise large |


## Table `matches` — 34 rows (source)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| match_id | int64 | 0.0 | 34 |
| match_date | datetime64[ns] | 0.0 | 34 |
| kick_off | object | 0.0 | 7 |
| competition_id | int64 | 0.0 | 1 |
| competition_name | object | 0.0 | 1 |
| country_name | object | 0.0 | 1 |
| season_id | int64 | 0.0 | 1 |
| season_name | object | 0.0 | 1 |
| match_week | int64 | 0.0 | 34 |
| competition_stage | object | 0.0 | 1 |
| home_team_id | int64 | 0.0 | 18 |
| home_team | object | 0.0 | 18 |
| away_team_id | int64 | 0.0 | 18 |
| away_team | object | 0.0 | 18 |
| home_score | int64 | 0.0 | 6 |
| away_score | int64 | 0.0 | 5 |
| stadium | object | 0.0 | 18 |
| referee | object | 0.0 | 16 |
| match_status | object | 0.0 | 1 |
| data_version | object | 0.0 | 1 |
| xy_fidelity_version | object | 0.0 | 1 |
| shot_fidelity_version | object | 0.0 | 1 |
| parsed | bool | 0.0 | 1 |


## Table `managers` — 68 rows (source)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| match_id | int64 | 0.0 | 34 |
| team_id | int64 | 0.0 | 18 |
| team_name | object | 0.0 | 18 |
| manager_id | int64 | 0.0 | 22 |
| manager_name | object | 0.0 | 22 |
| manager_full_name | object | 0.0 | 22 |
| manager_country | object | 0.0 | 6 |
| manager_source | object | 0.0 | 1 |


## Table `squads` — 1,353 rows (source)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| match_id | int64 | 0.0 | 34 |
| team_id | int64 | 0.0 | 18 |
| team_name | object | 0.0 | 18 |
| player_id | int64 | 0.0 | 460 |
| player_name | object | 0.0 | 460 |
| player_full_name | object | 0.0 | 460 |
| jersey_number | int64 | 0.0 | 49 |
| nationality | object | 0.0 | 56 |
| lineup_n_positions | int64 | 0.0 | 7 |
| lineup_first_position | object | 22.5 | 23 |
| lineup_sub_on_position | object | 78.0 | 22 |
| lineup_started | bool | 0.0 | 2 |
| lineup_yellow_cards | int64 | 0.0 | 2 |
| lineup_sending_offs | int64 | 0.0 | 2 |


## Table `events` — 137,765 rows (source)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| event_id | object | 0.0 | 137765.0 |
| match_id | int64 | 0.0 | 34.0 |
| index | int64 | 0.0 | 4893.0 |
| period | int64 | 0.0 | 2.0 |
| minute | int64 | 0.0 | 99.0 |
| second | int64 | 0.0 | 60.0 |
| timestamp | object | 0.0 | 92412.0 |
| type | object | 0.0 | 33.0 |
| team_id | int64 | 0.0 | 18.0 |
| team_name | object | 0.0 | 18.0 |
| player_id | float64 | 0.4 | 372.0 |
| player_name | object | 0.4 | 372.0 |
| position_name | object | 0.4 | 23.0 |
| possession | int64 | 0.0 | 189.0 |
| possession_team_id | int64 | 0.0 | 18.0 |
| play_pattern | object | 0.0 | 9.0 |
| x | float64 | 0.7 | 1197.0 |
| y | float64 | 0.7 | 800.0 |
| end_x | float64 | 47.4 | 1195.0 |
| end_y | float64 | 47.4 | 800.0 |
| duration | float64 | 27.7 | 80561.0 |
| under_pressure | bool | 0.0 | 2.0 |
| counterpress | bool | 0.0 | 2.0 |
| outcome | object | 90.1 | 34.0 |
| pass_recipient_id | float64 | 72.2 | 371.0 |
| pass_recipient_name | object | 72.2 | 371.0 |
| pass_length | float64 | 71.5 | 18583.0 |
| pass_angle | float64 | 71.5 | 29097.0 |
| pass_height | object | 71.5 | 3.0 |
| pass_type | object | 96.0 | 7.0 |
| pass_technique | object | 99.7 | 4.0 |
| pass_body_part | object | 72.7 | 7.0 |
| pass_cross | bool | 0.0 | 2.0 |
| pass_switch | bool | 0.0 | 2.0 |
| pass_through_ball | bool | 0.0 | 2.0 |
| pass_shot_assist | bool | 0.0 | 2.0 |
| pass_goal_assist | bool | 0.0 | 2.0 |
| pass_assisted_shot_id | object | 99.5 | 690.0 |
| shot_xg | float64 | 99.3 | 909.0 |
| shot_type | object | 99.3 | 3.0 |
| shot_body_part | object | 99.3 | 4.0 |
| shot_technique | object | 99.3 | 6.0 |
| shot_end_z | float64 | 99.5 | 70.0 |
| shot_key_pass_id | object | 99.5 | 690.0 |
| duel_type | object | 98.5 | 2.0 |
| aerial_won | bool | 0.0 | 2.0 |
| card | object | 99.9 | 3.0 |
| goalkeeper_type | object | 99.2 | 11.0 |
| sub_replacement_id | float64 | 99.8 | 159.0 |
| sub_replacement_name | object | 99.8 | 159.0 |
| formation | object | 99.9 | 13.0 |
| tactics_lineup | object | 99.9 |  |
| coordinate_system | object | 0.0 | 1.0 |
| elapsed_min | float64 | 0.0 | 6080.0 |


## Table `appearances` — 1,353 rows (derived)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| match_id | int64 | 0.0 | 34 |
| team_id | int64 | 0.0 | 18 |
| team_name | object | 0.0 | 18 |
| player_id | int64 | 0.0 | 460 |
| player_name | object | 0.0 | 460 |
| jersey_number | int64 | 0.0 | 49 |
| nationality | object | 0.0 | 56 |
| lineup_n_positions | int64 | 0.0 | 7 |
| lineup_started | bool | 0.0 | 2 |
| lineup_yellow_cards | int64 | 0.0 | 2 |
| minutes_played | float64 | 0.0 | 578 |
| on_elapsed | float64 | 22.5 | 267 |
| off_elapsed | float64 | 22.5 | 303 |
| start_reason | object | 22.5 | 2 |
| entry_position | object | 22.5 | 23 |
| end_reason | object | 22.5 | 5 |
| sub_on_minute | float64 | 77.8 | 45 |
| sub_off_minute | float64 | 77.4 | 49 |
| n_spells | float64 | 22.5 | 1 |
| appeared | bool | 0.0 | 2 |
| is_starter | bool | 0.0 | 2 |
| sent_off | bool | 0.0 | 2 |
| minutes_flag | object | 0.0 | 2 |
| squad_status | object | 0.0 | 3 |
| match_position | object | 22.5 | 23 |
| match_role | object | 22.5 | 10 |


## Table `spells` — 1,049 rows (derived)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| match_id | int64 | 0.0 | 34 |
| team_id | int64 | 0.0 | 18 |
| player_id | float64 | 0.0 | 373 |
| player_name | object | 0.0 | 373 |
| position | object | 0.0 | 23 |
| start | float64 | 0.0 | 267 |
| end | float64 | 0.0 | 303 |
| start_reason | object | 0.0 | 2 |
| end_reason | object | 0.0 | 5 |
| on_minute | int64 | 0.0 | 46 |
| on_period | int64 | 0.0 | 2 |
| off_minute | float64 | 70.8 | 49 |
| off_period | float64 | 70.8 | 2 |
| minutes | float64 | 0.0 | 577 |


## Table `goals` — 113 rows (derived)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| match_id | int64 | 0.0 | 33 |
| index | int64 | 0.0 | 111 |
| period | int64 | 0.0 | 2 |
| minute | int64 | 0.0 | 67 |
| elapsed_min | float64 | 0.0 | 109 |
| scoring_team_id | float64 | 0.0 | 13 |
| player_name | object | 2.6 | 38 |
| goal_type | object | 0.0 | 3 |


## Table `formations` — 195 rows (source)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| match_id | int64 | 0.0 | 34 |
| team_id | int64 | 0.0 | 18 |
| team_name | object | 0.0 | 18 |
| index | int64 | 0.0 | 128 |
| period | int64 | 0.0 | 2 |
| minute | int64 | 0.0 | 50 |
| elapsed_min | float64 | 0.0 | 124 |
| type | object | 0.0 | 2 |
| formation | object | 0.0 | 13 |
| formation_changed | bool | 0.0 | 2 |


## Table `substitutions_raw` — 301 rows (derived)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| match_id | int64 | 0.0 | 34 |
| event_id | object | 0.0 | 301 |
| index | int64 | 0.0 | 280 |
| period | int64 | 0.0 | 2 |
| minute | int64 | 0.0 | 45 |
| second | int64 | 0.0 | 60 |
| elapsed_min | float64 | 0.0 | 266 |
| team_id | int64 | 0.0 | 18 |
| team_name | object | 0.0 | 18 |
| player_off_id | float64 | 0.0 | 152 |
| player_off_name | object | 0.0 | 152 |
| player_on_id | float64 | 0.0 | 159 |
| player_on_name | object | 0.0 | 159 |
| off_position | object | 0.0 | 22 |
| sub_reason | object | 0.0 | 2 |


## Table `sending_offs` — 5 rows (derived)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| match_id | int64 | 0.0 | 5 |
| index | int64 | 0.0 | 5 |
| period | int64 | 0.0 | 2 |
| minute | int64 | 0.0 | 5 |
| elapsed_min | float64 | 0.0 | 5 |
| team_id | int64 | 0.0 | 5 |
| player_id | float64 | 0.0 | 5 |
| player_name | object | 0.0 | 5 |
| card | object | 0.0 | 2 |


## Table `period_bounds` — 68 rows (derived)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| match_id | int64 | 0.0 | 34 |
| period | int64 | 0.0 | 2 |
| start_clock | float64 | 0.0 | 2 |
| end_clock | float64 | 0.0 | 59 |
| duration | float64 | 0.0 | 57 |
| offset | float64 | 0.0 | 28 |
| bounds_source | object | 0.0 | 1 |


## Table `flags` — 137,765 rows (derived)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| event_id | object | 0.0 | 137765.0 |
| match_id | int64 | 0.0 | 34.0 |
| index | int64 | 0.0 | 4893.0 |
| period | int64 | 0.0 | 2.0 |
| minute | int64 | 0.0 | 99.0 |
| second | int64 | 0.0 | 60.0 |
| timestamp | object | 0.0 | 92412.0 |
| type | object | 0.0 | 33.0 |
| team_id | int64 | 0.0 | 18.0 |
| team_name | object | 0.0 | 18.0 |
| player_id | float64 | 0.4 | 372.0 |
| player_name | object | 0.4 | 372.0 |
| position_name | object | 0.4 | 23.0 |
| possession | int64 | 0.0 | 189.0 |
| possession_team_id | int64 | 0.0 | 18.0 |
| play_pattern | object | 0.0 | 9.0 |
| x | float64 | 0.7 | 1197.0 |
| y | float64 | 0.7 | 800.0 |
| end_x | float64 | 47.4 | 1195.0 |
| end_y | float64 | 47.4 | 800.0 |
| duration | float64 | 27.7 | 80561.0 |
| under_pressure | bool | 0.0 | 2.0 |
| counterpress | bool | 0.0 | 2.0 |
| outcome | object | 90.1 | 34.0 |
| pass_recipient_id | float64 | 72.2 | 371.0 |
| pass_recipient_name | object | 72.2 | 371.0 |
| pass_length | float64 | 71.5 | 18583.0 |
| pass_angle | float64 | 71.5 | 29097.0 |
| pass_height | object | 71.5 | 3.0 |
| pass_type | object | 96.0 | 7.0 |
| pass_technique | object | 99.7 | 4.0 |
| pass_body_part | object | 72.7 | 7.0 |
| pass_cross | bool | 0.0 | 2.0 |
| pass_switch | bool | 0.0 | 2.0 |
| pass_through_ball | bool | 0.0 | 2.0 |
| pass_shot_assist | bool | 0.0 | 2.0 |
| pass_goal_assist | bool | 0.0 | 2.0 |
| pass_assisted_shot_id | object | 99.5 | 690.0 |
| shot_xg | float64 | 99.3 | 909.0 |
| shot_type | object | 99.3 | 3.0 |
| shot_body_part | object | 99.3 | 4.0 |
| shot_technique | object | 99.3 | 6.0 |
| shot_end_z | float64 | 99.5 | 70.0 |
| shot_key_pass_id | object | 99.5 | 690.0 |
| duel_type | object | 98.5 | 2.0 |
| aerial_won | bool | 0.0 | 2.0 |
| card | object | 99.9 | 3.0 |
| goalkeeper_type | object | 99.2 | 11.0 |
| sub_replacement_id | float64 | 99.8 | 159.0 |
| sub_replacement_name | object | 99.8 | 159.0 |
| formation | object | 99.9 | 13.0 |
| tactics_lineup | object | 99.9 |  |
| coordinate_system | object | 0.0 | 1.0 |
| elapsed_min | float64 | 0.0 | 6080.0 |
| passes | int32 | 0.0 | 2.0 |
| passes_completed | int32 | 0.0 | 2.0 |
| long_passes | int32 | 0.0 | 2.0 |
| long_passes_completed | int32 | 0.0 | 2.0 |
| progressive_passes | int32 | 0.0 | 2.0 |
| final_third_passes | int32 | 0.0 | 2.0 |
| box_passes | int32 | 0.0 | 2.0 |
| crosses_completed | int32 | 0.0 | 2.0 |
| through_balls | int32 | 0.0 | 2.0 |
| key_passes | int32 | 0.0 | 2.0 |
| assists | int32 | 0.0 | 2.0 |
| shots | int32 | 0.0 | 2.0 |
| shots_on_target | int32 | 0.0 | 2.0 |
| goals | int32 | 0.0 | 2.0 |
| xg | float64 | 0.0 | 910.0 |
| npxg | float64 | 0.0 | 909.0 |
| xa | float64 | 0.0 | 691.0 |
| progressive_carries | int32 | 0.0 | 2.0 |
| carries_into_final_third | int32 | 0.0 | 2.0 |
| carries_into_box | int32 | 0.0 | 2.0 |
| dribbles | int32 | 0.0 | 2.0 |
| dribbles_completed | int32 | 0.0 | 2.0 |
| touches | int32 | 0.0 | 2.0 |
| box_touches | int32 | 0.0 | 2.0 |
| final_third_touches | int32 | 0.0 | 2.0 |
| tackles | int32 | 0.0 | 2.0 |
| tackles_won | int32 | 0.0 | 2.0 |
| interceptions | int32 | 0.0 | 2.0 |
| blocks | int32 | 0.0 | 2.0 |
| clearances | int32 | 0.0 | 2.0 |
| ball_recoveries | int32 | 0.0 | 2.0 |
| pressures | int32 | 0.0 | 2.0 |
| counterpressures | int32 | 0.0 | 2.0 |
| aerials_won | int32 | 0.0 | 2.0 |
| aerials_lost | int32 | 0.0 | 2.0 |
| defensive_actions | int32 | 0.0 | 2.0 |
| fouls_committed | int32 | 0.0 | 2.0 |
| fouls_won | int32 | 0.0 | 2.0 |
| yellow_cards | int32 | 0.0 | 2.0 |
| red_cards | int32 | 0.0 | 2.0 |
| turnovers | int32 | 0.0 | 2.0 |
| gk_saves | int32 | 0.0 | 2.0 |
| gk_claims | int32 | 0.0 | 2.0 |
| gk_goals_conceded | int32 | 0.0 | 2.0 |


## Table `pms` — 1,049 rows (derived)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| match_id | int64 | 0.0 | 34 |
| team_id | int64 | 0.0 | 18 |
| team_name | object | 0.0 | 18 |
| player_id | int64 | 0.0 | 373 |
| player_name | object | 0.0 | 373 |
| jersey_number | int64 | 0.0 | 48 |
| nationality | object | 0.0 | 51 |
| lineup_n_positions | int64 | 0.0 | 6 |
| lineup_started | bool | 0.0 | 2 |
| lineup_yellow_cards | int64 | 0.0 | 2 |
| minutes_played | float64 | 0.0 | 577 |
| on_elapsed | float64 | 0.0 | 267 |
| off_elapsed | float64 | 0.0 | 303 |
| start_reason | object | 0.0 | 2 |
| entry_position | object | 0.0 | 23 |
| end_reason | object | 0.0 | 5 |
| sub_on_minute | float64 | 71.3 | 45 |
| sub_off_minute | float64 | 70.8 | 49 |
| n_spells | float64 | 0.0 | 1 |
| appeared | bool | 0.0 | 1 |
| is_starter | bool | 0.0 | 2 |
| sent_off | bool | 0.0 | 2 |
| minutes_flag | object | 0.0 | 1 |
| squad_status | object | 0.0 | 2 |
| match_position | object | 0.0 | 23 |
| match_role | object | 0.0 | 10 |
| goals | float64 | 0.0 | 4 |
| npxg | float64 | 0.0 | 483 |
| xg | float64 | 0.0 | 484 |
| xa | float64 | 0.0 | 392 |
| shots | float64 | 0.0 | 11 |
| shots_on_target | float64 | 0.0 | 5 |
| assists | float64 | 0.0 | 3 |
| key_passes | float64 | 0.0 | 9 |
| passes | float64 | 0.0 | 123 |
| progressive_passes | float64 | 0.0 | 14 |
| final_third_passes | float64 | 0.0 | 23 |
| box_passes | float64 | 0.0 | 10 |
| crosses_completed | float64 | 0.0 | 5 |
| through_balls | float64 | 0.0 | 5 |
| progressive_carries | float64 | 0.0 | 13 |
| carries_into_final_third | float64 | 0.0 | 11 |
| carries_into_box | float64 | 0.0 | 8 |
| dribbles | float64 | 0.0 | 10 |
| dribbles_completed | float64 | 0.0 | 7 |
| touches | float64 | 0.0 | 303 |
| box_touches | float64 | 0.0 | 39 |
| final_third_touches | float64 | 0.0 | 131 |
| tackles | float64 | 0.0 | 9 |
| tackles_won | float64 | 0.0 | 6 |
| interceptions | float64 | 0.0 | 8 |
| blocks | float64 | 0.0 | 11 |
| clearances | float64 | 0.0 | 13 |
| ball_recoveries | float64 | 0.0 | 13 |
| pressures | float64 | 0.0 | 44 |
| counterpressures | float64 | 0.0 | 14 |
| aerials_won | float64 | 0.0 | 10 |
| defensive_actions | float64 | 0.0 | 27 |
| fouls_committed | float64 | 0.0 | 7 |
| fouls_won | float64 | 0.0 | 7 |
| turnovers | float64 | 0.0 | 13 |
| gk_saves | float64 | 0.0 | 10 |
| gk_claims | float64 | 0.0 | 8 |
| passes_completed | float64 | 0.0 | 119 |
| long_passes | float64 | 0.0 | 34 |
| long_passes_completed | float64 | 0.0 | 23 |
| aerials_lost | float64 | 0.0 | 10 |
| yellow_cards | float64 | 0.0 | 2 |
| red_cards | float64 | 0.0 | 2 |
| gk_goals_conceded | float64 | 0.0 | 6 |
| match_date | datetime64[ns] | 0.0 | 34 |
| home_team_id | int64 | 0.0 | 18 |
| away_team_id | int64 | 0.0 | 18 |
| home_team | object | 0.0 | 18 |
| away_team | object | 0.0 | 18 |
| home_away | object | 0.0 | 2 |
| opponent | object | 0.0 | 18 |


## Table `season` — 377 rows (derived)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| team_id | int64 | 0.0 | 18 |
| player_id | int64 | 0.0 | 373 |
| goals | float64 | 0.0 | 11 |
| npxg | float64 | 0.0 | 181 |
| xg | float64 | 0.0 | 181 |
| xa | float64 | 0.0 | 155 |
| shots | float64 | 0.0 | 23 |
| shots_on_target | float64 | 0.0 | 17 |
| assists | float64 | 0.0 | 9 |
| key_passes | float64 | 0.0 | 19 |
| passes | float64 | 0.0 | 130 |
| progressive_passes | float64 | 0.0 | 23 |
| final_third_passes | float64 | 0.0 | 25 |
| box_passes | float64 | 0.0 | 21 |
| crosses_completed | float64 | 0.0 | 13 |
| through_balls | float64 | 0.0 | 12 |
| progressive_carries | float64 | 0.0 | 27 |
| carries_into_final_third | float64 | 0.0 | 25 |
| carries_into_box | float64 | 0.0 | 15 |
| dribbles | float64 | 0.0 | 22 |
| dribbles_completed | float64 | 0.0 | 15 |
| touches | float64 | 0.0 | 232 |
| box_touches | float64 | 0.0 | 46 |
| final_third_touches | float64 | 0.0 | 108 |
| tackles | float64 | 0.0 | 25 |
| tackles_won | float64 | 0.0 | 20 |
| interceptions | float64 | 0.0 | 19 |
| blocks | float64 | 0.0 | 29 |
| clearances | float64 | 0.0 | 27 |
| ball_recoveries | float64 | 0.0 | 32 |
| pressures | float64 | 0.0 | 77 |
| counterpressures | float64 | 0.0 | 33 |
| aerials_won | float64 | 0.0 | 24 |
| defensive_actions | float64 | 0.0 | 58 |
| fouls_committed | float64 | 0.0 | 22 |
| fouls_won | float64 | 0.0 | 20 |
| turnovers | float64 | 0.0 | 27 |
| gk_saves | float64 | 0.0 | 12 |
| gk_claims | float64 | 0.0 | 12 |
| passes_completed | float64 | 0.0 | 114 |
| long_passes | float64 | 0.0 | 55 |
| long_passes_completed | float64 | 0.0 | 39 |
| aerials_lost | float64 | 0.0 | 22 |
| yellow_cards | float64 | 0.0 | 7 |
| red_cards | float64 | 0.0 | 2 |
| gk_goals_conceded | float64 | 0.0 | 9 |
| minutes_played | float64 | 0.0 | 305 |
| appearances | int64 | 0.0 | 15 |
| starts | int64 | 0.0 | 17 |
| sub_appearances | int64 | 0.0 | 13 |
| subbed_off | int64 | 0.0 | 15 |
| player_name | object | 0.0 | 373 |
| team_name | object | 0.0 | 18 |
| last_appearance | datetime64[ns] | 0.0 | 34 |
| unused_sub_count | int32 | 0.0 | 14 |
| matchday_squads | int64 | 0.0 | 16 |
| primary_position | object | 0.0 | 23 |
| primary_role | object | 0.0 | 10 |
| role_family | object | 0.0 | 4 |
| starts_pct | float64 | 0.0 | 21 |
| avg_minutes | float64 | 0.0 | 305 |
| goals_p90 | float64 | 0.0 | 38 |
| npxg_p90 | float64 | 0.0 | 181 |
| xg_p90 | float64 | 0.0 | 181 |
| xa_p90 | float64 | 0.0 | 155 |
| shots_p90 | float64 | 0.0 | 170 |
| shots_on_target_p90 | float64 | 0.0 | 94 |
| assists_p90 | float64 | 0.0 | 33 |
| key_passes_p90 | float64 | 0.0 | 151 |
| passes_p90 | float64 | 0.0 | 369 |
| progressive_passes_p90 | float64 | 0.0 | 239 |
| final_third_passes_p90 | float64 | 0.0 | 250 |
| box_passes_p90 | float64 | 0.0 | 165 |
| crosses_completed_p90 | float64 | 0.0 | 81 |
| through_balls_p90 | float64 | 0.0 | 58 |
| progressive_carries_p90 | float64 | 0.0 | 206 |
| carries_into_final_third_p90 | float64 | 0.0 | 186 |
| carries_into_box_p90 | float64 | 0.0 | 97 |
| dribbles_p90 | float64 | 0.0 | 174 |
| dribbles_completed_p90 | float64 | 0.0 | 127 |
| touches_p90 | float64 | 0.0 | 376 |
| box_touches_p90 | float64 | 0.0 | 263 |
| final_third_touches_p90 | float64 | 0.0 | 334 |
| tackles_p90 | float64 | 0.0 | 260 |
| tackles_won_p90 | float64 | 0.0 | 219 |
| interceptions_p90 | float64 | 0.0 | 198 |
| blocks_p90 | float64 | 0.0 | 255 |
| clearances_p90 | float64 | 0.0 | 218 |
| ball_recoveries_p90 | float64 | 0.0 | 309 |
| pressures_p90 | float64 | 0.0 | 350 |
| counterpressures_p90 | float64 | 0.0 | 288 |
| aerials_won_p90 | float64 | 0.0 | 185 |
| defensive_actions_p90 | float64 | 0.0 | 345 |
| fouls_committed_p90 | float64 | 0.0 | 212 |
| fouls_won_p90 | float64 | 0.0 | 175 |
| turnovers_p90 | float64 | 0.0 | 259 |
| gk_saves_p90 | float64 | 0.0 | 24 |
| gk_claims_p90 | float64 | 0.0 | 23 |
| pass_completion_pct | float64 | 1.3 | 222 |
| long_pass_completion_pct | float64 | 11.1 | 89 |
| tackle_success_pct | float64 | 29.7 | 33 |
| dribble_success_pct | float64 | 52.2 | 27 |
| goals_minus_xg | float64 | 0.0 | 181 |
| eligible | bool | 0.0 | 2 |
| sample_reliability | float64 | 0.0 | 289 |
| coverage_label | object | 0.0 | 3 |


## Table `season_pct` — 377 rows (derived)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| team_id | int64 | 0.0 | 18 |
| player_id | int64 | 0.0 | 373 |
| goals | float64 | 0.0 | 11 |
| npxg | float64 | 0.0 | 181 |
| xg | float64 | 0.0 | 181 |
| xa | float64 | 0.0 | 155 |
| shots | float64 | 0.0 | 23 |
| shots_on_target | float64 | 0.0 | 17 |
| assists | float64 | 0.0 | 9 |
| key_passes | float64 | 0.0 | 19 |
| passes | float64 | 0.0 | 130 |
| progressive_passes | float64 | 0.0 | 23 |
| final_third_passes | float64 | 0.0 | 25 |
| box_passes | float64 | 0.0 | 21 |
| crosses_completed | float64 | 0.0 | 13 |
| through_balls | float64 | 0.0 | 12 |
| progressive_carries | float64 | 0.0 | 27 |
| carries_into_final_third | float64 | 0.0 | 25 |
| carries_into_box | float64 | 0.0 | 15 |
| dribbles | float64 | 0.0 | 22 |
| dribbles_completed | float64 | 0.0 | 15 |
| touches | float64 | 0.0 | 232 |
| box_touches | float64 | 0.0 | 46 |
| final_third_touches | float64 | 0.0 | 108 |
| tackles | float64 | 0.0 | 25 |
| tackles_won | float64 | 0.0 | 20 |
| interceptions | float64 | 0.0 | 19 |
| blocks | float64 | 0.0 | 29 |
| clearances | float64 | 0.0 | 27 |
| ball_recoveries | float64 | 0.0 | 32 |
| pressures | float64 | 0.0 | 77 |
| counterpressures | float64 | 0.0 | 33 |
| aerials_won | float64 | 0.0 | 24 |
| defensive_actions | float64 | 0.0 | 58 |
| fouls_committed | float64 | 0.0 | 22 |
| fouls_won | float64 | 0.0 | 20 |
| turnovers | float64 | 0.0 | 27 |
| gk_saves | float64 | 0.0 | 12 |
| gk_claims | float64 | 0.0 | 12 |
| passes_completed | float64 | 0.0 | 114 |
| long_passes | float64 | 0.0 | 55 |
| long_passes_completed | float64 | 0.0 | 39 |
| aerials_lost | float64 | 0.0 | 22 |
| yellow_cards | float64 | 0.0 | 7 |
| red_cards | float64 | 0.0 | 2 |
| gk_goals_conceded | float64 | 0.0 | 9 |
| minutes_played | float64 | 0.0 | 305 |
| appearances | int64 | 0.0 | 15 |
| starts | int64 | 0.0 | 17 |
| sub_appearances | int64 | 0.0 | 13 |
| subbed_off | int64 | 0.0 | 15 |
| player_name | object | 0.0 | 373 |
| team_name | object | 0.0 | 18 |
| last_appearance | datetime64[ns] | 0.0 | 34 |
| unused_sub_count | int32 | 0.0 | 14 |
| matchday_squads | int64 | 0.0 | 16 |
| primary_position | object | 0.0 | 23 |
| primary_role | object | 0.0 | 10 |
| role_family | object | 0.0 | 4 |
| starts_pct | float64 | 0.0 | 21 |
| avg_minutes | float64 | 0.0 | 305 |
| goals_p90 | float64 | 0.0 | 38 |
| npxg_p90 | float64 | 0.0 | 181 |
| xg_p90 | float64 | 0.0 | 181 |
| xa_p90 | float64 | 0.0 | 155 |
| shots_p90 | float64 | 0.0 | 170 |
| shots_on_target_p90 | float64 | 0.0 | 94 |
| assists_p90 | float64 | 0.0 | 33 |
| key_passes_p90 | float64 | 0.0 | 151 |
| passes_p90 | float64 | 0.0 | 369 |
| progressive_passes_p90 | float64 | 0.0 | 239 |
| final_third_passes_p90 | float64 | 0.0 | 250 |
| box_passes_p90 | float64 | 0.0 | 165 |
| crosses_completed_p90 | float64 | 0.0 | 81 |
| through_balls_p90 | float64 | 0.0 | 58 |
| progressive_carries_p90 | float64 | 0.0 | 206 |
| carries_into_final_third_p90 | float64 | 0.0 | 186 |
| carries_into_box_p90 | float64 | 0.0 | 97 |
| dribbles_p90 | float64 | 0.0 | 174 |
| dribbles_completed_p90 | float64 | 0.0 | 127 |
| touches_p90 | float64 | 0.0 | 376 |
| box_touches_p90 | float64 | 0.0 | 263 |
| final_third_touches_p90 | float64 | 0.0 | 334 |
| tackles_p90 | float64 | 0.0 | 260 |
| tackles_won_p90 | float64 | 0.0 | 219 |
| interceptions_p90 | float64 | 0.0 | 198 |
| blocks_p90 | float64 | 0.0 | 255 |
| clearances_p90 | float64 | 0.0 | 218 |
| ball_recoveries_p90 | float64 | 0.0 | 309 |
| pressures_p90 | float64 | 0.0 | 350 |
| counterpressures_p90 | float64 | 0.0 | 288 |
| aerials_won_p90 | float64 | 0.0 | 185 |
| defensive_actions_p90 | float64 | 0.0 | 345 |
| fouls_committed_p90 | float64 | 0.0 | 212 |
| fouls_won_p90 | float64 | 0.0 | 175 |
| turnovers_p90 | float64 | 0.0 | 259 |
| gk_saves_p90 | float64 | 0.0 | 24 |
| gk_claims_p90 | float64 | 0.0 | 23 |
| pass_completion_pct | float64 | 1.3 | 222 |
| long_pass_completion_pct | float64 | 11.1 | 89 |
| tackle_success_pct | float64 | 29.7 | 33 |
| dribble_success_pct | float64 | 52.2 | 27 |
| goals_minus_xg | float64 | 0.0 | 181 |
| eligible | bool | 0.0 | 2 |
| sample_reliability | float64 | 0.0 | 289 |
| coverage_label | object | 0.0 | 3 |
| benchmark_level | object | 0.0 | 2 |
| benchmark_group | object | 0.0 | 8 |
| benchmark_n | float64 | 0.0 | 5 |
| aerials_won_p90_pct | float64 | 0.0 | 89 |
| ball_recoveries_p90_pct | float64 | 0.0 | 100 |
| box_touches_p90_pct | float64 | 0.0 | 104 |
| clearances_p90_pct | float64 | 0.0 | 95 |
| crosses_completed_p90_pct | float64 | 0.0 | 33 |
| dribbles_completed_p90_pct | float64 | 0.0 | 50 |
| final_third_passes_p90_pct | float64 | 0.0 | 98 |
| gk_claims_p90_pct | float64 | 0.0 | 22 |
| gk_saves_p90_pct | float64 | 0.0 | 21 |
| goals_p90_pct | float64 | 0.0 | 29 |
| interceptions_p90_pct | float64 | 0.0 | 83 |
| key_passes_p90_pct | float64 | 0.0 | 68 |
| long_pass_completion_pct_pct | float64 | 11.1 | 92 |
| pass_completion_pct_pct | float64 | 1.3 | 105 |
| pressures_p90_pct | float64 | 0.0 | 107 |
| progressive_carries_p90_pct | float64 | 0.0 | 68 |
| progressive_passes_p90_pct | float64 | 0.0 | 94 |
| shots_p90_pct | float64 | 0.0 | 73 |
| tackles_won_p90_pct | float64 | 0.0 | 90 |
| xa_p90_pct | float64 | 0.0 | 76 |
| xg_p90_pct | float64 | 0.0 | 83 |
| defensive_actions_p90_pct | float64 | 0.0 | 95 |
| touches_p90_pct | float64 | 0.0 | 106 |
| turnovers_p90_pct | float64 | 0.0 | 94 |
| small_benchmark_warning | bool | 0.0 | 1 |


## Table `team_stats` — 68 rows (derived)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| match_id | int64 | 0.0 | 34 |
| team_id | int64 | 0.0 | 18 |
| shots | int32 | 0.0 | 26 |
| shots_on_target | int32 | 0.0 | 13 |
| xg | float64 | 0.0 | 68 |
| npxg | float64 | 0.0 | 68 |
| passes | int32 | 0.0 | 66 |
| passes_completed | int32 | 0.0 | 67 |
| progressive_passes | int32 | 0.0 | 36 |
| progressive_carries | int32 | 0.0 | 32 |
| final_third_passes | int32 | 0.0 | 40 |
| box_passes | int32 | 0.0 | 24 |
| pressures | int32 | 0.0 | 55 |
| counterpressures | int32 | 0.0 | 31 |
| defensive_actions | int32 | 0.0 | 37 |
| final_third_touches | int32 | 0.0 | 68 |
| box_touches | int32 | 0.0 | 53 |
| touches | int32 | 0.0 | 66 |
| crosses_completed | int32 | 0.0 | 11 |
| fouls_committed | int32 | 0.0 | 15 |
| yellow_cards | int32 | 0.0 | 6 |
| red_cards | int32 | 0.0 | 2 |
| set_piece_shots | float64 | 0.0 | 18 |
| opponent_id | int64 | 0.0 | 18 |
| team_name | object | 0.0 | 18 |
| opponent | object | 0.0 | 18 |
| home_away | object | 0.0 | 2 |
| match_date | datetime64[ns] | 0.0 | 34 |
| ppda | float64 | 0.0 | 68 |
| shots_against | int32 | 0.0 | 26 |
| shots_on_target_against | int32 | 0.0 | 13 |
| xg_against | float64 | 0.0 | 68 |
| passes_against | int32 | 0.0 | 66 |
| final_third_touches_against | int32 | 0.0 | 68 |
| goals_for | int64 | 0.0 | 6 |
| goals_against | int64 | 0.0 | 6 |
| goal_diff | int64 | 0.0 | 11 |
| result | object | 0.0 | 3 |
| points | int64 | 0.0 | 3 |
| possession_proxy_pct | float64 | 0.0 | 68 |
| field_tilt_pct | float64 | 0.0 | 68 |
| pass_completion_pct | float64 | 0.0 | 68 |
| xg_diff | float64 | 0.0 | 68 |
| starting_formation | object | 0.0 | 12 |
| in_match_formation_changes | int64 | 0.0 | 4 |
| manager_id | int64 | 0.0 | 22 |
| manager_name | object | 0.0 | 22 |


## Table `workload` — 1,353 rows (derived)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| match_id | int64 | 0.0 | 34 |
| team_id | int64 | 0.0 | 18 |
| player_id | int64 | 0.0 | 460 |
| minutes_prev_7d | float64 | 0.0 | 165 |
| minutes_prev_14d | float64 | 0.0 | 302 |
| minutes_prev_28d | float64 | 0.0 | 418 |
| rest_days | float64 | 39.2 | 64 |
| team_rest_days | float64 | 26.5 | 16 |
| started_prev_match | object | 26.5 | 2 |
| consecutive_starts_before | int64 | 0.0 | 30 |
| starts_before | int64 | 0.0 | 33 |
| apps_before | int64 | 0.0 | 33 |
| prior_team_matches | int64 | 0.0 | 34 |
| start_share_before | float64 | 26.5 | 193 |
| minutes_share_before | float64 | 26.5 | 729 |


## Table `subs` — 301 rows (derived)

| column | dtype | missing_pct | distinct |
| --- | --- | --- | --- |
| match_id | int64 | 0.0 | 34 |
| event_id | object | 0.0 | 301 |
| index | int64 | 0.0 | 280 |
| period | int64 | 0.0 | 2 |
| minute | int64 | 0.0 | 45 |
| second | int64 | 0.0 | 60 |
| elapsed_min | float64 | 0.0 | 266 |
| team_id | int64 | 0.0 | 18 |
| team_name | object | 0.0 | 18 |
| player_off_id | float64 | 0.0 | 152 |
| player_off_name | object | 0.0 | 152 |
| player_on_id | float64 | 0.0 | 159 |
| player_on_name | object | 0.0 | 159 |
| off_position | object | 0.0 | 22 |
| sub_reason | object | 0.0 | 2 |
| home_away | object | 0.0 | 2 |
| opponent_id | int64 | 0.0 | 18 |
| opponent | object | 0.0 | 18 |
| match_date | datetime64[ns] | 0.0 | 34 |
| team_score | int64 | 0.0 | 5 |
| opponent_score | int64 | 0.0 | 5 |
| goal_diff | int64 | 0.0 | 9 |
| game_state | object | 0.0 | 3 |
| man_advantage | int64 | 0.0 | 3 |
| timing_band | object | 0.0 | 6 |
| match_phase | object | 0.0 | 5 |
| on_position | object | 0.0 | 22 |
| off_role | object | 0.0 | 9 |
| on_role | object | 0.0 | 9 |
| like_for_like | bool | 0.0 | 2 |
| player_on_display | object | 0.0 | 159 |
| player_off_display | object | 0.0 | 152 |
| sub_number | int64 | 0.0 | 5 |
| window_number | int64 | 0.0 | 4 |
| max_subs_allowed | int32 | 0.0 | 1 |
| subs_remaining_after | int64 | 0.0 | 5 |
| rule_source | object | 0.0 | 1 |
| multi_sub_window | bool | 0.0 | 2 |
| manager_id | int64 | 0.0 | 22 |
| manager_name | object | 0.0 | 22 |
| identity_check | object | 0.0 | 1 |

