from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.chat import DataAnalysisRequest, chat_endpoint


@pytest.mark.asyncio
async def test_chat_endpoint_preserves_http_exception_status(monkeypatch):
    """Regression test: expected 400 should not be converted into 500."""
    from app.api import chat as chat_module

    monkeypatch.setattr(
        chat_module, "load_user_settings_to_app_state", lambda _user_id, _state: None
    )

    app_state = SimpleNamespace(
        api_key="test-key",
        llm_initialized=True,
        llm_service=object(),
        schema_path=None,  # Forces explicit 400 in endpoint pre-check
        data_path="/tmp/data.csv",
        agent_graph=None,
    )

    request = DataAnalysisRequest(question="How many rows are in the database?")

    with pytest.raises(HTTPException) as exc:
        await chat_endpoint(
            request=request,
            current_user={"user_id": "user-1"},
            app_state=app_state,
        )

    assert exc.value.status_code == 400
    assert "Schema path not configured" in str(exc.value.detail)
