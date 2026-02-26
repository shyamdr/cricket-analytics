"""Quick POC script to test Photon (photon.komoot.io) geocoding for cricket venues."""

import csv
import os
import sys

import requests

PHOTON_URL = "https://photon.komoot.io/api"
USER_AGENT = "cricket-analytics-poc/0.1 (https://github.com/shyamdr/cricket-analytics)"
CSV_PATH = os.path.join(os.path.dirname(__file__), "nominatim_results.csv")
CSV_COLUMNS = ["input", "latitude", "longitude", "city", "country", "type"]


def geocode(query: str) -> list[dict]:
    """Query Photon geocoding API and return list of GeoJSON features."""
    resp = requests.get(
        PHOTON_URL,
        params={"q": query, "lang": "en", "limit": 3},
        headers={"User-Agent": USER_AGENT},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("features", [])


def extract_city_country(feature: dict) -> tuple[str, str]:
    """Extract city and country from a Photon GeoJSON feature's properties."""
    props = feature.get("properties", {})
    city = props.get("city", "")
    country = props.get("country", "")
    return city, country


def append_to_csv(row: dict) -> None:
    """Append a single row to the results CSV, creating it with headers if needed."""
    file_exists = os.path.isfile(CSV_PATH)
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main() -> None:
    if len(sys.argv) < 2:
        #print("Usage: python3 scripts/nominatim_poc.py \"<venue address>\"")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    #print(f"Searching: {query}\n")

    results = geocode(query)

    if not results:
        #print("No results found.")
        append_to_csv(
            {"input": query, "latitude": "", "longitude": "", "city": "", "country": "", "type": ""}
        )
        #print(f"(empty row appended to {CSV_PATH})")
        sys.exit(0)

    for i, feature in enumerate(results, 1):
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [None, None])
        lon, lat = coords[0], coords[1]
        name = props.get("name", "N/A")
        city = props.get("city", "N/A")
        country = props.get("country", "N/A")
        osm_value = props.get("osm_value", "N/A")
        # print(f"Result {i}:")
        # print(f"  Name:    {name}")
        # print(f"  Lat:     {lat}")
        # print(f"  Lon:     {lon}")
        # print(f"  City:    {city}")
        # print(f"  Country: {country}")
        # print(f"  Type:    {osm_value}")
        # print()

    top = results[0]
    top_coords = top.get("geometry", {}).get("coordinates", [None, None])
    top_props = top.get("properties", {})
    city, country = extract_city_country(top)
    append_to_csv(
        {
            "input": query,
            "latitude": top_coords[1] if len(top_coords) > 1 else "",
            "longitude": top_coords[0] if len(top_coords) > 0 else "",
            "city": city,
            "country": country,
            "type": top_props.get("osm_value", ""),
        }
    )
    #print(f"Top result appended to {CSV_PATH}")


if __name__ == "__main__":
    main()
