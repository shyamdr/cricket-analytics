# Image & Visual Assets Strategy

## Overview

Player headshots, team logos, and country flags sourced from ESPN Cricinfo.
Images are **downloaded and self-hosted** — zero runtime dependency on ESPN's CDN.
All transforms (crop, resize, format conversion) happen at build time or display time
using Next.js `<Image>` component and CSS.

### Why Self-Host (not hotlink ESPN CDN)

The original approach hotlinked ESPN's Cloudinary CDN (`img1.hscicdn.com`) with URL-based
transforms. This creates fragile runtime dependencies:

- ESPN can block hotlinking, change CDN structure, or rate-limit at any time
- `e_background_removal` is an expensive AI transform — ESPN throttles concurrent requests
  (observed: 40 simultaneous requests → random failures/drops)
- `p.imgci.com` already returns 403 for direct access — only `img1.hscicdn.com/image/upload/` works
- If ESPN goes down or changes anything, the entire site's images break

Self-hosting eliminates all of this. One-time download, serve from our own infrastructure.

### Self-Hosting Architecture

```
Scrape (one-time + delta)                    Serve (runtime)
─────────────────────────                    ───────────────
ESPN player page                             Next.js <Image>
  → Playwright extracts __NEXT_DATA__          → reads from data/images/players/
  → Downloads PNG via Cloudinary URL           → auto-generates WebP, resizes
  → Saves to data/images/players/{id}.png      → serves optimized variants
  → Records metadata in bronze.espn_images     → CSS handles circular crop, effects
```

## Self-Hosted Image Pipeline

### What to Download

For each player, download **one high-quality PNG** with background already removed by
ESPN's Cloudinary AI. This gives us a transparent-background image we can crop/resize
ourselves without needing any AI processing locally.

**Download transform:** `f_png,e_background_removal,q_auto`
- `f_png` — PNG format, preserves transparency
- `e_background_removal` — let ESPN's Cloudinary AI remove the background once
- `q_auto` — auto quality optimization (smaller file, no visible quality loss)

**Which source image to use (priority order):**
1. `headshotImageUrl` (`.png`, 600×436 original) — formal cutout, already transparent.
   Background removal is a no-op but harmless. Best quality.
2. `imageUrl` (`.1.png`/`.2.png`, 160×136 original) — small cutout. Background removal
   helps clean up any remaining artifacts. Lower quality due to small source.
3. `imageUrl` (`.jpg`, action photo) — needs background removal. Quality varies.

### Storage

```
data/images/
├── players/          # Player headshots — {espn_id}.png
│   ├── 5390.png      # AC Gilchrist
│   ├── 32540.png     # CA Pujara
│   ├── 230558.png    # SP Narine
│   └── ...           # ~939 files
├── teams/            # Team logos — {espn_object_id}.png
│   ├── 335974.png    # Chennai Super Kings
│   └── ...           # ~133 files
└── venues/           # Venue photos — {espn_object_id}.png (future)
    └── ...
```

- Location: `data/images/` (gitignored, alongside DuckDB)
- Format: PNG (transparency preserved)
- Naming: `{espn_id}.png` — simple, deterministic, no slugs or name collisions
- Estimated size: ~939 players × ~200KB avg = **~188MB**
- Fits in Docker image alongside DuckDB (~50MB compressed)

### Why PNG (not WebP)

- PNG is the **archival master** — lossless, universal, preserves transparency
- WebP/AVIF conversion happens at **serve time** via Next.js `<Image>` component
  (automatic format negotiation based on browser support)
- Storing WebP would lock us into one optimized format — PNG gives flexibility
- PNG is what ESPN serves natively for cutouts — no transcoding artifacts

### Download Pipeline

The existing `image_scraper.py` already scrapes player pages and extracts image URLs.
The change: after extracting URLs, also **download the actual image file** via HTTP GET
from ESPN's Cloudinary CDN (no Playwright needed for the download — just the URL).

