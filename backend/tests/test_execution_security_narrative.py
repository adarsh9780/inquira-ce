from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_user_facing_execution_docs_do_not_claim_sandboxing() -> None:
    paths = [
        ROOT.parent / "README.md",
        ROOT.parent / "frontend" / "README.md",
        ROOT / "app" / "legal" / "terms.md",
        ROOT.parent / "frontend" / "public" / "terms-and-conditions.html",
    ]

    for path in paths:
        text = path.read_text(encoding="utf-8").lower()
        assert "sandboxed execution" not in text, path
        assert "user permissions" in text, path


def test_execution_policy_prompts_admit_local_user_permission_boundary() -> None:
    for relative in [
        "app/core/prompts/yaml/is_safe_prompt.yaml",
        "app/core/prompts/yaml/system_prompt.yaml",
    ]:
        text = (ROOT / relative).read_text(encoding="utf-8").lower()
        assert "not sandboxed" in text
        assert "operating-system permissions" in text
