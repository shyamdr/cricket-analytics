# Cricket Analytics 🏏

An end-to-end cricket analytics platform built on IPL ball-by-ball data from [Cricsheet](https://cricsheet.org).

## Architecture

```
Cricsheet (JSON/CSV)
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

# Install and run full pipeline
make setup
make all        # downloads data + builds bronze/silver/gold layers

# Or with Docker
docker compose up
```

## Commands

```bash
make help       # show all available commands
make ingest     # download from Cricsheet → DuckDB bronze
make transform  # dbt run (bronze → silver → gold)
make test       # run pytest
make lint       # ruff check + ruff format
make api        # start FastAPI on :8000
make ui         # start Streamlit on :8501
```

## Data

All data is sourced from [Cricsheet](https://cricsheet.org) (CC BY 4.0 license):
- ~1169 IPL matches (2008–2025), ball-by-ball JSON
- Player registry CSV (16,000+ people)

Data is not stored in git — it's downloaded and rebuilt by the pipeline.

## Project Structure

```
src/
├── ingestion/      # download + load raw data into DuckDB
├── dbt/            # bronze → silver → gold transformations
├── orchestration/  # Dagster assets and jobs
├── api/            # FastAPI serving layer
├── ui/             # Streamlit app
└── ml/             # future ML models
```

## License

MIT
