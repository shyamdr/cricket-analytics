"""Unit tests for project configuration."""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestSettings:
    """Verify Settings class defaults and behavior."""

    def test_project_root_is_absolute(self) -> None:
        from src.config import settings

        assert settings.project_root.is_absolute()

    def test_data_dir_under_project_root(self) -> None:
        from src.config import settings

        assert str(settings.data_dir).startswith(str(settings.project_root))

    def test_duckdb_path_extension(self) -> None:
        from src.config import settings

        assert settings.duckdb_path.suffix == ".duckdb"

    def test_default_ports(self) -> None:
        from src.config import settings

        assert settings.api_port == 8000
        assert settings.ui_port == 8501

    def test_schemas_are_strings(self) -> None:
        from src.config import settings

        assert isinstance(settings.bronze_schema, str)
        assert isinstance(settings.silver_schema, str)
        assert isinstance(settings.gold_schema, str)

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings can be overridden via environment variables."""
        monkeypatch.setenv("CRICKET_API_PORT", "9999")
        from src.config import Settings

        s = Settings()
        assert s.api_port == 9999
