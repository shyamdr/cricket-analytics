# Contributing

Setup and workflow for developing on cricket-analytics.

## Prerequisites

- Python 3.11+ (project is developed on 3.13, CI tests on 3.11 and 3.13)
- `git`
- Node.js 20+ only if touching the Next.js frontend in `apps/web/`
- Docker optional (for `docker compose up` workflow)
- Disk: ~1GB for the built DuckDB + raw downloads

## First-time setup

```bash
git clone https://github.com/shyamdr/cricket-analytics.git
cd cricket-analytics
python3 -m venv .venv
source .venv/bin/activate
make setup            # installs [all] extras + pre-commit hooks
make all              # ingest + dbt build — takes 2-3 minutes
```

`make all` downloads Cricsheet data, loads into DuckDB bronze, and runs dbt through silver and gold. When it completes you'll have `data/cricket.duckdb` (~400MB) with IPL + T20I bronze and IPL gold.

## Running things

```bash
make api              # FastAPI on :8000
make ui               # Streamlit on :8501 (legacy, internal)
make dagster          # Dagster webserver on :3000
make web              # Next.js dev server on :3000 (run `make web-setup` once first)
```

The FastAPI API serves the Next.js frontend. Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `apps/web/.env.local` when running both locally.

## Before pushing

```bash
make check            # runs lint + unit tests — same checks as CI
```

This is the minimum. Pre-commit hooks also run `ruff check` and `ruff format` on staged files. Install them with `make setup` if you haven't.

For anything touching silver/gold models or enrichment:

```bash
make dbt-test         # 59 dbt tests
make test             # 117 pytest tests (unit + integration + smoke)
```

## Code style

- **Formatting:** `ruff format` (black-compatible). Run `make format` to auto-format.
- **Linting:** `ruff check` with rules: E, W, F, I, N, UP, B, SIM, TCH, RUF. E501 (line length) is ignored.
- **Types:** `from __future__ import annotations` at the top of every Python file. Type hints required on all function signatures.
- **Logging:** `structlog.get_logger()`. Keyword-style args: `logger.info("loaded matches", count=1169)`, not printf-style.
- **SQL in Python:** parameterized queries with `$1, $2, ...`. Never f-string user input into SQL.
- **Table references:** import from `src/tables.py`, don't build f-strings with `settings.gold_schema`.
- **DuckDB connections:** use `write_conn()` context manager or `get_read_conn()` / `get_query_fn()`. Never call `duckdb.connect()` directly.

## Where to add things

- **New Cricsheet dataset (BBL, PSL, etc.)** — add to `config/datasets.yml`, no code change needed
- **New API endpoint** — new route in the relevant `src/api/routers/*.py`; add integration test in `tests/integration/test_api.py`
- **New dbt silver/gold model** — add to `src/dbt/models/silver/` or `src/dbt/models/gold/`, update `schema.yml` with description + tests
- **New enrichment source** — module in `src/enrichment/`, Dagster asset in `src/orchestration/assets/enrichment.py`, bronze table in `src/database.py` DDL, silver model gated behind `source_exists` macro
- **New frontend page** — `apps/web/src/app/**/page.tsx` (Next.js app router convention)
- **New seed CSV** — `src/dbt/seeds/`, reference via `{{ ref('seed_name') }}` in models
- **Architectural decision** — new ADR in `docs/adr/`, follow the format of existing ADRs (Status, Date, Context, Decision, Rationale, Consequences)

## Testing

Tests are organized by marker:
- `tests/unit/` — no DB, no network, pure logic. Runs on every PR.
- `tests/integration/` — requires `data/cricket.duckdb` built. Runs after DB build in CI.
- `tests/smoke/` — DB connectivity, API startup, imports. Runs after integration.

```bash
pytest -m unit            # fast, no DB
pytest -m integration     # requires `make all` first
pytest -m smoke
pytest tests/unit/test_ingestion.py::TestParseMatch::test_minimal  # single test
```

Add tests in the same file structure as the code you're testing. Name test functions `test_<behavior>`, not `test_<function_name>`.

## Data workflows

### Rebuild DuckDB from scratch
Delete the file and re-run:
```bash
rm data/cricket.duckdb
make all
```

### Add T20I to gold (not IPL only)
Edit `src/dbt/models/**/*.sql` if any filter assumes IPL, then:
```bash
make ingest PROFILE=standard      # IPL + T20I
make transform
```

Render deployment currently builds with `--profile minimal` (IPL only) to keep the baked-in DuckDB small. Update `render.yaml` when expanding.

### Run enrichment for a specific season
```bash
make enrich SEASON=2024
```

Runs ESPN match scraper for that season. To run all seasons: `make enrich` (no SEASON arg).

### Backfill ESPN ball data
```bash
python -m src.enrichment.run_ball_scraper --season 2024
```

Ball scraper is slower (~20 seconds per match) because it intercepts ESPN's commentary API one match at a time. Budget ~6 hours for a full IPL season.

## Git conventions

- Branch naming: descriptive kebab-case. No prefix convention enforced.
- Never commit directly to `main`. Push to a branch, open a PR.
- Commit message format: conventional commits
  - `feat: add standings endpoint`
  - `fix: correct NRR calculation for tied matches`
  - `refactor: extract weather description into dbt macro`
  - `docs: add ADR-005 on format-agnostic design`
  - `chore: bump ruff to 0.15.2`
- First line ≤70 chars. Use the body for detail (what + why, not how).
- Do not amend commits that have been pushed unless explicitly asked.

## CI

GitHub Actions runs three jobs on every push:
1. **lint** (Python 3.11) — `ruff check` + `ruff format --check`
2. **unit-tests** (Python 3.11 + 3.13 matrix) — `pytest -m unit`
3. **integration-tests** (Python 3.11 + 3.13 matrix) — builds DuckDB, runs `pytest -m "integration or smoke"` and `dbt test`

All three must pass for a PR to merge. pip cache is keyed on `pyproject.toml` hash.

## Deployments

- **Frontend** → Vercel (auto from `main` of `apps/web/` nested git)
- **API** → Render (auto from `main` of root repo; builds via `Dockerfile.api`)
- **Pipeline** → Local or CI only; not deployed continuously

Render API sleeps after 15 minutes of inactivity. First request after idle takes ~30 seconds.

## Where to find things

- Steering files (AI context, architecture decisions at a glance) — `.kiro/steering/`
- ADRs — `docs/adr/`
- Other docs — `docs/`
- Tests — `tests/`
- Config — `config/datasets.yml`
- Makefile — all common commands with `make help`

## Questions

- "How does X work?" — check `.kiro/steering/` first, then `docs/`, then the code
- "Why was X done this way?" — check `docs/adr/`
- "What's the current state?" — `.kiro/steering/progress.md`
- "What are all the API endpoints?" — `.kiro/steering/api-endpoints-reference.md`
- "What does this dbt model do?" — `.kiro/steering/dbt-models-reference.md` or the model's `schema.yml`
