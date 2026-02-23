from types import SimpleNamespace

from app.services import code_executor


def _cfg(**overrides):
    base = {
        "safe_py_runner_source": "auto",
        "safe_py_runner_pypi": "safe-py-runner",
        "safe_py_runner_github": "git+https://github.com/adarsh9780/safe-py-runner.git",
        "safe_py_runner_local_path": None,
        "runner_python_executable": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_build_safe_py_runner_install_targets_prefers_configured_github_source():
    config = _cfg(safe_py_runner_source="github")
    targets = code_executor._build_safe_py_runner_install_targets(config)
    assert targets == [["git+https://github.com/adarsh9780/safe-py-runner.git"]]


def test_install_safe_py_runner_falls_back_to_pip_when_uv_fails(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(cmd, capture_output, text):
        calls.append(cmd)
        if cmd[:3] == ["uv", "pip", "install"]:
            return SimpleNamespace(returncode=1, stdout="", stderr="uv failed")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(code_executor.subprocess, "run", fake_run)

    config = _cfg(
        safe_py_runner_source="github",
        runner_python_executable="/tmp/runner-python",
    )
    err = code_executor._install_safe_py_runner_from_config(config)

    assert err is None
    assert calls[0] == [
        "uv",
        "pip",
        "install",
        "--python",
        "/tmp/runner-python",
        "git+https://github.com/adarsh9780/safe-py-runner.git",
    ]
    assert calls[1] == [
        "/tmp/runner-python",
        "-m",
        "pip",
        "install",
        "git+https://github.com/adarsh9780/safe-py-runner.git",
    ]
