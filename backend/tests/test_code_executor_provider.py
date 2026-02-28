from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import code_executor
from app.services.execution_config import load_execution_runtime_config


@pytest.fixture(autouse=True)
def _clear_execution_config_cache():
    load_execution_runtime_config.cache_clear()
    yield
    load_execution_runtime_config.cache_clear()


@pytest.mark.asyncio
async def test_execute_code_uses_local_subprocess_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("INQUIRA_EXECUTION_PROVIDER", "local_subprocess")

    captured = {"called": False}

    def fake_subprocess(script_path: str, timeout: int, working_dir: str):
        captured["called"] = True
        assert Path(script_path).exists()
        assert timeout == 7
        assert working_dir == str(tmp_path)
        return {
            "success": True,
            "stdout": "ok",
            "stderr": "",
            "has_stdout": True,
            "has_stderr": False,
            "error": None,
            "result": 1,
            "result_type": "scalar",
        }

    monkeypatch.setattr(code_executor, "_run_in_subprocess", fake_subprocess)

    result = await code_executor.execute_code(
        code="result = 1",
        timeout=7,
        working_dir=str(tmp_path),
    )

    assert captured["called"] is True
    assert result["success"] is True
    assert result["stdout"] == "ok"
    assert result["has_stdout"] is True
    assert result["has_stderr"] is False


@pytest.mark.asyncio
async def test_execute_code_uses_jupyter_provider(monkeypatch):
    monkeypatch.setenv("INQUIRA_EXECUTION_PROVIDER", "local_jupyter")

    class FakeManager:
        async def execute(
            self,
            *,
            workspace_id: str,
            workspace_duckdb_path: str,
            code: str,
            timeout: int,
            config,
        ):
            assert workspace_id == "ws-1"
            assert workspace_duckdb_path == "/tmp/ws/workspace.duckdb"
            assert "result = 2" in code
            assert timeout == 11
            return {
                "success": True,
                "stdout": "",
                "stderr": "",
                "error": None,
                "result": 2,
                "result_type": "scalar",
            }

    async def fake_get_manager():
        return FakeManager()

    monkeypatch.setattr(code_executor, "get_workspace_kernel_manager", fake_get_manager)

    result = await code_executor.execute_code(
        code="result = 2",
        timeout=11,
        workspace_id="ws-1",
        workspace_duckdb_path="/tmp/ws/workspace.duckdb",
    )

    assert result["success"] is True
    assert result["result"] == 2


@pytest.mark.asyncio
async def test_execute_code_reads_provider_from_toml(monkeypatch, tmp_path):
    cfg = tmp_path / "inquira.toml"
    cfg.write_text(
        """
[execution]
provider = "local_subprocess"
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.delenv("INQUIRA_EXECUTION_PROVIDER", raising=False)
    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))

    def fake_subprocess(script_path: str, timeout: int, working_dir: str):
        return {
            "success": True,
            "stdout": "from_toml",
            "stderr": "",
            "error": None,
            "result": None,
            "result_type": None,
        }

    monkeypatch.setattr(code_executor, "_run_in_subprocess", fake_subprocess)

    result = await code_executor.execute_code(
        code="print('x')",
        timeout=5,
        working_dir=str(tmp_path),
    )

    assert result["success"] is True
    assert result["stdout"] == "from_toml"


@pytest.mark.asyncio
async def test_execute_code_rejects_unknown_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("INQUIRA_EXECUTION_PROVIDER", "piston")

    result = await code_executor.execute_code(
        code="result = 3",
        timeout=8,
        working_dir=str(tmp_path),
    )

    assert result["success"] is False
    assert "Unsupported execution provider" in (result["error"] or "")
    assert result["has_stderr"] is True


@pytest.mark.asyncio
async def test_execute_code_default_workdir_avoids_legacy_workspace_root(monkeypatch, tmp_path):
    monkeypatch.setenv("INQUIRA_EXECUTION_PROVIDER", "local_subprocess")
    expected_dir = tmp_path / "runtime" / "exec_tmp"

    monkeypatch.setattr(
        code_executor.os.path,
        "expanduser",
        lambda path: str(expected_dir) if path == "~/.inquira/runtime/exec_tmp" else path,
    )

    def fake_subprocess(script_path: str, timeout: int, working_dir: str):
        assert working_dir == str(expected_dir)
        assert "~/.inquira/workspaces" not in working_dir
        return {
            "success": True,
            "stdout": "ok",
            "stderr": "",
            "error": None,
            "result": None,
            "result_type": None,
        }

    monkeypatch.setattr(code_executor, "_run_in_subprocess", fake_subprocess)

    result = await code_executor.execute_code(code="x = 1", timeout=3)
    assert result["success"] is True


@pytest.mark.asyncio
async def test_execute_code_requires_workspace_metadata_for_jupyter(monkeypatch):
    monkeypatch.setenv("INQUIRA_EXECUTION_PROVIDER", "local_jupyter")

    result = await code_executor.execute_code(code="x = 1", timeout=3)
    assert result["success"] is False
    assert "workspace_id" in (result["error"] or "")


@pytest.mark.asyncio
async def test_get_workspace_kernel_manager_uses_config_idle_minutes(monkeypatch):
    fake_config = SimpleNamespace(kernel_idle_minutes=99)
    monkeypatch.setattr(code_executor, "load_execution_runtime_config", lambda: fake_config)

    await code_executor.shutdown_workspace_kernel_manager()
    manager = await code_executor.get_workspace_kernel_manager()
    assert manager is not None