**Flow per player:**
1. Visit `https://www.espncricinfo.com/cricketers/player-{key_cricinfo}` (Playwright)
2. Extract `headshotImageUrl` and `imageUrl` from `__NEXT_DATA__`
3. Pick best source: `headshotImageUrl` if available, else `imageUrl`
4. Construct download URL: `https://img1.hscicdn.com/image/upload/f_png,e_background_removal,q_auto{path}`
5. HTTP GET the image (plain `httpx` or `aiohttp` — no browser needed for CDN)
6. Save to `data/images/players/{espn_id}.png`
7. Record metadata in `bronze.espn_images` (same as before, plus `local_path` column)

**Delta logic:** Skip download if `data/images/players/{espn_id}.png` already exists on disk.
Re-download only if `--full-refresh` is passed.

**Rate limiting:** Same circuit breaker as existing scraper. Page scraping is the bottleneck
(2s delay between pages). Image download is a simple CDN GET — much faster, no rate limit concern.

**Batch strategy (safe rollout):**
1. Test with `--limit 1` — single player, verify file saves correctly
2. Increase to `--limit 10` — verify batch behavior
3. Run full pipeline via Dagster — ~939 players, ~45 min

### Transforms at Display Time (Next.js)

With the downloaded PNG as the master, all display variants are generated at serve time:

| Use Case | How | Tool |
|----------|-----|------|
| Card (300×400) | `<Image width={300} height={400} style={{objectFit:'cover'}}/>` | Next.js |
| Thumbnail (48×48) | `<Image width={48} height={48}/>` | Next.js |
| WebP conversion | Automatic — Next.js serves WebP to supporting browsers | Next.js |
| Circular crop | `border-radius: 50%` in CSS | CSS |
| Vibrance / contrast | `filter: saturate(1.3) contrast(1.1)` | CSS |
| Wide banner | `<Image>` with `objectFit: cover` + aspect ratio container | CSS |
| Grayscale | `filter: grayscale(1)` — works in CSS even though ESPN blocks it | CSS |
| Blur (placeholder) | `placeholder="blur"` prop on `<Image>` | Next.js |

Key insight: CSS `filter` gives us grayscale, sepia, brightness, contrast — all the effects
ESPN's Cloudinary blocks. We don't need their server-side processing anymore.

### Serving from API (for non-Next.js consumers)

The FastAPI API can serve images directly:
```
GET /images/players/{espn_id}.png → data/images/players/{espn_id}.png
```
With `Cache-Control: public, max-age=31536000` (1 year — images rarely change).

Or bake images into the Docker image alongside DuckDB for zero-latency serving.

### Fallback Strategy

For players with no image at all (<5%):
- Generate initials-based avatar (e.g., "VK" for V Kohli)
- Use CSS with team primary color as background
- Same pattern as GitHub, Slack, Google — looks intentional, not broken

### Migration Path

1. ✅ Current: `bronze.espn_images` stores CMS paths (URLs only) — 71 players scraped
2. → Next: Add image download step — save PNGs to `data/images/players/`
3. → Next: Add `local_path` column to `bronze.espn_images` for tracking
4. → Next: Frontend reads from local files instead of ESPN CDN
5. → Future: Delta scrape once per season for new players (~20-30 per IPL season)

## Player Headshots

### Data Source

ESPN Cricinfo player profile pages contain image data in `__NEXT_DATA__` JSON:

```
https://www.espncricinfo.com/cricketers/{player-slug}-{key_cricinfo}
```

Each player object has:
- `player.imageUrl` — always present (~100% coverage). Action photo or cutout.
- `player.headshotImageUrl` — only for well-known players. Formal cutout with transparent background.
- `player.image` — full object with `id`, `url`, `width`, `height`, `caption`
- `player.headshotImage` — full object (when available)

The CMS image ID is NOT the same as the ESPN player ID — it's a separate content ID
only available from the `__NEXT_DATA__` on the player profile page.

