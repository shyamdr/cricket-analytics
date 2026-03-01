"""Unit tests for the centralized database module.

Tests connection factory, query helper, and append_to_bronze dedup logic
using an in-memory DuckDB instance (no disk, no real data needed).
"""

from __future__ import annotations

import duckdb
import pyarrow as pa
import pytest

from src.database import append_to_bronze


@pytest.mark.unit
class TestAppendToBronze:
    """Test the idempotent append logic used by all bronze loaders."""

    @pytest.fixture()
    def mem_conn(self) -> duckdb.DuckDBPyConnection:
        """In-memory DuckDB connection for isolated tests."""
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE SCHEMA IF NOT EXISTS bronze")
        yield conn
        conn.close()

    def _make_table(self, ids: list[str], values: list[int]) -> pa.Table:
        return pa.table({"match_id": ids, "value": values})

    def test_creates_table_on_first_run(self, mem_conn) -> None:
        data = self._make_table(["m1", "m2"], [10, 20])
        result = append_to_bronze(mem_conn, "bronze.test_table", data, "match_id")
        assert result == 2
        rows = mem_conn.execute("SELECT COUNT(*) FROM bronze.test_table").fetchone()
        assert rows[0] == 2

    def test_skips_duplicates_on_second_run(self, mem_conn) -> None:
        data = self._make_table(["m1", "m2"], [10, 20])
        append_to_bronze(mem_conn, "bronze.test_table", data, "match_id")

        # Same data again — should insert 0
        result = append_to_bronze(mem_conn, "bronze.test_table", data, "match_id")
        assert result == 0
        rows = mem_conn.execute("SELECT COUNT(*) FROM bronze.test_table").fetchone()
        assert rows[0] == 2

    def test_appends_only_new_rows(self, mem_conn) -> None:
        data1 = self._make_table(["m1", "m2"], [10, 20])
        append_to_bronze(mem_conn, "bronze.test_table", data1, "match_id")

        # Mix of existing and new
        data2 = self._make_table(["m2", "m3", "m4"], [20, 30, 40])
        result = append_to_bronze(mem_conn, "bronze.test_table", data2, "match_id")
        assert result == 2  # only m3 and m4 are new
        rows = mem_conn.execute("SELECT COUNT(*) FROM bronze.test_table").fetchone()
        assert rows[0] == 4

    def test_empty_input_returns_zero(self, mem_conn) -> None:
        data = pa.table(
            {"match_id": pa.array([], type=pa.string()), "value": pa.array([], type=pa.int64())}
        )
        result = append_to_bronze(mem_conn, "bronze.test_table", data, "match_id")
        assert result == 0

    def test_preserves_data_types(self, mem_conn) -> None:
        data = pa.table(
            {
                "match_id": ["m1"],
                "name": ["test"],
                "score": [42],
                "is_active": [True],
            }
        )
        append_to_bronze(mem_conn, "bronze.typed_table", data, "match_id")
        row = mem_conn.execute("SELECT * FROM bronze.typed_table").fetchone()
        assert row == ("m1", "test", 42, True)

    def test_large_batch_dedup(self, mem_conn) -> None:
        """Verify dedup works correctly with larger datasets."""
        # Insert 500 rows
        ids1 = [f"m{i}" for i in range(500)]
        vals1 = list(range(500))
        data1 = self._make_table(ids1, vals1)
        append_to_bronze(mem_conn, "bronze.large_table", data1, "match_id")

        # Try inserting 300 rows: 200 overlap + 100 new
        ids2 = [f"m{i}" for i in range(300, 600)]
        vals2 = list(range(300, 600))
        data2 = self._make_table(ids2, vals2)
        result = append_to_bronze(mem_conn, "bronze.large_table", data2, "match_id")
        assert result == 100  # only m500-m599 are new
        rows = mem_conn.execute("SELECT COUNT(*) FROM bronze.large_table").fetchone()
        assert rows[0] == 600


@pytest.mark.unit
class TestGetConnections:
    """Test connection factory functions."""

    def test_get_read_conn_returns_connection(self) -> None:
        """Read connection should work if the DB file exists."""
        from src.config import settings

        if not settings.duckdb_path.exists():
            pytest.skip("DuckDB not found — run `make all` first")
        from src.database import get_read_conn

        conn = get_read_conn()
        result = conn.execute("SELECT 1").fetchone()
        assert result[0] == 1
        conn.close()

    def test_query_helper_returns_dicts(self) -> None:
        """The query() helper should return list of dicts."""
        from src.config import settings

        if not settings.duckdb_path.exists():
            pytest.skip("DuckDB not found — run `make all` first")
        from src.database import query

        result = query("SELECT 1 as val, 'hello' as msg")
        assert len(result) == 1
        assert result[0]["val"] == 1
        assert result[0]["msg"] == "hello"
