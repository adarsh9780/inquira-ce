"""Prompt-only resource recommendations for active workspace runtimes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import psutil
except Exception:  # pragma: no cover - fallback for constrained environments
    psutil = None  # type: ignore[assignment]


@dataclass(frozen=True)
class MemorySnapshot:
    available_bytes: int
    total_bytes: int
    available_percent: float


def get_memory_snapshot() -> MemorySnapshot:
    """Return host memory availability using psutil when present."""
    if psutil is not None:
        memory = psutil.virtual_memory()
        total = max(1, int(memory.total or 1))
        available = max(0, int(memory.available or 0))
        return MemorySnapshot(
            available_bytes=available,
            total_bytes=total,
            available_percent=(available / total) * 100,
        )
    unavailable = 2**63 - 1
    return MemorySnapshot(
        available_bytes=unavailable,
        total_bytes=unavailable,
        available_percent=100.0,
    )


def build_workspace_resource_recommendation(
    *,
    runtime_snapshots: list[dict[str, Any]],
    workspace_names: dict[str, str] | None = None,
    idle_warning_minutes: int = 20,
    min_available_percent: float = 15.0,
    min_available_bytes: int = 2 * 1024 * 1024 * 1024,
) -> dict[str, Any]:
    """Return prompt-only close recommendations for idle runtimes under pressure."""
    memory = get_memory_snapshot()
    pressure = (
        memory.available_percent < float(min_available_percent)
        or memory.available_bytes < int(min_available_bytes)
    )
    idle_threshold_seconds = max(1, int(idle_warning_minutes)) * 60
    workspace_names = workspace_names or {}
    candidates: list[dict[str, Any]] = []

    if pressure:
        for snapshot in runtime_snapshots:
            status = str(snapshot.get("status") or "missing").strip().lower()
            idle_seconds = max(0, int(snapshot.get("idle_seconds") or 0))
            if status == "busy" or idle_seconds < idle_threshold_seconds:
                continue
            workspace_id = str(snapshot.get("workspace_id") or "").strip()
            if not workspace_id:
                continue
            candidates.append(
                {
                    "workspace_id": workspace_id,
                    "workspace_name": workspace_names.get(workspace_id) or "",
                    "status": status,
                    "idle_seconds": idle_seconds,
                    "last_used_at": snapshot.get("last_used_at") or None,
                    "reason": "Workspace has been idle while system memory is low.",
                }
            )

    return {
        "type": "workspace_resource_recommendation",
        "available_memory_bytes": memory.available_bytes,
        "available_memory_percent": memory.available_percent,
        "memory_pressure": pressure,
        "idle_warning_minutes": max(1, int(idle_warning_minutes)),
        "candidates": candidates,
    }
