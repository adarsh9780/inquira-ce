import pytest
import httpx

from app.services.agent_client import AgentClient, AgentRuntimeError


def test_agent_client_configurable_defaults_when_llm_payload_missing():
    payload = {
        "user_id": "u1",
        "workspace_id": "w1",
        "conversation_id": "c1",
        "model": "gpt-test",
        "llm": None,
    }

    cfg = AgentClient._configurable(payload)
    assert cfg["thread_id"] == "u1:w1:c1"
    assert cfg["model"] == "gpt-test"
    assert cfg["api_key"] == ""
    assert cfg["provider"] == ""
    assert cfg["base_url"] == ""
    assert cfg["default_model"] == ""
    assert cfg["lite_model"] == ""
    assert cfg["coding_model"] == ""


def test_agent_client_trace_safe_input_redacts_llm_api_key():
    payload = {
        "question": "hello",
        "llm": {
            "provider": "openrouter",
            "api_key": "secret-key",
            "default_model": "gpt-test",
        },
    }

    safe = AgentClient._trace_safe_input(payload)
    assert isinstance(safe.get("llm"), dict)
    assert "api_key" not in safe["llm"]
    assert safe["llm"]["provider"] == "openrouter"


def test_agent_client_headers_support_x_api_key_mode(monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_client.load_agent_service_config",
        lambda: type(
            "Cfg",
            (),
            {
                "base_url": "https://agents.example.com",
                "expected_api_major": 1,
                "default_agent": "agent_v2",
                "auth_mode": "x_api_key",
                "shared_secret": "",
                "api_key": "token-123",
                "manage_assistants": False,
                "recursion_limit": 80,
            },
        )(),
    )
    client = AgentClient()
    headers = client.headers_with()
    assert headers["x-api-key"] == "token-123"
    assert "Authorization" not in headers


def test_agent_client_run_config_includes_recursion_limit(monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_client.load_agent_service_config",
        lambda: type(
            "Cfg",
            (),
            {
                "base_url": "https://agents.example.com",
                "expected_api_major": 1,
                "default_agent": "agent_v2",
                "auth_mode": "bearer",
                "shared_secret": "",
                "api_key": "token-123",
                "manage_assistants": False,
                "recursion_limit": 88,
            },
        )(),
    )
    client = AgentClient()
    cfg = client._run_config(
        {
            "user_id": "u1",
            "workspace_id": "w1",
            "conversation_id": "c1",
            "model": "gpt-test",
            "llm": {},
        }
    )
    assert cfg["recursion_limit"] == 88
    assert cfg["configurable"]["thread_id"] == "u1:w1:c1"


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


@pytest.mark.asyncio
async def test_agent_client_stream_passthrough_emits_langgraph_events(monkeypatch):
    captured = {"stream_mode": None}

    class _Resp:
        def __init__(self, status_code: int = 200, payload=None):
            self.status_code = status_code
            self.text = ""
            self.content = b"{}"
            self._payload = payload if payload is not None else {}

        def json(self):
            return self._payload

        async def aread(self):
            return b""

        async def aiter_lines(self):
            lines = [
                "event: metadata",
                "data: {\"run_id\":\"run-1\"}",
                "",
                "event: messages",
                "data: {\"content\":\"Hello\"}",
                "",
                "event: updates",
                "data: {\"create_plan\":{\"plan\":\"Plan A\"}}",
                "",
                "event: values",
                "data: {\"metadata\":{\"is_safe\":true,\"is_relevant\":true}}",
                "",
                "event: end",
                "data: {}",
                "",
            ]
            for line in lines:
                yield line

    class _StreamCtx:
        async def __aenter__(self):
            return _Resp(200, {})

        async def __aexit__(self, exc_type, exc, tb):
            _ = exc_type, exc, tb
            return False

    class _Client:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            _ = exc_type, exc, tb
            return False

        async def post(self, url, *args, **kwargs):
            _ = args, kwargs
            if url.endswith("/assistants/search"):
                return _Resp(200, [{"assistant_id": "agent_v2"}])
            return _Resp(404, {})

        def stream(self, method, url, *args, **kwargs):
            _ = method, url, args
            payload = kwargs.get("json") if isinstance(kwargs, dict) else None
            if isinstance(payload, dict):
                stream_mode = payload.get("stream_mode")
                if isinstance(stream_mode, list):
                    captured["stream_mode"] = list(stream_mode)
            return _StreamCtx()

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
    events = []
    async for event in client.stream({"agent_profile": "agent_v2"}):
        events.append(event)

    assert [evt["event"] for evt in events] == ["metadata", "messages", "updates", "values"]
    assert events[1]["data"]["content"] == "Hello"
    assert events[2]["data"]["create_plan"]["plan"] == "Plan A"
    assert captured["stream_mode"] is not None
    assert "values" in captured["stream_mode"]


