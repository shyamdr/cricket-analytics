# Requirements Document

## Introduction

Enrich the cricket analytics platform with venue geographic coordinates (latitude/longitude) for all IPL venues. This is Phase 1.1 of the data enrichment roadmap — a prerequisite for the weather enrichment pipeline (Phase 1.2) and future location-based analytics. Coordinates are sourced dynamically via the Photon geocoding API (fuzzy matching powered by ElasticSearch), stored in a DuckDB bronze table, transformed through dbt silver/gold layers, and joined into the existing `dim_venues` gold model. The pipeline is fully automated and reproducible — on a fresh clone, `make all` geocodes all venues from scratch; on subsequent runs, only new venues are geocoded via delta logic. No manual curation, seed CSVs, or hardcoded data is involved at any stage.

## Glossary

- **Photon_API**: A free, open-source geocoding API at `https://photon.komoot.io/api` powered by ElasticSearch with fuzzy/typo-tolerant matching. Accepts query params `q` (search text), `lang` (language), `limit` (max results). Returns GeoJSON FeatureCollection with `geometry.coordinates` as `[longitude, latitude]`. No API key required.
- **Geocoding_Script**: A Python script at `src/enrichment/geocode_venues.py` that reads venue-city pairs from DuckDB, calls the Photon_API for each pair, and writes results into the `bronze.venue_coordinates` table.
- **dim_venues**: The gold-layer dbt model providing the venue dimension table, currently containing venue name, city, match counts, and first/last match dates — to be enriched with latitude and longitude.
- **stg_venue_coordinates**: A silver-layer dbt model that cleans and types the raw geocoding data from `bronze.venue_coordinates`.
- **Venue_Coordinate**: A pair of latitude (decimal degrees, -90 to 90) and longitude (decimal degrees, -180 to 180) values identifying a geographic location.
- **Delta_Logic**: The idempotent pattern where the Geocoding_Script compares venue-city pairs in the source data against those already present in `bronze.venue_coordinates`, and only geocodes the difference — ensuring no duplicate rows and no redundant API calls.
- **Bronze_Schema**: The `bronze` schema in DuckDB where raw/ingested data is stored (e.g., `bronze.matches`, `bronze.deliveries`, `bronze.venue_coordinates`).

## Requirements

### Requirement 1: Venue Geocoding Script

**User Story:** As a data engineer, I want an automated Python script that dynamically geocodes all venue-city pairs from the existing match data using the Photon API, so that venue coordinates are always up to date without any manual curation, seed CSVs, or hardcoded data.

#### Acceptance Criteria

1. WHEN executed, THE Geocoding_Script SHALL read unique venue-city pairs from the existing match data in DuckDB (from `bronze.matches` or the `stg_matches` silver model).
2. THE Geocoding_Script SHALL call the Photon_API at `https://photon.komoot.io/api` with query parameters `q` (constructed from venue name and city), `lang=en`, and `limit=3` for each venue-city pair requiring geocoding.
3. WHEN the Photon_API returns a valid GeoJSON FeatureCollection with at least one feature, THE Geocoding_Script SHALL extract the longitude from `geometry.coordinates[0]` and the latitude from `geometry.coordinates[1]` of the top result.
4. THE Geocoding_Script SHALL store geocoding results in a `bronze.venue_coordinates` table in DuckDB with columns including venue, city, latitude, longitude, and the Photon API response name for traceability.
5. THE Geocoding_Script SHALL implement Delta_Logic: compare venue-city pairs in the source data against those already in `bronze.venue_coordinates`, and only geocode venues that do not yet have a row in the table.
6. WHEN the DuckDB database does not yet contain a `bronze.venue_coordinates` table (fresh clone scenario), THE Geocoding_Script SHALL create the table and geocode all venue-city pairs.
7. IF the Photon_API returns an empty FeatureCollection for a venue-city pair, THEN THE Geocoding_Script SHALL log a warning with the venue name and city, and store the row with NULL latitude and longitude.
8. IF the Photon_API request fails due to a network or HTTP error, THEN THE Geocoding_Script SHALL retry the request up to 3 times with exponential backoff before logging the failure and continuing to the next venue.
9. THE Geocoding_Script SHALL output coordinates with at least 4 decimal places of precision (approximately 11-meter accuracy).
10. THE Geocoding_Script SHALL include a brief delay between consecutive Photon_API requests to avoid overwhelming the free service.

