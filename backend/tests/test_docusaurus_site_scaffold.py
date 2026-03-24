from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS_SITE = ROOT / "docs-site"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _desktop_asset_names() -> tuple[str, str]:
    release_version = VERSION.replace("a", "-alpha.")
    return (
        f"Inquira_{release_version}_aarch64.dmg",
        f"Inquira_{release_version}_x64-setup.exe",
    )


def test_docs_site_exists_with_inquira_branding():
    assert DOCS_SITE.exists()
    macos_asset, windows_asset = _desktop_asset_names()

    config = (DOCS_SITE / "docusaurus.config.ts").read_text(encoding="utf-8")
    home_page = (DOCS_SITE / "src" / "pages" / "index.tsx").read_text(encoding="utf-8")
    download_page = (DOCS_SITE / "src" / "pages" / "download.tsx").read_text(encoding="utf-8")
    custom_css = (DOCS_SITE / "src" / "css" / "custom.css").read_text(encoding="utf-8")
    custom_css_lower = custom_css.lower()

    assert "title: 'Inquira'" in config
    assert "blog: false" in config
    assert "favicon: 'img/favicon.ico'" in config
    assert "image: 'img/inquira-social-card.png'" in config
    assert "src: 'img/inquira-logo-animated.svg'" in config
    assert "Desktop-First AI Workspace" in home_page
    assert "Analyze data at the speed of thought." in home_page
    assert "api.github.com/repos/adarsh9780/inquira-ce/releases/latest" in download_page
    assert macos_asset in download_page
    assert windows_asset in download_page
    assert "Download for macOS" in download_page
    assert "Download for Windows" in download_page
    assert "--ifm-background-color: #fdfcf8;" in custom_css_lower
    assert "--ifm-font-color-base: #27272a;" in custom_css_lower
