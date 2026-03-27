from pathlib import Path


def test_agent_runtime_hot_path_avoids_path_resolve_calls() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    guarded_files = [
        repo_root / "agents" / "agent_v2" / "router.py",
        repo_root / "agents" / "agent_v2" / "nodes.py",
        repo_root / "agents" / "agent_v2" / "runtime.py",
        repo_root / "agents" / "agent_v2" / "services" / "llm_runtime_config.py",
        repo_root / "agents" / "agent_v2" / "services" / "tracing.py",
        repo_root / "agents" / "agent_v2" / "coding_subagent" / "generator.py",
        repo_root / "agents" / "agent_v2" / "tools" / "bash_tool.py",
    ]

    violations: list[str] = []
    for file_path in guarded_files:
        source = file_path.read_text(encoding="utf-8")
        if ".resolve(" in source:
            violations.append(str(file_path))

    assert not violations, (
        "Agent runtime hot-path files must avoid Path.resolve() to prevent "
        "LangGraph blocking detection via implicit os.getcwd:\n"
        + "\n".join(violations)
    )
