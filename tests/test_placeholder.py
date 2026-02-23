"""Placeholder test to prevent pytest exit code 5 (no tests collected)."""


def test_project_imports() -> None:
    """Verify core project modules are importable."""
    from src.config import settings

    assert settings.bronze_schema == "bronze"
