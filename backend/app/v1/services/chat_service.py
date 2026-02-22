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
from .secret_storage_service import SecretStorageService
from .workspace_storage_service import WorkspaceStorageService
from ...core.logger import logprint


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
    async def _preflight_check(
        session: AsyncSession,
        user,
        workspace_id: str,
        conversation_id: str | None,
        question: str,
        table_name_override: str | None,
        active_schema_override: dict[str, Any] | None,
    ) -> tuple[Any, str, dict[str, Any], str, str]:
        """Shared logic to validate workspace, conversation, and dataset before analysis."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        conversation = None
        if conversation_id:
            conversation = await ConversationRepository.get_conversation(session, conversation_id)
            if conversation and conversation.workspace_id != workspace_id:
                logprint(f"⚠️ Conversation {conversation_id} belongs to different workspace. Resetting.")
                conversation = None

        if conversation is None:
            created_conversation = await ConversationService.create_conversation(
                session=session,
                user_id=user.id,
                workspace_id=workspace_id,
                title=ChatService._derive_conversation_title(question),
            )
            conversation = created_conversation
            conversation_id = created_conversation.id
            logprint(f"✅ Created new conversation {conversation_id} for workspace {workspace_id}")

        schema: dict[str, Any] | None = None
        table_name: str | None = None
        data_path: str | None = None

        def _normalize_table_name(raw: str) -> str:
            return "".join(c if c.isalnum() or c == "_" else "_" for c in raw.strip()).lower()

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
            if selected_dataset is not None:
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

                if active_schema_override and isinstance(active_schema_override, dict):
                    override_table = str(active_schema_override.get("table_name", "")).strip().lower()
                    if not override_table or override_table == table_name:
                        schema = active_schema_override
                        if not schema.get("table_name"):
                            schema["table_name"] = table_name
            else:
                logprint(f"⚠️ Requested table '{requested_table}' not found in workspace {workspace_id}. Falling back.")

        if schema is None:
            latest_dataset = await DatasetRepository.get_latest_for_workspace(session, workspace_id)
            if latest_dataset is not None:
                table_name = latest_dataset.table_name
                data_path = latest_dataset.source_path
                if latest_dataset.schema_path:
                    schema = await ChatService._load_schema(latest_dataset.schema_path)

        if schema is None:
            schema = {"table_name": table_name or "", "columns": []}

        if conversation_id is None:
            raise HTTPException(status_code=500, detail="Conversation initialization failed")

        return conversation, conversation_id, schema, table_name or "", data_path or ""

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
        """Run one analysis cycle and persist resulting turn."""
        conversation, conversation_id, schema, table_name, data_path = await ChatService._preflight_check(
            session=session,
            user=user,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            question=question,
            table_name_override=table_name_override,
            active_schema_override=active_schema_override,
        )

        memory_path = WorkspaceStorageService.build_agent_memory_path(user.username, workspace_id)
        graph = await langgraph_manager.get_graph(workspace_id, memory_path)

        input_state = InputSchema(
            messages=[HumanMessage(content=question)],
            active_schema=schema,
            previous_code=current_code,
            current_code=current_code,
            table_name=table_name,
            data_path=data_path,
            context=context or "",
        )
        thread_id = f"{user.id}:{workspace_id}:{conversation_id}"
        config = {
            "configurable": {
                "api_key": api_key,
                "thread_id": thread_id,
                "model": model,
            }
        }
        resolved_api_key = (api_key or "").strip() or (SecretStorageService.get_api_key(user.id) or "")
        config["configurable"]["api_key"] = resolved_api_key
        if not resolved_api_key:
            raise HTTPException(status_code=401, detail="API key not configured")

        result = await graph.ainvoke(input_state, config=config)
        response_payload = ChatService._build_response_payload(result)

        turn_id = await ChatService._persist_turn(
            session=session,
            conversation=conversation,
            conversation_id=conversation_id,
            question=question,
            response_payload=response_payload,
            result=result,
        )

        return response_payload, conversation_id, turn_id

    @staticmethod
    def _build_response_payload(result: dict[str, Any]) -> dict[str, Any]:
        """Extract structured response from graph output."""
        metadata = result.get("metadata", {})
        if hasattr(metadata, "model_dump"):
            metadata = metadata.model_dump()
        elif hasattr(metadata, "dict"):
            metadata = metadata.dict()

        code = result.get("current_code", "") or result.get("code", "") or ""
        code_guard_feedback = result.get("code_guard_feedback", "") or ""
        explanation = result.get("plan", "") if code else ""

        if not code and code_guard_feedback:
            explanation = (
                "I could not generate executable code that passed validation.\n"
                f"Reason: {code_guard_feedback}"
            )
        else:
            final_messages = result.get("messages", [])
            if not explanation and final_messages:
                last_message = final_messages[-1]
                explanation = str(getattr(last_message, "content", ""))

        return {
            "is_safe": bool(metadata.get("is_safe", True)),
            "is_relevant": bool(metadata.get("is_relevant", True)),
            "code": code,
            "explanation": explanation,
            "metadata": metadata,
        }

    @staticmethod
    async def _persist_turn(
        session: AsyncSession,
        conversation: Any,
        conversation_id: str,
        question: str,
        response_payload: dict[str, Any],
        result: dict[str, Any],
    ) -> str:
        """Helper to persist a conversation turn in the database."""
        seq_no = await ConversationRepository.next_seq_no(session, conversation_id)
        if seq_no == 1 and (conversation.title or "").strip().lower() == "new conversation":
            conversation.title = ChatService._derive_conversation_title(question)
        
        turn = await ConversationRepository.create_turn(
            session=session,
            conversation_id=conversation_id,
            seq_no=seq_no,
            user_text=question,
            assistant_text=response_payload["explanation"],
            tool_events=[],
            metadata=response_payload.get("metadata", {}),
            code_snapshot=response_payload["code"],
        )
        await session.commit()
        return turn.id

    @staticmethod
    async def analyze_and_stream_turns(
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
    ):
        """Async generator that yields incremental analysis events (SSE-compatible)."""
        conversation, conversation_id, schema, table_name, data_path = await ChatService._preflight_check(
            session=session,
            user=user,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            question=question,
            table_name_override=table_name_override,
            active_schema_override=active_schema_override,
        )

        yield {"event": "status", "data": {"stage": "start", "message": "Starting analysis"}}

        memory_path = WorkspaceStorageService.build_agent_memory_path(user.username, workspace_id)
        graph = await langgraph_manager.get_graph(workspace_id, memory_path)

        input_state = InputSchema(
            messages=[HumanMessage(content=question)],
            active_schema=schema,
            previous_code=current_code,
            current_code=current_code,
            table_name=table_name,
            data_path=data_path,
            context=context or "",
        )
        thread_id = f"{user.id}:{workspace_id}:{conversation_id}"
        config = {
            "configurable": {
                "api_key": api_key,
                "thread_id": thread_id,
                "model": model,
            }
        }
        resolved_api_key = (api_key or "").strip() or (SecretStorageService.get_api_key(user.id) or "")
        config["configurable"]["api_key"] = resolved_api_key
        if not resolved_api_key:
            raise HTTPException(status_code=401, detail="API key not configured")

        aggregated: dict[str, Any] = {}
        async for step in graph.astream(input_state, config=config):
            for node_name, payload in step.items():
                if isinstance(payload, dict):
                    aggregated.update(payload)
                if node_name == "code_guard":
                    logprint(
                        "[V1 Chat] code_guard node",
                        level="INFO",
                        request_id=thread_id,
                        guard_status=aggregated.get("guard_status"),
                        retry_count=aggregated.get("code_guard_retries", 0),
                        feedback=aggregated.get("code_guard_feedback", ""),
                    )
                yield {"event": "node", "data": {"node": node_name, "message": f"{node_name} completed"}}

        # Final state merge if checkpointer is active
        try:
            final_state = await graph.aget_state(config)
            if getattr(final_state, "values", None):
                aggregated = final_state.values
        except Exception:
            pass

        response_payload = ChatService._build_response_payload(aggregated)
        logprint(
            "[V1 Chat] final response summary",
            level="INFO",
            request_id=thread_id,
            has_code=bool((response_payload.get("code", "") or "").strip()),
            code_len=len(response_payload.get("code", "") or ""),
            has_await_query=("await query(" in (response_payload.get("code", "") or "")),
            guard_status=aggregated.get("guard_status", ""),
            guard_feedback=aggregated.get("code_guard_feedback", ""),
        )
        
        # Persist once at the end
        turn_id = await ChatService._persist_turn(
            session=session,
            conversation=conversation,
            conversation_id=conversation_id,
            question=question,
            response_payload=response_payload,
            result=aggregated,
        )
        
        # Add IDs to payload for final UI update
        response_payload.update({
            "conversation_id": conversation_id,
            "turn_id": turn_id
        })
        
        yield {"event": "final", "data": response_payload}
