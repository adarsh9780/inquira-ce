from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def test_ci_workflow_uses_node24_ready_action_versions():
    text = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "uses: actions/checkout@v6" in text
    assert "uses: actions/setup-node@v6" in text
    assert "uses: astral-sh/setup-uv@v7" in text


def test_ci_workflow_pins_supported_python_for_uv_jobs():
    text = CI_WORKFLOW.read_text(encoding="utf-8")

    assert 'python-version: "3.13"' in text
    assert "uv sync --group dev" in text
    assert "uv sync --project backend --group dev" in text
