import warnings
from types import SimpleNamespace

from langchain_core.messages import HumanMessage

from app.agent_v2.router import RouteDecision, decide_route


class _FakeChain:
    def invoke(self, _payload):
        warnings.warn(
            "Pydantic serializer warnings:\n"
            "  PydanticSerializationUnexpectedValue(...)",
            UserWarning,
        )
        return RouteDecision(route="analysis")


class _FakePrompt:
    def __or__(self, _rhs):
        return _FakeChain()


class _FakeChatOpenAI:
    def with_structured_output(self, _schema):
        return object()


def test_decide_route_suppresses_known_pydantic_serializer_warning(monkeypatch):
    monkeypatch.setattr("app.agent_v2.router.create_chat_model", lambda **_kwargs: _FakeChatOpenAI())
    monkeypatch.setattr(
        "app.agent_v2.router.load_llm_runtime_config",
        lambda: SimpleNamespace(
            provider="openrouter",
            requires_api_key=True,
            base_url="http://localhost:4000/v1",
            lite_model="google/gemini-2.5-flash-lite",
            default_model="google/gemini-2.5-flash",
        ),
    )
    monkeypatch.setattr(
        "app.agent_v2.router.ChatPromptTemplate.from_messages",
        lambda *_args, **_kwargs: _FakePrompt(),
    )

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        route = decide_route(
            [HumanMessage(content="show me sample rows")],
            {"api_key": "key", "model": "google/gemini-2.5-flash"},
        )

    assert route == "analysis"
    assert len(captured) == 0


def test_decide_route_skips_llm_for_ollama_provider(monkeypatch):
    called = {"create": 0}
    monkeypatch.setattr(
        "app.agent_v2.router.load_llm_runtime_config",
        lambda: SimpleNamespace(
            provider="ollama",
            requires_api_key=False,
            base_url="http://localhost:11434/v1",
            lite_model="llama3.2",
            default_model="llama3.2",
        ),
    )
    monkeypatch.setattr(
        "app.agent_v2.router.create_chat_model",
        lambda **_kwargs: called.__setitem__("create", called["create"] + 1),
    )

    route = decide_route(
        [HumanMessage(content="show row count by region")],
        {"api_key": "", "model": "llama3.2"},
    )

    assert route == "analysis"
    assert called["create"] == 0
