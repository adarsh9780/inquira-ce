from pathlib import Path


def test_release_workflow_disables_draft_mode():
    repo_root = Path(__file__).resolve().parents[2]
    workflow = repo_root / ".github" / "workflows" / "release.yml"
    content = workflow.read_text(encoding="utf-8")

    assert "releaseDraft: true" not in content
    assert content.count("releaseDraft: false") == 3
    assert "--draft" not in content


def test_release_workflow_waits_for_ci_completion():
    repo_root = Path(__file__).resolve().parents[2]
    workflow = repo_root / ".github" / "workflows" / "release.yml"
    content = workflow.read_text(encoding="utf-8")

    assert "wait for completion" in content
    assert "maxAttempts = 60" in content
    assert "pollIntervalMs = 20000" in content
    assert "run.status !== \"completed\"" in content
