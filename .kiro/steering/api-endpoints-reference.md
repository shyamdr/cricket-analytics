# InsideEdge API — Endpoint Reference

FastAPI app at `src/api/app.py`. 9 routers under `/api/v1/*` plus a health check at `/`.

- Base URL (prod): `https://insideedge-api.onrender.com`
- Base URL (local): `http://localhost:8000`
- OpenAPI docs: `/docs` (interactive) and `/openapi.json` (spec)
- All endpoints are GET. CORS allows `insideedge.vercel.app` (+ preview deploys) and `localhost:3000`.
- Dependency injection: every router receives `db: DbQuery` via `Depends(get_query_fn)`. Tests override with `app.dependency_overrides[get_query_fn]`.
- Table constants: imported from `src/tables.py` (e.g. `MATCHES`, `PLAYERS`, `BATTING_INNINGS`), not built inline from `settings.gold_schema`.

## Health

| Method | Path | Handler | Returns |
|---|---|---|---|
| GET | `/` | `root()` | `{"status": "ok", "service": "insideedge-api"}` |

## Players (`src/api/routers/players.py`, prefix `/api/v1/players`)

| Path | Handler | Query params | Purpose |
|---|---|---|---|
| `GET /` | `list_players` | `search`, `limit` (1-500, def 50), `offset` | List/search players by name (ILIKE) |
| `GET /{player_name}` | `get_player` | — | Player profile row from `dim_players`. 404 if missing |
| `GET /{player_name}/batting` | `get_player_batting` | `season`, `limit`, `offset` | Per-match batting innings from `fact_batting_innings` |
| `GET /{player_name}/bowling` | `get_player_bowling` | `season`, `limit`, `offset` | Per-match bowling innings from `fact_bowling_innings` |

## Teams (`src/api/routers/teams.py`, prefix `/api/v1/teams`)

| Path | Handler | Query params | Purpose |
|---|---|---|---|
| `GET /` | `list_teams` | — | All teams from `dim_teams`, ordered by name |
| `GET /{team_name}` | `get_team` | — | Team row from `dim_teams`. 404 if missing |
| `GET /{team_name}/matches` | `get_team_matches` | `season`, `limit`, `offset` | Matches where team1=X or team2=X |

## Matches (`src/api/routers/matches.py`, prefix `/api/v1/matches`)

| Path | Handler | Query params | Purpose |
|---|---|---|---|
| `GET /` | `list_matches` | `season`, `venue` (ILIKE), `limit`, `offset` | List matches from `dim_matches` |
| `GET /seasons` | `list_seasons` | — | All seasons with match counts |
| `GET /venues` | `list_venues` | — | All venues from `dim_venues` |
| `GET /recent` | `recent_matches_with_scores` | `limit` (1-50, def 10) | Recent matches + 2 innings scores + top 2 batters/bowlers per innings. Used by frontend home page |
| `GET /by-tournament` | `matches_by_tournament` | `days` (1-365, def 30) | Recent matches grouped by `event_name`. Cutoff date computed in Python (not SQL INTERVAL) |
| `GET /{match_id}` | `get_match` | — | Match row from `dim_matches`. 404 if missing |
| `GET /{match_id}/summary` | `get_match_summary` | — | Both innings team totals from `fact_match_summary` |
| `GET /{match_id}/batting` | `get_match_batting` | — | All batters' innings for the match |
| `GET /{match_id}/bowling` | `get_match_bowling` | — | All bowlers' innings for the match |

## Batting analytics (`src/api/routers/batting.py`, prefix `/api/v1/batting`)

| Path | Handler | Query params | Purpose |
|---|---|---|---|
| `GET /top` | `top_run_scorers` | `season`, `limit` (1-100, def 10) | Top run scorers with team (latest batting_team), innings, runs, SR, 4s, 6s |
| `GET /stats/{player_name}` | `player_batting_stats` | — | Career totals: innings, runs, HS, avg, SR, 4s, 6s, dots, 50s, 100s |
| `GET /season-breakdown/{player_name}` | `player_season_breakdown` | — | Per-season totals for a batter |

Note: `top_run_scorers` joins `dim_players` to get `espn_player_id` for frontend image lookups.

## Bowling analytics (`src/api/routers/bowling.py`, prefix `/api/v1/bowling`)

| Path | Handler | Query params | Purpose |
|---|---|---|---|
| `GET /top` | `top_wicket_takers` | `season`, `limit` (1-100, def 10) | Top wicket takers with bowling team (derived from `dim_matches.team1/team2` vs `batting_team`) |
| `GET /stats/{player_name}` | `player_bowling_stats` | — | Career totals: innings, wickets, runs, avg, econ, best, dots, wides, no-balls |
| `GET /season-breakdown/{player_name}` | `player_bowling_season_breakdown` | — | Per-season totals for a bowler |

## Standings (`src/api/routers/standings.py`, prefix `/api/v1/standings`)

| Path | Handler | Query params | Purpose |
|---|---|---|---|
| `GET /` | `get_standings` | `season` (required) | Points table: played, won, lost, NR, points (2·W + NR), NRR. Returns `[]` if ≤ 2 teams (bilateral series) |

NRR = (runs_for / overs_faced) − (runs_against / overs_bowled). Built from `dim_matches` + `fact_match_summary`.

## Images (`src/api/routers/images.py`, prefix `/api/v1/images`)

| Path | Handler | Purpose |
|---|---|---|
| `GET /{category}/{image_id}.png` | `get_image` | Serve cached PNG from `data/images/{category}/{image_id}.png` |

- Valid categories: `players`, `teams`, `grounds`, `venues`
- `image_id` must be all digits (ESPN ID) — path traversal guard
- Cache-Control: `public, max-age=86400, immutable`
- 404 on invalid category or missing file; 400 on non-numeric ID

## News (`src/api/routers/news.py`, prefix `/api/v1/news`)

| Path | Handler | Query params | Purpose |
|---|---|---|---|
| `GET /` | `get_news` | `limit` (1-30, def 10) | Proxy ESPN Cricinfo RSS: `title, description, link, image, pub_date` |

- Source: `https://www.espncricinfo.com/rss/content/story/feeds/0.xml`
- Timeout: 10s. Returns `[]` on HTTP error or parse error (no exception propagated)

## Conventions across routers

- Parameterized queries use `$1, $2, ...` (DuckDB positional placeholders). Never string interpolation of user input.
- Dynamic WHERE clause building (e.g. `list_matches`) tracks `idx` counter and appends to `params` list.
- Pagination default: `limit=50`, `offset=0`. Max limit varies: 500 for listings, 100 for analytics, 50 for recent, 30 for news.
- `ILIKE` used for case-insensitive name/venue search.
- Path params with spaces (e.g. `/players/V Kohli`) are passed as-is — FastAPI URL-decodes them.
- 404 pattern: check `if not rows:` after query, raise `HTTPException(404)`. Used for `get_player`, `get_team`, `get_match`.
- Response shape: list of dicts for collection endpoints, single dict for detail endpoints, empty list for "no data" (not 404) on analytics endpoints like standings.

## What's NOT here

- No POST/PUT/DELETE — read-only API
- No auth — public endpoints
- No Pydantic response models yet — deferred until gold schema stabilizes post-enrichment (see progress.md P2 backlog)
- No SSE / WebSocket — Phase 2 (live match data) not started
- No ML inference endpoints — Phase 3 not started
