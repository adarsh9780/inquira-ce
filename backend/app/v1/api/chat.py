import asyncio
import json
import math
import traceback
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_appdata_db_session
from ..schemas.chat import (
    AnalyzeRequest,
    AnalyzeResponse,
    InterventionResponseAck,
    InterventionResponseRequest,
)
from ..services.chat_service import ChatService
from ..services.agent_intervention_service import get_agent_intervention_service
from .deps import ensure_appdata_principal, get_current_user, get_langgraph_manager
from ...core.logger import logprint

router = APIRouter(
    prefix="/chat",
    tags=["V1 Chat"],
    dependencies=[Depends(ensure_appdata_principal)],
)


def _normalize_sse_payload(payload: Any) -> Any:
    if isinstance(payload, float):
        if math.isfinite(payload):
            return payload
        return None
    if isinstance(payload, dict):
        return {str(key): _normalize_sse_payload(value) for key, value in payload.items()}
    if isinstance(payload, (list, tuple)):
        return [_normalize_sse_payload(item) for item in payload]
    return payload


def _to_sse(event: str, payload: dict[str, Any]) -> str:
    normalized_payload = _normalize_sse_payload(payload)
    serialized_payload = json.dumps(normalized_payload, default=str, allow_nan=False)
    return f"event: {event}\ndata: {serialized_payload}\n\n"


def _error_event_payload(exc: BaseException) -> dict[str, Any]:
    if isinstance(exc, HTTPException):
        status = int(getattr(exc, "status_code", 500) or 500)
        raw_detail = getattr(exc, "detail", None)
        if isinstance(raw_detail, str) and raw_detail.strip():
            detail = raw_detail.strip()
        elif raw_detail is None:
            detail = "Streaming analysis failed."
        else:
            detail = str(raw_detail)
        return {"detail": detail, "status_code": status}

    detail = str(exc).strip() or exc.__class__.__name__
    return {"detail": detail, "status_code": 500}


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    payload: AnalyzeRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
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
        preferred_table_name=payload.preferred_table_name,
        active_schema_override=payload.active_schema,
        attachments=[item.model_dump() for item in payload.attachments],
        api_key=payload.api_key,
    )

    return AnalyzeResponse(
        conversation_id=conversation_id,
        turn_id=turn_id,
        is_safe=response_payload["is_safe"],
        is_relevant=response_payload["is_relevant"],
        code=response_payload["code"],
        explanation=response_payload["explanation"],
        result_explanation=response_payload.get("result_explanation"),
        code_explanation=response_payload.get("code_explanation"),
        run_id=response_payload.get("run_id"),
        execution=response_payload.get("execution"),
        metadata=response_payload.get("metadata"),
        artifacts=response_payload.get("artifacts") or [],
        final_script_artifact_id=response_payload.get("final_script_artifact_id"),
    )


@router.post("/stream")
async def stream_analyze(
    payload: AnalyzeRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
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
                preferred_table_name=payload.preferred_table_name,
                active_schema_override=payload.active_schema,
                attachments=[item.model_dump() for item in payload.attachments],
                api_key=payload.api_key,
            ):
                yield _to_sse(event["event"], event["data"])
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            if isinstance(exc, asyncio.CancelledError):
                # Client-side aborts can cancel the server coroutine; avoid noisy
                # tracebacks because there is no live consumer to receive events.
                logprint("⚠️ [V1 Chat] Stream cancelled before completion.", level="warning")
                return

            error_payload = _error_event_payload(exc)
            logprint(
                (
                    "❌ [V1 Chat] Stream error "
                    f"(type={exc.__class__.__name__}, status={error_payload.get('status_code')}):\n"
                    f"{traceback.format_exc()}"
                ),
                level="error",
            )
            try:
                yield _to_sse("error", error_payload)
            except Exception:
                # If transport is already broken we still prefer a graceful exit.
                return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post(
    "/interventions/{intervention_id}/response",
    response_model=InterventionResponseAck,
)
async def respond_to_intervention(
    intervention_id: str,
    payload: InterventionResponseRequest,
    current_user=Depends(get_current_user),
):
    """Submit a user response for a pending intervention request."""
    accepted = await get_agent_intervention_service().submit_response(
        intervention_id=intervention_id,
        user_id=str(current_user.id),
        selected=payload.selected,
    )
    return InterventionResponseAck(
        intervention_id=str(intervention_id),
        accepted=bool(accepted),
    )
