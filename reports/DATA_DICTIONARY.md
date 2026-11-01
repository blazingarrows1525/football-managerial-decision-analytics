# Data Dictionary

> Auto-generated from the executed run (2026-11-01 17:30 UTC). Types and missingness are measured, not assumed.

## Metric definitions
| metric | definition | numerator | denominator | unit | source_fields |
|---|---|---|---|---|---|
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

## Table `matches` — 34 rows
| field | dtype | missing_pct | description / derivation |
|---|---|---|---|
| match_id | int64 | 0.0 | StatsBomb match id (int) |
| match_date | datetime64[ns] | 0.0 | kick-off date (local date, no tz) |
| kick_off | object | 0.0 |  |
| competition_id | int64 | 0.0 |  |
| competition_name | object | 0.0 |  |
| country_name | object | 0.0 |  |
| season_id | int64 | 0.0 |  |
| season_name | object | 0.0 |  |
| match_week | int64 | 0.0 |  |
| competition_stage | object | 0.0 |  |
| home_team_id | int64 | 0.0 | StatsBomb team ids |
| home_team | object | 0.0 |  |
| away_team_id | int64 | 0.0 | StatsBomb team ids |
| away_team | object | 0.0 |  |
| home_score | int64 | 0.0 | final score (source) |
| away_score | int64 | 0.0 | final score (source) |
| stadium | object | 0.0 | names when supplied; never imputed |
| referee | object | 0.0 | names when supplied; never imputed |
| match_status | object | 0.0 |  |
| data_version | object | 0.0 |  |
| xy_fidelity_version | object | 0.0 |  |
| shot_fidelity_version | object | 0.0 |  |
| parsed | bool | 0.0 | events file parsed (bool) |

## Table `managers` — 68 rows
| field | dtype | missing_pct | description / derivation |
|---|---|---|---|
| match_id | int64 | 0.0 |  |
| team_id | int64 | 0.0 |  |
| team_name | object | 0.0 |  |
| manager_id | int64 | 0.0 |  |
| manager_name | object | 0.0 |  |
| manager_full_name | object | 0.0 |  |
| manager_country | object | 0.0 |  |
| manager_source | object | 0.0 |  |

## Table `appearances` — 1,353 rows
| field | dtype | missing_pct | description / derivation |
|---|---|---|---|
| match_id | int64 | 0.0 |  |
| team_id | int64 | 0.0 |  |
| team_name | object | 0.0 |  |
| player_id | int64 | 0.0 |  |
| player_name | object | 0.0 |  |
| jersey_number | int64 | 0.0 |  |
| nationality | object | 0.0 |  |
| lineup_n_positions | int64 | 0.0 |  |
| lineup_started | bool | 0.0 |  |
| lineup_yellow_cards | int64 | 0.0 |  |
| minutes_played | float64 | 0.0 | actual playing time incl. stoppage, periods 1-4, from event timeline |
| on_elapsed | float64 | 22.5 | elapsed playing minutes of entry/exit |
| off_elapsed | float64 | 22.5 | elapsed playing minutes of entry/exit |
| start_reason | object | 22.5 |  |
| entry_position | object | 22.5 |  |
| end_reason | object | 22.5 |  |
| sub_on_minute | float64 | 77.8 | clock minute of entry/exit (stoppage counted, 45+2 = 47) |
| sub_off_minute | float64 | 77.4 | clock minute of entry/exit (stoppage counted, 45+2 = 47) |
| n_spells | float64 | 22.5 |  |
| appeared | bool | 0.0 |  |
| is_starter | bool | 0.0 |  |
| sent_off | bool | 0.0 |  |
| minutes_flag | object | 0.0 | derived_from_events / unused_substitute / unknown_* |
| squad_status | object | 0.0 | starter / used_substitute / unused_substitute |
| match_position | object | 22.5 | most frequent event position in the match; match_role = project role code |
| match_role | object | 22.5 |  |

