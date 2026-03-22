from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS_SITE = ROOT / "docs-site"


def test_docs_site_exists_with_inquira_branding():
    assert DOCS_SITE.exists()

    config = (DOCS_SITE / "docusaurus.config.ts").read_text(encoding="utf-8")
    home_page = (DOCS_SITE / "src" / "pages" / "index.tsx").read_text(encoding="utf-8")
    download_page = (DOCS_SITE / "src" / "pages" / "download.tsx").read_text(encoding="utf-8")
    custom_css = (DOCS_SITE / "src" / "css" / "custom.css").read_text(encoding="utf-8")

    assert "title: 'Inquira'" in config
    assert "blog: false" in config
    assert "src: 'img/inquira-icon.png'" in config
    assert "Desktop AI workspace" in home_page
    assert "Free should feel open" in home_page
    assert "api.github.com/repos/adarsh9780/inquira-ce/releases/latest" in download_page
    assert "Download for macOS" in download_page
    assert "Download for Windows" in download_page
    assert "--ifm-background-color: #fdfcf8;" in custom_css
    assert "--ifm-font-color-base: #27272a;" in custom_css
