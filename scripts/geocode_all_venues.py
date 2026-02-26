"""Geocode all IPL venues from DuckDB bronze.matches using Photon (photon.komoot.io).

Tries a fallback chain of queries per venue-city pair:
  1. Raw venue string
  2. Venue + ", " + city (skip if city is NULL)
  3. Venue truncated at first comma
  4. Venue truncated at first comma + ", " + city (skip if city is NULL)

Writes results to scripts/geocode_all_results.csv.
"""

import csv
import os
import time

import duckdb
import requests

# --- Config ---
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cricket.duckdb")
CSV_PATH = os.path.join(os.path.dirname(__file__), "geocode_all_results.csv")
PHOTON_URL = "https://photon.komoot.io/api"
USER_AGENT = "cricket-analytics-poc/0.1"
REQUEST_TIMEOUT = 10
DELAY_SECONDS = 1

CSV_COLUMNS = [
    "venue",
    "city",
    "query_used",
    "attempt",
    "latitude",
    "longitude",
    "photon_name",
    "photon_city",
    "photon_country",
    "photon_state",
    "osm_value",
]


def get_venue_city_pairs(db_path: str) -> list[tuple[str, str | None]]:
    """Query distinct venue-city pairs from bronze.matches."""
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


def photon_query(query: str) -> list[dict]:
    """Call Photon API with limit=1, lang=en. Returns list of GeoJSON features."""
    resp = requests.get(
        PHOTON_URL,
        params={"q": query, "lang": "en", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json().get("features", [])


def build_queries(venue: str, city: str | None) -> list[tuple[int, str]]:
    """Build the fallback chain of (attempt_number, query_string) pairs."""
    truncated = venue.split(",")[0].strip()
    queries: list[tuple[int, str]] = []

    # Attempt 1: raw venue
    queries.append((1, venue))

    # Attempt 2: venue + city (skip if no city)
    if city:
        queries.append((2, f"{venue}, {city}"))

    # Attempt 3: venue truncated at first comma
    queries.append((3, truncated))

    # Attempt 4: truncated + city (skip if no city)
    if city:
        queries.append((4, f"{truncated}, {city}"))

    return queries


def extract_result(feature: dict) -> dict:
    """Extract relevant fields from a Photon GeoJSON feature."""
    props = feature.get("properties", {})
    coords = feature.get("geometry", {}).get("coordinates", [None, None])
    return {
        "latitude": coords[1] if len(coords) > 1 else "",
        "longitude": coords[0] if len(coords) > 0 else "",
        "photon_name": props.get("name", ""),
        "photon_city": props.get("city", ""),
        "photon_country": props.get("country", ""),
        "photon_state": props.get("state", ""),
        "osm_value": props.get("osm_value", ""),
    }


def geocode_venue(
    venue: str, city: str | None, index: int, total: int
) -> dict:
    """Try the fallback chain for a single venue. Returns a CSV row dict."""
    queries = build_queries(venue, city)
    city_display = city or "N/A"

    for attempt_num, query_str in queries:
        print(
            f"  Processing {index}/{total}: {venue} ({city_display})... attempt {attempt_num} ",
            end="",
            flush=True,
        )
        try:
            features = photon_query(query_str)
        except requests.RequestException as e:
            print(f"ERROR ({e})")
            time.sleep(DELAY_SECONDS)
            continue

        time.sleep(DELAY_SECONDS)

        if features:
            print("HIT")
            result = extract_result(features[0])
            return {
                "venue": venue,
                "city": city or "",
                "query_used": query_str,
                "attempt": str(attempt_num),
                **result,
            }
        else:
            print("MISS")

    # All attempts failed
    print(f"  Processing {index}/{total}: {venue} ({city_display})... FAILED (all attempts)")
    return {
        "venue": venue,
        "city": city or "",
        "query_used": "",
        "attempt": "FAILED",
        "latitude": "",
        "longitude": "",
        "photon_name": "",
        "photon_city": "",
        "photon_country": "",
        "photon_state": "",
        "osm_value": "",
    }


def main() -> None:
    # Delete existing CSV for a fresh start
    if os.path.isfile(CSV_PATH):
        os.remove(CSV_PATH)
        print(f"Deleted existing {CSV_PATH}")

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
            row = geocode_venue(venue, city, i, total)
            writer.writerow(row)
            f.flush()

            if row["attempt"] == "FAILED":
                failed += 1
            else:
                found += 1

    print(f"\nResults: {found}/{total} found, {failed}/{total} failed")
    print(f"Output: {CSV_PATH}")


if __name__ == "__main__":
    main()
