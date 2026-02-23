from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"


def test_release_docs_use_makefile_workflow():
    release_doc = (DOCS / "release_process.md").read_text(encoding="utf-8")
    assert "make set-version" in release_doc
    assert "make metadata" in release_doc
    assert "make git-tag" in release_doc

    contrib_doc = (DOCS / "contributing.md").read_text(encoding="utf-8")
    assert "make set-version" in contrib_doc
    assert "make metadata" in contrib_doc


def test_docs_do_not_contain_obvious_secret_placeholders():
    misc_doc = (DOCS / "dummy.md").read_text(encoding="utf-8")
    assert "AIza" not in misc_doc


def test_readme_omits_internal_misc_links_from_primary_map():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "./docs/gemini.md" not in readme
    assert "./docs/dummy.md" not in readme
