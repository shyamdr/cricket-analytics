"""Test Google Maps Geocoding API for cricket venues.

Reads venues from DuckDB, geocodes via Google, writes to scripts/google_results.csv.
API key read from .env file (GOOGLE_MAPS_API_KEY).
"""

import csv
import os
import time

import duckdb
import requests

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cricket.duckdb")
CSV_PATH = os.path.join(os.path.dirname(__file__), "google_results.csv")
GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
DELAY = 0.1  # Google allows 50 QPS, but let's be polite

CSV_COLUMNS = [
    "venue",
    "city",
    "query_used",
    "latitude",
    "longitude",
    "formatted_address",
    "place_type",
    "status",
]


def load_api_key() -> str:
    """Load API key from .env file."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("GOOGLE_MAPS_API_KEY="):
                return line.split("=", 1)[1]
    raise RuntimeError("GOOGLE_MAPS_API_KEY not found in .env")


def get_venue_city_pairs(db_path: str) -> list[tuple[str, str | None]]:
    con = duckdb.connect(db_path, read_only=True)
    rows = con.execute(
        """
        SELECT DISTINCT venue, city
        FROM bronze.matches
        WHERE venue IS NOT NULL
        ORDER BY venue
        """
    ).fetchall()
    con.close()
    return rows


def geocode(query: str, api_key: str) -> dict:
    """Call Google Geocoding API."""
    resp = requests.get(
        GOOGLE_GEOCODE_URL,
        params={"address": query, "key": api_key},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def geocode_venue(venue: str, city: str | None, api_key: str, index: int, total: int) -> dict:
    """Geocode a single venue. Simple query: venue + city."""
    truncated = venue.split(",")[0].strip()
    if city:
        query = f"{truncated}, {city}"
    else:
        query = truncated

    city_display = city or "N/A"
    print(f"  [{index}/{total}] {venue} ({city_display}) → query: '{query}' ", end="", flush=True)

    try:
        data = geocode(query, api_key)
    except Exception as e:
        print(f"ERROR ({e})")
        return {
            "venue": venue, "city": city or "", "query_used": query,
            "latitude": "", "longitude": "", "formatted_address": "",
            "place_type": "", "status": f"ERROR: {e}",
        }

    status = data.get("status", "UNKNOWN")
    results = data.get("results", [])

    if status != "OK" or not results:
        print(f"MISS ({status})")
        return {
            "venue": venue, "city": city or "", "query_used": query,
            "latitude": "", "longitude": "", "formatted_address": "",
            "place_type": "", "status": status,
        }

    top = results[0]
    loc = top["geometry"]["location"]
    types = ", ".join(top.get("types", []))
    addr = top.get("formatted_address", "")
    print(f"HIT → {addr}")

    return {
        "venue": venue,
        "city": city or "",
        "query_used": query,
        "latitude": loc["lat"],
        "longitude": loc["lng"],
        "formatted_address": addr,
        "place_type": types,
        "status": "OK",
    }


def main() -> None:
    api_key = load_api_key()
    print(f"API key loaded ({api_key[:10]}...)")

    if os.path.isfile(CSV_PATH):
        os.remove(CSV_PATH)

    print(f"Connecting to DuckDB: {DB_PATH}")
    pairs = get_venue_city_pairs(DB_PATH)
    total = len(pairs)
    print(f"Found {total} distinct venue-city pairs\n")

    found = 0
    failed = 0

    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        for i, (venue, city) in enumerate(pairs, 1):
            row = geocode_venue(venue, city, api_key, i, total)
            writer.writerow(row)
            f.flush()

            if row["status"] != "OK":
                failed += 1
            else:
                found += 1

            time.sleep(DELAY)

    print(f"\nResults: {found}/{total} found, {failed}/{total} failed")
    print(f"Output: {CSV_PATH}")


if __name__ == "__main__":
    main()
