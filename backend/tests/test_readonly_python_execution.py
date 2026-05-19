import asyncio
import time

import duckdb
import pytest

from app.services.readonly_python_execution import (
    ReadOnlyExecutionBlockedError,
    ReadOnlyPythonExecutionService,
    assert_readonly_python,
    _normalize_filesystem_path,
)
from app.v1.services.chat_service import ChatService


def _workspace_db(tmp_path):
    db_path = tmp_path / "workspace.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE TABLE numbers AS SELECT 1 AS value UNION ALL SELECT 2")
    conn.close()
    return db_path


@pytest.mark.asyncio
async def test_readonly_python_worker_executes_readonly_query(tmp_path):
    db_path = _workspace_db(tmp_path)
    service = ReadOnlyPythonExecutionService()

    result = await service.execute(
        workspace_id="workspace-1",
        workspace_duckdb_path=str(db_path),
        code='df = conn.execute("SELECT * FROM numbers ORDER BY value").fetchdf()\nexport_dataframe(df, "numbers")',
        timeout=10,
        run_id="run-1",
    )

    assert result["success"] is True
    assert result["artifacts"][0]["kind"] == "dataframe"
    assert result["artifacts"][0]["row_count"] == 2


def test_readonly_python_guard_rejects_literal_write_sql():
    with pytest.raises(ReadOnlyExecutionBlockedError):
        assert_readonly_python('conn.execute("CREATE TABLE x AS SELECT 1")')


def test_readonly_python_guard_rejects_writable_duckdb_connection(tmp_path):
    db_path = tmp_path / "workspace.duckdb"
    with pytest.raises(ReadOnlyExecutionBlockedError):
        assert_readonly_python(f'import duckdb\nduckdb.connect({str(db_path)!r}, read_only=False)')


def test_readonly_path_normalization_handles_equivalent_windows_shapes(monkeypatch):
    monkeypatch.setattr("os.path.abspath", lambda value: f"C:\\Workspace\\{str(value).replace('/', '\\')}")
    monkeypatch.setattr("os.path.normcase", lambda value: str(value).replace("/", "\\").lower())

    assert _normalize_filesystem_path("Data/workspace.duckdb") == (
        _normalize_filesystem_path("Data\\workspace.duckdb")
    )


@pytest.mark.asyncio
async def test_readonly_python_runtime_rejects_dynamic_write_sql(tmp_path):
    db_path = _workspace_db(tmp_path)
    service = ReadOnlyPythonExecutionService()

    result = await service.execute(
        workspace_id="workspace-1",
        workspace_duckdb_path=str(db_path),
        code='sql = "CREATE TABLE x AS SELECT 1"\nconn.execute(sql)',
        timeout=10,
        run_id="run-2",
    )

    assert result["success"] is False
    assert "Blocked write-like SQL statement: CREATE" in result["error"]


@pytest.mark.asyncio
async def test_readonly_python_worker_allows_parallel_runs_across_conversations(tmp_path):
    db_path = _workspace_db(tmp_path)
    service = ReadOnlyPythonExecutionService(max_parallel_per_workspace=2)
    code = 'import time\ntime.sleep(0.8)\nresult = conn.execute("SELECT COUNT(*) FROM numbers").fetchone()[0]\nexport_scalar(result, "count_" + _RUN_ID)'

    started = time.perf_counter()
    first, second = await asyncio.gather(
        service.execute(
            workspace_id="workspace-1",
            workspace_duckdb_path=str(db_path),
            code=code,
            timeout=10,
            run_id="run-a",
        ),
        service.execute(
            workspace_id="workspace-1",
            workspace_duckdb_path=str(db_path),
            code=code,
            timeout=10,
            run_id="run-b",
        ),
    )

    assert first["success"] is True
    assert second["success"] is True
    assert time.perf_counter() - started < 1.5


@pytest.mark.asyncio
async def test_conversation_run_guard_blocks_duplicate_conversation():
    await ChatService._claim_conversation_run("conversation-1")
    try:
        with pytest.raises(Exception) as exc:
            await ChatService._claim_conversation_run("conversation-1")
        assert getattr(exc.value, "status_code", None) == 409
    finally:
        await ChatService._release_conversation_run("conversation-1")
