# ADR-003: Monorepo with Nested Frontend Git Repo

## Status
Accepted

## Date
2026-04-17

## Context

The project needs a Python data pipeline (ingestion, dbt, Dagster, FastAPI, Streamlit) and a Next.js frontend. Deployment targets differ: API goes to Render (Docker), frontend goes to Vercel (Git-integrated).

Two organizational options:
1. Single monorepo — Python + Next.js under one root
2. Two repos — `cricket-analytics` (backend) and `insideedge-web` (frontend)

For a solo developer, multi-repo coordination overhead (cross-repo PRs, version pinning, shared types) is pure waste. But Vercel's Git integration and `create-next-app` both expect the Next.js app to be a git repo root.

## Decision

**Monorepo with a nested `.git` inside `apps/web/`.**

- Root repo (`cricket-analytics`) tracks everything except `apps/web/.git/`
- `apps/web/` has its own `.git` folder — Vercel deploys from that
- Both push to separate GitHub repos: `shyamdr/cricket-analytics` and the Vercel-linked frontend repo

## Rationale

- One source of truth for architecture decisions, steering files, ADRs
- Atomic changes: API endpoint + frontend fetch can go in a single PR at root
- Shared TypeScript types can be generated from FastAPI OpenAPI spec if needed
- Vercel's Git integration works out-of-the-box because `apps/web/` is itself a git repo

## Consequences

### Positive
- Solo developer overhead stays low — one checkout, one IDE session
- Root repo stays clean of frontend's 600+ MB `node_modules/`
- Can work on API and frontend together without cross-repo PR dance

### Negative
- `git status` from root doesn't show changes inside `apps/web/` — easy to forget uncommitted frontend work
- Two separate commit histories for changes that span both sides
- Contributors need to understand "there's another git repo inside this one"
- Can't use git submodules cleanly (Vercel doesn't love submodules for root-of-repo builds)

### Mitigations
- Steering docs (progress.md, project-architecture.md) flag the nested `.git` explicitly
- Makefile targets (`make web`, `make web-build`) cd into the correct directory so surface-level workflow doesn't expose the split
- CI runs from root and tests only backend; frontend has its own Vercel build
