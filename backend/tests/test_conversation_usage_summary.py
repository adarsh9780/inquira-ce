from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.v1.services.conversation_service import ConversationService


def _turn(turn_id: str, conversation_id: str, seq_no: int, usage: dict | None = None, *, deleted: bool = False):
    metadata = {"token_usage": usage} if usage is not None else {}
    return SimpleNamespace(
        id=turn_id,
        conversation_id=conversation_id,
        parent_turn_id=None,
        seq_no=seq_no,
        sibling_order=seq_no,
        user_text=f"Question {seq_no}",
        assistant_text=f"Answer {seq_no}",
        created_at=datetime(2026, 1, seq_no, tzinfo=UTC),
        metadata_json=json.dumps(metadata),
        is_marked_for_deletion=deleted,
    )


def test_aggregate_turn_usage_sums_all_visible_provider_fields_without_estimating() -> None:
    turns = [
        _turn("turn-1", "conv-1", 1, {"input_tokens": 100, "output_tokens": 40, "price_usd": 0.001}),
        _turn("turn-2", "conv-1", 2, {"input_tokens": 20, "cached_tokens": 5, "output_tokens": 10}),
        _turn("turn-3", "conv-1", 3),
    ]

    summary = ConversationService.aggregate_turn_usage("conv-1", turns)

    assert summary["conversation_id"] == "conv-1"
    assert summary["turn_count"] == 3
    assert summary["turns_with_usage"] == 2
    assert summary["usage"]["input_tokens"] == 120
    assert summary["usage"]["output_tokens"] == 50
    assert summary["usage"]["cached_tokens"] == 5
    assert summary["usage"]["price_usd"] == pytest.approx(0.001)
    assert summary["usage"]["total_tokens"] is None


@pytest.mark.asyncio
async def test_get_conversation_usage_uses_visible_turn_repository(monkeypatch) -> None:
    conversation = SimpleNamespace(id="conv-1", workspace_id="workspace-1")
    visible_turns = [
        _turn("turn-1", "conv-1", 1, {"input_tokens": 100, "total_tokens": 140}),
        _turn("turn-2", "conv-1", 2, {"output_tokens": 15, "price_usd": 0.002}),
    ]

    async def fake_get_conversation(session, conversation_id, *, include_deleted=False):
        _ = session, include_deleted
        assert conversation_id == "conv-1"
        return conversation

    async def fake_ensure_workspace_access(session, principal_id, workspace_id):
        _ = session
        assert principal_id == "user-1"
        assert workspace_id == "workspace-1"
        return SimpleNamespace(id=workspace_id)

    async def fake_list_turns_in_sequence(session, conversation_id):
        _ = session
        assert conversation_id == "conv-1"
        return visible_turns

    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.get_conversation", fake_get_conversation)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationService.ensure_workspace_access", fake_ensure_workspace_access)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.list_turns_in_sequence", fake_list_turns_in_sequence)

    summary = await ConversationService.get_conversation_usage(object(), "user-1", "conv-1")

    assert summary["turn_count"] == 2
    assert summary["turns_with_usage"] == 2
    assert summary["usage"]["input_tokens"] == 100
    assert summary["usage"]["output_tokens"] == 15
    assert summary["usage"]["total_tokens"] == 140
    assert summary["usage"]["price_usd"] == pytest.approx(0.002)


@pytest.mark.asyncio
async def test_workspace_turn_tree_includes_node_usage_and_conversation_summary(monkeypatch) -> None:
    conversation = SimpleNamespace(
        id="conv-1",
        title="Analysis",
        last_turn_at=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
        final_turn_id="turn-2",
    )
    turns = [
        _turn("turn-1", "conv-1", 1, {"input_tokens": 100, "output_tokens": 20}),
        _turn("turn-2", "conv-1", 2, {"input_tokens": 50, "price_usd": 0.003}),
    ]
    turns[1].parent_turn_id = "turn-1"

    async def fake_ensure_workspace_access(session, principal_id, workspace_id):
        _ = session, principal_id
        return SimpleNamespace(id=workspace_id)

    async def fake_list_conversations(session, workspace_id, limit=200):
        _ = session, workspace_id, limit
        return [conversation]

    async def fake_list_turns_for_workspace(session, workspace_id):
        _ = session, workspace_id
        return turns

    monkeypatch.setattr("app.v1.services.conversation_service.ConversationService.ensure_workspace_access", fake_ensure_workspace_access)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.list_conversations", fake_list_conversations)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.list_turns_for_workspace", fake_list_turns_for_workspace)

    payload = await ConversationService.get_workspace_turn_tree(object(), "user-1", "workspace-1")

    tree_conversation = payload["conversations"][0]
    assert tree_conversation["usage_summary"]["usage"]["input_tokens"] == 150
    assert tree_conversation["usage_summary"]["usage"]["output_tokens"] == 20
    assert tree_conversation["usage_summary"]["usage"]["price_usd"] == pytest.approx(0.003)
    assert tree_conversation["roots"][0]["usage"]["input_tokens"] == 100
    assert tree_conversation["roots"][0]["children"][0]["usage"]["price_usd"] == pytest.approx(0.003)

