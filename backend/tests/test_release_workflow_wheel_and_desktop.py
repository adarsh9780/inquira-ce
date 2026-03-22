from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
MAKEFILE = ROOT / "Makefile"


def test_release_workflow_is_desktop_only():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "build_tauri:" in text
    assert "build_wheel:" not in text
    assert "publish_wheel_to_release:" not in text
    assert "publish_wheel_to_pypi:" not in text
    assert "uv build --wheel" not in text
    assert "gh-action-pypi-publish" not in text
    assert "dist/*.whl" not in text


def test_release_workflow_reuses_ci_instead_of_rerunning_validation():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "guard_release_prereqs:" in text
    assert "Ensure CI workflow succeeded for this tag commit" in text
    assert 'workflow_id: "ci.yml"' in text
    assert "validate_backend:" not in text
    assert "validate_frontend:" not in text
    assert "needs: [guard_release_prereqs]" in text


def test_release_workflow_windows_tauri_build_is_optional():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "build_tauri:" in text
    assert "continue-on-error: ${{ matrix.optional }}" in text
    assert "- os: windows-latest" in text
    assert "optional: true" in text


def test_release_workflow_sets_prerelease_flag_from_tag_shape():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "Detect release channel" in text
    assert 'if [[ "$ref_name" =~ ^v[0-9]+\\.[0-9]+\\.[0-9]+$ ]]; then' in text
    assert 'echo "prerelease=false" >> "$GITHUB_OUTPUT"' in text
    assert 'echo "prerelease=true" >> "$GITHUB_OUTPUT"' in text
    assert "prerelease: ${{ steps.release_channel.outputs.prerelease }}" in text
    assert "prerelease: true" not in text


def test_release_workflow_stages_bundled_uv_for_desktop_builds():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "build_tauri:" in text
    assert "- name: Setup UV" in text
    assert "uses: astral-sh/setup-uv@v4" in text
    assert 'uv-version: "0.6.3"' in text
    assert "- name: Stage bundled uv (macOS)" in text
    assert 'cp "$(command -v uv)" src-tauri/bundled-tools/uv' in text
    assert "- name: Stage bundled uv (Windows)" in text
    assert "Copy-Item (Get-Command uv).Source src-tauri/bundled-tools/uv.exe -Force" in text


def test_makefile_has_wheel_and_desktop_build_targets():
    text = MAKEFILE.read_text(encoding="utf-8")

    assert "build-desktop:" in text
    assert "cargo tauri build" in text
