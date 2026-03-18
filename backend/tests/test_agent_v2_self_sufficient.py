from pathlib import Path


def test_embedded_backend_agent_v2_removed_after_externalization() -> None:
    embedded = Path(__file__).resolve().parents[1] / "app" / "agent_v2"
    assert not embedded.exists(), "backend/app/agent_v2 must remain removed after runtime externalization"
