from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"


def test_makefile_set_version_updates_version_file_and_targets():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "set-version: check-input-version-greater" in text
    assert "scripts/maintenance/bump_versions.py" in text
    assert "--write-version-file" in text


def test_makefile_set_version_requires_greater_version_than_current():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "check-input-version-greater: check-input-version check-version-file" in text
    assert "must be greater than current VERSION" in text
    assert "Version check passed:" in text


def test_makefile_metadata_uses_release_metadata_script():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "metadata: check-version-file" in text
    assert "scripts/maintenance/generate_release_metadata.py" in text
    assert ".github/release/metadata.json" in text


def test_makefile_check_version_target_prints_all_versions():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "check-version:" in text
    assert "scripts/maintenance/show_versions.py" in text
    assert "make check-version" in text


def test_makefile_test_target_runs_backend_pytest():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "test:" in text
    assert "cd backend && uv run --group dev pytest" in text


def test_makefile_git_tag_reads_version_file():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "git-tag: check-no-version-arg check-version-file check-tag-not-latest" in text
    assert 'file_version="$$(tr -d' in text
    assert 'tag="v$$file_version"' in text


def test_makefile_git_commit_uses_commit_message_txt():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "commit_message.txt is missing or empty" in text
    assert 'current_msg="$$(cat commit_message.txt)"' in text
    assert "git commit -F commit_message.txt" in text