### Image URL Pattern

Base CDN: `https://img1.hscicdn.com/image/upload/{transforms}/lsci/db/PICTURES/CMS/{folder}/{id}.{ext}`

Raw paths from `__NEXT_DATA__` look like:
```
/lsci/db/PICTURES/CMS/322200/322236.png      (headshot cutout)
/lsci/db/PICTURES/CMS/322200/322236.1.png    (small cutout variant)
/lsci/db/PICTURES/CMS/144100/144164.jpg      (action photo)
```

### Cloudinary Transforms (applied via URL — no local processing)

ESPN's CDN is Cloudinary-backed (`img1.hscicdn.com`). Transforms are applied server-side
via URL path segments — zero local processing, zero storage.

**Important:** `p.imgci.com` returns 403 for direct hotlinks. Always use `img1.hscicdn.com/image/upload/`.

#### Named Transforms (ESPN presets)

Tested and verified working (April 2026):

| Named Transform | Output Size | Use Case |
|-----------------|-------------|----------|
| `t_h_100` | 100×100 | Tiny avatar, face-cropped square |
| `t_h_100_2x` | 200×200 | Retina avatar, face-cropped square — **best for zoomed headshots** |
| `t_ds_square_w_80` | 80×80 | Inline icon |
| `t_ds_square_w_160` | 160×160 | Small thumbnail |
| `t_ds_square_w_320` | 320×320 | Medium thumbnail |
| `t_ds_square_w_640` | 640×640 | Large square |
| `t_ds_square_w_800` | 800×800 | Hero square |
| `t_ds_wide_w_320` | 320×180 | Small wide card (16:9) |
| `t_ds_wide_w_640` | 640×360 | Medium wide card (16:9) |
| `t_ds_wide_w_800` | 800×450 | Large wide card (16:9) |
| `t_ds_wide_w_1200` | 1200×675 | Hero banner (16:9) |

Not available: `t_h_100_2p`, `t_h_100_3p`, `t_h_100_4p`, `t_h_100_3x`, `t_h_100_4x`, `t_h_200`, `t_h_200_2x`,
`t_h_300`, `t_h_300_2x`, `t_h_content_2x`, `t_h_content_3x`, `t_player_headshot`, `t_player_headshot_lg` — all return 400.

Note: `t_h_100_2x` is the only retina variant. There is no `2p`/`3p`/`4p` naming convention —
the suffix is `_2x` (2× retina scaling of the base `t_h_100` 100×100 preset).

#### Raw Cloudinary Parameters (custom transforms)

These can be combined freely in the URL path:

**Format & Quality:**

| Parameter | Purpose | Status |
|-----------|---------|--------|
| `f_png` | Force PNG (preserves transparency) | ✅ Works |
| `f_webp` | WebP output (smaller file size) | ✅ Works |
| `f_auto` | Auto-detect best format for browser | ✅ Works |
| `q_auto` | Auto quality optimization | ✅ Works |

**Crop & Resize:**

| Parameter | Purpose | Status |
|-----------|---------|--------|
| `c_thumb,g_face` | Smart crop centered on detected face | ✅ Works |
| `c_fill,g_face` | Fill dimensions, anchor on face — **best for production cards** | ✅ Works |
| `w_N,h_N` | Target width/height (Cloudinary upscales if needed) | ✅ Works |
| `z_N` | Zoom factor for face crop (e.g., `z_1.2`, `z_1.5`) | ✅ Works |

**Effects:**

