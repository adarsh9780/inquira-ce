from types import SimpleNamespace

import pytest

from app.v1.services.chat_service import ChatService


def _authoritative_execution_result() -> tuple[dict, int, float, str]:
    return (
        {
            "success": True,
            "stdout": "workspace-ok",
            "stderr": "",
            "error": None,
            "artifacts": [
                {
                    "artifact_id": "art-1",
                    "run_id": "run-1",
                    "kind": "dataframe",
                    "logical_name": "result",
                    "row_count": 1,
                    "schema": [],
                    "preview_rows": [],
                    "created_at": "",
                }
            ],
        },
        0,
        10.0,
        "wrapped_code",
    )


@pytest.mark.asyncio
async def test_analyze_and_persist_turn_uses_authoritative_runtime_when_agent_execution_is_not_explicitly_authoritative(
    monkeypatch,
):
    execution_calls: list[str] = []

    async def _fake_preflight(**_kwargs):
        return (SimpleNamespace(title="New Conversation"), "conv-1", {}, "tbl", "/tmp/ws.duckdb")

    async def _fake_persist_turn(**_kwargs):
        return "turn-1"

    async def _fake_execute_generated_code_with_retries(**kwargs):
        execution_calls.append(str(kwargs.get("generated_code") or ""))
        return _authoritative_execution_result()

    async def _fake_finalize_kernel_run(**_kwargs):
        return None

    async def _fake_health(self):
        _ = self
        return {"status": "ok", "api_major": 1}

    async def _fake_run(self, payload):
        _ = self, payload
        return {
            "route": "analysis",
            "metadata": {"is_safe": True, "is_relevant": True},
            "final_code": "print('fresh')",
            "final_execution": {
                "success": True,
                "stdout": "agent-ok",
                "stderr": "",
                "retry_count": 0,
                "duration_ms": 1,
            },
            "final_artifacts": [],
            "final_executed_code": "print('fresh')",
            "messages": [],
        }

    monkeypatch.setattr(ChatService, "_preflight_check", staticmethod(_fake_preflight))
    monkeypatch.setattr(ChatService, "_persist_turn", staticmethod(_fake_persist_turn))
    monkeypatch.setattr(
        ChatService,
        "_execute_generated_code_with_retries",
        staticmethod(_fake_execute_generated_code_with_retries),
    )
    monkeypatch.setattr(ChatService, "_finalize_kernel_run", staticmethod(_fake_finalize_kernel_run))
    monkeypatch.setattr(
        "app.v1.services.chat_service.SecretStorageService.get_api_key",
        lambda _uid, provider="openrouter": "key",
    )
    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.assert_health", _fake_health)
    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.run", _fake_run)

    payload, conversation_id, turn_id = await ChatService.analyze_and_persist_turn(
        session=object(),
        langgraph_manager=None,
        user=SimpleNamespace(id="user-1", username="alice"),
        workspace_id="ws-1",
        conversation_id=None,
        question="Print fresh",
        current_code="print('stale')",
        model="google/gemini-2.5-flash",
        context=None,
        api_key="test-api-key",
    )

    assert conversation_id == "conv-1"
    assert turn_id == "turn-1"
    assert execution_calls == ["print('fresh')"]
    assert payload["code"] == "print('fresh')"
    assert payload["execution"]["stdout"] == "workspace-ok"
    assert payload["artifacts"][0]["artifact_id"] == "art-1"
    assert payload["metadata"]["execution_source"] == "workspace_kernel"


@pytest.mark.asyncio
async def test_stream_uses_last_values_snapshot_and_runs_authoritative_runtime(monkeypatch):
    execution_calls: list[str] = []

    async def _fake_preflight(**_kwargs):
        return (SimpleNamespace(title="New Conversation"), "conv-2", {}, "tbl", "/tmp/ws.duckdb")

    async def _fake_persist_turn(**_kwargs):
        return "turn-2"

    async def _fake_execute_generated_code_with_retries(**kwargs):
        execution_calls.append(str(kwargs.get("generated_code") or ""))
        return _authoritative_execution_result()

    async def _fake_finalize_kernel_run(**_kwargs):
        return None

    async def _fake_health(self):
        _ = self
        return {"status": "ok", "api_major": 1}

    async def _fake_stream():
        yield {"event": "metadata", "data": {"run_id": "run-1"}}
        yield {
            "event": "values",
            "data": {
                "run_id": "run-1",
                "route": "analysis",
                "metadata": {"is_safe": True, "is_relevant": True},
                "final_code": "print('fresh')",
                "final_execution": {
                    "success": True,
                    "stdout": "agent-ok",
                    "stderr": "",
                    "retry_count": 0,
                    "duration_ms": 2,
                },
                "final_artifacts": [],
                "final_executed_code": "print('fresh')",
                "messages": [],
            },
        }
        # Simulate late update noise that should not override the final values snapshot.
        yield {
            "event": "updates",
            "data": {
                "analysis_generate_code": {
                    "current_code": "print('stale')",
                    "candidate_code": "print('stale')",
                }
            },
        }

    monkeypatch.setattr(ChatService, "_preflight_check", staticmethod(_fake_preflight))
    monkeypatch.setattr(ChatService, "_persist_turn", staticmethod(_fake_persist_turn))
    monkeypatch.setattr(
        ChatService,
        "_execute_generated_code_with_retries",
        staticmethod(_fake_execute_generated_code_with_retries),
    )
    monkeypatch.setattr(ChatService, "_finalize_kernel_run", staticmethod(_fake_finalize_kernel_run))
    monkeypatch.setattr(
        "app.v1.services.chat_service.SecretStorageService.get_api_key",
        lambda _uid, provider="openrouter": "key",
    )
    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.assert_health", _fake_health)
    monkeypatch.setattr(
        "app.v1.services.chat_service.AgentClient.stream",
        lambda _self, _payload: _fake_stream(),
    )

    user = SimpleNamespace(id="user-2", username="bob")
    events = []
    async for event in ChatService.analyze_and_stream_turns(
        session=None,
        langgraph_manager=None,
        user=user,
        workspace_id="ws-1",
        conversation_id="conv-2",
        question="Run the latest code",
        current_code="print('stale')",
        model="google/gemini-2.5-flash",
        context=None,
        table_name_override=None,
        active_schema_override=None,
        api_key=None,
    ):
        events.append(event)

    final_events = [evt for evt in events if evt.get("event") == "final"]
    assert final_events
    final_payload = final_events[-1]["data"]

    assert execution_calls == ["print('fresh')"]
    assert final_payload["code"] == "print('fresh')"
    assert final_payload["execution"]["stdout"] == "workspace-ok"
    assert final_payload["artifacts"][0]["artifact_id"] == "art-1"
    assert final_payload["metadata"]["execution_source"] == "workspace_kernel"

