"""LangGraph analysis orchestration embedded in the persistent data worker."""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from typing import Any, Callable


class LangGraphAnalysisAgent:
    """Run the migrated agent graph while keeping execution inside this worker."""

    def __init__(self, *, kernels: Any, graph: Any | None = None) -> None:
        self.kernels = kernels
        self._graph = graph

    def _get_graph(self) -> Any:
        if self._graph is None:
            from .agent_v2.graph import build_graph

            self._graph = build_graph({})
        return self._graph

    async def analyze(
        self,
        params: dict[str, Any],
        emit: Callable[[dict[str, Any]], Any] | None = None,
    ) -> dict[str, Any]:
        values = _validate_params(params)
        graph_input = _graph_input(values)
        config = {"configurable": _model_config(values["model"])}
        event_loop = asyncio.get_running_loop()
        token_tasks: set[asyncio.Task[Any]] = set()

        async def runtime_execute(**request: Any) -> dict[str, Any]:
            requested_timeout = _positive_int(
                request.get("timeout_seconds", request.get("timeout")),
                values["timeout_seconds"],
            )
            timeout = min(values["timeout_seconds"], requested_timeout)
            code = str(request.get("code") or "")
            return await self.kernels.execute(
                workspace_id=values["workspace_id"],
                database_path=values["database_path"],
                code=code,
                run_id=values["run_id"],
                artifact_dir=values["artifact_dir"],
                timeout_seconds=timeout,
                output_contract=request.get("output_contract") if "output_contract" in request else None,
                emit=emit,
            )

        graph_input["runtime_execute"] = runtime_execute

        from .agent_v2.streaming import reset_stream_token_emitter, set_stream_token_emitter
        from .agent_v2.tools.execute_python import reset_local_executor, set_local_executor

        def emit_token(node: str, text: str) -> None:
            def schedule() -> None:
                task = event_loop.create_task(
                    _emit(emit, {"type": "token", "node": node, "text": text})
                )
                token_tasks.add(task)
                task.add_done_callback(token_tasks.discard)

            event_loop.call_soon_threadsafe(schedule)

        executor_token = set_local_executor(runtime_execute)
        stream_token = set_stream_token_emitter(emit_token)
        final_state: dict[str, Any] = {}
        try:
            graph = self._get_graph()
            async for item in graph.astream(
                graph_input,
                config=config,
                stream_mode=["custom", "values"],
            ):
                mode, payload = _stream_item(item)
                if mode == "values" and isinstance(payload, dict):
                    final_state = payload
                elif mode == "custom":
                    event = _custom_event(payload)
                    if event:
                        await _emit(emit, event)
        finally:
            reset_stream_token_emitter(stream_token)
            reset_local_executor(executor_token)
            await asyncio.sleep(0)
            if token_tasks:
                await asyncio.gather(*tuple(token_tasks), return_exceptions=True)

        return _worker_result(final_state)


def _graph_input(values: dict[str, Any]) -> dict[str, Any]:
    from langchain_core.messages import AIMessage, HumanMessage

    messages: list[Any] = []
    context = values["context"]
    for turn in context.get("turns", []):
        user_text = str(turn.get("user_text") or "").strip()
        assistant_text = str(turn.get("assistant_text") or "").strip()
        if user_text:
            messages.append(HumanMessage(content=user_text))
        if assistant_text:
            messages.append(AIMessage(content=assistant_text))

    question_content: str | list[dict[str, Any]] = values["question"]
    attachments = values.get("attachments", [])
    if attachments:
        blocks: list[dict[str, Any]] = [{"type": "text", "text": values["question"]}]
        for attachment in attachments:
            blocks.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{attachment['media_type']};base64,{attachment['data_base64']}"
                },
            })
        question_content = blocks
    messages.append(HumanMessage(content=question_content))

    schema = values["schema"]
    tables = schema.get("tables", [])
    return {
        "messages": messages,
        "workspace_id": values["workspace_id"],
        "user_id": "local-user",
        "conversation_id": values.get("conversation_id"),
        "turn_id": values.get("turn_id"),
        "artifact_dir": values["artifact_dir"],
        "scratchpad_path": values["artifact_dir"],
        "table_names": [str(table.get("name") or "").strip() for table in tables if str(table.get("name") or "").strip()],
        "data_path": values["database_path"],
        "context": str(schema.get("context") or ""),
        "workspace_schema": schema,
        "schema_folder_path": "",
        "current_code": str(values.get("current_code") or ""),
        "previous_code": str(values.get("current_code") or ""),
        "run_id": values["run_id"],
        "known_columns": [],
        "attachments": attachments,
        "privacy": {"allow_llm_data_samples": bool(values["model"].get("allow_data_samples"))},
    }


