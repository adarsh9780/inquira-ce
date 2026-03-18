import pytest
import httpx

from app.services.agent_client import AgentClient, AgentRuntimeError


@pytest.mark.asyncio
async def test_agent_client_fails_on_contract_api_major_mismatch(monkeypatch):
    class _Resp:
        def __init__(self, status_code: int = 200, payload=None):
            self.status_code = status_code
            self.text = ""
            self.content = b"{}"
            self._payload = payload if payload is not None else {}

        def json(self):
            return self._payload

    class _Client:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            _ = exc_type, exc, tb
            return False

        async def get(self, url, *args, **kwargs):
            _ = args, kwargs
            if url.endswith("/ok"):
                return _Resp(200, {"ok": True})
            if url.endswith("/info"):
                return _Resp(200, {"version": "0.0.0"})
            return _Resp(404, {})

        async def post(self, url, *args, **kwargs):
            _ = args, kwargs
            if url.endswith("/assistants/search"):
                return _Resp(200, [{"assistant_id": "agent_v2"}])
            return _Resp(404, {})

    monkeypatch.setattr("app.services.agent_client.httpx.AsyncClient", _Client)
    monkeypatch.setattr(
        "app.services.agent_client.load_agent_service_config",
        lambda: type(
            "Cfg",
            (),
            {
                "base_url": "http://127.0.0.1:8123",
                "expected_api_major": 9,
                "default_agent": "agent_v2",
                "auth_mode": "shared_secret",
                "shared_secret": "abc",
            },
        )(),
    )

    client = AgentClient()
    with pytest.raises(AgentRuntimeError):
        await client.assert_health()


@pytest.mark.asyncio
async def test_agent_client_wraps_connect_error_into_agent_runtime_error(monkeypatch):
    class _Client:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            _ = exc_type, exc, tb
            return False

        async def get(self, url, *args, **kwargs):
            _ = url, args, kwargs
            raise httpx.ConnectError("All connection attempts failed")

    monkeypatch.setattr("app.services.agent_client.httpx.AsyncClient", _Client)
    monkeypatch.setattr(
        "app.services.agent_client.load_agent_service_config",
        lambda: type(
            "Cfg",
            (),
            {
                "base_url": "http://127.0.0.1:8123",
                "expected_api_major": 1,
                "default_agent": "agent_v2",
                "auth_mode": "shared_secret",
                "shared_secret": "abc",
            },
        )(),
    )

    client = AgentClient()
    with pytest.raises(AgentRuntimeError) as exc_info:
        await client.assert_health()
    assert "Agent runtime unreachable during health check" in str(exc_info.value)
    assert "http://127.0.0.1:8123" in str(exc_info.value)
