"""Shared data access for the Streamlit UI."""

from __future__ import annotations

import duckdb
import streamlit as st

from src.config import settings


@st.cache_resource
def get_conn() -> duckdb.DuckDBPyConnection:
    """Get a cached read-only DuckDB connection."""
    return duckdb.connect(str(settings.duckdb_path), read_only=True)


def query(sql: str, params: list | None = None) -> list[dict]:
    """Execute SQL and return list of dicts."""
    conn = get_conn()
    result = conn.execute(sql, params or [])
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]
