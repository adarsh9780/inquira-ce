from types import SimpleNamespace

import pytest

from app.v1.services.chat_service import ChatService


class _FakeGraph:
    def __init__(self):
        self.input_state = None
        self.updated_state = None
        self.known_thread_ids: list[str] = []

    async def aget_state(self, config=None):
        thread_id = str((config or {}).get("configurable", {}).get("thread_id", ""))
        self.known_thread_ids.append(thread_id)
        return SimpleNamespace(
            values={
                "known_columns": [
                    {
                        "table_name": "orders",
                        "name": "gross_margin",
                        "dtype": "DOUBLE",
                        "description": "Profitability percentage",
                    }
                ]
            }
        )

    async def aupdate_state(self, config=None, values=None):
        thread_id = str((config or {}).get("configurable", {}).get("thread_id", ""))
        self.known_thread_ids.append(thread_id)
        self.updated_state = values
        return None

    async def ainvoke(self, input_state, config=None):
        _ = config
        self.input_state = input_state
        return {
            "route": "analysis",
            "metadata": {"is_safe": True, "is_relevant": True},
            "final_code": "",
            "final_explanation": "done",
            "output_contract": [],
            "messages": [],
            "known_columns": [
                {
                    "table_name": "orders",
                    "name": "gross_margin",
                    "dtype": "DOUBLE",
                    "description": "Profitability percentage",
                },
                {
                    "table_name": "orders",
                    "name": "order_total",
                    "dtype": "DOUBLE",
                    "description": "Order amount",
                },
            ],
        }


class _FakeLanggraphManager:
    def __init__(self, graph):
        self.graph = graph

    async def get_graph(self, _workspace_id, _memory_path):
        return self.graph


@pytest.mark.asyncio
async def test_chat_service_shares_known_columns_across_workspace_conversations(monkeypatch):
    fake_graph = _FakeGraph()

    async def _fake_preflight(**_kwargs):
        return (SimpleNamespace(title="New Conversation"), "conv-1", {}, "orders", "/tmp/ws.db")

    async def _fake_persist_turn(**_kwargs):
        return "turn-1"

    def _fake_build_input_state(**kwargs):
        return kwargs

    monkeypatch.setattr(ChatService, "_preflight_check", staticmethod(_fake_preflight))
    monkeypatch.setattr(ChatService, "_persist_turn", staticmethod(_fake_persist_turn))
    monkeypatch.setattr("app.v1.services.chat_service.get_agent_bindings", lambda: SimpleNamespace(build_input_state=_fake_build_input_state))
    monkeypatch.setattr(
        "app.v1.services.chat_service.SecretStorageService.get_api_key",
        lambda _uid, provider="openrouter": "key",
    )

    user = SimpleNamespace(id="user-1", username="alice")
    payload, conversation_id, turn_id = await ChatService.analyze_and_persist_turn(
        session=None,
        langgraph_manager=_FakeLanggraphManager(fake_graph),
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
    assert fake_graph.input_state is not None
    assert fake_graph.input_state["known_columns"][0]["name"] == "gross_margin"
    assert fake_graph.updated_state is not None
    assert len(fake_graph.updated_state["known_columns"]) == 2
    assert "user-1:ws-1:known_columns" in fake_graph.known_thread_ids
