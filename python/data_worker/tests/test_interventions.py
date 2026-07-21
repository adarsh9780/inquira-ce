from __future__ import annotations

import asyncio

from inquira_data_worker.interventions import InterventionBroker


def test_intervention_round_trip_normalizes_single_selection() -> None:
    async def scenario() -> None:
        broker = InterventionBroker()
        pending = await broker.create_request(
            workspace_id="workspace-1", prompt="Continue?",
            options=["approve", "deny"], multi_select=False, timeout_sec=5,
        )
        assert await broker.submit_response(pending.id, ["approve", "deny"]) is True
        assert await broker.await_response(pending.id, timeout_sec=1) == {
            "selected": ["approve"], "timed_out": False, "status": "submitted",
        }
        assert await broker.submit_response(pending.id, ["deny"]) is False

    asyncio.run(scenario())


def test_intervention_timeout_removes_pending_request() -> None:
    async def scenario() -> None:
        broker = InterventionBroker()
        pending = await broker.create_request(
            workspace_id="workspace-1", prompt="Continue?",
            options=["approve"], multi_select=False, timeout_sec=1,
        )
        result = await broker.await_response(pending.id, timeout_sec=0.01)
        assert result == {"selected": [], "timed_out": True, "status": "timeout"}
        assert await broker.submit_response(pending.id, ["approve"]) is False

    asyncio.run(scenario())
