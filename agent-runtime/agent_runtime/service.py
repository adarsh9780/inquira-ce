from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse

from .config import AgentServiceConfig, load_agent_service_config
from .contracts import AgentRequest, AgentRunResponse, HealthResponse
from .tracing import init_phoenix_tracing


def _ensure_backend_import_path() -> None:
    base = Path(__file__).resolve().parents[2]
    backend_dir = base / "backend"
    if backend_dir.exists():
        backend_str = str(backend_dir)
        if backend_str not in sys.path:
            sys.path.insert(0, backend_str)


_ensure_backend_import_path()

from app.agent_v2.events import reset_agent_event_emitter, set_agent_event_emitter
from app.agent_v2.graph import build_graph
from app.agent_v2.state import build_input_state
from app.agent_v2.streaming import reset_stream_token_emitter, set_stream_token_emitter


def _plain(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if hasattr(value, "model_dump"):
        try:
            return _plain(value.model_dump())
        except Exception:
            return str(value)
    if hasattr(value, "dict"):
        try:
            return _plain(value.dict())
        except Exception:
            return str(value)
    if hasattr(value, "content"):
        return {"content": str(getattr(value, "content", "")), "type": str(getattr(value, "type", ""))}
    return str(value)


def _parse_auth_header(authorization: str | None) -> str:
    raw = str(authorization or "").strip()
    if not raw.lower().startswith("bearer "):
        return ""
    return raw[7:].strip()


def _auth_guard(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    cfg = load_agent_service_config()
    if cfg.auth_mode != "shared_secret":
        return
    expected = str(cfg.shared_secret or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Agent shared secret is not configured")
    actual = _parse_auth_header(authorization)
    if actual != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _build_config(req: AgentRequest) -> dict[str, Any]:
    llm = req.llm if isinstance(req.llm, dict) else {}
    return {
        "configurable": {
            "thread_id": f"{req.user_id}:{req.workspace_id}:{req.conversation_id}",
            "api_key": str(llm.get("api_key") or "").strip(),
            "provider": str(llm.get("provider") or "").strip(),
            "base_url": str(llm.get("base_url") or "").strip(),
            "model": str(req.model or "").strip(),
            "default_model": str(llm.get("default_model") or "").strip(),
            "lite_model": str(llm.get("lite_model") or "").strip(),
            "coding_model": str(llm.get("coding_model") or "").strip(),
        }
    }


def _build_state(req: AgentRequest) -> dict[str, Any]:
    return build_input_state(
        question=req.question,
        schema=req.active_schema,
        current_code=req.current_code,
        table_name=req.table_name,
        data_path=req.data_path,
        context=req.context,
        workspace_id=req.workspace_id,
        user_id=req.user_id,
        scratchpad_path="",
        known_columns=[],
        attachments=req.attachments,
    )


def create_app() -> FastAPI:
    cfg = load_agent_service_config()
    init_phoenix_tracing(cfg)
    app = FastAPI(title="Inquira Agent Runtime", version="1.0.0")

    @app.get("/v1/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        runtime = load_agent_service_config()
        return HealthResponse(status="ok", api_major=runtime.api_major)

    @app.post("/v1/agent/run", response_model=AgentRunResponse, dependencies=[Depends(_auth_guard)])
    async def run_agent(req: AgentRequest) -> AgentRunResponse:
        graph = build_graph()
        state = _build_state(req)
        config = _build_config(req)
        result = await graph.ainvoke(state, config=config)
        run_id = str(result.get("run_id") or uuid.uuid4())
        return AgentRunResponse(run_id=run_id, result=_plain(result))

    @app.post("/v1/agent/stream", dependencies=[Depends(_auth_guard)])
    async def stream_agent(req: AgentRequest):
        graph = build_graph()
        state = _build_state(req)
        config = _build_config(req)

        async def event_generator() -> AsyncGenerator[str, None]:
            queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
            stream_token = None
            event_token = None
            run_task: asyncio.Task[Any] | None = None

            def emit(event: str, payload: dict[str, Any]) -> None:
                queue.put_nowait((str(event), _plain(payload) if isinstance(payload, dict) else {"value": _plain(payload)}))

            try:
                stream_token = set_stream_token_emitter(lambda node, text: emit("token", {"node": node, "text": text}))
                event_token = set_agent_event_emitter(lambda event, payload: emit(event, payload))

                async def _run() -> None:
                    aggregated: dict[str, Any] = {}
                    async for step in graph.astream(state, config=config):
                        for node_name, payload in step.items():
                            if isinstance(payload, dict):
                                aggregated.update(payload)
                            emit("node", {"node": str(node_name), "payload": _plain(payload), "output": str((payload or {}).get("plan") if isinstance(payload, dict) else "")})
                    emit("final", {"run_id": str(aggregated.get("run_id") or uuid.uuid4()), "result": _plain(aggregated)})

                run_task = asyncio.create_task(_run())

                while True:
                    if run_task.done() and queue.empty():
                        break
                    try:
                        event, payload = await asyncio.wait_for(queue.get(), timeout=0.05)
                    except asyncio.TimeoutError:
                        continue
                    data = json.dumps(payload, default=str)
                    yield f"event: {event}\\ndata: {data}\\n\\n"

                if run_task is not None:
                    exc = run_task.exception()
                    if exc is not None:
                        payload = {"detail": str(exc), "status_code": 500}
                        yield f"event: error\\ndata: {json.dumps(payload, default=str)}\\n\\n"
            finally:
                if stream_token is not None:
                    reset_stream_token_emitter(stream_token)
                if event_token is not None:
                    reset_agent_event_emitter(event_token)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    return app
