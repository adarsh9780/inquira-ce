from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
CE_OPS = ROOT / "scripts" / "maintenance" / "ce_ops.py"


def test_makefile_setv_updates_version_file_and_targets():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "setv: check-input-version-greater" in text
    assert "scripts/maintenance/bump_versions.py" in text
    assert "--write-version-file" in text
    assert "set-version:" not in text


def test_makefile_setv_requires_greater_version_than_current():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "check-input-version-greater: check-input-version check-version-file" in text
    assert "scripts/maintenance/version_guard.py greater" in text


def test_makefile_exposes_repo_neutral_operational_targets():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "dev:" in text
    assert "ce_ops.py dev" in text
    assert "commit:" in text
    assert 'ce_ops.py commit --msg "$(or $(msg),$(MSG))" --file "$(or $(file),$(FILE))"' in text
    assert "push:" in text
    assert "ce_ops.py push" in text
    assert "tag:" in text
    assert "ce_ops.py tag --tag" in text
    assert "status:" in text
    assert "ce_ops.py status" in text
    assert "git-add:" not in text
    assert "git-commit:" not in text
    assert "git-push:" not in text
    assert "help-push:" not in text


def test_ce_ops_uses_windows_safe_dev_command_and_git_helpers():
    text = CE_OPS.read_text(encoding="utf-8")
    assert '["npm.cmd", "run", "dev"] if os.name == "nt" else ["npm", "run", "dev"]' in text
    assert '["cargo", "tauri", "dev"]' in text
    assert "def cmd_commit" in text
    assert "Provide either msg=... or file=..., not both." in text
    assert "def cmd_push" in text
    assert "Cannot push from a detached HEAD." in text
    assert "def cmd_tag" in text
    assert "Tag must look like vX.Y.Z or vX.Y.Z-suffix." in text


def test_makefile_check_version_target_prints_all_versions():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "check-version:" in text
    assert "scripts/maintenance/show_versions.py" in text
    assert "make check-version" in text


def test_makefile_test_target_runs_backend_and_frontend_tests():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "test: test-fast" in text
    assert (
        "test-fast: ruff-test mypy-test test-backend test-agent test-rust "
        "test-frontend build-frontend"
    ) in text
    assert "ruff-test:" in text
    assert "cd backend && uv run --group dev ruff check app/v1 tests" in text
    assert "mypy-test:" in text
    assert "cd backend && uv run --group dev mypy --config-file mypy.ini app/v1" in text
    assert "cd backend && uv run --group dev pytest" in text
    assert "cd frontend && npm ci && npm test" in text


def test_makefile_build_target_stages_uv_and_runs_ce_tauri_build():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "build:" in text
    assert "uv run python scripts/maintenance/bundle_uv.py" in text
    assert "cd src-tauri && cargo tauri build" in text


def test_tauri_build_precommand_installs_from_ce_root_frontend_path():
    text = (ROOT / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8")
    assert "npm --prefix frontend ci" in text
    assert "npm --prefix frontend run build -- --outDir dist" in text
    assert "../frontend ci" not in text


def test_makefile_git_commit_uses_commit_message_txt():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "commit:" in text
    assert "commit_message.txt is missing or empty" not in text
    assert 'current_msg="$$(cat commit_message.txt)"' not in text
    assert "git commit -F commit_message.txt" not in text
    assert ": > commit_message.txt" not in text


def test_makefile_no_longer_owns_desktop_release_or_tag_workflows():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "build-desktop" not in text
    assert "metadata:" not in text
    assert "git-tag:" not in text
    assert "help-release:" not in text
    assert "release:" not in text
