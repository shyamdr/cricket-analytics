# ESPN Cricinfo __NEXT_DATA__ — Complete Field Reference

Source: Full-scorecard page `__NEXT_DATA__` JSON for RCB vs LSG, IPL 2024 (match 1422133).

This document catalogs every field in the ESPN JSON response. Each field is marked:
- **ADD** — worth storing, enriches our data beyond what Cricsheet provides
- **SKIP** — not useful for analytics (UI/display metadata, images, slugs, etc.)
- **ALREADY HAVE** — we already capture this in our existing ESPN enrichment or Cricsheet data

The JSON has two top-level objects: `match` and `content`.

---

## 1. match object — Match-Level Metadata

### 1.1 Match Identifiers & Status

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `match.objectId` | int | `1422133` | ESPN's unique match ID. Primary key for ESPN data. | ALREADY HAVE |
| `match.id` | int | `114028` | ESPN internal row ID (different from objectId). | SKIP |
| `match._uid` | int | `114028` | Same as id, internal use. | SKIP |
| `match.scribeId` | int | `1422133` | Same as objectId, used by ESPN's scoring system. | SKIP |
| `match.slug` | str | `"royal-challengers-bengaluru-vs-lucknow-super-giants-15th-match"` | URL-friendly match identifier. | ALREADY HAVE |
| `match.title` | str | `"15th Match"` | Human-readable match title (e.g. "15th Match", "Final", "Qualifier 1"). | ALREADY HAVE |
| `match.stage` | str | `"FINISHED"` | Match lifecycle stage: FINISHED, LIVE, UPCOMING, ABANDONED. | SKIP |
| `match.state` | str | `"POST"` | Match state: POST, LIVE, PRE. | SKIP |
| `match.status` | str | `"RESULT"` | Match status: RESULT, NO RESULT, ABANDONED. | SKIP |
| `match.statusText` | str | `"LSG won by 28 runs"` | Human-readable result text. | ALREADY HAVE |
| `match.statusEng` | str | `"RESULT"` | English status label. | SKIP |
| `match.resultStatus` | int | `1` | Numeric result code (1 = result, 0 = no result). | SKIP |
| `match.coverage` | str | `"Y"` | Whether ESPN has full ball-by-ball coverage. | SKIP |
| `match.coverageNote` | str | `""` | Notes about coverage gaps. | SKIP |

### 1.2 Match Classification

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `match.format` | str | `"T20"` | Match format: T20, ODI, TEST, T10, THE_HUNDRED, etc. | SKIP (have from Cricsheet) |
| `match.generalClassId` | int | `6` | ESPN's classification ID (6 = T20). | SKIP |
| `match.internationalClassId` | null | `null` | Null for franchise cricket, set for internationals. Needed when expanding beyond franchise leagues. | ADD |
| `match.subClassId` | null | `null` | Sub-classification (e.g. warm-up, practice). Useful for filtering non-standard matches. | ADD |
| `match.season` | str | `"2024"` | Season identifier. | ALREADY HAVE |
| `match.dayType` | str | `"SINGLE"` | SINGLE for limited-overs, MULTI for Tests. | SKIP |
| `match.scheduledDays` | int | `1` | Number of scheduled days (1 for T20, 5 for Test). | SKIP |
| `match.scheduledOvers` | int | `20` | Scheduled overs per innings. | SKIP (have from Cricsheet) |
| `match.scheduledInnings` | int | `1` | Scheduled innings per team (1 for limited-overs, 2 for Test). | SKIP |
| `match.ballsPerOver` | int | `6` | Balls per over. | SKIP (have from Cricsheet) |
| `match.finalType` | int | `0` | 0 = not a final, other values for final types. | SKIP |

### 1.3 Timing

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `match.startDate` | str | `"2024-04-02T00:00:00.000Z"` | Match start date (midnight UTC of match day). | ALREADY HAVE |
| `match.endDate` | str | `"2024-04-02T00:00:00.000Z"` | Match end date (same as start for single-day). | SKIP |
| `match.startTime` | str | `"2024-04-02T14:00:00.000Z"` | Actual start time with timezone (first ball). | ALREADY HAVE |
| `match.endTime` | str | `"2024-04-02T21:38:30.000Z"` | Actual end time (last ball / result). Match duration = endTime - startTime. | ADD |
| `match.timePublished` | bool | `true` | Whether start time was published (false for TBD matches). | SKIP |
| `match.scheduleNote` | str | `""` | Scheduling notes (rain delays, etc.). | SKIP |
| `match.hoursInfo` | str | `"19.30 start, First Session 19.30-21.00, Interval 21.00-21.20..."` | Session timing breakdown in local time. Contains innings break info. | ADD |
| `match.daysInfo` | str | `"2 April 2024"` | Human-readable date. | SKIP |

### 1.4 Floodlight / Day-Night

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `match.floodlit` | str | `"night"` | Lighting condition: "day", "night", "daynight". Critical for dew factor analysis. | ALREADY HAVE |

### 1.5 Toss & Result

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `match.winnerTeamId` | int | `6903` | ESPN team ID of the winner. | SKIP (have from Cricsheet) |
| `match.tossWinnerTeamId` | int | `4340` | ESPN team ID of toss winner. | SKIP (have from Cricsheet) |
| `match.tossWinnerChoice` | int | `2` | 1 = bat, 2 = field. | SKIP (have from Cricsheet) |
| `match.tiebreakerTeamId` | null | `null` | Team that won the super over (null if no super over). | SKIP (have from Cricsheet) |
| `match.isSuperOver` | bool | `false` | Whether match went to super over. | SKIP (have from Cricsheet) |
| `match.isScheduledInningsComplete` | bool | `true` | Whether all scheduled innings were completed. | SKIP |
| `match.hasFollowon` | bool | `false` | Test-only: whether follow-on was enforced. | SKIP |

### 1.6 Live Match State (snapshot at time of scrape)

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `match.liveInning` | int | `2` | Last active innings number. | SKIP |
| `match.liveOvers` | float | `19.04` | Last over.ball at time of scrape. | SKIP |
| `match.liveBalls` | int | `114` | Total balls bowled in last active innings. | SKIP |
| `match.liveInningPredictions` | null | | Live win probability (null for completed matches). | SKIP |
| `match.liveOversPending` | null | | Overs remaining (null for completed). | SKIP |
| `match.liveRecentBalls` | null | | Recent ball-by-ball summary (null for completed). | SKIP |
| `match.livePlayers` | null | | Current batsmen/bowler (null for completed). | SKIP |
| `match.actualDays` | int | `1` | Actual number of days the match lasted. | SKIP |
| `match.liveDay` | int | `1` | Current day number. | SKIP |
| `match.liveSession` | int | `1` | Current session number. | SKIP |

### 1.7 Status Data (structured result breakdown)

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `match.statusData.statusTextLangKey` | str | `"match_status_text_won_runs"` | i18n key for result type. | SKIP |
| `match.statusData.statusTextLangData.wonByRuns` | int | `28` | Winning margin in runs (0 if won by wickets). | SKIP (have from Cricsheet) |
| `match.statusData.statusTextLangData.wonByWickets` | int | `0` | Winning margin in wickets (0 if won by runs). | SKIP (have from Cricsheet) |
| `match.statusData.statusTextLangData.wonByBalls` | int | `0` | Balls remaining when won by wickets. Derivable from Cricsheet deliveries. | SKIP |
| `match.statusData.statusTextLangData.firstBattingTeamId` | int | `6903` | ESPN ID of team batting first. | SKIP |
| `match.statusData.statusTextLangData.currentBattingTeamId` | int | `4340` | ESPN ID of team batting at end. | SKIP |
| `match.statusData.statusTextLangData.crr` | null | | Current run rate (null for completed). | SKIP |
| `match.statusData.statusTextLangData.rrr` | null | | Required run rate (null for completed). | SKIP |
| `match.statusData.statusTextLangData.requiredRuns` | null | | Runs needed (null for completed). | SKIP |
| `match.statusData.statusTextLangData.remainingBalls` | null | | Balls remaining (null for completed). | SKIP |
| `match.statusData.statusTextLangData.leadRuns` | null | | Lead in runs (Test matches). | SKIP |
| `match.statusData.statusTextLangData.trailRuns` | null | | Trail in runs (Test matches). | SKIP |
| `match.statusData.statusTextLangData.day` | null | | Day number (Test matches). | SKIP |
| `match.statusData.statusTextLangData.session` | null | | Session number (Test matches). | SKIP |
| `match.statusData.statusTextLangData.rainRuleType` | null | | DLS/VJD method type if applied. | SKIP |

