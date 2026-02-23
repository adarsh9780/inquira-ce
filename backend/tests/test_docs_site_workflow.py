from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
MKDOCS_CONFIG = ROOT / "mkdocs.yml"
DOWNLOADS_DOC = ROOT / "docs" / "downloads.md"
INDEX_DOC = ROOT / "docs" / "index.md"


def test_pages_workflow_builds_and_deploys_docs_site():
    text = PAGES_WORKFLOW.read_text(encoding="utf-8")

    assert "name: Docs Site" in text
    assert "actions/upload-pages-artifact@v3" in text
    assert "actions/deploy-pages@v4" in text
    assert "pages: write" in text
    assert "id-token: write" in text
    assert "mkdocs build --strict" in text


def test_mkdocs_config_includes_downloads_and_core_docs_nav():
    text = MKDOCS_CONFIG.read_text(encoding="utf-8")

    assert "theme:" in text
    assert "name: material" in text
    assert "- Home: docs/index.md" in text
    assert "- Downloads: docs/downloads.md" in text
    assert "- CI And Release Automation: docs/ci-and-release-automation.md" in text


def test_downloads_doc_links_latest_release_and_pypi():
    text = DOWNLOADS_DOC.read_text(encoding="utf-8")

    assert "https://github.com/adarsh9780/inquira-ce/releases/latest" in text
    assert "https://pypi.org/project/inquira-ce/" in text
    assert "https://api.github.com/repos/adarsh9780/inquira-ce/releases/latest" in text


def test_index_doc_mentions_distribution_channels():
    text = INDEX_DOC.read_text(encoding="utf-8")

    assert "pip install inquira-ce" in text
    assert "Desktop installers" in text
    assert "Open latest release" in text
