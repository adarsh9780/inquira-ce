from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.v1.services.conversation_service import ConversationService


@pytest.mark.asyncio
async def test_mark_final_turn_clears_previous_final(monkeypatch, tmp_path: Path) -> None:
    previous_dir = tmp_path / "turn-1"
    previous_dir.mkdir()
    (previous_dir / "analysis.py").write_text("print(1)\n", encoding="utf-8")
    (previous_dir / "turn.json").write_text("{}", encoding="utf-8")

    current_dir = tmp_path / "turn-2"
    current_dir.mkdir()
    (current_dir / "analysis.py").write_text("print(2)\n", encoding="utf-8")
    (current_dir / "turn.json").write_text("{}", encoding="utf-8")

    conversation = SimpleNamespace(id="conv-1", workspace_id="ws-1", final_turn_id="turn-1")
    previous_turn = SimpleNamespace(
        id="turn-1",
        conversation_id="conv-1",
        is_final=True,
        execution_summary_json='{"success": true}',
        code_path=str(previous_dir / "analysis.py"),
        manifest_path=str(previous_dir / "turn.json"),
    )
    current_turn = SimpleNamespace(
        id="turn-2",
        conversation_id="conv-1",
        is_final=False,
        execution_summary_json='{"success": true}',
        parent_turn_id="turn-1",
        result_kind="dataframe",
        code_path=str(current_dir / "analysis.py"),
        manifest_path=str(current_dir / "turn.json"),
        seq_no=2,
        user_text="q",
        assistant_text="a",
        tool_events_json=None,
        metadata_json=None,
        code_snapshot="print(2)",
        created_at="2026-05-02T10:00:00Z",
    )

    async def fake_get_conversation(_session, _conversation_id):
        return conversation

    async def fake_ensure_workspace_access(_session, _principal_id, _workspace_id):
        return SimpleNamespace(id="ws-1")

    async def fake_get_turn(_session, turn_id):
        if turn_id == "turn-1":
            return previous_turn
        if turn_id == "turn-2":
            return current_turn
        return None

    session = SimpleNamespace()

    async def _commit():
        return None

    session.commit = _commit

    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.get_conversation", fake_get_conversation)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationService.ensure_workspace_access", fake_ensure_workspace_access)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.get_turn", fake_get_turn)

    result = await ConversationService.mark_final_turn(
        session=session,
        principal_id="principal-1",
        conversation_id="conv-1",
        turn_id="turn-2",
    )

    assert result["id"] == "turn-2"
    assert conversation.final_turn_id == "turn-2"
    assert previous_turn.is_final is False
    assert current_turn.is_final is True


@pytest.mark.asyncio
async def test_mark_final_turn_requires_persisted_turn_bundle(monkeypatch) -> None:
    conversation = SimpleNamespace(id="conv-1", workspace_id="ws-1", final_turn_id=None)
    current_turn = SimpleNamespace(
        id="turn-2",
        conversation_id="conv-1",
        is_final=False,
        execution_summary_json='{"success": true}',
        parent_turn_id=None,
        result_kind="dataframe",
        code_path=None,
        manifest_path=None,
        seq_no=1,
        user_text="q",
        assistant_text="a",
        tool_events_json=None,
        metadata_json=None,
        code_snapshot="print(2)",
        created_at="2026-05-02T10:00:00Z",
    )

    async def fake_get_conversation(_session, _conversation_id):
        return conversation

    async def fake_ensure_workspace_access(_session, _principal_id, _workspace_id):
        return SimpleNamespace(id="ws-1")

    async def fake_get_turn(_session, turn_id):
        if turn_id == "turn-2":
            return current_turn
        return None

    session = SimpleNamespace()

    async def _commit():
        return None

    session.commit = _commit

    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.get_conversation", fake_get_conversation)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationService.ensure_workspace_access", fake_ensure_workspace_access)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.get_turn", fake_get_turn)

    with pytest.raises(Exception) as exc_info:
        await ConversationService.mark_final_turn(
            session=session,
            principal_id="principal-1",
            conversation_id="conv-1",
            turn_id="turn-2",
        )

    assert "persisted turn bundles" in str(exc_info.value)