</text>
</invoke>

### 1.8 Series

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `match.series.objectId` | int | `1410320` | ESPN series ID. Used to construct URLs. | ALREADY HAVE |
| `match.series.name` | str | `"Indian Premier League"` | Series short name. | SKIP (have from Cricsheet) |
| `match.series.longName` | str | `"Indian Premier League"` | Series full name. | SKIP |
| `match.series.alternateName` | str | `"IPL"` | Series abbreviation. | SKIP |
| `match.series.seoName` | str | `"Indian Premier League 2024"` | SEO-friendly name with year. | SKIP |
| `match.series.slug` | str | `"indian-premier-league-2024"` | URL slug. | SKIP |
| `match.series.year` | int | `2024` | Series year. | SKIP |
| `match.series.season` | str | `"2024"` | Season string. | SKIP |
| `match.series.typeId` | int | `3` | Series type (3 = franchise league). | SKIP |
| `match.series.trophyId` | int | `117` | Trophy identifier. | SKIP |
| `match.series.isTrophy` | bool | `true` | Whether series has a trophy. | SKIP |
| `match.series.description` | str | `"in India"` | Location description. | SKIP |
| `match.series.startDate` | str | `"2024-03-22T00:00:00.000Z"` | Series start date. | SKIP |
| `match.series.endDate` | str | `"2024-05-26T00:00:00.000Z"` | Series end date. | SKIP |
| `match.series.hasStandings` | bool | `true` | Whether points table exists. | SKIP |
| `match.series.standingsType` | int | `3` | Standings format type. | SKIP |
| `match.series.totalVideos` | int | `834` | Total videos for the series. | SKIP |
| `match.series.totalSquads` | int | `10` | Number of team squads. | SKIP |
| `match.series.gamePlayWatch` | bool | `true` | Whether game highlights are available. | SKIP |


### 1.9 Ground / Venue

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `match.ground.objectId` | int | `57897` | ESPN ground ID. Unique per venue. | ADD |
| `match.ground.name` | str | `"M Chinnaswamy Stadium, Bengaluru"` | Full venue name with city. | SKIP (have from Cricsheet) |
| `match.ground.smallName` | str | `"Bengaluru"` | Short venue name (usually city). | SKIP |
| `match.ground.longName` | str | `"M Chinnaswamy Stadium, Bengaluru"` | Same as name. | SKIP |
| `match.ground.slug` | str | `"m-chinnaswamy-stadium-bengaluru"` | URL slug. | SKIP |
| `match.ground.location` | str | `""` | Sub-location within city (often empty). | SKIP |
| `match.ground.capacity` | str | `"40,000"` | Stadium capacity as formatted string. | ADD |
| `match.ground.image.*` | dict | | Stadium photo metadata (url, caption, credit). | SKIP |
| `match.ground.town.objectId` | int | `57892` | ESPN town/city ID. | SKIP |
| `match.ground.town.name` | str | `"Bengaluru"` | City name. | SKIP (have from Cricsheet) |
| `match.ground.town.timezone` | str | `"Asia/Kolkata"` | Venue timezone (IANA format). Useful for local time calculations. | ADD |
| `match.ground.town.area` | str | `""` | Sub-area (usually empty). | SKIP |
| `match.ground.country.objectId` | int | `6` | ESPN country ID. | SKIP |
| `match.ground.country.name` | str | `"India"` | Country name. | SKIP |
| `match.ground.country.abbreviation` | str | `"IND"` | Country code. | SKIP |


### 1.10 Teams (match.teams[])

Each match has 2 team entries. The team object contains the team info plus match-specific data.

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `teams[].team.objectId` | int | `1298768` | ESPN team ID. Stable across seasons. | ALREADY HAVE |
| `teams[].team.name` | str | `"LSG"` | Team abbreviation. | SKIP |
| `teams[].team.longName` | str | `"Lucknow Super Giants"` | Full team name. | ALREADY HAVE |
| `teams[].team.abbreviation` | str | `"LSG"` | Same as name for franchise teams. | SKIP |
| `teams[].team.unofficialName` | str | `"Lucknow"` | Informal/city-based name. | SKIP |
| `teams[].team.slug` | str | `"lucknow-super-giants"` | URL slug. | SKIP |
| `teams[].team.isCountry` | bool | `false` | false for franchise, true for national teams. | SKIP |
| `teams[].team.primaryColor` | str | `"#FA8C16"` | Team brand color (hex). Could be useful for UI. | ADD |
| `teams[].team.imageUrl` | str | `"/lsci/db/PICTURES/CMS/414000/414035.png"` | Team logo URL. | SKIP |
| `teams[].team.image.*` | dict | | Team logo metadata. | SKIP |
| `teams[].team.country.*` | dict | | Country the team belongs to. | SKIP |
| `teams[].isHome` | bool | `false` | Whether this team is the home team at this venue. | ADD |
| `teams[].isLive` | bool | `false` | Whether team is currently batting (live matches). | SKIP |
| `teams[].score` | str | `"181/5"` | Final score as "runs/wickets" string. | SKIP (have from Cricsheet) |
| `teams[].scoreInfo` | null | | Additional score info (DLS target, etc.). | SKIP |
| `teams[].inningNumbers` | list | `[1]` | Which innings this team batted in (e.g. [1] or [1,3] for Tests). | SKIP |
| `teams[].points` | int | `2` | Points earned in this match (for standings). | ADD |
| `teams[].sidePlayers` | int | `11` | Number of players in the playing XI. | SKIP |
| `teams[].sideBatsmen` | int | `11` | Number of batsmen listed (usually same as sidePlayers). | SKIP |
| `teams[].sideFielders` | int | `11` | Number of fielders listed. | SKIP |
| `teams[].teamOdds` | null | | Betting odds (null for most matches). | SKIP |


### 1.11 Captain (match.teams[].captain)

Full player object for each team's captain. Contains rich biographical data.

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `captain.objectId` | int | `422108` | ESPN player ID for captain. | ALREADY HAVE |
| `captain.name` | str | `"KL Rahul"` | Captain short name. | ALREADY HAVE |
| `captain.longName` | str | `"KL Rahul"` | Captain full name. | SKIP |
| `captain.dateOfBirth.year` | int | `1992` | Birth year. | ADD |
| `captain.dateOfBirth.month` | int | `4` | Birth month. | ADD |
| `captain.dateOfBirth.date` | int | `18` | Birth day. | ADD |
| `captain.dateOfDeath` | null | | Death date (null for living players). | SKIP |
| `captain.gender` | str | `"M"` | Gender. | SKIP |
| `captain.battingStyles` | list | `["rhb"]` | Batting hand codes: rhb (right-hand bat), lhb (left-hand bat). | ADD |
| `captain.bowlingStyles` | list | `[]` | Bowling style codes: ob, sla, rmf, rf, lmf, etc. | ADD |
| `captain.longBattingStyles` | list | `["right-hand bat"]` | Human-readable batting style. | ADD |
| `captain.longBowlingStyles` | list | `[]` | Human-readable bowling style. | ADD |
| `captain.countryTeamId` | int | `6` | ESPN ID of player's national team (6 = India). | ADD |
| `captain.playerRoleTypeIds` | list | `[7]` | Numeric role IDs (see playingRoles for human-readable). | SKIP |
| `captain.playingRoles` | list | `["wicketkeeper batter"]` | Human-readable playing roles. Values seen: "batter", "bowler", "allrounder", "batting allrounder", "bowling allrounder", "wicketkeeper batter", "wicketkeeper". | ADD |
| `captain.slug` | str | `"kl-rahul"` | URL slug. | SKIP |
| `captain.imageUrl` | str | | Player photo URL. | SKIP |
| `captain.headshotImageUrl` | str | | Headshot photo URL. | SKIP |
| `captain.image.*` | dict | | Photo metadata. | SKIP |
| `captain.headshotImage.*` | dict | | Headshot metadata. | SKIP |
| `captain.mobileName` | str | `"Rahul"` | Short display name for mobile. | SKIP |
| `captain.indexName` | str | `"Rahul, KL"` | Alphabetical index name. | SKIP |
| `captain.battingName` | str | `"KL Rahul"` | Name as shown in batting scorecard. | SKIP |
| `captain.fieldingName` | str | `"Rahul"` | Name as shown in fielding records. | SKIP |