@pytest.mark.asyncio
async def test_agent_client_stream_retries_once_on_retryable_api_connection_error(monkeypatch):
    class _Resp:
        def __init__(self, status_code: int = 200, payload=None, lines=None):
            self.status_code = status_code
            self.text = ""
            self.content = b"{}"
            self._payload = payload if payload is not None else {}
            self._lines = lines or []

        def json(self):
            return self._payload

        async def aread(self):
            return b""

        async def aiter_lines(self):
            for line in self._lines:
                yield line

    class _StreamCtx:
        def __init__(self, resp):
            self._resp = resp

        async def __aenter__(self):
            return self._resp

        async def __aexit__(self, exc_type, exc, tb):
            _ = exc_type, exc, tb
            return False

    class _Client:
        stream_calls = 0

        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            _ = exc_type, exc, tb
            return False

        async def post(self, url, *args, **kwargs):
            _ = args, kwargs
            if url.endswith("/assistants/search"):
                return _Resp(200, [{"assistant_id": "agent_v2"}])
            return _Resp(404, {})

        def stream(self, method, url, *args, **kwargs):
            _ = method, url, args, kwargs
            type(self).stream_calls += 1
            if type(self).stream_calls == 1:
                lines = [
                    "event: updates",
                    'data: {"route":{"next":"react_loop"}}',
                    "",
                    "event: error",
                    'data: {"error":"APIConnectionError","message":"Connection error."}',
                    "",
                ]
            else:
                lines = [
                    "event: values",
                    'data: {"metadata":{"is_safe":true,"is_relevant":true}}',
                    "",
                    "event: end",
                    "data: {}",
                    "",
                ]
            return _StreamCtx(_Resp(200, {}, lines=lines))

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
    events = []
    async for event in client.stream({"agent_profile": "agent_v2"}):
        events.append(event)

    assert _Client.stream_calls == 2
    assert [evt["event"] for evt in events] == ["updates", "values"]


@pytest.mark.asyncio
async def test_agent_client_run_sends_redacted_input_but_keeps_configurable_api_key(monkeypatch):
    captured: dict[str, dict] = {}

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

        async def post(self, url, *args, **kwargs):
            _ = args
            body = kwargs.get("json") if isinstance(kwargs, dict) else None
            if isinstance(body, dict):
                captured[url] = body
            if url.endswith("/assistants/search"):
                return _Resp(200, [{"assistant_id": "agent_v2"}])
            if url.endswith("/runs/wait"):
                return _Resp(200, {"values": {"route": "analysis"}})
            return _Resp(404, {})

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
    _ = await client.run(
        {
            "agent_profile": "agent_v2",
            "user_id": "u1",
            "workspace_id": "w1",
            "conversation_id": "c1",
            "model": "gpt-test",
            "llm": {
                "provider": "openrouter",
                "api_key": "secret-key",
                "base_url": "https://openrouter.ai/api/v1",
                "default_model": "gpt-test",
                "lite_model": "gpt-test-lite",
                "coding_model": "gpt-test",
            },
        }
    )

    run_body = captured["http://127.0.0.1:8123/runs/wait"]
    assert isinstance(run_body.get("input"), dict)
    assert isinstance(run_body["input"].get("llm"), dict)
    assert "api_key" not in run_body["input"]["llm"]
    assert run_body["config"]["configurable"]["api_key"] == "secret-key"


