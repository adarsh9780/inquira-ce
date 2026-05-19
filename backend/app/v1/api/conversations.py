"""API v1 conversation and turn routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_appdata_db_session
from ..schemas.common import MessageResponse
from ..schemas.conversation import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationResponse,
    FinalTurnRerunResponse,
    GlobalTurnTreeConversationResponse,
    GlobalTurnTreeResponse,
    TurnRelationsResponse,
    TurnTreeNodeResponse,
    TurnTreeResponse,
    ConversationUpdateRequest,
    TurnPageResponse,
    TurnOrderUpdateRequest,
    TurnParentUpdateRequest,
    TurnResponse,
)
from ..services.conversation_service import ConversationService
from ..services.chat_service import ChatService
from .deps import ensure_appdata_principal, get_current_user

router = APIRouter(
    tags=["V1 Conversations"],
    dependencies=[Depends(ensure_appdata_principal)],
)


@router.post("/workspaces/{workspace_id}/conversations", response_model=ConversationResponse)
async def create_conversation(
    workspace_id: str,
    payload: ConversationCreateRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Create conversation under a workspace."""
    conv = await ConversationService.create_conversation(
        session=session,
        principal_id=current_user.id,
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
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """List workspace conversations ordered by recency."""
    conversations = await ConversationService.list_conversations(
        session=session,
        principal_id=current_user.id,
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
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Delete all turns while keeping conversation."""
    await ConversationService.clear_conversation(session, current_user.id, conversation_id)
    return MessageResponse(message="Conversation cleared")


@router.delete("/conversations/{conversation_id}", response_model=MessageResponse)
async def delete_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Delete conversation and all turns."""
    await ConversationService.delete_conversation(session, current_user.id, conversation_id)
    return MessageResponse(message="Conversation deleted")


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def patch_conversation(
    conversation_id: str,
    payload: ConversationUpdateRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Update conversation title."""
    conv = await ConversationService.update_conversation(
        session=session,
        principal_id=current_user.id,
        conversation_id=conversation_id,
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


@router.get("/conversations/{conversation_id}/turns", response_model=TurnPageResponse)
async def list_turns(
    conversation_id: str,
    limit: int = Query(default=5, ge=1, le=50),
    before: str | None = None,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """List turns using cursor pagination."""
    turns, next_cursor = await ConversationService.list_turns(
        session=session,
        principal_id=current_user.id,
        conversation_id=conversation_id,
        limit=limit,
        before=before,
    )
    return TurnPageResponse(
        turns=[TurnResponse(**turn) for turn in turns],
        next_cursor=next_cursor,
    )


@router.get("/conversations/{conversation_id}/turns/{turn_id}", response_model=TurnResponse)
async def get_turn(
    conversation_id: str,
    turn_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Fetch one turn by id."""
    turn = await ConversationService.get_turn(
        session=session,
        principal_id=current_user.id,
        conversation_id=conversation_id,
        turn_id=turn_id,
    )
    return TurnResponse(**turn)


@router.get("/conversations/{conversation_id}/turns/{turn_id}/relations", response_model=TurnRelationsResponse)
async def get_turn_relations(
    conversation_id: str,
    turn_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Fetch turn lineage and branch navigation details."""
    payload = await ConversationService.get_turn_relations(
        session=session,
        principal_id=current_user.id,
        conversation_id=conversation_id,
        turn_id=turn_id,
    )
    return TurnRelationsResponse(
        current=TurnResponse(**payload["current"]),
        parent=TurnResponse(**payload["parent"]) if payload["parent"] else None,
        children=[TurnResponse(**turn) for turn in payload["children"]],
        previous_turn=TurnResponse(**payload["previous_turn"]) if payload["previous_turn"] else None,
        next_turn=TurnResponse(**payload["next_turn"]) if payload["next_turn"] else None,
    )


def _build_turn_tree_node(payload: dict) -> TurnTreeNodeResponse:
    return TurnTreeNodeResponse(
        id=payload["id"],
        parent_turn_id=payload.get("parent_turn_id"),
        seq_no=payload["seq_no"],
        sibling_order=payload.get("sibling_order", 0),
        user_text=payload["user_text"],
        assistant_text=payload.get("assistant_text", ""),
        created_at=payload["created_at"],
        children=[_build_turn_tree_node(child) for child in payload.get("children") or []],
    )


@router.get("/workspaces/{workspace_id}/turn-tree", response_model=GlobalTurnTreeResponse)
async def get_workspace_turn_tree(
    workspace_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Fetch all visible conversation trees for a workspace."""
    payload = await ConversationService.get_workspace_turn_tree(
        session=session,
        principal_id=current_user.id,
        workspace_id=workspace_id,
    )
    return GlobalTurnTreeResponse(
        conversations=[
            GlobalTurnTreeConversationResponse(
                id=conversation["id"],
                title=conversation["title"],
                last_turn_at=conversation["last_turn_at"],
                created_at=conversation["created_at"],
                updated_at=conversation["updated_at"],
                roots=[_build_turn_tree_node(node) for node in conversation.get("roots") or []],
            )
            for conversation in payload["conversations"]
        ]
    )


@router.get("/conversations/{conversation_id}/turn-tree", response_model=TurnTreeResponse)
async def get_turn_tree(
    conversation_id: str,
    current_turn_id: str | None = None,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Fetch the full turn tree for a conversation."""
    payload = await ConversationService.get_turn_tree(
        session=session,
        principal_id=current_user.id,
        conversation_id=conversation_id,
        current_turn_id=current_turn_id,
    )
    return TurnTreeResponse(
        roots=[_build_turn_tree_node(node) for node in payload["roots"]],
        current_turn_id=payload.get("current_turn_id"),
        final_turn_id=payload.get("final_turn_id"),
    )


@router.delete("/conversations/{conversation_id}/turns/{turn_id}", response_model=MessageResponse)
async def delete_turn(
    conversation_id: str,
    turn_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Soft-delete one visible leaf turn."""
    await ConversationService.delete_turn(
        session=session,
        principal_id=current_user.id,
        conversation_id=conversation_id,
        turn_id=turn_id,
    )
    return MessageResponse(message="Turn deleted")


@router.patch("/conversations/{conversation_id}/turns/{turn_id}/parent", response_model=TurnResponse)
async def move_turn_parent(
    conversation_id: str,
    turn_id: str,
    payload: TurnParentUpdateRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Move one visible turn under another visible turn in the same conversation."""
    turn = await ConversationService.move_turn_parent(
        session=session,
        principal_id=current_user.id,
        conversation_id=conversation_id,
        turn_id=turn_id,
        parent_turn_id=payload.parent_turn_id,
    )
    return TurnResponse(**turn)


@router.patch("/conversations/{conversation_id}/turns/order", response_model=TurnTreeResponse)
async def reorder_turns(
    conversation_id: str,
    payload: TurnOrderUpdateRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Replace display order for all visible siblings under one parent."""
    tree = await ConversationService.reorder_turns(
        session=session,
        principal_id=current_user.id,
        conversation_id=conversation_id,
        parent_turn_id=payload.parent_turn_id,
        turn_ids=payload.turn_ids,
    )
    return TurnTreeResponse(
        roots=[_build_turn_tree_node(node) for node in tree["roots"]],
        current_turn_id=tree.get("current_turn_id"),
        final_turn_id=tree.get("final_turn_id"),
    )


@router.get("/conversations/{conversation_id}/final-turn", response_model=TurnResponse | None)
async def get_final_turn(
    conversation_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Fetch the selected final turn for a conversation."""
    turn = await ConversationService.get_final_turn(
        session=session,
        principal_id=current_user.id,
        conversation_id=conversation_id,
    )
    return TurnResponse(**turn) if turn else None


@router.post("/conversations/{conversation_id}/turns/{turn_id}/final", response_model=TurnResponse)
async def mark_final_turn(
    conversation_id: str,
    turn_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Mark one successful turn as the final reproducible turn."""
    turn = await ConversationService.mark_final_turn(
        session=session,
        principal_id=current_user.id,
        conversation_id=conversation_id,
        turn_id=turn_id,
    )
    return TurnResponse(**turn)


@router.post("/conversations/{conversation_id}/final-turn/rerun", response_model=FinalTurnRerunResponse)
async def rerun_final_turn(
    conversation_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Rerun the selected final turn from its stored code snapshot."""
    payload = await ChatService.rerun_final_turn(
        session=session,
        user=current_user,
        conversation_id=conversation_id,
    )
    return FinalTurnRerunResponse(**payload)
