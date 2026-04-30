from __future__ import annotations

from pathlib import Path


def test_coding_prompt_prioritizes_schema_context_pack_and_batched_search() -> None:
    prompt_path = (
        Path(__file__).resolve().parents[1]
        / "agent_v2"
        / "coding_subagent"
        / "prompts"
        / "coding_system.yaml"
    )
    source = prompt_path.read_text(encoding="utf-8")

    assert "Use it first before requesting schema lookup tools" in source
    assert "batched into one `search_schema` call" in source
    assert "Avoid repeated or equivalent schema lookup requests" in source


def test_coding_prompt_enforces_bounded_materialization_rules() -> None:
    prompt_path = (
        Path(__file__).resolve().parents[1]
        / "agent_v2"
        / "coding_subagent"
        / "prompts"
        / "coding_system.yaml"
    )
    source = prompt_path.read_text(encoding="utf-8")

    assert "Convert to pandas only for a bounded final result" in source
    assert "Never materialize a raw full-table relation into pandas" in source
    assert "Build Plotly charts only from bounded aggregated data" in source


def test_react_prompt_matches_schema_lookup_policy() -> None:
    prompt_path = Path(__file__).resolve().parents[1] / "agent_v2" / "prompts" / "react_system.yaml"
    source = prompt_path.read_text(encoding="utf-8")

    assert "Use it first before requesting schema lookup tools" in source
    assert "batched into one `search_schema` call" in source
    assert "Avoid repeated or equivalent schema lookup requests" in source
