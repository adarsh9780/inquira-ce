from pathlib import Path


def test_tauri_agent_runtime_enables_langgraph_isolated_loops():
    repo_root = Path(__file__).resolve().parents[2]
    source = (repo_root / "src-tauri" / "src" / "lib.rs").read_text(encoding="utf-8")

    assert '.env("BG_JOB_ISOLATED_LOOPS", "true")' in source