Note: The same player object structure appears for ALL player references throughout the JSON (batsmen, bowlers, fielders, umpires, etc.). The biographical fields (DOB, batting/bowling styles, playingRoles) are the same everywhere a player appears.


### 1.12 Officials

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `match.umpires[]` | list | 2 entries | On-field umpires. Each has `.player` (full player object) and `.team` (nationality). | SKIP (have from Cricsheet) |
| `match.tvUmpires[]` | list | 1 entry | Third umpire / TV umpire. Same structure. | SKIP (have from Cricsheet) |
| `match.reserveUmpires[]` | list | 1 entry | Reserve / fourth umpire. Same structure. | SKIP (have from Cricsheet) |
| `match.matchReferees[]` | list | 1 entry | Match referee. Same structure. | SKIP (have from Cricsheet) |

Note: Each official entry has a full player object (with DOB, slug, etc.) and a team object (their nationality). The player data for officials is not particularly useful for cricket analytics.

### 1.13 Replacement Players (Impact Player Substitutions)

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `match.replacementPlayers[]` | list | 2 entries | Impact player substitutions made during the match. | |
| `replacementPlayers[].player.objectId` | int | `853265` | ESPN ID of player coming IN. | ADD |
| `replacementPlayers[].player.name` | str | `"MK Lomror"` | Name of player coming in. | ADD |
| `replacementPlayers[].replacingPlayer.objectId` | int | `1159720` | ESPN ID of player going OUT. | ADD |
| `replacementPlayers[].replacingPlayer.name` | str | `"Yash Dayal"` | Name of player going out. | ADD |
| `replacementPlayers[].team.name` | str | `"RCB"` | Team making the substitution. | ADD |
| `replacementPlayers[].over` | float | `12.5` | Over.ball when substitution happened (e.g. 12.5 = over 13, ball 5). | ADD |
| `replacementPlayers[].oversUnique` | float | `12.06` | Unique over representation. | SKIP |
| `replacementPlayers[].inning` | int | `2` | Innings number when substitution happened. | ADD |
| `replacementPlayers[].playerReplacementType` | int | `8` | Type code (8 = impact player). | ADD |
| `replacementPlayers[].player.*` | dict | | Full player object for incoming player (DOB, styles, roles). | (covered in player section) |
| `replacementPlayers[].replacingPlayer.*` | dict | | Full player object for outgoing player. | (covered in player section) |

Note: We already capture replacements from Cricsheet (`replacements` field in deliveries), but ESPN gives us the exact over/ball and full player objects. The ESPN data is richer.


### 1.14 Miscellaneous Match Fields

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `match.isCancelled` | bool | `false` | Whether match was cancelled. | SKIP |
| `match.liveStreamUrl` | null | | Live stream URL (null for completed). | SKIP |
| `match.highlightsUrl` | null | | Highlights URL (usually null). | SKIP |
| `match.internationalNumber` | null | | ICC match number (null for franchise). | SKIP |
| `match.generalNumber` | null | | General match number. | SKIP |
| `match.previewStoryId` | int | `323763` | ESPN article ID for match preview. | SKIP |
| `match.reportStoryId` | int | `323799` | ESPN article ID for match report. | SKIP |
| `match.liveBlogStoryId` | int | `323791` | ESPN article ID for live blog. | SKIP |
| `match.fantasyPickStoryId` | null | | Fantasy picks article ID. | SKIP |
| `match.reportStory.storyId` | int | `323799` | Same as reportStoryId. | SKIP |
| `match.liveBlogStory.storyId` | int | `323791` | Same as liveBlogStoryId. | SKIP |
| `match.drawOdds` | null | | Draw odds (null for limited-overs). | SKIP |
| `match.insightsEnabled` | bool | `false` | Whether AI insights are available. | SKIP |
| `match.hasMatchPlayers` | bool | `true` | Whether player data is available. | SKIP |
| `match.hasCommentary` | bool | `true` | Whether ball-by-ball commentary exists. | SKIP |
| `match.hasScorecard` | bool | `true` | Whether scorecard is available. | SKIP |
| `match.hasStandings` | bool | `true` | Whether standings are available. | SKIP |
| `match.hasSuperStats` | bool | `true` | Whether advanced stats are available. | SKIP |
| `match.hasGameboard` | bool | `true` | Whether gameboard visualization exists. | SKIP |
| `match.hasFanRatings` | bool | `true` | Whether fan ratings are available. | SKIP |
| `match.hasGalleries` | bool | `false` | Whether photo galleries exist. | SKIP |
| `match.hasImages` | bool | `true` | Whether match images exist. | SKIP |
| `match.hasVideos` | bool | `true` | Whether match videos exist. | SKIP |
| `match.hasStories` | bool | `true` | Whether articles exist. | SKIP |
| `match.languages` | list | `["hi"]` | Available language translations. | SKIP |
| `match.generatedAt` | str | `"2026-03-01T19:40:19.861Z"` | When this JSON was generated by ESPN. | SKIP |
| `match.scorecardSource` | str | `"emma"` | Internal scoring system name. | SKIP |
| `match.ballByBallSource` | str | `"feedback"` | Ball-by-ball data source. | SKIP |
| `match.headToHeadSource` | str | `"feedback"` | Head-to-head stats source. | SKIP |
| `match.commentarySource` | str | `"cms"` | Commentary data source. | SKIP |
| `match.hawkeyeSource` | null | | Hawk-Eye data source (null = not available). | SKIP |
| `match.liveCommentator` | str | `"@bose_abhimanyu"` | Live commentator handle. | SKIP |
| `match.liveScorer` | str | `"Chandan Duorah"` | Live scorer name. | SKIP |
| `match.debutPlayers` | null | | Players making debut (null if none or not tracked). | ADD |
| `match.otherSerieses` | list | `[]` | Other series this match belongs to (usually empty). | SKIP |


---

## 2. content.matchPlayers — Playing XI with Roles

This is where we get the playing XI with their match-specific roles (captain, keeper, etc.).

### 2.1 Team Players Entry (content.matchPlayers.teamPlayers[])

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `teamPlayers[].team.objectId` | int | `1298768` | ESPN team ID. | ALREADY HAVE |
| `teamPlayers[].team.longName` | str | `"Lucknow Super Giants"` | Full team name. | ALREADY HAVE |
| `teamPlayers[].players[]` | list | 12 entries | Players in the squad (playing XI + impact sub). | |

### 2.2 Individual Player Entry (content.matchPlayers.teamPlayers[].players[])

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `players[].playerRoleType` | str | `"C"`, `"WK"`, `"CWK"`, `"P"` | Match-specific role: C=captain, WK=keeper, CWK=captain+keeper, P=player. | ALREADY HAVE |
| `players[].isOverseas` | bool | `false` | Whether player is an overseas (non-domestic) player. Critical for squad composition analysis. | ADD |
| `players[].isWithdrawn` | bool | `false` | Whether player withdrew from the match. | SKIP |
| `players[].note` | null | | Player-specific notes (injury, etc.). | SKIP |
| `players[].player.objectId` | int | `1151286` | ESPN player ID. | ALREADY HAVE |
| `players[].player.name` | str | `"M Siddharth"` | Short name. | ALREADY HAVE |
| `players[].player.longName` | str | `"Manimaran Siddharth"` | Full name. | ALREADY HAVE |
| `players[].player.dateOfBirth` | dict | `{year: 1999, month: 11, date: 16}` | Date of birth (year/month/date). | ADD |
| `players[].player.dateOfDeath` | null | | Date of death (null for living). | SKIP |
| `players[].player.gender` | str | `"M"` | Gender. | SKIP |
| `players[].player.battingStyles` | list | `["rhb"]` | Batting hand: rhb, lhb. | ADD |
| `players[].player.bowlingStyles` | list | `["sla"]` | Bowling style codes: ob, sla, rmf, rf, lmf, rm, lb, lm, rsm, slo, etc. | ADD |
| `players[].player.longBattingStyles` | list | `["right-hand bat"]` | Human-readable batting style. | ADD |
| `players[].player.longBowlingStyles` | list | `["slow left-arm orthodox"]` | Human-readable bowling style. | ADD |
| `players[].player.countryTeamId` | int | `6` | ESPN ID of player's national team. Can derive nationality. | ADD |
| `players[].player.playerRoleTypeIds` | list | `[4]` | Numeric role type IDs. | SKIP |
| `players[].player.playingRoles` | list | `["bowler"]` | Human-readable playing roles. Values: "batter", "bowler", "allrounder", "batting allrounder", "bowling allrounder", "wicketkeeper batter", "wicketkeeper", "top-order batter", "middle-order batter", "opening batter". | ADD |
| `players[].player.slug` | str | `"manimaran-siddharth"` | URL slug. | SKIP |
| `players[].player.imageUrl` | str | | Player photo URL. | SKIP |
| `players[].player.headshotImageUrl` | str | | Headshot URL. | SKIP |
| `players[].player.image.*` | dict | | Photo metadata. | SKIP |
| `players[].player.headshotImage.*` | dict | | Headshot metadata. | SKIP |
| `players[].player.mobileName` | str | `"Siddharth"` | Short display name. | SKIP |
| `players[].player.indexName` | str | `"Siddharth, M"` | Alphabetical index name. | SKIP |
| `players[].player.battingName` | str | `"M Siddharth"` | Scorecard batting name. | SKIP |
| `players[].player.fieldingName` | str | `"Siddharth"` | Fielding record name. | SKIP |


