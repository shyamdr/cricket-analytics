# Laptop Migration Guide

Complete step-by-step process for moving the project to a new laptop with zero data or context loss.
Every command below is copy-paste ready. Run them in **Terminal** (macOS built-in app: press ⌘+Space, type "Terminal", hit Enter).

Assumes macOS on Apple Silicon (M-series chip). If the new laptop is Intel, Homebrew's install path is `/usr/local/bin` instead of `/opt/homebrew/bin` — the install script auto-detects this, so no changes needed there, but some shell prompts below reference `/opt/homebrew`; replace with `/usr/local` if you're on Intel.

---

## What gets transferred automatically (via git)

Everything under `.git` tracking — which includes **all project context**:

- All source code (`src/`, `tests/`, `apps/web/`, `scripts/`, `config/`)
- All Kiro context: `.kiro/steering/` (5 files), `.kiro/hooks/` (3 files), `.kiro/specs/` (3 specs)
- All docs (`docs/`, `CONTRIBUTING.md`, `README.md`), all ADRs (001–005)
- CI config, pre-commit config, Docker files, pyproject.toml

When you clone the repo on the new laptop, every single file above comes along. No backup needed.

## What needs manual backup (not in git)

These three files are the complete manual-backup list. Upload all three from the old laptop to Google Drive.

| File | Size | Purpose |
|---|---|---|
| `~/Desktop/cricket-analytics-secrets.env` | <1 KB | API keys + frontend env vars |
| `~/Desktop/data-images.tar.gz` | 62 MB | ESPN image cache (808 files) |
| `data/cricket.duckdb` (inside project folder) | 1.3 GB | Full bronze+silver+gold DuckDB |

---

# PART A — On the OLD laptop

Nothing to do here. The handoff commit already pushed everything needed, and the two Desktop files (`cricket-analytics-secrets.env` + `data-images.tar.gz`) are already generated. Just upload these three files to Google Drive.

Sanity check before handing in the old laptop (open Terminal, paste each line):

```bash
cd ~/Personal\ Space/Projects/cricket-analytics
git status                         # output should be: "nothing to commit, working tree clean"
git log origin/main..HEAD          # output should be empty (nothing unpushed)
ls -lh ~/Desktop/cricket-analytics-secrets.env ~/Desktop/data-images.tar.gz
ls -lh data/cricket.duckdb
```

---

# PART B — On the NEW laptop

Every step is a Terminal command. Open Terminal (⌘+Space → "Terminal" → Enter) and paste each block.

## Step 1 — Download the three backup files from Google Drive

On the new laptop, download the three files into this exact structure:

```
~/Downloads/cricket-analytics-secrets.env
~/Downloads/cricket-analytics-backup/cricket.duckdb
~/Downloads/cricket-analytics-backup/data-images.tar.gz
```

Create the folder first (paste in Terminal):

```bash
mkdir -p ~/Downloads/cricket-analytics-backup
```

Then drag-drop the downloaded files into the right places through Finder, OR verify from Terminal:

```bash
ls -lh ~/Downloads/cricket-analytics-secrets.env \
       ~/Downloads/cricket-analytics-backup/cricket.duckdb \
       ~/Downloads/cricket-analytics-backup/data-images.tar.gz
```

All three files must show up. If any is missing, re-download before continuing.

## Step 2 — Install Xcode Command Line Tools

Homebrew and git both need this. Paste in Terminal:

```bash
xcode-select --install
```

A GUI popup will appear asking to install the command line tools. Click "Install". Wait a few minutes until it finishes. If you see "command line tools are already installed", that's fine — move on.

## Step 3 — Install Homebrew

Paste this exact command in Terminal. It's the official one-liner from https://brew.sh:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

It will prompt for your Mac password and take a few minutes. When done, it prints two commands to "add Homebrew to your PATH". Run both of them. On Apple Silicon they look like this — paste exactly:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Verify:

```bash
brew --version
```

Should print `Homebrew 4.x.x` or similar.

## Step 4 — Install Python 3.13, Node.js, and git via Homebrew

```bash
brew install python@3.13 node git
```

This takes a few minutes. Verify all three:

```bash
python3.13 --version    # should print Python 3.13.x
node --version          # should print v20.x or later
git --version           # should print git version 2.x
```

## Step 5 — Configure git with your identity

```bash
git config --global user.name "shyamdr"
git config --global user.email "shyamdrangapure@gmail.com"
git config --global init.defaultBranch main
```

## Step 6 — Install Kiro

