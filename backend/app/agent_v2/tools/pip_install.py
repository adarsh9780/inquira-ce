"""Package install tool with required user intervention."""

from __future__ import annotations

import asyncio
from typing import Any

from ...services.code_executor import bootstrap_workspace_runtime, reset_workspace_kernel
from ...services.execution_config import load_execution_runtime_config
from ...services.runner_env import install_runner_package
from ...v1.services.agent_intervention_service import get_agent_intervention_service
from ..events import emit_agent_event
from ..runtime import load_agent_runtime_config
from . import new_tool_call_id


def _normalize_packages(packages: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for pkg in packages:
        token = str(pkg or "").strip()
        key = token.lower()
        if not token or key in seen:
            continue
        seen.add(key)
        normalized.append(token)
    return normalized


async def pip_install(
    *,
    user_id: str,
    workspace_id: str,
    data_path: str | None,
    packages: list[str],
) -> dict[str, Any]:
    call_id = new_tool_call_id("pip_install")
    requested = _normalize_packages(packages)
    emit_agent_event(
        "tool_call",
        {
            "tool": "pip_install",
            "args": {"packages": requested},
            "call_id": call_id,
        },
    )

    if not requested:
        payload = {"installed": [], "denied": [], "message": "No package names provided."}
        emit_agent_event(
            "tool_result",
            {"call_id": call_id, "output": payload, "status": "error", "duration_ms": 1},
        )
        return payload

    runtime = load_agent_runtime_config()
    broker = get_agent_intervention_service()
    pending = await broker.create_request(
        user_id=user_id,
        workspace_id=workspace_id,
        prompt="Install these packages to continue analysis?",
        options=requested,
        multi_select=True,
        timeout_sec=runtime.intervention_timeout_seconds,
    )
    emit_agent_event(
        "intervention_request",
        {
            "id": pending.id,
            "prompt": pending.prompt,
            "options": pending.options,
            "multi_select": pending.multi_select,
            "timeout_sec": pending.timeout_sec,
        },
    )

    intervention_result = await broker.await_response(
        intervention_id=pending.id,
        timeout_sec=pending.timeout_sec,
    )
    selected = _normalize_packages(intervention_result.get("selected", []))
    emit_agent_event(
        "intervention_response",
        {"id": pending.id, "selected": selected},
    )
    if intervention_result.get("timed_out"):
        payload = {"installed": [], "denied": requested, "message": "User did not respond in time."}
        emit_agent_event(
            "tool_result",
            {"call_id": call_id, "output": payload, "status": "error", "duration_ms": 1},
        )
        return payload
    if not selected:
        payload = {"installed": [], "denied": requested, "message": "User denied package installation."}
        emit_agent_event(
            "tool_result",
            {"call_id": call_id, "output": payload, "status": "error", "duration_ms": 1},
        )
        return payload
    if not data_path:
        payload = {"installed": [], "denied": selected, "message": "Missing workspace data path."}
        emit_agent_event(
            "tool_result",
            {"call_id": call_id, "output": payload, "status": "error", "duration_ms": 1},
        )
        return payload

    installed: list[str] = []
    failed: list[dict[str, str]] = []
    execution_config = load_execution_runtime_config()
    for package_spec in selected:
        emit_agent_event(
            "tool_progress",
            {"call_id": call_id, "line": f"$ uv pip install --python <runner> {package_spec}"},
        )
        try:
            install_result = await asyncio.to_thread(
                install_runner_package,
                execution_config,
                package_spec,
                None,
                data_path,
            )
            for line in (install_result.stdout or "").splitlines():
                emit_agent_event("tool_progress", {"call_id": call_id, "line": line})
            for line in (install_result.stderr or "").splitlines():
                emit_agent_event("tool_progress", {"call_id": call_id, "line": line})
            installed.append(package_spec)
        except Exception as exc:
            failed.append({"package": package_spec, "error": str(exc)})
            emit_agent_event(
                "tool_progress",
                {"call_id": call_id, "line": f"[error] {package_spec}: {exc}"},
            )

    if installed:
        await reset_workspace_kernel(workspace_id)
        await bootstrap_workspace_runtime(
            workspace_id=workspace_id,
            workspace_duckdb_path=data_path,
        )

    payload = {
        "installed": installed,
        "failed": failed,
        "denied": [pkg for pkg in requested if pkg not in selected],
    }
    status = "success" if installed and not failed else "error"
    emit_agent_event(
        "tool_result",
        {"call_id": call_id, "output": payload, "status": status, "duration_ms": 1},
    )
    return payload
