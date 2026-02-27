import json
from types import SimpleNamespace

from app.services import code_executor


def _policy_cfg():
    return SimpleNamespace(
        timeout_seconds=60,
        memory_limit_mb=512,
        max_output_kb=512,
        blocked_imports=[],
        blocked_builtins=[],
    )


def _config(runner_python_executable: str):
    return SimpleNamespace(
        runner_policy=_policy_cfg(),
        runner_project_path=None,
        runner_python_executable=runner_python_executable,
    )


def _ok_runner_result(result_value):
    payload = json.dumps(
        {
            "stdout": "runner-stdout",
            "stderr": "",
            "result": {"type": "scalar", "data": result_value},
        }
    )
    return SimpleNamespace(ok=True, stdout="__INQUIRA_RESULT__" + payload, stderr="", error=None)


def test_run_in_safe_runner_uses_new_engine_api_when_available(monkeypatch, tmp_path):
    venv_dir = tmp_path / "new-api-venv"
    (venv_dir / "bin").mkdir(parents=True)
    (venv_dir / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")

    monkeypatch.setattr(
        code_executor,
        "load_execution_runtime_config",
        lambda: _config(str(venv_dir / "bin" / "python")),
    )

    captured = {}

    class FakeRunnerPolicy:
        def __init__(self, **kwargs):
            captured["policy_kwargs"] = kwargs

    class FakeLocalEngine:
        def __init__(self, *, venv_dir, venv_manager="uv", packages=None):
            captured["engine_venv_dir"] = venv_dir
            captured["engine_venv_manager"] = venv_manager
            captured["engine_packages"] = packages

    def fake_run_code(*, code, engine, input_data=None, policy=None, policy_file=None):
        captured["run_code_kwargs"] = {
            "code": code,
            "engine_type": type(engine).__name__,
            "input_data": input_data,
            "policy_type": type(policy).__name__,
            "policy_file": policy_file,
        }
        return _ok_runner_result(7)

    fake_module = SimpleNamespace(
        RunnerPolicy=FakeRunnerPolicy,
        LocalEngine=FakeLocalEngine,
        run_code=fake_run_code,
    )
    monkeypatch.setitem(code_executor.sys.modules, "safe_py_runner", fake_module)

    result = code_executor._run_in_safe_runner(script="result = 7", timeout=12)

    assert result["success"] is True
    assert result["result"] == 7
    assert result["result_type"] == "scalar"
    assert captured["engine_venv_dir"] == str(venv_dir)
    assert captured["engine_venv_manager"] == "python"
    assert captured["run_code_kwargs"]["input_data"] == {}
    assert captured["run_code_kwargs"]["engine_type"] == "FakeLocalEngine"


def test_run_in_safe_runner_falls_back_to_legacy_python_executable_api(monkeypatch, tmp_path):
    venv_dir = tmp_path / "legacy-api-venv"
    (venv_dir / "bin").mkdir(parents=True)
    (venv_dir / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")

    monkeypatch.setattr(
        code_executor,
        "load_execution_runtime_config",
        lambda: _config(str(venv_dir / "bin" / "python")),
    )

    captured = {}

    class FakeRunnerPolicy:
        def __init__(self, **kwargs):
            captured["policy_kwargs"] = kwargs

    def fake_run_code(*, code, input_data=None, policy=None, python_executable=None):
        captured["python_executable"] = python_executable
        return _ok_runner_result(11)

    fake_module = SimpleNamespace(
        RunnerPolicy=FakeRunnerPolicy,
        run_code=fake_run_code,
    )
    monkeypatch.setitem(code_executor.sys.modules, "safe_py_runner", fake_module)

    result = code_executor._run_in_safe_runner(script="result = 11", timeout=10)

    assert result["success"] is True
    assert result["result"] == 11
    assert captured["python_executable"] == str(venv_dir / "bin" / "python")


def test_run_in_safe_runner_errors_when_engine_api_needs_runner_venv_path(monkeypatch):
    monkeypatch.setattr(
        code_executor,
        "load_execution_runtime_config",
        lambda: _config("/usr/bin/python3"),
    )

    class FakeRunnerPolicy:
        def __init__(self, **kwargs):
            _ = kwargs

    class FakeLocalEngine:
        def __init__(self, *, venv_dir, venv_manager="uv", packages=None):
            _ = (venv_dir, venv_manager, packages)

    def fake_run_code(*, code, engine, input_data=None, policy=None, policy_file=None):
        _ = (code, engine, input_data, policy, policy_file)
        return _ok_runner_result(1)

    fake_module = SimpleNamespace(
        RunnerPolicy=FakeRunnerPolicy,
        LocalEngine=FakeLocalEngine,
        run_code=fake_run_code,
    )
    monkeypatch.setitem(code_executor.sys.modules, "safe_py_runner", fake_module)

    result = code_executor._run_in_safe_runner(script="result = 1", timeout=5)

    assert result["success"] is False
    assert "INQUIRA_RUNNER_PYTHON" in (result["error"] or "")
