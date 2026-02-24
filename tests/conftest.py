"""Shared fixtures for the cricket-analytics test suite."""

from __future__ import annotations

import json

import duckdb
import pytest
from fastapi.testclient import TestClient

from src.config import settings

# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: pure logic tests, no DB needed")
    config.addinivalue_line("markers", "integration: tests that hit the real DuckDB")
    config.addinivalue_line("markers", "smoke: quick sanity checks")


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_available() -> bool:
    """Check whether the DuckDB file exists (data pipeline has been run)."""
    return settings.duckdb_path.exists()


@pytest.fixture(scope="session")
def db_conn(db_available: bool):
    """Session-scoped read-only DuckDB connection."""
    if not db_available:
        pytest.skip("DuckDB not found — run `make all` first")
    conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def api_client(db_available: bool):
    """FastAPI TestClient backed by the real DuckDB."""
    if not db_available:
        pytest.skip("DuckDB not found — run `make all` first")
    from src.api.app import app

    with TestClient(app) as client:
        yield client


# ---------------------------------------------------------------------------
# Sample Cricsheet JSON (for unit tests — no DB needed)
# ---------------------------------------------------------------------------

SAMPLE_MATCH_JSON: dict = {
    "meta": {"data_version": "1.1.0", "created": "2025-01-01", "revision": 1},
    "info": {
        "balls_per_over": 6,
        "city": "Mumbai",
        "dates": ["2024-04-01"],
        "event": {"name": "Indian Premier League", "match_number": 1},
        "gender": "male",
        "match_type": "T20",
        "overs": 20,
        "season": "2024",
        "teams": ["Mumbai Indians", "Chennai Super Kings"],
        "toss": {"decision": "field", "winner": "Chennai Super Kings"},
        "venue": "Wankhede Stadium",
        "outcome": {"winner": "Mumbai Indians", "by": {"runs": 12}},
        "player_of_match": ["RG Sharma"],
        "players": {
            "Mumbai Indians": ["RG Sharma", "SA Yadav"],
            "Chennai Super Kings": ["MS Dhoni", "RA Jadeja"],
        },
        "registry": {
            "people": {
                "RG Sharma": "abc12345",
                "SA Yadav": "def67890",
                "MS Dhoni": "ghi11111",
                "RA Jadeja": "jkl22222",
            }
        },
    },
    "innings": [
        {
            "team": "Mumbai Indians",
            "overs": [
                {
                    "over": 0,
                    "deliveries": [
                        {
                            "batter": "RG Sharma",
                            "bowler": "RA Jadeja",
                            "non_striker": "SA Yadav",
                            "runs": {"batter": 4, "extras": 0, "total": 4},
                        },
                        {
                            "batter": "RG Sharma",
                            "bowler": "RA Jadeja",
                            "non_striker": "SA Yadav",
                            "runs": {"batter": 0, "extras": 1, "total": 1},
                            "extras": {"wides": 1},
                        },
                        {
                            "batter": "RG Sharma",
                            "bowler": "RA Jadeja",
                            "non_striker": "SA Yadav",
                            "runs": {"batter": 0, "extras": 0, "total": 0},
                            "wickets": [
                                {
                                    "player_out": "RG Sharma",
                                    "kind": "bowled",
                                }
                            ],
                        },
                    ],
                }
            ],
        }
    ],
}


@pytest.fixture()
def sample_match_json() -> dict:
    """Return a minimal Cricsheet match JSON for unit testing."""
    return json.loads(json.dumps(SAMPLE_MATCH_JSON))


# Sample match with no result
SAMPLE_NO_RESULT_JSON: dict = {
    "meta": {"data_version": "1.1.0", "created": "2025-01-01", "revision": 1},
    "info": {
        "balls_per_over": 6,
        "city": "Bangalore",
        "dates": ["2024-04-02"],
        "event": {"name": "Indian Premier League", "match_number": 2},
        "gender": "male",
        "match_type": "T20",
        "overs": 20,
        "season": "2024",
        "teams": ["Royal Challengers Bangalore", "Delhi Capitals"],
        "toss": {"decision": "bat", "winner": "Royal Challengers Bangalore"},
        "venue": "M Chinnaswamy Stadium",
        "outcome": {"result": "no result"},
        "players": {
            "Royal Challengers Bangalore": ["V Kohli"],
            "Delhi Capitals": ["R Pant"],
        },
        "registry": {"people": {"V Kohli": "aaa11111", "R Pant": "bbb22222"}},
    },
    "innings": [],
}


@pytest.fixture()
def sample_no_result_json() -> dict:
    """Return a Cricsheet match JSON with no result (rain, etc.)."""
    return json.loads(json.dumps(SAMPLE_NO_RESULT_JSON))