| Parameter | Purpose | Status |
|-----------|---------|--------|
| `e_background_removal` | AI background removal → transparent PNG | ✅ Works |
| `e_blur:N` | Gaussian blur (e.g., `e_blur:300`) | ✅ Works |
| `e_sharpen` | Sharpen image | ✅ Works |
| `e_contrast:N` | Adjust contrast (e.g., `e_contrast:20`) | ✅ Works |
| `e_vibrance:N` | Boost color vibrance (e.g., `e_vibrance:40`) | ✅ Works |
| `e_grayscale` | Grayscale conversion | ❌ Blocked (404) |
| `e_sepia` | Sepia tone | ❌ Blocked (404) |
| `e_brightness:N` | Brightness adjustment | ❌ Blocked (404) |
| `r_max` | Circular crop (max border radius) | ❌ Blocked (404) |

### Recommended Transform Recipes

**Production card (player profile page)** — best overall quality:
```
f_auto,h_400,w_300,c_fill,g_face
```
300×400 portrait, face-centered, sharp. `f_auto` lets Cloudinary pick optimal format per browser.
This is the one to use everywhere on the website. Works on both headshots and action photos.

Example: `https://img1.hscicdn.com/image/upload/f_auto,h_400,w_300,c_fill,g_face/lsci/db/PICTURES/CMS/323000/323035.png`

**Zoomed headshot (scorecard, small UI):**
```
t_h_100_2x
```
200×200 tight face crop. ESPN's own preset — optimized for their images.
This is the only retina headshot preset that works (no `2p`/`3p`/`4p` variants exist).

**Tiny avatar (inline in tables/lists):**
```
f_png,c_thumb,g_face,w_48,h_48
```

**Medium card (match cards, team pages):**
```
f_png,c_fill,g_face,w_240,h_320
```

**Large hero (player detail page):**
```
f_png,c_fill,g_face,w_600,h_800
```

**Wide banner (team header, match header):**
```
f_png,c_fill,g_face,w_800,h_300
```

**Transparent cutout (overlay on colored backgrounds):**
```
f_png,e_background_removal,c_fill,g_face,w_300,h_400
```

**Optimized for web (smallest file size):**
```
f_webp,q_auto,e_background_removal,c_fill,g_face,w_300,h_400
```
WebP + auto quality = ~15KB vs ~136KB for PNG at same dimensions.

**Card 2× (retina displays):**
```
f_png,e_background_removal,h_800,w_600,c_fill,g_face
```
600×800 — double the card size for retina/HiDPI screens.

**Hero 2× (retina displays):**
```
f_png,e_background_removal,c_fill,g_face,w_1200,h_1600
```
1200×1600 — double the hero size. ~1.3MB, use only where needed.

**Thumb HD (face crop, high clarity):**
```
f_png,e_background_removal,c_thumb,g_face,w_600,h_600
```
600×600 tight face crop — much sharper than the 300×300 version.

**Vibrance boost:**
```
f_png,e_background_removal,e_vibrance:40,c_fill,g_face,w_300,h_400
```

### Display Strategy (two tiers)

**Tier 1: Players with `headshotImageUrl` (formal cutout)**
- Already has transparent background (600×436 originals)
- Just needs face crop + resize
- Production: `f_auto,h_400,w_300,c_fill,g_face`
- Example: `https://img1.hscicdn.com/image/upload/f_auto,h_400,w_300,c_fill,g_face/lsci/db/PICTURES/CMS/322200/322236.png`

**Tier 2: Players with only `imageUrl` (action photo / small cutout)**
- Small originals (~160×136), Cloudinary upscales
- Needs background removal for transparent overlay use
- Production: `f_auto,e_background_removal,h_400,w_300,c_fill,g_face`
- Example: `https://img1.hscicdn.com/image/upload/f_auto,e_background_removal,h_400,w_300,c_fill,g_face/lsci/db/PICTURES/CMS/144100/144164.jpg`

### Image Source Dimensions (from ESPN)

| URL suffix | Typical original size | Notes |
|------------|----------------------|-------|
| `.png` (headshotImageUrl) | 600×436 | High-res formal cutout, transparent BG |
| `.1.png` / `.2.png` (imageUrl variants) | 160×136 | Small cutout, transparent BG |
| `.jpg` (imageUrl action photos) | Varies | Action photo with background |

