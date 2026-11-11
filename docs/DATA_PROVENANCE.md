# Data Provenance

> Generated 2026-11-11 11:30 UTC from `data/manifest/source_manifest.json` (manifest version 1.0.0). The manifest stores hashes, sizes and counts only; no source data is redistributed in this repository.

## Source

- **Name.** StatsBomb Open Data
- **Publisher.** StatsBomb / Hudl
- **Repository.** https://github.com/hudl/open-data
- **Download base URL.** `https://raw.githubusercontent.com/hudl/open-data/master/data`
- **Terms.** https://github.com/hudl/open-data/blob/master/LICENSE.pdf
- **Field documentation.** https://github.com/hudl/open-data/tree/master/doc
- **Attribution requirement.** State StatsBomb as the data source and use the StatsBomb logo (Media Pack) when publishing analysis based on the data.
- **Source revision when verified.** commit `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb` (2026-09-07T16:27:15Z)

### Terms as read from the source licence

- The data are provided for analysis and research; analysis and conclusions may be shared publicly (1.1).
- The user may not edit, distort, distribute, reproduce, sell or provide the data to third parties (1.2.1).
- No commercial exploitation of the data or of analysis derived from it (1.2.2).
- Publications of analysis must be accredited with the StatsBomb brand logo (1.4).
- The service is provided as is; StatsBomb may withdraw it at any time (2.1, 3.2).

Consequence for this project: raw and processed event tables are **not** committed. The pipeline downloads the files from the official repository on first run and caches them locally (`data/raw/`, git-ignored). Figures, summary tables and reports are analysis and carry the attribution.

## Scope

- **Competition / season.** 1. Bundesliga 2023/2024 (competition 9, season 281)
- **Matches.** 34 analysed of 34 published for this competition-season; focus team filter: Bayer Leverkusen
- **Dates.** 2023-08-19 to 2024-05-18
- **Match IDs.** 3895052, 3895060, 3895067, 3895074, 3895086, 3895095, 3895107, 3895113, 3895121, 3895134, 3895139, 3895153, 3895158, 3895167, 3895180, 3895182, 3895194, 3895202, 3895210, 3895220, 3895232, 3895244, 3895250, 3895258, 3895266, 3895275, 3895286, 3895292, 3895302, 3895309, 3895320, 3895333, 3895340, 3895348

## Retrieval

- **Files.** 70 (120.05 MB), 0 failed
- **Raw files written between.** 2026-11-01T16:47:55+00:00 and 2026-11-01T16:48:38+00:00 (UTC; cache hits keep their original download time)
- **Integrity.** SHA-256 of every file is in the manifest

| resource | files | bytes |
| --- | --- | --- |
| competitions | 1 | 34887 |
| events | 34 | 119223803 |
| lineups | 34 | 733155 |
| matches | 1 | 63079 |


## Parsed tables

| table | rows | columns |
| --- | --- | --- |
| matches | 34 | 23 |
| managers | 68 | 8 |
| events | 137765 | 54 |
| squads | 1353 | 14 |
| period_bounds | 68 | 7 |
| appearances | 1353 | 26 |
| spells | 1049 | 14 |
| substitutions_raw | 301 | 15 |
| goals | 113 | 8 |
| sending_offs | 5 | 9 |
| formations | 195 | 10 |
| parse_issues | 0 | 0 |
| flags | 137765 | 98 |
| pms | 1049 | 77 |
| season | 377 | 106 |
| season_pct | 377 | 134 |
| team_stats | 68 | 47 |
| workload | 1353 | 15 |
| subs | 301 | 41 |


## Validation

- Domain rules passed: **16 / 16**
- Table contracts passed: **14 / 14**

