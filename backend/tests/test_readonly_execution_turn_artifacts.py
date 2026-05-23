from __future__ import annotations

import duckdb
import pytest

from app.services.output_capture import build_run_wrapped_code
from app.services.readonly_python_execution import ReadOnlyPythonExecutionService


@pytest.mark.asyncio
async def test_readonly_execution_exports_dataframe_directly_to_turn_folder(tmp_path) -> None:
    workspace_db = tmp_path / "workspace.duckdb"
    conn = duckdb.connect(str(workspace_db))
    conn.execute("CREATE TABLE source AS SELECT 1 AS amount")
    conn.close()

    artifact_dir = tmp_path / "conversations" / "conversation-1" / "turn-1"
    code = """
import pandas as pd
result_df = pd.DataFrame({"amount": [10, 20]})
export_dataframe(result_df, "Sales Summary")
"""
    wrapped = build_run_wrapped_code(
        code,
        "run-1",
        [],
        conversation_id="conversation-1",
        turn_id="turn-1",
        artifact_dir=str(artifact_dir),
    )

    result = await ReadOnlyPythonExecutionService().execute(
        workspace_id="workspace-1",
        workspace_duckdb_path=str(workspace_db),
        code=wrapped,
        timeout=20,
        run_id="run-1",
    )

    assert result["success"] is True
    artifacts = result["artifacts"]
    named_artifact = next(item for item in artifacts if item["logical_name"] == "Sales Summary")
    assert named_artifact["artifact_id"].startswith("Sales_Summary__")
    assert named_artifact["storage_path"].startswith(str(artifact_dir))
    assert named_artifact["storage_path"].endswith(".parquet")
    assert duckdb.connect().execute("SELECT SUM(amount) FROM read_parquet(?)", [named_artifact["storage_path"]]).fetchone() == (30,)
    assert not (tmp_path / "scratchpad" / "artifacts.duckdb").exists()
