"""Shared data access for the Streamlit UI.

Wraps the centralized connection factory with Streamlit's caching
so the read-only connection is reused across reruns.
"""

from __future__ import annotations

import streamlit as st

from src.database import get_read_conn


@st.cache_resource
def get_conn():
    """Get a cached read-only DuckDB connection."""
    return get_read_conn()


def query(sql: str, params: list | None = None) -> list[dict]:
    """Execute SQL and return list of dicts."""
    conn = get_conn()
    result = conn.execute(sql, params or [])
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]
