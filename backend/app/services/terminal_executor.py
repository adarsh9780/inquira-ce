"""Workspace-scoped terminal command execution helpers."""

from __future__ import annotations

import asyncio
import os
import platform
import shutil
from pathlib import Path
from typing import Any


def detect_shell_command() -> tuple[str, list[str]]:
    """Return best-effort default shell executable + base args for current OS."""
    if os.name == "nt":
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell:
            return powershell, ["-NoLogo", "-NoProfile", "-Command"]
        cmd = shutil.which("cmd")
        if cmd:
            return cmd, ["/C"]
        return "cmd", ["/C"]

    shell = os.environ.get("SHELL", "").strip()
    if shell:
        return shell, ["-lc"]
    bash = shutil.which("bash")
    if bash:
        return bash, ["-lc"]
    sh = shutil.which("sh")
    if sh:
        return sh, ["-lc"]
    return "/bin/sh", ["-lc"]


def normalize_workspace_cwd(workspace_dir: str, cwd: str | None) -> str:
    """Resolve requested cwd to an absolute path, defaulting to workspace dir."""
    base = Path(workspace_dir).resolve()
    if not cwd:
        return str(base)
    requested = Path(cwd).expanduser()
    resolved = requested.resolve() if requested.is_absolute() else (base / requested).resolve()
    return str(resolved)


async def run_workspace_terminal_command(
    *,
    command: str,
    workspace_dir: str,
    cwd: str | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    """Execute one terminal command in workspace context and return streams."""
    trimmed = (command or "").strip()
    if not trimmed:
        return {
            "stdout": "",
            "stderr": "No command provided.",
            "exit_code": 1,
            "cwd": normalize_workspace_cwd(workspace_dir, cwd),
            "shell": "",
            "platform": platform.system(),
            "timed_out": False,
        }

    exec_cwd = normalize_workspace_cwd(workspace_dir, cwd)
    shell_bin, shell_args = detect_shell_command()
    process = await asyncio.create_subprocess_exec(
        shell_bin,
        *shell_args,
        trimmed,
        cwd=exec_cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(),
            timeout=max(1, int(timeout)),
        )
        timed_out = False
    except asyncio.TimeoutError:
        process.kill()
        stdout_bytes, stderr_bytes = await process.communicate()
        timed_out = True

    stdout = (stdout_bytes or b"").decode("utf-8", errors="replace")
    stderr = (stderr_bytes or b"").decode("utf-8", errors="replace")

    if timed_out:
        timeout_message = f"Command timed out after {max(1, int(timeout))} seconds."
        stderr = f"{stderr}\n{timeout_message}".strip()

    return {
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": process.returncode if process.returncode is not None else 1,
        "cwd": exec_cwd,
        "shell": shell_bin,
        "platform": platform.system(),
        "timed_out": timed_out,
    }
