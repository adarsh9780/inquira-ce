from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEBUG_BUILD_WORKFLOW = ROOT / ".github" / "workflows" / "debug-build.yml"


def test_debug_build_workflow_is_manual_only():
    text = DEBUG_BUILD_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "push:" not in text
    assert '- "**"' not in text


def test_debug_build_workflow_uses_node24_ready_actions():
    text = DEBUG_BUILD_WORKFLOW.read_text(encoding="utf-8")

    assert "uses: actions/checkout@v6" in text
    assert "uses: actions/setup-node@v6" in text
    assert "uses: astral-sh/setup-uv@v7" in text
