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


def test_validate_stable_version_accepts_release_and_v_prefix():
    mod = _load_module()
    assert mod.validate_stable_version("0.5.24") == "0.5.24"
    assert mod.validate_stable_version("v0.5.24") == "0.5.24"


def test_resolve_target_versions_allows_per_target_overrides():
    mod = _load_module()
    out = mod.resolve_target_versions(
        base_version="0.5.24",
        backend_version="0.5.25",
        tauri_version="0.5.26",
        frontend_version="0.5.27",
    )
    assert out == {
        "base": "0.5.24",
        "backend": "0.5.25",
        "tauri": "0.5.26",
        "frontend": "0.5.27",
    }


def test_run_updates_dry_run_reports_all_effective_versions():
    mod = _load_module()
    lines = mod.run_updates(base_version="0.6.0", dry_run=True)
    joined = "\n".join(lines)
    assert "base_version=0.6.0" in joined
    assert "backend_version=0.6.0" in joined
    assert "tauri_version=0.6.0" in joined
    assert "frontend_version=0.6.0" in joined
    assert "release_name=" not in joined


def test_stable_validation_rejects_prerelease_versions():
    mod = _load_module()
    try:
        mod.validate_stable_version("0.5.7a23")
        assert False, "Expected ValueError for prerelease format"
    except ValueError as exc:
        assert "Major.Minor.Patch" in str(exc)
    try:
        mod.validate_stable_version("0.5.7-alpha.23")
        assert False, "Expected ValueError for prerelease format"
    except ValueError as exc:
        assert "Major.Minor.Patch" in str(exc)


def test_run_updates_reports_core_versioned_files(monkeypatch, tmp_path: Path):
    mod = _load_module()

    backend_pyproject = tmp_path / "backend" / "pyproject.toml"
    backend_pyproject.parent.mkdir(parents=True, exist_ok=True)
    backend_pyproject.write_text('version = "0.5.23"\n', encoding="utf-8")

    backend_main = tmp_path / "backend" / "app" / "main.py"
    backend_main.parent.mkdir(parents=True, exist_ok=True)
    backend_main.write_text('APP_VERSION = "0.5.23"\n', encoding="utf-8")

    tauri_cargo = tmp_path / "src-tauri" / "Cargo.toml"
    tauri_cargo.parent.mkdir(parents=True, exist_ok=True)
    tauri_cargo.write_text('version = "0.5.23"\n', encoding="utf-8")

    tauri_conf = tmp_path / "src-tauri" / "tauri.conf.json"
    tauri_conf.write_text('{\n  "version": "0.5.23"\n}\n', encoding="utf-8")

    frontend_package = tmp_path / "frontend" / "package.json"
    frontend_package.parent.mkdir(parents=True, exist_ok=True)
    frontend_package.write_text('{\n  "version": "0.5.23"\n}\n', encoding="utf-8")

    frontend_lock = tmp_path / "frontend" / "package-lock.json"
    frontend_lock.write_text(
        '{\n  "version": "0.5.23",\n  "packages": {\n    "": {\n      "version": "0.5.23"\n    }\n  }\n}\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "BACKEND_PYPROJECT", backend_pyproject)
    monkeypatch.setattr(mod, "BACKEND_MAIN", backend_main)
    monkeypatch.setattr(mod, "TAURI_CARGO", tauri_cargo)
    monkeypatch.setattr(mod, "TAURI_CONF", tauri_conf)
    monkeypatch.setattr(mod, "FRONTEND_PACKAGE", frontend_package)
    monkeypatch.setattr(mod, "FRONTEND_LOCK", frontend_lock)

    results = mod.run_updates(base_version="0.5.24")

    assert any("backend/pyproject.toml" in line for line in results)
    assert any("backend/app/main.py" in line for line in results)
    assert any("src-tauri/Cargo.toml" in line for line in results)
    assert any("src-tauri/tauri.conf.json" in line for line in results)
    assert any("frontend/package.json" in line for line in results)
    assert any("frontend/package-lock.json" in line for line in results)


def test_run_updates_warns_for_missing_targets_instead_of_failing(monkeypatch, tmp_path: Path):
    mod = _load_module()

    backend_pyproject = tmp_path / "backend" / "pyproject.toml"
    backend_pyproject.parent.mkdir(parents=True, exist_ok=True)
    backend_pyproject.write_text('version = "0.5.23"\n', encoding="utf-8")

    tauri_cargo = tmp_path / "src-tauri" / "Cargo.toml"
    tauri_cargo.parent.mkdir(parents=True, exist_ok=True)
    tauri_cargo.write_text('version = "0.5.23"\n', encoding="utf-8")

    tauri_conf = tmp_path / "src-tauri" / "tauri.conf.json"
    tauri_conf.write_text('{\n  "version": "0.5.23"\n}\n', encoding="utf-8")

    frontend_package = tmp_path / "frontend" / "package.json"
    frontend_package.parent.mkdir(parents=True, exist_ok=True)
    frontend_package.write_text('{\n  "version": "0.5.23"\n}\n', encoding="utf-8")

    frontend_lock = tmp_path / "frontend" / "package-lock.json"
    frontend_lock.write_text(
        '{\n  "version": "0.5.23",\n  "packages": {\n    "": {\n      "version": "0.5.23"\n    }\n  }\n}\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "BACKEND_PYPROJECT", backend_pyproject)
    monkeypatch.setattr(mod, "BACKEND_MAIN", tmp_path / "backend" / "app" / "main.py")
    monkeypatch.setattr(mod, "TAURI_CARGO", tauri_cargo)
    monkeypatch.setattr(mod, "TAURI_CONF", tauri_conf)
    monkeypatch.setattr(mod, "FRONTEND_PACKAGE", frontend_package)
    monkeypatch.setattr(mod, "FRONTEND_LOCK", frontend_lock)

    results = mod.run_updates(base_version="0.5.24")

    assert any("warning=missing_file:backend/app/main.py" in line for line in results)
    assert not any("release/metadata.json" in line for line in results)
    assert not any("docs-site" in line for line in results)
