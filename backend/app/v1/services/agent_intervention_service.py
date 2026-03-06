"""In-memory human intervention broker for paused agent tool calls."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class PendingIntervention:
    id: str
    user_id: str
    workspace_id: str
    prompt: str
    options: list[str]
    multi_select: bool
    timeout_sec: int
    created_at: datetime
    future: asyncio.Future[dict[str, Any]]


class AgentInterventionService:
    """Tracks intervention requests and resumes waiting graph tasks."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._pending: dict[str, PendingIntervention] = {}

    async def create_request(
        self,
        *,
        user_id: str,
        workspace_id: str,
        prompt: str,
        options: list[str],
        multi_select: bool,
        timeout_sec: int,
    ) -> PendingIntervention:
        intervention_id = uuid.uuid4().hex
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        pending = PendingIntervention(
            id=intervention_id,
            user_id=str(user_id),
            workspace_id=str(workspace_id),
            prompt=str(prompt or "").strip(),
            options=[str(opt) for opt in options if str(opt).strip()],
            multi_select=bool(multi_select),
            timeout_sec=max(1, int(timeout_sec)),
            created_at=datetime.now(UTC),
            future=future,
        )
        async with self._lock:
            self._pending[intervention_id] = pending
        return pending

    async def await_response(
        self,
        *,
        intervention_id: str,
        timeout_sec: int,
    ) -> dict[str, Any]:
        pending = await self.get_request(intervention_id)
        if pending is None:
            return {"selected": [], "timed_out": True, "status": "missing"}
        try:
            response = await asyncio.wait_for(
                pending.future,
                timeout=max(1, int(timeout_sec)),
            )
            if isinstance(response, dict):
                return response
            return {"selected": [], "timed_out": False, "status": "invalid"}
        except asyncio.TimeoutError:
            return {"selected": [], "timed_out": True, "status": "timeout"}
        finally:
            await self.remove_request(intervention_id)

    async def submit_response(
        self,
        *,
        intervention_id: str,
        user_id: str,
        selected: list[str],
    ) -> bool:
        pending = await self.get_request(intervention_id)
        if pending is None:
            return False
        if pending.user_id != str(user_id):
            return False
        if pending.future.done():
            return False

        safe_selected = [str(item) for item in selected if str(item).strip()]
        if not pending.multi_select and len(safe_selected) > 1:
            safe_selected = safe_selected[:1]

        pending.future.set_result(
            {
                "selected": safe_selected,
                "timed_out": False,
                "status": "submitted",
            }
        )
        return True

    async def get_request(self, intervention_id: str) -> PendingIntervention | None:
        async with self._lock:
            return self._pending.get(str(intervention_id))

    async def remove_request(self, intervention_id: str) -> None:
        async with self._lock:
            self._pending.pop(str(intervention_id), None)


_service = AgentInterventionService()


def get_agent_intervention_service() -> AgentInterventionService:
    return _service
