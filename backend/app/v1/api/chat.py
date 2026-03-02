from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any
import json
import traceback

from ..db.session import get_db_session
from ..schemas.chat import AnalyzeRequest, AnalyzeResponse
from ..services.chat_service import ChatService
from .deps import get_current_user, get_langgraph_manager
from ...core.logger import logprint

router = APIRouter(prefix="/chat", tags=["V1 Chat"])


def _to_sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    payload: AnalyzeRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
    langgraph_manager=Depends(get_langgraph_manager),
):
    """Run analysis in workspace scope and persist a turn."""
    response_payload, conversation_id, turn_id = await ChatService.analyze_and_persist_turn(
        session=session,
        langgraph_manager=langgraph_manager,
        user=current_user,
        workspace_id=payload.workspace_id,
        conversation_id=payload.conversation_id,
        question=payload.question,
        current_code=payload.current_code,
        model=payload.model,
        context=payload.context,
        table_name_override=payload.table_name,
        active_schema_override=payload.active_schema,
        api_key=payload.api_key,
    )

    return AnalyzeResponse(
        conversation_id=conversation_id,
        turn_id=turn_id,
        is_safe=response_payload["is_safe"],
        is_relevant=response_payload["is_relevant"],
        code=response_payload["code"],
        explanation=response_payload["explanation"],
        run_id=response_payload.get("run_id"),
        execution=response_payload.get("execution"),
        artifacts=response_payload.get("artifacts") or [],
        final_script_artifact_id=response_payload.get("final_script_artifact_id"),
    )


@router.post("/stream")
async def stream_analyze(
    payload: AnalyzeRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
    langgraph_manager=Depends(get_langgraph_manager),
):
    """Stream analysis events using SSE for real-time UI updates."""

    async def event_generator():
        try:
            async for event in ChatService.analyze_and_stream_turns(
                session=session,
                langgraph_manager=langgraph_manager,
                user=current_user,
                workspace_id=payload.workspace_id,
                conversation_id=payload.conversation_id,
                question=payload.question,
                current_code=payload.current_code,
                model=payload.model,
                context=payload.context,
                table_name_override=payload.table_name,
                active_schema_override=payload.active_schema,
                api_key=payload.api_key,
            ):
                yield _to_sse(event["event"], event["data"])
        except Exception as e:
            logprint(f"❌ [V1 Chat] Stream error:\n{traceback.format_exc()}", level="error")
            yield _to_sse("error", {"detail": str(e), "status_code": 500})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
