from pathlib import Path


def test_agent_policy_example_does_not_reference_removed_pip_install_tool():
    policy_path = Path(__file__).resolve().parents[2] / "inquira.policy.toml.example"
    text = policy_path.read_text(encoding="utf-8")

    assert "tools.pip_install" not in text
    assert "pip_install" not in text