| check | rule | violations | checked | status |
| --- | --- | --- | --- | --- |
| Duplicate event IDs | event_id unique | 0 | 137765 | PASS |
| Duplicate squad rows | one row per player per match | 0 | 1353 | PASS |
| Event coordinates outside 120x80 | 0<=x<=120, 0<=y<=80 | 0 | 136803 | PASS |
| End coordinates outside pitch (+2 tolerance) | end location on/near pitch | 0 | 72499 | PASS |
| xG outside [0,1] | 0<=statsbomb_xg<=1 | 0 | 916 | PASS |
| Negative minutes played | minutes >= 0 | 0 | 1353 | PASS |
| Matches with unordered event index | event index increasing | 0 | 34 | PASS |
| Clock steps backwards >5s within period | timestamps ordered (flag only) | 0 | 137765 | PASS |
| Team-matches without exactly 11 starters | XI has 11 players | 0 | 68 | PASS |
| Team-matches without exactly one starting GK | one goalkeeper slot (event-position based) | 0 | 68 | PASS |
| Player selected twice in same XI | XI players distinct | 0 | 748 | PASS |
| Substitutions missing team/player/time | complete substitution records | 0 | 301 | PASS |
| Overlapping on-pitch spells | player cannot be on pitch twice simultaneously | 0 | 1049 | PASS |
| Event goals != published score | goal events reconcile to final score | 0 | 34 | PASS |
| Event players missing from matchday squad | player references resolve | 0 | 1045 | PASS |
| Appearances with unknown minutes | minutes derivable from events | 0 | 1353 | PASS |


## Transformations

1. parse matches, lineups and events JSON into flat canonical tables (no raw row deleted)
2. add an elapsed-minute clock from period bounds
3. reconstruct on-pitch spells and minutes from Starting XI, Substitution and sending-off events
4. derive event flags (progressive actions, box touches, key passes, ...)
5. aggregate to player-match, player-season (per 90, role percentiles) and team-match tables
6. enrich substitutions with score state, timing band, roles and rule windows

## Derived-table dependencies

| table | built from |
| --- | --- |
| appearances | events, squads, period_bounds |
| spells | events, period_bounds |
| goals | events, matches |
| formations | events |
| flags | events |
| pms | flags, appearances, matches |
| season | pms, appearances |
| season_pct | season |
| team_stats | flags, matches, goals, formations, managers |
| workload | appearances, matches |
| subs | substitutions_raw, goals, sending_offs, appearances, team_stats |


## Data limitations

- Team-centric sample: every analysed match involves the focus team; opponents appear twice (home and away).
- League matches only: no cup, European or international fixtures.
- No player age, height, injury, fitness, GPS, tracking, salary or market-value data.
- No post-shot xG; StatsBomb xG is a model output of the provider.
- StatsBomb 360 freeze frames are published for these matches but are optional and not loaded by default.
- Manager identity is the name recorded per match; tenure outside the analysed matches is unknown.

## First files in the manifest (illustration)

| path | bytes | sha256 | file_written_utc |
| --- | --- | --- | --- |
| competitions.json | 34887 | e6cd42f5d8956d6aa30fb917ce8d4c3b3df1879a93f02f8feba820930a6971fa | 2026-11-01T16:47:55+00:00 |
| events/3895052.json | 3205861 | ecc00b4e7ddd0154532329091d5d82fd7de4b9f6aa8da174788816001e40e605 | 2026-11-01T16:47:56+00:00 |
| events/3895060.json | 3798711 | 1b2fcf16823fbf04f4ae40492d492304f8d54fdb991cebc7fdcaa2e1d72e5585 | 2026-11-01T16:47:57+00:00 |
| events/3895067.json | 3453122 | 8bba4bec9d870aa5b88eab122ba50f33c89d038580893e330e9c0ec41e9a946a | 2026-11-01T16:47:58+00:00 |
| events/3895074.json | 3745841 | b43f2c87a77eeca368247ac290fa85297183c14f1a1eb7f5d9b335173205427d | 2026-11-01T16:48:00+00:00 |
| events/3895086.json | 3626424 | 84d8ce36e84efbe1b168d39efe0b166c50a48da3cf587986a6455cbb06d6e119 | 2026-11-01T16:48:02+00:00 |

