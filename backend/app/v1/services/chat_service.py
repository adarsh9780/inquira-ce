"""Workspace conversation chat analysis service.

Persists turns in app DB and uses per-workspace LangGraph checkpoint state.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
import uuid
from pathlib import Path
from typing import Any
from typing import Callable
from typing import cast

import duckdb
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...agent.events import reset_agent_event_emitter, set_agent_event_emitter
from ...agent.registry import get_agent_bindings
from ...services.code_executor import execute_code, get_workspace_run_exports
from ...services.output_capture import (
    build_auto_capture_result_code,
    build_run_wrapped_code,
    normalize_output_contract,
)
from ...services.llm_provider_catalog import (
    model_supports_vision,
    normalize_llm_provider,
    provider_default_base_url,
    provider_requires_api_key,
)
from ...services.llm_runtime_config import load_llm_runtime_config
from ..repositories.conversation_repository import ConversationRepository
from ..repositories.dataset_repository import DatasetRepository
from ..repositories.preferences_repository import PreferencesRepository
from ..repositories.workspace_repository import WorkspaceRepository
from .conversation_service import ConversationService
from .secret_storage_service import SecretStorageService
from .workspace_storage_service import WorkspaceStorageService
from ...core.logger import logprint

LegacySetStreamEmitter = Callable[[Callable[[str, str], None] | None], Any]
LegacyResetStreamEmitter = Callable[[Any], None]
set_legacy_stream_token_emitter: LegacySetStreamEmitter | None
reset_legacy_stream_token_emitter: LegacyResetStreamEmitter | None

try:
    from ...agent.graph import (
        reset_stream_token_emitter as reset_legacy_stream_token_emitter,
    )
    from ...agent.graph import (
        set_stream_token_emitter as set_legacy_stream_token_emitter,
    )
except Exception:  # pragma: no cover - legacy fallback only
    set_legacy_stream_token_emitter = None
    reset_legacy_stream_token_emitter = None


class _AttrAccessDict(dict[str, Any]):
    """Dict with attribute access for compatibility with legacy graph mocks."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