def _model_config(model: dict[str, Any]) -> dict[str, Any]:
    selected = str(model.get("model") or "").strip()
    return {
        "provider": str(model.get("provider") or "").strip().lower(),
        "model": selected,
        "default_model": selected,
        "lite_model": str(model.get("lite_model") or selected).strip(),
        "coding_model": str(model.get("coding_model") or selected).strip(),
        "api_key": str(model.get("api_key") or ""),
        "base_url": str(model.get("base_url") or "").strip(),
        "temperature": float(model.get("temperature", 0.0)),
        "max_tokens": _positive_int(model.get("max_tokens"), 4096),
        "top_p": float(model.get("top_p", 1.0)),
        "top_k": int(model.get("top_k", 0)),
        "frequency_penalty": float(model.get("frequency_penalty", 0.0)),
        "presence_penalty": float(model.get("presence_penalty", 0.0)),
        "context_window": _positive_int(model.get("context_window"), 0),
    }


def _stream_item(item: Any) -> tuple[str, Any]:
    if isinstance(item, tuple) and len(item) == 2:
        return str(item[0]), item[1]
    if isinstance(item, dict):
        return "values", item
    return "", item


def _custom_event(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    event_type = str(payload.get("event") or payload.get("type") or "").strip()
    if not event_type:
        return None
    data = payload.get("data")
    if not isinstance(data, dict):
        data = {}
    return {"type": event_type, **data}


def _empty_execution() -> dict[str, Any]:
    return {
        "success": True,
        "stdout": "",
        "stderr": "",
        "error": None,
        "result": None,
        "result_kind": "",
        "artifacts": [],
        "timed_out": False,
    }


def _worker_result(state: dict[str, Any]) -> dict[str, Any]:
    route = str(state.get("route") or "analysis").strip().lower()
    execution = state.get("final_execution")
    if not isinstance(execution, dict):
        execution = _empty_execution()
    error = str(state.get("last_error") or "").strip()
    success = route != "analysis" or (bool(execution.get("success")) and not error)
    if route == "analysis" and state.get("final_execution") is None:
        success = False
        if not error:
            error = "The analysis agent did not produce an execution result."
    return {
        "success": success,
        "answer": str(state.get("final_explanation") or state.get("result_explanation") or "").strip(),
        "code": str(state.get("final_code") or "").strip(),
        "execution": execution,
        "metadata": state.get("metadata") if isinstance(state.get("metadata"), dict) else {},
        "route": route,
        "error": error or None,
    }


def _validate_params(params: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(params, dict):
        raise ValueError("Agent parameters must be an object.")
    values = dict(params)
    for key in ("workspace_id", "database_path", "question", "run_id", "artifact_dir"):
        if not isinstance(values.get(key), str) or not values[key].strip():
            raise ValueError(f"{key} is required.")
    database = Path(values["database_path"]).expanduser().resolve()
    if not database.is_file():
        raise ValueError("database_path must identify an existing workspace catalog.")
    timeout = values.get("timeout_seconds")
    if not isinstance(timeout, int) or timeout < 1 or timeout > 3600:
        raise ValueError("timeout_seconds must be between 1 and 3600.")
    model = values.get("model")
    if not isinstance(model, dict):
        raise ValueError("model configuration is required.")
    provider = str(model.get("provider") or "").strip().lower()
    if provider not in {"openai", "openrouter", "ollama", "anthropic"}:
        raise ValueError("The selected model provider is not supported by the agent.")
    if not str(model.get("model") or "").strip():
        raise ValueError("A model is required.")
    if provider != "ollama" and not str(model.get("api_key") or "").strip():
        raise ValueError("The model provider API key is missing.")
    schema = values.get("schema")
    if schema is None:
        schema = {"context": "", "tables": []}
    if not isinstance(schema, dict) or not isinstance(schema.get("tables", []), list):
        raise ValueError("semantic schema is invalid.")
    context = values.get("context")
    if context is None:
        context = {"turns": []}
    if not isinstance(context, dict) or not isinstance(context.get("turns", []), list):
        raise ValueError("conversation context is invalid.")
    values.update({
        "database_path": str(database),
        "artifact_dir": str(Path(values["artifact_dir"]).expanduser().resolve()),
        "schema": schema,
        "context": context,
        "model": model,
        "attachments": _attachments(values.get("attachments")),
    })
    return values


def _attachments(raw: Any) -> list[dict[str, str]]:
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > 5:
        raise ValueError("attachments are invalid.")
    result: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("attachments are invalid.")
        normalized = {
            key: str(item.get(key) or "").strip()
            for key in ("attachment_id", "media_type", "filename", "data_base64")
        }
        if not all(normalized.values()) or not normalized["media_type"].startswith("image/"):
            raise ValueError("attachments are invalid.")
        result.append(normalized)
    return result


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


async def _emit(callback: Callable[[dict[str, Any]], Any] | None, event: dict[str, Any]) -> None:
    if callback is None:
        return
    value = callback(event)
    if inspect.isawaitable(value):
        await value
