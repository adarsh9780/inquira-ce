from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"


def test_makefile_exposes_pretty_targets_via_rich_runner():
    text = MAKEFILE.read_text(encoding="utf-8")

    assert "test-pretty:" in text
    assert "ruff-test-pretty:" in text
    assert "mypy-test-pretty:" in text
    assert "test-backend-pretty:" in text
    assert "test-frontend-pretty:" in text
    assert "check-version-pretty:" in text
    assert "uv run --with rich python scripts/maintenance/pretty_make.py test-pretty" in text
    assert "uv run --with rich python scripts/maintenance/pretty_make.py ruff-test-pretty" in text
    assert "uv run --with rich python scripts/maintenance/pretty_make.py mypy-test-pretty" in text
    assert (
        "uv run --with rich python scripts/maintenance/pretty_make.py test-backend-pretty"
        in text
    )
    assert (
        "uv run --with rich python scripts/maintenance/pretty_make.py test-frontend-pretty"
        in text
    )
    assert (
        "uv run --with rich python scripts/maintenance/pretty_make.py check-version-pretty"
        in text
    )


def test_makefile_fast_suite_covers_agent_rust_frontend_build_and_core_tests():
    text = MAKEFILE.read_text(encoding="utf-8")

    assert "test: test-fast" in text
    assert "test-fast: ruff-test mypy-test test-backend test-agent test-rust test-frontend build-frontend" in text
    assert "uv run --project agents --with pytest --with pytest-asyncio pytest agents/tests" in text
    assert "cd src-tauri && cargo test" in text