Cloudinary upscales small originals to any requested size. Quality degrades on extreme
upscaling (160px → 800px), but `c_fill,g_face` at 300×400 looks good even from 160px originals.

### Scraping Approach

One-time Playwright scrape of ~938 player profile pages:
1. Construct URL: `https://www.espncricinfo.com/cricketers/player-name-{key_cricinfo}`
   - `key_cricinfo` available in `bronze.people` for all 938 dim_players (100% coverage)
2. Extract `__NEXT_DATA__` → `props.appPageProps.data.player`
3. Store `imageUrl` and `headshotImageUrl` (raw CMS paths) in `bronze.player_images`
4. Frontend constructs full URL with appropriate transforms at display time

Estimated time: ~45 minutes (938 pages × ~3 sec/page with Playwright).
Follows same pattern as existing `match_scraper.py`.

### Coverage

| Source | Coverage | Quality |
|--------|----------|---------|
| `headshotImageUrl` (cutout) | ~50% of players | Excellent — formal cutout, already transparent |
| `imageUrl` (action photo) | ~95%+ of players | Good — action photo, bg removal via Cloudinary |
| No image at all | <5% (very obscure) | Use initials avatar fallback |

### Verified Working (tested April 2026)

| Player | Type | Transparent BG | Face Crop |
|--------|------|----------------|-----------|
| Virat Kohli | Headshot cutout | Yes (native) | Yes |
| Ruturaj Gaikwad | Headshot cutout | Yes (native) | Yes |
| Anil Kumble (retired) | Headshot cutout | Yes (native) | Yes |
| Arshdeep Singh | Headshot cutout | Yes (native) | Yes |
| AA Jhunjhunwala (obscure) | Action photo | Yes (via `e_background_removal`) | Yes |
| A Ashish Reddy (lesser-known) | Action photo | Yes (via `e_background_removal`) | Yes |

## Team Logos / Emblems

### IPL Franchise Logos

All from ESPN Cricinfo CDN, transparent PNGs. Extracted from `__NEXT_DATA__` on IPL series/match pages.

| Team | CMS Path | ESPN objectId |
|------|----------|---------------|
| Chennai Super Kings | `/lsci/db/PICTURES/CMS/313400/313421.logo.png` | 335974 |
| Mumbai Indians | `/lsci/db/PICTURES/CMS/415000/415033.png` | 335978 |
| Royal Challengers Bengaluru | `/lsci/db/PICTURES/CMS/378000/378049.png` | 335970 |
| Kolkata Knight Riders | `/lsci/db/PICTURES/CMS/313400/313419.logo.png` | 335971 |
| Delhi Capitals | `/lsci/db/PICTURES/CMS/313400/313422.logo.png` | 335975 |
| Punjab Kings | `/lsci/db/PICTURES/CMS/414800/414846.png` | 335973 |
| Rajasthan Royals | `/lsci/db/PICTURES/CMS/400400/400406.png` | 335977 |
| Sunrisers Hyderabad | `/lsci/db/PICTURES/CMS/414800/414845.png` | 628333 |
| Gujarat Titans | `/lsci/db/PICTURES/CMS/334700/334707.png` | 1298769 |
| Lucknow Super Giants | `/lsci/db/PICTURES/CMS/415000/415032.png` | 1298768 |

Full URL example: `https://img1.hscicdn.com/image/upload/f_png/lsci/db/PICTURES/CMS/313400/313421.logo.png`

Note: Defunct teams (Deccan Chargers, Pune Warriors, Kochi Tuskers, Rising Pune Supergiant,
Gujarat Lions) would need separate scraping from historical series pages.

### International Team Logos / Flags

Available from `__NEXT_DATA__` global data (`props.globalDetails`) on any ESPN Cricinfo page:
- `testTeams[]` — 12 Test-playing nations
- `odiTeams[]` — 14 ODI nations
- `otherTeams[]` — 94 associate/affiliate nations

