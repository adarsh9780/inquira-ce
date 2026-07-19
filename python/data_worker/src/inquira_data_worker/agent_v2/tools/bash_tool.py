"""Restricted workspace command tool with streamed progress events.

The public tool is still named "bash" for prompt/API compatibility, but the
implementation avoids shell execution so the same commands work on Windows and
POSIX hosts.
"""

from __future__ import annotations

import asyncio
import fnmatch
import os
import re
import shlex
import shutil
from pathlib import Path
from typing import Any

from ..events import emit_agent_event
from ..runtime import load_agent_runtime_config
from . import new_tool_call_id


_BLOCKED_SYNTAX_RE = re.compile(r"(&&|\|\||\||;|>|<|`|\$\(|\r|\n)")


def _split_command(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except Exception:
        return command.split()


def _first_token(command: str) -> str:
    tokens = _split_command(command)
    if not tokens:
        return ""
    return str(tokens[0]).strip().lower()


def _validate_command(command: str) -> str | None:
    normalized = str(command or "").strip()
    if not normalized:
        return "No command provided."
    if _BLOCKED_SYNTAX_RE.search(normalized):
        return "Blocked shell syntax in command."
    runtime = load_agent_runtime_config()
    allowlist = {cmd.lower() for cmd in runtime.bash_allowed_commands}
    token = _first_token(normalized)
    if token not in allowlist:
        return f"Command '{token or '<empty>'}' is not allowed."
    return None


def _workspace_dir_from_data_path(data_path: str | None) -> tuple[Path | None, dict[str, Any] | None]:
    if not data_path:
        return None, {"error": "Missing workspace data path.", "stdout": "", "stderr": "Missing data path", "exit_code": 1}

    workspace_path = Path(data_path).expanduser()
    if not workspace_path.is_absolute():
        return None, {
            "error": "Workspace data path must be absolute.",
            "stdout": "",
            "stderr": "Invalid data path",
            "exit_code": 1,
        }
    return workspace_path.parent, None


def _within_workspace(workspace_dir: Path, path: Path) -> bool:
    workspace_abs = os.path.realpath(os.path.abspath(os.fspath(workspace_dir)))
    path_abs = os.path.realpath(os.path.abspath(os.fspath(path)))
    try:
        return os.path.commonpath([workspace_abs, path_abs]) == workspace_abs
    except ValueError:
        return False


def _resolve_workspace_path(workspace_dir: Path, raw: str | None = None) -> Path:
    value = str(raw or ".").strip() or "."
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = workspace_dir / candidate
    resolved = Path(os.path.realpath(os.path.abspath(os.fspath(candidate))))
    if not _within_workspace(workspace_dir, resolved):
        raise ValueError("Path must stay within the workspace directory.")
    return resolved


def _expand_path_args(workspace_dir: Path, args: list[str], *, default: str = ".") -> list[Path]:
    raw_args = args or [default]
    paths: list[Path] = []
    for raw in raw_args:
        if any(char in raw for char in "*?["):
            matches = sorted(workspace_dir.glob(raw))
            if matches:
                for match in matches:
                    resolved = Path(os.path.realpath(os.path.abspath(os.fspath(match))))
                    if not _within_workspace(workspace_dir, resolved):
                        raise ValueError("Path must stay within the workspace directory.")
                    paths.append(resolved)
                continue
        paths.append(_resolve_workspace_path(workspace_dir, raw))
    return paths


def _relative(path: Path, workspace_dir: Path) -> str:
    workspace_abs = os.path.realpath(os.path.abspath(os.fspath(workspace_dir)))
    path_abs = os.path.realpath(os.path.abspath(os.fspath(path)))
    try:
        value = os.path.relpath(path_abs, workspace_abs)
    except ValueError:
        return path.name
    normalized = Path(value).as_posix()
    return "." if normalized == "" else normalized


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    suffix = "\n[output truncated]\n"
    return text[: max(0, limit - len(suffix))] + suffix, True


def _ok(stdout: str, *, max_output_chars: int) -> dict[str, Any]:
    rendered, truncated = _truncate(stdout, max_output_chars)
    return {
        "error": "",
        "stdout": rendered,
        "stderr": "Output truncated." if truncated else "",
        "exit_code": 0,
    }


def _fail(message: str, *, exit_code: int = 1) -> dict[str, Any]:
    return {"error": message, "stdout": "", "stderr": message, "exit_code": exit_code}


def _cmd_ls(workspace_dir: Path, args: list[str], *, max_output_chars: int) -> dict[str, Any]:
    visible_args = [arg for arg in args if not arg.startswith("-")]
    paths = _expand_path_args(workspace_dir, visible_args)
    lines: list[str] = []
    for path in paths:
        if not path.exists():
            return _fail(f"Path not found: {_relative(path, workspace_dir)}")
        if path.is_dir():
            entries = sorted(path.iterdir(), key=lambda item: item.name.lower())
            if len(paths) > 1:
                lines.append(f"{_relative(path, workspace_dir)}:")
            lines.extend(f"{entry.name}{'/' if entry.is_dir() else ''}" for entry in entries)
        else:
            lines.append(_relative(path, workspace_dir))
    return _ok("\n".join(lines) + ("\n" if lines else ""), max_output_chars=max_output_chars)


def _cmd_cat(workspace_dir: Path, args: list[str], *, max_output_chars: int) -> dict[str, Any]:
    paths = _expand_path_args(workspace_dir, args)
    chunks: list[str] = []
    for path in paths:
        if not path.is_file():
            return _fail(f"File not found: {_relative(path, workspace_dir)}")
        chunks.append(_read_text(path))
    return _ok("".join(chunks), max_output_chars=max_output_chars)


def _parse_line_count(args: list[str], default: int) -> tuple[int, list[str]]:
    remaining: list[str] = []
    count = default
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "-n" and idx + 1 < len(args):
            try:
                count = max(0, int(args[idx + 1]))
            except ValueError:
                count = default
            idx += 2
            continue
        if arg.startswith("-n") and len(arg) > 2:
            try:
                count = max(0, int(arg[2:]))
            except ValueError:
                count = default
            idx += 1
            continue
        remaining.append(arg)
        idx += 1
    return count, remaining


def _cmd_head_tail(
    workspace_dir: Path,
    args: list[str],
    *,
    tail: bool,
    max_output_chars: int,
) -> dict[str, Any]:
    count, path_args = _parse_line_count(args, 10)
    paths = _expand_path_args(workspace_dir, path_args)
    chunks: list[str] = []
    for path in paths:
        if not path.is_file():
            return _fail(f"File not found: {_relative(path, workspace_dir)}")
        lines = _read_text(path).splitlines()
        selected = lines[-count:] if tail and count else lines[:count]
        if len(paths) > 1:
            chunks.append(f"==> {_relative(path, workspace_dir)} <==")
        chunks.extend(selected)
    return _ok("\n".join(chunks) + ("\n" if chunks else ""), max_output_chars=max_output_chars)


def _cmd_wc(workspace_dir: Path, args: list[str], *, max_output_chars: int) -> dict[str, Any]:
    paths = _expand_path_args(workspace_dir, [arg for arg in args if not arg.startswith("-")])
    lines: list[str] = []
    total_lines = total_words = total_chars = 0
    for path in paths:
        if not path.is_file():
            return _fail(f"File not found: {_relative(path, workspace_dir)}")
        text = _read_text(path)
        line_count = len(text.splitlines())
        word_count = len(text.split())
        char_count = len(text)
        total_lines += line_count
        total_words += word_count
        total_chars += char_count
        lines.append(f"{line_count:7d} {word_count:7d} {char_count:7d} {_relative(path, workspace_dir)}")
    if len(paths) > 1:
        lines.append(f"{total_lines:7d} {total_words:7d} {total_chars:7d} total")
    return _ok("\n".join(lines) + ("\n" if lines else ""), max_output_chars=max_output_chars)


def _cmd_find(workspace_dir: Path, args: list[str], *, max_output_chars: int) -> dict[str, Any]:
    root_arg = "."
    pattern = "*"
    idx = 0
    if args and not args[0].startswith("-"):
        root_arg = args[0]
        idx = 1
    while idx < len(args):
        if args[idx] == "-name" and idx + 1 < len(args):
            pattern = args[idx + 1]
            idx += 2
            continue
        idx += 1
    root = _resolve_workspace_path(workspace_dir, root_arg)
    if not root.exists():
        return _fail(f"Path not found: {_relative(root, workspace_dir)}")
    if root.is_file():
        matches = [root] if fnmatch.fnmatch(root.name, pattern) else []
    else:
        matches = [path for path in root.rglob("*") if fnmatch.fnmatch(path.name, pattern)]
    lines = [_relative(path, workspace_dir) for path in sorted(matches)]
    return _ok("\n".join(lines) + ("\n" if lines else ""), max_output_chars=max_output_chars)


def _iter_search_files(path: Path, *, recursive: bool) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        iterator = path.rglob("*") if recursive else path.iterdir()
        return [candidate for candidate in iterator if candidate.is_file()]
    return []


def _cmd_grep(workspace_dir: Path, args: list[str], *, max_output_chars: int) -> dict[str, Any]:
    ignore_case = False
    show_line_numbers = False
    recursive = False
    filtered: list[str] = []
    for arg in args:
        if arg in {"-i", "--ignore-case"}:
            ignore_case = True
        elif arg in {"-n", "--line-number"}:
            show_line_numbers = True
        elif arg in {"-R", "-r", "--recursive"}:
            recursive = True
        else:
            filtered.append(arg)
    if not filtered:
        return _fail("grep requires a pattern.")
    pattern = filtered[0]
    path_args = filtered[1:] or ["."]
    flags = re.IGNORECASE if ignore_case else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as exc:
        return _fail(f"Invalid grep pattern: {exc}")
    paths = _expand_path_args(workspace_dir, path_args)
    lines: list[str] = []
    for path in paths:
        if path.is_dir() and not recursive:
            recursive = True
        for file_path in _iter_search_files(path, recursive=recursive):
            try:
                file_lines = _read_text(file_path).splitlines()
            except OSError:
                continue
            for line_no, line in enumerate(file_lines, start=1):
                if not regex.search(line):
                    continue
                prefix = _relative(file_path, workspace_dir)
                if show_line_numbers:
                    prefix = f"{prefix}:{line_no}"
                lines.append(f"{prefix}:{line}")
    exit_code = 0 if lines else 1
    payload = _ok("\n".join(lines) + ("\n" if lines else ""), max_output_chars=max_output_chars)
    payload["exit_code"] = exit_code
    payload["error"] = "" if exit_code == 0 else "No matches found."
    return payload


def _validate_rg_args(workspace_dir: Path, args: list[str]) -> str | None:
    for arg in args:
        if arg.startswith("-"):
            continue
        if arg in {".", ".."} or "/" in arg or "\\" in arg or Path(arg).is_absolute():
            try:
                _resolve_workspace_path(workspace_dir, arg)
            except ValueError as exc:
                return str(exc)
    return None


async def _cmd_rg(
    workspace_dir: Path,
    args: list[str],
    *,
    timeout: int,
    max_output_chars: int,
) -> dict[str, Any]:
    rg_bin = shutil.which("rg")
    if not rg_bin:
        return _fail("Command 'rg' is not available on this system.")
    validation_error = _validate_rg_args(workspace_dir, args)
    if validation_error:
        return _fail(validation_error)
    proc = await asyncio.create_subprocess_exec(
        rg_bin,
        *args,
        cwd=str(workspace_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=max(5, int(timeout)))
    except TimeoutError:
        proc.kill()
        await proc.communicate()
        return _fail("Command timed out.", exit_code=124)
    stdout = out_b.decode(errors="replace")
    stderr = err_b.decode(errors="replace")
    rendered, truncated = _truncate(stdout, max_output_chars)
    return {
        "error": "" if proc.returncode == 0 else (stderr.strip() or "Command failed."),
        "stdout": rendered,
        "stderr": (stderr + ("\nOutput truncated." if truncated else "")).strip(),
        "exit_code": int(proc.returncode or 0),
    }


async def _run_workspace_command(
    *,
    workspace_dir: Path,
    tokens: list[str],
    timeout: int,
    max_output_chars: int,
) -> dict[str, Any]:
    command = tokens[0].lower()
    args = tokens[1:]
    try:
        if command == "ls":
            return _cmd_ls(workspace_dir, args, max_output_chars=max_output_chars)
        if command == "cat":
            return _cmd_cat(workspace_dir, args, max_output_chars=max_output_chars)
        if command == "head":
            return _cmd_head_tail(workspace_dir, args, tail=False, max_output_chars=max_output_chars)
        if command == "tail":
            return _cmd_head_tail(workspace_dir, args, tail=True, max_output_chars=max_output_chars)
        if command == "wc":
            return _cmd_wc(workspace_dir, args, max_output_chars=max_output_chars)
        if command == "find":
            return _cmd_find(workspace_dir, args, max_output_chars=max_output_chars)
        if command == "grep":
            return _cmd_grep(workspace_dir, args, max_output_chars=max_output_chars)
        if command == "rg":
            return await _cmd_rg(
                workspace_dir,
                args,
                timeout=timeout,
                max_output_chars=max_output_chars,
            )
    except (OSError, ValueError) as exc:
        return _fail(str(exc))
    return _fail(f"Command '{command}' is not implemented by the cross-platform workspace runner.")


async def run_bash(
    *,
    user_id: str,
    workspace_id: str,
    data_path: str | None,
    command: str,
    timeout: int = 60,
) -> dict[str, Any]:
    _ = user_id, workspace_id
    call_id = new_tool_call_id("bash")
    emit_agent_event(
        "tool_call",
        {"tool": "bash", "args": {"command": command}, "call_id": call_id},
    )

    validation_error = _validate_command(command)
    if validation_error:
        payload = {"error": validation_error, "stdout": "", "stderr": validation_error, "exit_code": 1}
        emit_agent_event(
            "tool_result",
            {"call_id": call_id, "output": payload, "status": "error", "duration_ms": 1},
        )
        return payload

    workspace_dir, path_error = _workspace_dir_from_data_path(data_path)
    if path_error:
        emit_agent_event(
            "tool_result",
            {"call_id": call_id, "output": path_error, "status": "error", "duration_ms": 1},
        )
        return path_error

    runtime = load_agent_runtime_config()
    response = await _run_workspace_command(
        workspace_dir=workspace_dir or Path("."),
        tokens=_split_command(command),
        timeout=timeout,
        max_output_chars=runtime.bash_max_output_chars,
    )
    stdout = str(response.get("stdout") or "")
    stderr = str(response.get("stderr") or "")
    for line in stdout.splitlines():
        emit_agent_event("tool_progress", {"call_id": call_id, "line": line})
    for line in stderr.splitlines():
        emit_agent_event("tool_progress", {"call_id": call_id, "line": line})

    status = "success" if int(response.get("exit_code") or 1) == 0 else "error"
    emit_agent_event(
        "tool_result",
        {"call_id": call_id, "output": response, "status": status, "duration_ms": 1},
    )
    return response
