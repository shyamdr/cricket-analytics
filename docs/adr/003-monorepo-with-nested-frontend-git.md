# ADR-003: Monorepo with Frontend Under apps/web

## Status
Accepted (superseded the earlier nested-git variant on 2026-04-22)

## Date
2026-04-17 (original), 2026-04-22 (revised)

## Context

The project needs a Python data pipeline (ingestion, dbt, Dagster, FastAPI, Streamlit) and a Next.js frontend. Deployment targets differ: API goes to Render (Docker), frontend goes to Vercel (Git-integrated).

Two organizational options:
1. Single monorepo — Python + Next.js under one root
2. Two repos — `cricket-analytics` (backend) and `insideedge-web` (frontend)

For a solo developer, multi-repo coordination overhead (cross-repo PRs, version pinning, shared types) is pure waste.

## Decision

**Single monorepo. The Next.js app lives at `apps/web/` and is tracked by the root repo. No nested `.git` folder.**

- Root repo (`shyamdr/cricket-analytics`) tracks everything including `apps/web/**` source files
- `apps/web/node_modules/` and `apps/web/.next/` are gitignored
- Vercel is configured to deploy from the root repo (`shyamdr/cricket-analytics`) with **Root Directory = `apps/web`** in Vercel project settings
- A single `git push` from the root updates both backend and frontend

## Rationale

- Vercel's Git integration supports monorepos directly via the "Root Directory" project setting — no nested git needed
- One source of truth: architecture decisions, steering files, ADRs, CI, and frontend/backend changes all live in one place
- Atomic changes: API endpoint + frontend fetch go in a single commit at the root
- Shared TypeScript types can be generated from FastAPI OpenAPI spec if needed
- `git status` from root shows all changes across the stack — no surprise uncommitted frontend work

## Historical Note

Earlier revision of this ADR (2026-04-17) described a nested `apps/web/.git` repo intended for Vercel. This was never actually used — the nested repo had no remote and Vercel was deploying from the root repo the whole time. The nested `.git` was a leftover from `create-next-app` and was removed on 2026-04-22 after it caused confusion (phantom uncommitted files, inability to see frontend state from root).

## Consequences

### Positive
- Solo developer overhead stays low — one checkout, one IDE session, one `git push`
- Root repo's `git status` is the single source of truth for what's committed
- CI runs from root; frontend builds on Vercel from `apps/web`
- Contributors only need to understand one git repo

### Negative
- `apps/web/node_modules/` still exists locally (must stay gitignored — 600+ MB)
- Vercel deploys everything when any file in the repo changes (can be mitigated with Vercel's "Ignored Build Step" setting if needed: `git diff --quiet HEAD^ HEAD -- apps/web`)

### Mitigations
- `.gitignore` covers `node_modules/`, `.next/`, `.vercel/`
- Makefile targets (`make web`, `make web-build`, `make web-setup`) cd into `apps/web` so surface-level workflow is ergonomic
