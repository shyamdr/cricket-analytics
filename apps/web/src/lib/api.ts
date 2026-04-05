/**
 * API client for the Cricket Analytics FastAPI backend.
 *
 * In development, Next.js rewrites /api/* to the FastAPI server (see next.config.ts).
 * In production, set NEXT_PUBLIC_API_URL to the deployed FastAPI URL.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export async function fetchAPI<T>(path: string): Promise<T> {
  const url = `${API_BASE}/api/v1${path}`;
  const res = await fetch(url, { next: { revalidate: 3600 } }); // cache 1 hour
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText} for ${url}`);
  }
  return res.json() as Promise<T>;
}