@pytest.mark.asyncio
async def test_agent_client_run_skips_assistant_management_when_disabled(monkeypatch):
    captured: dict[str, dict] = {}

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

        async def post(self, url, *args, **kwargs):
            _ = args
            if url.endswith("/assistants/search"):
                raise AssertionError("assistants/search should not be called when management is disabled")
            body = kwargs.get("json") if isinstance(kwargs, dict) else None
            if isinstance(body, dict):
                captured[url] = body
            if url.endswith("/runs/wait"):
                return _Resp(200, {"values": {"route": "analysis"}})
            return _Resp(404, {})

    monkeypatch.setattr("app.services.agent_client.httpx.AsyncClient", _Client)
    monkeypatch.setattr(
        "app.services.agent_client.load_agent_service_config",
        lambda: type(
            "Cfg",
            (),
            {
                "base_url": "https://agents.example.com",
                "expected_api_major": 1,
                "default_agent": "agent_v2",
                "auth_mode": "bearer",
                "shared_secret": "",
                "api_key": "ls-token",
                "manage_assistants": False,
                "recursion_limit": 90,
            },
        )(),
    )

    client = AgentClient()
    _ = await client.run(
        {
            "agent_profile": "agent_v2",
            "user_id": "u1",
            "workspace_id": "w1",
            "conversation_id": "c1",
            "model": "gpt-test",
            "llm": {},
        }
    )

    run_body = captured["https://agents.example.com/runs/wait"]
    assert run_body["assistant_id"] == "agent_v2"
    assert run_body["config"]["recursion_limit"] == 90


@pytest.mark.asyncio
async def test_agent_client_assert_health_uses_cached_result(monkeypatch):
    counts = {"ok": 0, "info": 0}

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
                counts["ok"] += 1
                return _Resp(200, {"ok": True})
            if url.endswith("/info"):
                counts["info"] += 1
                return _Resp(200, {"version": "1.0"})
            return _Resp(404, {})

        async def post(self, url, *args, **kwargs):
            _ = url, args, kwargs
            return _Resp(404, {})

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
                "manage_assistants": False,
                "health_cache_ttl_sec": 60,
            },
        )(),
    )
    AgentClient._health_cache.clear()

    client = AgentClient()
    first = await client.assert_health()
    second = await client.assert_health()

    assert first["status"] == "ok"
    assert second["status"] == "ok"
    assert counts["ok"] == 1
    assert counts["info"] == 1


@pytest.mark.asyncio
async def test_agent_client_run_reuses_cached_assistant_lookup(monkeypatch):
    counts = {"search": 0}

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

        async def post(self, url, *args, **kwargs):
            _ = args, kwargs
            if url.endswith("/assistants/search"):
                counts["search"] += 1
                return _Resp(200, [{"assistant_id": "agent_v2"}])
            if url.endswith("/runs/wait"):
                return _Resp(200, {"values": {"route": "analysis"}})
            return _Resp(404, {})

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
                "manage_assistants": True,
                "assistant_cache_ttl_sec": 300,
                "recursion_limit": 80,
            },
        )(),
    )
    AgentClient._assistant_cache.clear()

    client = AgentClient()
    payload = {
        "agent_profile": "agent_v2",
        "user_id": "u1",
        "workspace_id": "w1",
        "conversation_id": "c1",
        "model": "gpt-test",
        "llm": {},
    }
    _ = await client.run(payload)
    _ = await client.run(payload)

    assert counts["search"] == 1
