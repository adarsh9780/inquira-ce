from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncGenerator

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse

from .config import load_agent_service_config
from .contracts import AgentRequest, AgentRunResponse, HealthResponse
from .loader import load_agent_graph
from .tracing import init_phoenix_tracing


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
        return str(getattr(value, "content", ""))
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


def _build_state(req: AgentRequest) -> dict[str, Any]:
    return {
        "request_id": req.request_id,
        "question": req.question,
        "current_code": req.current_code,
        "table_name": req.table_name,
        "preferred_table_name": req.preferred_table_name,
        "data_path": req.data_path,
        "active_schema": req.active_schema,
        "context": req.context,
        "workspace_id": req.workspace_id,
        "user_id": req.user_id,
        "attachments": req.attachments,
    }


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


def _select_agent(req: AgentRequest) -> str:
    cfg = load_agent_service_config()
    preferred = str(req.agent_profile or "").strip()
    if preferred and preferred in cfg.available_agents:
        return preferred
    return cfg.default_agent


def create_app() -> FastAPI:
    cfg = load_agent_service_config()
    init_phoenix_tracing(cfg)
    app = FastAPI(title="Inquira Agent Runtime", version="1.0.0")

    @app.get("/v1/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        runtime = load_agent_service_config()
        return HealthResponse(
            status="ok",
            api_major=runtime.api_major,
            active_agent=runtime.default_agent,
        )

    @app.post("/v1/agent/run", response_model=AgentRunResponse, dependencies=[Depends(_auth_guard)])
    async def run_agent(req: AgentRequest) -> AgentRunResponse:
        agent_name = _select_agent(req)
        graph = load_agent_graph(agent_name)
        result = await graph.ainvoke(_build_state(req), config=_build_config(req))
        run_id = str((result or {}).get("run_id") or uuid.uuid4())
        return AgentRunResponse(run_id=run_id, result=_plain(result if isinstance(result, dict) else {}))

    @app.post("/v1/agent/stream", dependencies=[Depends(_auth_guard)])
    async def stream_agent(req: AgentRequest):
        agent_name = _select_agent(req)
        graph = load_agent_graph(agent_name)
        state = _build_state(req)
        config = _build_config(req)

        async def event_generator() -> AsyncGenerator[str, None]:
            queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()

            def emit(event: str, payload: dict[str, Any]) -> None:
                queue.put_nowait((str(event), _plain(payload) if isinstance(payload, dict) else {"value": _plain(payload)}))

            try:
                aggregated: dict[str, Any] = {}
                async for step in graph.astream(state, config=config):
                    for node_name, payload in step.items():
                        payload_dict = payload if isinstance(payload, dict) else {"value": payload}
                        if isinstance(payload, dict):
                            aggregated.update(payload)
                        emit("node", {"node": str(node_name), "output": str(payload_dict.get("plan") or payload_dict.get("answer") or "")})

                final_payload = {
                    "run_id": str(aggregated.get("run_id") or uuid.uuid4()),
                    "result": _plain(aggregated),
                }
                emit("final", final_payload)

                while not queue.empty():
                    event, payload = await queue.get()
                    data = json.dumps(payload, default=str)
                    yield f"event: {event}\\ndata: {data}\\n\\n"
            except Exception as exc:
                payload = {"detail": str(exc), "status_code": 500}
                yield f"event: error\\ndata: {json.dumps(payload, default=str)}\\n\\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    return app
