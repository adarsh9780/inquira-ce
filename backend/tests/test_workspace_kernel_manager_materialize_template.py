from __future__ import annotations

import json

import duckdb

from app.services import workspace_kernel_manager as manager


def test_materialize_exports_template_materializes_dataframe_parquet(tmp_path) -> None:
    scratchpad_path = tmp_path / "scratchpad.duckdb"
    parquet_path = tmp_path / "exports" / "df-1.parquet"
    scratchpad_conn = duckdb.connect(str(scratchpad_path))
    try:
        scratchpad_conn.execute("CREATE TABLE result_df AS SELECT 1 AS value")
        scratchpad_conn.execute(
            """
            CREATE TABLE artifact_manifest (
              artifact_id VARCHAR PRIMARY KEY,
              run_id VARCHAR NOT NULL,
              workspace_id VARCHAR NOT NULL,
              logical_name VARCHAR NOT NULL,
              kind VARCHAR NOT NULL,
              table_name VARCHAR,
              payload_json TEXT,
              schema_json TEXT,
              row_count BIGINT,
              created_at TIMESTAMP NOT NULL,
              expires_at TIMESTAMP NOT NULL,
              status VARCHAR NOT NULL,
              error TEXT
            )
            """
        )

        specs = [
            {
                "artifact_id": "df-1",
                "kind": "dataframe",
                "storage_path": str(parquet_path),
                "table_name": "result_df",
            }
        ]
        rendered = manager._MATERIALIZE_EXPORTS_TEMPLATE.replace(
            manager._MATERIALIZE_EXPORTS_SPECS_SENTINEL,
            json.dumps(json.dumps(specs, ensure_ascii=True, default=str)),
        )

        namespace = {"scratchpad_conn": scratchpad_conn}
        exec(rendered, namespace)

        assert parquet_path.is_file()
        assert scratchpad_conn.execute("SELECT * FROM read_parquet(?)", [str(parquet_path)]).fetchall() == [(1,)]
        assert namespace["_inquira_materialized"] == [
            {"artifact_id": "df-1", "size_bytes": parquet_path.stat().st_size}
        ]
        assert "{{_escaped_table}}" not in rendered
        assert manager._MATERIALIZE_EXPORTS_SPECS_SENTINEL not in rendered
    finally:
        scratchpad_conn.close()


def test_materialize_exports_template_uses_safe_sentinel_replacement() -> None:
    rendered = manager._MATERIALIZE_EXPORTS_TEMPLATE.replace(
        manager._MATERIALIZE_EXPORTS_SPECS_SENTINEL,
        json.dumps("[]"),
    )

    compile(rendered, "<materialize_exports>", "exec")
    assert "{{_escaped_table}}" not in rendered
    assert "{_escaped_table}" in rendered
    assert "COPY (SELECT * FROM" in rendered
    assert "artifact_manifest" in rendered
    assert manager._MATERIALIZE_EXPORTS_SPECS_SENTINEL not in rendered
