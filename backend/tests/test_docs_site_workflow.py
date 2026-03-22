from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
DOCS_SITE_CONFIG = ROOT / "docs-site" / "docusaurus.config.ts"
SIDEBARS = ROOT / "docs-site" / "sidebars.ts"
DOWNLOADS_DOC = ROOT / "docs-site" / "docs" / "downloads.md"
INDEX_DOC = ROOT / "docs-site" / "docs" / "index.md"
INSTALL_DOC = ROOT / "docs-site" / "docs" / "install.md"
README = ROOT / "README.md"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _desktop_asset_names() -> tuple[str, str]:
    release_version = VERSION.replace("a", "-alpha.")
    return (
        f"Inquira_{release_version}_aarch64.dmg",
        f"Inquira_{release_version}_x64-setup.exe",
    )


def test_pages_workflow_builds_and_deploys_docs_site():
    text = PAGES_WORKFLOW.read_text(encoding="utf-8")

    assert "name: Docs Site" in text
    assert "actions/upload-pages-artifact@v3" in text
    assert "actions/deploy-pages@v4" in text
    assert "pages: write" in text
    assert "id-token: write" in text
    assert "actions/setup-node@v4" in text
    assert "npm ci" in text
    assert "npm run build" in text
    assert "docs-site/build" in text


def test_docusaurus_config_and_sidebar_include_core_docs():
    config = DOCS_SITE_CONFIG.read_text(encoding="utf-8")
    sidebar = SIDEBARS.read_text(encoding="utf-8")

    assert "themes: ['@docusaurus/theme-mermaid']" in config
    assert "markdown: {" in config
    assert "mermaid: true" in config
    assert "'index'" in sidebar
    assert "'downloads'" in sidebar
    assert "'ci-and-release-automation'" in sidebar


def test_downloads_doc_links_release_and_api():
    text = DOWNLOADS_DOC.read_text(encoding="utf-8")
    macos_asset, windows_asset = _desktop_asset_names()

    assert "https://github.com/adarsh9780/inquira-ce/releases/latest" in text
    assert macos_asset in text
    assert windows_asset in text
    assert "pypi.org/project/inquira-ce/" not in text
    assert "https://api.github.com/repos/adarsh9780/inquira-ce/releases/latest" in text


def test_index_doc_mentions_desktop_distribution_channel():
    text = INDEX_DOC.read_text(encoding="utf-8")

    assert "pip install inquira-ce" not in text
    assert "Python package" not in text
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


def test_install_doc_points_to_versioned_desktop_assets():
    text = INSTALL_DOC.read_text(encoding="utf-8")
    macos_asset, windows_asset = _desktop_asset_names()

    assert macos_asset in text
    assert windows_asset in text
