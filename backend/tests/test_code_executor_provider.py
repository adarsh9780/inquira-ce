from pathlib import Path

import pytest

from app.services import code_executor
from app.services.execution_config import load_execution_runtime_config


@pytest.mark.asyncio
async def test_execute_code_uses_local_subprocess_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("INQUIRA_EXECUTION_PROVIDER", "local_subprocess")
    load_execution_runtime_config.cache_clear()

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
            "error": None,
            "result": 1,
            "result_type": "scalar",
        }

    def fail_safe_runner(script: str, timeout: int):
        raise AssertionError("safe runner should not be called")

    monkeypatch.setattr(code_executor, "_run_in_subprocess", fake_subprocess)
    monkeypatch.setattr(code_executor, "_run_in_safe_runner", fail_safe_runner)

    result = await code_executor.execute_code(
        code="result = 1",
        timeout=7,
        working_dir=str(tmp_path),
    )

    assert captured["called"] is True
    assert result["success"] is True
    assert result["stdout"] == "ok"


@pytest.mark.asyncio
async def test_execute_code_uses_safe_runner_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("INQUIRA_EXECUTION_PROVIDER", "local_safe_runner")
    load_execution_runtime_config.cache_clear()

    captured = {"called": False}

    def fake_safe_runner(script: str, timeout: int):
        captured["called"] = True
        assert "result = 2" in script
        assert timeout == 11
        return {
            "success": True,
            "stdout": "",
            "stderr": "",
            "error": None,
            "result": 2,
            "result_type": "scalar",
        }

    def fail_subprocess(script_path: str, timeout: int, working_dir: str):
        raise AssertionError("subprocess runner should not be called")

    monkeypatch.setattr(code_executor, "_run_in_safe_runner", fake_safe_runner)
    monkeypatch.setattr(code_executor, "_run_in_subprocess", fail_subprocess)

    result = await code_executor.execute_code(
        code="result = 2",
        timeout=11,
        working_dir=str(tmp_path),
    )

    assert captured["called"] is True
    assert result["success"] is True
    assert result["result"] == 2


@pytest.mark.asyncio
async def test_execute_code_reads_provider_from_toml(monkeypatch, tmp_path):
    cfg = tmp_path / "inquira.toml"
    cfg.write_text(
        """
[execution]
provider = "local_subprocess"
""".strip()
    )
    monkeypatch.delenv("INQUIRA_EXECUTION_PROVIDER", raising=False)
    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))
    load_execution_runtime_config.cache_clear()

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
    def unexpected_safe_runner(script: str, timeout: int):
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error": "unexpected",
            "result": None,
            "result_type": None,
        }

    monkeypatch.setattr(code_executor, "_run_in_safe_runner", unexpected_safe_runner)

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
    load_execution_runtime_config.cache_clear()

    result = await code_executor.execute_code(
        code="result = 3",
        timeout=8,
        working_dir=str(tmp_path),
    )

    assert result["success"] is False
    assert "Unsupported execution provider" in (result["error"] or "")
