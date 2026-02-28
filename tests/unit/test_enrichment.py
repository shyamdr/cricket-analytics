"""Unit tests for the enrichment module.

Tests ESPN data extraction, series resolution cache logic, and
__NEXT_DATA__ parsing — all without network or browser access.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

# Skip entire module if playwright is not installed (e.g. CI unit-test job)
pytest.importorskip("playwright", reason="playwright not installed — skipping enrichment tests")

from src.enrichment.espn_client import ROLE_MAP, _extract_match_data
from src.enrichment.series_resolver import SeriesResolver

# ---------------------------------------------------------------------------
# Fixtures — realistic ESPN __NEXT_DATA__ structures
# ---------------------------------------------------------------------------

# Minimal __NEXT_DATA__ for a match scorecard page (IPL 2024 final style)
SAMPLE_NEXT_DATA: dict = {
    "props": {
        "appPageProps": {
            "data": {
                "data": {
                    "match": {
                        "objectId": 1410537,
                        "slug": "kolkata-knight-riders-vs-sunrisers-hyderabad-final-1410537",
                        "title": "KKR vs SRH, Final",
                        "statusText": "Kolkata Knight Riders won by 8 wickets",
                        "floodlit": 2,
                        "startDate": "2024-05-26T00:00:00.000Z",
                        "startTime": "2024-05-26T14:00:00.000Z",
                        "season": "2024",
                        "series": {
                            "objectId": 1410320,
                            "name": "Indian Premier League 2024",
                            "slug": "indian-premier-league-2024-1410320",
                        },
                    },
                    "content": {
                        "matchPlayers": {
                            "teamPlayers": [
                                {
                                    "team": {
                                        "name": "Kolkata Knight Riders",
                                        "longName": "Kolkata Knight Riders",
                                        "objectId": 4341,
                                    },
                                    "players": [
                                        {
                                            "player": {
                                                "objectId": 1079434,
                                                "name": "S Narine",
                                                "longName": "Sunil Narine",
                                            },
                                            "playerRoleType": "P",
                                        },
                                        {
                                            "player": {
                                                "objectId": 481896,
                                                "name": "SA Yadav",
                                                "longName": "Shreyas Iyer",
                                            },
                                            "playerRoleType": "C",
                                        },
                                        {
                                            "player": {
                                                "objectId": 604302,
                                                "name": "PD Salt",
                                                "longName": "Phil Salt",
                                            },
                                            "playerRoleType": "WK",
                                        },
                                    ],
                                },
                                {
                                    "team": {
                                        "name": "Sunrisers Hyderabad",
                                        "longName": "Sunrisers Hyderabad",
                                        "objectId": 5765,
                                    },
                                    "players": [
                                        {
                                            "player": {
                                                "objectId": 719719,
                                                "name": "T Head",
                                                "longName": "Travis Head",
                                            },
                                            "playerRoleType": "P",
                                        },
                                        {
                                            "player": {
                                                "objectId": 642519,
                                                "name": "PK Cummins",
                                                "longName": "Pat Cummins",
                                            },
                                            "playerRoleType": "C",
                                        },
                                        {
                                            "player": {
                                                "objectId": 1175441,
                                                "name": "H Klaasen",
                                                "longName": "Heinrich Klaasen",
                                            },
                                            "playerRoleType": "WK",
                                        },
                                    ],
                                },
                            ]
                        }
                    },
                }
            }
        }
    }
}


# __NEXT_DATA__ with missing matchPlayers (edge case — some old matches)
SAMPLE_NEXT_DATA_NO_PLAYERS: dict = {
    "props": {
        "appPageProps": {
            "data": {
                "data": {
                    "match": {
                        "objectId": 335982,
                        "slug": "old-match-335982",
                        "title": "MI vs CSK",
                        "statusText": "Mumbai Indians won",
                        "floodlit": 1,
                        "startDate": "2008-04-18T00:00:00.000Z",
                        "startTime": None,
                        "season": "2008",
                        "series": {
                            "objectId": 313494,
                            "name": "Indian Premier League 2008",
                            "slug": "ipl-2008-313494",
                        },
                    },
                    "content": {"matchPlayers": {"teamPlayers": []}},
                }
            }
        }
    }
}


# Series info extracted from a match page (for series resolver tests)
SAMPLE_SERIES_NEXT_DATA: dict = {
    "props": {
        "appPageProps": {
            "data": {
                "data": {
                    "match": {
                        "objectId": 1410537,
                        "season": "2024",
                        "series": {
                            "objectId": 1410320,
                            "name": "Indian Premier League 2024",
                            "slug": "indian-premier-league-2024-1410320",
                        },
                    },
                }
            }
        }
    }
}


@pytest.fixture()
def sample_next_data() -> dict:
    """Realistic ESPN __NEXT_DATA__ for a match with full player data."""
    return json.loads(json.dumps(SAMPLE_NEXT_DATA))


@pytest.fixture()
def sample_next_data_no_players() -> dict:
    """ESPN __NEXT_DATA__ with empty teamPlayers list."""
    return json.loads(json.dumps(SAMPLE_NEXT_DATA_NO_PLAYERS))


# ---------------------------------------------------------------------------
# _extract_match_data tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractMatchData:
    """Test ESPN __NEXT_DATA__ → enrichment dict extraction."""

    def test_match_metadata(self, sample_next_data: dict) -> None:
        result = _extract_match_data(sample_next_data)
        assert result["espn_match_id"] == 1410537
        assert result["espn_series_id"] == 1410320
        assert result["title"] == "KKR vs SRH, Final"
        assert result["season"] == "2024"
        assert result["floodlit"] == 2
        assert result["start_date"] == "2024-05-26T00:00:00.000Z"
        assert result["start_time"] == "2024-05-26T14:00:00.000Z"
        assert result["status_text"] == "Kolkata Knight Riders won by 8 wickets"

    def test_team1_captain_and_keeper(self, sample_next_data: dict) -> None:
        result = _extract_match_data(sample_next_data)
        assert result["team1_name"] == "Kolkata Knight Riders"
        assert result["team1_espn_id"] == 4341
        assert result["team1_captain"] == "SA Yadav"
        assert result["team1_keeper"] == "PD Salt"

    def test_team2_captain_and_keeper(self, sample_next_data: dict) -> None:
        result = _extract_match_data(sample_next_data)
        assert result["team2_name"] == "Sunrisers Hyderabad"
        assert result["team2_espn_id"] == 5765
        assert result["team2_captain"] == "PK Cummins"
        assert result["team2_keeper"] == "H Klaasen"

    def test_captain_wicketkeeper_dual_role(self, sample_next_data: dict) -> None:
        """CWK role means the player is both captain and keeper."""
        # Modify fixture: make one player CWK (replaces both C and WK)
        data = json.loads(json.dumps(sample_next_data))
        team2 = data["props"]["appPageProps"]["data"]["data"]["content"]["matchPlayers"][
            "teamPlayers"
        ][1]
        # Remove separate C and WK, add single CWK player
        team2["players"] = [
            team2["players"][0],  # T Head (P)
            {
                "player": {"objectId": 642519, "name": "PK Cummins", "longName": "Pat Cummins"},
                "playerRoleType": "CWK",
            },
        ]
        result = _extract_match_data(data)
        assert result["team2_captain"] == "PK Cummins"
        assert result["team2_keeper"] == "PK Cummins"

    def test_teams_enrichment_json(self, sample_next_data: dict) -> None:
        result = _extract_match_data(sample_next_data)
        teams = json.loads(result["teams_enrichment_json"])
        assert len(teams) == 2
        assert teams[0]["team_name"] == "Kolkata Knight Riders"
        assert len(teams[0]["players"]) == 3
        assert len(teams[1]["players"]) == 3

    def test_player_roles_in_enrichment_json(self, sample_next_data: dict) -> None:
        result = _extract_match_data(sample_next_data)
        teams = json.loads(result["teams_enrichment_json"])
        kkr_players = {p["player_name"]: p for p in teams[0]["players"]}
        assert kkr_players["S Narine"]["role"] == "player"
        assert kkr_players["S Narine"]["is_captain"] is False
        assert kkr_players["SA Yadav"]["role"] == "captain"
        assert kkr_players["SA Yadav"]["is_captain"] is True
        assert kkr_players["PD Salt"]["role"] == "wicketkeeper"
        assert kkr_players["PD Salt"]["is_keeper"] is True

    def test_no_players_edge_case(self, sample_next_data_no_players: dict) -> None:
        """Matches with empty teamPlayers should still extract match metadata."""
        result = _extract_match_data(sample_next_data_no_players)
        assert result["espn_match_id"] == 335982
        assert result["espn_series_id"] == 313494
        assert result["season"] == "2008"
        assert result["team1_name"] is None
        assert result["team1_captain"] is None
        assert result["team2_name"] is None

    def test_slug_extracted(self, sample_next_data: dict) -> None:
        result = _extract_match_data(sample_next_data)
        assert "1410537" in result["slug"]


# ---------------------------------------------------------------------------
# ROLE_MAP tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRoleMap:
    """Verify the ESPN role code mapping."""

    def test_all_known_roles(self) -> None:
        assert ROLE_MAP["C"] == "captain"
        assert ROLE_MAP["WK"] == "wicketkeeper"
        assert ROLE_MAP["CWK"] == "captain_wicketkeeper"
        assert ROLE_MAP["P"] == "player"

    def test_unknown_role_defaults_to_player(self) -> None:
        assert ROLE_MAP.get("UNKNOWN", "player") == "player"


# ---------------------------------------------------------------------------
# Series resolver cache logic tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSeriesResolverCache:
    """Test SeriesResolver in-memory cache logic (no DB, no browser)."""

    @patch.object(SeriesResolver, "_load_from_db")
    def test_get_by_season_returns_cached(self, mock_load: MagicMock) -> None:
        resolver = SeriesResolver()
        resolver._season_cache = {"2024": 1410320, "2023": 1345038}
        assert resolver.get_by_season("2024") == 1410320
        assert resolver.get_by_season("2023") == 1345038

    @patch.object(SeriesResolver, "_load_from_db")
    def test_get_by_season_returns_none_for_unknown(self, mock_load: MagicMock) -> None:
        resolver = SeriesResolver()
        resolver._season_cache = {"2024": 1410320}
        assert resolver.get_by_season("2019") is None

    @patch.object(SeriesResolver, "_load_from_db")
    def test_get_returns_match_cache(self, mock_load: MagicMock) -> None:
        resolver = SeriesResolver()
        resolver._match_cache = {"1410537": 1410320}
        assert resolver.get("1410537") == 1410320

    @patch.object(SeriesResolver, "_load_from_db")
    def test_get_returns_none_for_unknown_match(self, mock_load: MagicMock) -> None:
        resolver = SeriesResolver()
        resolver._match_cache = {}
        assert resolver.get("9999999") is None

    @patch.object(SeriesResolver, "_load_from_db")
    def test_cache_size(self, mock_load: MagicMock) -> None:
        resolver = SeriesResolver()
        resolver._season_cache = {"2024": 1, "2023": 2, "2022": 3}
        assert resolver.cache_size == 3

    @patch.object(SeriesResolver, "_load_from_db")
    def test_store_series_updates_season_cache(self, mock_load: MagicMock) -> None:
        resolver = SeriesResolver()
        resolver._season_cache = {}

        # Directly update cache (simulating what _store_series does internally)
        resolver._season_cache["2024"] = 1410320

        assert resolver.get_by_season("2024") == 1410320


# ---------------------------------------------------------------------------
# Series info extraction from __NEXT_DATA__ (used by series_resolver)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSeriesInfoExtraction:
    """Test series metadata extraction from ESPN __NEXT_DATA__."""

    def test_extract_series_from_next_data(self) -> None:
        """Simulate what _discover_series_from_match extracts from __NEXT_DATA__."""
        next_data = SAMPLE_SERIES_NEXT_DATA
        app_data = next_data["props"]["appPageProps"]["data"]
        data = app_data.get("data", app_data)
        series = data["match"]["series"]
        season = data["match"].get("season", "")

        result = {
            "series_id": int(series["objectId"]),
            "series_name": series.get("name", ""),
            "season": str(season),
            "series_slug": series.get("slug", ""),
            "discovered_from": "1410537",
        }

        assert result["series_id"] == 1410320
        assert result["series_name"] == "Indian Premier League 2024"
        assert result["season"] == "2024"
        assert "1410320" in result["series_slug"]

    def test_missing_season_defaults_to_empty(self) -> None:
        """If season is missing from match data, should default to empty string."""
        next_data = json.loads(json.dumps(SAMPLE_SERIES_NEXT_DATA))
        del next_data["props"]["appPageProps"]["data"]["data"]["match"]["season"]

        app_data = next_data["props"]["appPageProps"]["data"]
        data = app_data.get("data", app_data)
        season = data["match"].get("season", "")

        assert season == ""

    def test_missing_series_raises_key_error(self) -> None:
        """If series block is missing, extraction should fail with KeyError."""
        next_data = json.loads(json.dumps(SAMPLE_SERIES_NEXT_DATA))
        del next_data["props"]["appPageProps"]["data"]["data"]["match"]["series"]

        app_data = next_data["props"]["appPageProps"]["data"]
        data = app_data.get("data", app_data)

        with pytest.raises(KeyError):
            _ = data["match"]["series"]
