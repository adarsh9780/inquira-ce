import pytest

from app.services.agent_client import AgentClient, AgentRuntimeError


@pytest.mark.asyncio
async def test_agent_client_fails_on_api_major_mismatch(monkeypatch):
    class _Resp:
        status_code = 200
        text = ""
        content = b"{}"

        def json(self):
            return {"status": "ok", "api_major": 9}

    class _Client:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            _ = exc_type, exc, tb
            return False

        async def get(self, *args, **kwargs):
            _ = args, kwargs
            return _Resp()

    monkeypatch.setattr("app.services.agent_client.httpx.AsyncClient", _Client)
    monkeypatch.setattr(
        "app.services.agent_client.load_agent_service_config",
        lambda: type("Cfg", (), {
            "base_url": "http://127.0.0.1:8123",
            "expected_api_major": 1,
            "auth_mode": "shared_secret",
            "shared_secret": "abc",
        })(),
    )

    client = AgentClient()
    with pytest.raises(AgentRuntimeError):
        await client.assert_health()
