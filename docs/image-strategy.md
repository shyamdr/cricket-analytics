# Image & Visual Assets Strategy

## Overview

Player headshots, team logos, and country flags sourced from ESPN Cricinfo's Cloudinary CDN.
Zero cost, zero storage — all transforms happen via URL parameters at display time.

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

ESPN's CDN is Cloudinary-backed and supports these transforms:

| Transform | Purpose |
|-----------|---------|
| `f_png` | Force PNG output (preserves transparency) |
| `f_auto` | Auto-detect best format |
| `c_thumb,g_face` | Smart crop centered on detected face |
| `w_200,h_200` | Resize to 200x200 |
| `e_background_removal` | AI background removal (produces transparent PNG) |
| `z_1.2` | Zoom factor for face crop |

### Display Strategy (two tiers)

**Tier 1: Players with `headshotImageUrl` (formal cutout)**
- Already has transparent background
- Just needs face crop + resize
- Transform: `f_png,c_thumb,g_face,w_200,h_200`
- Example: `https://img1.hscicdn.com/image/upload/f_png,c_thumb,g_face,w_200,h_200/lsci/db/PICTURES/CMS/322200/322236.png`

**Tier 2: Players with only `imageUrl` (action photo)**
- Needs background removal + face crop
- Transform: `f_png,e_background_removal,c_thumb,g_face,w_200,h_200`
- Example: `https://img1.hscicdn.com/image/upload/f_png,e_background_removal,c_thumb,g_face,w_200,h_200/lsci/db/PICTURES/CMS/144100/144164.jpg`

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