---

## 3. content.innings[] — Scorecard Data

Two entries (one per innings). Contains full scorecard: batsmen, bowlers, partnerships, wickets, fall of wickets, DRS reviews, over-by-over data with per-ball spatial fields.

### 3.1 Innings Summary

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `innings[].inningNumber` | int | `1` | Innings number (1 or 2). | SKIP (have from Cricsheet) |
| `innings[].isCurrent` | bool | `false` | Whether this is the current/last innings. | SKIP |
| `innings[].team` | dict | | Batting team (full team object with objectId, name, etc.). | SKIP (have from Cricsheet) |
| `innings[].isBatted` | bool | `true` | Whether this innings was actually batted. | SKIP |
| `innings[].runs` | int | `181` | Total runs scored. | SKIP (have from Cricsheet) |
| `innings[].wickets` | int | `5` | Total wickets fallen. | SKIP (have from Cricsheet) |
| `innings[].lead` | int | `181` | Lead over opposition (181 for 1st innings = total, negative for 2nd if behind). | SKIP |
| `innings[].target` | int | `0` | Target to win (0 for 1st innings, set for 2nd). | SKIP (have from Cricsheet) |
| `innings[].overs` | int/float | `20` or `19.4` | Overs bowled (int if complete, float if partial e.g. 19.4). | SKIP (have from Cricsheet) |
| `innings[].balls` | int | `120` | Total balls bowled. | SKIP (derivable) |
| `innings[].totalOvers` | int | `20` | Total scheduled overs. | SKIP |
| `innings[].totalBalls` | int | `120` | Total scheduled balls. | SKIP |
| `innings[].minutes` | null | | Duration in minutes (null for T20s, populated for Tests). | SKIP |
| `innings[].extras` | int | `10` | Total extras. | SKIP (have from Cricsheet) |
| `innings[].byes` | int | `0` | Total byes. | SKIP (have from Cricsheet) |
| `innings[].legbyes` | int | `0` | Total leg byes. | SKIP (have from Cricsheet) |
| `innings[].wides` | int | `10` | Total wides. | SKIP (have from Cricsheet) |
| `innings[].noballs` | int | `0` | Total no balls. | SKIP (have from Cricsheet) |
| `innings[].penalties` | int | `0` | Total penalty runs. | SKIP (have from Cricsheet) |
| `innings[].event` | int | `5` | Event type code (internal). | SKIP |
| `innings[].ballsPerOver` | int | `6` | Balls per over. | SKIP |
| `innings[].fours` | null | | Total fours (null in this sample, may be populated elsewhere). | SKIP |
| `innings[].sixes` | null | | Total sixes (null in this sample). | SKIP |
| `innings[].runsSaved` | null | | Runs saved by fielding (null). Not derivable from any other source. | ADD |
| `innings[].catches` | null | | Total catches (null). | SKIP |
| `innings[].catchesDropped` | null | | Dropped catches (null). Not derivable from any other source — unique fielding quality metric. | ADD |


### 3.2 Innings Batsmen (innings[].inningBatsmen[])

