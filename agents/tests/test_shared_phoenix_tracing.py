from __future__ import annotations

import sys
from pathlib import Path

# Ensure shared modules at repo root are importable in agent test runs.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.observability import phoenix


def _build_fake_otel_setup(called: dict) -> dict:
    class FakeResourceAttributes:
        PROJECT_NAME = "openinference.project.name"

    class FakeResource:
        def __init__(self, attributes):
            self.attributes = attributes

    class FakeTracerProvider:
        def __init__(self, resource):
            called["resource"] = resource
            self.processors = []

        def add_span_processor(self, processor):
            self.processors.append(processor)
            called["span_processor"] = processor

    class FakeOTLPSpanExporter:
        def __init__(self, **kwargs):
            called["exporter_kwargs"] = kwargs

    class FakeBatchSpanProcessor:
        def __init__(self, exporter):
            called["span_exporter"] = exporter

    class FakeTraceApi:
        @staticmethod
        def set_tracer_provider(*, tracer_provider):
            called["trace_provider"] = tracer_provider

    class FakeLangChainInstrumentor:
        def instrument(self, *, tracer_provider):
            called["instrumented_provider"] = tracer_provider

    return {
        "LangChainInstrumentor": FakeLangChainInstrumentor,
        "ResourceAttributes": FakeResourceAttributes,
        "trace_api": FakeTraceApi,
        "OTLPSpanExporter": FakeOTLPSpanExporter,
        "Resource": FakeResource,
        "TracerProvider": FakeTracerProvider,
        "BatchSpanProcessor": FakeBatchSpanProcessor,
    }


def test_shared_phoenix_uses_agent_service_section(monkeypatch, tmp_path):
    called = {}

    cfg = tmp_path / "inquira.toml"
    cfg.write_text(
        """
[agent_service.phoenix]
enabled = true
project = "agent-from-toml"
endpoint = "http://127.0.0.1:6006/v1/traces"
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))
    monkeypatch.delenv("INQUIRA_AGENT_PHOENIX_ENABLED", raising=False)
    monkeypatch.delenv("INQUIRA_AGENT_PHOENIX_PROJECT", raising=False)
    monkeypatch.delenv("INQUIRA_AGENT_PHOENIX_ENDPOINT", raising=False)
    phoenix.reset_phoenix_tracing_state()

    assert (
        phoenix.init_phoenix_tracing(
            section_path=("agent_service", "phoenix"),
            enabled_env="INQUIRA_AGENT_PHOENIX_ENABLED",
            project_env="INQUIRA_AGENT_PHOENIX_PROJECT",
            endpoint_env="INQUIRA_AGENT_PHOENIX_ENDPOINT",
            default_project="inquira-agent",
            load_otel_setup=lambda: _build_fake_otel_setup(called),
        )
        is True
    )
    assert called["resource"].attributes["openinference.project.name"] == "agent-from-toml"
    assert called["exporter_kwargs"]["endpoint"] == "http://127.0.0.1:6006/v1/traces"
    assert called["instrumented_provider"] is called["trace_provider"]


def test_shared_phoenix_env_overrides_toml(monkeypatch, tmp_path):
    called = {}

    cfg = tmp_path / "inquira.toml"
    cfg.write_text(
        """
[agent_service.phoenix]
enabled = false
project = "from-toml"
endpoint = "http://toml:6006/v1/traces"
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))
    monkeypatch.setenv("INQUIRA_AGENT_PHOENIX_ENABLED", "true")
    monkeypatch.setenv("INQUIRA_AGENT_PHOENIX_PROJECT", "from-env")
    monkeypatch.setenv("INQUIRA_AGENT_PHOENIX_ENDPOINT", "http://env:6006/v1/traces")
    phoenix.reset_phoenix_tracing_state()

    assert (
        phoenix.init_phoenix_tracing(
            section_path=("agent_service", "phoenix"),
            enabled_env="INQUIRA_AGENT_PHOENIX_ENABLED",
            project_env="INQUIRA_AGENT_PHOENIX_PROJECT",
            endpoint_env="INQUIRA_AGENT_PHOENIX_ENDPOINT",
            default_project="inquira-agent",
            load_otel_setup=lambda: _build_fake_otel_setup(called),
        )
        is True
    )
    assert called["resource"].attributes["openinference.project.name"] == "from-env"
    assert called["exporter_kwargs"]["endpoint"] == "http://env:6006/v1/traces"


def test_shared_phoenix_disabled_returns_false(monkeypatch, tmp_path):
    called = {"invoked": False}

    cfg = tmp_path / "inquira.toml"
    cfg.write_text(
        """
[agent_service.phoenix]
enabled = false
project = "disabled"
endpoint = "http://127.0.0.1:6006/v1/traces"
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))
    monkeypatch.delenv("INQUIRA_AGENT_PHOENIX_ENABLED", raising=False)
    phoenix.reset_phoenix_tracing_state()

    assert (
        phoenix.init_phoenix_tracing(
            section_path=("agent_service", "phoenix"),
            enabled_env="INQUIRA_AGENT_PHOENIX_ENABLED",
            project_env="INQUIRA_AGENT_PHOENIX_PROJECT",
            endpoint_env="INQUIRA_AGENT_PHOENIX_ENDPOINT",
            default_project="inquira-agent",
            load_otel_setup=lambda: called.update({"invoked": True}),
        )
        is False
    )
    assert called["invoked"] is False
