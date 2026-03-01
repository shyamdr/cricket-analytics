"""Smoke tests — verify the system isn't fundamentally broken."""

from __future__ import annotations

import pytest

from src.config import settings

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@pytest.mark.smoke
class TestConfig:
    """Settings load correctly."""

    def test_project_root_exists(self) -> None:
        assert settings.project_root.exists()

    def test_schemas_defined(self) -> None:
        assert settings.bronze_schema == "bronze"
        assert settings.silver_schema == "main_silver"
        assert settings.gold_schema == "main_gold"

    def test_cricsheet_urls(self) -> None:
        assert "cricsheet.org" in settings.cricsheet_matches_url
        assert "cricsheet.org" in settings.cricsheet_people_url

    def test_imports(self) -> None:
        """Core modules are importable without errors."""
        from src.api import app, database  # noqa: F401
        from src.ingestion import bronze_loader, downloader  # noqa: F401


# ---------------------------------------------------------------------------
# Database connectivity
# ---------------------------------------------------------------------------


@pytest.mark.smoke
class TestDatabase:
    """DuckDB is accessible and has expected schemas."""

    def test_connection(self, db_conn) -> None:
        result = db_conn.execute("SELECT 1 AS ok").fetchone()
        assert result[0] == 1

    def test_bronze_schema_exists(self, db_conn) -> None:
        schemas = [
            r[0]
            for r in db_conn.execute(
                "SELECT schema_name FROM information_schema.schemata"
            ).fetchall()
        ]
        assert "bronze" in schemas

    def test_silver_schema_exists(self, db_conn) -> None:
        schemas = [
            r[0]
            for r in db_conn.execute(
                "SELECT schema_name FROM information_schema.schemata"
            ).fetchall()
        ]
        assert settings.silver_schema in schemas

    def test_gold_schema_exists(self, db_conn) -> None:
        schemas = [
            r[0]
            for r in db_conn.execute(
                "SELECT schema_name FROM information_schema.schemata"
            ).fetchall()
        ]
        assert settings.gold_schema in schemas

    def test_bronze_tables_exist(self, db_conn) -> None:
        tables = [
            r[0]
            for r in db_conn.execute(
                "SELECT table_name FROM information_schema.tables " "WHERE table_schema = 'bronze'"
            ).fetchall()
        ]
        assert "matches" in tables
        assert "deliveries" in tables
        assert "people" in tables

    def test_gold_tables_exist(self, db_conn) -> None:
        tables = [
            r[0]
            for r in db_conn.execute(
                "SELECT table_name FROM information_schema.tables "
                f"WHERE table_schema = '{settings.gold_schema}'"
            ).fetchall()
        ]
        for expected in [
            "dim_matches",
            "dim_players",
            "dim_teams",
            "dim_venues",
            "fact_deliveries",
            "fact_batting_innings",
            "fact_bowling_innings",
            "fact_match_summary",
        ]:
            assert expected in tables, f"Missing gold table: {expected}"


# ---------------------------------------------------------------------------
# API startup
# ---------------------------------------------------------------------------


@pytest.mark.smoke
class TestAPIStartup:
    """FastAPI app starts and health check works."""

    def test_health_check(self, api_client) -> None:
        resp = api_client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_openapi_docs(self, api_client) -> None:
        resp = api_client.get("/openapi.json")
        assert resp.status_code == 200
        assert "paths" in resp.json()
