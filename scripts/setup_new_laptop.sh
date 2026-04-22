#!/usr/bin/env bash
# Setup script for a fresh laptop checkout of cricket-analytics.
#
# What this script does:
#   1. Verifies prerequisites (Python 3.11+, Node 20+, git, uv or pip)
#   2. Restores .env and apps/web/.env.local from a secrets file you pass in
#   3. Restores data/cricket.duckdb and data/images/ from a backup directory
#   4. Creates the Python virtualenv and installs deps
#   5. Installs Next.js dependencies
#   6. Runs the smoke + dbt test suites to verify everything works
#
# Usage:
#   bash scripts/setup_new_laptop.sh \
#     --secrets /path/to/secrets.env \
#     --backup-dir /path/to/gdrive/backup
#
# The secrets.env file should contain BOTH sets of env vars in one file,
# prefixed so we know where each line goes:
#
#   ROOT_ENV GOOGLE_MAPS_API_KEY=...
#   WEB_ENV  NEXT_PUBLIC_API_URL=https://insideedge-api.onrender.com
#
# The backup directory should contain:
#   - cricket.duckdb
#   - data-images.tar.gz
#
set -euo pipefail

SECRETS_FILE=""
BACKUP_DIR=""
SKIP_TESTS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --secrets) SECRETS_FILE="$2"; shift 2 ;;
    --backup-dir) BACKUP_DIR="$2"; shift 2 ;;
    --skip-tests) SKIP_TESTS=true; shift ;;
    -h|--help)
      sed -n '2,28p' "$0"
      exit 0
      ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

step() { echo; echo "━━━ $1 ━━━"; }
ok() { echo "  ✓ $1"; }
warn() { echo "  ⚠ $1"; }
fail() { echo "  ✗ $1"; exit 1; }

# ─── Step 1: verify prerequisites ────────────────────────────────────────────
step "1/6 Verifying prerequisites"

command -v git >/dev/null || fail "git not installed"
ok "git: $(git --version)"

command -v python3 >/dev/null || fail "python3 not installed (need 3.11+)"
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [[ $PY_MAJOR -lt 3 || ($PY_MAJOR -eq 3 && $PY_MINOR -lt 11) ]]; then
  fail "Python $PY_VERSION found — need 3.11+"
fi
ok "python: $(python3 --version)"

command -v node >/dev/null || fail "node not installed (need 20+)"
ok "node: $(node --version)"

command -v npm >/dev/null || fail "npm not installed"
ok "npm: $(npm --version)"

# ─── Step 2: restore secrets ─────────────────────────────────────────────────
step "2/6 Restoring secrets (.env files)"

if [[ -z "$SECRETS_FILE" ]]; then
  warn "No --secrets flag provided; skipping .env restore"
  warn "You will need to create .env and apps/web/.env.local manually"
else
  if [[ ! -f "$SECRETS_FILE" ]]; then
    fail "Secrets file not found: $SECRETS_FILE"
  fi

  # Parse secrets.env — lines starting with ROOT_ENV go to .env, WEB_ENV to apps/web/.env.local
  : > .env
  : > apps/web/.env.local
  while IFS= read -r line; do
    [[ -z "$line" || "$line" =~ ^# ]] && continue
    if [[ "$line" =~ ^ROOT_ENV[[:space:]]+(.+)$ ]]; then
      echo "${BASH_REMATCH[1]}" >> .env
    elif [[ "$line" =~ ^WEB_ENV[[:space:]]+(.+)$ ]]; then
      echo "${BASH_REMATCH[1]}" >> apps/web/.env.local
    fi
  done < "$SECRETS_FILE"
  ok "wrote .env ($(wc -l < .env) lines)"
  ok "wrote apps/web/.env.local ($(wc -l < apps/web/.env.local) lines)"
fi

# ─── Step 3: restore data ────────────────────────────────────────────────────
step "3/6 Restoring data (DuckDB + images)"

mkdir -p data

if [[ -z "$BACKUP_DIR" ]]; then
  warn "No --backup-dir flag provided; skipping data restore"
  warn "Run 'make ingest' and re-run enrichment to rebuild data/ from scratch"
else
  if [[ ! -d "$BACKUP_DIR" ]]; then
    fail "Backup directory not found: $BACKUP_DIR"
  fi

  if [[ -f "$BACKUP_DIR/cricket.duckdb" ]]; then
    cp "$BACKUP_DIR/cricket.duckdb" data/cricket.duckdb
    DUCKDB_SIZE=$(du -h data/cricket.duckdb | cut -f1)
    ok "restored data/cricket.duckdb ($DUCKDB_SIZE)"
  else
    warn "cricket.duckdb not found in backup dir; will need to rebuild via 'make ingest && make transform'"
  fi

  if [[ -f "$BACKUP_DIR/data-images.tar.gz" ]]; then
    tar -xzf "$BACKUP_DIR/data-images.tar.gz" -C data
    IMAGE_COUNT=$(find data/images -type f 2>/dev/null | wc -l | tr -d ' ')
    ok "restored data/images/ ($IMAGE_COUNT files)"
  else
    warn "data-images.tar.gz not found; will need to re-scrape from ESPN"
  fi
fi

# ─── Step 4: Python deps ─────────────────────────────────────────────────────
step "4/6 Installing Python dependencies"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  ok "created .venv"
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -e ".[all]" >/dev/null
ok "installed Python packages"

# ─── Step 5: Node deps ───────────────────────────────────────────────────────
step "5/6 Installing frontend dependencies"

(cd apps/web && npm install --silent)
ok "installed npm packages"

# ─── Step 6: smoke test ──────────────────────────────────────────────────────
if [[ "$SKIP_TESTS" == "true" ]]; then
  step "6/6 Tests skipped (--skip-tests)"
else
  step "6/6 Running smoke tests"

  if [[ -f data/cricket.duckdb ]]; then
    pytest -m smoke -q 2>&1 | tail -5 || warn "smoke tests failed — investigate"
    ok "smoke tests done"

    (cd src/dbt && dbt test --quiet 2>&1 | tail -3) || warn "dbt tests failed — investigate"
    ok "dbt tests done"
  else
    warn "data/cricket.duckdb missing — cannot run integration/dbt tests yet"
    pytest -m unit -q 2>&1 | tail -5 || warn "unit tests failed"
    ok "unit tests done"
  fi
fi

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Setup complete."
echo
echo "Next steps:"
echo "  source .venv/bin/activate"
echo "  make api                 # start FastAPI server"
echo "  make web                 # start Next.js dev server"
echo "  make dagster             # start Dagster webserver"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
