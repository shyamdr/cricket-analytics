# Laptop Migration Guide

Complete checklist for moving the project to a fresh laptop with zero data or context loss.

## What gets transferred automatically (via git)

Everything under `.git` tracking — which includes **all project context**:

- All source code (`src/`, `tests/`, `apps/web/`, `scripts/`, `config/`)
- All Kiro context: `.kiro/steering/` (5 files), `.kiro/hooks/` (3 files), `.kiro/specs/` (3 specs)
- All docs (`docs/`, `CONTRIBUTING.md`, `README.md`)
- All ADRs (001–005)
- CI config, pre-commit config, Docker files, pyproject.toml

When you clone the repo on the new laptop, every single file above comes along. No backup needed.

## What needs manual backup (not in git)

These three items are the complete manual-backup list.

### 1. Secrets (tiny, critical)

File: `~/Desktop/cricket-analytics-secrets.env`

This is a merged file containing both `.env` (root) and `apps/web/.env.local` (frontend) values with `ROOT_ENV` / `WEB_ENV` prefixes. The setup script reads it and writes each line to the correct destination.

Put it somewhere you can reach from the new laptop: password manager, private encrypted note, or a private Google Drive folder (not public share).

### 2. Data — DuckDB file (1.3 GB)

File: `data/cricket.duckdb`

This is your entire bronze + silver + gold layer: 1169 matches, 278K deliveries, all enrichment. Upload to Google Drive.

Alternative: rebuild from scratch on the new laptop with `make all` (takes ~5 min for ingestion + dbt, plus ~hours for ESPN enrichment). Only choose this if you're OK losing the enrichment state.

### 3. Data — images tarball (67 MB, 808 files)

File: `~/Desktop/data-images.tar.gz`

ESPN-scraped player/team/ground images. These take hours to re-scrape. Upload to Google Drive.

## Migration steps

### Before leaving the old laptop

Already done by the handoff commit — just verify:

```bash
cd ~/Personal\ Space/Projects/cricket-analytics
git status                         # should be clean
git log origin/main..HEAD          # should be empty (nothing unpushed)
```

Also confirm these three files exist on your desktop, and upload to Google Drive:

```
~/Desktop/cricket-analytics-secrets.env       (already created by handoff script)
~/Desktop/data-images.tar.gz                  (already created by handoff script)
~/Personal Space/Projects/cricket-analytics/data/cricket.duckdb    (upload directly)
```

### On the new laptop

1. Install prerequisites:
   - Homebrew, then `brew install python@3.13 node git`
   - [Kiro](https://kiro.ai) + sign in

2. Configure git:
   ```bash
   git config --global user.name "shyamdr"
   git config --global user.email "shyamdrangapure@gmail.com"
   ```

3. Clone:
   ```bash
   mkdir -p ~/Personal\ Space/Projects
   cd ~/Personal\ Space/Projects
   git clone https://github.com/shyamdr/cricket-analytics.git
   cd cricket-analytics
   ```

4. Download from Google Drive to `~/Downloads/cricket-analytics-backup/`:
   - `cricket.duckdb`
   - `data-images.tar.gz`

5. Download the secrets file to `~/Downloads/cricket-analytics-secrets.env`.

6. Run the setup script — it restores secrets, data, installs Python + Node deps, and runs smoke tests:
   ```bash
   bash scripts/setup_new_laptop.sh \
     --secrets ~/Downloads/cricket-analytics-secrets.env \
     --backup-dir ~/Downloads/cricket-analytics-backup
   ```

7. Restore Kiro user-level MCP config (one file, not in the repo):
   ```bash
   mkdir -p ~/.kiro/settings
   cat > ~/.kiro/settings/mcp.json <<'EOF'
   {
     "mcpServers": {
       "fetch": {
         "command": "uvx",
         "args": ["mcp-server-fetch"],
         "env": {},
         "disabled": true,
         "autoApprove": []
       }
     },
     "powers": { "mcpServers": {} }
   }
   EOF
   ```

8. Reinstall Kiro extensions via the Extensions panel:
   - dvirtz.parquet-viewer
   - mermaidchart.vscode-mermaid-chart
   - ms-python.python + debugpy
   - ms-toolsai.jupyter + renderers/keymap/cell-tags/slideshow
   - ms-vscode.makefile-tools
   - repreng.csv

## Verification

After setup, the Kiro context should be fully in place. Open the project, ask Kiro "what's the current state of the project?" and it should answer from the steering files. Also verify:

```bash
source .venv/bin/activate
make dbt-test        # 59 dbt tests pass = DuckDB intact
make test            # 117 pytest tests pass = code + data intact
make api             # FastAPI starts
make web             # Next.js starts
```

## Rollback

If something goes wrong, the old laptop still has everything. Nothing is deleted until you're satisfied with the new setup.
