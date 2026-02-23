# Cricsheet Data Reference

Source: https://cricsheet.org

## Dataset Overview

- 1169 IPL (Indian Premier League) match JSON files, all T20 format, male
- Seasons: 2007/08 through 2025
- 10 teams across history (some renamed): Royal Challengers Bangalore/Bengaluru, Mumbai Indians, Chennai Super Kings, Kolkata Knight Riders, Delhi Capitals (formerly Daredevils), Punjab Kings (formerly Kings XI Punjab), Rajasthan Royals, Sunrisers Hyderabad, Gujarat Titans, Lucknow Super Giants
- People registry CSV: 16,471 people (players, officials, etc.)

## Match JSON Structure (versions 1.0.0 and 1.1.0)

### Top-level keys
- `meta`: { data_version, created, revision }
- `info`: match metadata
- `innings`: array of innings objects

### info object
- `balls_per_over`: always 6
- `city`: string
- `dates`: array of date strings (YYYY-MM-DD)
- `event`: { name: "Indian Premier League", match_number?: int, stage?: "Final"|"Qualifier 1"|etc }
- `gender`: "male"
- `match_type`: "T20"
- `officials`: { match_referees[], reserve_umpires[], tv_umpires[], umpires[] }
- `outcome`: see Outcome section below
- `overs`: 20
- `player_of_match`: [string]
- `players`: { "Team A": [player_names], "Team B": [player_names] } — playing XI
- `registry.people`: { "Player Name": "identifier_hash" } — links to people.csv
- `season`: string (e.g. "2025", "2007/08")
- `team_type`: "club"
- `teams`: [team1, team2]
- `toss`: { decision: "bat"|"field", winner: "Team Name" }
- `venue`: string

### Outcome types
- Normal win: `{ winner: "Team", by: { runs: N } }` or `{ winner: "Team", by: { wickets: N } }`
- DLS method: adds `method: "D/L"`
- Tie with super over: `{ result: "tie", eliminator: "Winning Team" }`
- No result: `{ result: "no result" }`

### Innings object
- `team`: batting team name
- `overs`: array of over objects
- `super_over`: boolean (true if this is a super over innings)
- `powerplays`: [{ from, to, type: "mandatory" }] (present in v1.0.0 files)
- `target`: { overs: int, runs: int } (present on 2nd innings)

### Over object
- `over`: 0-indexed over number (0 = first over)
- `deliveries`: array of delivery objects

### Delivery object
- `batter`: batter name (string)
- `bowler`: bowler name (string)
- `non_striker`: non-striker name (string)
- `runs`: { batter: int, extras: int, total: int }
- `extras`?: { wides?, noballs?, byes?, legbyes?, penalty? } — each is an int, only present if > 0
- `wickets`?: array of wicket objects
- `review`?: { by: team, umpire: name, batter: name, decision: "upheld"|"overturned"|etc, type: "wicket"|etc }
- `replacements`?: { match: [{ in: player, out: player, team: team, reason: "impact_player" }] }

### Wicket object
- `player_out`: string
- `kind`: one of: bowled, caught, caught and bowled, hit wicket, lbw, obstructing the field, retired hurt, retired out, run out, stumped
- `fielders`?: [{ name: string }] — present for caught, run out, stumped

### Extras types found
wides, noballs, byes, legbyes, penalty

## People CSV (people.csv)

- `identifier`: 8-char hex hash — matches registry.people values in match JSON
- `name`: short name (e.g. "V Kohli")
- `unique_name`: disambiguated name
- `key_cricinfo`, `key_cricbuzz`, `key_bcci`, etc.: cross-reference IDs to other cricket databases

## Key relationships
- Match JSON `info.registry.people[player_name]` → people.csv `identifier`
- Match JSON `info.players[team]` → list of player short names used in deliveries
- Player names in deliveries (batter, bowler, non_striker, fielders, player_out) use the same short name format as in info.players
