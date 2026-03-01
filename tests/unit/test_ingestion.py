"""Unit tests for the ingestion parsing logic."""

from __future__ import annotations

import pytest

from src.ingestion.bronze_loader import _parse_deliveries, _parse_match_info

# ---------------------------------------------------------------------------
# _parse_match_info
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseMatchInfo:
    """Test match-level metadata extraction from Cricsheet JSON."""

    def test_basic_fields(self, sample_match_json: dict) -> None:
        result = _parse_match_info("1234567", sample_match_json)
        assert result["match_id"] == "1234567"
        assert result["season"] == "2024"
        assert result["date"] == "2024-04-01"
        assert result["city"] == "Mumbai"
        assert result["venue"] == "Wankhede Stadium"
        assert result["team1"] == "Mumbai Indians"
        assert result["team2"] == "Chennai Super Kings"

    def test_toss_info(self, sample_match_json: dict) -> None:
        result = _parse_match_info("1234567", sample_match_json)
        assert result["toss_winner"] == "Chennai Super Kings"
        assert result["toss_decision"] == "field"

    def test_outcome_by_runs(self, sample_match_json: dict) -> None:
        result = _parse_match_info("1234567", sample_match_json)
        assert result["outcome_winner"] == "Mumbai Indians"
        assert result["outcome_by_runs"] == 12
        assert result["outcome_by_wickets"] is None
        assert result["outcome_method"] is None
        assert result["outcome_result"] is None

    def test_no_result_match(self, sample_no_result_json: dict) -> None:
        result = _parse_match_info("9999999", sample_no_result_json)
        assert result["outcome_winner"] is None
        assert result["outcome_result"] == "no result"
        assert result["outcome_by_runs"] is None
        assert result["outcome_by_wickets"] is None

    def test_event_info(self, sample_match_json: dict) -> None:
        result = _parse_match_info("1234567", sample_match_json)
        assert result["event_name"] == "Indian Premier League"
        assert result["event_match_number"] == 1
        assert result["event_stage"] is None

    def test_player_of_match(self, sample_match_json: dict) -> None:
        result = _parse_match_info("1234567", sample_match_json)
        assert result["player_of_match"] == "RG Sharma"

    def test_match_type_and_overs(self, sample_match_json: dict) -> None:
        result = _parse_match_info("1234567", sample_match_json)
        assert result["match_type"] == "T20"
        assert result["overs"] == 20
        assert result["balls_per_over"] == 6

    def test_data_version(self, sample_match_json: dict) -> None:
        result = _parse_match_info("1234567", sample_match_json)
        assert result["data_version"] == "1.1.0"

    def test_players_json(self, sample_match_json: dict) -> None:
        import json

        result = _parse_match_info("1234567", sample_match_json)
        team1_players = json.loads(result["players_team1_json"])
        team2_players = json.loads(result["players_team2_json"])
        assert "RG Sharma" in team1_players
        assert "MS Dhoni" in team2_players

    def test_registry_json(self, sample_match_json: dict) -> None:
        import json

        result = _parse_match_info("1234567", sample_match_json)
        registry = json.loads(result["registry_json"])
        assert registry["RG Sharma"] == "abc12345"
        assert registry["MS Dhoni"] == "ghi11111"

    def test_meta_fields(self, sample_match_json: dict) -> None:
        result = _parse_match_info("1234567", sample_match_json)
        assert result["meta_created"] == "2025-01-01"
        assert result["meta_revision"] == 1

    def test_team_type(self, sample_match_json: dict) -> None:
        result = _parse_match_info("1234567", sample_match_json)
        assert result["team_type"] == "club"

    def test_officials_json(self, sample_match_json: dict) -> None:
        import json

        result = _parse_match_info("1234567", sample_match_json)
        officials = json.loads(result["officials_json"])
        assert "AY Dandekar" in officials["umpires"]
        assert "J Srinath" in officials["match_referees"]

    def test_optional_fields_absent(self, sample_match_json: dict) -> None:
        """Fields not present in the source JSON should be None."""
        result = _parse_match_info("1234567", sample_match_json)
        assert result["match_type_number"] is None
        assert result["toss_uncontested"] is None
        assert result["event_group"] is None
        assert result["supersubs_json"] is None
        assert result["missing_json"] is None

    def test_no_result_empty_innings(self, sample_no_result_json: dict) -> None:
        """No-result match should still parse match info correctly."""
        result = _parse_match_info("9999999", sample_no_result_json)
        assert result["team1"] == "Royal Challengers Bangalore"
        assert result["team2"] == "Delhi Capitals"
        assert result["player_of_match"] is None


