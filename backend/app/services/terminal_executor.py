"""Workspace-scoped persistent terminal session helpers."""

from __future__ import annotations

import asyncio
import os
import platform
import re
import shlex
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable

from app.core.logger import logprint


_DONE_RE = re.compile(r"__INQUIRA_DONE__(?P<token>[A-Za-z0-9]+)__(?P<code>-?\d+)")
_CWD_RE = re.compile(r"__INQUIRA_CWD__(?P<token>[A-Za-z0-9]+)__(?P<cwd>.*)")


@dataclass
class TerminalSession:
    session_key: str
    process: asyncio.subprocess.Process
    shell: str
    mode: str
    cwd: str
    workspace_dir: str
    lock: asyncio.Lock


class TerminalSessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, TerminalSession] = {}
        self._sessions_lock = asyncio.Lock()

    @staticmethod
    def detect_shell_command() -> tuple[str, list[str], str]:
        """Return shell executable + args + mode classifier."""
        if os.name == "nt":
            powershell = shutil.which("pwsh") or shutil.which("powershell")
            if powershell:
                return powershell, ["-NoLogo", "-NoProfile"], "powershell"
            cmd = shutil.which("cmd") or "cmd"
            return cmd, ["/Q"], "cmd"

        shell = os.environ.get("SHELL", "").strip()
        if shell:
            shell_name = Path(shell).name.lower()
            if "zsh" in shell_name:
                return shell, [], "posix"
            if "bash" in shell_name:
                return shell, [], "posix"
            return shell, [], "posix"

        bash = shutil.which("bash")
        if bash:
            return bash, [], "posix"
        sh = shutil.which("sh") or "/bin/sh"
        return sh, [], "posix"

    @staticmethod
    def normalize_workspace_cwd(workspace_dir: str, cwd: str | None) -> str:
        base = Path(workspace_dir).resolve()
        if not cwd:
            return str(base)
        return TerminalSessionManager.resolve_workspace_cwd(
            workspace_dir=workspace_dir,
            cwd=cwd,
            current_cwd=str(base),
        )

    @staticmethod
    def resolve_workspace_cwd(
        *,
        workspace_dir: str,
        cwd: str | None,
        current_cwd: str | None = None,
    ) -> str:
        base = Path(workspace_dir).resolve()
        anchor = Path(current_cwd).resolve() if current_cwd else base
        if not cwd:
            resolved = anchor
        else:
            requested = Path(cwd).expanduser()
            resolved = requested.resolve() if requested.is_absolute() else (anchor / requested).resolve()
        try:
            resolved.relative_to(base)
        except ValueError as exc:
            raise PermissionError("cwd must stay within the workspace directory.") from exc
        return str(resolved)

    async def _start_session(self, session_key: str, workspace_dir: str) -> TerminalSession:
        shell_bin, shell_args, mode = self.detect_shell_command()
        process = await asyncio.create_subprocess_exec(
            shell_bin,
            *shell_args,
            cwd=self.normalize_workspace_cwd(workspace_dir, None),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        session = TerminalSession(
            session_key=session_key,
            process=process,
            shell=shell_bin,
            mode=mode,
            cwd=self.normalize_workspace_cwd(workspace_dir, None),
            workspace_dir=self.normalize_workspace_cwd(workspace_dir, None),
            lock=asyncio.Lock(),
        )
        return session

    async def get_or_start_session(self, *, session_key: str, workspace_dir: str) -> TerminalSession:
        async with self._sessions_lock:
            session = self._sessions.get(session_key)
            if session and session.process.returncode is None:
                return session
            session = await self._start_session(session_key, workspace_dir)
            self._sessions[session_key] = session
            return session

    async def stop_session(self, session_key: str) -> bool:
        async with self._sessions_lock:
            session = self._sessions.pop(session_key, None)
        if session is None:
            return False
        if session.process.returncode is None:
            session.process.terminate()
            try:
                await asyncio.wait_for(session.process.wait(), timeout=2)
            except asyncio.TimeoutError:
                session.process.kill()
                await session.process.wait()
        return True

    async def shutdown(self) -> None:
        async with self._sessions_lock:
            keys = list(self._sessions.keys())
        for key in keys:
            await self.stop_session(key)

    def _wrap_command(self, *, mode: str, command: str, token: str) -> str:
        if mode == "powershell":
            return (
                f"{command}\n"
                f"Write-Output \"__INQUIRA_DONE__{token}__$LASTEXITCODE\"\n"
                f"Write-Output \"__INQUIRA_CWD__{token}__$($PWD.Path)\"\n"
            )
        if mode == "cmd":
            return (
                f"{command}\r\n"
                f"echo __INQUIRA_DONE__{token}__%ERRORLEVEL%\r\n"
                f"echo __INQUIRA_CWD__{token}__%CD%\r\n"
            )

        # posix
        return (
            f"{command}\n"
            f"__inq_exit=$?\n"
            f"printf '__INQUIRA_DONE__{token}__%s\\n' \"$__inq_exit\"\n"
            f"printf '__INQUIRA_CWD__{token}__%s\\n' \"$PWD\"\n"
        )

    @staticmethod
    def _parse_first_command_tokens(command: str) -> list[str]:
        try:
            return shlex.split(command, posix=os.name != "nt")
        except Exception:
            return command.split()

    def _validate_inline_cd_command(self, *, session: TerminalSession, command: str) -> None:
        tokens = self._parse_first_command_tokens(command)
        if not tokens or tokens[0].lower() != "cd":
            return
        if len(tokens) > 2:
            raise ValueError("cd command accepts at most one path argument.")
        target = tokens[1] if len(tokens) == 2 else session.workspace_dir
        self.resolve_workspace_cwd(
            workspace_dir=session.workspace_dir,
            cwd=target,
            current_cwd=session.cwd,
        )

    async def run_command(
        self,
        *,
        session_key: str,
        command: str,
        workspace_dir: str,
        cwd: str | None = None,
        timeout: int = 120,
        on_output_line: Callable[[str], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        trimmed = (command or "").strip()
        if not trimmed:
            resolved = self.normalize_workspace_cwd(workspace_dir, cwd)
            return {
                "stdout": "",
                "stderr": "No command provided.",
                "exit_code": 1,
                "cwd": resolved,
                "shell": "",
                "platform": platform.system(),
                "timed_out": False,
                "persistent": True,
            }

        session = await self.get_or_start_session(session_key=session_key, workspace_dir=workspace_dir)
        self._validate_inline_cd_command(session=session, command=trimmed)
        token = uuid.uuid4().hex[:12]
        payload = self._wrap_command(mode=session.mode, command=trimmed, token=token)

        stdout_lines: list[str] = []
        stderr_text = ""
        exit_code = 1
        detected_cwd = session.cwd
        timed_out = False

        async with session.lock:
            stdin = session.process.stdin
            stdout_stream = session.process.stdout
            if stdin is None or stdout_stream is None:
                return {
                    "stdout": "",
                    "stderr": "Terminal session stream is unavailable.",
                    "exit_code": 1,
                    "cwd": session.cwd,
                    "shell": session.shell,
                    "platform": platform.system(),
                    "timed_out": False,
                    "persistent": True,
                }

            # If caller requested cwd, cd first in current persistent shell.
            if cwd:
                target_cwd = self.resolve_workspace_cwd(
                    workspace_dir=session.workspace_dir,
                    cwd=cwd,
                    current_cwd=session.cwd,
                )
                if target_cwd != session.cwd:
                    if session.mode == "powershell":
                        escaped = target_cwd.replace("'", "''")
                        cd_payload = f"Set-Location -Path '{escaped}'\n"
                    elif session.mode == "cmd":
                        cd_payload = f"cd /d {target_cwd}\r\n"
                    else:
                        cd_payload = f"cd {shlex.quote(target_cwd)}\n"
                    stdin.write(cd_payload.encode("utf-8", errors="replace"))
                    await stdin.drain()

            stdin.write(payload.encode("utf-8", errors="replace"))
            await stdin.drain()

            deadline = asyncio.get_running_loop().time() + max(1, int(timeout))
            done_seen = False
            cwd_seen = False

            try:
                while True:
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0:
                        raise asyncio.TimeoutError

                    line_bytes = await asyncio.wait_for(stdout_stream.readline(), timeout=remaining)
                    if not line_bytes:
                        break

                    line = line_bytes.decode("utf-8", errors="replace").rstrip("\r\n")

                    done_match = _DONE_RE.search(line)
                    if done_match and done_match.group("token") == token:
                        exit_code = int(done_match.group("code"))
                        done_seen = True
                        continue

                    cwd_match = _CWD_RE.search(line)
                    if cwd_match and cwd_match.group("token") == token:
                        detected_cwd = cwd_match.group("cwd") or detected_cwd
                        cwd_seen = True
                        if done_seen:
                            break
                        continue

                    stdout_lines.append(line)
                    if on_output_line is not None:
                        await on_output_line(line)

                    if done_seen and cwd_seen:
                        break

            except asyncio.TimeoutError:
                timed_out = True
                stderr_text = f"Command timed out after {max(1, int(timeout))} seconds."

        # Keep session alive and update tracked cwd.
        session.cwd = detected_cwd

        stdout = "\n".join(stdout_lines).strip()
        return {
            "stdout": stdout,
            "stderr": stderr_text,
            "exit_code": exit_code,
            "cwd": detected_cwd,
            "shell": session.shell,
            "platform": platform.system(),
            "timed_out": timed_out,
            "persistent": True,
        }

    async def run_command_stream(
        self,
        *,
        session_key: str,
        command: str,
        workspace_dir: str,
        cwd: str | None = None,
        timeout: int = 120,
    ) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async def on_output_line(line: str) -> None:
            await queue.put({"type": "output", "line": line})

        async def worker() -> None:
            try:
                result = await self.run_command(
                    session_key=session_key,
                    command=command,
                    workspace_dir=workspace_dir,
                    cwd=cwd,
                    timeout=timeout,
                    on_output_line=on_output_line,
                )
                await queue.put({"type": "final", "result": result})
            except Exception as exc:
                await queue.put({"type": "error", "error": str(exc)})

        worker_task = asyncio.create_task(worker())
        try:
            while True:
                event = await queue.get()
                yield event
                if event.get("type") in {"final", "error"}:
                    break
        finally:
            await worker_task


_terminal_session_manager = TerminalSessionManager()


def detect_shell_command() -> tuple[str, list[str]]:
    shell, args, _mode = TerminalSessionManager.detect_shell_command()
    return shell, args


def normalize_workspace_cwd(workspace_dir: str, cwd: str | None) -> str:
    return TerminalSessionManager.normalize_workspace_cwd(workspace_dir, cwd)


def make_terminal_session_key(*, user_id: str, workspace_id: str) -> str:
    return f"{user_id}:{workspace_id}"


async def stop_workspace_terminal_session(*, user_id: str, workspace_id: str) -> bool:
    return await _terminal_session_manager.stop_session(make_terminal_session_key(user_id=user_id, workspace_id=workspace_id))


async def shutdown_terminal_sessions() -> None:
    await _terminal_session_manager.shutdown()


async def run_workspace_terminal_command(
    *,
    user_id: str,
    workspace_id: str,
    command: str,
    workspace_dir: str,
    cwd: str | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    session_key = make_terminal_session_key(user_id=user_id, workspace_id=workspace_id)
    logprint(
        "Terminal command execution",
        level="INFO",
        workspace_id=workspace_id,
        user_id=user_id,
        command_preview=command[:200],
    )
    return await _terminal_session_manager.run_command(
        session_key=session_key,
        command=command,
        workspace_dir=workspace_dir,
        cwd=cwd,
        timeout=timeout,
    )


async def stream_workspace_terminal_command(
    *,
    user_id: str,
    workspace_id: str,
    command: str,
    workspace_dir: str,
    cwd: str | None = None,
    timeout: int = 120,
) -> AsyncIterator[dict[str, Any]]:
    session_key = make_terminal_session_key(user_id=user_id, workspace_id=workspace_id)
    logprint(
        "Terminal command streaming execution",
        level="INFO",
        workspace_id=workspace_id,
        user_id=user_id,
        command_preview=command[:200],
    )
    async for event in _terminal_session_manager.run_command_stream(
        session_key=session_key,
        command=command,
        workspace_dir=workspace_dir,
        cwd=cwd,
        timeout=timeout,
    ):
        yield event
