from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
TAURI_CONF = ROOT / "src-tauri" / "tauri.conf.json"
BACKEND_PYPROJECT = ROOT / "backend" / "pyproject.toml"


def test_publish_wheel_to_release_checks_out_repo_for_gh_cli_context():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "publish_wheel_to_release:" in text
    assert "- uses: actions/checkout@v4" in text
    assert 'gh release upload "${GITHUB_REF_NAME}" dist/*.whl --clobber' in text


def test_tauri_before_build_command_is_shell_portable():
    text = TAURI_CONF.read_text(encoding="utf-8")

    assert '"beforeBuildCommand": "node -e ' in text
    assert "[ -d frontend ]" not in text


def test_backend_pyproject_avoids_vcs_direct_dependency_for_pypi():
    text = BACKEND_PYPROJECT.read_text(encoding="utf-8")

    assert "safe-py-runner>=0.1.6" in text
    assert "safe-py-runner @ git+https://" not in text
