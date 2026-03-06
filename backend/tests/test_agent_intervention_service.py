import pytest

from app.v1.services.agent_intervention_service import AgentInterventionService


@pytest.mark.asyncio
async def test_intervention_service_round_trip_submission():
    service = AgentInterventionService()
    pending = await service.create_request(
        user_id="user-1",
        workspace_id="ws-1",
        prompt="Install package?",
        options=["statsmodels"],
        multi_select=True,
        timeout_sec=3,
    )

    accepted = await service.submit_response(
        intervention_id=pending.id,
        user_id="user-1",
        selected=["statsmodels"],
    )
    result = await service.await_response(
        intervention_id=pending.id,
        timeout_sec=3,
    )

    assert accepted is True
    assert result["timed_out"] is False
    assert result["selected"] == ["statsmodels"]


@pytest.mark.asyncio
async def test_intervention_service_timeout_auto_denies():
    service = AgentInterventionService()
    pending = await service.create_request(
        user_id="user-2",
        workspace_id="ws-2",
        prompt="Install package?",
        options=["scipy"],
        multi_select=True,
        timeout_sec=1,
    )

    result = await service.await_response(
        intervention_id=pending.id,
        timeout_sec=1,
    )

    assert result["timed_out"] is True
    assert result["selected"] == []
