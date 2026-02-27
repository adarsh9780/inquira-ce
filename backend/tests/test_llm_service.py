import pytest
import warnings
from fastapi import HTTPException
from pydantic import BaseModel

from app.services.llm_service import LLMService


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
    monkeypatch.setattr("app.services.llm_service.ChatOpenAI", lambda **_kwargs: object())

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

    monkeypatch.setattr("app.services.llm_service.ChatOpenAI", FakeChatOpenAI)
    svc = LLMService(api_key="k")

    with pytest.raises(HTTPException) as exc:
        svc.ask("ping", str)

    assert exc.value.status_code == 500
    assert "API_KEY_INVALID" in exc.value.detail


def test_llm_service_ask_passes_max_tokens_to_bound_client(monkeypatch):
    captured = {}

    class FakeBoundClient:
        def invoke(self, _query):
            return type("Resp", (), {"content": "OK"})()

    class FakeChatOpenAI:
        def __init__(self, **_kwargs):
            pass

        def bind(self, **kwargs):
            captured["max_tokens"] = kwargs.get("max_tokens")
            return FakeBoundClient()

    monkeypatch.setattr("app.services.llm_service.ChatOpenAI", FakeChatOpenAI)
    svc = LLMService(api_key="k")

    result = svc.ask("ping", str, max_tokens=8)
    assert result == "OK"
    assert captured["max_tokens"] == 8


def test_llm_service_ask_uses_runtime_default_max_tokens(monkeypatch):
    captured = {}

    class FakeBoundClient:
        def invoke(self, _query):
            return type("Resp", (), {"content": "OK"})()

    class FakeChatOpenAI:
        def __init__(self, **_kwargs):
            pass

        def bind(self, **kwargs):
            captured["max_tokens"] = kwargs.get("max_tokens")
            return FakeBoundClient()

    monkeypatch.setattr("app.services.llm_service.ChatOpenAI", FakeChatOpenAI)
    svc = LLMService(api_key="k")

    result = svc.ask("ping", str)
    assert result == "OK"
    assert captured["max_tokens"] == 4096


def test_llm_service_ask_suppresses_known_pydantic_serializer_warning(monkeypatch):
    class SchemaOutput(BaseModel):
        value: str

    class FakeStructuredChain:
        def invoke(self, _query):
            import warnings

            warnings.warn(
                "Pydantic serializer warnings:\n"
                "  PydanticSerializationUnexpectedValue(...)",
                UserWarning,
            )
            return SchemaOutput(value="ok")

    class FakeBoundClient:
        def with_structured_output(self, _fmt):
            return FakeStructuredChain()

    class FakeChatOpenAI:
        def __init__(self, **_kwargs):
            pass

        def bind(self, **_kwargs):
            return FakeBoundClient()

    monkeypatch.setattr("app.services.llm_service.ChatOpenAI", FakeChatOpenAI)
    svc = LLMService(api_key="k")

    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        result = svc.ask("ping", SchemaOutput)

    assert isinstance(result, SchemaOutput)
    assert result.value == "ok"
    assert len(captured_warnings) == 0