## Table `events` — 137,765 rows
| field | dtype | missing_pct | description / derivation |
|---|---|---|---|
| event_id | object | 0.0 |  |
| match_id | int64 | 0.0 |  |
| index | int64 | 0.0 |  |
| period | int64 | 0.0 |  |
| minute | int64 | 0.0 |  |
| second | int64 | 0.0 |  |
| timestamp | object | 0.0 |  |
| type | object | 0.0 |  |
| team_id | int64 | 0.0 |  |
| team_name | object | 0.0 |  |
| player_id | float64 | 0.4 |  |
| player_name | object | 0.4 |  |
| position_name | object | 0.4 |  |
| possession | int64 | 0.0 |  |
| possession_team_id | int64 | 0.0 |  |
| play_pattern | object | 0.0 |  |
| x | float64 | 0.7 |  |
| y | float64 | 0.7 |  |
| end_x | float64 | 47.4 |  |
| end_y | float64 | 47.4 |  |
| duration | float64 | 27.7 |  |
| under_pressure | bool | 0.0 |  |
| counterpress | bool | 0.0 |  |
| outcome | object | 90.1 |  |
| pass_recipient_id | float64 | 72.2 |  |
| pass_recipient_name | object | 72.2 |  |
| pass_length | float64 | 71.5 |  |
| pass_angle | float64 | 71.5 |  |
| pass_height | object | 71.5 |  |
| pass_type | object | 96.0 |  |
| pass_technique | object | 99.7 |  |
| pass_body_part | object | 72.7 |  |
| pass_cross | bool | 0.0 |  |
| pass_switch | bool | 0.0 |  |
| pass_through_ball | bool | 0.0 |  |
| pass_shot_assist | bool | 0.0 |  |
| pass_goal_assist | bool | 0.0 |  |
| pass_assisted_shot_id | object | 99.5 |  |
| shot_xg | float64 | 99.3 |  |
| shot_type | object | 99.3 |  |
| shot_body_part | object | 99.3 |  |
| shot_technique | object | 99.3 |  |
| shot_end_z | float64 | 99.5 |  |
| shot_key_pass_id | object | 99.5 |  |
| duel_type | object | 98.5 |  |
| aerial_won | bool | 0.0 |  |
| card | object | 99.9 |  |
| goalkeeper_type | object | 99.2 |  |
| sub_replacement_id | float64 | 99.8 |  |
| sub_replacement_name | object | 99.8 |  |
| formation | object | 99.9 |  |
| coordinate_system | object | 0.0 |  |
| elapsed_min | float64 | 0.0 |  |

## Table `substitutions` — 301 rows
| field | dtype | missing_pct | description / derivation |
|---|---|---|---|
| match_id | int64 | 0.0 |  |
| event_id | object | 0.0 |  |
| index | int64 | 0.0 |  |
| period | int64 | 0.0 |  |
| minute | int64 | 0.0 |  |
| second | int64 | 0.0 |  |
| elapsed_min | float64 | 0.0 |  |
| team_id | int64 | 0.0 |  |
| team_name | object | 0.0 |  |
| player_off_id | float64 | 0.0 |  |
| player_off_name | object | 0.0 |  |
| player_on_id | float64 | 0.0 |  |
| player_on_name | object | 0.0 |  |
| off_position | object | 0.0 |  |
| sub_reason | object | 0.0 |  |
| home_away | object | 0.0 |  |
| opponent_id | int64 | 0.0 |  |
| opponent | object | 0.0 |  |
| match_date | datetime64[ns] | 0.0 |  |
| team_score | int64 | 0.0 | team-perspective score strictly before the event |
| opponent_score | int64 | 0.0 | team-perspective score strictly before the event |
| goal_diff | int64 | 0.0 | team-perspective score strictly before the event |
| game_state | object | 0.0 | team-perspective score strictly before the event |
| man_advantage | int64 | 0.0 | + = opponent had more sending-offs before the event |
| timing_band | object | 0.0 | configurable analytical band |
| match_phase | object | 0.0 |  |
| on_position | object | 0.0 |  |
| off_role | object | 0.0 |  |
| on_role | object | 0.0 |  |
| like_for_like | bool | 0.0 |  |
| sub_number | int64 | 0.0 |  |
| window_number | int64 | 0.0 | 0 = interval change; rules user-configured |
| max_subs_allowed | int32 | 0.0 |  |
| subs_remaining_after | int64 | 0.0 |  |
| rule_source | object | 0.0 |  |
| multi_sub_window | bool | 0.0 |  |
| manager_id | int64 | 0.0 |  |
| manager_name | object | 0.0 |  |
| identity_check | object | 0.0 | players resolved against matchday squad |

