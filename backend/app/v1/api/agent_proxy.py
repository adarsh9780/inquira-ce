"""Authenticated proxy endpoints for internal LangGraph runtime API."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ...services.agent_client import AgentClient
from ...services.agent_service_config import load_agent_service_config
from .deps import ensure_appdata_principal

router = APIRouter(
    prefix="/agent",
    tags=["V1 Agent Proxy"],
    dependencies=[Depends(ensure_appdata_principal)],
)


def _normalize_json_response(resp: httpx.Response) -> Any:
    if not resp.content:
        return {}
    try:
        payload = resp.json()
    except Exception:
        payload = {"raw": resp.text}
    return payload


async def _forward_json(
    *,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    agent_client = AgentClient()
    timeout = httpx.Timeout(180.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        cfg = load_agent_service_config()
        resp = await client.request(
            method=method.upper(),
            url=f"{cfg.base_url}{path}",
            json=payload if payload is not None else None,
            headers=agent_client.headers_with(
                {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
            ),
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text or "Agent proxy request failed.")
    return _normalize_json_response(resp)


@router.get("/ok")
async def proxy_ok() -> Any:
    return await _forward_json(method="GET", path="/ok")


@router.get("/info")
async def proxy_info() -> Any:
    return await _forward_json(method="GET", path="/info")


@router.post("/assistants/search")
async def proxy_assistants_search(payload: dict[str, Any]) -> Any:
    return await _forward_json(method="POST", path="/assistants/search", payload=payload)


@router.post("/assistants")
async def proxy_assistants_create(payload: dict[str, Any]) -> Any:
    return await _forward_json(method="POST", path="/assistants", payload=payload)


@router.post("/runs/wait")
async def proxy_runs_wait(payload: dict[str, Any]) -> Any:
    return await _forward_json(method="POST", path="/runs/wait", payload=payload)


@router.post("/runs/stream")
async def proxy_runs_stream(payload: dict[str, Any]):
    agent_client = AgentClient()
    cfg = load_agent_service_config()
    timeout = httpx.Timeout(180.0)
    client = httpx.AsyncClient(timeout=timeout)
    try:
        req = client.build_request(
            "POST",
            f"{cfg.base_url}/runs/stream",
            json=payload,
            headers=agent_client.headers_with(
                {
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                }
            ),
        )
        resp = await client.send(req, stream=True)
    except Exception as exc:  # noqa: BLE001
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Agent proxy stream failed: {exc}") from exc

    if resp.status_code >= 400:
        text = (await resp.aread()).decode(errors="ignore")
        await resp.aclose()
        await client.aclose()
        raise HTTPException(status_code=resp.status_code, detail=text or "Agent proxy stream failed.")

    async def _iter_bytes():
        try:
            async for chunk in resp.aiter_bytes():
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    return StreamingResponse(
        _iter_bytes(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
