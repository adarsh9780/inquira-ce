"""API v1 conversation and turn routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_db_session
from ..schemas.common import MessageResponse
from ..schemas.conversation import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationResponse,
    TurnPageResponse,
    TurnResponse,
)
from ..services.conversation_service import ConversationService
from .deps import get_current_user

router = APIRouter(tags=["V1 Conversations"])


@router.post("/workspaces/{workspace_id}/conversations", response_model=ConversationResponse)
async def create_conversation(
    workspace_id: str,
    payload: ConversationCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Create conversation under a workspace."""
    conv = await ConversationService.create_conversation(
        session=session,
        user_id=current_user.id,
        workspace_id=workspace_id,
        title=payload.title,
    )
    return ConversationResponse(
        id=conv.id,
        workspace_id=conv.workspace_id,
        title=conv.title,
        last_turn_at=conv.last_turn_at,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.get("/workspaces/{workspace_id}/conversations", response_model=ConversationListResponse)
async def list_conversations(
    workspace_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """List workspace conversations ordered by recency."""
    conversations = await ConversationService.list_conversations(
        session=session,
        user_id=current_user.id,
        workspace_id=workspace_id,
        limit=limit,
    )
    return ConversationListResponse(
        conversations=[
            ConversationResponse(
                id=conv.id,
                workspace_id=conv.workspace_id,
                title=conv.title,
                last_turn_at=conv.last_turn_at,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
            for conv in conversations
        ]
    )


@router.post("/conversations/{conversation_id}/clear", response_model=MessageResponse)
async def clear_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Delete all turns while keeping conversation."""
    await ConversationService.clear_conversation(session, current_user.id, conversation_id)
    return MessageResponse(message="Conversation cleared")


@router.delete("/conversations/{conversation_id}", response_model=MessageResponse)
async def delete_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Delete conversation and all turns."""
    await ConversationService.delete_conversation(session, current_user.id, conversation_id)
    return MessageResponse(message="Conversation deleted")


@router.get("/conversations/{conversation_id}/turns", response_model=TurnPageResponse)
async def list_turns(
    conversation_id: str,
    limit: int = Query(default=5, ge=1, le=50),
    before: str | None = None,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """List turns using cursor pagination."""
    turns, next_cursor = await ConversationService.list_turns(
        session=session,
        user_id=current_user.id,
        conversation_id=conversation_id,
        limit=limit,
        before=before,
    )
    return TurnPageResponse(
        turns=[TurnResponse(**turn) for turn in turns],
        next_cursor=next_cursor,
    )