Each has `image.url` with the team's flag/emblem as a 500x500 PNG.

Key distinction: these are cricket board emblems/flags, NOT country flags.
- India = BCCI-style logo, not the tricolor
- England = ECB lion, not the Union Jack
- West Indies = WICB logo (not a country flag — they're a multi-nation team)

This is exactly what you want for a cricket site.

Example: `https://img1.hscicdn.com/image/upload/f_png/lsci/db/PICTURES/CMS/381800/381895.png` (India)

### Country Flags (supplementary, for T20I context)

If actual country flags are needed alongside cricket emblems:
- `flag-icons` npm package (SVG, MIT license)
- Or `https://flagcdn.com/w80/{iso_code}.png`

## Venue Images

ESPN Cricinfo has ground/stadium photos for major venues.
Available from match page `__NEXT_DATA__` → `match.ground.image`.

Examples found:
- Narendra Modi Stadium, Ahmedabad: `/lsci/db/PICTURES/CMS/66800/66837.jpg`
- Sawai Mansingh Stadium, Jaipur: `/lsci/db/PICTURES/CMS/67500/67517.jpg`
- Arun Jaitley Stadium, Delhi: `/lsci/db/PICTURES/CMS/61100/61133.jpg`

Can be collected during the existing match enrichment scrape — the ground object
is already in the `__NEXT_DATA__` your match_scraper.py processes.

## Complete Visual Asset Inventory

| Asset Type | Source | Coverage | How to Get |
|------------|--------|----------|------------|
| Player headshots (cutout) | ESPN `headshotImageUrl` | ~50% (well-known) | Playwright scrape of player pages |
| Player photos (action) | ESPN `imageUrl` | ~95%+ (nearly all) | Same scrape, fallback |
| Background removal | Cloudinary `e_background_removal` | Works on all | URL transform at display time |
| Face crop | Cloudinary `c_thumb,g_face` | Works on all | URL transform at display time |
| IPL franchise logos | ESPN match/series pages | 10/10 current teams | One-time extract from `__NEXT_DATA__` |
| International team emblems | ESPN `globalDetails` | 120+ teams | One-time extract from any page |
| Venue/stadium photos | ESPN match pages | Most major venues | During match enrichment scrape |
| Country flags | flag-icons npm / flagcdn | All countries | npm package or CDN |
| Initials avatar (fallback) | Generated in frontend | 100% | CSS/JS, no data needed |

## IPL Official Headshots (supplementary)

Pattern: `https://documents.iplt20.com/ipl/IPLHeadshot{year}/{ipl_headshot_id}.png`
- Available for 2023-2026 seasons
- 248 current squad players with 100% coverage
- IPL headshot IDs are NOT ESPN IDs — mapped via squad page scraping
- Best quality official photos, but only covers current season rosters

## Licensing Notes

- ESPN Cricinfo images: NOT licensed for redistribution. Hotlinking from their CDN.
- If ESPN changes CDN structure or blocks hotlinking, images break. Acceptable risk for a free project.
- Cloudinary transforms are applied on ESPN's infrastructure, not ours.
- IPL official images: same hotlinking approach.
- Flag icons (flag-icons npm): MIT license, no restrictions.

## Fallback Strategy

For players with no image at all:
- Generate initials-based avatar (e.g., "VK" for V Kohli)
- Use CSS with team primary color as background (already have `primaryColor` from ESPN enrichment)
- This is the same pattern GitHub, Slack, and Google use — looks intentional, not broken

## Appendix: Exhaustive Transform Testing (April 2026)

Tested against `img1.hscicdn.com` using CA Pujara headshot (600×436 original) and cutout (160×136 original).

### CDN Domains

| Domain | Status | Notes |
|--------|--------|-------|
| `p.imgci.com` | ❌ 403 Forbidden | Blocks direct hotlinks (CloudFront) |
| `img1.hscicdn.com/image/upload/` | ✅ Works | Cloudinary-backed, supports all transforms |

### Named Transform Results

| Transform | Status | Output | Notes |
|-----------|--------|--------|-------|
| `t_h_100` | ✅ 200 | 100×100 (14KB) | Base headshot preset |
| `t_h_100_2x` | ✅ 200 | 200×200 (50KB) | 2× retina of t_h_100 — **only retina variant** |
| `t_h_100_2p` | ❌ 400 | — | Does not exist |
| `t_h_100_3p` | ❌ 400 | — | Does not exist |
| `t_h_100_4p` | ❌ 400 | — | Does not exist |
| `t_h_100_3x` | ❌ 400 | — | Does not exist |
| `t_h_100_4x` | ❌ 400 | — | Does not exist |
| `t_h_200` | ❌ 400 | — | Does not exist |
| `t_h_200_2x` | ❌ 400 | — | Does not exist |
| `t_h_300` | ❌ 400 | — | Does not exist |
| `t_h_300_2x` | ❌ 400 | — | Does not exist |
| `t_h_content_2x` | ❌ 400 | — | Does not exist |
| `t_h_content_3x` | ❌ 400 | — | Does not exist |
| `t_player_headshot` | ❌ 400 | — | Does not exist |
| `t_player_headshot_lg` | ❌ 400 | — | Does not exist |
| `t_ds_square_w_80` | ✅ 200 | 80×80 (8KB) | Square crop |
| `t_ds_square_w_160` | ✅ 200 | 160×160 (27KB) | Square crop |
| `t_ds_square_w_320` | ✅ 200 | 320×320 (98KB) | Square crop |
| `t_ds_square_w_640` | ✅ 200 | 640×640 (331KB) | Square crop |
| `t_ds_square_w_800` | ✅ 200 | 800×800 (467KB) | Square crop |
| `t_ds_wide_w_320` | ✅ 200 | 320×180 (34KB) | 16:9 wide crop |
| `t_ds_wide_w_640` | ✅ 200 | 640×360 (122KB) | 16:9 wide crop |
| `t_ds_wide_w_800` | ✅ 200 | 800×450 (176KB) | 16:9 wide crop |
| `t_ds_wide_w_1200` | ✅ 200 | 1200×675 (327KB) | 16:9 wide crop |

### Raw Cloudinary Parameter Results

| Transform | Status | Output | Notes |
|-----------|--------|--------|-------|
| (no transform) | ✅ 200 | 600×436 | Original size |
| `f_png` | ✅ 200 | 600×436 (226KB) | Force PNG |
| `f_png,q_auto` | ✅ 200 | 600×436 (64KB) | PNG + auto quality |
| `f_webp,q_auto,c_fill,g_face,w_300,h_400` | ✅ 200 | 300×400 (15KB) | **Smallest file size** |
| `f_auto,h_400,w_300,c_fill,g_face` | ✅ 200 | 300×400 (152KB) | **Best production recipe** |
| `f_png,c_thumb,g_face,w_200,h_200` | ✅ 200 | 200×200 (50KB) | Tight face crop |
| `f_png,c_thumb,g_face,w_300,h_300` | ✅ 200 | 300×300 (97KB) | Medium face crop |
| `f_png,c_fill,g_face,w_300,h_400` | ✅ 200 | 300×400 (136KB) | Portrait fill |
| `f_png,c_fill,g_face,w_400,h_400` | ✅ 200 | 400×400 (148KB) | Square fill |
| `f_png,c_fill,g_face,w_240,h_320` | ✅ 200 | 240×320 (90KB) | Medium card |
| `f_png,c_fill,g_face,w_600,h_800` | ✅ 200 | 600×800 (423KB) | Large hero |
| `f_png,c_fill,g_face,w_800,h_300` | ✅ 200 | 800×300 (115KB) | Wide banner |
| `f_png,c_fill,g_face,w_200,h_200,z_1.2` | ✅ 200 | 200×200 (40KB) | Zoom 1.2× |
| `f_png,c_fill,g_face,w_300,h_400,z_1.5` | ✅ 200 | 300×400 (136KB) | Zoom 1.5× |
| `f_png,w_400` | ✅ 200 | 400×291 (84KB) | Width-only resize |
| `f_png,w_800` | ✅ 200 | 800×581 (291KB) | Width-only resize |
| `f_png,e_background_removal` | ✅ 200 | 600×436 (197KB) | AI bg removal |
| `f_png,e_background_removal,c_fill,g_face,w_300,h_400` | ✅ 200 | 300×400 (136KB) | BG removal + crop |
| `f_png,e_sharpen,c_fill,g_face,w_300,h_400` | ✅ 200 | 300×400 (149KB) | Sharpen |
| `f_png,e_contrast:20,c_fill,g_face,w_300,h_400` | ✅ 200 | 300×400 (136KB) | Contrast boost |
| `f_png,e_vibrance:40,c_fill,g_face,w_300,h_400` | ✅ 200 | 300×400 (139KB) | Color vibrance |
| `f_png,e_blur:300,c_fill,w_300,h_400` | ✅ 200 | 300×400 (85KB) | Blur |
| `f_png,c_thumb,g_face,w_48,h_48` | ✅ 200 | 48×48 (4KB) | Tiny inline avatar |
| `f_png,c_thumb,g_face,w_200,h_200,r_max` | ❌ 404 | — | Circular crop blocked |
| `f_png,e_grayscale,c_fill,g_face,w_300,h_400` | ❌ 404 | — | Grayscale blocked |
| `f_png,e_sepia,c_fill,g_face,w_300,h_400` | ❌ 404 | — | Sepia blocked |
| `f_png,e_brightness:20,c_fill,g_face,w_300,h_400` | ❌ 404 | — | Brightness blocked |

### Upscaling Behavior

Cloudinary upscales small originals (160×136 cutouts) to any requested size.
Tested: `c_fill,g_face,h_400,w_300` on a 160×136 original → returns 300×400 (upscaled).
Quality degrades on extreme upscaling but `c_fill,g_face` at 300×400 looks acceptable even from 160px originals.

### 2× Retina Variants (tested April 2026)

| Transform | Status | Output | Notes |
|-----------|--------|--------|-------|
| `f_png,e_background_removal,h_800,w_600,c_fill,g_face` | ✅ 200 | 600×800 (466KB) | Card 2× |
| `f_png,e_background_removal,c_fill,g_face,w_1200,h_1600` | ✅ 200 | 1200×1600 (1.3MB) | Hero 2× |
| `f_png,e_background_removal,c_thumb,g_face,w_600,h_600` | ✅ 200 | 600×600 (335KB) | Thumb HD |
| `f_png,e_background_removal,c_fill,g_face,w_1200,h_675` | ✅ 200 | 1200×675 (wide 16:9 + transparent) |
| `f_png,e_background_removal,e_vibrance:40,c_fill,g_face,w_300,h_400` | ✅ 200 | 300×400 | Vibrance + transparent |

### Key Takeaways

1. **Use `f_auto,h_400,w_300,c_fill,g_face`** for all production player images
2. **Use `t_h_100_2x`** for zoomed headshot thumbnails (200×200)
3. **`t_h_100_2x` is the only retina headshot preset** — no `2p`/`3p`/`4p` variants exist
4. **`f_webp,q_auto`** gives 10× smaller files than `f_png` — use for performance-critical pages
5. **`e_background_removal`** works on all images — use for transparent overlays on colored backgrounds
6. **Blocked effects:** grayscale, sepia, brightness, circular crop (`r_max`) — ESPN's Cloudinary config rejects these
7. **Working effects:** sharpen, contrast, vibrance, blur, background_removal
8. **Always use `img1.hscicdn.com`** — `p.imgci.com` returns 403
