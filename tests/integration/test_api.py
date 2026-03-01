"""Integration tests -- FastAPI endpoints against real DuckDB."""

from __future__ import annotations

import pytest

_V1 = "/api/v1"


@pytest.mark.integration
class TestHealthAndDocs:
    """Basic API health and documentation."""

    def test_root(self, api_client) -> None:
        resp = api_client.get("/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.integration
class TestPlayersAPI:
    """Player endpoints."""

    def test_list_players(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/players?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 10
        assert "player_name" in data[0]

    def test_search_players(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/players?search=Kohli")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any("Kohli" in p["player_name"] for p in data)

    def test_get_player(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/players/V Kohli")
        assert resp.status_code == 200
        data = resp.json()
        assert data["player_name"] == "V Kohli"

    def test_get_player_not_found(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/players/Nonexistent Player XYZ")
        assert resp.status_code == 404

    def test_player_batting(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/players/V Kohli/batting")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert "runs_scored" in data[0]

    def test_player_bowling(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/players/RA Jadeja/bowling")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert "wickets" in data[0]


@pytest.mark.integration
class TestTeamsAPI:
    """Team endpoints."""

    def test_list_teams(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/teams")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 10
        team_names = [t["team_name"] for t in data]
        assert "Mumbai Indians" in team_names
        assert "Chennai Super Kings" in team_names

    def test_get_team(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/teams/Mumbai Indians")
        assert resp.status_code == 200
        assert resp.json()["team_name"] == "Mumbai Indians"

    def test_get_team_not_found(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/teams/Fake Team FC")
        assert resp.status_code == 404

    def test_team_matches(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/teams/Mumbai Indians/matches")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert all("match_id" in m for m in data)

    def test_team_matches_by_season(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/teams/Mumbai Indians/matches?season=2024")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert all(m["season"] == "2024" for m in data)


@pytest.mark.integration
class TestMatchesAPI:
    """Match endpoints."""

    def test_list_matches(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/matches?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5

    def test_list_matches_by_season(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/matches?season=2020&limit=100")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert all(m["season"] == "2020" for m in data)

    def test_list_seasons(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/matches/seasons")
        assert resp.status_code == 200
        data = resp.json()
        seasons = [s["season"] for s in data]
        assert "2020" in seasons
        assert "2021" in seasons
        assert len(seasons) >= 17

    def test_list_venues(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/matches/venues")
        assert resp.status_code == 200
        assert len(resp.json()) >= 30

    def test_get_match_batting(self, api_client) -> None:
        matches = api_client.get(f"{_V1}/matches?limit=1").json()
        match_id = matches[0]["match_id"]
        resp = api_client.get(f"{_V1}/matches/{match_id}/batting")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert "runs_scored" in data[0]

    def test_get_match_bowling(self, api_client) -> None:
        matches = api_client.get(f"{_V1}/matches?limit=1").json()
        match_id = matches[0]["match_id"]
        resp = api_client.get(f"{_V1}/matches/{match_id}/bowling")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert "wickets" in data[0]


@pytest.mark.integration
class TestBattingAPI:
    """Batting analytics endpoints."""

    def test_top_run_scorers(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/batting/top?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        assert all(d["total_runs"] > 0 for d in data)
        assert data[0]["total_runs"] >= data[-1]["total_runs"]

    def test_top_run_scorers_by_season(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/batting/top?season=2024&limit=3")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_player_batting_stats(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/batting/stats/V Kohli")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["total_runs"] > 0

    def test_player_season_breakdown(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/batting/season-breakdown/V Kohli")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert all("season" in d for d in data)


@pytest.mark.integration
class TestBowlingAPI:
    """Bowling analytics endpoints."""

    def test_top_wicket_takers(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/bowling/top?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        assert all(d["total_wickets"] > 0 for d in data)
        assert data[0]["total_wickets"] >= data[-1]["total_wickets"]

    def test_player_bowling_stats(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/bowling/stats/YS Chahal")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["total_wickets"] > 0

    def test_player_bowling_season_breakdown(self, api_client) -> None:
        resp = api_client.get(f"{_V1}/bowling/season-breakdown/YS Chahal")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert all("season" in d for d in data)
