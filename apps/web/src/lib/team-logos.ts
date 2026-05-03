/**
 * Team visual metadata — fetched from the API (dim_teams), not hardcoded.
 *
 * The API serves team_name, espn_team_id, primary_color, brand_color_alt,
 * and logo_url from the gold layer, which joins ESPN enrichment with
 * curated brand colors from a dbt seed CSV.
 *
 * This module provides:
 * - A cache populated once via fetchTeamMeta()
 * - Lookup functions for logo URL, colors, and gradient color
 * - Runtime canvas-based clash detection (no hardcoded flags)
 */

// ---------------------------------------------------------------------------
// Types & cache
// ---------------------------------------------------------------------------

export interface TeamMeta {
  teamName: string;
  espnTeamId: number | null;
  primaryColor: string;
  colorAlt: string;
  abbreviation: string | null;
}

const _cache = new Map<string, TeamMeta>();
let _fetched = false;
let _fetchPromise: Promise<void> | null = null;

// ---------------------------------------------------------------------------
// Static fallback — ensures logos load even when API is cold/sleeping
// ---------------------------------------------------------------------------
const _STATIC_TEAMS: Record<string, { espnTeamId: number; primaryColor: string; colorAlt: string; abbreviation: string }> = {
  "Chennai Super Kings": { espnTeamId: 335974, primaryColor: "#FCCA06", colorAlt: "#F15A22", abbreviation: "CSK" },
  "Mumbai Indians": { espnTeamId: 335978, primaryColor: "#004B8D", colorAlt: "#D1AB3E", abbreviation: "MI" },
  "Royal Challengers Bengaluru": { espnTeamId: 335970, primaryColor: "#D4213D", colorAlt: "#000000", abbreviation: "RCB" },
  "Kolkata Knight Riders": { espnTeamId: 335971, primaryColor: "#3A225D", colorAlt: "#D4A84B", abbreviation: "KKR" },
  "Delhi Capitals": { espnTeamId: 335975, primaryColor: "#004C93", colorAlt: "#EF1B23", abbreviation: "DC" },
  "Punjab Kings": { espnTeamId: 335973, primaryColor: "#D4213D", colorAlt: "#A7A9AC", abbreviation: "PBKS" },
  "Rajasthan Royals": { espnTeamId: 335977, primaryColor: "#254AA5", colorAlt: "#FF69B4", abbreviation: "RR" },
  "Sunrisers Hyderabad": { espnTeamId: 628333, primaryColor: "#FF822A", colorAlt: "#000000", abbreviation: "SRH" },
  "Gujarat Titans": { espnTeamId: 1298769, primaryColor: "#1C1C2B", colorAlt: "#A0E4F1", abbreviation: "GT" },
  "Lucknow Super Giants": { espnTeamId: 1298768, primaryColor: "#0057E2", colorAlt: "#A72056", abbreviation: "LSG" },
};

// Pre-populate cache with static data
for (const [name, data] of Object.entries(_STATIC_TEAMS)) {
  _cache.set(name, {
    teamName: name,
    espnTeamId: data.espnTeamId,
    primaryColor: data.primaryColor,
    colorAlt: data.colorAlt,
    abbreviation: data.abbreviation,
  });
}

// ---------------------------------------------------------------------------
// Fetch from API (call once on app load — overwrites static with live data)
// ---------------------------------------------------------------------------

const API = process.env.NEXT_PUBLIC_API_URL || "";

export function fetchTeamMeta(): Promise<void> {
  if (_fetched) return Promise.resolve();
  if (_fetchPromise) return _fetchPromise;

  _fetchPromise = fetch(`${API}/api/v1/teams`)
    .then((res) => (res.ok ? res.json() : []))
    .then((teams) => {
      for (const t of teams) {
        const existing = _cache.get(t.team_name);
        _cache.set(t.team_name, {
          teamName: t.team_name,
          // Prefer API value, but keep static fallback if API returns null
          espnTeamId: t.espn_team_id ?? existing?.espnTeamId ?? null,
          primaryColor: t.primary_color ?? existing?.primaryColor ?? "#6B7280",
          colorAlt: t.brand_color_alt ?? t.primary_color ?? existing?.colorAlt ?? "#6B7280",
          abbreviation: t.team_abbreviation ?? existing?.abbreviation ?? null,
        });
      }
      _fetched = true;
    })
    .catch(() => {
      // API unavailable — functions return fallbacks
    });

  return _fetchPromise;
}

export function isTeamMetaLoaded(): boolean {
  return _fetched;
}