One entry per batsman who was listed in the playing XI (including subs who didn't bat).

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `inningBatsmen[].player` | dict | | Full player object (objectId, name, DOB, styles, roles). | (covered in player section) |
| `inningBatsmen[].playerRoleType` | str | `"CWK"` | Match role: C, WK, CWK, P. | ALREADY HAVE |
| `inningBatsmen[].battedType` | str | `"yes"`, `"sub"`, `"DNB"` | Whether player batted: "yes" = batted, "sub" = substitute (didn't bat), "DNB" = did not bat. | ADD |
| `inningBatsmen[].runs` | int | `81` | Runs scored (null if didn't bat). | SKIP (have from Cricsheet) |
| `inningBatsmen[].balls` | int | `56` | Balls faced (null if didn't bat). | SKIP (have from Cricsheet) |
| `inningBatsmen[].minutes` | int | `76` | Time at crease in minutes. Not available in Cricsheet. | ADD |
| `inningBatsmen[].fours` | int | `8` | Number of fours hit. | SKIP (have from Cricsheet) |
| `inningBatsmen[].sixes` | int | `5` | Number of sixes hit. | SKIP (have from Cricsheet) |
| `inningBatsmen[].strikerate` | float | `144.64` | Strike rate (runs/balls * 100). | SKIP (derivable) |
| `inningBatsmen[].isOut` | bool | `true` | Whether batsman was dismissed. | SKIP (have from Cricsheet) |
| `inningBatsmen[].dismissalType` | int | `1` | Numeric dismissal type code (1=caught, etc.). | SKIP (have from Cricsheet) |
| `inningBatsmen[].dismissalBatsman` | dict | | Player object of dismissed batsman (same as player for most). | SKIP |
| `inningBatsmen[].dismissalBowler` | dict | | Player object of bowler who took the wicket. | SKIP (have from Cricsheet) |
| `inningBatsmen[].dismissalFielders` | list | | Fielder(s) involved in dismissal. | SKIP (have from Cricsheet) |
| `inningBatsmen[].dismissalText` | dict | | Structured dismissal text with short/long/commentary/fielderText/bowlerText. Useful for future NLP analysis. | ADD |
| `inningBatsmen[].dismissalComment` | list | | Rich text commentary about the dismissal. | SKIP |add it, could be useful if we ever do nlp
| `inningBatsmen[].fowOrder` | int | `3` | Fall of wicket order (0-indexed). | SKIP |
| `inningBatsmen[].fowWicketNum` | int | `4` | Wicket number (1-indexed). | SKIP |
| `inningBatsmen[].fowRuns` | int | `143` | Team score when this wicket fell. | SKIP (derivable from Cricsheet) |
| `inningBatsmen[].fowBalls` | null | | Balls bowled when wicket fell (often null). | SKIP |
| `inningBatsmen[].fowOvers` | float | `16.4` | Over.ball when wicket fell. | SKIP |
| `inningBatsmen[].fowOverNumber` | int | `17` | Over number (1-indexed). | SKIP |
| `inningBatsmen[].ballOversActual` | float | `16.4` | Over.ball of dismissal delivery. | SKIP |
| `inningBatsmen[].ballOversUnique` | float | `16.04` | Unique over representation. | SKIP |
| `inningBatsmen[].ballTotalRuns` | int | `143` | Team total at dismissal. | SKIP |
| `inningBatsmen[].ballBatsmanRuns` | int | `0` | Runs scored on dismissal ball. | SKIP |
| `inningBatsmen[].videos` | list | `[]` | Related video highlights. | SKIP |
| `inningBatsmen[].images` | list | `[]` | Related photos. | SKIP |
| `inningBatsmen[].currentType` | null | | Current batting status (null for completed). | SKIP |


### 3.3 Innings Bowlers (innings[].inningBowlers[])

One entry per bowler who bowled in the innings.

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `inningBowlers[].player` | dict | | Full player object (objectId, name, DOB, styles, roles). | (covered in player section) |
| `inningBowlers[].bowledType` | str | `"yes"` | Whether bowler actually bowled: "yes" = bowled. | SKIP |
| `inningBowlers[].overs` | int | `4` | Complete overs bowled. | SKIP (have from Cricsheet) |
| `inningBowlers[].balls` | int | `24` | Total balls bowled. | SKIP (have from Cricsheet) |
| `inningBowlers[].maidens` | int | `0` | Maiden overs. Trivially derivable from Cricsheet ball-by-ball. | SKIP |
| `inningBowlers[].conceded` | int | `39` | Runs conceded. | SKIP (have from Cricsheet) |
| `inningBowlers[].wickets` | int | `1` | Wickets taken. | SKIP (have from Cricsheet) |
| `inningBowlers[].economy` | float | `9.75` | Economy rate. | SKIP (derivable) |
| `inningBowlers[].runsPerBall` | float | `1.62` | Runs per ball. | SKIP (derivable) |
| `inningBowlers[].dots` | int | `11` | Dot balls bowled. Derivable from Cricsheet ball-by-ball (batter_runs=0, no extras). | SKIP |
| `inningBowlers[].fours` | int | `3` | Fours conceded. | SKIP (derivable from Cricsheet) |
| `inningBowlers[].sixes` | int | `3` | Sixes conceded. | SKIP (derivable from Cricsheet) |
| `inningBowlers[].wides` | int | `1` | Wides bowled. | SKIP (have from Cricsheet) |
| `inningBowlers[].noballs` | int | `0` | No balls bowled. | SKIP (have from Cricsheet) |
| `inningBowlers[].videos` | list | `[]` | Related video highlights. | SKIP |
| `inningBowlers[].images` | list | 1 entry | Related photos (action shots). | SKIP |
| `inningBowlers[].currentType` | null | | Current bowling status (null for completed). | SKIP |
| `inningBowlers[].inningWickets` | list | 1 entry | Detailed wicket info for each wicket this bowler took. Contains dismissalBatsman, dismissalType, fowOrder, fowWicketNum, fowRuns, fowOvers, dismissalComment (rich text). | SKIP (have from Cricsheet) |


### 3.4 Innings Partnerships (innings[].inningPartnerships[])

One entry per batting partnership in the innings.

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `inningPartnerships[].player1` | dict | | Full player object for first batsman. | |
| `inningPartnerships[].player2` | dict | | Full player object for second batsman. | |
| `inningPartnerships[].player1Runs` | int | `32` | Runs scored by player 1 during this partnership. | ADD |
| `inningPartnerships[].player1Balls` | int | `19` | Balls faced by player 1 during this partnership. | ADD |
| `inningPartnerships[].player2Runs` | int | `20` | Runs scored by player 2 during this partnership. | ADD |
| `inningPartnerships[].player2Balls` | int | `14` | Balls faced by player 2 during this partnership. | ADD |
| `inningPartnerships[].runs` | int | `53` | Total partnership runs (includes extras). | ADD |
| `inningPartnerships[].balls` | int | `33` | Total balls in partnership. | ADD |
| `inningPartnerships[].overs` | float | `5.3` | Overs duration of partnership. | SKIP (derivable) |
| `inningPartnerships[].outPlayerId` | int | `60530` | ESPN player ID of the batsman who got out to end this partnership. | ADD |
| `inningPartnerships[].start` | null | | Partnership start state (null in this sample). | SKIP |
| `inningPartnerships[].end` | dict | | Partnership end state: `{oversActual, ballsActual, totalInningRuns, totalInningWickets}`. | SKIP |
| `inningPartnerships[].isLive` | bool | `false` | Whether partnership is ongoing. | SKIP |

Note: Partnership data is derivable from Cricsheet ball-by-ball data, but ESPN gives it pre-computed with individual contributions broken out. Useful for partnership analysis without recomputing from deliveries.


### 3.5 Innings Overs (innings[].inningOvers[]) — Over-by-Over Summary

One entry per over bowled. Contains per-over aggregates AND per-ball spatial data.

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `inningOvers[].overNumber` | int | `1` | Over number (1-indexed). | SKIP |
| `inningOvers[].overRuns` | int | `12` | Runs scored in this over. | SKIP (derivable) |
| `inningOvers[].overWickets` | int | `0` | Wickets in this over. | SKIP (derivable) |
| `inningOvers[].isComplete` | bool | `true` | Whether over was completed. | SKIP |
| `inningOvers[].totalBalls` | int | `6` | Balls bowled in this over (>6 if extras). | SKIP |
| `inningOvers[].totalRuns` | int | `12` | Cumulative runs at end of over. | SKIP |
| `inningOvers[].totalWickets` | int | `0` | Cumulative wickets at end of over. | SKIP |
| `inningOvers[].overRunRate` | int | `12` | Run rate for this over. | SKIP |
| `inningOvers[].bowlers` | list | 1 entry | Bowler(s) for this over (usually 1, can be 2 if bowler changed mid-over). | SKIP |
| `inningOvers[].requiredRunRate` | int | `0` | Required run rate at this point (0 for 1st innings). | SKIP |
| `inningOvers[].requiredRuns` | int | `0` | Runs needed (0 for 1st innings). | SKIP |
| `inningOvers[].remainingBalls` | int | `114` | Balls remaining in innings. | SKIP |
| `inningOvers[].events` | list | `[]` | Special events during the over (strategic timeouts, etc.). | SKIP |

#### Over-Level Predictions

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `inningOvers[].predictions.score` | int | `177` | Predicted final innings score at end of this over. | ADD |
| `inningOvers[].predictions.winProbability` | float | `55.04` | Win probability for batting team at end of this over (0-100). | ADD |


### 3.6 Per-Ball Data (innings[].inningOvers[].balls[]) — THE GOLD MINE

This is the most valuable section. Every ball bowled has spatial, shot, and prediction data that does NOT exist in Cricsheet.

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `balls[].id` | int | `45747699` | ESPN's unique ball ID. | ADD |
| `balls[]._uid` | int | `45747699` | Same as id. | SKIP |
| `balls[].inningNumber` | int | `1` | Innings number. | SKIP (context) |
| `balls[].overNumber` | int | `1` | Over number (1-indexed). | SKIP (context) |
| `balls[].ballNumber` | int | `1` | Ball number within the over (1-indexed). | SKIP (context) |
| `balls[].oversActual` | float | `0.1` | Over.ball in decimal (0.1 = over 1, ball 1). | SKIP |
| `balls[].oversUnique` | float | `0.01` | Unique over representation. | SKIP |
| `balls[].ballsActual` | null | | Alternate ball representation (often null). | SKIP |
| `balls[].ballsUnique` | null | | Alternate unique representation (often null). | SKIP |
| `balls[].batsmanPlayerId` | int | `58406` | ESPN player ID of batter on strike. | ADD |
| `balls[].nonStrikerPlayerId` | int | `60530` | ESPN player ID of non-striker. | SKIP |
| `balls[].bowlerPlayerId` | int | `62587` | ESPN player ID of bowler. | ADD |
| `balls[].outPlayerId` | null/int | `null` | ESPN player ID of dismissed batter (null if not out). | SKIP (have from Cricsheet) |
| `balls[].batsmanRuns` | int | `0` | Runs scored by batter off this ball. | SKIP (have from Cricsheet) |
| `balls[].totalRuns` | int | `0` | Total runs off this ball (batter + extras). | SKIP (have from Cricsheet) |
| `balls[].isFour` | bool | `false` | Whether this ball was a four. | SKIP (have from Cricsheet) |
| `balls[].isSix` | bool | `false` | Whether this ball was a six. | SKIP (have from Cricsheet) |
| `balls[].isWicket` | bool | `false` | Whether a wicket fell on this ball. | SKIP (have from Cricsheet) |
| `balls[].dismissalType` | null/int | `null` | Numeric dismissal type (null if not out). | SKIP (have from Cricsheet) |
| `balls[].wides` | int | `0` | Wide runs on this ball. | SKIP (have from Cricsheet) |
| `balls[].noballs` | int | `0` | No ball runs on this ball. | SKIP (have from Cricsheet) |
| `balls[].byes` | int | `0` | Bye runs on this ball. | SKIP (have from Cricsheet) |
| `balls[].legbyes` | int | `0` | Leg bye runs on this ball. | SKIP (have from Cricsheet) |
| `balls[].penalties` | int | `0` | Penalty runs on this ball. | SKIP (have from Cricsheet) |
| `balls[].totalInningRuns` | int | `0` | Cumulative innings total after this ball. | SKIP |
| `balls[].totalInningWickets` | int | `0` | Cumulative wickets after this ball. | SKIP |
| `balls[].timestamp` | null/str | `null` | ISO timestamp of when ball was bowled (often null for older matches). | SKIP | i think we should keep this, it will help in finding weather information atnthat time
| `balls[].modified` | str | `"2024-04-02T14:00:34.000Z"` | When this ball record was last modified. | SKIP | idk what this means and how it is different from the above one

#### Spatial / Shot Fields (NOT in Cricsheet — unique to ESPN)

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `balls[].wagonX` | int | `233` | X coordinate on wagon wheel diagram (0-300 range). Where the ball went after being hit. 150 = center of pitch. | ADD |
| `balls[].wagonY` | int | `165` | Y coordinate on wagon wheel diagram (0-300 range). 0 = bowler's end, 300 = behind batter. | ADD |
| `balls[].wagonZone` | int | `2` | Wagon wheel zone (0-8). 0 = dot ball / no shot played. Zones 1-8 map to fielding regions around the ground. | ADD |
| `balls[].pitchLine` | str | `"OUTSIDE_OFFSTUMP"` | Line of delivery. Values: DOWN_LEG, ON_THE_STUMPS, OUTSIDE_OFFSTUMP, WIDE_DOWN_LEG, WIDE_OUTSIDE_OFFSTUMP. Available from ~2015. | ADD |
| `balls[].pitchLength` | str | `"GOOD_LENGTH"` | Length of delivery. Values: FULL, FULL_TOSS, GOOD_LENGTH, SHORT, SHORT_OF_A_GOOD_LENGTH, YORKER. Available from ~2015. | ADD |
| `balls[].shotType` | str | `"PUSH"` | Type of shot played. Modern values (2015+): COVER_DRIVE, CUT_SHOT, DAB, DEFENDED, FLICK, HOOK, LEFT_ALONE, LEG_GLANCE, ON_DRIVE, PULL, PUSH, RAMP, REVERSE_SWEEP, SLOG_SHOT, SLOG_SWEEP, SQUARE_DRIVE, STEERED, STRAIGHT_DRIVE, SWEEP_SHOT, UPPER_CUT. Legacy values (2008-era): CUT_SHOT_ON_BACK_FOOT, FORWARD_DEFENCE, OFF_SIDE_DRIVE_ON_FRONT_FOOT, NO_SHOT, etc. | ADD |
| `balls[].shotControl` | int | `1` | Shot control rating. 1 = controlled, 2 = uncontrolled. Missing on wides (no shot played). Available from ~2015. | ADD |

#### Per-Ball Predictions

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `balls[].predictions.score` | int | `171` | Predicted final innings score after this ball. | ADD |
| `balls[].predictions.winProbability` | float | `48.3` | Win probability for batting team after this ball (0-100). | ADD |

#### Per-Ball Display Text

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `balls[].batsmanStatText.statInfo` | str | `"0* (1b)"` | Batter's current score at this point. | SKIP |
| `balls[].batsmanStatText.short` | str | `"Q de Kock 0* (1b)"` | Short batter stat line. | SKIP |
| `balls[].batsmanStatText.long` | str | `"Quinton de Kock 0* (1b)"` | Long batter stat line. | SKIP |
| `balls[].bowlerStatText.short` | str | `"RJW Topley 0.1-0-0-0"` | Short bowler figures at this point. | SKIP |
| `balls[].bowlerStatText.long` | str | `"Reece Topley 0.1-0-0-0"` | Long bowler figures. | SKIP |


### 3.7 Innings Wickets (innings[].inningWickets[])

Detailed wicket entries. Same data as inningBatsmen dismissal fields but organized by wicket order.

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `inningWickets[].player` | dict | | Full player object of dismissed batsman. | SKIP (have from Cricsheet) |
| `inningWickets[].playerRoleType` | str | `"CWK"` | Match role of dismissed player. | SKIP |
| `inningWickets[].battedType` | str | `"yes"` | Whether player batted. | SKIP |
| `inningWickets[].runs` | int | `20` | Runs scored by dismissed batsman. | SKIP (have from Cricsheet) |
| `inningWickets[].balls` | int | `14` | Balls faced. | SKIP (have from Cricsheet) |
| `inningWickets[].minutes` | int | `26` | Time at crease in minutes. | ADD (same as batsmen minutes) |
| `inningWickets[].fours` | int | `0` | Fours hit. | SKIP |
| `inningWickets[].sixes` | int | `2` | Sixes hit. | SKIP |
| `inningWickets[].strikerate` | float | `142.85` | Strike rate. | SKIP |
| `inningWickets[].isOut` | bool | `true` | Always true in this array. | SKIP |
| `inningWickets[].dismissalType` | int | `1` | Numeric dismissal code. | SKIP |
| `inningWickets[].dismissalBatsman` | dict | | Player object of dismissed batter. | SKIP |
| `inningWickets[].dismissalBowler` | dict | | Player object of bowler. | SKIP |
| `inningWickets[].dismissalFielders` | list | | Fielder(s) involved. | SKIP |
| `inningWickets[].dismissalText` | dict | | Structured text: short ("caught"), long ("c Dagar b Maxwell"), commentary (full scorecard line), fielderText, bowlerText. | SKIP |
| `inningWickets[].dismissalComment` | list | | Rich HTML commentary about the dismissal. | SKIP | This is importatn, include this as well
| `inningWickets[].fowOrder` | int | `0` | Fall of wicket order (0-indexed). | SKIP |
| `inningWickets[].fowWicketNum` | int | `1` | Wicket number (1-indexed). | SKIP |
| `inningWickets[].fowRuns` | int | `53` | Team score when wicket fell. | SKIP |
| `inningWickets[].fowOvers` | float | `5.3` | Over.ball when wicket fell. | SKIP |
| `inningWickets[].fowOverNumber` | int | `6` | Over number (1-indexed). | SKIP |
| `inningWickets[].fowBalls` | null | | Balls bowled (often null). | SKIP |
| `inningWickets[].ballOversActual` | float | `5.3` | Over.ball of dismissal delivery. | SKIP |
| `inningWickets[].ballOversUnique` | float | `5.03` | Unique over representation. | SKIP |
| `inningWickets[].ballTotalRuns` | int | `53` | Team total at dismissal. | SKIP |
| `inningWickets[].ballBatsmanRuns` | int | `0` | Runs on dismissal ball. | SKIP |
| `inningWickets[].videos` | list | `[]` | Related videos. | SKIP |
| `inningWickets[].images` | list | 1 entry | Related photos. | SKIP |
| `inningWickets[].currentType` | null | | Current status. | SKIP |

### 3.8 Fall of Wickets (innings[].inningFallOfWickets[])

Compact fall-of-wickets summary. Subset of inningWickets data.

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `inningFallOfWickets[].dismissalBatsman` | dict | | Abbreviated player object (id, objectId, name, longName, slug, imageUrl, headshotImageUrl). | SKIP |
| `inningFallOfWickets[].fowType` | int | `1` | Fall of wicket type. | SKIP |
| `inningFallOfWickets[].fowOrder` | int | `0` | Order (0-indexed). | SKIP |
| `inningFallOfWickets[].fowWicketNum` | int | `1` | Wicket number (1-indexed). | SKIP |
| `inningFallOfWickets[].fowRuns` | int | `53` | Team score at fall. | SKIP (derivable from Cricsheet) |
| `inningFallOfWickets[].fowOvers` | float | `5.3` | Over.ball at fall. | SKIP (derivable from Cricsheet) |
| `inningFallOfWickets[].fowBalls` | null | | Balls at fall (often null). | SKIP |


### 3.9 DRS Reviews (innings[].inningDRSReviews[])

Decision Review System data. More structured than Cricsheet's review field.

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `inningDRSReviews[].decisionChallengeType` | int | `2` | Challenge type code. | SKIP |
| `inningDRSReviews[].decisionChallengeSubType` | int | `18` | Challenge sub-type code. | SKIP |
| `inningDRSReviews[].reviewTeam` | dict | | Team that requested the review (objectId, name, abbreviation). | SKIP (have from Cricsheet) |
| `inningDRSReviews[].umpire` | dict | | Umpire whose decision was challenged. | SKIP (have from Cricsheet) |
| `inningDRSReviews[].batsman` | dict | | Batsman involved in the review. | SKIP (have from Cricsheet) |
| `inningDRSReviews[].bowler` | dict | | Bowler involved in the review. | SKIP |
| `inningDRSReviews[].oversActual` | float | `14.5` | Over.ball when review was taken. | SKIP (have from Cricsheet) |
| `inningDRSReviews[].ballsActual` | null | | Ball number (often null). | SKIP |
| `inningDRSReviews[].reviewSide` | str | `"bowling"` | Which side reviewed: "bowling" or "batting". | ADD |
| `inningDRSReviews[].resultType` | str | `"upheld"` | Review result: "upheld" (original decision stands) or "overturned". | SKIP (have from Cricsheet) |
| `inningDRSReviews[].isUmpireCall` | bool | `false` | Whether it was "umpire's call" (marginal decision, review retained). | ADD |
| `inningDRSReviews[].remainingCount` | int | `2` | Reviews remaining for the team after this review. | ADD |
| `inningDRSReviews[].originalDecision` | str | `"called"` | Umpire's original on-field decision: "called" (given out) or "notcalled" (not out). | ADD |
| `inningDRSReviews[].drsDecision` | str | `"notcalled"` | DRS final decision: "called" (out) or "notcalled" (not out). | ADD |

### 3.10 Over Groups (innings[].inningOverGroups[])

Phase-wise breakdown: powerplay, middle overs, death overs.

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `inningOverGroups[].type` | str | `"POWERPLAY"` | Phase type: POWERPLAY, MIDDLE_OVERS, FINAL_OVERS. | ADD |
| `inningOverGroups[].inningNumber` | int | `1` | Innings number. | SKIP |
| `inningOverGroups[].startOverNumber` | int | `1` | First over of this phase (1-indexed). | ADD |
| `inningOverGroups[].endOverNumber` | int | `6` | Last over of this phase. | ADD |
| `inningOverGroups[].oversRuns` | int | `54` | Runs scored in this phase. | ADD |
| `inningOverGroups[].oversWickets` | int | `1` | Wickets lost in this phase. | ADD |
| `inningOverGroups[].totalRuns` | int | `54` | Cumulative runs at end of phase. | SKIP |
| `inningOverGroups[].totalWickets` | int | `1` | Cumulative wickets at end of phase. | SKIP |
| `inningOverGroups[].isComplete` | bool | `true` | Whether phase was completed. | SKIP |
| `inningOverGroups[].topBatsmen` | list | 1 entry | Top batter in this phase with runs/balls/fours/sixes. | SKIP (derivable) |
| `inningOverGroups[].topBowlers` | list | 1 entry | Top bowler in this phase with overs/maidens/conceded/wickets. | SKIP (derivable) |

Note: Phase data is derivable from Cricsheet ball-by-ball, but ESPN gives it pre-computed. The phase boundaries (powerplay overs 1-6, middle 7-16, death 17-20) are format-specific and may vary for non-T20 formats.


---

## 4. content — Other Sections

### 4.1 Match Player Awards (content.matchPlayerAwards[])

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `matchPlayerAwards[].type` | str | `"PLAYER_OF_MATCH"` | Award type. | SKIP (have from Cricsheet) |
| `matchPlayerAwards[].player` | dict | | Full player object of award winner. | SKIP (have from Cricsheet) |
| `matchPlayerAwards[].team` | dict | | Team of award winner. | SKIP |
| `matchPlayerAwards[].inningStats` | list | 1 entry | Stats summary for the award winner. | SKIP |

### 4.2 Notes (content.notes)

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `notes.groups` | list | | Array of note groups. Each has `type` and `notes` (array of strings). Contains powerplay info, strategic timeout info, innings break details. | SKIP |

### 4.3 Super Over Innings (content.superOverInnings)

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `superOverInnings` | list | `[]` | Empty for non-super-over matches. Would contain same structure as innings[] for super over. | SKIP (have from Cricsheet) |

### 4.4 Close of Play (content.closeOfPlay)

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `closeOfPlay` | null | | Close of play summary (null for T20s, used in Tests). | SKIP |


---

## 5. content.supportInfo — Surrounding Context

### 5.1 Most Valued Player (content.supportInfo.mostValuedPlayerOfTheMatch)

ESPN's own MVP calculation based on "impact" scoring.

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `mostValuedPlayerOfTheMatch.player` | dict | | Full player object. | |
| `mostValuedPlayerOfTheMatch.team` | dict | | Player's team. | |
| `mostValuedPlayerOfTheMatch.battedType` | str | `"DNB"` | Whether MVP batted. | SKIP |
| `mostValuedPlayerOfTheMatch.runs` | int | `0` | Runs scored. | SKIP |
| `mostValuedPlayerOfTheMatch.ballsFaced` | int | `0` | Balls faced. | SKIP |
| `mostValuedPlayerOfTheMatch.smartRuns` | int | `0` | ESPN's "smart runs" metric. | ADD |
| `mostValuedPlayerOfTheMatch.bowledType` | str | `"yes"` | Whether MVP bowled. | SKIP |
| `mostValuedPlayerOfTheMatch.fieldedType` | str | `"yes"` | Whether MVP fielded. | SKIP |
| `mostValuedPlayerOfTheMatch.wickets` | int | `3` | Wickets taken. | SKIP |
| `mostValuedPlayerOfTheMatch.conceded` | int | `14` | Runs conceded. | SKIP |
| `mostValuedPlayerOfTheMatch.smartWickets` | float | `4.5` | ESPN's "smart wickets" metric (quality-adjusted). | ADD |
| `mostValuedPlayerOfTheMatch.totalImpact` | float | `117.34` | Total impact score (ESPN's proprietary metric). | ADD |
| `mostValuedPlayerOfTheMatch.battingImpact` | int | `0` | Batting impact component. | ADD |
| `mostValuedPlayerOfTheMatch.bowlingImpact` | float | `117.34` | Bowling impact component. | ADD |

### 5.2 Series Standings (content.supportInfo.seriesStandings)

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `seriesStandings.series` | dict | 25 keys | Full series object. | SKIP |
| `seriesStandings.notes` | str | | Standings notes (points system explanation). | SKIP |
| `seriesStandings.groups` | list | 1 entry | Standings groups (contains team standings with points, NRR, etc.). | SKIP |
| `seriesStandings.teamsToQualifyCount` | int | `0` | Teams that qualify from this group. | SKIP |
| `seriesStandings.available` | dict | 8 keys | Available standings columns. | SKIP |
| `seriesStandings.finalMatches` | list | `[]` | Final/playoff matches. | SKIP |
| `seriesStandings.liveTeamIds` | list | `[]` | Currently playing team IDs. | SKIP |
| `seriesStandings.objects` | dict | 1 key | Related objects. | SKIP |

### 5.3 Stories & Media

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `supportInfo.stories` | list | 5 entries | Related ESPN articles. | SKIP |
| `supportInfo.videos` | list | 3 entries | Related video highlights. | SKIP |
| `supportInfo.seriesStories` | list | `[]` | Series-level stories. | SKIP |
| `supportInfo.recentReportStory` | dict | 33 keys | Most recent match report article. | SKIP |
| `supportInfo.recentPreviewStory` | dict | 33 keys | Most recent match preview article. | SKIP |
| `supportInfo.liveBlogStory` | dict | 33 keys | Live blog article. | SKIP |
| `supportInfo.fantasyPickStory` | null | | Fantasy picks article. | SKIP |
| `supportInfo.social` | null | | Social media links. | SKIP |

### 5.4 Surrounding Matches

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `supportInfo.teamsPrevMatches` | dict | 2 keys | Previous match for each team (keyed by ESPN team ID). | SKIP |
| `supportInfo.teamsNextMatches` | dict | 2 keys | Next match for each team. | SKIP |
| `supportInfo.seriesPrevMatches` | list | 2 entries | Previous matches in the series. | SKIP |
| `supportInfo.seriesNextMatches` | list | 2 entries | Next matches in the series. | SKIP |

### 5.5 Other Support Info

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `supportInfo.playersOfTheMatch` | list | 1 entry | Player of the match (same as matchPlayerAwards). | SKIP |
| `supportInfo.playersOfTheSeries` | null | | Player of the series (null mid-season). | SKIP |
| `supportInfo.matchSeriesResult` | null | | Series result (null mid-season). | SKIP |
| `supportInfo.liveInfo` | null | | Live match info (null for completed). | SKIP |
| `supportInfo.liveSummary` | null | | Live summary (null for completed). | SKIP |
| `supportInfo.superOverLiveSummary` | null | | Super over live summary. | SKIP |
| `supportInfo.superOver` | bool | `false` | Whether match had super over. | SKIP |
| `supportInfo.weather` | null | | Weather data (null in this sample, may be populated for some matches). | ADD (if populated) |
| `supportInfo.bet365Odds` | null | | Betting odds. | SKIP |
| `supportInfo.hasTeamSquads` | bool | `true` | Whether squad data is available. | SKIP |
| `supportInfo.hasStats` | bool | `true` | Whether stats are available. | SKIP |
| `supportInfo.hasFantasyStats` | bool | `false` | Whether fantasy stats exist. | SKIP |
| `supportInfo.hasFanComments` | bool | `false` | Whether fan comments exist. | SKIP |
| `supportInfo.hasPolls` | bool | `true` | Whether polls exist. | SKIP |


---

## 6. Ball-Level Commentary API Fields (from scroll-based scraping)

These fields come from the ESPN commentary API (captured via Playwright route interception, NOT from `__NEXT_DATA__`). They are the same spatial fields as section 3.6 above, plus additional commentary-specific fields. See `docs/espn-ball-data-scraping.md` for the scraping approach.

| Field | Type | Example | Description | Verdict |
|-------|------|---------|-------------|---------|
| `id` | int | `45747699` | Unique ESPN ball ID. Same as balls[].id in scorecard. | ADD |
| `inningNumber` | int | `2` | Innings number. | SKIP |
| `overNumber` | int | `18` | Over number (1-indexed). | SKIP |
| `ballNumber` | int | `3` | Ball within over. | SKIP |
| `oversActual` | float | `17.3` | Over.ball decimal. | SKIP |
| `oversUnique` | float | `17.03` | Unique over representation. | SKIP |
| `batsmanPlayerId` | int | `58406` | ESPN batter ID. | ADD |
| `bowlerPlayerId` | int | `62587` | ESPN bowler ID. | ADD |
| `nonStrikerPlayerId` | int | `60530` | ESPN non-striker ID. | SKIP |
| `batsmanRuns` | int | `4` | Batter runs. | SKIP |
| `totalRuns` | int | `4` | Total runs. | SKIP |
| `totalInningRuns` | int | `145` | Cumulative innings total. | SKIP |
| `totalInningWickets` | int | `7` | Cumulative wickets. | SKIP |
| `isFour` | bool | `true` | Four flag. | SKIP |
| `isSix` | bool | `false` | Six flag. | SKIP |
| `isWicket` | bool | `false` | Wicket flag. | SKIP |
| `wides` | int | `0` | Wide runs. | SKIP |
| `noballs` | int | `0` | No ball runs. | SKIP |
| `byes` | int | `0` | Bye runs. | SKIP |
| `legbyes` | int | `0` | Leg bye runs. | SKIP |
| `penalties` | int | `0` | Penalty runs. | SKIP |
| `dismissalType` | null/int | | Dismissal type code. | SKIP |
| `dismissalText` | null/str | `"caught"` | Human-readable dismissal. | SKIP |
| `outPlayerId` | null/int | | Dismissed player ESPN ID. | SKIP |
| `wagonX` | int | `233` | Wagon wheel X (0-300). | ADD |
| `wagonY` | int | `165` | Wagon wheel Y (0-300). | ADD |
| `wagonZone` | int | `2` | Wagon wheel zone (0-8). | ADD |
| `pitchLine` | str | `"OUTSIDE_OFFSTUMP"` | Delivery line. | ADD |
| `pitchLength` | str | `"GOOD_LENGTH"` | Delivery length. | ADD |
| `shotType` | str | `"PUSH"` | Shot type. | ADD |
| `shotControl` | int | `1` | Shot control (1=controlled, 2=uncontrolled). | ADD |
| `timestamp` | str/null | `"2024-04-02T14:00:34.000Z"` | Ball timestamp. | SKIP |
| `title` | str | `"Bumrah to Kohli, FOUR"` | Human-readable ball description. | SKIP |
| `commentTextItems` | list | | Array of commentary text objects (rich text). | SKIP |
| `smartStats` | list | | Contextual stats shown during commentary (e.g. "Kohli averages 45.2 in powerplay"). | SKIP |
| `predictions` | dict | | Win probability and predicted score. | ADD (same as 3.6) |

Note: The commentary API fields are a superset of the scorecard per-ball fields. The spatial/shot fields are identical. The commentary API adds `title`, `commentTextItems`, `smartStats`, and `dismissalText` as a string (vs the scorecard's structured dict).


---

## 7. Summary: Fields Worth Adding

Grouped by enrichment priority. Fields marked ADD above, organized by what they enable.

### Tier 1: Unique, High-Value (not in Cricsheet, not derivable)

**Per-ball spatial data** (from scorecard or commentary API):
- `wagonX`, `wagonY`, `wagonZone` — wagon wheel coordinates and zone
- `pitchLine`, `pitchLength` — delivery line and length (from ~2015)
- `shotType` — type of shot played (from 2008, naming varies)
- `shotControl` — controlled vs uncontrolled (from ~2015)
- `predictions.score`, `predictions.winProbability` — per-ball win probability and predicted score

**Player biographical data** (from any player object):
- `dateOfBirth` (year/month/date) — player age analysis
- `battingStyles` / `longBattingStyles` — left-hand vs right-hand bat
- `bowlingStyles` / `longBowlingStyles` — bowling type (pace, spin, etc.)
- `playingRoles` — official playing role (batter, bowler, allrounder, etc.)
- `countryTeamId` — player nationality
- `isOverseas` — overseas player flag (from matchPlayers)

**Match timing**:
- `match.endTime` — match end time (enables match duration calculation)
- `match.hoursInfo` — session timing breakdown

**ESPN impact metrics**:
- `mostValuedPlayerOfTheMatch.totalImpact` — ESPN's proprietary impact score
- `mostValuedPlayerOfTheMatch.battingImpact` / `bowlingImpact` — component scores
- `mostValuedPlayerOfTheMatch.smartRuns` / `smartWickets` — quality-adjusted metrics

### Tier 2: Useful Enrichment (adds context beyond Cricsheet)

**Innings-level**:
- `inningBatsmen[].minutes` — time at crease (not in Cricsheet)
- `inningBowlers[].maidens` — maiden overs (derivable but tedious)
- `inningBowlers[].dots` — dot balls bowled

**Partnership data**:
- `inningPartnerships[]` — pre-computed partnership breakdowns with individual contributions

**DRS enrichment**:
- `inningDRSReviews[].isUmpireCall` — umpire's call flag
- `inningDRSReviews[].remainingCount` — reviews remaining
- `inningDRSReviews[].originalDecision` / `drsDecision` — structured decision data
- `inningDRSReviews[].reviewSide` — which side reviewed

**Phase data**:
- `inningOverGroups[]` — powerplay/middle/death overs breakdown (derivable but pre-computed)

**Over-level predictions**:
- `inningOvers[].predictions` — predicted score and win probability per over

### Tier 3: Nice to Have

**Venue**:
- `match.ground.objectId` — ESPN venue ID (for cross-referencing)
- `match.ground.capacity` — stadium capacity
- `match.ground.town.timezone` — venue timezone

**Team**:
- `teams[].isHome` — home team flag
- `teams[].team.primaryColor` — team brand color (for UI)
- `teams[].points` — points earned

**Match**:
- `match.debutPlayers` — debut player list (if populated)
- `match.statusData.statusTextLangData.wonByBalls` — balls remaining when won by wickets
- `match.replacementPlayers[]` — impact player substitution details (over, inning, players)

**Weather**:
- `supportInfo.weather` — weather data (null in sample, may be populated for some matches)

### Already Captured

These fields are already extracted by our existing `match_scraper.py`:
- `espn_match_id`, `espn_series_id`, `slug`, `title`, `statusText`
- `floodlit`, `startDate`, `startTime`, `season`
- `team1/2_name`, `team1/2_espn_id`, `team1/2_captain`, `team1/2_keeper`
- `teams_enrichment_json` (full player roles per team)

