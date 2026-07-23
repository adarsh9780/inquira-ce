from __future__ import annotations

import importlib.util
import re
import tomllib
from dataclasses import fields
from pathlib import Path

from inquira_data_worker.agent_v2 import nodes
from inquira_data_worker.agent_v2.runtime import AgentRuntimeConfig
from inquira_data_worker.langgraph_agent import LangGraphAnalysisAgent
from inquira_data_worker.runtime import WorkerRuntime


def test_worker_uses_the_langgraph_agent_only() -> None:
    runtime = WorkerRuntime()
    agent_root = Path(nodes.__file__).parent

    assert isinstance(runtime.agent, LangGraphAnalysisAgent)
    assert importlib.util.find_spec("inquira_data_worker.agent") is None
    assert importlib.util.find_spec("inquira_data_worker.agent_guard") is None
    assert importlib.util.find_spec("inquira_data_worker.interventions") is None
    assert importlib.util.find_spec("inquira_data_worker.agent_v2.services.tracing") is None
    assert importlib.util.find_spec("inquira_data_worker.agent_v2.tools.bash_tool") is None
    assert importlib.util.find_spec("inquira_data_worker.agent_v2.tools.finish_analysis") is None
    assert not hasattr(runtime, "interventions")
    assert not hasattr(nodes, "analysis_execute_code_node")
    assert not hasattr(nodes, "analysis_assess_context_node")
    assert not hasattr(nodes, "analysis_assess_to_next")
    assert not hasattr(nodes, "react_loop_node")
    assert not (agent_root / "manifest.json").exists()
    assert not (agent_root / "prompts" / "react_system.yaml").exists()
    assert not (agent_root / "coding_subagent" / "graph.py").exists()


def test_local_worker_configuration_contains_only_consumed_local_settings() -> None:
    field_names = {field.name for field in fields(AgentRuntimeConfig)}

    assert field_names == {
        "max_tool_calls",
        "max_code_executions",
        "turn_timeout",
        "memory_max_recent_messages",
        "memory_max_summary_tokens",
    }


def test_worker_declares_the_langchain_packages_it_imports() -> None:
    project = tomllib.loads(
        (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )
    dependencies = {
        re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*", str(item)).group(0)
        for item in project["project"]["dependencies"]
    }

    assert "langchain-core" in dependencies
    assert "langchain" not in dependencies