## Table `player_season` — 377 rows
| field | dtype | missing_pct | description / derivation |
|---|---|---|---|
| team_id | int64 | 0.0 |  |
| player_id | int64 | 0.0 |  |
| goals | float64 | 0.0 | Shots with outcome Goal in periods 1-4 (shoot-out excluded) |
| npxg | float64 | 0.0 | Sum of StatsBomb xG on non-penalty shots |
| xg | float64 | 0.0 | Sum of StatsBomb xG on all shots (periods 1-4) |
| xa | float64 | 0.0 | xG of shots assisted by the player's passes (pass.assisted_shot_id) |
| shots | float64 | 0.0 | Shot events (periods 1-4) |
| shots_on_target | float64 | 0.0 | Shots with outcome Goal / Saved / Saved To Post |
| assists | float64 | 0.0 | Passes flagged goal_assist by StatsBomb |
| key_passes | float64 | 0.0 | Passes flagged shot_assist or goal_assist |
| passes | float64 | 0.0 | Pass attempts |
| progressive_passes | float64 | 0.0 | PROJECT DEFINITION: completed open-play pass starting outside the defending 40% (x >= 48) and ending >=25% closer to the opponent goal centre |
| final_third_passes | float64 | 0.0 | Completed passes from x<80 ending x>=80 |
| box_passes | float64 | 0.0 | Completed passes ending in the penalty area from outside it |
| crosses_completed | float64 | 0.0 | Completed passes flagged cross |
| through_balls | float64 | 0.0 | Passes with technique Through Ball |
| progressive_carries | float64 | 0.0 | PROJECT DEFINITION: carry ending >=25% closer to goal centre, end x >= 48 and >=5 units forward |
| carries_into_final_third | float64 | 0.0 | Carries from x<80 ending x>=80 |
| carries_into_box | float64 | 0.0 | Carries ending in the penalty area from outside it |
| dribbles | float64 | 0.0 | Dribble (take-on) attempts |
| dribbles_completed | float64 | 0.0 | Dribbles with outcome Complete |
| touches | float64 | 0.0 | On-ball actions (pass, receipt, carry, shot, dribble, clearance, interception, recovery, block, ...) |
| box_touches | float64 | 0.0 | On-ball actions located in the opponent penalty area |
| final_third_touches | float64 | 0.0 | On-ball actions with x >= 80 |
| tackles | float64 | 0.0 | Duels of type Tackle |
| tackles_won | float64 | 0.0 | Tackles with outcome Won / Success / Success In Play / Success Out |
| interceptions | float64 | 0.0 | Interception events |
| blocks | float64 | 0.0 | Block events |
| clearances | float64 | 0.0 | Clearance events |
| ball_recoveries | float64 | 0.0 | Ball Recovery events without recovery_failure |
| pressures | float64 | 0.0 | Pressure events |
| counterpressures | float64 | 0.0 | Pressure events flagged counterpress |
| aerials_won | float64 | 0.0 | aerial_won flag on pass/shot/clearance/miscontrol |
| defensive_actions | float64 | 0.0 | tackles + interceptions + blocks + clearances + ball recoveries |
| fouls_committed | float64 | 0.0 | Foul Committed events |
| fouls_won | float64 | 0.0 | Foul Won events |
| turnovers | float64 | 0.0 | Dispossessed + Miscontrol events |
| gk_saves | float64 | 0.0 | Goal Keeper events whose type is a save |
| gk_claims | float64 | 0.0 | Goal Keeper collected / punch / sweeper / smother actions |
| passes_completed | float64 | 0.0 | Passes with no outcome (StatsBomb: no outcome = complete) |
| long_passes | float64 | 0.0 |  |
| long_passes_completed | float64 | 0.0 |  |
| aerials_lost | float64 | 0.0 | Duels of type Aerial Lost |
| yellow_cards | float64 | 0.0 | Yellow cards (foul_committed/bad_behaviour card) |
| red_cards | float64 | 0.0 | Red or second-yellow cards |
| gk_goals_conceded | float64 | 0.0 | Goal Keeper events of type Goal Conceded |
| minutes_played | float64 | 0.0 | Actual playing time on pitch incl. stoppage (periods 1-4) from Starting XI/substitution/sending-off events |
| appearances | int64 | 0.0 |  |
| starts | int64 | 0.0 |  |
| sub_appearances | int64 | 0.0 |  |
| subbed_off | int64 | 0.0 |  |
| player_name | object | 0.0 |  |
| team_name | object | 0.0 |  |
| last_appearance | datetime64[ns] | 0.0 |  |
| unused_sub_count | int32 | 0.0 |  |
| matchday_squads | int64 | 0.0 |  |
| primary_position | object | 0.0 | minutes-weighted most common match position |
| primary_role | object | 0.0 |  |
| role_family | object | 0.0 |  |
| starts_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| avg_minutes | float64 | 0.0 |  |
| goals_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| npxg_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| xg_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| xa_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| shots_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| shots_on_target_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| assists_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| key_passes_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| passes_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| progressive_passes_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| final_third_passes_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| box_passes_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| crosses_completed_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| through_balls_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| progressive_carries_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| carries_into_final_third_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| carries_into_box_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| dribbles_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| dribbles_completed_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| touches_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| box_touches_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| final_third_touches_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| tackles_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| tackles_won_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| interceptions_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| blocks_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| clearances_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| ball_recoveries_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| pressures_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| counterpressures_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| aerials_won_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| defensive_actions_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| fouls_committed_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| fouls_won_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| turnovers_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| gk_saves_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| gk_claims_p90 | float64 | 0.0 | count / minutes_played * 90 (NaN if minutes = 0) |
| pass_completion_pct | float64 | 1.3 | percentile within benchmark group of eligible players |
| long_pass_completion_pct | float64 | 11.1 | percentile within benchmark group of eligible players |
| tackle_success_pct | float64 | 29.7 | percentile within benchmark group of eligible players |
| dribble_success_pct | float64 | 52.3 | percentile within benchmark group of eligible players |
| goals_minus_xg | float64 | 0.0 |  |
| eligible | bool | 0.0 | minutes_played >= config.min_minutes |
| sample_reliability | float64 | 0.0 | min(1, minutes/900) * 100 |
| coverage_label | object | 0.0 | high/moderate/low data coverage |
| benchmark_level | object | 0.0 |  |
| benchmark_group | object | 0.0 |  |
| benchmark_n | float64 | 0.0 |  |
| aerials_won_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| ball_recoveries_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| box_touches_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| clearances_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| crosses_completed_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| dribbles_completed_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| final_third_passes_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| gk_claims_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| gk_saves_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| goals_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| interceptions_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| key_passes_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| long_pass_completion_pct_pct | float64 | 11.1 | percentile within benchmark group of eligible players |
| pass_completion_pct_pct | float64 | 1.3 | percentile within benchmark group of eligible players |
| pressures_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| progressive_carries_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| progressive_passes_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| shots_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| tackles_won_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| xa_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| xg_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| defensive_actions_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| touches_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| turnovers_p90_pct | float64 | 0.0 | percentile within benchmark group of eligible players |
| small_benchmark_warning | bool | 0.0 |  |

