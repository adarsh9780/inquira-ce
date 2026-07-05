import asyncio
import duckdb
import pytest

from app.services.output_capture import build_run_wrapped_code
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
    artifact_dir = tmp_path / "turn-1"
    code = build_run_wrapped_code(
        'df = conn.execute("SELECT * FROM numbers ORDER BY value").fetchdf()\nexport_dataframe(df, "numbers")',
        "run-1",
        [],
        conversation_id="conversation-1",
        turn_id="turn-1",
        artifact_dir=str(artifact_dir),
    )

    result = await service.execute(
        workspace_id="workspace-1",
        workspace_duckdb_path=str(db_path),
        code=code,
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
async def test_readonly_python_worker_allows_parallel_runs_across_conversations(monkeypatch, tmp_path):
    db_path = _workspace_db(tmp_path)
    service = ReadOnlyPythonExecutionService(max_parallel_per_workspace=2)
    active_count = 0
    max_active = 0
    entered_count = 0
    both_entered = asyncio.Event()
    release_runs = asyncio.Event()

    async def fake_execute_process(
        self,
        *,
        workspace_id,
        workspace_duckdb_path,
        code,
        timeout,
        run_id,
    ):
        _ = (self, workspace_id, workspace_duckdb_path, code, timeout)
        nonlocal active_count, max_active, entered_count
        active_count += 1
        entered_count += 1
        max_active = max(max_active, active_count)
        if entered_count == 2:
            both_entered.set()
        try:
            await asyncio.wait_for(release_runs.wait(), timeout=2)
        finally:
            active_count -= 1
        return {
            "success": True,
            "stdout": "",
            "stderr": "",
            "error": None,
            "result": None,
            "result_type": None,
            "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
            "artifacts": [],
            "run_id": run_id,
        }

    monkeypatch.setattr(ReadOnlyPythonExecutionService, "_execute_process", fake_execute_process)
    tasks = [
        asyncio.create_task(
            service.execute(
                workspace_id="workspace-1",
                workspace_duckdb_path=str(db_path),
                code="result = 1",
                timeout=10,
                run_id="run-a",
            )
        ),
        asyncio.create_task(
            service.execute(
                workspace_id="workspace-1",
                workspace_duckdb_path=str(db_path),
                code="result = 1",
                timeout=10,
                run_id="run-b",
            )
        ),
    ]
    try:
        await asyncio.wait_for(both_entered.wait(), timeout=2)
    finally:
        release_runs.set()
        if not both_entered.is_set():
            await asyncio.gather(*tasks, return_exceptions=True)
    first, second = await asyncio.gather(*tasks)

    assert first["success"] is True
    assert second["success"] is True
    assert {first["run_id"], second["run_id"]} == {"run-a", "run-b"}
    assert max_active == 2


@pytest.mark.asyncio
async def test_conversation_run_guard_blocks_duplicate_conversation():
    await ChatService._claim_conversation_run("conversation-1")
    try:
        with pytest.raises(Exception) as exc:
            await ChatService._claim_conversation_run("conversation-1")
        assert getattr(exc.value, "status_code", None) == 409
    finally:
        await ChatService._release_conversation_run("conversation-1")
