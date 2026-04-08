/**
 * API client for the Cricket Analytics FastAPI backend.
 *
 * In development, Next.js rewrites /api/* to the FastAPI server (see next.config.ts).
 * In production, set NEXT_PUBLIC_API_URL to the deployed FastAPI URL.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export async function fetchAPI<T>(path: string): Promise<T> {
  const url = `${API_BASE}/api/v1${path}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000); // 10s timeout

  try {
    const res = await fetch(url, {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!res.ok) {
      throw new Error(`API error: ${res.status} ${res.statusText}`);
    }
    return res.json() as Promise<T>;
  } finally {
    clearTimeout(timeout);
  }
}