Download from https://kiro.ai, install the `.dmg` (drag to Applications), open it, and sign in with the same account you use on this laptop.

## Step 7 — Clone the repo

```bash
mkdir -p ~/Personal\ Space/Projects
cd ~/Personal\ Space/Projects
git clone https://github.com/shyamdr/cricket-analytics.git
cd cricket-analytics
```

You should now be inside the project folder. Verify:

```bash
pwd
# should print: /Users/<your-user>/Personal Space/Projects/cricket-analytics

ls .kiro/steering
# should list 5 .md files (project-architecture, progress, etc.)
```

## Step 8 — Run the automated setup script

This one command restores secrets, DuckDB, images, creates the Python virtualenv, installs all Python + Node dependencies, and runs smoke tests to confirm everything works:

```bash
bash scripts/setup_new_laptop.sh \
  --secrets ~/Downloads/cricket-analytics-secrets.env \
  --backup-dir ~/Downloads/cricket-analytics-backup
```

It takes ~5-10 minutes. You'll see progress for each of the 6 steps. At the end it prints "Setup complete." If any step fails, it tells you which one and you can fix + rerun.

## Step 9 — Restore Kiro user-level MCP config

This one config file lives outside the repo in your home folder. Paste the whole block — it creates the file with the exact content from the old laptop:

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
  "powers": {
    "mcpServers": {}
  }
}
EOF
```

## Step 10 — Reinstall Kiro extensions

Open Kiro, click the Extensions icon in the sidebar, and install each of these:

- `dvirtz.parquet-viewer` — Parquet Viewer
- `mermaidchart.vscode-mermaid-chart` — Mermaid Chart
- `ms-python.python` — Python (installs debugpy automatically)
- `ms-toolsai.jupyter` — Jupyter (installs renderers, keymap, cell-tags, slideshow automatically)
- `ms-vscode.makefile-tools` — Makefile Tools
- `repreng.csv` — CSV Edit

## Step 11 — Final verification

Open the project in Kiro (File → Open Folder → select `cricket-analytics`). Then in Kiro's chat, ask:

> "What's the current state of the project?"

Kiro should answer from the steering files (progress.md, project-architecture.md, etc.) — summarizing the medallion architecture, 9 API routers, 21 dbt models, current phase, etc. If it does, all project context has transferred successfully.

Also verify the code works from Terminal:

```bash
cd ~/Personal\ Space/Projects/cricket-analytics
source .venv/bin/activate
make dbt-test         # 59 dbt tests should pass
make test             # 117 pytest tests should pass
```

Start the services to confirm they run:

```bash
make api              # FastAPI on http://localhost:8000/docs
# (open another Terminal tab, ⌘+T)
make web              # Next.js on http://localhost:3000
```

Open http://localhost:3000 — the InsideEdge site should load with real data (read from the restored DuckDB).

---

## Troubleshooting

**`brew: command not found` after install**
→ You missed Step 3's PATH commands. Close Terminal, reopen, and the `eval` line in `~/.zprofile` will run automatically. Verify with `brew --version`.

**`python3.13: command not found` after `brew install`**
→ Homebrew installs it as `python3.13`, not `python3`. The setup script uses `python3` which falls back to whatever Homebrew linked. If the script complains, run:
```bash
ln -sf /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3
```

**`npm install` fails in apps/web**
→ Node version mismatch. Next.js 16 needs Node 20+. Check with `node --version`. If below 20, reinstall with `brew install node@20 && brew link --overwrite node@20`.

**Playwright browsers missing**
→ The enrichment module uses Playwright. If you plan to run enrichment:
```bash
source .venv/bin/activate
python -m playwright install webkit
```

**Smoke tests fail with "data/cricket.duckdb not found"**
→ The DuckDB restore step in `setup_new_laptop.sh` skipped because the file wasn't in the backup dir. Check `~/Downloads/cricket-analytics-backup/cricket.duckdb` exists (exact filename, no extra `.zip` or whatever Google Drive added). If you need to rebuild from scratch instead:
```bash
source .venv/bin/activate
make ingest
make transform
```
This rebuilds bronze + silver + gold from Cricsheet (~5 min). You'll lose enrichment state unless you re-run `make enrich` (takes hours).

**Kiro doesn't load the project context**
→ Double-check `.kiro/steering/` has 5 `.md` files (`ls .kiro/steering`). If yes, restart Kiro (⌘+Q, reopen). Steering files auto-load when the project opens.

## Rollback

If anything goes wrong during migration, the old laptop still has everything. Nothing is deleted on the old laptop by this process. Take your time on the new one.
