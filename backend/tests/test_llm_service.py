import pytest
import warnings
from types import SimpleNamespace
from fastapi import HTTPException
from pydantic import BaseModel

from app.services.llm_service import LLMService


def _runtime_stub(**overrides):
    base = {
        "provider": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "requires_api_key": True,
        "default_model": "google/gemini-2.5-flash",
        "default_max_tokens": 4096,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_llm_service_loads_api_key_from_repo_root_env(monkeypatch, tmp_path):
    backend_dir = tmp_path / "backend"
    services_dir = backend_dir / "app" / "services"
    services_dir.mkdir(parents=True)
    module_path = services_dir / "llm_service.py"
    module_path.write_text("# stub", encoding="utf-8")

    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=test-root-key\n", encoding="utf-8")

    # Ensure process env doesn't already satisfy the key.
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    # Pretend llm_service.py lives in our temp backend/app/services path.
    monkeypatch.setattr("app.services.llm_service.__file__", str(module_path))
    # Avoid constructing real chat client in this unit test.
    monkeypatch.setattr("app.services.llm_service.create_chat_model", lambda **_kwargs: object())
    monkeypatch.setattr(
        "app.services.llm_service.load_llm_runtime_config",
        lambda: _runtime_stub(provider="openrouter"),
    )

    svc = LLMService(api_key="")
    assert svc.api_key == "test-root-key"


def test_llm_service_ask_surfaces_provider_error_message(monkeypatch):
    class FakeChatOpenAI:
        def __init__(self, **_kwargs):
            pass

        def bind(self, **_kwargs):
            return self

        def invoke(self, _query):
            raise RuntimeError("API_KEY_INVALID: invalid key")

    monkeypatch.setattr("app.services.llm_service.create_chat_model", lambda **_kwargs: FakeChatOpenAI())
    monkeypatch.setattr("app.services.llm_service.load_llm_runtime_config", lambda: _runtime_stub())
    svc = LLMService(api_key="k")

    with pytest.raises(HTTPException) as exc:
        svc.ask("ping", str)

    assert exc.value.status_code == 500
    assert "API_KEY_INVALID" in exc.value.detail


def test_llm_service_ask_passes_max_tokens_to_factory(monkeypatch):
    captured = {"calls": []}

    class FakeChatOpenAI:
        def invoke(self, _query):
            return type("Resp", (), {"content": "OK"})()

    def fake_create_chat_model(**kwargs):
        captured["calls"].append(kwargs)
        return FakeChatOpenAI()

    monkeypatch.setattr("app.services.llm_service.create_chat_model", fake_create_chat_model)
    monkeypatch.setattr("app.services.llm_service.load_llm_runtime_config", lambda: _runtime_stub())
    svc = LLMService(api_key="k")

    result = svc.ask("ping", str, max_tokens=8)
    assert result == "OK"
    assert captured["calls"][-1]["max_tokens"] == 8


def test_llm_service_ask_uses_runtime_default_max_tokens_in_factory(monkeypatch):
    captured = {"calls": []}

    class FakeChatOpenAI:
        def invoke(self, _query):
            return type("Resp", (), {"content": "OK"})()

    def fake_create_chat_model(**kwargs):
        captured["calls"].append(kwargs)
        return FakeChatOpenAI()

    monkeypatch.setattr("app.services.llm_service.create_chat_model", fake_create_chat_model)
    monkeypatch.setattr("app.services.llm_service.load_llm_runtime_config", lambda: _runtime_stub())
    svc = LLMService(api_key="k")

    result = svc.ask("ping", str)
    assert result == "OK"
    assert captured["calls"][-1]["max_tokens"] == 4096


def test_llm_service_ask_suppresses_known_pydantic_serializer_warning(monkeypatch):
    class SchemaOutput(BaseModel):
        value: str

    captured = {"calls": []}

    class FakeStructuredChain:
        def invoke(self, _query):
            import warnings

            warnings.warn(
                "Pydantic serializer warnings:\n"
                "  PydanticSerializationUnexpectedValue(...)",
                UserWarning,
            )
            return SchemaOutput(value="ok")

    class FakeChatOpenAI:
        def with_structured_output(self, _fmt):
            return FakeStructuredChain()

    def fake_create_chat_model(**kwargs):
        captured["calls"].append(kwargs)
        return FakeChatOpenAI()

    monkeypatch.setattr("app.services.llm_service.create_chat_model", fake_create_chat_model)
    monkeypatch.setattr("app.services.llm_service.load_llm_runtime_config", lambda: _runtime_stub())
    svc = LLMService(api_key="k")

    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        result = svc.ask("ping", SchemaOutput)

    assert isinstance(result, SchemaOutput)
    assert result.value == "ok"
    assert len(captured_warnings) == 0
    assert captured["calls"][-1]["max_tokens"] == 4096


def test_llm_service_ollama_no_key(monkeypatch):
    runtime = SimpleNamespace(
        provider="ollama",
        base_url="http://localhost:11434/v1",
        requires_api_key=False,
        default_model="llama3.2",
        default_max_tokens=4096,
    )
    captured = {}

    class FakeModel:
        def invoke(self, _query):
            return type("Resp", (), {"content": "OK"})()

    monkeypatch.setattr("app.services.llm_service.load_llm_runtime_config", lambda: runtime)

    def _fake_create_chat_model(**kwargs):
        captured["kwargs"] = kwargs
        return FakeModel()

    monkeypatch.setattr("app.services.llm_service.create_chat_model", _fake_create_chat_model)
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    svc = LLMService(api_key="")
    assert svc.client is not None
    assert captured["kwargs"]["provider"] == "ollama"
    assert captured["kwargs"]["api_key"] == ""
