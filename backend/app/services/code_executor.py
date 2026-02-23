"""
code_executor.py — Server-Side Python Code Execution

Runs AI-generated (or user-written) Python code in a subprocess with:
- Timeout protection
- Working directory isolation
- stdout/stderr capture
- Result serialization (DataFrames, Plotly figures, scalars)
"""

import json
import os
import subprocess
import tempfile
import sys
import asyncio
from pathlib import Path
from typing import Any, Optional

from app.core.logger import logprint
from app.services.execution_config import load_execution_runtime_config


# Wrapper script injected around user code to capture the last expression result.
_WRAPPER_TEMPLATE = '''
import sys, json, io

# Redirect stdout
_captured_stdout = io.StringIO()
_captured_stderr = io.StringIO()
_old_stdout = sys.stdout
_old_stderr = sys.stderr
sys.stdout = _captured_stdout
sys.stderr = _captured_stderr

_result = None
_result_type = None

try:
{indented_code}

    # Try to capture the last expression
    import builtins as _bi
    _last_val = _bi.__dict__.get("_")
    if _last_val is not None:
        _result = _last_val
except Exception as _e:
    _captured_stderr.write(str(_e) + "\\n")
    import traceback
    traceback.print_exc(file=_captured_stderr)

# Serialize result
sys.stdout = _old_stdout
sys.stderr = _old_stderr

def _serialize(obj):
    """Best-effort serialization of common data-science objects."""
    try:
        import pandas as pd
        if isinstance(obj, pd.DataFrame):
            return {{"type": "DataFrame", "data": json.loads(obj.to_json(orient="split", date_format="iso"))}}
    except ImportError:
        pass
    try:
        import plotly.graph_objects as go
        if isinstance(obj, go.Figure):
            return {{"type": "Figure", "data": json.loads(obj.to_json())}}
    except ImportError:
        pass
    if obj is not None:
        try:
            json.dumps(obj)
            return {{"type": "scalar", "data": obj}}
        except (TypeError, ValueError):
            return {{"type": "scalar", "data": repr(obj)}}
    return None

_out = {{
    "stdout": _captured_stdout.getvalue(),
    "stderr": _captured_stderr.getvalue(),
    "result": _serialize(_result),
}}
print("__INQUIRA_RESULT__" + json.dumps(_out))
'''


async def execute_code(
    code: str,
    timeout: int = 60,
    working_dir: Optional[str] = None,
) -> dict[str, Any]:
    """
    Execute Python code in a subprocess.

    Returns:
        {
            "success": bool,
            "stdout": str,
            "stderr": str,
            "error": str | None,
            "result": Any | None,
            "result_type": str | None,
        }
    """
    if not code or not code.strip():
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error": "No code provided",
            "result": None,
            "result_type": None,
        }

    # Indent the user code by 4 spaces to fit inside the try block
    indented = "\n".join("    " + line for line in code.splitlines())
    wrapper = _WRAPPER_TEMPLATE.format(indented_code=indented)

    # Determine working directory
    if working_dir is None:
        working_dir = os.path.expanduser("~/.inquira/workspaces")
    Path(working_dir).mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir=working_dir
    ) as f:
        f.write(wrapper)
        f.flush()
        script_path = f.name

    try:
        config = load_execution_runtime_config()
        provider = config.provider.strip().lower()

        if provider == "local_subprocess":
            return await asyncio.to_thread(
                _run_in_subprocess,
                script_path=script_path,
                timeout=timeout,
                working_dir=working_dir,
            )

        if provider == "local_safe_runner":
            return await asyncio.to_thread(
                _run_in_safe_runner,
                script=wrapper,
                timeout=timeout,
            )

        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error": (
                f"Unsupported execution provider '{config.provider}'. "
                "Supported values: local_subprocess, local_safe_runner."
            ),
            "result": None,
            "result_type": None,
        }

    except subprocess.TimeoutExpired:
        logprint("Code execution timed out", level="warning")
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error": f"Execution timed out after {timeout} seconds.",
            "result": None,
            "result_type": None,
        }
    except Exception as e:
        logprint(f"Code execution error: {e}", level="error")
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error": str(e),
            "result": None,
            "result_type": None,
        }
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass


def _parse_wrapped_output(stdout_raw: str, stderr_raw: str, returncode: int) -> dict[str, Any]:
    parsed_result = None
    result_type = None
    clean_stdout = stdout_raw

    if "__INQUIRA_RESULT__" in stdout_raw:
        parts = stdout_raw.split("__INQUIRA_RESULT__", 1)
        clean_stdout = parts[0]
        try:
            payload = json.loads(parts[1].strip())
            clean_stdout = payload.get("stdout", clean_stdout)
            stderr_raw = payload.get("stderr", stderr_raw) or stderr_raw
            if payload.get("result"):
                result_type = payload["result"].get("type")
                parsed_result = payload["result"].get("data")
        except (json.JSONDecodeError, IndexError):
            pass

    success = returncode == 0 and not stderr_raw.strip()
    clean_stderr = stderr_raw.strip()
    return {
        "success": success,
        "stdout": clean_stdout.strip(),
        "stderr": clean_stderr,
        "error": clean_stderr if not success else None,
        "result": parsed_result,
        "result_type": result_type,
    }