// ---------------------------------------------------------------------------
// Lookup functions
// ---------------------------------------------------------------------------

function getMeta(teamName: string): TeamMeta | null {
  // Check live cache first (populated by fetchTeamMeta or static init)
  const cached = _cache.get(teamName);
  if (cached) return cached;

  // Fallback to static data if cache miss (handles tree-shaking edge cases)
  const s = _STATIC_TEAMS[teamName];
  if (s) {
    const meta: TeamMeta = {
      teamName,
      espnTeamId: s.espnTeamId,
      primaryColor: s.primaryColor,
      colorAlt: s.colorAlt,
      abbreviation: s.abbreviation,
    };
    _cache.set(teamName, meta);
    return meta;
  }

  return null;
}

/**
 * Returns the URL for a team's logo via the API image endpoint.
 * Uses a relative path so Next.js rewrite proxy handles it in dev,
 * keeping it same-origin for canvas pixel analysis.
 * In production, NEXT_PUBLIC_API_URL is baked into the path.
 */
const IMAGE_BASE = "https://pub-78fc5db4e6f54c2bba7c541ea83216f6.r2.dev";

export function getTeamLogoUrl(teamName: string): string | null {
  const meta = getMeta(teamName);
  if (!meta?.espnTeamId) return null;
  return `${IMAGE_BASE}/teams/${meta.espnTeamId}.png`;
}

export function getTeamColor(teamName: string): string {
  return getMeta(teamName)?.primaryColor ?? "#6B7280";
}

/**
 * Returns the URL for a player's photo from the R2 CDN.
 */
export function getPlayerImageUrl(espnPlayerId: number | null): string | null {
  if (!espnPlayerId) return null;
  return `${IMAGE_BASE}/players/${espnPlayerId}.png`;
}

export function getTeamColorAlt(teamName: string): string {
  return getMeta(teamName)?.colorAlt ?? "#6B7280";
}

export function getTeamAbbreviation(teamName: string): string | null {
  return getMeta(teamName)?.abbreviation ?? null;
}

// ---------------------------------------------------------------------------
// Runtime canvas-based clash detection
// ---------------------------------------------------------------------------

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

const CLASH_THRESHOLD = 80;
const _clashCache = new Map<string, boolean>();

/**
 * Synchronously checks the clash cache. Returns null if not yet analyzed.
 */
export function checkLogoClash(imgSrc: string, bgHex: string): boolean | null {
  return _clashCache.get(`${imgSrc}:${bgHex}`) ?? null;
}

/**
 * Loads a logo into a hidden canvas, samples opaque pixels to compute
 * the dominant color, and compares against the background hex.
 * Returns true if they clash (distance < threshold).
 */
export function analyzeLogoClashAsync(imgSrc: string, bgHex: string): Promise<boolean> {
  const key = `${imgSrc}:${bgHex}`;
  if (_clashCache.has(key)) return Promise.resolve(_clashCache.get(key)!);

  return new Promise((resolve) => {
    const img = new window.Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      const size = 40;
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext("2d");
      if (!ctx) { _clashCache.set(key, false); resolve(false); return; }

      ctx.drawImage(img, 0, 0, size, size);
      const data = ctx.getImageData(0, 0, size, size).data;

      let rSum = 0, gSum = 0, bSum = 0, count = 0;
      for (let i = 0; i < data.length; i += 4) {
        if (data[i + 3] > 128) {
          rSum += data[i];
          gSum += data[i + 1];
          bSum += data[i + 2];
          count++;
        }
      }

      if (count === 0) { _clashCache.set(key, false); resolve(false); return; }

      const [bgR, bgG, bgB] = hexToRgb(bgHex);
      const dr = rSum / count - bgR;
      const dg = gSum / count - bgG;
      const db = bSum / count - bgB;
      const dist = Math.sqrt(dr * dr + dg * dg + db * db);

      const clashes = dist < CLASH_THRESHOLD;
      _clashCache.set(key, clashes);
      resolve(clashes);
    };
    img.onerror = () => { _clashCache.set(key, false); resolve(false); };
    img.src = imgSrc;
  });
}

/**
 * Returns the best gradient color for a team given clash analysis result.
 * If clashes is true, returns colorAlt instead of primary.
 */
export function getTeamGradientColor(teamName: string, clashes: boolean): string {
  const meta = getMeta(teamName);
  if (!meta) return "#6B7280";
  return clashes ? meta.colorAlt : meta.primaryColor;
}
