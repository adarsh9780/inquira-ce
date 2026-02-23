from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GITIGNORE = ROOT / ".gitignore"


def test_gitignore_blocks_common_cache_and_os_junk():
    text = GITIGNORE.read_text(encoding="utf-8")
    required_patterns = [
        "__pycache__/",
        ".pytest_cache/",
        ".mypy_cache/",
        ".ruff_cache/",
        ".coverage",
        "coverage/",
        ".DS_Store",
        "**/.DS_Store",
        "backend/.venv/",
        "frontend/dist/",
    ]
    for pattern in required_patterns:
        assert pattern in text
