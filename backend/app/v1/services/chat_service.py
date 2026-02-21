"""Workspace conversation chat analysis service.

Persists turns in app DB and uses per-workspace LangGraph checkpoint state.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from typing import cast

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
                return cast(dict[str, Any], json.load(file))

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
        table_name_override: str | None = None,
        active_schema_override: dict[str, Any] | None = None,
        api_key: str | None = None,
    ) -> tuple[dict[str, Any], str, str]:
        """Run one analysis cycle and persist resulting turn.

        Returns:
            tuple(response_payload, conversation_id, turn_id)
        """
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        if conversation_id is None:
            created_conversation = await ConversationService.create_conversation(
                session=session,
                user_id=user.id,
                workspace_id=workspace_id,
                title=ChatService._derive_conversation_title(question),
            )
            conversation_id = created_conversation.id

        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None or conversation.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Conversation not found in workspace")

        schema: dict[str, Any] | None = None
        table_name: str | None = None
        data_path: str | None = None

        def _normalize_table_name(raw: str) -> str:
            return "".join(c if c.isalnum() or c == "_" else "_" for c in raw.strip()).lower()

        # Hard invariant: if client selected a table, it must already exist in
        # workspace dataset catalog with persisted schema metadata.
        if table_name_override and str(table_name_override).strip():
            requested_table = _normalize_table_name(str(table_name_override))
            if not requested_table:
                raise HTTPException(
                    status_code=400,
                    detail="Dataset preflight failed: selected table name is invalid.",
                )

            selected_dataset = await DatasetRepository.get_for_workspace_table(
                session=session,
                workspace_id=workspace_id,
                table_name=requested_table,
            )
            if selected_dataset is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Dataset preflight failed: selected table is not synced to workspace. "
                        "Please reselect your dataset in the Data tab."
                    ),
                )

            table_name = selected_dataset.table_name
            data_path = selected_dataset.source_path
            if not selected_dataset.schema_path:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Dataset preflight failed: schema metadata is missing for selected table. "
                        "Please reselect your dataset in the Data tab."
                    ),
                )
            try:
                schema = await ChatService._load_schema(selected_dataset.schema_path)
            except HTTPException as exc:
                if exc.status_code == 404:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Dataset preflight failed: schema file is unavailable for selected table. "
                            "Please reselect your dataset in the Data tab."
                        ),
                    ) from exc
                raise

            # Prefer explicit active schema for current browser session when provided,
            # but only after server-side preflight validates synced dataset metadata.
            if active_schema_override and isinstance(active_schema_override, dict):
                override_table = str(active_schema_override.get("table_name", "")).strip().lower()
                if not override_table or override_table == table_name:
                    schema = active_schema_override
                    if not schema.get("table_name"):
                        schema["table_name"] = table_name

        if schema is None:
            latest_dataset = await DatasetRepository.get_latest_for_workspace(session, workspace_id)
            if latest_dataset is not None:
                table_name = latest_dataset.table_name
                data_path = latest_dataset.source_path
                if latest_dataset.schema_path:
                    schema = await ChatService._load_schema(latest_dataset.schema_path)

        if schema is None:
            # Workspace chat remains available as a general-purpose assistant
            # even when no dataset is attached yet.
            schema = {"table_name": table_name or "", "columns": []}

        memory_path = WorkspaceStorageService.build_agent_memory_path(user.username, workspace_id)
        graph = await langgraph_manager.get_graph(workspace_id, memory_path)

        input_state = InputSchema(
            messages=[HumanMessage(content=question)],
            active_schema=schema,
            previous_code=current_code,
            current_code=current_code,
            table_name=table_name,
            data_path=data_path,
        )
        thread_id = f"{user.id}:{workspace_id}:{conversation_id}"
        config = {
            "configurable": {
                "api_key": None,
                "thread_id": thread_id,
            }
        }

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
