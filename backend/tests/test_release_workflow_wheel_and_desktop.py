from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
MAKEFILE = ROOT / "Makefile"


def test_release_workflow_publishes_wheel_independently_of_tauri():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "publish_wheel_to_release:" in text
    assert "needs: [build_wheel]" in text
    assert "needs: [build_wheel, build_tauri]" not in text


def test_release_workflow_publishes_wheel_to_pypi_environment():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "publish_wheel_to_pypi:" in text
    assert "environment: pypi" in text
    assert "pypa/gh-action-pypi-publish@release/v1" in text


def test_release_workflow_syncs_frontend_assets_for_wheel_packaging():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "Build frontend for wheel" in text
    assert "Sync frontend dist into backend package data" in text
    assert "cp -R src/inquira/frontend/dist backend/app/frontend/dist" in text


def test_makefile_has_wheel_and_desktop_build_targets():
    text = MAKEFILE.read_text(encoding="utf-8")

    assert "build-wheel: build-frontend sync-frontend-dist" in text
    assert "build-desktop:" in text
    assert "cargo tauri build" in text
    assert "cp -R src/inquira/frontend/dist backend/app/frontend/dist" in text
