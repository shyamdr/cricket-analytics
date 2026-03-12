# Cricket Analytics 🏏

An end-to-end cricket analytics platform built on ball-by-ball data from [Cricsheet](https://cricsheet.org).

Supports 21 datasets across men's and women's cricket — T20 leagues, ODIs, Tests, and internationals. Dataset selection is controlled via a single YAML config file.

## Architecture

```
config/datasets.yml (what to ingest)
  → Ingestion (Python + httpx)
    → Bronze (DuckDB — raw staged data)
      → Silver (dbt — cleaned, typed, normalized)
        → Gold (dbt — aggregated, analytics-ready)
          → FastAPI (query API)
          → Streamlit (interactive UI)
```

## Tech Stack

| Layer | Tool |
|-------|------|
| Storage | DuckDB |
| Orchestration | Dagster |
| Transformation | dbt-core + dbt-duckdb |
| API | FastAPI |
| UI | Streamlit |
| CI/CD | GitHub Actions |

## Quick Start

```bash
# Clone and setup
git clone https://github.com/shyamdr/cricket-analytics.git
cd cricket-analytics
python -m venv .venv && source .venv/bin/activate

# Install and run full pipeline (uses default profile: IPL + T20I)
make setup
make all

# Or with Docker
docker compose up
```

## Commands

```bash
make help       # show all available commands
make ingest     # ingest datasets (default profile from config/datasets.yml)
make transform  # dbt run (bronze → silver → gold)
make test       # run pytest
make lint       # ruff check + ruff format
make enrich     # ESPN match enrichment (optional: SEASON=2024)
make api        # start FastAPI on :8000
make ui         # start Streamlit on :8501
make dagster    # start Dagster orchestration UI
```

## Dataset Configuration

All dataset selection is controlled by `config/datasets.yml`. To change what gets ingested, edit the YAML — no code changes needed.

```bash
# Use default profile (defined in datasets.yml)
make ingest

# Use a named profile
make ingest PROFILE=minimal     # IPL only
make ingest PROFILE=t20_all     # all T20 leagues + internationals
make ingest PROFILE=everything  # every available dataset

# Ingest specific datasets (overrides profile)
python -m src.ingestion.run --dataset ipl bbl psl

# Ingest all datasets with enabled: true
python -m src.ingestion.run --enabled

# List all available datasets and profiles
python -m src.ingestion.run --list
```

To add a new league, just flip `enabled: true` in the YAML or add it to a profile.

## Data

All data is sourced from [Cricsheet](https://cricsheet.org) (CC BY 4.0 license). 21 datasets available including IPL, T20I, BBL, PSL, CPL, ODI, Tests, WPL, WBBL, and more.

Data is not stored in git — it's downloaded and rebuilt by the pipeline.

## Project Structure

```
cricket-analytics/
├── config/             # datasets.yml — what to ingest and enrich
├── src/
│   ├── ingestion/      # download + load raw data into DuckDB
│   ├── dbt/            # bronze → silver → gold transformations
│   ├── orchestration/  # Dagster assets and jobs
│   ├── api/            # FastAPI serving layer
│   ├── ui/             # Streamlit app
│   └── ml/             # future ML models
├── tests/              # pytest (unit + integration + smoke)
└── data/               # .gitignored — DuckDB + raw downloads
```

## License

MIT
