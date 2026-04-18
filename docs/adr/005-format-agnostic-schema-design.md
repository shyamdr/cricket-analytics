# ADR-005: Format-Agnostic Schema Design

## Status
Accepted

## Date
2026-04-17

## Context

The project started with IPL data. IPL is T20, 20 overs per innings, split-year seasons like `'2020/21'`, 10 teams since 2008. It would have been easy to encode IPL assumptions into silver and gold models:

- `CASE WHEN season = '2020/21' THEN '2021' ...` to normalize season strings
- `WHERE over_num <= 19` to filter to "valid" overs
- Hardcoded 20-over phase thresholds (powerplay 0-5, middle 6-14, death 15-19)
- Assuming `batter_runs <= 6` for validation tests
- Column-level constraints that assume T20 match duration

But the data platform supports 21 Cricsheet datasets including ODIs (50 overs), Tests (multi-day, no over cap), The Hundred (100 balls), and women's matches. Cross-format analysis is a first-class use case ("how does Kohli's T20I strike rate compare to his IPL strike rate?"). Hardcoding any one format poisons cross-format queries.

## Decision

**Every model, test, and derived column must work across all cricket formats and leagues without modification.**

This is a hard constraint, not a preference. Format-specific logic is rejected at code review (self-review, since solo).

## Rationale

Cricket's a 150-year-old sport with dozens of competing formats and rules. Any hardcoded assumption ("season is 4 digits", "max 20 overs", "6 runs is the max off one ball", "date range starts in 2008") will eventually break:
- Tests span multiple days and seasons; "season" is ambiguous
- BBL runs December-February; its split-year seasons are real, not data bugs
- The Hundred has 10-ball "overs" partway through
- No-balls can result in 7+ runs off a single ball
- Women's cricket has its own Cricsheet datasets with different coverage

The cost of format-agnostic design is small; the cost of retrofitting format-specific hacks is catastrophic.

## Patterns

### Season derivation
Use `EXTRACT(YEAR FROM match_date)`, not string parsing of the Cricsheet `season` field.
- IPL 2020/21 (played Sep-Nov 2020 in UAE) → `'2020'` ✓
- BBL 2020/21 (played Dec 2020 - Feb 2021) → `'2020'` or `'2021'` per match ✓
- IPL 2025 → `'2025'` ✓

The raw Cricsheet season is preserved in `season_raw` for reference queries, but the canonical `season` is date-derived. See `stg_matches.sql`.

### Phase classification
`fact_deliveries.phase` branches on `max_overs`:
- `20` → T20 rules (powerplay 0-5, middle 6-14, death 15-19)
- `50` → ODI rules (powerplay 0-9, middle 10-39, death 40-49)
- `100` → The Hundred (100-ball special case)
- Other (Tests, unknown) → `NULL`

New formats get new branches, not rewrites.

### Validation tests
Replace value-checking ("batter_runs ≤ 6", "max 20 overs") with relational checks:
- `total_runs = batter_runs + extras_runs` ✓ works for any format
- `runs_scored >= 0` ✓ works for any format
- `wickets <= 10` ✓ works for any format (but not T100/exhibition formats with fewer batters — revisit if added)
- Every completed match has ≥1 delivery ✓ works for any format

### Naming
- `max_overs`, not `t20_overs`
- `match_result_type` enum, not IPL-specific win categories
- `fact_batting_innings`, not `fact_t20_batting_innings`

### Config
`config/datasets.yml` treats all 21 Cricsheet datasets uniformly. No dataset gets special handling at ingestion.

## Consequences

### Positive
- Adding a new league (BBL, PSL, T20 World Cup) requires zero schema changes — just flip `enabled: true` in the YAML
- Cross-format analytics ("how does this player perform in T20Is vs IPL?") require no special-case logic
- Format-specific bugs surface as data quality issues, not code rewrites

### Negative
- Some code is slightly more verbose than format-specific equivalents (phase classification branches)
- Tests are relational not value-bound, so they won't catch "batter scored 15 off one ball in a T20 match" — but that's arguably not a test failure, it's a data issue to investigate
- Requires discipline every time a new feature is added — tempting to write `WHERE event_name = 'Indian Premier League'` and move on

### Non-goals
This ADR does not require:
- Every query to support every format (an IPL-specific dashboard is fine)
- Every derived column to be defined for every format (Test match "strike rate" uses different conventions — leave it NULL or document the definition)
- Retroactively abstracting IPL-specific dashboards or Streamlit pages

It only requires that core models, tests, and config remain format-agnostic.
