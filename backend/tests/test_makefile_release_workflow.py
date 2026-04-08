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
    assert "scripts/maintenance/version_guard.py greater" in text


def test_makefile_check_version_target_prints_all_versions():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "check-version:" in text
    assert "scripts/maintenance/show_versions.py" in text
    assert "make check-version" in text


def test_makefile_test_target_runs_backend_and_frontend_tests():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "test:" in text
    assert "test: ruff-test mypy-test test-backend test-frontend" in text
    assert "ruff-test:" in text
    assert "cd backend && uv run --group dev ruff check app/v1 tests" in text
    assert "mypy-test:" in text
    assert "cd backend && uv run --group dev mypy --config-file mypy.ini app/v1" in text
    assert "cd backend && uv run --group dev pytest" in text
    assert "cd frontend && npm ci && npm test" in text


def test_makefile_build_target_stages_uv_and_runs_ce_tauri_build():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "build:" in text
    assert 'uv_path="$$(command -v uv)"' in text
    assert 'uv_name="$$(basename "$$uv_path")"' in text
    assert "mkdir -p src-tauri/bundled-tools" in text
    assert 'cp "$$uv_path" "src-tauri/bundled-tools/$$uv_name"' in text
    assert 'chmod +x "src-tauri/bundled-tools/$$uv_name"' in text
    assert "cd src-tauri && cargo tauri build" in text


def test_tauri_build_precommand_installs_from_ce_root_frontend_path():
    text = (ROOT / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8")
    assert "npm --prefix frontend ci" in text
    assert "npm --prefix frontend run build -- --outDir dist" in text
    assert "../frontend ci" not in text


def test_makefile_git_commit_uses_commit_message_txt():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "commit_message.txt is missing or empty" in text
    assert 'current_msg="$$(cat commit_message.txt)"' in text
    assert "git commit -F commit_message.txt" in text
    assert ": > commit_message.txt" in text


def test_makefile_no_longer_owns_desktop_release_or_tag_workflows():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "build-desktop" not in text
    assert "metadata:" not in text
    assert "git-tag:" not in text
    assert "help-release:" not in text
    assert "release:" not in text
