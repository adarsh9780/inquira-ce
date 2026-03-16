from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.agent_v2.state import build_input_state
from app.v1.services.chat_service import ChatService


def test_build_input_state_embeds_image_attachments_in_human_message():
    state = build_input_state(
        question="What is in this chart?",
        schema={},
        current_code="",
        table_name="",
        data_path="/tmp/ws.duckdb",
        context="",
        workspace_id="ws-1",
        user_id="u-1",
        scratchpad_path="/tmp/scratch.duckdb",
        attachments=[
            {
                "attachment_id": "att-1",
                "filename": "chart.png",
                "media_type": "image/png",
                "data_base64": "YWJj",
            }
        ],
    )

    content = state["messages"][0].content
    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"] == "data:image/png;base64,YWJj"


@pytest.mark.asyncio
async def test_chat_rejects_image_attachments_for_non_vision_models(monkeypatch):
    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1", duckdb_path="/tmp/ws.duckdb")

    async def fake_create_conversation(*, session, principal_id, workspace_id, title):
        return SimpleNamespace(id="conv-vision", title=title)

    async def fake_list_for_workspace(_session, _workspace_id):
        return []

    async def fake_get_graph(_workspace_id, _memory_path):
        class _Graph:
            async def ainvoke(self, input_state, config=None):
                return {"metadata": {"is_safe": True, "is_relevant": True}, "plan": "ok", "current_code": ""}

        return _Graph()

    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationService.create_conversation", fake_create_conversation)
    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.list_for_workspace", fake_list_for_workspace)

    session = SimpleNamespace()

    async def _commit():
        return None

    session.commit = _commit
    langgraph_manager = SimpleNamespace(get_graph=fake_get_graph)
    user = SimpleNamespace(id="u1", username="alice")

    with pytest.raises(HTTPException) as exc:
        await ChatService.analyze_and_persist_turn(
            session=session,
            langgraph_manager=langgraph_manager,
            user=user,
            workspace_id="ws-1",
            conversation_id=None,
            question="Describe this image",
            current_code="",
            model="openrouter/free",
            context=None,
            attachments=[
                {
                    "attachment_id": "att-1",
                    "filename": "chart.png",
                    "media_type": "image/png",
                    "data_base64": "YWJj",
                }
            ],
            api_key="x",
        )

    assert exc.value.status_code == 400
    assert "does not support image attachments" in str(exc.value.detail).lower()
