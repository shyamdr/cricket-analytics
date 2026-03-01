"""Integration tests — verify gold layer data quality against known facts."""

from __future__ import annotations

import pytest

from src.config import settings

_gold = settings.gold_schema


@pytest.mark.integration
class TestGoldLayerRowCounts:
    """Row counts should be within expected ranges."""

    def test_dim_matches_count(self, db_conn) -> None:
        (count,) = db_conn.execute(f"SELECT COUNT(*) FROM {_gold}.dim_matches").fetchone()
        assert count >= 1100, f"Expected >= 1100 matches, got {count}"

    def test_dim_players_count(self, db_conn) -> None:
        (count,) = db_conn.execute(f"SELECT COUNT(*) FROM {_gold}.dim_players").fetchone()
        assert count >= 900, f"Expected >= 900 players, got {count}"

    def test_dim_teams_count(self, db_conn) -> None:
        (count,) = db_conn.execute(f"SELECT COUNT(*) FROM {_gold}.dim_teams").fetchone()
        assert count >= 10, f"Expected >= 10 teams, got {count}"

    def test_dim_venues_count(self, db_conn) -> None:
        (count,) = db_conn.execute(f"SELECT COUNT(*) FROM {_gold}.dim_venues").fetchone()
        assert count >= 30, f"Expected >= 30 venues, got {count}"

    def test_fact_deliveries_count(self, db_conn) -> None:
        (count,) = db_conn.execute(f"SELECT COUNT(*) FROM {_gold}.fact_deliveries").fetchone()
        assert count >= 250_000, f"Expected >= 250K deliveries, got {count}"

    def test_fact_batting_innings_count(self, db_conn) -> None:
        (count,) = db_conn.execute(f"SELECT COUNT(*) FROM {_gold}.fact_batting_innings").fetchone()
        assert count >= 15_000, f"Expected >= 15K batting innings, got {count}"

    def test_fact_bowling_innings_count(self, db_conn) -> None:
        (count,) = db_conn.execute(f"SELECT COUNT(*) FROM {_gold}.fact_bowling_innings").fetchone()
        assert count >= 12_000, f"Expected >= 12K bowling innings, got {count}"

    def test_fact_match_summary_count(self, db_conn) -> None:
        (count,) = db_conn.execute(f"SELECT COUNT(*) FROM {_gold}.fact_match_summary").fetchone()
        assert count >= 2_000, f"Expected >= 2K match summaries, got {count}"


@pytest.mark.integration
class TestGoldLayerDataIntegrity:
    """Verify data relationships and constraints in the gold layer."""

    def test_no_null_match_ids(self, db_conn) -> None:
        (count,) = db_conn.execute(
            f"SELECT COUNT(*) FROM {_gold}.dim_matches WHERE match_id IS NULL"
        ).fetchone()
        assert count == 0

    def test_unique_match_ids(self, db_conn) -> None:
        (total,) = db_conn.execute(f"SELECT COUNT(*) FROM {_gold}.dim_matches").fetchone()
        (distinct,) = db_conn.execute(
            f"SELECT COUNT(DISTINCT match_id) FROM {_gold}.dim_matches"
        ).fetchone()
        assert total == distinct, f"Duplicate match_ids: {total} total vs {distinct} distinct"

    def test_seasons_are_valid(self, db_conn) -> None:
        """All seasons should be 4-digit year strings."""
        seasons = [
            r[0]
            for r in db_conn.execute(
                f"SELECT DISTINCT season FROM {_gold}.dim_matches ORDER BY season"
            ).fetchall()
        ]
        for s in seasons:
            assert len(s) == 4, f"Season '{s}' is not a 4-digit year"
            assert s.isdigit(), f"Season '{s}' is not numeric"

    def test_no_2020_2021_season_merge(self, db_conn) -> None:
        """Regression: 2020 and 2021 should be separate seasons (COVID fix)."""
        seasons = [
            r[0]
            for r in db_conn.execute(f"SELECT DISTINCT season FROM {_gold}.dim_matches").fetchall()
        ]
        assert "2020" in seasons, "Missing 2020 season (COVID UAE bubble)"
        assert "2021" in seasons, "Missing 2021 season"

        (count_2020,) = db_conn.execute(
            f"SELECT COUNT(*) FROM {_gold}.dim_matches WHERE season = '2020'"
        ).fetchone()
        (count_2021,) = db_conn.execute(
            f"SELECT COUNT(*) FROM {_gold}.dim_matches WHERE season = '2021'"
        ).fetchone()
        assert count_2020 <= 65, f"2020 has {count_2020} matches — too many"
        assert count_2021 <= 65, f"2021 has {count_2021} matches — too many"

    def test_match_dates_in_range(self, db_conn) -> None:
        """Match dates should be between 2008 and 2026."""
        min_date, max_date = db_conn.execute(
            f"SELECT MIN(match_date), MAX(match_date) FROM {_gold}.dim_matches"
        ).fetchone()
        assert min_date.year >= 2008
        assert max_date.year <= 2026

    def test_every_match_has_two_teams(self, db_conn) -> None:
        (count,) = db_conn.execute(
            f"SELECT COUNT(*) FROM {_gold}.dim_matches WHERE team1 IS NULL OR team2 IS NULL"
        ).fetchone()
        assert count == 0, f"{count} matches missing team1 or team2"

    def test_batting_innings_reference_valid_matches(self, db_conn) -> None:
        """Every batting innings should reference an existing match."""
        (orphans,) = db_conn.execute(f"""
            SELECT COUNT(*) FROM {_gold}.fact_batting_innings bi
            LEFT JOIN {_gold}.dim_matches m ON bi.match_id = m.match_id
            WHERE m.match_id IS NULL
        """).fetchone()
        assert orphans == 0, f"{orphans} batting innings reference non-existent matches"

    def test_bowling_innings_reference_valid_matches(self, db_conn) -> None:
        (orphans,) = db_conn.execute(f"""
            SELECT COUNT(*) FROM {_gold}.fact_bowling_innings bo
            LEFT JOIN {_gold}.dim_matches m ON bo.match_id = m.match_id
            WHERE m.match_id IS NULL
        """).fetchone()
        assert orphans == 0, f"{orphans} bowling innings reference non-existent matches"

    def test_no_negative_runs(self, db_conn) -> None:
        (count,) = db_conn.execute(
            f"SELECT COUNT(*) FROM {_gold}.fact_batting_innings WHERE runs_scored < 0"
        ).fetchone()
        assert count == 0

    def test_strike_rate_reasonable(self, db_conn) -> None:
        """Strike rates should be between 0 and 700 (theoretical max)."""
        (count,) = db_conn.execute(
            f"SELECT COUNT(*) FROM {_gold}.fact_batting_innings "
            "WHERE strike_rate < 0 OR strike_rate > 700"
        ).fetchone()
        assert count == 0, f"{count} batting innings with unreasonable strike rate"

    def test_economy_rate_reasonable(self, db_conn) -> None:
        """Economy rates should be non-negative. Very high rates are valid for
        partial overs (e.g. 0.1 overs bowled → extrapolated economy can exceed 36)."""
        (count,) = db_conn.execute(
            f"SELECT COUNT(*) FROM {_gold}.fact_bowling_innings WHERE economy_rate < 0"
        ).fetchone()
        assert count == 0, f"{count} bowling innings with negative economy rate"