## Table `team_match_stats` — 68 rows
| field | dtype | missing_pct | description / derivation |
|---|---|---|---|
| match_id | int64 | 0.0 |  |
| team_id | int64 | 0.0 |  |
| shots | int32 | 0.0 | Shot events (periods 1-4) |
| shots_on_target | int32 | 0.0 | Shots with outcome Goal / Saved / Saved To Post |
| xg | float64 | 0.0 | Sum of StatsBomb xG on all shots (periods 1-4) |
| npxg | float64 | 0.0 | Sum of StatsBomb xG on non-penalty shots |
| passes | int32 | 0.0 | Pass attempts |
| passes_completed | int32 | 0.0 | Passes with no outcome (StatsBomb: no outcome = complete) |
| progressive_passes | int32 | 0.0 | PROJECT DEFINITION: completed open-play pass starting outside the defending 40% (x >= 48) and ending >=25% closer to the opponent goal centre |
| progressive_carries | int32 | 0.0 | PROJECT DEFINITION: carry ending >=25% closer to goal centre, end x >= 48 and >=5 units forward |
| final_third_passes | int32 | 0.0 | Completed passes from x<80 ending x>=80 |
| box_passes | int32 | 0.0 | Completed passes ending in the penalty area from outside it |
| pressures | int32 | 0.0 | Pressure events |
| counterpressures | int32 | 0.0 | Pressure events flagged counterpress |
| defensive_actions | int32 | 0.0 | tackles + interceptions + blocks + clearances + ball recoveries |
| final_third_touches | int32 | 0.0 | On-ball actions with x >= 80 |
| box_touches | int32 | 0.0 | On-ball actions located in the opponent penalty area |
| touches | int32 | 0.0 | On-ball actions (pass, receipt, carry, shot, dribble, clearance, interception, recovery, block, ...) |
| crosses_completed | int32 | 0.0 | Completed passes flagged cross |
| fouls_committed | int32 | 0.0 | Foul Committed events |
| yellow_cards | int32 | 0.0 | Yellow cards (foul_committed/bad_behaviour card) |
| red_cards | int32 | 0.0 | Red or second-yellow cards |
| set_piece_shots | float64 | 0.0 |  |
| opponent_id | int64 | 0.0 |  |
| team_name | object | 0.0 |  |
| opponent | object | 0.0 |  |
| home_away | object | 0.0 |  |
| match_date | datetime64[ns] | 0.0 |  |
| ppda | float64 | 0.0 | APPROXIMATION: opponent passes in own 60% / team tackles+interceptions+fouls+failed challenges in that zone |
| shots_against | int32 | 0.0 |  |
| shots_on_target_against | int32 | 0.0 |  |
| xg_against | float64 | 0.0 |  |
| passes_against | int32 | 0.0 |  |
| final_third_touches_against | int32 | 0.0 |  |
| goals_for | int64 | 0.0 |  |
| goals_against | int64 | 0.0 |  |
| goal_diff | int64 | 0.0 |  |
| result | object | 0.0 | from reconciled goal events |
| points | int64 | 0.0 | from reconciled goal events |
| possession_proxy_pct | float64 | 0.0 | PROXY: team passes / all passes in match |
| field_tilt_pct | float64 | 0.0 | PROXY: final-third on-ball actions share |
| pass_completion_pct | float64 | 0.0 |  |
| xg_diff | float64 | 0.0 |  |
| starting_formation | object | 0.0 |  |
| in_match_formation_changes | int64 | 0.0 |  |
| manager_id | int64 | 0.0 |  |
| manager_name | object | 0.0 |  |

