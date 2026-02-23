from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
MKDOCS_CONFIG = ROOT / "mkdocs.yml"
DOWNLOADS_DOC = ROOT / "docs" / "downloads.md"
INDEX_DOC = ROOT / "docs" / "index.md"
INSTALL_DOC = ROOT / "docs" / "install.md"
README = ROOT / "README.md"


def test_pages_workflow_builds_and_deploys_docs_site():
    text = PAGES_WORKFLOW.read_text(encoding="utf-8")

    assert "name: Docs Site" in text
    assert "actions/upload-pages-artifact@v3" in text
    assert "actions/deploy-pages@v4" in text
    assert "pages: write" in text
    assert "id-token: write" in text
    assert "mkdocs build" in text


def test_mkdocs_config_includes_downloads_and_core_docs_nav():
    text = MKDOCS_CONFIG.read_text(encoding="utf-8")

    assert "theme:" in text
    assert "name: material" in text
    assert "- Home: index.md" in text
    assert "- Downloads: downloads.md" in text
    assert "- CI And Release Automation: ci-and-release-automation.md" in text
    assert "pymdownx.superfences" in text
    assert "mermaid.min.js" in text
    assert "js/mermaid-init.js" in text


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


def test_docs_and_readme_no_longer_use_script_install_methods():
    docs = [
        README.read_text(encoding="utf-8"),
        INSTALL_DOC.read_text(encoding="utf-8"),
        DOWNLOADS_DOC.read_text(encoding="utf-8"),
    ]
    combined = "\n".join(docs)

    assert "curl -fsSL" not in combined
    assert "install-inquira.sh" not in combined
    assert "install-inquira.ps1" not in combined
    assert "irm " not in combined
