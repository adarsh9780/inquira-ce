from pathlib import Path


def test_result_explanation_prompt_requires_analyst_markdown_style() -> None:
    prompt = (
        Path(__file__).resolve().parents[1]
        / "agent_v2"
        / "prompts"
        / "result_explanation_system.yaml"
    ).read_text(encoding="utf-8")

    assert "Write like a strong business analyst" in prompt
    assert "Use markdown." in prompt
    assert "## Answer" in prompt
    assert "## Key Findings" in prompt
    assert "## Why It Matters" in prompt
    assert "## Caveats" in prompt
    assert "Do not sound like a generic assistant" in prompt
    assert "Avoid filler phrases like" in prompt