## Table `workload` — 1,353 rows
| field | dtype | missing_pct | description / derivation |
|---|---|---|---|
| match_id | int64 | 0.0 |  |
| team_id | int64 | 0.0 |  |
| player_id | int64 | 0.0 |  |
| minutes_prev_7d | float64 | 0.0 | minutes in earlier DATASET matches within window (proxy, not fatigue) |
| minutes_prev_14d | float64 | 0.0 |  |
| minutes_prev_28d | float64 | 0.0 |  |
| rest_days | float64 | 39.2 | days since previous dataset appearance |
| team_rest_days | float64 | 26.5 |  |
| started_prev_match | object | 26.5 | started team's previous dataset match |
| consecutive_starts_before | int64 | 0.0 |  |
| starts_before | int64 | 0.0 |  |
| apps_before | int64 | 0.0 |  |
| prior_team_matches | int64 | 0.0 |  |
| start_share_before | float64 | 26.5 |  |
| minutes_share_before | float64 | 26.5 |  |

## Source register
| source | url | role_in_project | access | terms | status |
|---|---|---|---|---|---|
| StatsBomb Open Data (Hudl) | https://github.com/statsbomb/open-data | PRIMARY: competitions, matches (incl. managers, referee, stadium), lineups, events | Public GitHub repository, raw JSON over HTTPS | Free for research/education; attribute StatsBomb as data source and follow the repository LICENSE / attribution instructions (use of logo requested for published outputs). Verify current terms before redistribution. | used |
| API-Football v3 | https://www.api-football.com/documentation-v3 | OPTIONAL enrichment (coach, injuries, fixtures) — requires the user's own key | REST API; key from Colab Secrets / environment variable API_FOOTBALL_KEY | Subscription terms of the provider; coverage varies by league | not used by default (no key supplied) |
| Metrica Sports sample data | https://github.com/metrica-sports/sample-data | OPTIONAL separate tracking demo only (anonymised; never merged with named players) | Public GitHub repository | See repository licence | not used |
| football-data.co.uk | https://www.football-data.co.uk/ | OPTIONAL supplementary team-level results only | CSV downloads | See website notes | not used |
| User-supplied files | data/external/ | USER_DATA mode (StatsBomb-format JSON) and optional managers.csv mapping | Local files placed by the user | User must hold rights to use the files | optional |
