from types import SimpleNamespace

import pytest

from app.services.agent_client import AgentClient
from app.v1.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_analyze_and_persist_turn_uses_remote_agent_client(monkeypatch):
    captured_payload: dict[str, object] = {}

    async def _fake_preflight(**_kwargs):
        return (
            SimpleNamespace(title="New Conversation"),
            "conv-1",
            {"tables": [{"table_name": "orders", "columns": []}]},
            "orders",
            "/tmp/ws.db",
        )

    async def _fake_persist_turn(**_kwargs):
        return "turn-1"

    monkeypatch.setattr(ChatService, "_preflight_check", staticmethod(_fake_preflight))
    monkeypatch.setattr(ChatService, "_persist_turn", staticmethod(_fake_persist_turn))
    monkeypatch.setattr(
        "app.v1.services.chat_service.SecretStorageService.get_api_key",
        lambda _uid, provider="openrouter": "key",
    )

    async def fake_health(self):
        _ = self
        return {"status": "ok", "api_major": 1}

    async def fake_run(self, payload):
        _ = self
        captured_payload.update(payload)
        return {
            "route": "analysis",
            "metadata": {"is_safe": True, "is_relevant": True},
            "final_code": "",
            "final_explanation": "done",
            "output_contract": [],
            "messages": [],
        }

    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.assert_health", fake_health)
    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.run", fake_run)
    async def _fake_resolve_llm_preferences(_session, _user_id):
        return {
            "provider": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "requires_api_key": True,
            "selected_lite_model": "openai/gpt-4.1-mini",
            "selected_main_model": "google/gemini-2.5-flash",
            "selected_coding_model": "google/gemini-2.5-flash",
            "temperature": 0.0,
            "max_tokens": 2048,
            "top_p": 1.0,
            "top_k": 0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }
    monkeypatch.setattr(
        "app.v1.services.chat_service.ChatService._resolve_llm_preferences",
        staticmethod(_fake_resolve_llm_preferences),
    )

    user = SimpleNamespace(id="user-1", username="alice")
    payload, conversation_id, turn_id = await ChatService.analyze_and_persist_turn(
        session=None,
        langgraph_manager=None,
        user=user,
        workspace_id="ws-1",
        conversation_id=None,
        question="show profitability trend",
        current_code="",
        model="google/gemini-2.5-flash",
        context=None,
    )

    assert payload["is_safe"] is True
    assert conversation_id == "conv-1"
    assert turn_id == "turn-1"
    assert captured_payload["workspace_id"] == "ws-1"
    assert captured_payload["conversation_id"] == "conv-1"
    assert captured_payload["table_names"] == ["orders"]
    assert captured_payload["workspace_schema"] == {"tables": [{"table_name": "orders", "columns": []}]}
    assert captured_payload["scratchpad_path"] == "/tmp/scratchpad/artifacts.duckdb"
    assert "table_name" not in captured_payload
    assert "preferred_table_name" not in captured_payload
    assert "active_schema" not in captured_payload
    assert captured_payload["agent_profile"] == "agent_v2"
    assert captured_payload["llm"]["api_key"] == "key"
    assert captured_payload["llm"]["top_k"] == 0


def test_build_remote_agent_payload_normalizes_windows_paths():
    payload = ChatService._build_remote_agent_payload(
        request_id="req-1",
        user_id="user-1",
        workspace_id="ws-1",
        conversation_id="conv-1",
        question="show profitability trend",
        current_code="",
        model="google/gemini-2.5-flash",
        context="",
        table_names=["orders"],
        data_path=r"C:\tmp\ws.db",
        workspace_schema={},
        scratchpad_path=r"C:\tmp\scratchpad\artifacts.duckdb",
        attachments=[],
        llm_prefs={
            "provider": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "selected_lite_model": "openai/gpt-4.1-mini",
            "selected_main_model": "google/gemini-2.5-flash",
            "selected_coding_model": "google/gemini-2.5-flash",
            "temperature": 0.0,
            "max_tokens": 2048,
            "top_p": 1.0,
            "top_k": 0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        },
        resolved_api_key="key",
        agent_profile="agent_v2",
    )

    assert payload["data_path"] == "C:/tmp/ws.db"
    assert payload["scratchpad_path"] == "C:/tmp/scratchpad/artifacts.duckdb"


def test_agent_client_configurable_clamps_max_tokens_to_context_budget():
    payload = {
        "user_id": "user-1",
        "workspace_id": "ws-1",
        "conversation_id": "conv-1",
        "question": "x" * 8000,
        "current_code": "",
        "context": "",
        "workspace_schema": {},
        "attachments": [],
        "model": "google/gemini-2.5-flash",
        "llm": {
            "api_key": "key",
            "provider": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "default_model": "google/gemini-2.5-flash",
            "lite_model": "google/gemini-2.5-flash-lite",
            "coding_model": "google/gemini-2.5-flash",
            "temperature": 0.0,
            "max_tokens": 4096,
            "context_window": 4096,
            "top_p": 1.0,
            "top_k": 0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        },
    }

    config = AgentClient._configurable(payload)

    assert config["max_tokens"] < 4096
    assert config["max_tokens"] >= 1
