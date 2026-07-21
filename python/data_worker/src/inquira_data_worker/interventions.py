"""In-process broker for user decisions requested by the local agent."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PendingIntervention:
    id: str
    workspace_id: str
    prompt: str
    options: list[str]
    multi_select: bool
    timeout_sec: float
    future: asyncio.Future[dict[str, Any]]


class InterventionBroker:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._pending: dict[str, PendingIntervention] = {}

    async def create_request(
        self,
        *,
        workspace_id: str,
        prompt: str,
        options: list[str],
        multi_select: bool,
        timeout_sec: float,
    ) -> PendingIntervention:
        normalized_options = _strings(options, limit=20)
        pending = PendingIntervention(
            id=uuid.uuid4().hex,
            workspace_id=str(workspace_id or "").strip(),
            prompt=str(prompt or "").strip()[:2_000],
            options=normalized_options,
            multi_select=bool(multi_select),
            timeout_sec=max(0.01, float(timeout_sec)),
            future=asyncio.get_running_loop().create_future(),
        )
        async with self._lock:
            self._pending[pending.id] = pending
        return pending

    async def await_response(
        self, intervention_id: str, *, timeout_sec: float | None = None
    ) -> dict[str, Any]:
        pending = await self.get(intervention_id)
        if pending is None:
            return {"selected": [], "timed_out": True, "status": "missing"}
        timeout = pending.timeout_sec if timeout_sec is None else max(0.01, float(timeout_sec))
        try:
            response = await asyncio.wait_for(pending.future, timeout=timeout)
            return response if isinstance(response, dict) else {
                "selected": [], "timed_out": False, "status": "invalid"
            }
        except asyncio.TimeoutError:
            return {"selected": [], "timed_out": True, "status": "timeout"}
        finally:
            await self.remove(intervention_id)

    async def submit_response(self, intervention_id: str, selected: list[str]) -> bool:
        pending = await self.get(intervention_id)
        if pending is None or pending.future.done():
            return False
        allowed = set(pending.options)
        normalized = [item for item in _strings(selected, limit=20) if not allowed or item in allowed]
        if not pending.multi_select:
            normalized = normalized[:1]
        pending.future.set_result({
            "selected": normalized,
            "timed_out": False,
            "status": "submitted",
        })
        return True

    async def get(self, intervention_id: str) -> PendingIntervention | None:
        async with self._lock:
            return self._pending.get(str(intervention_id or "").strip())

    async def remove(self, intervention_id: str) -> None:
        async with self._lock:
            self._pending.pop(str(intervention_id or "").strip(), None)

    async def close(self) -> None:
        async with self._lock:
            pending = list(self._pending.values())
            self._pending.clear()
        for item in pending:
            if not item.future.done():
                item.future.cancel()


def _strings(values: list[str], *, limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values if isinstance(values, list) else []:
        value = str(raw or "").strip()[:200]
        if value and value not in seen:
            seen.add(value)
            result.append(value)
        if len(result) == limit:
            break
    return result
