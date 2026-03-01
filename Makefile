.PHONY: setup ingest transform test lint all api ui clean help dagster

PYTHON := python3
PIP := pip
DBT_DIR := src/dbt

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Install all dependencies
	$(PIP) install -e ".[all]"
	pre-commit install

ingest: ## Download data from Cricsheet and load into DuckDB bronze layer
	$(PYTHON) -m src.ingestion.run

transform: ## Run dbt transformations (seed + bronze → silver → gold)
	cd $(DBT_DIR) && dbt seed --profiles-dir . && dbt run --profiles-dir .

dbt-test: ## Run dbt tests
	cd $(DBT_DIR) && dbt test --profiles-dir .

dbt-docs: ## Generate and serve dbt docs
	cd $(DBT_DIR) && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .

test: ## Run pytest
	$(PYTHON) -m pytest tests/ -v

lint: ## Run linting (ruff check + ruff format check)
	ruff check src/ tests/
	ruff format --check src/ tests/

format: ## Auto-format code
	ruff check --fix src/ tests/
	ruff format src/ tests/

all: setup ingest transform ## Full pipeline: setup + ingest + transform

dagster: ## Start Dagster webserver (orchestration UI)
	@mkdir -p .dagster
	export DAGSTER_HOME="$$(pwd)/.dagster" && dagster dev -m src.orchestration

api: ## Start FastAPI server
	uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload

ui: ## Start Streamlit app
	streamlit run src/ui/app.py --server.port 8501

clean: ## Remove generated data and build artifacts
	rm -rf data/
	rm -rf src/dbt/target/ src/dbt/dbt_packages/ src/dbt/logs/
	rm -rf .pytest_cache/ htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