# ---------------------------------------------------------------------------
# _parse_deliveries
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseDeliveries:
    """Test ball-by-ball delivery extraction from Cricsheet JSON."""

    def test_delivery_count(self, sample_match_json: dict) -> None:
        rows = _parse_deliveries("1234567", sample_match_json)
        # 3 deliveries in the sample (including a wide)
        assert len(rows) == 3

    def test_basic_delivery(self, sample_match_json: dict) -> None:
        rows = _parse_deliveries("1234567", sample_match_json)
        first = rows[0]
        assert first["match_id"] == "1234567"
        assert first["innings"] == 1
        assert first["batting_team"] == "Mumbai Indians"
        assert first["over_num"] == 0
        assert first["ball_num"] == 1
        assert first["batter"] == "RG Sharma"
        assert first["bowler"] == "RA Jadeja"
        assert first["non_striker"] == "SA Yadav"
        assert first["batter_runs"] == 4
        assert first["extras_runs"] == 0
        assert first["total_runs"] == 4
        assert first["is_wicket"] is False

    def test_wide_delivery(self, sample_match_json: dict) -> None:
        rows = _parse_deliveries("1234567", sample_match_json)
        wide = rows[1]
        assert wide["extras_wides"] == 1
        assert wide["extras_runs"] == 1
        assert wide["batter_runs"] == 0
        assert wide["total_runs"] == 1

    def test_wicket_delivery(self, sample_match_json: dict) -> None:
        rows = _parse_deliveries("1234567", sample_match_json)
        wicket = rows[2]
        assert wicket["is_wicket"] is True
        assert wicket["wicket_player_out"] == "RG Sharma"
        assert wicket["wicket_kind"] == "bowled"
        assert wicket["wicket_fielder1"] is None  # bowled has no fielder

    def test_non_boundary_flag(self, sample_match_json: dict) -> None:
        """First delivery has non_boundary=True in the fixture."""
        rows = _parse_deliveries("1234567", sample_match_json)
        assert rows[0]["non_boundary"] is True
        # Second delivery has no non_boundary key → None
        assert rows[1]["non_boundary"] is None

    def test_review_fields(self, sample_match_json: dict) -> None:
        """Second delivery (wide) has a review in the fixture."""
        rows = _parse_deliveries("1234567", sample_match_json)
        review_row = rows[1]
        assert review_row["review_by"] == "Chennai Super Kings"
        assert review_row["review_umpire"] == "AY Dandekar"
        assert review_row["review_batter"] == "RG Sharma"
        assert review_row["review_decision"] == "struck down"
        assert review_row["review_type"] == "wicket"
        assert review_row["review_umpires_call"] is None

    def test_review_absent(self, sample_match_json: dict) -> None:
        """First delivery has no review — all review fields should be None."""
        rows = _parse_deliveries("1234567", sample_match_json)
        first = rows[0]
        assert first["review_by"] is None
        assert first["review_umpire"] is None
        assert first["review_decision"] is None

    def test_replacements_json(self, sample_match_json: dict) -> None:
        """Third delivery (wicket) has an impact_player replacement."""
        import json

        rows = _parse_deliveries("1234567", sample_match_json)
        wicket_row = rows[2]
        repl = json.loads(wicket_row["replacements_json"])
        assert repl["match"][0]["in"] == "JC Buttler"
        assert repl["match"][0]["reason"] == "impact_player"

    def test_replacements_absent(self, sample_match_json: dict) -> None:
        """First delivery has no replacements — should be None."""
        rows = _parse_deliveries("1234567", sample_match_json)
        assert rows[0]["replacements_json"] is None

    def test_no_result_no_deliveries(self, sample_no_result_json: dict) -> None:
        rows = _parse_deliveries("9999999", sample_no_result_json)
        assert len(rows) == 0

    def test_super_over_flag(self) -> None:
        """Super over innings should be flagged."""
        data = {
            "innings": [
                {
                    "team": "Team A",
                    "super_over": True,
                    "overs": [
                        {
                            "over": 0,
                            "deliveries": [
                                {
                                    "batter": "Player1",
                                    "bowler": "Player2",
                                    "non_striker": "Player3",
                                    "runs": {"batter": 6, "extras": 0, "total": 6},
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        rows = _parse_deliveries("SO_TEST", data)
        assert len(rows) == 1
        assert rows[0]["is_super_over"] is True
