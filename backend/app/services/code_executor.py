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
from pathlib import Path
from typing import Any, Optional

from app.core.logger import logprint


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
        import sys
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir,
            stdin=subprocess.DEVNULL,
        )

        stdout_raw = result.stdout
        stderr_raw = result.stderr

        # Parse the structured result from our wrapper
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

        success = result.returncode == 0 and not stderr_raw.strip()

        return {
            "success": success,
            "stdout": clean_stdout.strip(),
            "stderr": stderr_raw.strip(),
            "error": stderr_raw.strip() if not success else None,
            "result": parsed_result,
            "result_type": result_type,
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
