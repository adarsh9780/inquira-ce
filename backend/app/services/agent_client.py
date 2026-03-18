"""HTTP client for external LangGraph API service."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator

import httpx

from .agent_service_config import load_agent_service_config


class AgentRuntimeError(RuntimeError):
    """Raised when agent runtime call fails."""


class AgentClient:
    _CONTRACT_API_MAJOR = 1

    def __init__(self) -> None:
        self._cfg = load_agent_service_config()

    @property
    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._cfg.auth_mode == "shared_secret" and self._cfg.shared_secret:
            headers["Authorization"] = f"Bearer {self._cfg.shared_secret}"
        return headers

    @staticmethod
    def _configurable(payload: dict[str, Any]) -> dict[str, Any]:
        llm = payload.get("llm") if isinstance(payload.get("llm"), dict) else {}
        return {
            "thread_id": f"{payload.get('user_id', '')}:{payload.get('workspace_id', '')}:{payload.get('conversation_id', '')}",
            "api_key": str(llm.get("api_key") or "").strip(),
            "provider": str(llm.get("provider") or "").strip(),
            "base_url": str(llm.get("base_url") or "").strip(),
            "model": str(payload.get("model") or "").strip(),
            "default_model": str(llm.get("default_model") or "").strip(),
            "lite_model": str(llm.get("lite_model") or "").strip(),
            "coding_model": str(llm.get("coding_model") or "").strip(),
        }

    def _assistant_id(self, payload: dict[str, Any]) -> str:
        requested = str(payload.get("agent_profile") or "").strip()
        return requested or self._cfg.default_agent

    async def _ensure_assistant(self, client: httpx.AsyncClient, assistant_id: str) -> str:
        search_resp = await client.post(
            f"{self._cfg.base_url}/assistants/search",
            json={"graph_id": assistant_id, "limit": 1, "offset": 0},
            headers={**self._headers, "Content-Type": "application/json"},
        )
        if search_resp.status_code != 200:
            raise AgentRuntimeError(
                f"Assistant lookup failed: {search_resp.status_code} {search_resp.text}"
            )
        body = search_resp.json() if search_resp.content else []
        assistants = body if isinstance(body, list) else []
        if assistants:
            first = assistants[0] if isinstance(assistants[0], dict) else {}
            found = str(first.get("assistant_id") or "").strip()
            if found:
                return found

        create_resp = await client.post(
            f"{self._cfg.base_url}/assistants",
            json={
                "assistant_id": assistant_id,
                "graph_id": assistant_id,
                "if_exists": "do_nothing",
            },
            headers={**self._headers, "Content-Type": "application/json"},
        )
        if create_resp.status_code not in {200, 201, 409}:
            raise AgentRuntimeError(
                f"Assistant creation failed: {create_resp.status_code} {create_resp.text}"
            )
        return assistant_id

    async def assert_health(self) -> dict[str, Any]:
        timeout = httpx.Timeout(5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            ok_resp = await client.get(f"{self._cfg.base_url}/ok", headers=self._headers)
            if ok_resp.status_code != 200:
                raise AgentRuntimeError(
                    f"Agent health check failed: {ok_resp.status_code} {ok_resp.text}"
                )
            info_resp = await client.get(f"{self._cfg.base_url}/info", headers=self._headers)
            if info_resp.status_code != 200:
                raise AgentRuntimeError(
                    f"Agent info check failed: {info_resp.status_code} {info_resp.text}"
                )

            expected = int(self._cfg.expected_api_major)
            actual = int(self._CONTRACT_API_MAJOR)
            if actual != expected:
                raise AgentRuntimeError(
                    f"Agent API major mismatch: expected {expected}, got {actual}"
                )

            assistant_id = await self._ensure_assistant(client, self._cfg.default_agent)

            info = info_resp.json() if info_resp.content else {}
            info_dict = info if isinstance(info, dict) else {}
            return {
                "status": "ok",
                "api_major": actual,
                "active_agent": assistant_id,
                "langgraph_info": info_dict,
            }

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        timeout = httpx.Timeout(180.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            assistant_id = await self._ensure_assistant(client, self._assistant_id(payload))
            resp = await client.post(
                f"{self._cfg.base_url}/runs/wait",
                json={
                    "assistant_id": assistant_id,
                    "input": payload,
                    "config": {"configurable": self._configurable(payload)},
                    "metadata": {
                        "request_id": str(payload.get("request_id") or ""),
                        "workspace_id": str(payload.get("workspace_id") or ""),
                        "conversation_id": str(payload.get("conversation_id") or ""),
                    },
                    "on_completion": "delete",
                },
                headers={**self._headers, "Content-Type": "application/json"},
            )
        if resp.status_code != 200:
            raise AgentRuntimeError(f"Agent run failed: {resp.status_code} {resp.text}")

        body = resp.json() if resp.content else {}
        if not isinstance(body, dict):
            raise AgentRuntimeError("Agent run returned non-object response")
        if isinstance(body.get("__error__"), dict):
            err = body.get("__error__") or {}
            raise AgentRuntimeError(
                f"{str(err.get('error') or 'Agent run failed')}: {str(err.get('message') or '')}"
            )

        result = body.get("values") if isinstance(body.get("values"), dict) else body
        if not isinstance(result, dict):
            raise AgentRuntimeError("Agent run response missing result payload")
        return result

    async def stream(self, payload: dict[str, Any]) -> AsyncGenerator[dict[str, Any], None]:
        timeout = httpx.Timeout(180.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            assistant_id = await self._ensure_assistant(client, self._assistant_id(payload))
            async with client.stream(
                "POST",
                f"{self._cfg.base_url}/runs/stream",
                json={
                    "assistant_id": assistant_id,
                    "input": payload,
                    "config": {"configurable": self._configurable(payload)},
                    "metadata": {
                        "request_id": str(payload.get("request_id") or ""),
                        "workspace_id": str(payload.get("workspace_id") or ""),
                        "conversation_id": str(payload.get("conversation_id") or ""),
                    },
                    "stream_mode": ["updates", "messages", "events", "custom"],
                    "on_completion": "delete",
                },
                headers={**self._headers, "Accept": "text/event-stream", "Content-Type": "application/json"},
            ) as resp:
                if resp.status_code != 200:
                    text = await resp.aread()
                    raise AgentRuntimeError(
                        f"Agent stream failed: {resp.status_code} {text.decode(errors='ignore')}"
                    )

                event_name = "message"
                data_parts: list[str] = []
                aggregated: dict[str, Any] = {}
                run_id = ""

                async for raw_line in resp.aiter_lines():
                    line = str(raw_line or "")
                    if not line:
                        if data_parts:
                            payload_text = "\n".join(data_parts)
                            try:
                                payload_data = json.loads(payload_text)
                            except Exception:
                                payload_data = {"raw": payload_text}

                            if event_name == "metadata" and isinstance(payload_data, dict):
                                run_id = str(payload_data.get("run_id") or run_id)
                            elif event_name == "updates" and isinstance(payload_data, dict):
                                for node_name, node_payload in payload_data.items():
                                    payload_dict = node_payload if isinstance(node_payload, dict) else {"value": node_payload}
                                    if isinstance(node_payload, dict):
                                        aggregated.update(node_payload)
                                    yield {
                                        "event": "node",
                                        "data": {
                                            "node": str(node_name),
                                            "output": str(payload_dict.get("plan") or payload_dict.get("answer") or ""),
                                        },
                                    }
                            elif event_name == "values" and isinstance(payload_data, dict):
                                aggregated.update(payload_data)
                            elif event_name in {"messages", "messages/partial", "messages-tuple"}:
                                text = ""
                                if isinstance(payload_data, dict):
                                    text = str(payload_data.get("content") or payload_data.get("text") or "")
                                elif isinstance(payload_data, list) and payload_data:
                                    text = str(payload_data[0] or "")
                                if text:
                                    yield {"event": "token", "data": {"node": "messages", "text": text}}
                            elif event_name in {"error", "failed"}:
                                detail = payload_data if isinstance(payload_data, dict) else {"detail": str(payload_data)}
                                raise AgentRuntimeError(f"Agent stream error: {detail}")
                            elif event_name not in {"end"}:
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

                if aggregated:
                    final_payload = {"run_id": run_id or "", "result": aggregated}
                    yield {"event": "final", "data": final_payload}
