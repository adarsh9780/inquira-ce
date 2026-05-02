from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.v1.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_rerun_final_turn_uses_stored_code_and_creates_child_turn(monkeypatch, tmp_path) -> None:
    code_path = tmp_path / "analysis.py"
    code_path.write_text("print('rerun me')\n", encoding="utf-8")

    conversation = SimpleNamespace(id="conv-1", workspace_id="ws-1", final_turn_id="turn-final")
    final_turn = SimpleNamespace(
        id="turn-final",
        conversation_id="conv-1",
        user_text="Monthly revenue",
        code_path=str(code_path),
        code_snapshot="print('fallback')\n",
        result_kind="dataframe",
    )
    captured: dict[str, object] = {}

    async def fake_get_conversation(_session, _conversation_id):
        return conversation

    async def fake_get_workspace(_session, _workspace_id, _principal_id):
        return SimpleNamespace(id="ws-1", duckdb_path=str(tmp_path / "workspace.db"))

    async def fake_get_turn(_session, _turn_id):
        return final_turn

    async def fake_load_workspace_schema(*, session, workspace_id, duckdb_path, preferred_table_name, active_schema_override):
        _ = session, workspace_id, duckdb_path, preferred_table_name, active_schema_override
        return {"table_name": "orders", "tables": [{"table_name": "orders", "context": "", "columns": []}]}

    async def fake_apply_execution(*, workspace_id, workspace_duckdb_path, question, run_id, generated_code, output_contract, response_payload):
        _ = workspace_id, workspace_duckdb_path, question, run_id, output_contract
        captured["generated_code"] = generated_code
        response_payload["execution"] = {"status": "success", "success": True}
        response_payload["artifacts"] = [{"artifact_id": "df-1", "kind": "dataframe"}]

    async def fake_persist_turn(*, session, conversation, username, workspace_id, workspace_schema, data_path, conversation_id, question, attachments, response_payload, result, parent_turn_id=None):
        _ = session, conversation, username, workspace_id, workspace_schema, data_path, conversation_id, question, attachments, response_payload, result
        captured["parent_turn_id"] = parent_turn_id
        return "turn-rerun"

    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.get_conversation", fake_get_conversation)
    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.get_turn", fake_get_turn)
    monkeypatch.setattr("app.v1.services.chat_service.ChatService._load_workspace_schema", fake_load_workspace_schema)
    monkeypatch.setattr("app.v1.services.chat_service.ChatService._apply_authoritative_execution_to_response", fake_apply_execution)
    monkeypatch.setattr("app.v1.services.chat_service.ChatService._persist_turn", fake_persist_turn)

    result = await ChatService.rerun_final_turn(
        session=SimpleNamespace(),
        user=SimpleNamespace(id="user-1", username="ada"),
        conversation_id="conv-1",
    )

    assert captured["generated_code"] == "print('rerun me')\n"
    assert captured["parent_turn_id"] == "turn-final"
    assert result["turn_id"] == "turn-rerun"
    assert result["execution"]["success"] is True
