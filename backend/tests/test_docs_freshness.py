from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_ce_repo_no_longer_owns_docs_site():
    assert not (ROOT / "docs-site").exists()


def test_readme_omits_internal_misc_links_from_primary_map():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "./docs/gemini.md" not in readme
    assert "./docs/dummy.md" not in readme
