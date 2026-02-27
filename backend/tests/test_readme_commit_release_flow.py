from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
DOCS = ROOT / "docs"


def test_readme_is_docs_table_of_contents():
    text = README.read_text(encoding="utf-8")
    assert "<img src=\"./backend/app/logo/inquira_logo.svg\"" in text
    assert "img.shields.io" in text
    assert "## Quick Start" in text
    assert "## Documentation Map" in text
    assert "make check-version" in text
    assert "make ruff-test" in text
    assert "make mypy-test" in text
    assert "create a local root `commit_message.txt` file" in text
    assert "./docs/overview.md" in text
    assert "./docs/commit-and-release.md" in text
    assert "./docs/changelog.md" in text


def test_docs_chain_has_next_links():
    expected = {
        "overview.md": "Next: [Install](./install.md)",
        "install.md": "Next: [Development](./development.md)",
        "development.md": "Next: [Commit And Release Flow](./commit-and-release.md)",
        "commit-and-release.md": "Next: [CI And Release Automation](./ci-and-release-automation.md)",
        "ci-and-release-automation.md": "Next: [Architecture](./architecture.md)",
        "architecture.md": "Next: [Roadmap](./roadmap.md)",
        "roadmap.md": "Next: [Contributing](./contributing.md)",
        "contributing.md": "Next: [Changelog](./changelog.md)",
        "changelog.md": "Next: [Back To Overview](./overview.md)",
    }
    for name, marker in expected.items():
        text = (DOCS / name).read_text(encoding="utf-8")
        assert marker in text
