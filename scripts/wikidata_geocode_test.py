"""Test Wikidata as a geocoding source for cricket venues.

Strategy:
  1. Search Wikidata MediaWiki API (full-text search) for venue name
  2. Filter results to cricket-related entities (check description/claims)
  3. Get coordinates via SPARQL for matched Q-IDs

Reads venues from DuckDB bronze.matches, writes results to scripts/wikidata_results.csv.
"""

import csv
import os
import re
import time

import duckdb
import requests

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cricket.duckdb")
CSV_PATH = os.path.join(os.path.dirname(__file__), "wikidata_results.csv")
USER_AGENT = "cricket-analytics-poc/0.1 (https://github.com/shyamdr/cricket-analytics)"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
SPARQL_URL = "https://query.wikidata.org/sparql"
DELAY = 1.0  # seconds between API calls

CSV_COLUMNS = [
    "venue",
    "city",
    "search_query",
    "attempt",
    "qid",
    "wikidata_label",
    "wikidata_description",
    "latitude",
    "longitude",
    "country",
]


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


def search_wikidata(query: str) -> list[dict]:
    """Full-text search on Wikidata. Returns list of {title, snippet}."""
    resp = requests.get(
        WIKIDATA_API,
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": 5,
            "format": "json",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("query", {}).get("search", [])


def get_entity_details(qid: str) -> dict | None:
    """Get label, description, and coordinates for a Wikidata entity."""
    sparql = f"""
    SELECT ?itemLabel ?itemDescription ?coord ?countryLabel WHERE {{
      BIND(wd:{qid} AS ?item)
      OPTIONAL {{ ?item wdt:P625 ?coord . }}
      OPTIONAL {{ ?item wdt:P17 ?country . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    LIMIT 1
    """
    resp = requests.get(
        SPARQL_URL,
        params={"query": sparql, "format": "json"},
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()
    bindings = resp.json().get("results", {}).get("bindings", [])
    if not bindings:
        return None
    b = bindings[0]
    coord_str = b.get("coord", {}).get("value", "")
    lat, lon = None, None
    if coord_str:
        # Parse "Point(lon lat)"
        m = re.match(r"Point\(([-\d.]+)\s+([-\d.]+)\)", coord_str)
        if m:
            lon, lat = float(m.group(1)), float(m.group(2))
    return {
        "label": b.get("itemLabel", {}).get("value", ""),
        "description": b.get("itemDescription", {}).get("value", ""),
        "latitude": lat,
        "longitude": lon,
        "country": b.get("countryLabel", {}).get("value", ""),
    }


def is_cricket_related(snippet: str, description: str) -> bool:
    """Check if a Wikidata result looks cricket-related."""
    text = (snippet + " " + description).lower()
    cricket_terms = ["cricket", "stadium", "ground", "oval", "sports"]
    return any(t in text for t in cricket_terms)


def build_search_queries(venue: str, city: str | None) -> list[tuple[int, str]]:
    """Build fallback search queries."""
    queries = []
    truncated = venue.split(",")[0].strip()

    # Attempt 1: venue + "cricket" (to bias results)
    queries.append((1, f"{truncated} cricket"))

    # Attempt 2: venue + city + "cricket"
    if city:
        queries.append((2, f"{truncated} {city} cricket"))

    # Attempt 3: just the venue name
    queries.append((3, truncated))

    # Attempt 4: venue + city
    if city:
        queries.append((4, f"{truncated} {city}"))

    return queries



def geocode_venue(venue: str, city: str | None, index: int, total: int) -> dict:
    """Try to find a venue on Wikidata and get its coordinates."""
    queries = build_search_queries(venue, city)
    city_display = city or "N/A"

    for attempt_num, query_str in queries:
        print(
            f"  [{index}/{total}] {venue} ({city_display}) attempt {attempt_num}: '{query_str}' ",
            end="",
            flush=True,
        )
        try:
            results = search_wikidata(query_str)
        except Exception as e:
            print(f"ERROR ({e})")
            time.sleep(DELAY)
            continue

        time.sleep(DELAY)

        # Find first cricket-related result with coordinates
        for r in results:
            qid = r["title"]
            snippet = r.get("snippet", "")

            # Get entity details
            try:
                details = get_entity_details(qid)
            except Exception:
                continue

            time.sleep(DELAY)

            if details is None:
                continue

            desc = details.get("description", "")

            # Check if cricket-related
            if not is_cricket_related(snippet, desc):
                continue

            # Check if has coordinates
            if details["latitude"] is None:
                continue

            print(f"HIT → {details['label']} ({qid})")
            return {
                "venue": venue,
                "city": city or "",
                "search_query": query_str,
                "attempt": str(attempt_num),
                "qid": qid,
                "wikidata_label": details["label"],
                "wikidata_description": desc,
                "latitude": details["latitude"],
                "longitude": details["longitude"],
                "country": details["country"],
            }

        print("MISS")

    # All attempts failed
    print(f"  [{index}/{total}] {venue} ({city_display}) → FAILED (all attempts)")
    return {
        "venue": venue,
        "city": city or "",
        "search_query": "",
        "attempt": "FAILED",
        "qid": "",
        "wikidata_label": "",
        "wikidata_description": "",
        "latitude": "",
        "longitude": "",
        "country": "",
    }


def main() -> None:
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