def _run_in_subprocess(script_path: str, timeout: int, working_dir: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=working_dir,
        stdin=subprocess.PIPE,
    )
    return _parse_wrapped_output(
        stdout_raw=result.stdout,
        stderr_raw=result.stderr,
        returncode=result.returncode,
    )


def _run_in_safe_runner(script: str, timeout: int) -> dict[str, Any]:
    config = load_execution_runtime_config()
    policy_cfg = config.runner_policy

    if config.runner_project_path:
        local_src = Path(config.runner_project_path).expanduser().resolve() / "src"
        if local_src.exists():
            src_path = str(local_src)
            if src_path not in sys.path:
                sys.path.insert(0, src_path)

    try:
        from safe_py_runner import RunnerPolicy, run_code
    except Exception as e:
        install_error = _install_safe_py_runner_from_config(config)
        if install_error:
            msg = (
                "Execution provider 'local_safe_runner' is enabled but safe_py_runner "
                f"could not be imported: {e}. Install attempt failed: {install_error}"
            )
            return {
                "success": False,
                "stdout": "",
                "stderr": msg,
                "error": msg,
                "result": None,
                "result_type": None,
            }

        try:
            from safe_py_runner import RunnerPolicy, run_code
        except Exception as import_after_install:
            msg = (
                "Execution provider 'local_safe_runner' is enabled but safe_py_runner "
                "could not be imported after install attempt: "
                f"{import_after_install}"
            )
            return {
                "success": False,
                "stdout": "",
                "stderr": msg,
                "error": msg,
                "result": None,
                "result_type": None,
            }

    effective_timeout = max(1, min(timeout, policy_cfg.timeout_seconds))
    policy = RunnerPolicy(
        timeout_seconds=effective_timeout,
        memory_limit_mb=max(64, int(policy_cfg.memory_limit_mb)),
        max_output_kb=max(32, int(policy_cfg.max_output_kb)),
        blocked_imports=policy_cfg.blocked_imports,
        blocked_builtins=policy_cfg.blocked_builtins,
    )

    runner_result = run_code(
        code=script,
        input_data={},
        policy=policy,
        python_executable=config.runner_python_executable,
    )

    if not runner_result.ok:
        msg = runner_result.error or runner_result.stderr or "Execution failed"
        return {
            "success": False,
            "stdout": runner_result.stdout.strip(),
            "stderr": runner_result.stderr.strip(),
            "error": msg,
            "result": None,
            "result_type": None,
        }

    return _parse_wrapped_output(
        stdout_raw=runner_result.stdout,
        stderr_raw=runner_result.stderr,
        returncode=0,
    )


def _build_safe_py_runner_install_targets(config) -> list[list[str]]:
    source = (config.safe_py_runner_source or "auto").strip().lower()
    local_path = config.safe_py_runner_local_path
    pypi_spec = config.safe_py_runner_pypi or "safe-py-runner"
    github_spec = (
        config.safe_py_runner_github
        or "git+https://github.com/adarsh9780/safe-py-runner.git"
    )

    if source == "pypi":
        return [[pypi_spec]]
    if source == "github":
        return [[github_spec]]
    if source == "local":
        if local_path and Path(local_path).exists():
            return [["-e", local_path]]
        return []

    targets: list[list[str]] = [[pypi_spec], [github_spec]]
    if local_path and Path(local_path).exists():
        targets.append(["-e", local_path])
    return targets


def _install_safe_py_runner_from_config(config) -> str | None:
    targets = _build_safe_py_runner_install_targets(config)
    if not targets:
        return "no valid safe-py-runner install source was configured"

    runner_python = config.runner_python_executable
    python_bin = runner_python or sys.executable
    errors: list[str] = []

    for target_args in targets:
        uv_cmd = ["uv", "pip", "install"]
        if runner_python:
            uv_cmd.extend(["--python", runner_python])
        uv_cmd.extend(target_args)
        try:
            uv_proc = subprocess.run(uv_cmd, capture_output=True, text=True)
            if uv_proc.returncode == 0:
                return None
            errors.append((uv_proc.stderr or uv_proc.stdout or "").strip())
        except Exception as e:
            errors.append(str(e))

        pip_cmd = [python_bin, "-m", "pip", "install", *target_args]
        try:
            pip_proc = subprocess.run(pip_cmd, capture_output=True, text=True)
            if pip_proc.returncode == 0:
                return None
            errors.append((pip_proc.stderr or pip_proc.stdout or "").strip())
        except Exception as e:
            errors.append(str(e))

    compact = [e for e in errors if e]
    return compact[-1] if compact else "unknown install failure"
