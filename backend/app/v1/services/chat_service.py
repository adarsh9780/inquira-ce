"""Workspace conversation chat analysis service.

Persists turns in app DB and uses per-workspace LangGraph checkpoint state.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Any
from typing import cast

import duckdb
from fastapi import HTTPException
from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from ...agent.graph import InputSchema
from ...services.code_executor import execute_code, get_workspace_run_exports
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
    def _build_run_wrapped_code(code: str, run_id: str) -> str:
        body = str(code or "").rstrip()
        if not body:
            return ""
        return f"set_active_run({run_id!r})\n{body}\n"

    @staticmethod
    async def _finalize_kernel_run(
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        run_id: str,
        question: str,
        generated_code: str,
        executed_code: str,
        stdout: str,
        stderr: str,
        execution_status: str,
        retry_count: int,
    ) -> None:
        finalize_payload = {
            "question": question,
            "generated_code": generated_code,
            "executed_code": executed_code,
            "stdout": stdout,
            "stderr": stderr,
            "execution_status": execution_status,
            "retry_count": int(retry_count),
        }
        finalize_code = (
            f"set_active_run({run_id!r})\n"
            f"finalize_run({run_id!r}, metadata={finalize_payload!r})\n"
        )
        await execute_code(
            code=finalize_code,
            timeout=30,
            working_dir=str(Path(workspace_duckdb_path).parent),
            workspace_id=workspace_id,
            workspace_duckdb_path=workspace_duckdb_path,
        )

    @staticmethod
    async def _execute_generated_code_with_retries(
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        generated_code: str,
        run_id: str,
        max_retries: int = 2,
    ) -> tuple[dict[str, Any], int, float, str]:
        retries = 0
        wrapped_code = ChatService._build_run_wrapped_code(generated_code, run_id)
        last_result: dict[str, Any] = {
            "success": True,
            "stdout": "",
            "stderr": "",
            "error": None,
            "result": None,
            "result_type": None,
            "result_kind": "none",
            "result_name": None,
            "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
            "artifacts": [],
        }
        started = time.perf_counter()
        while True:
            last_result = await execute_code(
                code=wrapped_code,
                timeout=90,
                working_dir=str(Path(workspace_duckdb_path).parent),
                workspace_id=workspace_id,
                workspace_duckdb_path=workspace_duckdb_path,
            )
            if bool(last_result.get("success")):
                break
            if retries >= max_retries:
                break
            retries += 1
        duration_ms = max(1, int((time.perf_counter() - started) * 1000))
        return last_result, retries, float(duration_ms), wrapped_code

    @staticmethod
    def _assemble_final_script(*, question: str, generated_code: str, run_id: str) -> str:
        lines = [
            "# Inquira reproducible script",
            f"# run_id: {run_id}",
            f"# question: {question}",
            "",
            "# NOTE: Inquira runtime provides these helpers in-kernel:",
            "# set_active_run, export_dataframe, export_figure, export_scalar, finalize_run",
            f"set_active_run({run_id!r})",
            "",
            generated_code.rstrip(),
            "",
            f"finalize_run({run_id!r})",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def _build_inline_artifact_fallback(
        *,
        run_id: str,
        execution_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        result = execution_result.get("result")
        result_type = str(execution_result.get("result_type") or "").lower()
        if result_type != "dataframe":
            return []
        if not isinstance(result, dict):
            return []
        columns = result.get("columns")
        rows = result.get("data")
        if not isinstance(columns, list) or not isinstance(rows, list):
            return []
        return [
            {
                "artifact_id": None,
                "run_id": run_id,
                "kind": "dataframe",
                "pointer": None,
                "logical_name": "result",
                "row_count": len(rows),
                "schema": [{"name": str(c), "dtype": ""} for c in columns],
                "preview_rows": rows,
                "created_at": "",
                "expires_at": "",
                "status": "ready",
                "error": None,
                "table_name": None,
            }
        ]

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
    async def _read_live_table_columns(duckdb_path: str, table_name: str) -> list[dict[str, Any]]:
        """Read authoritative column names/types from workspace DuckDB."""

        def _read() -> list[dict[str, Any]]:
            con = duckdb.connect(duckdb_path, read_only=True)
            try:
                rows = con.execute(f'DESCRIBE "{table_name}"').fetchall()
                return [
                    {
                        "name": str(row[0]),
                        "dtype": str(row[1]),
                        "description": "",
                        "samples": [],
                    }
                    for row in rows
                ]
            finally:
                con.close()

        try:
            return await asyncio.to_thread(_read)
        except Exception:
            return []

    @staticmethod
    def _merge_schema_with_live_columns(
        schema: dict[str, Any] | None,
        table_name: str,
        live_columns: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Prefer live DuckDB columns while preserving optional schema descriptions."""
        base = dict(schema or {})
        raw_columns = base.get("columns", [])
        existing_columns = raw_columns if isinstance(raw_columns, list) else []
        by_name = {
            str(col.get("name", "")).strip().lower(): col
            for col in existing_columns
            if isinstance(col, dict) and str(col.get("name", "")).strip()
        }

        merged_columns: list[dict[str, Any]] = []
        for live in live_columns:
            name = str(live.get("name", "")).strip()
            if not name:
                continue
            old = by_name.get(name.lower(), {})
            merged_columns.append(
                {
                    "name": name,
                    "dtype": str(live.get("dtype") or old.get("dtype") or old.get("type") or "VARCHAR"),
                    "description": str(old.get("description", "")),
                    "samples": old.get("samples", []) if isinstance(old.get("samples", []), list) else [],
                }
            )

        return {
            "table_name": table_name,
            "context": str(base.get("context", "")),
            "columns": merged_columns,
        }

    @staticmethod
    def _merge_override_metadata(
        schema: dict[str, Any] | None,
        active_schema_override: dict[str, Any] | None,
        table_name: str,
    ) -> dict[str, Any] | None:
        """Merge optional frontend context/description hints without replacing backend columns."""
        if not schema or not isinstance(schema, dict):
            return schema
        if not active_schema_override or not isinstance(active_schema_override, dict):
            return schema

        override_table = str(active_schema_override.get("table_name", "")).strip().lower()
        if override_table and override_table != table_name:
            return schema

        merged = dict(schema)
        override_context = active_schema_override.get("context")
        if isinstance(override_context, str):
            merged["context"] = override_context

        raw_columns = merged.get("columns", [])
        schema_columns = raw_columns if isinstance(raw_columns, list) else []
        override_raw_columns = active_schema_override.get("columns", [])
        override_columns = override_raw_columns if isinstance(override_raw_columns, list) else []
        override_by_name = {
            str(col.get("name", "")).strip().lower(): col
            for col in override_columns
            if isinstance(col, dict) and str(col.get("name", "")).strip()
        }

        enriched_columns: list[dict[str, Any]] = []
        for col in schema_columns:
            if not isinstance(col, dict):
                continue
            name = str(col.get("name", "")).strip()
            if not name:
                continue
            candidate = dict(col)
            override = override_by_name.get(name.lower())
            if isinstance(override, dict):
                if isinstance(override.get("description"), str):
                    candidate["description"] = override["description"]
                if isinstance(override.get("samples"), list):
                    candidate["samples"] = override["samples"]
            enriched_columns.append(candidate)
        merged["columns"] = enriched_columns
        return merged

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
        workspace_duckdb_path = str(workspace.duckdb_path)

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
                if selected_dataset.schema_path:
                    try:
                        schema = await ChatService._load_schema(selected_dataset.schema_path)
                    except HTTPException as exc:
                        if exc.status_code != 404:
                            raise
            else:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "Dataset preflight failed: selected table was not found in this workspace. "
                        "Re-select your dataset and try again."
                    ),
                )

        if schema is None:
            latest_dataset = await DatasetRepository.get_latest_for_workspace(session, workspace_id)
            if latest_dataset is not None:
                table_name = latest_dataset.table_name
                if latest_dataset.schema_path:
                    try:
                        schema = await ChatService._load_schema(latest_dataset.schema_path)
                    except HTTPException as exc:
                        if exc.status_code != 404:
                            raise

        schema = ChatService._merge_override_metadata(
            schema,
            active_schema_override,
            table_name or "",
        )

        if table_name:
            live_columns = await ChatService._read_live_table_columns(
                workspace.duckdb_path,
                table_name,
            )
            if live_columns:
                schema = ChatService._merge_schema_with_live_columns(
                    schema,
                    table_name,
                    live_columns,
                )

        if schema is None:
            schema = {"table_name": table_name or "", "columns": []}

        if conversation_id is None:
            raise HTTPException(status_code=500, detail="Conversation initialization failed")

        return conversation, conversation_id, schema, table_name or "", workspace_duckdb_path

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
        run_id = str(uuid.uuid4())
        response_payload["run_id"] = run_id
        response_payload["execution"] = None
        response_payload["artifacts"] = []
        response_payload["final_script_artifact_id"] = None

        code_to_execute = str(response_payload.get("code") or "").strip()
        if code_to_execute:
            execution_result, retry_count, duration_ms, executed_code = (
                await ChatService._execute_generated_code_with_retries(
                    workspace_id=workspace_id,
                    workspace_duckdb_path=data_path,
                    generated_code=code_to_execute,
                    run_id=run_id,
                    max_retries=2,
                )
            )
            await ChatService._finalize_kernel_run(
                workspace_id=workspace_id,
                workspace_duckdb_path=data_path,
                run_id=run_id,
                question=question,
                generated_code=code_to_execute,
                executed_code=executed_code,
                stdout=str(execution_result.get("stdout") or ""),
                stderr=str(execution_result.get("stderr") or execution_result.get("error") or ""),
                execution_status="success" if bool(execution_result.get("success")) else "failed",
                retry_count=retry_count,
            )
            artifacts = [
                item
                for item in (execution_result.get("artifacts") or [])
                if isinstance(item, dict)
            ]
            if not artifacts:
                artifacts = await get_workspace_run_exports(
                    workspace_id=workspace_id,
                    run_id=run_id,
                )
            if not artifacts:
                artifacts = ChatService._build_inline_artifact_fallback(
                    run_id=run_id,
                    execution_result=execution_result,
                )
            response_payload["execution"] = {
                "status": "success" if bool(execution_result.get("success")) else "failed",
                "stdout": str(execution_result.get("stdout") or ""),
                "stderr": str(execution_result.get("stderr") or execution_result.get("error") or ""),
                "retry_count": int(retry_count),
                "duration_ms": int(duration_ms),
            }
            response_payload["artifacts"] = artifacts
            response_payload["final_script_artifact_id"] = None

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
            "run_id": None,
            "execution": None,
            "artifacts": [],
            "final_script_artifact_id": None,
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
            tool_events=[{"type": "artifact", "data": item} for item in (response_payload.get("artifacts") or [])],
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
        run_id = str(uuid.uuid4())
        response_payload["run_id"] = run_id
        response_payload["execution"] = None
        response_payload["artifacts"] = []
        response_payload["final_script_artifact_id"] = None
        code_to_execute = str(response_payload.get("code") or "").strip()
        if code_to_execute:
            execution_result, retry_count, duration_ms, executed_code = (
                await ChatService._execute_generated_code_with_retries(
                    workspace_id=workspace_id,
                    workspace_duckdb_path=data_path,
                    generated_code=code_to_execute,
                    run_id=run_id,
                    max_retries=2,
                )
            )
            await ChatService._finalize_kernel_run(
                workspace_id=workspace_id,
                workspace_duckdb_path=data_path,
                run_id=run_id,
                question=question,
                generated_code=code_to_execute,
                executed_code=executed_code,
                stdout=str(execution_result.get("stdout") or ""),
                stderr=str(execution_result.get("stderr") or execution_result.get("error") or ""),
                execution_status="success" if bool(execution_result.get("success")) else "failed",
                retry_count=retry_count,
            )
            artifacts = [
                item
                for item in (execution_result.get("artifacts") or [])
                if isinstance(item, dict)
            ]
            if not artifacts:
                artifacts = await get_workspace_run_exports(
                    workspace_id=workspace_id,
                    run_id=run_id,
                )
            if not artifacts:
                artifacts = ChatService._build_inline_artifact_fallback(
                    run_id=run_id,
                    execution_result=execution_result,
                )
            response_payload["artifacts"] = artifacts
            response_payload["final_script_artifact_id"] = None
            response_payload["execution"] = {
                "status": "success" if bool(execution_result.get("success")) else "failed",
                "stdout": str(execution_result.get("stdout") or ""),
                "stderr": str(execution_result.get("stderr") or execution_result.get("error") or ""),
                "retry_count": int(retry_count),
                "duration_ms": int(duration_ms),
            }
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
