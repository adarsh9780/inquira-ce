"""API v1 chat analysis route bound to workspace/conversation."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_db_session
from ..schemas.chat import AnalyzeRequest, AnalyzeResponse
from ..services.chat_service import ChatService
from .deps import get_current_user, get_langgraph_manager

router = APIRouter(prefix="/chat", tags=["V1 Chat"])


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
    )
