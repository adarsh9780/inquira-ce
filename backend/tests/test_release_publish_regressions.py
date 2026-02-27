from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
TAURI_CONF = ROOT / "src-tauri" / "tauri.conf.json"
BACKEND_PYPROJECT = ROOT / "backend" / "pyproject.toml"


def test_publish_wheel_to_release_checks_out_repo_for_gh_cli_context():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "publish_wheel_to_release:" in text
    assert "- uses: actions/checkout@v4" in text
    assert "Ensure GitHub release exists" in text
    assert 'gh release view "${GITHUB_REF_NAME}"' in text
    assert 'gh release create "${GITHUB_REF_NAME}"' in text
    assert 'gh release upload "${GITHUB_REF_NAME}" dist/*.whl --clobber' in text


def test_tauri_before_build_command_is_shell_portable():
    text = TAURI_CONF.read_text(encoding="utf-8")

    assert '"beforeBuildCommand": "npm --prefix . run build -- --outDir dist' in text
    assert "npm --prefix frontend run build -- --outDir dist" in text
    assert "npm --prefix ../frontend run build -- --outDir dist" in text
    assert "||" in text
    assert "[ -d frontend ]" not in text


def test_backend_pyproject_avoids_vcs_direct_dependency_for_pypi():
    text = BACKEND_PYPROJECT.read_text(encoding="utf-8")

    assert "jupyter-client>=" in text
    assert "ipykernel>=" in text
    assert "safe-py-runner" not in text


def test_tauri_bundle_resources_include_backend_project_files():
    data = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
    resources = data.get("bundle", {}).get("resources", [])

    assert "../backend" not in resources
    assert "../backend/app" not in resources
    assert "../backend/app/__init__.py" in resources
    assert "../backend/app/main.py" in resources
    assert "../backend/app/app_config.json" in resources
    assert "../backend/app/agent" in resources
    assert "../backend/app/api" in resources
    assert "../backend/app/core" in resources
    assert "../backend/app/database" in resources
    assert "../backend/app/legal" in resources
    assert "../backend/app/logo" in resources
    assert "../backend/app/services" in resources
    assert "../backend/app/tools" in resources
    assert "../backend/app/v1" in resources
    assert "../backend/alembic" in resources
    assert "../backend/alembic.ini" in resources
    assert "../backend/main.py" in resources
    assert "../backend/pyproject.toml" in resources
    assert "../backend/uv.lock" in resources
    assert "../src-tauri/bundled-tools" in resources
    assert "../inquira.toml" in resources
    assert "../backend/app/static" not in resources
