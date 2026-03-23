from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
TAURI_CONF = ROOT / "src-tauri" / "tauri.conf.json"
BACKEND_PYPROJECT = ROOT / "backend" / "pyproject.toml"


def test_release_workflow_does_not_publish_python_wheels_or_pypi_artifacts():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "build_tauri:" in text
    assert "build_wheel:" not in text
    assert "publish_wheel_to_release:" not in text
    assert "publish_wheel_to_pypi:" not in text
    assert "gh-action-pypi-publish" not in text
    assert "dist/*.whl" not in text


def test_tauri_before_build_command_is_shell_portable():
    text = TAURI_CONF.read_text(encoding="utf-8")

    assert '"beforeBuildCommand": "npm --prefix . run build -- --outDir dist' in text
    assert "npm --prefix frontend run build -- --outDir dist" in text
    assert "npm --prefix ../frontend run build -- --outDir dist" in text
    assert "||" in text
    assert "[ -d frontend ]" not in text


def test_backend_pyproject_avoids_vcs_direct_dependency_for_runtime_stability():
    text = BACKEND_PYPROJECT.read_text(encoding="utf-8")

    assert "jupyter-client>=" in text
    assert "ipykernel>=" in text
    assert "safe-py-runner" not in text


def test_tauri_bundle_resources_include_backend_project_files():
    data = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
    resources = data.get("bundle", {}).get("resources", [])
    tauri_dir = TAURI_CONF.parent

    assert "../backend" not in resources
    assert "../backend/app" not in resources
    assert "../backend/app/__init__.py" in resources
    assert "../backend/app/main.py" in resources
    assert "../backend/app/app_config.json" in resources
    assert "../backend/app/agent" not in resources
    assert "../backend/app/api" not in resources
    assert "../backend/app/core" in resources
    assert "../backend/app/database" not in resources
    assert "../backend/app/legal" in resources
    assert "../backend/app/logo" in resources
    assert "../backend/app/services" in resources
    assert "../backend/app/tools" not in resources
    assert "../backend/app/v1" in resources
    assert "../agents" in resources
    assert "../backend/alembic" in resources
    assert "../backend/alembic.ini" in resources
    assert "../backend/main.py" in resources
    assert "../backend/pyproject.toml" in resources
    assert "../backend/uv.lock" in resources
    assert "../shared" not in resources
    assert "../shared/__init__.py" in resources
    assert "../shared/observability/__init__.py" in resources
    assert "../shared/observability/phoenix.py" in resources
    assert "../src-tauri/bundled-tools" in resources
    assert "../inquira.toml" in resources
    assert "../backend/app/static" not in resources

    for resource in resources:
        resolved = (tauri_dir / resource).resolve()
        assert resolved.exists(), f"Missing tauri bundle resource path: {resource}"


def test_tauri_bundle_resources_keep_shared_scope_tight():
    data = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
    resources = data.get("bundle", {}).get("resources", [])

    shared_resources = [resource for resource in resources if resource.startswith("../shared")]

    assert shared_resources == [
        "../shared/__init__.py",
        "../shared/observability/__init__.py",
        "../shared/observability/phoenix.py",
    ]
