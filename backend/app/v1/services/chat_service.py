"""Workspace conversation chat analysis service.

Persists turns in app DB and uses per-workspace LangGraph checkpoint state.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from ...agent.graph import InputSchema
from ..repositories.conversation_repository import ConversationRepository
from ..repositories.dataset_repository import DatasetRepository
from ..repositories.workspace_repository import WorkspaceRepository
from .conversation_service import ConversationService
from .workspace_storage_service import WorkspaceStorageService


class ChatService:
    """Runs analysis and persists chat turns."""

    @staticmethod
    def _derive_conversation_title(question: str) -> str:
        """Build readable conversation title from first question text."""
        normalized = " ".join((question or "").strip().split())
        if not normalized:
            return "New Conversation"
        if len(normalized) <= 60:
            return normalized
        return f"{normalized[:57]}..."

    @staticmethod
    async def _load_schema(filepath: str) -> dict[str, Any]:
        """Load JSON schema from disk with async-compatible boundary."""
        schema_path = Path(filepath)
        if not schema_path.exists():
            raise HTTPException(status_code=404, detail=f"Schema file not found: {schema_path}")

        def _read() -> dict[str, Any]:
            with schema_path.open("r", encoding="utf-8") as file:
                return json.load(file)

        return await asyncio.to_thread(_read)

    @staticmethod
    async def analyze_and_persist_turn(
        session: AsyncSession,
        langgraph_manager,
        user,
        workspace_id: str,
        conversation_id: str | None,
        question: str,
        current_code: str,
        model: str,
        context: str | None,
    ) -> tuple[dict[str, Any], str, str]:
        """Run one analysis cycle and persist resulting turn.

        Returns:
            tuple(response_payload, conversation_id, turn_id)
        """
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        if conversation_id is None:
            conversation = await ConversationService.create_conversation(
                session=session,
                user_id=user.id,
                workspace_id=workspace_id,
                title=ChatService._derive_conversation_title(question),
            )
            conversation_id = conversation.id

        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None or conversation.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Conversation not found in workspace")

        latest_dataset = await DatasetRepository.get_latest_for_workspace(session, workspace_id)
        if latest_dataset is None:
            raise HTTPException(status_code=400, detail="No dataset available in workspace")

        if not latest_dataset.schema_path:
            raise HTTPException(status_code=400, detail="Schema is missing for active dataset")

        schema = await ChatService._load_schema(latest_dataset.schema_path)

        memory_path = WorkspaceStorageService.build_agent_memory_path(user.username, workspace_id)
        graph = await langgraph_manager.get_graph(workspace_id, memory_path)

        input_state = InputSchema(
            messages=[HumanMessage(content=question)],
            active_schema=schema,
            previous_code=current_code,
            current_code=current_code,
            table_name=latest_dataset.table_name,
            data_path=latest_dataset.source_path,
        )
        thread_id = f"{user.id}:{workspace_id}:{conversation_id}"
        config = {
            "configurable": {
                "api_key": None,
                "thread_id": thread_id,
            }
        }

        # API key is still fetched from legacy settings for now to avoid hard break.
        from ...database.database import get_user_settings

        settings = get_user_settings(user.id) or {}
        api_key = settings.get("api_key")
        if not api_key:
            raise HTTPException(status_code=401, detail="API key not configured")
        config["configurable"]["api_key"] = api_key

        result = await graph.ainvoke(input_state, config=config)

        metadata = result.get("metadata", {})
        if hasattr(metadata, "model_dump"):
            metadata = metadata.model_dump()
        elif hasattr(metadata, "dict"):
            metadata = metadata.dict()

        code = result.get("current_code", "") or result.get("code", "") or ""
        explanation = result.get("plan", "") or ""

        final_messages = result.get("messages", [])
        if not explanation and final_messages:
            last_message = final_messages[-1]
            explanation = str(getattr(last_message, "content", ""))

        response_payload = {
            "is_safe": bool(metadata.get("is_safe", True)),
            "is_relevant": bool(metadata.get("is_relevant", True)),
            "code": code,
            "explanation": explanation,
        }

        seq_no = await ConversationRepository.next_seq_no(session, conversation_id)
        if seq_no == 1 and (conversation.title or "").strip().lower() == "new conversation":
            conversation.title = ChatService._derive_conversation_title(question)
        turn = await ConversationRepository.create_turn(
            session=session,
            conversation_id=conversation_id,
            seq_no=seq_no,
            user_text=question,
            assistant_text=explanation,
            tool_events=[],
            metadata=metadata,
            code_snapshot=code,
        )
        await session.commit()

        return response_payload, conversation_id, turn.id
