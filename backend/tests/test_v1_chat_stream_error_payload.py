from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.v1.api.chat import _error_event_payload, stream_analyze
from app.v1.schemas.chat import AnalyzeRequest
from app.v1.services.chat_service import ChatService


def test_error_event_payload_uses_http_exception_status_and_detail():
    payload = _error_event_payload(HTTPException(status_code=502, detail="Agent stream failed"))

    assert payload["status_code"] == 502
    assert payload["detail"] == "Agent stream failed"


def test_error_event_payload_falls_back_to_exception_name_when_empty_message():
    payload = _error_event_payload(RuntimeError(""))

    assert payload["status_code"] == 500
    assert payload["detail"] == "RuntimeError"


@pytest.mark.asyncio
async def test_stream_analyze_preserves_original_error_detail(monkeypatch):
    async def _failing_stream(**_kwargs):
        raise HTTPException(status_code=502, detail="synthetic stream failure")
        yield  # pragma: no cover

    monkeypatch.setattr(ChatService, "analyze_and_stream_turns", staticmethod(_failing_stream))

    response = await stream_analyze(
        AnalyzeRequest(
            workspace_id="ws-1",
            question="hello",
            conversation_id="conv-1",
            current_code="",
            model="google/gemini-2.5-flash",
            context=None,
            table_name=None,
            preferred_table_name=None,
            active_schema=None,
            attachments=[],
            api_key=None,
        ),
        session=None,
        current_user=SimpleNamespace(id="user-1"),
        langgraph_manager=None,
    )

    chunks = []
    async for part in response.body_iterator:
        chunks.append(part.decode() if isinstance(part, bytes) else str(part))

    joined = "".join(chunks)
    assert "synthetic stream failure" in joined
    assert "not associated with a value" not in joined


@pytest.mark.asyncio
async def test_stream_analyze_passes_reasoning_event_through(monkeypatch):
    async def _reasoning_stream(**_kwargs):
        yield {
            "event": "reasoning",
            "data": {
                "stage": "intent",
                "message": "I understand the question, so I need inspect data context.",
                "route": "analysis",
            },
        }
        yield {
            "event": "final",
            "data": {
                "conversation_id": "conv-1",
                "turn_id": "turn-1",
                "is_safe": True,
                "is_relevant": True,
                "code": "",
                "explanation": "done",
            },
        }

    monkeypatch.setattr(ChatService, "analyze_and_stream_turns", staticmethod(_reasoning_stream))

    response = await stream_analyze(
        AnalyzeRequest(
            workspace_id="ws-1",
            question="hello",
            conversation_id="conv-1",
            current_code="",
            model="google/gemini-2.5-flash",
            context=None,
            table_name=None,
            preferred_table_name=None,
            active_schema=None,
            attachments=[],
            api_key=None,
        ),
        session=None,
        current_user=SimpleNamespace(id="user-1"),
        langgraph_manager=None,
    )

    chunks = []
    async for part in response.body_iterator:
        chunks.append(part.decode() if isinstance(part, bytes) else str(part))

    joined = "".join(chunks)
    assert "event: reasoning" in joined
    assert "I understand the question" in joined
    assert "event: final" in joined
