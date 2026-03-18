"""HTTP client for external agent runtime service."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator

import httpx

from .agent_service_config import load_agent_service_config


class AgentRuntimeError(RuntimeError):
    """Raised when agent runtime call fails."""


class AgentClient:
    def __init__(self) -> None:
        self._cfg = load_agent_service_config()

    @property
    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._cfg.auth_mode == "shared_secret" and self._cfg.shared_secret:
            headers["Authorization"] = f"Bearer {self._cfg.shared_secret}"
        return headers

    async def assert_health(self) -> dict[str, Any]:
        timeout = httpx.Timeout(5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{self._cfg.base_url}/v1/health", headers=self._headers)
        if resp.status_code != 200:
            raise AgentRuntimeError(f"Agent health check failed: {resp.status_code} {resp.text}")
        data = resp.json() if resp.content else {}
        api_major = int(data.get("api_major") or 0)
        if api_major != int(self._cfg.expected_api_major):
            raise AgentRuntimeError(
                f"Agent API major mismatch: expected {self._cfg.expected_api_major}, got {api_major}"
            )
        return data if isinstance(data, dict) else {}

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        timeout = httpx.Timeout(180.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{self._cfg.base_url}/v1/agent/run",
                json=payload,
                headers={**self._headers, "Content-Type": "application/json"},
            )
        if resp.status_code != 200:
            raise AgentRuntimeError(f"Agent run failed: {resp.status_code} {resp.text}")
        body = resp.json() if resp.content else {}
        if not isinstance(body, dict):
            raise AgentRuntimeError("Agent run returned non-object response")
        result = body.get("result")
        if not isinstance(result, dict):
            raise AgentRuntimeError("Agent run response missing `result` object")
        return result

    async def stream(self, payload: dict[str, Any]) -> AsyncGenerator[dict[str, Any], None]:
        timeout = httpx.Timeout(180.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self._cfg.base_url}/v1/agent/stream",
                json=payload,
                headers={**self._headers, "Accept": "text/event-stream", "Content-Type": "application/json"},
            ) as resp:
                if resp.status_code != 200:
                    text = await resp.aread()
                    raise AgentRuntimeError(f"Agent stream failed: {resp.status_code} {text.decode(errors='ignore')}")

                event_name = "message"
                data_parts: list[str] = []
                async for raw_line in resp.aiter_lines():
                    line = str(raw_line or "")
                    if not line:
                        if data_parts:
                            payload_text = "\n".join(data_parts)
                            try:
                                payload_data = json.loads(payload_text)
                            except Exception:
                                payload_data = {"raw": payload_text}
                            yield {"event": event_name, "data": payload_data}
                        event_name = "message"
                        data_parts = []
                        continue
                    if line.startswith(":"):
                        continue
                    if line.startswith("event:"):
                        event_name = line[6:].strip() or "message"
                        continue
                    if line.startswith("data:"):
                        data_parts.append(line[5:].strip())
