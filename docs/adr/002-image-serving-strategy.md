# ADR-002: Image Serving Strategy

## Status
Accepted

## Date
2026-04-17

## Context

The platform has ~500 player headshots, 14 team logos, and venue photos stored locally
in `data/images/` (downloaded from ESPN's Cloudinary CDN during enrichment). These images
need to be served to the Next.js frontend.

Key constraints:
- Zero cost (free tier everything)
- API on Render free tier (sleeps after 15 min idle, ~30s cold start)
- Frontend on Vercel free tier (CDN-backed static assets)
- Player image count will grow to 1000+ as more leagues are added
- Team logos are stable (~14 files, rarely changes)

## Decision

**Hybrid approach: static for team logos, API-served for player images.**

### Team logos (14 files, ~1MB total)
- Copied to `apps/web/public/teams/{espn_id}.png`
- Committed to git
- Served directly by Next.js / Vercel CDN
- Zero API dependency — logos load even when API is sleeping

### Player images (500+ files, ~100MB total)
- Served through FastAPI endpoint: `GET /api/v1/images/players/{espn_id}.png`
- Reads from `data/images/players/` on disk
- Returns `Cache-Control: public, max-age=86400, immutable`
- Not committed to git (stays in gitignored `data/` directory)

### Why not commit all images to git?
500+ player PNGs at ~200KB each = ~100MB. Git stores every version of every binary
forever. Adding/updating images across seasons would bloat the repo significantly.
14 team logos (~1MB) is acceptable; 500+ player images is not.

### Why not hotlink ESPN's Cloudinary CDN?
- ESPN controls those URLs and can revoke access anytime
- Hotlinking third-party CDN bandwidth without permission is bad practice
- Can't control image transforms, caching, or availability
- Portfolio project should demonstrate data ownership, not dependency

## Future: Dedicated Image CDN (Phase 2+)

When the project scales beyond IPL (more leagues, 2000+ players), migrate to a
dedicated image CDN. Recommended options (all free tier):

### Cloudflare R2 (recommended)
- 10GB storage free, zero egress fees
- Custom domain support
- S3-compatible API (easy upload scripting)
- Workflow: enrichment pipeline uploads to R2, frontend references R2 URLs

### Cloudinary (alternative)
- 25GB storage + 25GB bandwidth/month free
- Built-in image transforms (resize, format conversion, face detection)
- Already familiar — ESPN uses Cloudinary under the hood

### Migration path
1. Current: team logos in `public/`, player images via FastAPI
2. Next: add `make sync-images` target to automate team logo copy
3. Future: upload all images to R2/Cloudinary during enrichment pipeline
4. Future: frontend references CDN URLs directly, API no longer serves images

## Consequences

### Positive
- Team logos load instantly (CDN-served, no API dependency)
- Player images work without committing 100MB+ to git
- Clear migration path to production-grade CDN
- API image endpoint has path traversal protection (numeric ID validation)

### Negative
- Player images depend on API being awake (Render cold start affects first load)
- Team logos need manual re-copy when new teams are added (`cp data/images/teams/*.png apps/web/public/teams/`)
- Two different serving mechanisms for the same type of asset (images)

### Neutral
- 1-day cache on player images is a reasonable tradeoff (images rarely change)
- Git repo grows by ~1MB for team logos (negligible)
