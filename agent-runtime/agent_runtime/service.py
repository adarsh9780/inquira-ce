from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncGenerator, Callable

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse

from .config import load_agent_service_config
from .contracts import AgentRequest, AgentRunResponse, HealthResponse
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


def _safe_table(table_name: str) -> str:
    raw = str(table_name or "").strip() or "data"
    return raw.replace('"', '""')


def _build_analysis_result(req: AgentRequest) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    table_name = _safe_table(req.table_name)
    route = "analysis"
    if not table_name:
        route = "general_chat"

    code = ""
    explanation = "I can help analyze your data."
    output_contract: list[dict[str, str]] = []

    if route == "analysis":
        code = (
            f'result_df = conn.sql("SELECT * FROM \"{table_name}\" LIMIT 20").fetchdf()\\n'
            "result_df"
        )
        explanation = (
            f"I prepared a starter analysis query against `{table_name}` and selected 20 rows for review."
        )
        output_contract = [{"name": "result_df", "kind": "dataframe"}]

    return {
        "run_id": run_id,
        "route": route,
        "metadata": {
            "is_safe": True,
            "is_relevant": route == "analysis",
            "tables_used": [table_name] if route == "analysis" else [],
            "joins_used": False,
            "join_keys": [],
        },
        "final_code": code,
        "final_explanation": explanation,
        "result_explanation": explanation,
        "code_explanation": (
            "The code uses the backend-provided `conn` DuckDB connection and materializes a dataframe."
            if code
            else ""
        ),
        "output_contract": output_contract,
        "messages": [],
    }


def _emit_text_chunks(text: str, emit: Callable[[str, dict[str, Any]], None], *, chunk_size: int = 24) -> None:
    rendered = str(text or "")
    if not rendered:
        return
    step = max(1, int(chunk_size))
    for idx in range(0, len(rendered), step):
        emit("token", {"node": "react_loop", "text": rendered[idx : idx + step]})


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
        result = _build_analysis_result(req)
        return AgentRunResponse(run_id=str(result.get("run_id") or uuid.uuid4()), result=_plain(result))

    @app.post("/v1/agent/stream", dependencies=[Depends(_auth_guard)])
    async def stream_agent(req: AgentRequest):
        async def event_generator() -> AsyncGenerator[str, None]:
            queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()

            def emit(event: str, payload: dict[str, Any]) -> None:
                queue.put_nowait((str(event), _plain(payload) if isinstance(payload, dict) else {"value": _plain(payload)}))

            try:
                result = _build_analysis_result(req)
                emit("agent_status", {"step": "generating_code", "message": "Generating analysis plan"})
                emit("node", {"node": "react_loop", "output": str(result.get("final_explanation") or "")})
                _emit_text_chunks(str(result.get("final_explanation") or ""), emit)
                emit("final", {"run_id": str(result.get("run_id") or uuid.uuid4()), "result": _plain(result)})

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