class ChatService:
    """Runs analysis and persists chat turns."""

    @staticmethod
    def _known_columns_thread_id(user_id: str, workspace_id: str) -> str:
        return f"{user_id}:{workspace_id}:known_columns"

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
    def _normalize_output_contract(contract: Any) -> list[dict[str, str]]:
        return normalize_output_contract(contract)

    @staticmethod
    def _as_plain_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            dumped = value.model_dump()
            if isinstance(dumped, dict):
                return dumped
            return {}
        if hasattr(value, "dict"):
            dumped = value.dict()
            if isinstance(dumped, dict):
                return dumped
            return {}
        return {}

    @staticmethod
    def _extract_last_message_text(messages: Any) -> str:
        if not isinstance(messages, list) or not messages:
            return ""
        last_message = messages[-1]
        content = getattr(last_message, "content", None)
        if content is None and isinstance(last_message, dict):
            content = last_message.get("content")
        return str(content or "").strip()

    @staticmethod
    def _coerce_input_state_for_graph(input_state: Any) -> Any:
        if isinstance(input_state, dict) and not isinstance(input_state, _AttrAccessDict):
            return _AttrAccessDict(input_state)
        return input_state

    @staticmethod
    async def _resolve_llm_preferences(session: AsyncSession, user_id: str) -> dict[str, Any]:
        runtime = load_llm_runtime_config()
        try:
            prefs = await PreferencesRepository.get_or_create(session, user_id)
        except Exception:  # noqa: BLE001
            provider = normalize_llm_provider(runtime.provider)
            base_url = runtime.base_url if provider == "openrouter" else provider_default_base_url(provider)
            return {
                "provider": provider,
                "base_url": base_url,
                "requires_api_key": provider_requires_api_key(provider),
                "selected_lite_model": runtime.lite_model,
                "selected_main_model": runtime.default_model,
                "selected_coding_model": runtime.default_model,
            }

        provider = normalize_llm_provider(getattr(prefs, "llm_provider", runtime.provider))
        base_url = runtime.base_url if provider == "openrouter" else provider_default_base_url(provider)
        selected_lite_model = str(
            getattr(prefs, "selected_lite_model", runtime.lite_model) or runtime.lite_model
        ).strip()
        return {
            "provider": provider,
            "base_url": base_url,
            "requires_api_key": provider_requires_api_key(provider),
            "selected_lite_model": selected_lite_model,
            "selected_main_model": str(getattr(prefs, "selected_model", runtime.default_model) or runtime.default_model).strip(),
            "selected_coding_model": str(
                getattr(prefs, "selected_coding_model", getattr(prefs, "selected_model", runtime.default_model))
                or getattr(prefs, "selected_model", runtime.default_model)
                or runtime.default_model
            ).strip(),
        }

    @staticmethod
    def _normalize_known_columns(raw: Any, max_items: int = 50) -> list[dict[str, str]]:
        if not isinstance(raw, list):
            return []
        normalized: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            table_name = str(item.get("table_name") or "").strip()
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            dedupe = f"{table_name.lower()}::{name.lower()}"
            if dedupe in seen:
                continue
            seen.add(dedupe)
            normalized.append(
                {
                    "table_name": table_name,
                    "name": name,
                    "dtype": str(item.get("dtype") or "").strip(),
                    "description": str(item.get("description") or "").strip(),
                }
            )
            if len(normalized) >= max_items:
                break
        return normalized

    @staticmethod
    async def _load_workspace_known_columns(
        *,
        graph: Any,
        user_id: str,
        workspace_id: str,
    ) -> list[dict[str, str]]:
        if not hasattr(graph, "aget_state"):
            return []
        cfg = {
            "configurable": {
                "thread_id": ChatService._known_columns_thread_id(user_id, workspace_id),
            }
        }
        try:
            state = await graph.aget_state(cfg)
        except Exception:
            return []
        values = getattr(state, "values", None)
        if not isinstance(values, dict):
            return []
        return ChatService._normalize_known_columns(values.get("known_columns"))

    @staticmethod
    async def _save_workspace_known_columns(
        *,
        graph: Any,
        user_id: str,
        workspace_id: str,
        known_columns: Any,
    ) -> None:
        if not hasattr(graph, "aupdate_state"):
            return
        normalized = ChatService._normalize_known_columns(known_columns)
        cfg = {
            "configurable": {
                "thread_id": ChatService._known_columns_thread_id(user_id, workspace_id),
            }
        }
        try:
            await graph.aupdate_state(cfg, {"known_columns": normalized})
        except Exception:
            return

    @staticmethod
    def _build_node_stream_payload(
        node_name: str,
        payload: Any,
        aggregated: dict[str, Any],
    ) -> dict[str, Any]:
        node = str(node_name or "").strip()
        payload_dict = ChatService._as_plain_dict(payload)
        aggregated_dict = ChatService._as_plain_dict(aggregated)

        payload_meta = ChatService._as_plain_dict(payload_dict.get("metadata"))
        aggregated_meta = ChatService._as_plain_dict(aggregated_dict.get("metadata"))
        metadata = dict(aggregated_meta)
        metadata.update(payload_meta)

        event_payload: dict[str, Any] = {
            "node": node,
            "message": f"{node} completed",
            "output": "",
        }

        if node == "check_safety":
            decision = metadata.get("is_safe")
            event_payload["decision"] = "safe" if bool(decision) else "unsafe"
            event_payload["output"] = str(metadata.get("safety_reasoning") or "").strip()
            return event_payload

        if node == "check_relevancy":
            decision = metadata.get("is_relevant")
            event_payload["decision"] = "relevant" if bool(decision) else "irrelevant"
            event_payload["output"] = str(metadata.get("relevancy_reasoning") or "").strip()
            return event_payload

        if node == "require_code":
            require_code = metadata.get("require_code")
            event_payload["decision"] = "code" if bool(require_code) else "noncode"
            if require_code is True:
                event_payload["output"] = "Code generation is required for this request."
            elif require_code is False:
                event_payload["output"] = "A direct language response is enough; code is not required."
            return event_payload

        if node == "create_plan":
            event_payload["output"] = str(
                payload_dict.get("plan")
                or aggregated_dict.get("plan")
                or ""
            ).strip()
            return event_payload

        if node in {"code_generator", "retry_code_generator"}:
            event_payload["output"] = str(
                payload_dict.get("code")
                or payload_dict.get("current_code")
                or aggregated_dict.get("current_code")
                or aggregated_dict.get("code")
                or ""
            ).strip()
            return event_payload

        if node == "code_guard":
            status = str(
                payload_dict.get("guard_status")
                or aggregated_dict.get("guard_status")
                or ""
            ).strip()
            feedback = str(
                payload_dict.get("code_guard_feedback")
                or aggregated_dict.get("code_guard_feedback")
                or ""
            ).strip()
            if status:
                event_payload["decision"] = status
            event_payload["output"] = feedback
            return event_payload

        if node == "explain_code":
            event_payload["output"] = str(
                payload_dict.get("final_explanation")
                or aggregated_dict.get("final_explanation")
                or ChatService._extract_last_message_text(payload_dict.get("messages"))
                or ""
            ).strip()
            return event_payload

        if node in {"noncode_generator", "general_purpose", "unsafe_rejector"}:
            event_payload["output"] = ChatService._extract_last_message_text(
                payload_dict.get("messages")
            )
            return event_payload

        return event_payload

    @staticmethod
    def _build_auto_capture_result_code(output_contract: list[dict[str, str]]) -> str:
        return build_auto_capture_result_code(output_contract)

    @staticmethod
    def _build_run_wrapped_code(code: str, run_id: str, output_contract: list[dict[str, str]]) -> str:
        return build_run_wrapped_code(code, run_id, output_contract)

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
        output_contract: list[dict[str, str]],
        max_retries: int = 2,
    ) -> tuple[dict[str, Any], int, float, str]:
        retries = 0
        wrapped_code = ChatService._build_run_wrapped_code(generated_code, run_id, output_contract)
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
            "# Inquira portable script",
            "# This code is designed to run outside Inquira without runtime helpers.",
            f"# inquira_run_id: {run_id}",
            f"# question: {question}",
            "",
            generated_code.rstrip(),
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
                "preview_rows": [],
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
                    "aliases": old.get("aliases", []) if isinstance(old.get("aliases", []), list) else [],
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
                if isinstance(override.get("aliases"), list):
                    candidate["aliases"] = override["aliases"]
            enriched_columns.append(candidate)
        merged["columns"] = enriched_columns
        return merged

    @staticmethod
    def _merge_workspace_schema_tables(
        tables: list[dict[str, Any]],
        preferred_table_name: str | None,
    ) -> dict[str, Any]:
        normalized_tables: list[dict[str, Any]] = []
        seen: set[str] = set()
        for table in tables:
            if not isinstance(table, dict):
                continue
            table_name = str(table.get("table_name") or "").strip()
            if not table_name:
                continue
            dedupe = table_name.lower()
            if dedupe in seen:
                continue
            seen.add(dedupe)
            normalized_tables.append(
                {
                    "table_name": table_name,
                    "context": str(table.get("context") or ""),
                    "columns": table.get("columns") if isinstance(table.get("columns"), list) else [],
                }
            )

        preferred_table = str(preferred_table_name or "").strip()
        return {
            "table_name": preferred_table,
            "tables": normalized_tables,
        }

    @staticmethod
    async def _load_workspace_schema(
        *,
        session: AsyncSession,
        workspace_id: str,
        duckdb_path: str,
        preferred_table_name: str | None,
        active_schema_override: dict[str, Any] | None,
    ) -> dict[str, Any]:
        datasets = await DatasetRepository.list_for_workspace(session, workspace_id)
        tables: list[dict[str, Any]] = []
        for dataset in datasets:
            table_name = str(getattr(dataset, "table_name", "") or "").strip()
            if not table_name:
                continue
            schema: dict[str, Any] | None = None
            schema_path = str(getattr(dataset, "schema_path", "") or "").strip()
            if schema_path:
                try:
                    schema = await ChatService._load_schema(schema_path)
                except HTTPException as exc:
                    if exc.status_code != 404:
                        raise
            live_columns = await ChatService._read_live_table_columns(duckdb_path, table_name)
            if live_columns:
                schema = ChatService._merge_schema_with_live_columns(schema, table_name, live_columns)
            if schema is None:
                schema = {"table_name": table_name, "context": "", "columns": []}
            schema = ChatService._merge_override_metadata(schema, active_schema_override, table_name) or schema
            tables.append(schema)

        if not tables and active_schema_override and isinstance(active_schema_override, dict):
            override_table = str(active_schema_override.get("table_name") or "").strip()
            if override_table:
                tables.append(
                    ChatService._merge_override_metadata(
                        {"table_name": override_table, "context": "", "columns": []},
                        active_schema_override,
                        override_table,
                    )
                    or {"table_name": override_table, "context": "", "columns": []}
                )

        return ChatService._merge_workspace_schema_tables(tables, preferred_table_name)

    @staticmethod
    def _normalize_chat_attachments(raw: Any) -> list[dict[str, str]]:
        if not isinstance(raw, list):
            return []
        normalized: list[dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            attachment_id = str(item.get("attachment_id") or "").strip()
            filename = str(item.get("filename") or "").strip()
            media_type = str(item.get("media_type") or "").strip()
            data_base64 = str(item.get("data_base64") or "").strip()
            if not attachment_id or not filename or not media_type or not data_base64:
                continue
            normalized.append(
                {
                    "attachment_id": attachment_id,
                    "filename": filename,
                    "media_type": media_type,
                    "data_base64": data_base64,
                }
            )
        return normalized

    @staticmethod
    def _workspace_db_missing_detail(duckdb_path: str) -> str:
        return (
            "Workspace database is missing.\n"
            f"Expected path: {duckdb_path}\n"
            "Please re-create the workspace data by selecting the original dataset again."
        )

    @staticmethod
    def _should_enforce_workspace_db_presence(duckdb_path: str) -> bool:
        parts = {part.lower() for part in Path(str(duckdb_path or "")).expanduser().parts}
        return ".inquira" in parts and "workspaces" in parts

    @staticmethod
    def _ensure_workspace_db_exists(duckdb_path: str) -> None:
        resolved = Path(str(duckdb_path or "")).expanduser()
        if resolved.exists():
            return
        if not ChatService._should_enforce_workspace_db_presence(str(resolved)):
            return
        raise HTTPException(
            status_code=409,
            detail=ChatService._workspace_db_missing_detail(str(resolved)),
        )

    @staticmethod
    async def _preflight_check(
        session: AsyncSession,
        user,
        workspace_id: str,
        conversation_id: str | None,
        question: str,
        table_name_override: str | None,
        preferred_table_name: str | None,
        active_schema_override: dict[str, Any] | None,
    ) -> tuple[Any, str, dict[str, Any], str, str]:
        """Shared logic to validate workspace, conversation, and dataset before analysis."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        workspace_duckdb_path = str(workspace.duckdb_path)
        ChatService._ensure_workspace_db_exists(workspace_duckdb_path)

        conversation = None
        if conversation_id:
            conversation = await ConversationRepository.get_conversation(session, conversation_id)
            if conversation and conversation.workspace_id != workspace_id:
                logprint(f"⚠️ Conversation {conversation_id} belongs to different workspace. Resetting.")
                conversation = None

        if conversation is None:
            created_conversation = await ConversationService.create_conversation(
                session=session,
                principal_id=user.id,
                workspace_id=workspace_id,
                title=ChatService._derive_conversation_title(question),
            )
            conversation = created_conversation
            conversation_id = created_conversation.id
            logprint(f"✅ Created new conversation {conversation_id} for workspace {workspace_id}")

        schema: dict[str, Any] | None = None
        table_name: str | None = None

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
        elif preferred_table_name and str(preferred_table_name).strip():
            preferred = _normalize_table_name(str(preferred_table_name))
            selected_dataset = await DatasetRepository.get_for_workspace_table(
                session=session,
                workspace_id=workspace_id,
                table_name=preferred,
            )
            if selected_dataset is not None:
                table_name = selected_dataset.table_name
        else:
            datasets = await DatasetRepository.list_for_workspace(session, workspace_id)
            if len(datasets) == 1:
                table_name = str(datasets[0].table_name or "").strip() or None

        schema = await ChatService._load_workspace_schema(
            session=session,
            workspace_id=workspace_id,
            duckdb_path=workspace_duckdb_path,
            preferred_table_name=table_name,
            active_schema_override=active_schema_override,
        )

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
        preferred_table_name: str | None = None,
        active_schema_override: dict[str, Any] | None = None,
        attachments: list[dict[str, str]] | None = None,
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
            preferred_table_name=preferred_table_name,
            active_schema_override=active_schema_override,
        )

        bindings = get_agent_bindings()
        memory_path = WorkspaceStorageService.build_agent_memory_path(user.username, workspace_id)
        graph = await langgraph_manager.get_graph(workspace_id, memory_path)
        known_columns = await ChatService._load_workspace_known_columns(
            graph=graph,
            user_id=str(user.id),
            workspace_id=workspace_id,
        )

        normalized_attachments = ChatService._normalize_chat_attachments(attachments)
        input_state = bindings.build_input_state(
            question=question,
            schema=schema,
            current_code=current_code,
            table_name=table_name,
            data_path=data_path,
            context=context or "",
            workspace_id=workspace_id,
            user_id=str(user.id),
            scratchpad_path=str(
                WorkspaceStorageService.build_scratchpad_db_path(user.username, workspace_id)
            ),
            known_columns=known_columns,
            attachments=normalized_attachments,
        )
        input_state = ChatService._coerce_input_state_for_graph(input_state)
        thread_id = f"{user.id}:{workspace_id}:{conversation_id}"
        config = {
            "configurable": {
                "api_key": api_key,
                "thread_id": thread_id,
                "model": model,
            }
        }
        llm_prefs = await ChatService._resolve_llm_preferences(session, str(user.id))
        resolved_api_key = (api_key or "").strip() or (
            SecretStorageService.get_api_key(user.id, provider=llm_prefs["provider"]) or ""
        )
        config["configurable"]["api_key"] = resolved_api_key
        config["configurable"]["provider"] = llm_prefs["provider"]
        config["configurable"]["base_url"] = llm_prefs["base_url"]
        config["configurable"]["lite_model"] = llm_prefs["selected_lite_model"]
        config["configurable"]["default_model"] = llm_prefs["selected_main_model"]
        config["configurable"]["coding_model"] = llm_prefs.get("selected_coding_model") or llm_prefs["selected_main_model"]
        if llm_prefs["requires_api_key"] and not resolved_api_key:
            raise HTTPException(status_code=401, detail="API key not configured")
        if normalized_attachments and not model_supports_vision(llm_prefs["provider"], model):
            raise HTTPException(
                status_code=400,
                detail="The selected model does not support image attachments.",
            )

        result = await graph.ainvoke(input_state, config=config)
        await ChatService._save_workspace_known_columns(
            graph=graph,
            user_id=str(user.id),
            workspace_id=workspace_id,
            known_columns=result.get("known_columns"),
        )
        response_payload = ChatService._build_response_payload(result)
        run_id = str(response_payload.get("run_id") or result.get("run_id") or uuid.uuid4())
        response_payload["run_id"] = run_id
        response_payload["execution"] = response_payload.get("execution")
        response_payload["artifacts"] = response_payload.get("artifacts") or []
        response_payload["final_script_artifact_id"] = response_payload.get("final_script_artifact_id")

        code_to_execute = str(response_payload.get("code") or "").strip()
        if code_to_execute and response_payload.get("execution") is None:
            execution_result, retry_count, duration_ms, executed_code = (
                await ChatService._execute_generated_code_with_retries(
                    workspace_id=workspace_id,
                    workspace_duckdb_path=data_path,
                    generated_code=code_to_execute,
                    run_id=run_id,
                    output_contract=response_payload.get("output_contract") or [],
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
        elif code_to_execute and response_payload.get("execution") is not None:
            execution_result = response_payload.get("execution") or {}
            executed_code = str(result.get("final_executed_code") or code_to_execute)
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
                retry_count=int(execution_result.get("retry_count") or 0),
            )

        turn_id = await ChatService._persist_turn(
            session=session,
            conversation=conversation,
            conversation_id=conversation_id,
            question=question,
            attachments=normalized_attachments,
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
        if not isinstance(metadata, dict):
            metadata = {}

        route = str(result.get("route") or "").strip().lower()
        if route == "unsafe":
            metadata.setdefault("is_safe", False)
            metadata.setdefault("is_relevant", False)
        elif route == "general_chat":
            metadata.setdefault("is_safe", True)
            metadata.setdefault("is_relevant", False)
        elif route:
            metadata.setdefault("is_safe", True)
            metadata.setdefault("is_relevant", True)

        code = (
            result.get("final_code")
            or result.get("current_code", "")
            or result.get("code", "")
            or ""
        )
        code_guard_feedback = result.get("code_guard_feedback", "") or ""
        result_explanation = str(
            result.get("result_explanation")
            or result.get("final_explanation")
            or result.get("answer")
            or ""
        ).strip()
        code_explanation = str(result.get("code_explanation") or "").strip()
        explanation = result_explanation if code else ""

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
            if code and not explanation:
                explanation = code_explanation or str(result.get("plan", "") or "").strip()

        metadata["result_explanation"] = result_explanation or explanation
        metadata["code_explanation"] = code_explanation
        metadata["tables_used"] = [
            str(item).strip()
            for item in (metadata.get("tables_used") or [])
            if str(item).strip()
        ]
        metadata["join_keys"] = [
            str(item).strip()
            for item in (metadata.get("join_keys") or [])
            if str(item).strip()
        ]
        metadata["joins_used"] = bool(metadata.get("joins_used"))

        execution_payload = result.get("final_execution")
        normalized_execution = None
        if isinstance(execution_payload, dict):
            normalized_execution = {
                "status": "success" if bool(execution_payload.get("success")) else "failed",
                "stdout": str(execution_payload.get("stdout") or ""),
                "stderr": str(
                    execution_payload.get("stderr")
                    or execution_payload.get("error")
                    or ""
                ),
                "retry_count": int(execution_payload.get("retry_count") or 0),
                "duration_ms": int(execution_payload.get("duration_ms") or 0),
                "success": bool(execution_payload.get("success")),
            }

        return {
            "is_safe": bool(metadata.get("is_safe", True)),
            "is_relevant": bool(metadata.get("is_relevant", True)),
            "code": code,
            "explanation": explanation,
            "result_explanation": result_explanation or explanation,
            "code_explanation": code_explanation,
            "metadata": metadata,
            "output_contract": ChatService._normalize_output_contract(result.get("output_contract")),
            "run_id": str(result.get("run_id") or "") or None,
            "execution": normalized_execution,
            "artifacts": [
                item for item in (result.get("final_artifacts") or []) if isinstance(item, dict)
            ],
            "final_script_artifact_id": None,
        }

    @staticmethod
    async def _persist_turn(
        session: AsyncSession,
        conversation: Any,
        conversation_id: str,
        question: str,
        attachments: list[dict[str, str]] | None,
        response_payload: dict[str, Any],
        result: dict[str, Any],
    ) -> str:
        """Helper to persist a conversation turn in the database."""
        seq_no = await ConversationRepository.next_seq_no(session, conversation_id)
        if seq_no == 1 and (conversation.title or "").strip().lower() == "new conversation":
            conversation.title = ChatService._derive_conversation_title(question)
        
        metadata = dict(response_payload.get("metadata", {}) or {})
        metadata["user_attachments"] = attachments or []

        turn = await ConversationRepository.create_turn(
            session=session,
            conversation_id=conversation_id,
            seq_no=seq_no,
            user_text=question,
            assistant_text=response_payload["explanation"],
            tool_events=[{"type": "artifact", "data": item} for item in (response_payload.get("artifacts") or [])],
            metadata=metadata,
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
        preferred_table_name: str | None = None,
        active_schema_override: dict[str, Any] | None = None,
        attachments: list[dict[str, str]] | None = None,
        api_key: str | None = None,
    ):
        """Async generator that yields incremental analysis events (SSE-compatible)."""
        event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        active_emitter_token = None
        active_legacy_emitter_token = None
        active_agent_event_token = None
        bindings = get_agent_bindings()

        def queue_event(event: str, data: dict[str, Any]) -> None:
            event_queue.put_nowait({"event": event, "data": data})

        async def run_pipeline() -> None:
            nonlocal active_emitter_token, active_legacy_emitter_token, active_agent_event_token, bindings
            try:
                conversation, resolved_conversation_id, schema, table_name, data_path = (
                    await ChatService._preflight_check(
                        session=session,
                        user=user,
                        workspace_id=workspace_id,
                        conversation_id=conversation_id,
                        question=question,
                        table_name_override=table_name_override,
                        preferred_table_name=preferred_table_name,
                        active_schema_override=active_schema_override,
                    )
                )

                queue_event("status", {"stage": "start", "message": "Starting analysis"})

                memory_path = WorkspaceStorageService.build_agent_memory_path(user.username, workspace_id)
                graph = await langgraph_manager.get_graph(workspace_id, memory_path)
                known_columns = await ChatService._load_workspace_known_columns(
                    graph=graph,
                    user_id=str(user.id),
                    workspace_id=workspace_id,
                )

                normalized_attachments = ChatService._normalize_chat_attachments(attachments)
                input_state = bindings.build_input_state(
                    question=question,
                    schema=schema,
                    current_code=current_code,
                    table_name=table_name,
                    data_path=data_path,
                    context=context or "",
                    workspace_id=workspace_id,
                    user_id=str(user.id),
                    scratchpad_path=str(
                        WorkspaceStorageService.build_scratchpad_db_path(user.username, workspace_id)
                    ),
                    known_columns=known_columns,
                    attachments=normalized_attachments,
                )
                input_state = ChatService._coerce_input_state_for_graph(input_state)
                thread_id = f"{user.id}:{workspace_id}:{resolved_conversation_id}"
                config = {
                    "configurable": {
                        "api_key": api_key,
                        "thread_id": thread_id,
                        "model": model,
                    }
                }
                llm_prefs = await ChatService._resolve_llm_preferences(session, str(user.id))
                resolved_api_key = (api_key or "").strip() or (
                    SecretStorageService.get_api_key(user.id, provider=llm_prefs["provider"]) or ""
                )
                config["configurable"]["api_key"] = resolved_api_key
                config["configurable"]["provider"] = llm_prefs["provider"]
                config["configurable"]["base_url"] = llm_prefs["base_url"]
                config["configurable"]["lite_model"] = llm_prefs["selected_lite_model"]
                config["configurable"]["default_model"] = llm_prefs["selected_main_model"]
                config["configurable"]["coding_model"] = llm_prefs.get("selected_coding_model") or llm_prefs["selected_main_model"]
                if llm_prefs["requires_api_key"] and not resolved_api_key:
                    raise HTTPException(status_code=401, detail="API key not configured")
                if normalized_attachments and not model_supports_vision(llm_prefs["provider"], model):
                    raise HTTPException(
                        status_code=400,
                        detail="The selected model does not support image attachments.",
                    )

                def emit_token(node_name: str, text: str) -> None:
                    queue_event("token", {"node": node_name, "text": text})

                if callable(bindings.set_stream_token_emitter):
                    active_emitter_token = bindings.set_stream_token_emitter(emit_token)
                if callable(set_legacy_stream_token_emitter):
                    active_legacy_emitter_token = set_legacy_stream_token_emitter(emit_token)
                active_agent_event_token = set_agent_event_emitter(
                    lambda event, data: queue_event(event, data)
                )

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
                        queue_event(
                            "node",
                            ChatService._build_node_stream_payload(
                                node_name=node_name,
                                payload=payload,
                                aggregated=aggregated,
                            ),
                        )

                # Final state merge if checkpointer is active
                try:
                    final_state = await graph.aget_state(config)
                    if getattr(final_state, "values", None):
                        aggregated = final_state.values
                except Exception:
                    pass

                await ChatService._save_workspace_known_columns(
                    graph=graph,
                    user_id=str(user.id),
                    workspace_id=workspace_id,
                    known_columns=aggregated.get("known_columns"),
                )

                response_payload = ChatService._build_response_payload(aggregated)
                run_id = str(response_payload.get("run_id") or aggregated.get("run_id") or uuid.uuid4())
                response_payload["run_id"] = run_id
                response_payload["execution"] = response_payload.get("execution")
                response_payload["artifacts"] = response_payload.get("artifacts") or []
                response_payload["final_script_artifact_id"] = response_payload.get("final_script_artifact_id")

                code_to_execute = str(response_payload.get("code") or "").strip()
                if code_to_execute and response_payload.get("execution") is None:
                    execution_result, retry_count, duration_ms, executed_code = (
                        await ChatService._execute_generated_code_with_retries(
                            workspace_id=workspace_id,
                            workspace_duckdb_path=data_path,
                            generated_code=code_to_execute,
                            run_id=run_id,
                            output_contract=response_payload.get("output_contract") or [],
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
                elif code_to_execute and response_payload.get("execution") is not None:
                    execution_result = response_payload.get("execution") or {}
                    executed_code = str(aggregated.get("final_executed_code") or code_to_execute)
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
                        retry_count=int(execution_result.get("retry_count") or 0),
                    )

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

                turn_id = await ChatService._persist_turn(
                    session=session,
                    conversation=conversation,
                    conversation_id=resolved_conversation_id,
                    question=question,
                    attachments=normalized_attachments,
                    response_payload=response_payload,
                    result=aggregated,
                )

                response_payload.update(
                    {
                        "conversation_id": resolved_conversation_id,
                        "turn_id": turn_id,
                    }
                )
                queue_event("final", response_payload)
            except HTTPException as exc:
                queue_event(
                    "error",
                    {"detail": str(exc.detail), "status_code": int(exc.status_code)},
                )
            except Exception as exc:
                queue_event("error", {"detail": str(exc), "status_code": 500})
            finally:
                if active_emitter_token is not None and callable(bindings.reset_stream_token_emitter):
                    bindings.reset_stream_token_emitter(active_emitter_token)
                if (
                    active_legacy_emitter_token is not None
                    and callable(reset_legacy_stream_token_emitter)
                ):
                    reset_legacy_stream_token_emitter(active_legacy_emitter_token)
                if active_agent_event_token is not None:
                    reset_agent_event_emitter(active_agent_event_token)

        runner = asyncio.create_task(run_pipeline())
        try:
            while True:
                if runner.done() and event_queue.empty():
                    break
                try:
                    queued = await asyncio.wait_for(event_queue.get(), timeout=0.05)
                except asyncio.TimeoutError:
                    continue
                if queued:
                    yield queued
        finally:
            if not runner.done():
                runner.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await runner
