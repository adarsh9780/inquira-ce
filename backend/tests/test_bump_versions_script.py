from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "maintenance" / "bump_versions.py"


def _load_module():
    spec = spec_from_file_location("bump_versions", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load bump_versions script module")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pep440_to_tauri_semver_prerelease_mapping():
    mod = _load_module()
    assert mod.pep440_to_tauri_semver("0.5.0a1") == "0.5.0-alpha.1"
    assert mod.pep440_to_tauri_semver("0.5.0b2") == "0.5.0-beta.2"
    assert mod.pep440_to_tauri_semver("0.5.0rc3") == "0.5.0-rc.3"
    assert mod.pep440_to_tauri_semver("0.5.0") == "0.5.0"


def test_resolve_target_versions_allows_per_target_overrides():
    mod = _load_module()
    out = mod.resolve_target_versions(
        base_version="0.5.0a1",
        backend_version="0.5.1a2",
        tauri_version="0.5.1-alpha.2",
        frontend_version="0.5.0a1",
    )
    assert out == {
        "base": "0.5.0a1",
        "backend": "0.5.1a2",
        "tauri": "0.5.1-alpha.2",
        "frontend": "0.5.0a1",
    }


def test_run_updates_dry_run_reports_all_effective_versions():
    mod = _load_module()
    lines = mod.run_updates(base_version="0.6.0a1", dry_run=True)
    joined = "\n".join(lines)
    assert "base_version=0.6.0a1" in joined
    assert "backend_version=0.6.0a1" in joined
    assert "tauri_version=0.6.0-alpha.1" in joined
    assert "frontend_version=0.6.0-alpha.1" in joined
    assert "wheel_url=" not in joined


def test_normalize_version_input_accepts_tag_style():
    mod = _load_module()
    assert mod.normalize_version_input("v0.5.0a6") == "0.5.0a6"
    assert mod.normalize_version_input("0.5.0a6") == "0.5.0a6"


def test_update_release_metadata_writes_versioned_json(
    monkeypatch, tmp_path: Path
):
    mod = _load_module()
    source = tmp_path / "release_metadata.md"
    source.write_text(
        "# Release v0.5.7a9\n\n- Fix workspace kernel release notes drift.\n",
        encoding="utf-8",
    )
    output = tmp_path / ".github" / "release" / "metadata.json"

    monkeypatch.setattr(mod, "RELEASE_METADATA_SOURCE", source)
    monkeypatch.setattr(mod, "RELEASE_METADATA_JSON", output)

    changed = mod.update_release_metadata("0.5.7a9")

    assert changed is True
    payload = output.read_text(encoding="utf-8")
    assert '"version": "0.5.7a9"' in payload
    assert '"tag": "v0.5.7a9"' in payload
    assert '"release_name": "Release v0.5.7a9"' in payload


def test_run_updates_reports_release_metadata_json_when_refreshed(
    monkeypatch, tmp_path: Path
):
    mod = _load_module()

    backend_pyproject = tmp_path / "backend" / "pyproject.toml"
    backend_pyproject.parent.mkdir(parents=True, exist_ok=True)
    backend_pyproject.write_text('version = "0.5.7a8"\n', encoding="utf-8")

    backend_main = tmp_path / "backend" / "app" / "main.py"
    backend_main.parent.mkdir(parents=True, exist_ok=True)
    backend_main.write_text('APP_VERSION = "0.5.7a8"\n', encoding="utf-8")

    tauri_cargo = tmp_path / "src-tauri" / "Cargo.toml"
    tauri_cargo.parent.mkdir(parents=True, exist_ok=True)
    tauri_cargo.write_text('version = "0.5.7-alpha.8"\n', encoding="utf-8")

    tauri_conf = tmp_path / "src-tauri" / "tauri.conf.json"
    tauri_conf.write_text('{\n  "version": "0.5.7-alpha.8"\n}\n', encoding="utf-8")

    frontend_package = tmp_path / "frontend" / "package.json"
    frontend_package.parent.mkdir(parents=True, exist_ok=True)
    frontend_package.write_text('{\n  "version": "0.5.7-alpha.8"\n}\n', encoding="utf-8")

    frontend_lock = tmp_path / "frontend" / "package-lock.json"
    frontend_lock.write_text(
        '{\n  "version": "0.5.7-alpha.8",\n  "packages": {\n    "": {\n      "version": "0.5.7-alpha.8"\n    }\n  }\n}\n',
        encoding="utf-8",
    )

    release_source = tmp_path / "release_metadata.md"
    release_source.write_text("# Release v0.5.7a9\n\n- Notes\n", encoding="utf-8")
    release_output = tmp_path / ".github" / "release" / "metadata.json"

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "BACKEND_PYPROJECT", backend_pyproject)
    monkeypatch.setattr(mod, "BACKEND_MAIN", backend_main)
    monkeypatch.setattr(mod, "TAURI_CARGO", tauri_cargo)
    monkeypatch.setattr(mod, "TAURI_CONF", tauri_conf)
    monkeypatch.setattr(mod, "FRONTEND_PACKAGE", frontend_package)
    monkeypatch.setattr(mod, "FRONTEND_LOCK", frontend_lock)
    monkeypatch.setattr(mod, "RELEASE_METADATA_SOURCE", release_source)
    monkeypatch.setattr(mod, "RELEASE_METADATA_JSON", release_output)

    results = mod.run_updates(base_version="0.5.7a9")

    assert any(
        ".github/release/metadata.json" in line for line in results
    )