### Requirement 2: dbt Silver Model for Venue Coordinates

**User Story:** As a data engineer, I want a dbt staging model that cleans and types the raw geocoding data from the bronze layer, so that downstream gold models consume well-structured coordinate data.

#### Acceptance Criteria

1. THE stg_venue_coordinates model SHALL source data from the `bronze.venue_coordinates` table.
2. THE stg_venue_coordinates model SHALL cast latitude and longitude as DOUBLE precision numeric types.
3. THE stg_venue_coordinates model SHALL include columns: venue, city, latitude, longitude.
4. WHEN `dbt run` is executed after the Geocoding_Script has populated `bronze.venue_coordinates`, THE stg_venue_coordinates model SHALL reflect the current contents of the bronze table without manual intervention.

### Requirement 3: Enriched dim_venues Gold Model

**User Story:** As a data analyst, I want the `dim_venues` model to include latitude and longitude columns, so that I can perform location-based analytics and enable the weather enrichment pipeline.

#### Acceptance Criteria

1. THE dim_venues model SHALL include `latitude` and `longitude` columns sourced from the stg_venue_coordinates model via a left join on venue and city.
2. THE dim_venues model SHALL retain all existing columns and their values unchanged (venue, city, total_matches, first_match_date, last_match_date).
3. WHEN a venue has no matching coordinates in stg_venue_coordinates, THE dim_venues model SHALL return NULL for latitude and longitude for that venue.
4. THE dim_venues model SHALL cast latitude and longitude as DOUBLE precision numeric types.
5. WHEN a new venue appears in the Cricsheet match data and the pipeline is re-run, THE dim_venues model SHALL include coordinates for the new venue after the Geocoding_Script geocodes the delta.

### Requirement 4: Dagster Asset Integration

**User Story:** As a data engineer, I want the geocoding script wrapped as a Dagster asset, so that it integrates into the existing orchestration pipeline and runs automatically as part of `make all` on a fresh clone.

#### Acceptance Criteria

1. THE Dagster asset for venue geocoding SHALL execute the Geocoding_Script after the bronze match data has been loaded (downstream of the ingestion asset).
2. THE Dagster asset for venue geocoding SHALL execute before the dbt transformation assets that depend on `bronze.venue_coordinates`.
3. WHEN the Dagster pipeline is materialized end-to-end (including via `make all`), THE venue geocoding asset SHALL run in the correct dependency order without manual intervention.
4. WHEN a new venue appears in the Cricsheet match data, THE next pipeline run SHALL geocode the new venue automatically without any manual steps.

### Requirement 5: dbt Schema Tests for Venue Coordinates

**User Story:** As a data engineer, I want dbt tests that validate the venue coordinates data, so that data quality issues are caught automatically during the CI pipeline.

#### Acceptance Criteria

1. THE stg_venue_coordinates model schema tests SHALL validate that latitude values are between -90 and 90 when not NULL.
2. THE stg_venue_coordinates model schema tests SHALL validate that longitude values are between -180 and 180 when not NULL.
3. THE dim_venues model schema tests SHALL validate that the venue-city uniqueness constraint is preserved after the coordinates join.
4. WHEN `dbt test` is executed, THE schema tests SHALL pass with zero failures against the current dataset.

### Requirement 6: pytest Validation for Venue Coordinates

**User Story:** As a data engineer, I want pytest integration tests that verify the geocoding pipeline output and the enriched dim_venues model, so that regressions are caught in the CI pipeline.

#### Acceptance Criteria

1. THE pytest test suite SHALL include a test that verifies `bronze.venue_coordinates` contains a row for every unique venue-city combination present in the source match data.
2. THE pytest test suite SHALL include a test that verifies latitude and longitude values in `dim_venues` are populated for at least 90% of venues (allowing for a small number of unresolvable venues).
3. THE pytest test suite SHALL include a test that verifies the total row count of `dim_venues` remains unchanged after adding coordinates (currently 63 rows).
4. THE pytest test suite SHALL include a test that verifies no existing column values in `dim_venues` (venue, city, total_matches, first_match_date, last_match_date) are altered by the coordinates enrichment.
5. THE pytest test suite SHALL include a test that verifies the Delta_Logic by confirming that re-running the Geocoding_Script does not duplicate rows in `bronze.venue_coordinates`.
