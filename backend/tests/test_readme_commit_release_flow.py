from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
DOCS = ROOT / "docs-site" / "docs"


def test_readme_is_docs_table_of_contents():
    text = README.read_text(encoding="utf-8")
    assert "<img src=\"./backend/app/logo/inquira_logo.svg\"" in text
    assert "img.shields.io" in text
    assert "## Quick Start" in text
    assert "## Official Documentation Map" in text
    assert "## Current Product Highlights" in text
    assert "https://docs.inquiraai.com/download" in text
    assert "create a local root `commit_message.txt` file" in text
    assert "https://docs.inquiraai.com/docs/architecture" in text
    assert "https://docs.inquiraai.com/docs/development" in text
    assert "https://docs.inquiraai.com/docs/roadmap" in text
    assert "## Upcoming Changes" not in text
    assert "**Supabase Auth**" not in text
    assert "align the auth page styling with the main UI" not in text


def test_ce_readme_links_to_hosted_docs_not_local_docs_site():
    text = README.read_text(encoding="utf-8")
    assert "https://docs.inquiraai.com/docs/" in text
    assert "./docs-site" not in text
